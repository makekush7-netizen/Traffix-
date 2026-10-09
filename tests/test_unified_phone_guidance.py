"""Real SUMO, two authenticated in-process phone clients; not physical devices."""
import asyncio
from copy import deepcopy
import pytest
from backend.harness.demo_engine import load_demo_config
from backend.harness.engine import WORLD
from backend.simulation.phone import UnifiedMobileBridge
from backend.simulation.engine import UnifiedEngine
from scripts.run_unified import prepare_environment


def test_two_authenticated_phone_observations_accept_worker_route(monkeypatch):
    prepare_environment()
    import backend.simulation.engine as module
    world=deepcopy(WORLD); world['routes']=[load_demo_config()['route_a']]
    monkeypatch.setattr(module,'WORLD',world)
    engine=UnifiedEngine(); engine.settings.update(demand_per_hour=3600,duration_s=10,drain_s=180)
    engine.start()
    try:
        async def exercise():
            actor={'id':'test-operator','role':'operator'}
            def command(payload):
                engine.command({'action':'lease','actor':actor,'lease_action':'acquire'}).result(5)
                return engine.command({'action':'v2','actor':actor,'command':{'api_version':'2.0','command_id':str(engine.coordinator.revision),'run_id':engine.run_id,'expected_revision':engine.coordinator.revision,'payload':payload}}).result(5)
            edge=world['routes'][0][0]
            event={'kind':'rain','edge_id':edge,'start_s':.25,'duration_s':120,'severity':.95}
            command({'action':'event_preview','event':event})
            command({'action':'event_apply','event':event})
            command({'action':'guidance','enabled':True})
            while len(engine.snapshot()['vehicles'])<2: engine.command({'action':'step'}).result(5)
            bridge=UnifiedMobileBridge(engine)
            claims=[]; sessions=[]; seq=[0,0]
            for vehicle in engine.snapshot()['vehicles'][:2]:
                claim=bridge.sessions.claim(bridge.sessions.issue(vehicle['id'])); claims.append(claim)
                session=bridge.sessions.authenticate({'sender_id':claim['session_id'],'run_id':claim['run_id'],'payload':{'token':claim['token']}})
                session.connected=True; sessions.append(session)
            def message(i,kind,payload,stamp=None):
                seq[i]+=1
                row={'v':1,'type':kind,'msg_id':f'msg.phone.{i}.{seq[i]}','run_id':engine.run_id,'sender_id':claims[i]['session_id'],'seq':seq[i],'sim_time_s':stamp,'payload':payload}
                from backend.app import VALIDATOR
                VALIDATOR.validate(row)
                return row
            for i,session in enumerate(sessions):
                assert (await bridge.dispatch(session,message(i,'probe.toggle',{'enabled':True})))[1]=='sharing_on'
            for tick in range(9):
                for i,session in enumerate(sessions):
                    frame=bridge.frame(session); payload=frame['payload']
                    assert payload['state']=='active'
                    sample={'frame_id':payload['frame_id'],'vehicle_id':session.vehicle_id,'pose':payload['pose']}
                    assert (await bridge.dispatch(session,message(i,'probe.sample',sample,frame['sim_time_s'])))[1]=='sample_accepted'
                if bridge.offers: break
                for _ in range(20): engine.command({'action':'step'}).result(5)
            assert bridge.accepted>=14
            assert bridge.offers
            offer=next(iter(bridge.offers.values()))
            i=next(i for i,s in enumerate(sessions) if s.vehicle_id==offer['vehicle_id'])
            original=engine.command
            def withdraw_before_worker(c):
                if c['action']=='phone_accept': sessions[i].reporting=False
                return original(c)
            engine.command=withdraw_before_worker
            with pytest.raises(ValueError,match='phone_evidence_or_consent_withdrawn'):
                await bridge.dispatch(sessions[i],message(i,'driver.decision',{'advisory_id':offer['advisory_id'],'choice':'accept'}))
            assert not any(e['kind']=='driver_route_applied' for e in engine.export()['events'])
            engine.command=original; sessions[i].reporting=True
            result=await bridge.dispatch(sessions[i],message(i,'driver.decision',{'advisory_id':offer['advisory_id'],'choice':'accept'}))
            assert result==('applied','route_applied')
            assert any(e['kind']=='driver_route_applied' and e['vehicle_id']==sessions[i].vehicle_id for e in engine.export()['events'])
            assert bridge.offers[offer['advisory_id']]['status']=='applied'
            assert engine.export()['manifest']['scenario_mutated']
            await bridge.dispatch(sessions[i],message(i,'probe.toggle',{'enabled':False}))
            assert not sessions[i].reporting
        asyncio.run(exercise())
    finally: engine.stop()
