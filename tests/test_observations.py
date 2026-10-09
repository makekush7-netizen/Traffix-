import pytest

from ml.observations import ObservationAggregator, ProbeSample


def test_empty_road_is_unknown_not_free_flow():
    a = ObservationAggregator({"edge.market": 10.0})
    o = a.snapshot("edge.market", 0)
    assert o.coverage == "unknown"
    assert o.slowdown is None


def test_chatty_vehicle_has_one_vote():
    a = ObservationAggregator({"edge.market": 10.0})
    for t in range(10):
        a.add_probe(ProbeSample("a", "edge.market", t, 0.0))
    a.add_probe(ProbeSample("b", "edge.market", 9, 10.0))
    o = a.snapshot("edge.market", 9)
    assert o.distinct_probes_60s == 2
    assert o.mean_speed_mps == 5.0
    assert o.slowdown == 0.5


def test_sample_ages_out_without_backfill():
    a = ObservationAggregator({"edge.market": 10.0})
    a.add_probe(ProbeSample("a", "edge.market", 0, 0.0))
    o = a.snapshot("edge.market", 16)
    assert o.coverage == "stale"
    assert o.slowdown is None


def test_rejects_nonfinite_speed_and_future_reads():
    with pytest.raises(ValueError):
        ProbeSample("a", "edge.market", 0, float("nan"))
    a = ObservationAggregator({"edge.market": 10.0})
    a.add_probe(ProbeSample("a", "edge.market", 10, 0.0))
    assert a.snapshot("edge.market", 5).coverage == "unknown"


def test_hidden_fixed_sensor_is_rejected():
    a = ObservationAggregator({"edge.market": 10.0})
    with pytest.raises(ValueError, match="not permitted"):
        a.add_fixed("edge.market", 0, 0, 1)


def test_old_vehicle_packet_cannot_replace_newer_state():
    a = ObservationAggregator({"edge.market": 10.0})
    a.add_probe(ProbeSample("a", "edge.market", 10, 8))
    assert a.add_probe(ProbeSample("a", "edge.market", 5, 0)) is False
    assert a.snapshot("edge.market", 10).slowdown == pytest.approx(0.2)
