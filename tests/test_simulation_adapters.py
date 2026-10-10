import pytest
from backend.simulation.observations import validate_observation, ObservationStore
from backend.simulation.policies import choose_phase, PolicyConfig
from backend.simulation.events import EventLedger
from backend.simulation.vision import LineCrossingAdapter, LocalYoloRunner


def observation(**updates):
    return dict(source_type='camera_measurement', source_id='cam.1', run_id='run.1',
                sim_time_s=10, wall_time_s=100, confidence=.8, coverage=['edge.1'],
                units={'count': 'vehicles'}, values={'count': 3}, **updates)


def test_observation_provenance_and_missing_are_unknown():
    store = ObservationStore('run.1')
    assert store.snapshot(now_sim_s=10, now_wall_s=100)['status'] == 'unknown'
    store.ingest(observation(), now_sim_s=10, now_wall_s=100)
    result = store.snapshot(now_sim_s=10, now_wall_s=100)
    assert result['phone_observation_count'] == 0
    assert result['observations'][0]['source_type'] == 'camera_measurement'
    assert store.snapshot(now_sim_s=99, now_wall_s=199)['status'] == 'unknown'


@pytest.mark.parametrize('field,value', [('sim_time_s', 100), ('wall_time_s', 1), ('confidence', float('nan')), ('source_type', 'truth'), ('run_id', 'wrong')])
def test_observation_rejects_bad_or_stale(field, value):
    data = observation(); data[field] = value
    with pytest.raises(ValueError):
        validate_observation(data, run_id='run.1', now_sim_s=10, now_wall_s=100)


def movements():
    return [dict(id='a', queue=8, upstream_capacity=10, downstream_occupied=0,
                 downstream_capacity=10, saturation=1, fresh=True),
            dict(id='b', queue=1, upstream_capacity=10, downstream_occupied=0,
                 downstream_capacity=10, saturation=1, fresh=True)]


def decision(**kwargs):
    args = dict(movements=movements(), phases={'A':['a'], 'B':['b']}, current_phase='A',
                green_elapsed_s=20, red_elapsed_s={'A':0, 'B':0}, clearance_complete=True)
    args.update(kwargs)
    return choose_phase(**args)


def test_pressure_safety_fairness_and_missing_inputs():
    assert decision(green_elapsed_s=1)['reason'] == 'minimum_green'
    assert decision(red_elapsed_s={'A':0, 'B':150})['phase_id'] == 'B'
    assert decision(clearance_complete=False)['reason'] == 'clearance'
    blocked = movements(); blocked[1]['downstream_occupied'] = 10
    assert decision(movements=blocked, red_elapsed_s={'B':150})['phase_id'] != 'B'
    stale = movements(); stale[0]['fresh'] = False
    assert decision(movements=stale)['action'] == 'fallback'
    assert decision(green_elapsed_s=100)['phase_id'] == 'B'
    assert decision(movements=[])['action'] == 'fallback'


def test_event_overlap_restores_remaining_restrictions_and_audits():
    ledger = EventLedger({'edge.1': {'closed':False, 'speed_factor':1.0}})
    ledger.draft('rain', 'rain', {'edge.1':{'speed_factor':.5}}, actor='op', start_s=0, end_s=100)
    assert ledger.preview('rain')['effective']['edge.1']['speed_factor'] == .5
    assert ledger.effective()['edge.1']['speed_factor'] == 1
    ledger.apply('rain', actor='op', sim_time_s=0)
    ledger.draft('work', 'roadworks', {'edge.1':{'closed':True}}, actor='op', start_s=0, end_s=100)
    ledger.preview('work')
    ledger.apply('work', actor='op', sim_time_s=0)
    ledger.apply('work', actor='op', sim_time_s=0)
    ledger.end('rain', actor='op', sim_time_s=10)
    assert ledger.effective()['edge.1'] == {'closed':True, 'speed_factor':1.0}
    ledger.end('work', actor='op', sim_time_s=11)
    assert not ledger.effective()['edge.1']['closed']
    assert len([a for a in ledger.audit if a['event_id']=='work' and a['action']=='apply']) == 1


def test_event_invalid_apply_is_atomic():
    ledger = EventLedger({'edge.1': {'closed':False, 'speed_factor':1.0}})
    with pytest.raises(ValueError):
        ledger.draft('bad', 'rain', {'missing':{'closed':True}}, actor='op', start_s=0, end_s=10)
    assert not ledger.events


def track(x, **kwargs):
    return dict(track_id='1', x=x, y=0, class_name='car', confidence=.9) | kwargs


def test_camera_unique_crossings_unknown_class_uncalibrated_and_stale():
    adapter = LineCrossingAdapter(line_x=0)
    assert adapter.process([track(-1)], frame_time_s=0, now_s=0)['count'] == 0
    result = adapter.process([track(1)], frame_time_s=1, now_s=1)
    assert result['count'] == 1 and result['speed_mps'] is None
    adapter.process([track(-1)], frame_time_s=2, now_s=2)
    assert adapter.process([track(1)], frame_time_s=3, now_s=3)['count'] == 1
    adapter.process([track(-1, track_id='2', class_name='ambulance')], frame_time_s=4, now_s=4)
    assert adapter.process([track(1, track_id='2', class_name='ambulance')], frame_time_s=5, now_s=5)['classes']['unknown'] == 1
    assert adapter.process([], frame_time_s=6, now_s=100)['status'] == 'stale'
    assert LineCrossingAdapter(line_x=0).process([], frame_time_s=0, now_s=0)['status'] == 'no_input'


def test_yolo_missing_weights_does_not_import_or_download():
    runner = LocalYoloRunner(None)
    assert runner.status == 'unavailable'
    with pytest.raises(ValueError):
        runner.track('missing.mp4')


def test_camera_occlusion_does_not_infer_crossing_through_missing_frames():
    adapter = LineCrossingAdapter(line_x=0, max_age_s=2)
    adapter.process([track(-1)], frame_time_s=0, now_s=0)
    assert adapter.process([track(1)], frame_time_s=10, now_s=10)['count'] == 0


def test_event_requires_preview_before_apply():
    ledger = EventLedger({'edge.1': {'closed':False}})
    ledger.draft('work', 'roadworks', {'edge.1':{'closed':True}}, actor='op', start_s=0, end_s=10)
    with pytest.raises(ValueError, match='preview'):
        ledger.apply('work', actor='op', sim_time_s=0)


def test_observation_null_value_remains_unknown():
    store = ObservationStore('run.1')
    data = observation(); data['values'] = {'count': None}
    store.ingest(data, now_sim_s=10, now_wall_s=100)
    assert store.snapshot(now_sim_s=10, now_wall_s=100)['status'] == 'unknown'

@pytest.mark.parametrize('elapsed', [-1, float('nan'), float('inf')])
def test_pressure_invalid_clock_falls_back(elapsed):
    assert decision(green_elapsed_s=elapsed)['action'] == 'fallback'


def test_calibrated_fixture_speed_and_low_confidence():
    adapter = LineCrossingAdapter(line_x=0, meters_per_pixel=.5, calibration_id='fixture-only')
    adapter.process([track(-1)], frame_time_s=0, now_s=0)
    assert adapter.process([track(1)], frame_time_s=1, now_s=1)['speed_mps'] == 1
    assert adapter.process([track(2, confidence=.1)], frame_time_s=2, now_s=2)['status'] == 'degraded_confidence'


def test_event_preview_is_audited_and_includes_reversal():
    ledger = EventLedger({'edge.1': {'closed':False}})
    ledger.draft('work', 'roadworks', {'edge.1':{'closed':True}}, actor='op', start_s=0, end_s=10)
    preview = ledger.preview('work')
    assert ledger.audit[-1]['action'] == 'preview'
    assert preview['restoration'] == {'edge.1': {'closed':False}}

@pytest.mark.parametrize('config', [PolicyConfig(hysteresis=float('nan')), PolicyConfig(min_green_s=True), PolicyConfig(max_green_s=float('inf'))])
def test_pressure_configuration_rejects_non_finite_or_boolean(config):
    with pytest.raises(ValueError, match='invalid_policy'):
        decision(config=config)


def test_pressure_rejects_conflicting_and_duplicate_movements():
    invalid = movements(); invalid[0]['conflicts_with'] = ['b']
    assert decision(movements=invalid, phases={'A':['a','b']})['action'] == 'fallback'
    assert decision(movements=movements()+[movements()[0]])['action'] == 'fallback'


def test_operator_report_cannot_establish_verified_traffic():
    store = ObservationStore('run.1')
    data = observation(); data['source_type'] = 'operator_report'
    store.ingest(data, now_sim_s=10, now_wall_s=100)
    assert store.snapshot(now_sim_s=10, now_wall_s=100)['status'] == 'unknown'


@pytest.mark.parametrize('updates', [{'coverage':[]}, {'coverage':[42]}, {'units':{'count':'m/s'}}])
def test_observation_rejects_invalid_coverage_or_units(updates):
    data = observation(); data.update(updates)
    with pytest.raises(ValueError):
        validate_observation(data, run_id='run.1', now_sim_s=10, now_wall_s=100)


def test_camera_untrusted_scalar_values_degrade_without_crashing():
    adapter = LineCrossingAdapter(line_x=0)
    assert adapter.process([track('bad')], frame_time_s=0, now_s=0)['status'] == 'degraded_confidence'
    assert adapter.process([], frame_time_s='bad', now_s=0)['status'] == 'stale'


@pytest.mark.parametrize('params', [{'line_x':float('nan')}, {'line_x':0,'max_tracks':0}, {'line_x':0,'meters_per_pixel':float('nan'),'calibration_id':'fixture'}])
def test_camera_configuration_validation(params):
    with pytest.raises(ValueError):
        LineCrossingAdapter(**params)

@pytest.mark.parametrize('elapsed', [True, '20'])
def test_pressure_rejects_non_numeric_clock(elapsed):
    assert decision(green_elapsed_s=elapsed)['action'] == 'fallback'


def test_pressure_unknown_phase_falls_back():
    assert decision(current_phase='not.a.phase')['action'] == 'fallback'


@pytest.mark.parametrize('bad', [{}, {'track_id':'1'}, None])
def test_camera_malformed_track_degrades(bad):
    assert LineCrossingAdapter(line_x=0).process([bad], frame_time_s=0, now_s=0)['status'] == 'degraded_confidence'


@pytest.mark.parametrize('start', [True, 'now', float('nan')])
def test_event_invalid_time_rejected_without_mutation(start):
    ledger = EventLedger({'edge.1': {'closed':False}})
    with pytest.raises(ValueError):
        ledger.draft('e','roadworks',{'edge.1':{'closed':True}}, actor='op', start_s=start, end_s=10)
    assert ledger.events == {}
