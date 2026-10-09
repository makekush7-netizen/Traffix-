from copy import deepcopy
import pytest
from backend.control import validate_diversion


def test_demo_guidance_defaults_off_and_requires_two_fresh_phones():
    from backend.harness.demo_rules import DemoRules
    rules=DemoRules()
    row=dict(edge_id='edge.test',coverage='fresh',fresh_probes=2,slowdown=.6)
    for t in range(40): assert rules.update(row,t) is None
    rules.set_enabled(True)
    for t in range(30): assert rules.update(row,t) is None
    assert rules.update(row,30)['duration_s']==30
    rules.set_enabled(False)
    assert rules.update(row,40) is None
    assert rules.update({**row,'fresh_probes':1},50) is None


def test_lost_evidence_breaks_continuous_slowdown_rule():
    from backend.harness.demo_rules import DemoRules
    rules=DemoRules(); rules.set_enabled(True)
    row=dict(edge_id='edge.test',coverage='fresh',fresh_probes=2,slowdown=.7)
    rules.update(row,0); rules.update(row,10)
    rules.update({**row,'coverage':'unknown','slowdown':None},20)
    assert rules.update(row,30) is None
    assert rules.update(row,40) is None
    assert rules.update(row,50) is None
    assert rules.update(row,60) is not None


def test_unknown_road_never_has_an_observed_colour():
    from backend.harness.demo_rules import road_colour
    assert road_colour({'coverage':'unknown','slowdown':None})=='unknown'
    assert road_colour({'coverage':'stale','slowdown':.8})=='unknown'
    assert road_colour({'coverage':'fresh','slowdown':.2})=='observed'
    assert road_colour({'coverage':'fresh','slowdown':.5})=='slow'
    assert road_colour({'coverage':'fresh','slowdown':.8})=='alert'


def test_stale_simulation_truth_is_not_issued_as_a_live_frame():
    from fastapi import HTTPException
    from backend.harness.mobile import MobileBridge
    class FailedEngine:
        def snapshot(self): return {'ready':True,'error':'SUMO stopped'}
    with pytest.raises(HTTPException) as failure: MobileBridge(FailedEngine())
    assert failure.value.status_code==503


def test_comparison_requires_matching_seed_checksums_and_complete_integrity():
    from backend.harness.demo_rules import comparison
    manifest=dict(seed=42,scenario_sha256='a',network_sha256='b',demand_sha256='c',complete=True,
                  final_counts={'collisions':0,'teleports':0},mean_journey_s=200)
    assert comparison(manifest,None)['available'] is False
    for key in ('seed','scenario_sha256','network_sha256','demand_sha256'):
        bad={**manifest,key:'wrong'}
        assert comparison(manifest,{'manifest':bad})['available'] is False
    assert comparison({**manifest,'complete':False},{'manifest':manifest})['available'] is False
    bad={**manifest,'final_counts':{'collisions':1,'teleports':0}}
    assert comparison(manifest,{'manifest':bad})['available'] is False
    assert comparison(manifest,{'manifest':manifest})['available'] is True


@pytest.mark.parametrize('overrides,reason',[
    ({'accepted':False},'accept_required'),({'current_edge':'after'},'past_decision_edge'),
    ({'vehicle_id':'other'},'wrong_vehicle'),({'now':45},'expired_advisory'),
    ({'queue_ratio':None},'bypass_unobserved'),({'queue_ratio':.6},'bypass_blocked')])
def test_demo_reuses_existing_diversion_guards(overrides,reason):
    args=dict(vehicle_id='rider',addressed_vehicle='rider',accepted=True,now=10,expiry=45,
              current_edge='before',decision_edge='before',queue_ratio=.1,route_valid=True)
    with pytest.raises(ValueError,match=reason): validate_diversion(**{**args,**overrides})
