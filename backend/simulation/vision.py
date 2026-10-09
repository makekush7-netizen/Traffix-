"""Independent camera fixtures and optional local tracking runtime.

No identity recognition, incident inference or real-camera accuracy claim. Track IDs
are camera-local. An uncalibrated image cannot supply physical speed or queue metres.
"""
from collections import Counter
from pathlib import Path
from math import isfinite
import hashlib


def finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


class LineCrossingAdapter:
    def __init__(self, *, line_x, max_age_s=2, min_confidence=.5, max_tracks=4096,
                 meters_per_pixel=None, calibration_id=None):
        if not all(finite_number(value) for value in (line_x, max_age_s, min_confidence)) or max_age_s <= 0 or not 0 <= min_confidence <= 1 or isinstance(max_tracks, bool) or not isinstance(max_tracks, int) or max_tracks <= 0:
            raise ValueError('invalid_camera_configuration')
        if meters_per_pixel is not None and (not calibration_id or not finite_number(meters_per_pixel) or meters_per_pixel <= 0):
            raise ValueError('calibration_required')
        self.line_x, self.max_age_s, self.min_confidence = line_x, max_age_s, min_confidence
        self.max_tracks = max_tracks
        self.meters_per_pixel, self.calibration_id = meters_per_pixel, calibration_id
        self._tracks, self._counted = {}, set()
        self._classes = Counter()
        self._last_time = None
        self.dropped_frames = 0

    def process(self, tracks, *, frame_time_s, now_s):
        def report(status, speed=None):
            return {'status': status, 'count': sum(self._classes.values()), 'classes': dict(self._classes),
                    'speed_mps': speed, 'calibration_id': self.calibration_id,
                    'source_type': 'camera_measurement', 'dropped_frames': self.dropped_frames}
        if not all(finite_number(t) for t in (frame_time_s, now_s)) or not 0 <= now_s-frame_time_s <= self.max_age_s or (self._last_time is not None and frame_time_s <= self._last_time):
            self.dropped_frames += 1
            return report('stale')
        self._last_time = frame_time_s
        accepted, speeds = 0, []
        seen = set()
        for track in tracks:
            if not isinstance(track, dict) or not {'track_id', 'x', 'y'} <= track.keys() or track['track_id'] is None:
                continue
            tid = str(track['track_id'])
            if tid in seen:
                continue
            seen.add(tid)
            confidence = track.get('confidence', 0)
            x, y = track['x'], track['y']
            if not all(finite_number(v) for v in (confidence, x, y)) or not self.min_confidence <= confidence <= 1:
                continue
            if tid not in self._tracks and len(self._tracks) >= self.max_tracks:
                return report('degraded_capacity')
            accepted += 1
            previous = self._tracks.get(tid)
            side = -1 if x < self.line_x else 1 if x > self.line_x else 0
            if previous and frame_time_s - previous[2] <= self.max_age_s:
                px, py, pt, old_side = previous
                if side and old_side and side != old_side and tid not in self._counted:
                    self._counted.add(tid)
                    cls = track.get('class_name')
                    self._classes[cls if cls in {'car','motorcycle','bicycle','bus','truck'} else 'unknown'] += 1
                if self.meters_per_pixel is not None and frame_time_s > pt:
                    speeds.append(((x-px)**2+(y-py)**2)**.5*self.meters_per_pixel/(frame_time_s-pt))
                side = side or old_side
            self._tracks[tid] = (x, y, frame_time_s, side)
        return report('available' if accepted else 'no_input' if not tracks else 'degraded_confidence',
                      sum(speeds)/len(speeds) if speeds else None)


class LocalYoloRunner:
    """Opt-in only. No automatic weights download; runtime import is lazy.

Caller supplies reviewed local weights, SHA256 and license record. Execute inference
outside the simulation owner with a bounded latest-frame queue in the host adapter.
"""
    def __init__(self, weights, *, sha256=None, license_record=None, tracker='bytetrack.yaml'):
        if tracker not in {'bytetrack.yaml', 'botsort.yaml'}:
            raise ValueError('unsupported_tracker')
        self.weights, self.sha256, self.license_record, self.tracker = weights, sha256, license_record, tracker
        self.status = 'ready' if weights and Path(weights).is_file() and sha256 and license_record else 'unavailable'
        self._model = None

    def track(self, clip):
        if self.status == 'unavailable' or not Path(clip).is_file():
            raise ValueError('local_weights_license_or_clip_unavailable')
        if self._model is None:
            if hashlib.sha256(Path(self.weights).read_bytes()).hexdigest() != self.sha256:
                raise ValueError('weights_checksum_mismatch')
            try:
                from ultralytics import YOLO
                self._model = YOLO(str(self.weights))
            except ImportError as exc:
                self.status = 'unavailable'
                raise RuntimeError('optional_ultralytics_not_installed') from exc
        try:
            return self._model.track(source=str(clip), tracker=self.tracker, stream=True, persist=True, verbose=False)
        except RuntimeError:
            self.status = 'degraded'
            raise
