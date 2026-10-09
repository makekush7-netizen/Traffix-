import pytest
from ml.observations import ObservationAggregator, ProbeSample, EdgeObservation
from eval.compare import compare_results
from tests.test_compare import result


def test_a_vehicle_that_left_an_edge_cannot_keep_voting_on_old_edge():
    a=ObservationAggregator({'old':10,'new':10})
    a.add_probe(ProbeSample('vehicle','old',0,1))
    a.add_probe(ProbeSample('vehicle','new',5,9))
    assert a.snapshot('old',5).fresh_probes==0


def test_negative_counts_and_fractional_counts_are_rejected():
    for count in [-1,1.5]:
        with pytest.raises(ValueError):
            EdgeObservation('e',0,'fresh',('phone',),1,.9,count,0,fresh_probes=count)


def test_boolean_strings_cannot_make_invalid_run_valid():
    r=result('fixed',100); r['complete']='False'
    with pytest.raises(ValueError,match='boolean'):
        compare_results([r])


def test_window_count_does_not_establish_current_fresh_probe_count():
    o=EdgeObservation.from_mapping(dict(edge_id='e',sim_time_s=60,coverage='fresh',sources='phone',
                                       slowdown=.9,distinct_probes_60s=2,sample_age_sim_s=0))
    assert o.fresh_probes==0
