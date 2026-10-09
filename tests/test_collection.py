import json
import pandas as pd
from eval.collect import collect_results
from eval.compare import compare_results
from tests.test_compare import result


def test_collection_computes_metrics_instead_of_trusting_manifest_headline(tmp_path):
    run=tmp_path/'run.fixed';run.mkdir()
    metadata=result('fixed',999)
    metadata['teleported']=0
    metadata['collisions']=0
    metadata['scheduled_cohort_size']=1
    (run/'manifest.json').write_text(json.dumps(metadata))
    pd.DataFrame([dict(vehicle_id='a',scheduled_depart_s=0,actual_depart_s=10,arrival_s=100,status='arrived',waiting_s=5,co2_mg=1000000)]).to_csv(run/'trips.csv',index=False)
    report=collect_results(tmp_path)
    assert report['results'][0]['mean_journey_s']==100
    assert not report['errors']


def test_missing_pending_vehicle_invalidates_export(tmp_path):
    run=tmp_path/'run.fixed';run.mkdir()
    metadata=result('fixed',999);metadata.update(teleported=0,scheduled_cohort_size=2)
    (run/'manifest.json').write_text(json.dumps(metadata))
    pd.DataFrame([dict(vehicle_id='a',scheduled_depart_s=0,actual_depart_s=10,arrival_s=100,status='arrived')]).to_csv(run/'trips.csv',index=False)
    report=collect_results(tmp_path)
    assert not report['results'] and 'cohort' in report['errors'][0]['reason']


def test_comparison_keeps_entire_missing_seed_from_expected_plan():
    plan=[]
    for seed in [300,301]:
        for policy in ['fixed','reactive','predictive']:
            plan.append(dict(run_id=f'run.{seed}.{policy}',scenario_id='rain',seed=seed,policy=policy,compliance=.6,sensor_mask_id='mask',data_source='sumo'))
    report=compare_results([result('fixed',100),result('reactive',80),result('predictive',70)],expected_jobs=plan)
    summary=[r for r in report['summary'] if r['metric']=='predictive_vs_fixed_pct'][0]
    assert summary['attempted_seeds']==2 and summary['paired_valid']==1
    assert len(report['pairs'])==2
