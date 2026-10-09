import json
import pytest

from backend.harness.response_lab import extension_plan


def row(**changes):
    return dict(state='Grr',elapsed_s=12,remaining_s=8,queue=4,opposing_queue=1,
                downstream_occupancy=.1,already_extended=False,**changes)


def test_response_plan_extends_only_bounded_observed_green():
    assert extension_plan(row()) == 13
    for changes in ({'state':'yrr'},{'state':'rrr'},{'elapsed_s':5},
                    {'downstream_occupancy':None},{'downstream_occupancy':.8},
                    {'already_extended':True},{'queue':0},{'opposing_queue':9},
                    {'elapsed_s':38,'remaining_s':2}):
        data=row();data.update(changes)
        with pytest.raises(ValueError): extension_plan(data)


def test_response_lab_worker_validates_and_applies_then_finishes():
    from backend.harness.response_lab import ResponseEngine
    engine=ResponseEngine();engine.start()
    try:
        state=engine.snapshot()
        assert state['metrics']['scheduled']==72
        assert state['response']['source']=='SIMULATED FULL-LANE SENSORS'
        assert len(state['response']['signals'])==6
        applied=False
        while not engine.snapshot()['ended']:
            state=engine.snapshot()
            for signal in state['response']['signals']:
                if signal['recommended'] and not applied:
                    command=dict(action='response_extend',run_id=state['run_id'],signal_id=signal['id'],phase_key=signal['phase_key'])
                    with pytest.raises(ValueError):engine.command({**command,'run_id':'wrong'}).result(5)
                    with pytest.raises(ValueError):engine.command({**command,'phase_key':'stale'}).result(5)
                    result=engine.command(command).result(5)
                    changed=next(s for s in result['response']['signals'] if s['id']==signal['id'])
                    assert changed['state']==signal['state']
                    assert changed['remaining_s']>signal['remaining_s']
                    with pytest.raises(ValueError): engine.command(command).result(5)
                    applied=True
            engine.command({'action':'step'}).result(5)
        final=engine.snapshot()
        assert applied
        assert final['metrics']['collisions']==final['metrics']['teleports']==0
        assert final['metrics']['arrived']==72
        assert json.loads((engine.run_dir/'manifest.json').read_text())['complete']
    finally: engine.stop()


def test_response_api_requires_operator_and_same_origin():
    from fastapi.testclient import TestClient
    from backend.harness.response_lab import create_response_app
    with TestClient(create_response_app()) as client:
        assert client.get('/api/response').status_code==403
        headers={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        state=client.get('/api/response',headers=headers).json()
        signal=state['response']['signals'][0]
        body=dict(run_id=state['run_id'],signal_id=signal['id'],phase_key=signal['phase_key'])
        assert client.post('/api/response/extend',json=body).status_code==403
        assert client.post('/api/response/extend',headers={**headers,'Origin':'http://other.example'},json=body).status_code==403
        assert client.post('/api/response/extend',headers=headers,json=body).status_code==422
        assert not client.get('/api/response',headers=headers).json()['response']['audit']


def test_smart_mode_requires_authenticated_current_run_and_resets_off():
    from fastapi.testclient import TestClient
    from backend.harness.response_lab import create_response_app
    with TestClient(create_response_app()) as client:
        headers={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        state=client.get('/api/response',headers=headers).json()
        body={'run_id':state['run_id'],'enabled':True}
        assert client.post('/api/response/smart',json=body).status_code==403
        assert client.post('/api/response/smart',headers={**headers,'Origin':'http://other.example'},json=body).status_code==403
        assert client.post('/api/response/smart',headers=headers,json={**body,'run_id':'old'}).status_code==422
        result=client.post('/api/response/smart',headers=headers,json=body)
        assert result.status_code==200
        assert result.json()['response']['smart_enabled'] is True
        assert client.post('/api/control',headers=headers,json={'action':'reset','scenario':'rain','seed':42}).status_code==200
        assert client.get('/api/response',headers=headers).json()['response']['smart_enabled'] is False


def test_smart_controller_acts_from_lane_evidence_on_worker():
    from backend.harness.response_lab import ResponseEngine
    engine=ResponseEngine();engine.start()
    try:
        state=engine.snapshot()
        assert state['signals'] and not state['response']['smart_enabled']
        engine.command({'action':'response_smart','run_id':state['run_id'],'enabled':True}).result(5)
        for _ in range(4000):
            state=engine.command({'action':'step'}).result(5)
            if state['response']['audit']:break
        assert state['response']['audit']
        event=state['response']['audit'][-1]
        assert event['controller']=='queue_responsive'
        assert 0<event['remaining_s']-event['previous_remaining_s']<=5
        assert state['metrics']['collisions']==state['metrics']['teleports']==0
        engine.command({'action':'response_smart','run_id':state['run_id'],'enabled':False}).result(5)
        count=len(engine.snapshot()['response']['audit'])
        for _ in range(20):engine.command({'action':'step'}).result(5)
        assert len(engine.snapshot()['response']['audit'])==count
    finally:engine.stop()
