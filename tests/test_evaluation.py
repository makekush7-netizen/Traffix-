import json
import pandas as pd
import pytest
from eval.forecasts import evaluate_forecasts
from eval.detection import evaluate_detection
from eval.report import write_run_report
from tests_helpers import trained_dataset
from ml.train import train_models


def test_forecast_evaluation_uses_only_declared_heldout_seeds(tmp_path):
    data=trained_dataset()
    train_models(data,tmp_path,train_seeds={100},validation_seeds={200},test_seeds={300})
    report=evaluate_forecasts(data,tmp_path)
    assert report['split']=='test_only' and report['test_seeds']==[300]
    assert report['horizons']['180']['eligible_rows']==40
    assert set(report['horizons']['180']['methods'])=={'persistence','trend','boosting'}
    with pytest.raises(ValueError,match='test'):
        evaluate_forecasts(data[data.seed==100],tmp_path)


def test_unknown_coverage_counts_as_missed_detection_not_an_excluded_positive():
    detections=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,active=a,usable_for_control=u) for t,a,u in [(0,False,True),(5,True,True),(10,False,False)]])
    truth=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,jam_label=j) for t,j in [(0,False),(5,True),(10,True)]])
    report=evaluate_detection(detections,truth)
    assert report['true_positive']==1 and report['false_negative']==1
    assert report['recall']==0.5 and report['coverage_fraction']==pytest.approx(2/3)


def test_missing_detector_rows_cannot_disappear():
    detections=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=0,active=False,usable_for_control=True)])
    truth=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,jam_label=True) for t in [0,5]])
    assert evaluate_detection(detections,truth)['false_negative']==2


def test_incomplete_report_does_not_publish_headline(tmp_path):
    from eval.cohort import Trip
    metadata=dict(run_id='r',scenario_id='rain',seed=42,policy='fixed',data_source='fixture',teleported=0)
    report=write_run_report([Trip('a',0,10,None,'active')],metadata,tmp_path)
    assert not report['complete'] and report['mean_journey_s'] is None
    text=(tmp_path/'report.md').read_text()
    assert 'fixture' in text and 'Unavailable' in text
    assert (tmp_path/'cohort.png').exists()


def test_sumo_report_requires_verified_scheduled_cohort_size(tmp_path):
    from eval.cohort import Trip
    metadata=dict(run_id='r',data_source='sumo',teleported=0)
    report=write_run_report([Trip('a',0,10,100,'arrived',co2_mg=100)],metadata,tmp_path)
    assert not report['valid'] and report['mean_journey_s'] is None


def test_report_uses_declared_artificial_blocker_exclusions(tmp_path):
    from eval.cohort import Trip
    metadata=dict(run_id='r',data_source='sumo',teleported=0,scheduled_cohort_size=2,excluded_metric_vehicle_ids=['blocker'])
    trips=[Trip('a',0,10,100,'arrived',co2_mg=100),Trip('blocker',0,0,None,'removed')]
    report=write_run_report(trips,metadata,tmp_path)
    assert report['scheduled']==1 and report['excluded']==1 and report['valid']
