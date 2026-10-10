"""Additive driver API authentication and route restriction acceptance."""
from copy import deepcopy
from fastapi.testclient import TestClient
from backend.simulation.app import create_app
from backend.harness.engine import WORLD


class DriverEngine:
    def __init__(self):
        edge=WORLD['routes'][0][0]
        self.row={'ready':True,'error':None,'run_id':'run.driver','sim_time_s':1,
                  'paused':True,'ended':False,'vehicles':[{'id':'car.0','type':'car',
                  'route_id':'route.0','route_path':WORLD['routes'][0]}],
                  'events':[{'event_id':'event.1','edge_id':edge,'kind':'blockage',
                  'effect':'simulated edge speed restriction; no physical obstacle',
                  'start_s':1,'end_s':61,'severity':.5,'status':'active'},
                  {'event_id':'event.other','edge_id':'not.on.route','kind':'rain','status':'active'}]}
    def start(self): pass
    def stop(self): pass
    def snapshot(self): return deepcopy(self.row)


def claim(client):
    bridge=client.app.state.mobile
    return client.post('/api/v2/phones/claim',json={'join_code':bridge.sessions.issue('car.0')}).json()


def test_public_discovery_and_driver_scoped_map_state():
    engine=DriverEngine()
    with TestClient(create_app(engine,{})) as client:
        capabilities=client.get('/api/v2/capabilities').json()
        assert capabilities['phone_protocol_version']==1
        assert capabilities['capabilities']['driver_world']
        credentials=claim(client)
        assert set(credentials)=={'run_id','session_id','vehicle_id','token'}
        params={k:credentials[k] for k in ('session_id','run_id')}
        headers={'Authorization':'Bearer '+credentials['token']}
        assert client.get('/api/v2/phones/world',params=params).status_code==401
        assert client.get('/api/v2/world',headers=headers).status_code==401
        world=client.get('/api/v2/phones/world',params=params,headers=headers).json()
        assert world['roads']==WORLD['roads'] and 'vehicles' not in world
        reply=client.get('/api/v2/phones/state',params=params,headers=headers).json()
        assert reply['route_id']=='route.0' and reply['route_path']==WORLD['routes'][0]
        assert reply['vehicle_type']=='car' and reply['role']=='driver'
        assert reply['paused'] and not reply['ended'] and reply['lifecycle']=='active'
        assert [e['event_id'] for e in reply['alerts']]==['event.1']
        assert [e['event_id'] for e in reply['route_events']]==['event.1']
        engine.row['events'][0]['status']='ended'
        engine.row['vehicles']=[];engine.row['arrived_vehicle_ids']=['car.0'];engine.row['ended']=True
        final=client.get('/api/v2/phones/state',params=params,headers=headers).json()
        assert final['lifecycle']=='arrived' and final['ended'] and final['alerts']==[]
        assert final['route_path']==WORLD['routes'][0]
        for bad in ({**params,'run_id':'run.other'},{**params,'session_id':'session.other'}):
            assert client.get('/api/v2/phones/world',params=bad,headers=headers).status_code==401
        assert client.get('/api/v2/phones/world',params=params,headers={**headers,'Origin':'https://evil.example'}).status_code==403
        engine.row['run_id']='run.reset'
        assert client.get('/api/v2/phones/state',params=params,headers=headers).status_code==401


def test_real_sumo_admin_restriction_reaches_only_bound_driver_and_ends():
    from backend.simulation.engine import UnifiedEngine
    from scripts.run_unified import prepare_environment
    prepare_environment()
    engine=UnifiedEngine(); engine.settings.update(demand_per_hour=3600,duration_s=10,drain_s=180)
    with TestClient(create_app(engine,{'operator':{'role':'operator','password':'test'}})) as client:
        token=client.post('/api/v2/auth/login',json={'username':'operator','password':'test'}).json()['token']
        headers={'Authorization':'Bearer '+token}
        assert client.post('/api/v2/lease',json={},headers=headers).status_code==200
        def command(payload):
            body={'api_version':'2.0','command_id':'driver.test.'+str(engine.coordinator.revision),
                  'run_id':engine.run_id,'expected_revision':engine.coordinator.revision,'payload':payload}
            response=client.post('/api/v2/commands',json=body,headers=headers)
            assert response.status_code==200,response.text
            assert response.json()['status']=='applied'
            return response.json()['state']
        for _ in range(80):
            if engine.snapshot()['vehicles']: break
            command({'action':'step'})
        vehicle=engine.snapshot()['vehicles'][0]
        assert vehicle['route_path'] and vehicle['route_id']
        invite=client.post('/api/v2/phones/invites',json={'vehicle_id':vehicle['id']},headers=headers).json()
        credentials=client.post('/api/v2/phones/claim',json={'join_code':invite['join_code']}).json()
        params={k:credentials[k] for k in ('session_id','run_id')}
        driver={'Authorization':'Bearer '+credentials['token']}
        event={'kind':'blockage','edge_id':vehicle['route_path'][0],
               'start_s':engine.snapshot()['sim_time_s'],'duration_s':60,'severity':.6}
        preview=command({'action':'event_preview','event':event})['event_preview']
        assert client.get('/api/v2/phones/state',params=params,headers=driver).json()['alerts']==[]
        command({'action':'event_apply','event':event})
        reply=client.get('/api/v2/phones/state',params=params,headers=driver).json()
        assert reply['alerts'][0]['event_id']==preview['event_id']
        assert 'speed restriction' in reply['alerts'][0]['effect']
        assert reply['route_path']==vehicle['route_path']
        assert client.get('/api/v2/observations',headers=headers).json()['accepted_uplinks']==0
        from backend.app import VALIDATOR
        with client.websocket_connect('/api/v2/phones/ws') as ws:
            hello={'v':1,'type':'session.hello','msg_id':'msg.driver.1','run_id':credentials['run_id'],
                   'sender_id':credentials['session_id'],'seq':1,'sim_time_s':None,
                   'payload':{'token':credentials['token'],'last_server_seq':0}}
            ws.send_json(hello)
            ready=ws.receive_json(); frame=ws.receive_json()
            VALIDATOR.validate(ready); VALIDATOR.validate(frame)
            assert frame['type']=='vehicle.frame' and 'route_path' not in frame['payload']
        command({'action':'event_end','event_id':preview['event_id']})
        reply=client.get('/api/v2/phones/state',params=params,headers=driver).json()
        assert reply['alerts']==[] and reply['route_events'][0]['status']=='ended'
        command({'action':'reset','settings':{'demand_per_hour':0}})
        assert client.get('/api/v2/phones/world',params=params,headers=driver).status_code==401
