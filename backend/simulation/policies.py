"""Pure normalized pressure heuristic. Decisions require worker-owned safe transitions.

Defaults are untested starting values, not calibrated performance results.
"""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PolicyConfig:
    version: str = 'pressure-v1'
    min_green_s: float = 10
    max_green_s: float = 60
    max_red_s: float = 120
    hysteresis: float = .1
    discharge_horizon_s: float = 1


def choose_phase(*, movements, phases, current_phase, green_elapsed_s, red_elapsed_s,
                 clearance_complete, config=None):
    config = config or PolicyConfig()
    def result(action, reason, phase=None, scores=None):
        return {'action': action, 'reason': reason, 'phase_id': phase,
                'scores': scores or {}, 'policy_version': config.version,
                'requires_worker_clearance': action == 'request_transition'}
    bounds = (config.min_green_s, config.max_green_s, config.max_red_s, config.hysteresis, config.discharge_horizon_s)
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x) for x in bounds) or not 0 <= config.min_green_s <= config.max_green_s or config.max_red_s <= 0 or config.discharge_horizon_s <= 0 or config.hysteresis < 0:
        raise ValueError('invalid_policy_bounds')
    if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not isfinite(t) or t < 0 for t in [green_elapsed_s, *red_elapsed_s.values()]):
        return result('fallback', 'invalid_clock')
    if current_phase not in phases:
        return result('fallback', 'unknown_phase')
    if not clearance_complete:
        return result('keep', 'clearance', current_phase)
    by_id = {m['id']: m for m in movements}
    if len(by_id) != len(movements):
        return result('fallback', 'duplicate_movement')
    required = {m for ids in phases.values() for m in ids}
    if not required or not required <= by_id.keys():
        return result('fallback', 'missing_observations')
    scores = {}
    for phase, ids in phases.items():
        if len(ids) != len(set(ids)) or any(set(by_id[mid].get('conflicts_with', [])) & set(ids) for mid in ids):
            return result('fallback', 'conflicting_movements')
        score, legal = 0, bool(ids)
        for mid in ids:
            m = by_id[mid]
            fields = ('queue', 'upstream_capacity', 'downstream_occupied', 'downstream_capacity', 'saturation')
            if not m.get('fresh') or any(not isinstance(m.get(k), (int, float)) or not isfinite(m[k]) or m[k] < 0 for k in fields):
                return result('fallback', 'stale_or_invalid_observations')
            if m['upstream_capacity'] <= 0 or m['downstream_capacity'] <= 0 or m['saturation'] <= 0:
                return result('fallback', 'invalid_capacity')
            if m['downstream_capacity'] - m['downstream_occupied'] < m['saturation'] * config.discharge_horizon_s:
                legal = False
            score += m['saturation'] * (m['queue']/m['upstream_capacity'] - m['downstream_occupied']/m['downstream_capacity'])
        if legal:
            scores[phase] = score
    if not scores:
        return result('fallback', 'receiving_space_unavailable')
    if green_elapsed_s < config.min_green_s:
        return result('keep', 'minimum_green', current_phase, scores)
    alternatives = [p for p in scores if p != current_phase]
    overdue = [p for p in alternatives if red_elapsed_s.get(p, 0) >= config.max_red_s]
    if overdue:
        selected = max(sorted(overdue), key=lambda p: red_elapsed_s.get(p, 0))
        return result('request_transition', 'maximum_red', selected, scores)
    if green_elapsed_s >= config.max_green_s:
        if not alternatives:
            return result('fallback', 'maximum_green_no_safe_alternative', scores=scores)
        return result('request_transition', 'maximum_green', max(sorted(alternatives), key=scores.get), scores)
    best = max(sorted(scores), key=scores.get)
    if current_phase in scores and scores[best] - scores[current_phase] <= config.hysteresis:
        return result('keep', 'hysteresis', current_phase, scores)
    return result('keep' if best == current_phase else 'request_transition', 'pressure', best, scores)
