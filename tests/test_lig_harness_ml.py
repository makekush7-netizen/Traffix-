import pytest
from backend.harness.engine import HarnessEngine

def test_harness_rejects_invalid_model_or_fake_phone_source_before_start():
    with pytest.raises(ValueError,match='probe mode'):
        HarnessEngine(ml_options={'probe_mode':'gps'})
    with pytest.raises(ValueError,match='predictive'):
        HarnessEngine(ml_options={'policy':'predictive'})

def test_harness_live_zero_uplinks_stays_unknown_on_sensor_poor_focus():
    engine=HarnessEngine(run_config=dict(profile='conservative',sublane=False,max_end_s=2400,
                                        warmup_s=10,demand_per_hour=500),ml_options={'probe_mode':'phone'})
    try:
        engine._reset('everyday',42)
        state=engine.snapshot()['intelligence']
        assert state['authenticated_phone_uplinks']==0
        focus=next(row for row in state['observations'] if row['edge_id']=='edge.lig.approach.0')
        assert focus['coverage']=='unknown' and focus['sources']==[] and focus['distinct_probes_60s']==0
        assert all(f['usable_for_control'] is False for f in state['forecasts'] if f['edge_id']==focus['edge_id'])
    finally:
        if engine._conn: engine._conn.close()
