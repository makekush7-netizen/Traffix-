"""Explicit accounts; no localhost bootstrap or default remote credentials."""
from collections import defaultdict, deque
import hashlib
import hmac
import secrets
import time
import json
import re
from pathlib import Path
import threading
from functools import wraps

def locked(method):
    @wraps(method)
    def wrapped(self,*args,**kwargs):
        with self._account_lock: return method(self,*args,**kwargs)
    return wrapped

class Auth:
    def __init__(self, accounts, clock=time.time, storage_path=None):
        self.clock=clock; self.accounts={}; self.sessions={}; self.attempts=defaultdict(deque)
        self._account_lock=threading.RLock()
        self.audit=deque(maxlen=1000)
        self.storage_path=Path(storage_path) if storage_path else None
        self.bootstrap=set()
        if self.storage_path and self.storage_path.exists():
            document=json.loads(self.storage_path.read_text(encoding='utf-8'))
            for name,value in document.get('accounts',{}).items():
                if self.normalize(name)!=name or value.get('role') not in ('operator','viewer') or value.get('can_takeover'):
                    raise ValueError('invalid_account_store')
                self.accounts[name]={**value,'salt':bytes.fromhex(value['salt']),'hash':bytes.fromhex(value['hash'])}
        for name, value in accounts.items():
            name=self.normalize(name); self.bootstrap.add(name)
            if value.get('role') not in ('operator','viewer'): raise ValueError('invalid_admin_role')
            if not isinstance(value.get('password'),str) or not value['password']: raise ValueError('empty_password')
            salt=secrets.token_bytes(16)
            self.accounts[name]={'role':value['role'],'can_takeover':value.get('can_takeover',False),
                'salt':salt,'hash':hashlib.scrypt(value['password'].encode(),salt=salt,n=16384,r=8,p=1)}
    @staticmethod
    def normalize(name): return name.strip().lower()

    def save(self):
        if not self.storage_path: return
        rows={name:{**value,'salt':value['salt'].hex(),'hash':value['hash'].hex()}
              for name,value in self.accounts.items() if name not in self.bootstrap}
        self.storage_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.storage_path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':1,'accounts':rows},indent=2),encoding='utf-8')
        temporary.replace(self.storage_path)

    @locked
    def register(self,username,password,remote,request_operator=True):
        name=self.normalize(username)
        if not re.fullmatch(r'[a-z][a-z0-9_.-]{2,31}',name): raise ValueError('invalid_username')
        if len(password)<8 or len(password)>256 or password.isspace(): raise ValueError('weak_password')
        self.rate_limit(remote,'register',5)
        if name in self.accounts: raise ValueError('username_unavailable')
        if len(self.accounts)>=256: raise ValueError('account_capacity')
        salt=secrets.token_bytes(16)
        self.accounts[name]={'role':'viewer','can_takeover':False,'operator_requested':bool(request_operator),
                            'salt':salt,'hash':hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1)}
        try: self.save()
        except OSError:
            del self.accounts[name]; raise
        return {'status':'registered','id':name,'role':'viewer','operator_requested':bool(request_operator)}

    def rate_limit(self,remote,kind,maximum):
        attempts=self.attempts[(remote,kind)]; now=self.clock()
        while attempts and attempts[0]<now-60: attempts.popleft()
        if len(attempts)>=maximum: raise ValueError(kind+'_rate_limited')
        attempts.append(now)

    @locked
    def list_users(self,actor):
        if actor['role']!='operator' or not actor.get('can_takeover'): raise ValueError('owner_required')
        return [{'id':name,'role':value['role'],'operator_requested':value.get('operator_requested',False),
                 'bootstrap':name in self.bootstrap} for name,value in sorted(self.accounts.items())]

    @locked
    def approve(self,actor,username):
        self.list_users(actor); name=self.normalize(username)
        if name in self.bootstrap: raise ValueError('bootstrap_account_protected')
        if name not in self.accounts: raise ValueError('unknown_account')
        old=dict(self.accounts[name]); self.accounts[name].update(role='operator',operator_requested=False)
        try: self.save()
        except OSError:
            self.accounts[name]=old; raise
        self.sessions={key:row for key,row in self.sessions.items() if row['id']!=name}
        self.audit.append({'kind':'operator_approved','actor':actor['id'],'target':name,'wall_s':self.clock()})
        return {'status':'approved','id':name,'role':'operator','reauthentication_required':True}

    @locked
    def request_operator(self,actor):
        name=actor['id']
        if name in self.bootstrap: raise ValueError('bootstrap_account_protected')
        if self.accounts[name]['role']=='operator': return {'status':'already_operator','id':name}
        old=self.accounts[name].get('operator_requested',False)
        self.accounts[name]['operator_requested']=True
        try: self.save()
        except OSError:
            self.accounts[name]['operator_requested']=old; raise
        for session in self.sessions.values():
            if session['id']==name: session['operator_requested']=True
        return {'status':'requested','id':name,'operator_requested':True}
    @locked
    def login(self, username,password, remote):
        self.rate_limit(remote,'login',10); now=self.clock(); username=self.normalize(username)
        account=self.accounts.get(username)
        if not account: raise ValueError('invalid_credentials')
        digest=hashlib.scrypt(password.encode(),salt=account['salt'],n=16384,r=8,p=1)
        if not hmac.compare_digest(digest,account['hash']): raise ValueError('invalid_credentials')
        token=secrets.token_urlsafe(32)
        self.sessions[hashlib.sha256(token.encode()).hexdigest()]={'id':username,'role':account['role'],
             'can_takeover':account['can_takeover'],'bootstrap':username in self.bootstrap,
             'operator_requested':account.get('operator_requested',False),'expires_wall_s':now+3600}
        return {'token':token,**self.sessions[hashlib.sha256(token.encode()).hexdigest()]}
    @locked
    def identity(self,token):
        digest=hashlib.sha256(token.encode()).hexdigest()
        row=self.sessions.get(digest)
        if not row or row['expires_wall_s']<=self.clock(): raise ValueError('session_expired')
        return dict(row)

    def command_actor(self,token):
        return {**self.identity(token),'_auth_digest':hashlib.sha256(token.encode()).hexdigest()}

    @locked
    def validate_actor(self,actor):
        row=self.sessions.get(actor.get('_auth_digest'))
        if not row or row['expires_wall_s']<=self.clock() or row['id']!=actor['id']:
            raise ValueError('session_expired_or_revoked')
    @locked
    def revoke(self,token): self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(),None)

    @locked
    def renew(self,token):
        actor=self.identity(token)
        self.revoke(token)
        fresh=secrets.token_urlsafe(32)
        actor['expires_wall_s']=self.clock()+3600
        self.sessions[hashlib.sha256(fresh.encode()).hexdigest()]=actor
        return {'token':fresh,**actor}
