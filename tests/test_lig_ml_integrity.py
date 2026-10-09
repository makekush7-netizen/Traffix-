from dataclasses import asdict
import json
import pandas as pd
import pytest
from eval.collect import collect_results
from eval.cohort import Trip
from eval.report import write_run_report
from ml.forecast import ForecastService
from ml.observations import EdgeObservation
from tests.test_compare import result


@pytest.mark.parametrize('failure',[{'valid':False},{'collisions':2},{'final_counts':{'collisions':2}}])
def test_arrived_invalid_run_cannot_publish_headlines(tmp_path,failure):
    metadata={**result('fixed',999),'scheduled_cohort_size':1,'teleported':0,'collisions':0,**failure}
    trips=[Trip('veh.one',0,0,100,'arrived',co2_mg=1e6)]
    run=tmp_path/'inputs'/'run';run.mkdir(parents=True)
    (run/'manifest.json').write_text(json.dumps(metadata))
    pd.DataFrame([asdict(t) for t in trips]).to_csv(run/'trips.csv',index=False)
    collected=collect_results(run.parent)['results'][0]
    report=write_run_report(trips,metadata,tmp_path/'report')
    for output in [collected,report]:
        assert output['complete'] is True
        assert output['valid'] is False
        assert output['mean_journey_s'] is None and output['co2_kg_final'] is None


def test_sumo_missing_collision_evidence_is_unverified(tmp_path):
    output=write_run_report([Trip('v',0,0,10,'arrived',co2_mg=10)],
                            dict(data_source='sumo',scheduled_cohort_size=1,teleported=0),tmp_path)
    assert output['valid'] is False and output['integrity_verified'] is False
    assert 'collision_evidence_missing' in output['invalid_reasons']


def test_clean_cohort_with_explicit_integrity_is_valid(tmp_path):
    output=write_run_report([Trip('v',0,0,10,'arrived',co2_mg=1e6)],
                            dict(data_source='sumo',scheduled_cohort_size=1,teleported=0,collisions=0,valid=True),tmp_path)
    assert output['valid'] and output['integrity_verified']
    assert output['mean_journey_s']==10 and output['co2_kg_final']==1


def observation(t,coverage='fresh'):
    return EdgeObservation('edge.test',t,coverage,('emulated_probe',),5,
                           .5 if coverage=='fresh' else None,2,0,fresh_probes=2)


def test_history_bracketing_boundary_is_eligible():
    history=[observation(t) for t in [0,10,*range(15,66,5)]]
    assert ForecastService().predict(history,120).usable_for_control


@pytest.mark.parametrize('history',[
    [observation(t) for t in [0,20,*range(25,66,5)]],
    [observation(t) for t in range(10,66,5)],
    [observation(t) for t in range(0,61,5)]+[observation(65,'stale')],
])
def test_irregular_history_still_abstains_when_evidence_is_bad(history):
    assert not ForecastService().predict(history,120).usable_for_control
