import pandas as pd
from eval.detection import evaluate_detection
from eval.tune import tune_triggers


def test_false_alert_and_later_missed_event_are_both_counted():
    obs=pd.DataFrame([dict(run_id='r',seed=200,policy='fixed',edge_id='e',sim_time_s=t,coverage='fresh',sources='phone',
                           mean_speed_mps=2 if t<=100 else 10,slowdown=.8 if t<=100 else 0,distinct_probes_60s=2,
                           fresh_probes=2,sample_age_sim_s=0,serving_green=True,phase_age_s=20,data_source='fixture') for t in range(0,401,5)])
    truth=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,jam_label=300<=t<=350) for t in range(0,401,5)])
    result=tune_triggers(obs,truth)
    score=next(s for s in result['scores'] if s['policy']=='reactive' and s['danger']==.7 and s['persistence_s']==30)
    assert score['false_alert_edges']==1 and score['missed_jam_edges']==1
    assert score['missed_events']==1 and score['false_alerts_per_sim_hour']>0


def test_event_rate_uses_simulation_hours_and_reports_warning_delay():
    truth=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,jam_label=100<=t<=150) for t in range(0,3601,5)])
    detections=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,active=20<=t<=30 or 110<=t<=150,usable_for_control=True) for t in range(0,3601,5)])
    result=evaluate_detection(detections,truth)
    assert result['jam_events']==1 and result['missed_events']==0
    assert result['false_alerts']==1 and result['false_alerts_per_sim_hour']==1
    assert result['median_detection_delay_s']==10
