from copy import deepcopy


class ProbeGateway:
    """Only exact echoes of frames issued to this session enter the phone stream."""
    def __init__(self, run_id):
        self.run_id = run_id
        self.frames = {}
        self.used = set()
        self.samples = []

    def issue(self, session_id, frame):
        now = frame['sim_time_s']
        self.frames = {key: value for key, value in self.frames.items()
                       if now - value['sim_time_s'] <= 15}
        self.used.intersection_update(self.frames)
        self.frames[(session_id, frame['payload']['frame_id'])] = deepcopy(frame)
        self.prune_samples(now)

    def prune_samples(self, now):
        self.samples[:] = [s for s in self.samples if now - s['sim_time_s'] <= 60]

    def accept(self, session_id, vehicle_id, sample, now):
        if sample['run_id'] != self.run_id:
            raise ValueError('wrong_run')
        if sample['payload']['vehicle_id'] != vehicle_id:
            raise ValueError('wrong_vehicle')
        key = (session_id, sample['payload']['frame_id'])
        frame = self.frames.get(key)
        if not frame:
            raise ValueError('unknown_frame')
        if key in self.used:
            raise ValueError('duplicate')
        if frame['sim_time_s'] > now:
            raise ValueError('future_frame')
        if now - frame['sim_time_s'] > 15:
            raise ValueError('stale_frame')
        if (sample['sim_time_s'] != frame['sim_time_s'] or
                sample['payload']['pose'] != frame['payload']['pose'] or
                vehicle_id != frame['payload']['vehicle_id'] or frame['payload']['state'] != 'active'):
            raise ValueError('altered_frame')
        self.used.add(key)
        accepted = dict(session_id=session_id, vehicle_id=vehicle_id,
                        sim_time_s=frame['sim_time_s'], source='phone', pose=deepcopy(frame['payload']['pose']))
        self.samples.append(accepted)
        self.prune_samples(now)
        return accepted
