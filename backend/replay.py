from bisect import bisect_right
from copy import deepcopy


class MatchedReplay:
    """Select recorded state at or before the live clock; no interpolation into the future."""
    REQUIRED = {'network', 'demand', 'scenario', 'sensor_mask', 'seed', 'sumo_version'}

    def __init__(self, live_manifest, recording_manifest, frames):
        if not self.REQUIRED.issubset(live_manifest) or not self.REQUIRED.issubset(recording_manifest):
            raise ValueError('missing_manifest')
        if any(live_manifest[k] != recording_manifest[k] for k in self.REQUIRED):
            raise ValueError('manifest_mismatch')
        self.frames = sorted(deepcopy(frames), key=lambda f: f['sim_time_s'])
        self.times = [f['sim_time_s'] for f in self.frames]
        if any(t < 0 for t in self.times) or len(set(self.times)) != len(self.times):
            raise ValueError('invalid_recording_times')

    def at(self, live_sim_time_s):
        index = bisect_right(self.times, live_sim_time_s) - 1
        if index < 0:
            return None
        frame = deepcopy(self.frames[index])
        frame['source'] = 'RECORDED'
        return frame
