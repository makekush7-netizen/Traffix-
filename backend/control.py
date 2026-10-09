"""Pure validation guards. Applying actions remains the worker's responsibility."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SignalState:
    phase_kind: str
    elapsed_s: float
    remaining_s: float


def green(state):
    if state.phase_kind != 'green':
        raise ValueError('clearance_preserved')
    if not all(math.isfinite(t) and t >= 0 for t in (state.elapsed_s, state.remaining_s)):
        raise ValueError('invalid_signal_time')


def extension_remaining(state, receiving_capacity):
    green(state)
    if not receiving_capacity:
        raise ValueError('receiving_capacity_unknown')
    maximum_remaining = 40 - state.elapsed_s
    if maximum_remaining <= state.remaining_s:
        raise ValueError('max_green')
    return min(state.remaining_s + 5, maximum_remaining)


def end_green_remaining(state):
    green(state)
    return max(0, 10 - state.elapsed_s)


def safe_restore(state):
    # The adapter must wait for a cycle boundary before switching programs.
    return 'wait_for_safe_boundary'


def validate_diversion(*, vehicle_id, addressed_vehicle, accepted, now, expiry,
                       current_edge, decision_edge, queue_ratio, route_valid):
    if vehicle_id != addressed_vehicle:
        raise ValueError('wrong_vehicle')
    if not accepted:
        raise ValueError('accept_required')
    if not math.isfinite(now) or not math.isfinite(expiry) or now >= expiry:
        raise ValueError('expired_advisory')
    if current_edge != decision_edge:
        raise ValueError('past_decision_edge')
    if queue_ratio is None:
        raise ValueError('bypass_unobserved')
    if not math.isfinite(queue_ratio) or not 0 <= queue_ratio <= 1:
        raise ValueError('invalid_queue_ratio')
    if queue_ratio > .35:
        raise ValueError('bypass_blocked')
    if not route_valid:
        raise ValueError('invalid_route')
    return True
