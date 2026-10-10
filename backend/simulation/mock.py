"""No SUMO or UI required; same FastAPI routes and v2 schemas as the real host."""
from concurrent.futures import Future
from copy import deepcopy
from .coordination import Coordinator

class MockEngine:
    def __init__(self):
        self.coordinator=Coordinator(); self.settings={'location':'lig','mode':'experiment'}
        self.value={'ready':True,'error':None,'run_id':'run.fixture','sim_time_s':0,'paused':True,
                    'vehicles':[],'signals':[],'scenario':'fixture','metrics':{},'source':'DETERMINISTIC FIXTURE','ended':False}
    def start(self): pass
    def stop(self): pass
    def snapshot(self): return deepcopy(self.value)
    def state(self): return {'api_version':'2.0','run':self.snapshot(),'scenario':self.settings,**self.coordinator.view()}
    def export(self): return {'manifest':{'complete':False,'source':'fixture','baseline':None},'frames':[self.snapshot()],'events':[]}
    def command(self,c):
        future=Future()
        try:
            if c['action']=='lease': result=self.coordinator.acquire(c['actor'],c['lease_action'],c.get('takeover',False))
            else: result=self.coordinator.execute(c['actor'],c['command'],self.value['run_id'],self.apply)
            future.set_result(result)
        except Exception as exc: future.set_exception(exc)
        return future
    def apply(self,p):
        if p['action'] not in ('pause','resume'): raise ValueError('fixture_supports_pause_resume_only')
        self.value['paused']=p['action']=='pause'; return self.snapshot()
