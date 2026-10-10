from dataclasses import asdict
import json
import pandas as pd
import pytest
from tests.test_compare import result
from eval.generate import experiment_grid
from eval.compare import compare_results
from eval.collect import collect_results


def test_demand_level_dimension_produces_original_training_and_validation_counts():
    train=experiment_grid(['rain','market','procession'],range(100,108),policies=['fixed'],demand_ids=['demand.reference','demand.high'])
    val=experiment_grid(['rain','market','procession'],range(200,203),policies=['fixed'],demand_ids=['demand.reference','demand.high'])
    assert len(train)==48 and len(val)==18
    assert len({r['run_id'] for r in train})==48


def test_changed_metric_cohort_is_rejected_even_when_raw_demand_hash_matches():
    baseline=result('fixed',150);changed=result('predictive',100)
    baseline.update(metric_cohort_sha256='a+b',excluded_vehicle_ids_sha256='none')
    changed.update(metric_cohort_sha256='a',excluded_vehicle_ids_sha256='b')
    with pytest.raises(ValueError,match='cohort|excluded'):
        compare_results([baseline,changed])


def test_emission_assumptions_cannot_differ_for_co2_gain():
    baseline=result('fixed',100);changed=result('predictive',90)
    baseline['emission_assumptions_sha256']='fleet1';changed['emission_assumptions_sha256']='fleet2'
    with pytest.raises(ValueError,match='emission'):
        compare_results([baseline,changed])


def test_collector_hashes_actual_metric_cohort_and_exclusions(tmp_path):
    from eval.cohort import Trip
    for policy,exclude in [('fixed',[]),('predictive',['b'])]:
        run=tmp_path/f'run.{policy}';run.mkdir()
        metadata=result(policy,100);metadata.update(scheduled_cohort_size=2,teleported=0,excluded_metric_vehicle_ids=exclude)
        (run/'manifest.json').write_text(json.dumps(metadata))
        pd.DataFrame([asdict(Trip('a',0,0,100,'arrived')),asdict(Trip('b',0,0,200 if policy=='fixed' else None,'arrived' if policy=='fixed' else 'removed'))]).to_csv(run/'trips.csv',index=False)
    results=collect_results(tmp_path)['results']
    assert len(results)==2
    with pytest.raises(ValueError,match='cohort|excluded'):
        compare_results(results)
