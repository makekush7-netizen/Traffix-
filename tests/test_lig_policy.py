from types import SimpleNamespace
import pytest

def test_bounded_extension_preserves_clearance_maximum_and_observation_guard():
    from backend.harness.policy import plan_extension
    assert plan_extension('Grr',15,15,True)==20
    assert plan_extension('Grr',37,1,True)==3
    for state,capacity in [('yrr',True),('rrr',True),('Grr',False)]:
        with pytest.raises(ValueError): plan_extension(state,15,15,capacity)

def test_selection_frozen_on_validation_and_forecasts_shutdown_after_action():
    from backend.harness.policy import BoundedPolicy
    from eval.lig_registry import load_registry
    selection=dict(method='trend',horizon_s=180,selection_split='validation_only',
                   validation_seeds=[200,201,202],reactive=dict(danger=.7,persistence_s=30),
                   predictive=dict(danger=.7,persistence_s=20))
    p=BoundedPolicy('predictive',load_registry(),selection=selection)
    assert p.intervened is False
    with pytest.raises(ValueError,match='selection'):
        BoundedPolicy('predictive',load_registry(),selection={**selection,'validation_seeds':[300]})

def test_visible_forecasts_disable_immediately_after_same_tick_intervention():
    from backend.harness.policy import visible_forecasts
    original=[dict(model='trend',predicted_slowdown=.9,usable_for_control=True,reason='ready')]
    projected=visible_forecasts(original,intervened=True)
    assert projected[0]['usable_for_control'] is False and projected[0]['predicted_slowdown'] is None
    assert original[0]['usable_for_control'] is True
