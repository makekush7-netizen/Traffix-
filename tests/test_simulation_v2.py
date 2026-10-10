from backend.simulation.coordination import Coordinator, Conflict
import pytest


def envelope(action='pause', command_id='c1', revision=0):
    return {'api_version':'2.0','command_id':command_id,'run_id':'run.1','expected_revision':revision,'payload':{'action':action}}


def test_serialized_revision_lease_idempotency_and_role():
    clock=[100.0]
    c=Coordinator(clock=lambda:clock[0])
    operator={'id':'alice','role':'operator'}
    viewer={'id':'bob','role':'viewer'}
    with pytest.raises(Conflict,match='operator_required'): c.acquire(viewer)
    c.acquire(operator)
    calls=[]
    execute=lambda payload: calls.append(payload) or {'sim_time_s':2}
    first=c.execute(operator,envelope(),'run.1',execute)
    assert first['revision']==1
    assert c.execute(operator,envelope(),'run.1',execute)==first
    assert len(calls)==1
    with pytest.raises(Conflict,match='revision_conflict'): c.execute(operator,envelope(command_id='c2'),'run.1',execute)
    with pytest.raises(Conflict,match='command_id_reused'): c.execute(operator,envelope('resume'),'run.1',execute)
    clock[0]+=31
    with pytest.raises(Conflict,match='lease_required'): c.execute(operator,envelope(command_id='c3',revision=1),'run.1',execute)


def test_wrong_run_and_failed_action_do_not_advance_revision():
    c=Coordinator(); actor={'id':'alice','role':'operator'}; c.acquire(actor)
    with pytest.raises(Conflict,match='wrong_run'): c.execute(actor,envelope(),'run.2',lambda p:None)
    def fail(p): raise ValueError('invalid')
    with pytest.raises(ValueError): c.execute(actor,envelope(),'run.1',fail)
    assert c.revision==0


def test_expired_actor_cannot_take_lease_or_replay_receipt():
    c=Coordinator(clock=lambda:100)
    expired={'id':'alice','role':'operator','expires_wall_s':99}
    with pytest.raises(Conflict,match='session_expired'): c.acquire(expired)


def test_reset_invalid_settings_does_not_change_active_scenario():
    from backend.simulation.engine import UnifiedEngine
    engine=UnifiedEngine()
    before=dict(engine.settings)
    with pytest.raises(ValueError):
        engine._apply_command({'action':'reset','settings':{'duration_s':float('nan')}})
    assert engine.settings==before


def test_missing_action_has_explicit_validation_error():
    from backend.simulation.engine import UnifiedEngine
    with pytest.raises(ValueError,match='invalid_action'):
        UnifiedEngine()._apply_command({})


def test_auth_expiry_rotation_and_role_validation():
    from backend.simulation.auth import Auth
    wall=[1]
    auth=Auth({'a':{'role':'operator','password':'local-only'}},clock=lambda:wall[0])
    token=auth.login('a','local-only','127.0.0.1')['token']
    fresh=auth.renew(token)['token']
    with pytest.raises(ValueError,match='session_expired'): auth.identity(token)
    assert auth.identity(fresh)['role']=='operator'
    wall[0]+=3601
    with pytest.raises(ValueError,match='session_expired'): auth.identity(fresh)
    with pytest.raises(ValueError,match='invalid_admin_role'): Auth({'a':{'role':'driver','password':'bad'}})

def test_http_auth_phone_claim_and_worker_conflict():
    from concurrent.futures import Future
    from copy import deepcopy
    from fastapi.testclient import TestClient
    from backend.simulation.app import create_app
    class Engine:
        def __init__(self):
            self.coordinator=Coordinator()
            self.row={'ready':True,'error':None,'run_id':'run.1','sim_time_s':0,'paused':True,'vehicles':[{'id':'car.0','type':'car'}],'scenario':'everyday'}
        def start(self): pass
        def stop(self): pass
        def snapshot(self): return deepcopy(self.row)
        def state(self): return {'run':self.snapshot(),**self.coordinator.view()}
        def export(self): return {'manifest':{'complete':False}}
        def command(self,c):
            f=Future()
            try:
                if c['action']=='lease': result=self.coordinator.acquire(c['actor'],c['lease_action'],c['takeover'])
                else: result=self.coordinator.execute(c['actor'],c['command'],'run.1',lambda p:self.snapshot())
                f.set_result(result)
            except Exception as exc: f.set_exception(exc)
            return f
    app=create_app(Engine(),{'alice':{'role':'operator','password':'test'},'bob':{'role':'viewer','password':'test'}})
    with TestClient(app) as client:
        assert client.get('/api/v2/state').status_code==401
        from starlette.websockets import WebSocketDisconnect
        with client.websocket_connect('/api/v2/stream') as ws:
            ws.send_json({'token':None})
            with pytest.raises(WebSocketDisconnect): ws.receive_json()
        op=client.post('/api/v2/auth/login',json={'username':'alice','password':'test'}).json()['token']
        view=client.post('/api/v2/auth/login',json={'username':'bob','password':'test'}).json()['token']
        headers={'Authorization':'Bearer '+op}
        assert client.get('/api/v2/state',headers=headers).status_code==200
        assert client.post('/api/v2/lease',json={},headers={'Authorization':'Bearer '+view}).status_code==409
        assert client.post('/api/v2/lease',json={},headers=headers).status_code==200
        assert client.post('/api/v2/commands',json=envelope(),headers=headers).json()['revision']==1
        assert client.post('/api/v2/commands',json=envelope(command_id='stale'),headers=headers).status_code==409
        assert client.get('/api/v2/phones/connection').status_code==401
        connection=client.get('/api/v2/phones/connection',headers=headers).json()
        assert connection['loopback_only'] is True
        assert client.get('/api/v2/phones/qr',headers=headers,params={'url':'https://evil.example'}).status_code==422
        assert client.post('/api/v2/phones/invites',headers=headers,json={'vehicle_id':'missing'}).status_code==409
        invite=client.post('/api/v2/phones/invites',headers=headers,json={'vehicle_id':'car.0'}).json()
        assert invite['vehicle_id']=='car.0'
        assert client.get('/api/v2/phones/qr',headers=headers,params={'url':'http://127.0.0.1:8005/operator/phone.html#code='+invite['join_code']}).headers['content-type']=='image/png'
        claim=client.post('/api/v2/phones/claim',json={'join_code':invite['join_code']})
        assert claim.status_code==200
        assert client.post('/api/v2/phones/claim',json={'join_code':invite['join_code']}).status_code==409
        assert client.get('/api/v2/observations',headers=headers).json()['accepted_uplinks']==0
        assert client.get('/api/v2/state',headers={**headers,'Origin':'https://evil.example'}).status_code==403
        import time
        sample={'source_type':'camera_measurement','source_id':'camera.1','run_id':'run.1','sim_time_s':0,
                'wall_time_s':time.time(),'confidence':.8,'coverage':['edge.lig.0'],
                'units':{'count':'vehicles'},'values':{'count':2}}
        body={'api_version':'2.0','observation':sample}
        reply=client.post('/api/v2/observations/ingest',headers=headers,json=body)
        assert reply.status_code==200 and not reply.json()['usable_for_control']
        health=client.get('/api/v2/observations/health',headers=headers).json()
        assert health['phone_observation_count']==0 and health['status']=='available'
        assert client.post('/api/v2/observations/ingest',headers=headers,json=body).status_code==422
        sample['source_type']='phone_sample'
        assert client.post('/api/v2/observations/ingest',headers=headers,json=body).json()['detail']=='phone_gateway_required'
        assert client.post('/api/v2/observations/ingest',headers={'Authorization':'Bearer '+view},json=body).status_code==403


def test_unified_zero_demand_reaches_complete_and_saves(tmp_path):
    from scripts.run_unified import prepare_environment
    prepare_environment()
    from backend.simulation.engine import UnifiedEngine
    engine=UnifiedEngine()
    engine.settings.update(demand_per_hour=0,duration_s=1,drain_s=2)
    engine.start()
    try:
        actor={'id':'headless','role':'operator'}
        engine.command({'action':'lease','actor':actor,'lease_action':'acquire'}).result(timeout=5)
        for i in range(3):
            command={'api_version':'2.0','command_id':f'step.{i}','run_id':engine.run_id,'expected_revision':i,'payload':{'action':'step'}}
            engine.command({'action':'v2','actor':actor,'command':command}).result(timeout=5)
        state=engine.snapshot()
        assert state['ended'] and state['result']['integrity']=='complete'
        assert state['metrics']['scheduled']==state['metrics']['arrived']==0
        assert len(engine.export()['frames'])>=2
        import json
        assert json.loads((engine.run_dir/'manifest.json').read_text())['complete']
        assert engine.export()['team_control']['revision']==3
    finally: engine.stop()

def test_saved_run_catalog_comparison_and_path_guard(tmp_path,monkeypatch):
    import json
    import backend.simulation.engine as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    base={'run_id':'lig.111111111111','network_sha256':'net','demand_sha256':'demand','seed':1,'settings':{'duration_s':10},'scenario_requested':'everyday','scenario_mutated':False,'integrity':'complete','execution_sha256':'code'}
    for suffix,change in [('111111111111',{}),('222222222222',{'policy':'bounded'}),('333333333333',{'demand_sha256':'different'}),('444444444444',{'scenario_mutated':True})]:
        path=tmp_path/'runs'/('lig.'+suffix); path.mkdir(parents=True)
        (path/'manifest.json').write_text(json.dumps({**base,**change,'run_id':path.name}))
    assert len(module.saved_runs())==4
    assert [r['run_id'] for r in module.comparable_runs(base)]==['lig.222222222222']
    assert module.comparable_runs({**base,'integrity':'incomplete'})==[]
    assert module.comparable_runs({**base,'execution_sha256':'new-controller'})==[]
    missing=dict(base); del missing['execution_sha256']
    assert module.comparable_runs(missing)==[]
    with pytest.raises(ValueError,match='invalid_run_id'): module.saved_run_path('../secret')
    with pytest.raises(FileNotFoundError): module.saved_run_path('lig.aaaaaaaaaaaa')

def test_queued_actor_revoked_before_worker_execution_and_rate_bounds():
    from backend.simulation.auth import Auth
    from backend.simulation.engine import UnifiedEngine
    auth=Auth({'a':{'role':'operator','password':'local'}})
    token=auth.login('a','local','127.0.0.1')['token']; actor=auth.command_actor(token)
    engine=UnifiedEngine(); engine._actor_validator=auth.validate_actor
    auth.revoke(token)
    with pytest.raises(ValueError,match='session_expired_or_revoked'):
        engine._execute({'action':'lease','actor':actor,'lease_action':'acquire'})
    for value in [float('nan'),True,.1,21]:
        with pytest.raises(ValueError,match='invalid_rate'): engine._apply_command({'action':'rate','value':value})
    engine._publish=lambda:None
    engine._apply_command({'action':'rate','value':.5})
    assert engine.rate==.5
