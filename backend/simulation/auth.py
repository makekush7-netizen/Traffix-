"""Explicit accounts; no localhost bootstrap or default remote credentials."""
from collections import defaultdict, deque
import hashlib
import hmac
import secrets
import time

class Auth:
    def __init__(self, accounts, clock=time.time):
        self.clock=clock; self.accounts={}; self.sessions={}; self.attempts=defaultdict(deque)
        for name, value in accounts.items():
            if value.get('role') not in ('operator','viewer'): raise ValueError('invalid_admin_role')
            if not isinstance(value.get('password'),str) or not value['password']: raise ValueError('empty_password')
            salt=secrets.token_bytes(16)
            self.accounts[name]={'role':value['role'],'can_takeover':value.get('can_takeover',False),
                'salt':salt,'hash':hashlib.scrypt(value['password'].encode(),salt=salt,n=16384,r=8,p=1)}
    def login(self, username,password, remote):
        attempts=self.attempts[remote]; now=self.clock()
        while attempts and attempts[0]<now-60: attempts.popleft()
        if len(attempts)>=10: raise ValueError('login_rate_limited')
        attempts.append(now); account=self.accounts.get(username)
        if not account: raise ValueError('invalid_credentials')
        digest=hashlib.scrypt(password.encode(),salt=account['salt'],n=16384,r=8,p=1)
        if not hmac.compare_digest(digest,account['hash']): raise ValueError('invalid_credentials')
        token=secrets.token_urlsafe(32)
        self.sessions[hashlib.sha256(token.encode()).hexdigest()]={'id':username,'role':account['role'],
             'can_takeover':account['can_takeover'],'expires_wall_s':now+3600}
        return {'token':token,**self.sessions[hashlib.sha256(token.encode()).hexdigest()]}
    def identity(self,token):
        digest=hashlib.sha256(token.encode()).hexdigest()
        row=self.sessions.get(digest)
        if not row or row['expires_wall_s']<=self.clock(): raise ValueError('session_expired')
        return dict(row)

    def command_actor(self,token):
        return {**self.identity(token),'_auth_digest':hashlib.sha256(token.encode()).hexdigest()}

    def validate_actor(self,actor):
        row=self.sessions.get(actor.get('_auth_digest'))
        if not row or row['expires_wall_s']<=self.clock() or row['id']!=actor['id']:
            raise ValueError('session_expired_or_revoked')
    def revoke(self,token): self.sessions.pop(hashlib.sha256(token.encode()).hexdigest(),None)

    def renew(self,token):
        actor=self.identity(token)
        self.revoke(token)
        fresh=secrets.token_urlsafe(32)
        actor['expires_wall_s']=self.clock()+3600
        self.sessions[hashlib.sha256(fresh.encode()).hexdigest()]=actor
        return {'token':fresh,**actor}
