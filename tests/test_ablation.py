import pytest
from tests.test_compare import result
from eval.ablation import compare_sensor_results


def test_cross_mask_paired_gain_and_missing_seed_are_reported():
    rows=[];plan=[]
    for seed in [300,301]:
        for mask in ['boundary','phones']:
            r=result('predictive',100 if mask=='boundary' else 80)
            r.update(seed=seed,sensor_mask_id=mask,run_id=f'run.{seed}.{mask}',probe_assignment_sha256=mask)
            plan.append(r)
            if seed==300:
                rows.append(r)
    report=compare_sensor_results(rows,baseline_mask='boundary',phone_mask='phones',expected_jobs=plan)
    assert report['summary'][0]['paired_valid']==1 and report['summary'][0]['attempted_seeds']==2
    assert report['summary'][0]['median_journey_improvement_pct']==pytest.approx(20)


def test_sensor_ablation_rejects_changed_cohort():
    a=result('predictive',100);b=result('predictive',80)
    a['sensor_mask_id']='boundary';b.update(sensor_mask_id='phones',cohort_sha256='changed')
    with pytest.raises(ValueError,match='cohort'):
        compare_sensor_results([a,b],baseline_mask='boundary',phone_mask='phones')
