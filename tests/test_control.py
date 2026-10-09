import pytest

from backend.control import SignalState, extension_remaining, end_green_remaining, validate_diversion, safe_restore


def test_clearance_and_maximum_green_preserved():
    with pytest.raises(ValueError, match='clearance'):
        extension_remaining(SignalState('yellow', 12, 3), True)
    assert extension_remaining(SignalState('green', 34, 3), True) == 6
    with pytest.raises(ValueError, match='max_green'):
        extension_remaining(SignalState('green', 40, 0), True)
    with pytest.raises(ValueError, match='receiving_capacity_unknown'):
        extension_remaining(SignalState('green', 12, 3), False)
    assert end_green_remaining(SignalState('green', 7, 15)) == 3
    assert end_green_remaining(SignalState('green', 15, 10)) == 0
    assert safe_restore(SignalState('yellow', 1, 3)) == 'wait_for_safe_boundary'


@pytest.mark.parametrize('overrides,reason', [
    ({'queue_ratio': None}, 'bypass_unobserved'),
    ({'queue_ratio': .36}, 'bypass_blocked'),
    ({'now': 46}, 'expired_advisory'),
    ({'current_edge': 'edge.after'}, 'past_decision_edge'),
    ({'accepted': False}, 'accept_required'),
    ({'vehicle_id': 'veh.role.auto'}, 'wrong_vehicle'),
    ({'route_valid': False}, 'invalid_route'),
])
def test_diversion_guard(overrides, reason):
    args = dict(vehicle_id='veh.role.rider', addressed_vehicle='veh.role.rider', accepted=True,
                now=20, expiry=45, current_edge='edge.upstream', decision_edge='edge.upstream',
                queue_ratio=.2, route_valid=True)
    args.update(overrides)
    with pytest.raises(ValueError, match=reason):
        validate_diversion(**args)
