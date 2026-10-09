import pandas as pd
import pytest
from eval.generate import build_dataset, experiment_grid


def frames():
    observations = pd.DataFrame([{
        "run_id": "r", "seed": 100, "policy": "fixed", "edge_id": "edge.market", "sim_time_s": t,
        "coverage": "fresh", "slowdown": t / 1000, "mean_speed_mps": 10,
        "distinct_probes_60s": 2, "sample_age_sim_s": 0, "fixed_queue_ratio": None
    } for t in range(0, 401, 5)])
    truth = pd.DataFrame([{"run_id": "r", "edge_id": "edge.market", "sim_time_s": t,
                           "slowdown_true": 0.8} for t in range(0, 401, 5)])
    return observations, truth


def test_features_do_not_read_future_and_labels_use_future_truth():
    obs, truth = frames()
    data = build_dataset(obs, truth)
    row = data.loc[data.sim_time_s == 60].iloc[0]
    assert row["slowdown_now"] == pytest.approx(0.06)
    assert row["target_120"] == pytest.approx(0.8)
    assert row["target_300"] == pytest.approx(0.8)


def test_truncated_future_is_not_a_training_label():
    obs, truth = frames()
    data = build_dataset(obs, truth)
    assert pd.isna(data.loc[data.sim_time_s == 350, "target_120"].iloc[0])


def test_truth_fields_in_observation_plane_are_rejected():
    obs, truth = frames()
    obs["slowdown_true"] = 0.9
    with pytest.raises(ValueError, match="privileged"):
        build_dataset(obs, truth)


def test_core_grid_is_45_unique_runs_and_seeds_are_held_out():
    grid = experiment_grid(["rain", "block", "procession"], [300, 301, 302, 303, 304])
    assert len(grid) == 45
    assert len({x["run_id"] for x in grid}) == 45
    assert {x["seed"] for x in grid} == {300, 301, 302, 303, 304}


def test_fixture_provenance_is_not_lost_in_dataset_generation():
    obs, truth = frames()
    obs['data_source'] = 'fixture'
    assert build_dataset(obs, truth).data_source.eq('fixture').all()
