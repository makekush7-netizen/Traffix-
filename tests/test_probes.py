from copy import deepcopy

import pytest

from backend.probes import ProbeGateway


def fixture():
    return dict(run_id='run.test', sim_time_s=10, payload=dict(frame_id='frame.1',
                vehicle_id='veh.role.rider', state='active', pose=dict(edge_id='edge.market', x_m=1, y_m=2, speed_mps=3)))


def test_no_uplinks_no_observations():
    gateway = ProbeGateway('run.test')
    gateway.issue('session.1', fixture())
    assert gateway.samples == []


@pytest.mark.parametrize('change,now,reason', [
    ('run', 10, 'wrong_run'), ('vehicle', 10, 'wrong_vehicle'),
    ('pose', 10, 'altered_frame'), ('time', 10, 'altered_frame'),
    ('none', 9, 'future_frame'), ('none', 26, 'stale_frame'),
    ('id', 10, 'unknown_frame'),
])
def test_invalid_samples_rejected(change, now, reason):
    gateway = ProbeGateway('run.test')
    frame = fixture()
    gateway.issue('session.1', frame)
    sample = deepcopy(frame)
    if change == 'run': sample['run_id'] = 'run.old'
    if change == 'vehicle': sample['payload']['vehicle_id'] = 'veh.role.auto'
    if change == 'pose': sample['payload']['pose']['speed_mps'] = 99
    if change == 'time': sample['sim_time_s'] = 11
    if change == 'id': sample['payload']['frame_id'] = 'frame.fake'
    with pytest.raises(ValueError, match=reason):
        gateway.accept('session.1', 'veh.role.rider', sample, now)
    assert gateway.samples == []


def test_frame_bound_to_session_and_accepted_once():
    gateway = ProbeGateway('run.test')
    frame = fixture()
    gateway.issue('session.1', frame)
    with pytest.raises(ValueError, match='unknown_frame'):
        gateway.accept('session.2', 'veh.role.rider', frame, 10)
    gateway.accept('session.1', 'veh.role.rider', frame, 10)
    with pytest.raises(ValueError, match='duplicate'):
        gateway.accept('session.1', 'veh.role.rider', frame, 10)
    assert len(gateway.samples) == 1
