"""V2 commands are checked and applied on the simulation owner thread."""
from collections import OrderedDict, deque
from copy import deepcopy
import hashlib
import json
import time


class Conflict(ValueError):
    pass


class Coordinator:
    def __init__(self, clock=time.time):
        self.clock=clock
        self.revision=0
        self.lease=None
        self.receipts=OrderedDict()
        self.audit=deque(maxlen=10000)

    def view(self):
        lease=self.lease if self.lease and self.lease['expires_wall_s']>self.clock() else None
        return {'revision':self.revision,'lease':deepcopy(lease),'audit':list(self.audit)[-100:]}

    def acquire(self, actor, action='acquire', takeover=False):
        if actor['role']!='operator': raise Conflict('operator_required')
        lease=self.view()['lease']
        if action not in ('acquire','renew','release'): raise Conflict('invalid_lease_action')
        if lease and lease['holder']!=actor['id'] and not (takeover and actor.get('can_takeover')):
            raise Conflict('lease_held')
        if action=='renew' and not lease: raise Conflict('lease_expired')
        self.lease=None if action=='release' else {'holder':actor['id'],'expires_wall_s':self.clock()+30}
        self.audit.append({'actor':actor['id'],'kind':'lease_'+action,'takeover':takeover,'wall_s':self.clock()})
        return self.view()

    def execute(self, actor, command, run_id, execute):
        if actor['role']!='operator': raise Conflict('operator_required')
        cid=command['command_id']; key=(actor['id'],cid)
        digest=hashlib.sha256(json.dumps(command,sort_keys=True).encode()).hexdigest()
        if key in self.receipts:
            prior=self.receipts[key]
            if prior[0]!=digest: raise Conflict('command_id_reused')
            return deepcopy(prior[1])
        if command['api_version']!='2.0': raise Conflict('unsupported_version')
        if command['run_id']!=run_id: raise Conflict('wrong_run')
        if command['expected_revision']!=self.revision: raise Conflict('revision_conflict')
        lease=self.view()['lease']
        if not lease or lease['holder']!=actor['id']: raise Conflict('lease_required')
        try: state=execute(command['payload'])
        except Exception as exc:
            self.audit.append({'actor':actor['id'],'command_id':cid,'kind':'rejected','reason':str(exc),'wall_s':self.clock()})
            raise
        self.revision+=1
        receipt={'api_version':'2.0','status':'applied','command_id':cid,'revision':self.revision,
                 'reason_code':'worker_applied','acknowledged_wall_s':self.clock(),
                 'acknowledged_sim_s':state.get('sim_time_s'),'state':state}
        self.receipts[key]=(digest,deepcopy(receipt))
        if len(self.receipts)>4096: self.receipts.popitem(last=False)
        self.audit.append({'actor':actor['id'],'command_id':cid,'kind':command['payload']['action'],
                           'revision':self.revision,'status':'applied','wall_s':self.clock()})
        return receipt
