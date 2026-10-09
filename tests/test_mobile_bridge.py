from copy import deepcopy
import pytest

from fastapi.testclient import TestClient
from backend.harness.app import create_app
from backend.app import VALIDATOR
from backend.harness.mobile import MobileBridge
from backend.harness.engine import WORLD


def packet(claim, kind, payload, seq, stamp=None):
    return dict(v=1, type=kind, msg_id=f'msg.phone.{seq}', run_id=claim['run_id'],
                sender_id=claim['session_id'], seq=seq, sim_time_s=stamp, payload=payload)


def receive(ws, kind):
    for _ in range(30):
        message = ws.receive_json()
        VALIDATOR.validate(message)
        if message['type'] == kind:
            return message
    raise AssertionError(f'Missing {kind}')


def test_two_real_sumo_bindings_and_permission_withdrawal():
    with TestClient(create_app()) as client:
        assert client.get('/driver').status_code == 200
        assert client.post('/api/control', json={'action':'step'}).status_code == 403
        auth = {'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        vehicles = client.get('/api/operator/state', headers=auth).json()['available_vehicles']
        claims = []
        for vehicle in vehicles[:2]:
            code = client.post('/api/operator/join', headers=auth, json={'vehicle_id':vehicle['id']}).json()['join_code']
            claim = client.post('/api/claim', json={'join_code':code}).json()
            assert client.post('/api/claim', json={'join_code':code}).status_code == 409
            claims.append(claim)
        assert claims[0]['vehicle_id'] != claims[1]['vehicle_id']
        with client.websocket_connect('/ws') as first, client.websocket_connect('/ws') as second:
            frames = []
            for ws, claim in zip((first,second),claims):
                ws.send_json(packet(claim,'session.hello',{'token':claim['token'],'last_server_seq':0},0))
                receive(ws,'session.ready')
                frames.append(receive(ws,'vehicle.frame'))
            assert client.get('/api/operator/state',headers=auth).json()['accepted_uplinks'] == 0
            first.send_json(packet(claims[0],'probe.toggle',{'enabled':True},1))
            assert receive(first,'ack')['payload']['status'] == 'applied'
            sample = deepcopy(frames[0]['payload']); sample.pop('state')
            first.send_json(packet(claims[0],'probe.sample',sample,2,frames[0]['sim_time_s']))
            assert receive(first,'ack')['payload']['status'] == 'applied'
            state = client.get('/api/operator/state',headers=auth).json()
            assert state['accepted_uplinks'] == 1
            assert any(o['coverage']=='fresh' and o['sources']==['phone'] for o in state['observations'])
            first.send_json(packet(claims[0],'probe.sample',sample,3,frames[0]['sim_time_s']))
            assert receive(first,'ack')['payload']['status'] == 'duplicate'
            first.send_json(packet(claims[0],'probe.toggle',{'enabled':False},4))
            receive(first,'ack')
            assert all(o['coverage']=='unknown' for o in client.get('/api/operator/state',headers=auth).json()['observations'])
            assert client.post('/api/control',headers=auth,json={'action':'step'}).status_code == 200


def test_altered_cross_vehicle_and_driver_control_are_rejected():
    with TestClient(create_app()) as client:
        auth={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        assert client.get('/api/operator/bootstrap',headers={'Host':'attacker.invalid'}).status_code==400
        vehicle=client.get('/api/operator/state',headers=auth).json()['available_vehicles'][0]
        code=client.post('/api/operator/join',headers=auth,json={'vehicle_id':vehicle['id']}).json()['join_code']
        claim=client.post('/api/claim',json={'join_code':code}).json()
        with client.websocket_connect('/ws') as ws:
            ws.send_json(packet(claim,'session.hello',{'token':claim['token'],'last_server_seq':0},0))
            receive(ws,'session.ready'); frame=receive(ws,'vehicle.frame')
            ws.send_json(packet(claim,'probe.toggle',{'enabled':True},1)); receive(ws,'ack')
            sample=deepcopy(frame['payload']); sample.pop('state'); sample['pose']['speed_mps']+=1
            ws.send_json(packet(claim,'probe.sample',sample,2,frame['sim_time_s']))
            assert receive(ws,'ack')['payload']['reason']=='altered_frame'
            sample['vehicle_id']='car.not.bound'
            ws.send_json(packet(claim,'probe.sample',sample,3,frame['sim_time_s']))
            assert receive(ws,'ack')['payload']['reason']=='wrong_vehicle'
            ws.send_json(packet(claim,'operator.command',{'command':'resume','proposal_id':None,'rate':None},4))
            assert receive(ws,'ack')['payload']['status']=='rejected'
            assert client.get('/api/operator/state',headers=auth).json()['accepted_uplinks']==0


class SnapshotEngine:
    """Controlled simulation time without a second TraCI writer."""
    def __init__(self):
        self.state=dict(ready=True,run_id='run.test',sim_time_s=100,paused=True,incident_active=False,
                        vehicles=[dict(id='car.1',edge_id=WORLD['roads'][0]['id'],type='car',x=1,y=2,speed=3)])
    def snapshot(self): return deepcopy(self.state)


def bound_bridge():
    engine=SnapshotEngine(); bridge=MobileBridge(engine)
    claim=bridge.sessions.claim(bridge.sessions.issue('car.1'))
    session=bridge.sessions.sessions[claim['session_id']]
    session.connected=True; session.last_seen=__import__('time').monotonic(); session.reporting=True
    frame=bridge.frame(session)
    sample=deepcopy(frame['payload']); sample.pop('state')
    return engine,bridge,claim,session,packet(claim,'probe.sample',sample,1,frame['sim_time_s'])


@pytest.mark.parametrize('stamp,reason',[(99,'future_frame'),(116,'stale_frame')])
def test_live_bridge_rejects_future_and_stale(stamp,reason):
    engine,bridge,claim,session,message=bound_bridge(); engine.state['sim_time_s']=stamp
    with pytest.raises(ValueError,match=reason): bridge.apply(session,message)
    assert bridge.accepted==0


def test_run_reset_invalidates_claims_and_prior_observations():
    engine,bridge,claim,session,message=bound_bridge()
    bridge.apply(session,message); old=bridge.sessions
    assert bridge.status()['accepted_uplinks']==1
    engine.state['run_id']='run.next'; bridge.sync()
    assert bridge.sessions is not old
    with pytest.raises(ValueError,match='unauthenticated'):
        bridge.sessions.authenticate(packet(claim,'session.hello',{'token':claim['token'],'last_server_seq':0},0))
    assert bridge.status()['accepted_uplinks']==0
    assert bridge.status()['observations']==[]


def test_heartbeat_withdraws_observations_during_pause_and_duplicate_id_is_ignored():
    engine,bridge,claim,session,message=bound_bridge()
    bridge.apply(session,message)
    duplicate=packet(claim,'probe.toggle',{'enabled':False},2); duplicate['msg_id']=message['msg_id']
    assert bridge.apply(session,duplicate)[0]=='duplicate'
    assert session.reporting
    session.last_seen-=7
    assert bridge.status()['observations']==[]
    assert not session.connected and not session.reporting
    assert engine.state['sim_time_s']==100


def test_advisory_binding_expiry_and_receipt_never_change_route():
    engine,bridge,claim,session,message=bound_bridge()
    advisory=dict(advisory_id='advisory.1',vehicle_id='car.1',kind='incident',route_id=None,message='Unverified operator note',expires_sim_s=110)
    bridge.guidance['advisory.1']=advisory
    decision=packet(claim,'driver.decision',{'advisory_id':'advisory.1','choice':'accept'},1)
    assert bridge.apply(session,decision)==('applied','advisory_acknowledged_no_route_change')
    assert engine.state['sim_time_s']==100
    bridge.guidance['advisory.2']={**advisory,'advisory_id':'advisory.2','expires_sim_s':100}
    with pytest.raises(ValueError,match='expired_advisory'):
        bridge.apply(session,packet(claim,'driver.decision',{'advisory_id':'advisory.2','choice':'accept'},2))


def test_remote_bootstrap_and_cross_origin_claim_are_blocked():
    with TestClient(create_app(),client=('192.168.1.15',1234)) as client:
        assert client.get('/api/operator/bootstrap').status_code==403
        assert client.post('/api/claim',headers={'Origin':'http://attacker.invalid'},json={'join_code':'fake'}).status_code==403


def test_websocket_reconnect_restores_binding_without_sharing_and_export_has_no_tokens():
    with TestClient(create_app()) as client:
        auth={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        vehicle=client.get('/api/operator/state',headers=auth).json()['available_vehicles'][0]
        code=client.post('/api/operator/join',headers=auth,json={'vehicle_id':vehicle['id']}).json()['join_code']
        claim=client.post('/api/claim',json={'join_code':code}).json()
        with client.websocket_connect('/ws') as ws:
            ws.send_json(packet(claim,'session.hello',{'token':claim['token'],'last_server_seq':0},0))
            receive(ws,'session.ready'); receive(ws,'vehicle.frame')
            ws.send_json(packet(claim,'probe.toggle',{'enabled':True},1)); receive(ws,'ack')
        with client.websocket_connect('/ws') as ws:
            ws.send_json(packet(claim,'session.hello',{'token':claim['token'],'last_server_seq':0},2))
            assert receive(ws,'session.ready')['payload']['vehicle_id']==claim['vehicle_id']
            receive(ws,'vehicle.frame')
            state=client.get('/api/operator/state',headers=auth).json()
            assert len(state['sessions'])==1 and state['sessions'][0]['reporting'] is False
            advisory=client.post('/api/operator/advisory',headers=auth,json={'session_id':claim['session_id'],'message':'Test unverified note'}).json()
            assert receive(ws,'guidance')['payload']==advisory
            ws.send_json(packet(claim,'driver.decision',{'advisory_id':advisory['advisory_id'],'choice':'accept'},3))
            assert receive(ws,'ack')['payload']['reason']=='advisory_acknowledged_no_route_change'
            export=client.get('/api/operator/export',headers=auth)
            assert export.status_code==200 and export.json()['phone_bridge']['accepted_uplinks']==0
            assert claim['token'] not in export.text and code not in export.text
            assert client.get('/api/operator/export').status_code==403
