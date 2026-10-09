"""Validated, source-preserving observations. No simulator truth access."""
from copy import deepcopy
from math import isfinite

SOURCE_TYPES = frozenset({'simulated_sensor', 'phone_sample', 'camera_measurement', 'operator_report', 'emulated_probe'})


def validate_observation(data, *, run_id, now_sim_s, now_wall_s, max_age_s=10):
    required = {'source_type', 'source_id', 'run_id', 'sim_time_s', 'wall_time_s', 'confidence', 'coverage', 'units', 'values'}
    if not required <= data.keys():
        raise ValueError('missing_observation_fields')
    if data['source_type'] not in SOURCE_TYPES or data['run_id'] != run_id or not data['source_id']:
        raise ValueError('invalid_source_or_run')
    for value in (data['sim_time_s'], data['wall_time_s'], data['confidence'], now_sim_s, now_wall_s, max_age_s):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError('non_finite_observation')
    if max_age_s <= 0 or not 0 <= data['confidence'] <= 1:
        raise ValueError('invalid_quality_or_age_bound')
    sim_age, wall_age = now_sim_s - data['sim_time_s'], now_wall_s - data['wall_time_s']
    if not 0 <= sim_age <= max_age_s or not 0 <= wall_age <= max_age_s:
        raise ValueError('stale_or_future_observation')
    if not isinstance(data['coverage'], list) or not isinstance(data['values'], dict) or not isinstance(data['units'], dict):
        raise ValueError('invalid_measurement_shape')
    if not data['values'].keys() <= data['units'].keys():
        raise ValueError('measurement_units_missing')
    expected_units = {'count': 'vehicles', 'queue': 'vehicles', 'speed_mps': 'm/s',
                      'queue_m': 'm', 'occupancy': 'fraction'}
    if not data['coverage'] or any(not isinstance(edge, str) or not edge for edge in data['coverage']):
        raise ValueError('invalid_coverage')
    if any(not isinstance(unit, str) or not unit for unit in data['units'].values()):
        raise ValueError('invalid_units')
    if any(key in expected_units and data['units'][key] != expected_units[key] for key in data['values']):
        raise ValueError('invalid_units')
    for value in data['values'].values():
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0):
            raise ValueError('invalid_measurement')
    return deepcopy(data) | {'age_s': sim_age, 'wall_age_s': wall_age,
                             'verified': data['source_type'] != 'operator_report'}


class ObservationStore:
    """Latest sample per source, bounded in size; absence is explicitly unknown."""
    def __init__(self, run_id, max_age_s=10, max_sources=256):
        self.run_id, self.max_age_s, self.max_sources = run_id, max_age_s, max_sources
        self._sources = {}

    def ingest(self, data, *, now_sim_s, now_wall_s):
        value = validate_observation(data, run_id=self.run_id, now_sim_s=now_sim_s,
                                     now_wall_s=now_wall_s, max_age_s=self.max_age_s)
        key = (value['source_type'], value['source_id'])
        old = self._sources.get(key)
        if old and (value['sim_time_s'] <= old['sim_time_s'] or value['wall_time_s'] <= old['wall_time_s']):
            raise ValueError('duplicate_or_out_of_order_observation')
        if key not in self._sources and len(self._sources) >= self.max_sources:
            raise ValueError('source_capacity')
        self._sources[key] = value
        return deepcopy(value)

    def snapshot(self, *, now_sim_s, now_wall_s):
        values = []
        for value in self._sources.values():
            try:
                values.append(validate_observation(value, run_id=self.run_id, now_sim_s=now_sim_s,
                                                   now_wall_s=now_wall_s, max_age_s=self.max_age_s))
            except ValueError:
                pass
        return {'status': 'available' if any(item['verified'] and any(v is not None for v in item['values'].values()) for item in values) else 'unknown', 'observations': values,
                'phone_observation_count': sum(v['source_type'] == 'phone_sample' for v in values)}
