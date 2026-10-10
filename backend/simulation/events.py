"""Event plans and composable restrictions; no simulator side effects.

The owner worker must apply the preview atomically before recording apply. This ledger
is not evidence of SUMO execution; host audit must include worker acknowledgement.
"""
from copy import deepcopy
from math import isfinite


class EventLedger:
    def __init__(self, base):
        self.base = deepcopy(base)
        self.events = {}
        self.audit = []

    def _audit(self, event_id, action, actor, sim_time_s):
        self.audit.append(dict(event_id=event_id, action=action, actor=actor, sim_time_s=sim_time_s))

    def draft(self, event_id, kind, restrictions, *, actor, start_s, end_s, seed=None):
        if event_id in self.events:
            raise ValueError('duplicate_event_id')
        if kind not in {'rain', 'roadworks', 'blockage', 'rally', 'sensor_outage'}:
            raise ValueError('unsupported_event_kind')
        if not actor or not isinstance(restrictions, dict) or not restrictions or not all(not isinstance(t, bool) and isinstance(t, (int, float)) and isfinite(t) for t in (start_s, end_s)) or start_s < 0 or end_s <= start_s:
            raise ValueError('invalid_event')
        for target, values in restrictions.items():
            if target not in self.base or not values or not values.keys() <= {'closed', 'speed_factor', 'sensor_available'}:
                raise ValueError('invalid_event_target_or_restriction')
            for key, value in values.items():
                if key == 'speed_factor':
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 < value <= 1:
                        raise ValueError('invalid_speed_factor')
                elif not isinstance(value, bool):
                    raise ValueError('invalid_boolean_restriction')
        self.events[event_id] = dict(event_id=event_id, kind=kind, restrictions=deepcopy(restrictions),
                                     author=actor, start_s=start_s, end_s=end_s, seed=seed, status='draft')
        self._audit(event_id, 'draft', actor, start_s)
        return deepcopy(self.events[event_id])

    def effective(self, include=None):
        state = deepcopy(self.base)
        for eid, event in self.events.items():
            if event['status'] != 'active' and eid != include:
                continue
            for target, restrictions in event['restrictions'].items():
                for key, value in restrictions.items():
                    default = False if key == 'closed' else True if key == 'sensor_available' else 1.0
                    old = state[target].get(key, default)
                    state[target][key] = old or value if key == 'closed' else old and value if key == 'sensor_available' else min(old, value)
        return state

    def preview(self, event_id):
        event = self.events[event_id]
        if event['status'] not in {'draft', 'previewed'}:
            raise ValueError('event_not_draft')
        event['status'] = 'previewed'
        self._audit(event_id, 'preview', event['author'], event['start_s'])
        return {'event': deepcopy(event), 'effective': self.effective(include=event_id),
                'restoration': self.effective(),
                'requires_worker_validation': True}

    def apply(self, event_id, *, actor, sim_time_s):
        event = self.events[event_id]
        if event['status'] == 'active':
            return self.effective()
        if event['status'] == 'draft':
            raise ValueError('event_requires_preview')
        if event['status'] != 'previewed' or not event['start_s'] <= sim_time_s < event['end_s']:
            raise ValueError('event_not_eligible')
        event['status'] = 'active'
        self._audit(event_id, 'apply', actor, sim_time_s)
        return self.effective()

    def end(self, event_id, *, actor, sim_time_s):
        event = self.events[event_id]
        if event['status'] == 'ended':
            return self.effective()
        event['status'] = 'ended' if event['status'] == 'active' else 'cancelled'
        self._audit(event_id, 'end', actor, sim_time_s)
        return self.effective()
