from ml.observations import ObservationAggregator, ProbeSample
from ml.detect import DetectionEngine


def observation(t, speed=0, count=2):
    a = ObservationAggregator({"edge.market": 10.0})
    for i in range(count):
        a.add_probe(ProbeSample(str(i), "edge.market", t, speed))
    return a.snapshot("edge.market", t)


def test_normal_red_does_not_raise_jam():
    d = DetectionEngine()
    for t in range(0, 61, 5):
        state = d.update(observation(t), serving_green=False, phase_age_s=40)
    assert not state.active


def test_sustained_slowdown_during_service_raises_jam():
    d = DetectionEngine()
    for t in range(0, 31, 5):
        state = d.update(observation(t), serving_green=True, phase_age_s=10)
    assert state.active
    assert state.evidence_s == 30


def test_one_probe_cannot_authorize_response():
    d = DetectionEngine()
    for t in range(0, 61, 5):
        state = d.update(observation(t, count=1), serving_green=True, phase_age_s=10)
    assert not state.usable_for_control
    assert not state.active


def test_gap_resets_persistence_and_recovery_uses_hysteresis():
    d = DetectionEngine()
    d.update(observation(0), serving_green=True, phase_age_s=10)
    assert not d.update(observation(40), serving_green=True, phase_age_s=10).active
    for t in range(45, 71, 5):
        state = d.update(observation(t), serving_green=True, phase_age_s=10)
    assert state.active
    for t in range(75, 131, 5):
        assert d.update(observation(t, 10), serving_green=True, phase_age_s=10).active
    assert not d.update(observation(135, 10), serving_green=True, phase_age_s=10).active
