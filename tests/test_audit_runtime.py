import pandas as pd
import pytest
from ml.integration import TrafficIntelligence
from ml.observations import EdgeObservation, ProbeSample
from ml.detect import DetectionEngine
from ml.forecast import ForecastService
from ml.trigger import FirstResponseTrigger
from eval.generate import build_dataset


def obs(t, slowdown=.9):
    return EdgeObservation('edge.market',t,'fresh',('phone',),10*(1-slowdown),slowdown,2,0,fresh_probes=2)


def test_runtime_and_dataset_features_match_after_long_history():
    from ml.features import build_features, FEATURE_COLUMNS
    runtime=TrafficIntelligence('run.same',{'edge.market':10})
    logs=[];truth=[]
    for t in range(0,401,5):
        for vehicle in ['a','b']:
            runtime.ingest_emulated_probe(ProbeSample(vehicle,'edge.market',t,5,source='emulated_probe'))
        output=runtime.tick(t,{})
        logs.append({**output['log_rows'][0],'seed':100,'policy':'fixed','data_source':'fixture'})
        truth.append(dict(run_id='run.same',edge_id='edge.market',sim_time_s=t,slowdown_true=.5))
    live=build_features(runtime.history['edge.market'])
    offline=build_dataset(pd.DataFrame(logs),pd.DataFrame(truth)).iloc[-1]
    for feature in FEATURE_COLUMNS:
        if pd.isna(live[feature]):
            assert pd.isna(offline[feature])
        else:
            assert live[feature]==pytest.approx(offline[feature]),feature


def test_red_queue_that_discharges_after_green_never_becomes_a_jam():
    detector=DetectionEngine()
    for t in range(0,61,5):
        assert not detector.update(obs(t),serving_green=False,phase_age_s=t).active
    assert not detector.update(obs(65),serving_green=True,phase_age_s=5).active
    assert not detector.update(obs(70,.4),serving_green=True,phase_age_s=10).active
    assert not detector.update(obs(75,.1),serving_green=True,phase_age_s=15).active


def test_trend_targets_same_future_average_window_as_model_labels():
    history=[obs(t,.2+t*.001) for t in range(0,61,5)]
    result=ForecastService().predict(history,120,method='trend')
    expected=sum(.2+t*.001 for t in range(155,181,5))/6
    assert result.predicted_slowdown==pytest.approx(expected)


def test_predictive_response_also_waits_for_green_evidence():
    from ml.forecast import ForecastResult
    trigger=FirstResponseTrigger()
    f=ForecastResult('edge.market','trend',180,.9,True,'ready')
    for t in range(0,61,5):
        assert not trigger.update(obs(t,.4),f,serving_green=False,phase_age_s=t).eligible
    assert not trigger.update(obs(65,.4),f,serving_green=True,phase_age_s=5).eligible
    assert not trigger.update(obs(70,.4),f,serving_green=True,phase_age_s=10).eligible
    assert trigger.update(obs(75,.4),f,serving_green=True,phase_age_s=15).eligible


def test_csv_fractional_probe_counts_are_not_truncated_into_valid_counts():
    with pytest.raises(ValueError):
        EdgeObservation.from_mapping(dict(edge_id='e',sim_time_s=0,coverage='fresh',sources='phone',
                                          slowdown=.9,distinct_probes_60s=2.9,fresh_probes=2.9,sample_age_sim_s=0))


def test_detector_rejects_duplicate_time_and_invalid_signal_context():
    d=DetectionEngine()
    d.update(obs(0),serving_green=True,phase_age_s=10)
    with pytest.raises(ValueError):
        d.update(obs(0),serving_green=True,phase_age_s=10)
    with pytest.raises(ValueError):
        DetectionEngine().update(obs(0),serving_green='false',phase_age_s=10)
