import pytest
from ml.observations import ObservationAggregator, ProbeSample
from ml.forecast import ForecastService


def history():
    a = ObservationAggregator({"edge.market": 10})
    out = []
    for t in range(0, 61, 5):
        for v in ["a", "b"]:
            a.add_probe(ProbeSample(v, "edge.market", t, 10 * (1 - t / 200)))
        out.append(a.snapshot("edge.market", t))
    return out


def test_persistence_and_trend_are_causal_and_clipped():
    f = ForecastService()
    assert f.predict(history(), 120, method="persistence").predicted_slowdown == pytest.approx(0.3)
    assert f.predict(history(), 120, method="trend").predicted_slowdown == pytest.approx(0.8375)
    assert f.predict(history(), 300, method="trend").predicted_slowdown == 1


def test_forecast_requires_history_and_stops_after_intervention():
    f = ForecastService()
    assert not f.predict(history()[-1:], 180).usable_for_control
    result = f.predict(history(), 180, intervention_active=True)
    assert result.predicted_slowdown is None
    assert not result.usable_for_control


def test_unsupported_horizon_is_rejected():
    with pytest.raises(ValueError):
        ForecastService().predict(history(), 60)


def test_a_gap_is_not_sixty_seconds_of_observation_history():
    samples = [history()[0], history()[-1]]
    assert not ForecastService().predict(samples, 180).usable_for_control
