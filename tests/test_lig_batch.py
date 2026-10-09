import pytest

def test_lig_training_plan_freezes_full_disjoint_seed_grid():
    from eval.lig_pipeline import training_plan
    jobs=training_plan()
    assert len(jobs)==96
    assert {j['seed'] for j in jobs}==set(range(100,108))|set(range(200,203))|set(range(300,305))
    assert {j['policy'] for j in jobs}=={'fixed'}
    assert {j['sensor_mask_id'] for j in jobs}=={'mask.lig.probes'}
    assert len({j['run_id'] for j in jobs})==96

def test_empty_full_state_road_can_confirm_recovery_without_filling_slowdown():
    import pandas as pd
    from eval.jam_gate import check_baseline_jam
    rows=[dict(run_id='run',policy='fixed',edge_id='e',sim_time_s=t,slowdown_true=.9,
               jam_length_m=80,serving_green=True,phase_age_s=t+5,vehicle_count=10) for t in range(0,70,5)]
    rows.extend(dict(run_id='run',policy='fixed',edge_id='e',sim_time_s=t,slowdown_true=None,
                     jam_length_m=0,serving_green=False,phase_age_s=0,vehicle_count=0) for t in range(70,110,5))
    assert check_baseline_jam(pd.DataFrame(rows))['passed']
