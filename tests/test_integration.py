import pytest
from ml.integration import TrafficIntelligence


def packet(vehicle, t, run='run.demo'):
    return dict(v=1, type='probe.sample', run_id=run, sim_time_s=t,
                payload=dict(vehicle_id=vehicle, frame_id=f'frame.{vehicle}.{t}', pose=dict(edge_id='edge.market', speed_mps=1, x_m=0, y_m=0)))


def test_runtime_uses_received_uplinks_and_emits_json_safe_events():
    runtime = TrafficIntelligence('run.demo', {'edge.market': 10})
    assert runtime.tick(0, {})['events'][0]['payload']['coverage'] == 'unknown'
    for t in range(5, 71, 5):
        for v in ['a','b']:
            assert runtime.ingest_probe(packet(v,t))
        out = runtime.tick(t, {'edge.market': {'serving_green': True, 'phase_age_s': 10}})
    assert out['detections']['edge.market']['active']
    forecasts = [e for e in out['events'] if e['type'] == 'forecast.edge']
    assert len(forecasts) == 3 and all(e['payload']['usable_for_control'] for e in forecasts)
    import json
    json.dumps(out, allow_nan=False)
    disconnected = runtime.tick(90, {})
    assert not disconnected['detections']['edge.market']['usable_for_control']
    assert all(e['payload']['predicted_slowdown'] is None for e in disconnected['events'] if e['type'] == 'forecast.edge')


def test_runtime_rejects_cross_run_and_clock_reversal():
    runtime = TrafficIntelligence('run.demo', {'edge.market': 10})
    with pytest.raises(ValueError, match='run'):
        runtime.ingest_probe(packet('a',0,run='old'))
    runtime.tick(5,{})
    with pytest.raises(ValueError):
        runtime.tick(4,{})
