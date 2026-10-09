import pandas as pd
from eval.jam_gate import check_baseline_jam


def trace(green=True, end=120):
    rows=[dict(run_id='run.fixed',policy='fixed',edge_id='edge.market',sim_time_s=t,
                             slowdown_true=.9,jam_length_m=100,serving_green=green,phase_age_s=10) for t in range(0,end+1,5)]
    rows.extend(dict(run_id='run.fixed',policy='fixed',edge_id='edge.market',sim_time_s=t,slowdown_true=.1,jam_length_m=0,serving_green=True,phase_age_s=10) for t in range(end+5,end+66,5))
    return pd.DataFrame(rows)


def test_persistent_jam_with_failed_green_service_passes_gate():
    result=check_baseline_jam(trace())
    assert result['passed'] and result['evidence'][0]['duration_s']>=60


def test_normal_red_queue_or_brief_pulse_does_not_pass_gate():
    assert not check_baseline_jam(trace(green=False))['passed']
    assert not check_baseline_jam(trace(end=20))['passed']


def test_single_green_sample_then_red_wait_is_not_failed_service():
    data=trace();data.loc[data.sim_time_s>0,'serving_green']=False
    assert not check_baseline_jam(data)['passed']


def test_separate_jams_do_not_have_a_duration_bridging_the_recovery():
    first=trace(end=60);second=trace(end=60);second.sim_time_s+=130
    data=pd.concat([first[first.sim_time_s<130],second],ignore_index=True)
    result=check_baseline_jam(data)
    assert len(result['evidence'])==2 and all(event['duration_s']==60 for event in result['evidence'])
