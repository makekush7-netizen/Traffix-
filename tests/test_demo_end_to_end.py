from copy import deepcopy
import asyncio
import pytest
from fastapi.testclient import TestClient
from backend.harness.app import create_demo_app
from backend.app import VALIDATOR


def message(claim,kind,payload,seq,stamp=None):
    return dict(v=1,type=kind,msg_id=f'msg.demo.{seq}',run_id=claim['run_id'],sender_id=claim['session_id'],
                seq=seq,sim_time_s=stamp,payload=payload)


def receive(ws,kind,stamp=0):
    # Preserve interleaved messages instead of dropping guidance while awaiting ack.
    if not hasattr(ws,'_demo_pending'): ws._demo_pending=[]
    for i,event in enumerate(ws._demo_pending):
        if event['type']==kind and (event['sim_time_s'] or 0)>=stamp: return ws._demo_pending.pop(i)
    for _ in range(100):
        event=ws.receive_json(); VALIDATOR.validate(event)
        if event['type']==kind and (event['sim_time_s'] or 0)>=stamp: return event
        if event['type']!=kind: ws._demo_pending.append(event)
    raise AssertionError('Missing '+kind)


def claim_vehicle(client,auth,vehicle):
    code=client.post('/api/operator/join',headers=auth,json={'vehicle_id':vehicle}).json()['join_code']
    return client.post('/api/claim',json={'join_code':code}).json()


def test_real_phone_evidence_offer_and_explicit_accept_change_only_bound_route():
    app=create_demo_app()
    with TestClient(app) as client:
        auth={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        assert client.get('/api/operator/state',headers=auth).json()['guidance_enabled'] is False
        claims=[claim_vehicle(client,auth,v) for v in ('veh.role.rider','veh.role.auto')]
        seq=[0,0]
        with client.websocket_connect('/ws') as first,client.websocket_connect('/ws') as second:
            sockets=(first,second)
            for i,ws in enumerate(sockets):
                ws.send_json(message(claims[i],'session.hello',{'token':claims[i]['token'],'last_server_seq':0},0))
                receive(ws,'session.ready'); frame=receive(ws,'vehicle.frame')
                seq[i]+=1; ws.send_json(message(claims[i],'probe.toggle',{'enabled':True},seq[i])); receive(ws,'ack')
                sample=deepcopy(frame['payload']); sample.pop('state')
                seq[i]+=1; ws.send_json(message(claims[i],'probe.sample',sample,seq[i],frame['sim_time_s'])); receive(ws,'ack')
            assert not client.get('/api/operator/state',headers=auth).json()['offers']
            assert client.post('/api/demo/guidance',headers=auth,json={'enabled':True}).status_code==200
            client.get('/api/operator/state',headers=auth)
            for _ in range(7):
                for _ in range(20): app.state.engine.command({'action':'step'}).result(5)
                stamp=app.state.engine.snapshot()['sim_time_s']
                for i,ws in enumerate(sockets):
                    seq[i]+=1; ws.send_json(message(claims[i],'heartbeat',{'visible':True},seq[i])); receive(ws,'ack')
                    frame=receive(ws,'vehicle.frame',stamp)
                    sample=deepcopy(frame['payload']); sample.pop('state')
                    seq[i]+=1; ws.send_json(message(claims[i],'probe.sample',sample,seq[i],frame['sim_time_s']))
                    assert receive(ws,'ack')['payload']['status']=='applied'
                state=client.get('/api/operator/state',headers=auth).json()
                if state['offers']: break
            assert state['offers'] and state['alert']['phones']==2
            offer=receive(first,'guidance')['payload']
            assert not app.state.engine.snapshot()['demo']['applied_vehicles']
            assert app.state.engine.snapshot()['demo']['routes']['veh.role.rider']=='route.demo.A'
            seq[1]+=1; second.send_json(message(claims[1],'driver.decision',{'advisory_id':offer['advisory_id'],'choice':'accept'},seq[1]))
            assert receive(second,'ack')['payload']['reason']=='wrong_vehicle'
            assert not app.state.engine.snapshot()['demo']['applied_vehicles']
            seq[0]+=1; first.send_json(message(claims[0],'driver.decision',{'advisory_id':offer['advisory_id'],'choice':'accept'},seq[0]))
            ack=receive(first,'ack')
            assert ack['payload']['status']=='applied' and ack['payload']['reason']=='route_applied'
            state=app.state.engine.snapshot()
            assert state['demo']['routes']['veh.role.rider']=='route.demo.B'
            assert state['demo']['routes']['veh.role.auto']=='route.demo.A'
            assert any(e['kind']=='driver_route_applied' for e in state['events'])
            assert client.get('/api/operator/state',headers=auth).json()['stage']==3
            own=client.get('/api/driver/state',params={'session_id':claims[0]['session_id'],'run_id':claims[0]['run_id']},
                           headers={'Authorization':'Bearer '+claims[0]['token']}).json()
            assert own['route_id']=='route.demo.B' and own['route_path']
            client.post('/api/demo/guidance',headers=auth,json={'enabled':False})
            assert not client.get('/api/operator/state',headers=auth).json()['guidance_enabled']
            while not app.state.engine.snapshot()['ended']:
                for _ in range(80):
                    if app.state.engine.snapshot()['ended']: break
                    app.state.engine.command({'action':'step'}).result(5)
                for i,ws in enumerate(sockets):
                    seq[i]+=1; ws.send_json(message(claims[i],'heartbeat',{'visible':True},seq[i])); receive(ws,'ack')
            final=app.state.engine.snapshot()
            assert final['metrics']['arrived']==12
            assert final['metrics']['collisions']==final['metrics']['teleports']==0
            assert client.get('/api/operator/state',headers=auth).json()['comparison']['available']


def test_worker_rejects_late_expired_unaccepted_and_wrong_vehicle_actions():
    from backend.harness.demo_engine import DemoEngine
    engine=DemoEngine(); engine.start()
    try:
        base=dict(action='demo_reroute',run_id=engine.run_id,vehicle_id='veh.role.rider',addressed_vehicle='veh.role.rider',
                  accepted=True,expires_sim_s=90,advisory_id='advisory.test')
        for change,reason in [({'accepted':False},'accept_required'),({'addressed_vehicle':'veh.role.auto'},'wrong_vehicle'),
                              ({'expires_sim_s':0},'expired_advisory')]:
            with pytest.raises(ValueError,match=reason): engine.command({**base,**change}).result(5)
        while engine.snapshot()['sim_time_s']<110: engine.command({'action':'step'}).result(5)
        with pytest.raises(ValueError,match='too_late|past_decision'):
            engine.command({**base,'expires_sim_s':200}).result(5)
        assert not engine.snapshot()['demo']['applied_vehicles']
    finally: engine.stop()
