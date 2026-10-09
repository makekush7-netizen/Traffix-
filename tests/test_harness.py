import time
import json

import pytest
from fastapi.testclient import TestClient

from backend.harness.app import create_app
from backend.harness.engine import HarnessEngine


def test_real_sumo_reset_step_and_seed_reproducibility():
    engine = HarnessEngine()
    canceled = engine.command({'action': 'step'})
    assert canceled.cancel()
    engine.start()
    try:
        first = engine.command({'action': 'reset', 'scenario': 'everyday', 'seed': 42}).result(30)
        assert first['source'] == 'SUMO simulation truth'
        assert first['paused']
        assert first['vehicles']
        frozen = first['sim_time_s']
        time.sleep(.3)
        assert engine.snapshot()['sim_time_s'] == frozen
        stepped = engine.command({'action': 'step'}).result(5)
        assert stepped['sim_time_s'] > frozen
        previous_dir = engine.run_dir
        second = engine.command({'action': 'reset', 'scenario': 'everyday', 'seed': 42}).result(30)
        saved = json.loads((previous_dir/'recording.json').read_text())
        assert saved['manifest']['run_id'] == first['run_id']
        assert saved['manifest']['complete'] is False
        assert first['run_id'] != second['run_id']
        assert first['vehicles'] == second['vehicles']
        assert first['metrics'] == second['metrics']
        with pytest.raises(ValueError):
            engine.command({'action': 'reset', 'scenario': 'made_up', 'seed': 42}).result(5)
        assert engine.snapshot()['run_id'] == second['run_id']
    finally:
        engine.stop()


def test_web_controls_and_export():
    with TestClient(create_app()) as client:
        auth={'Authorization':'Bearer '+client.get('/api/operator/bootstrap').json()['token']}
        assert client.get('/').status_code == 200
        geometry = client.get('/api/world').json()
        assert geometry['provenance']['source'] == 'OpenStreetMap'
        assert geometry['roads'] and geometry['junctions']
        lig = next(n for n in geometry['junctions'] if all(node in n['id'] for node in
                   ('2023505360','2023505361','2023505364','8389132295')))
        assert max(abs(value) for value in lig['position']) < 50
        assert client.post('/api/control', json={'action': 'set_rate', 'rate': 999}).status_code == 422
        response = client.post('/api/control', headers=auth, json={'action': 'step'})
        assert response.status_code == 200
        export = client.get('/api/export').json()
        assert export['manifest']['calibrated'] is False
        assert export['frames']


@pytest.mark.parametrize('scenario', ['rain', 'roadworks'])
def test_incident_clear_restores_speeds_and_does_not_retrigger(scenario):
    # Test owns TraCI on this thread; no background engine is started.
    engine = HarnessEngine()
    try:
        engine._reset(scenario, 42)
        assert engine.snapshot()['incident_active']
        originals = dict(engine._original_speeds)
        assert originals
        assert any(engine._conn.lane.getMaxSpeed(lane) < speed for lane,speed in originals.items())
        engine._execute({'action':'clear_incident'})
        engine._step()
        assert not engine.snapshot()['incident_active']
        assert all(engine._conn.lane.getMaxSpeed(lane) == speed for lane,speed in originals.items())
    finally:
        engine._save()
        if engine._conn: engine._conn.close()
