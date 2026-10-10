import pandas as pd
import pytest
from eval.network import summarize_network, summarize_actions


def test_time_weighted_queue_and_bypass_burden():
    truth=pd.DataFrame([dict(run_id='r',sim_time_s=t,edge_id=e,jam_length_m=q,vehicle_count=3) for t,q in [(0,0),(5,20),(10,40)] for e in ['main','bypass']])
    result=summarize_network(truth,bypass_edges=['bypass'])
    assert result['peak_total_queue_m']==80
    assert result['network_queue_m_s']==pytest.approx(600)
    assert result['bypass_queue_m_s']==pytest.approx(300)
    assert result['queue_sample_coverage']==1


def test_missing_queue_sample_is_not_zero_queue():
    truth=pd.DataFrame([dict(run_id='r',sim_time_s=t,edge_id='main',jam_length_m=q) for t,q in [(0,0),(5,None),(10,40)]])
    result=summarize_network(truth)
    assert result['network_queue_m_s'] is None and result['queue_sample_coverage']==pytest.approx(2/3)


def test_applied_actions_are_counted_once_with_rejections_separate():
    def event(action,status,kind):
        return dict(type='control.event',run_id='r',msg_id=f'm.{action}',payload=dict(action=dict(action_id=action,kind=kind,vehicle_id='v'),status=status))
    a=event('a','applied','extend_green');b=event('b','applied','reroute');c=event('c','rejected','reroute')
    result=summarize_actions([a,{'event':a},b,c])
    assert result['applied_signal_actions']==1 and result['applied_reroutes']==1 and result['rejected_control_actions']==1


def test_bypass_traffic_burden_rejects_mixed_runs():
    data=pd.DataFrame([dict(run_id=r,sim_time_s=0,edge_id='e',jam_length_m=0) for r in ['a','b']])
    with pytest.raises(ValueError):
        summarize_network(data)
