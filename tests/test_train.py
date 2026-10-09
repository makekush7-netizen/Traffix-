import json
import pandas as pd
import pytest
from ml.features import FEATURE_COLUMNS
from ml.train import train_models, split_by_seed
from ml.forecast import ForecastService


def dataset():
    rows = []
    for seed in [100, 200, 300]:
        for i in range(40):
            row = {name: 0.0 for name in FEATURE_COLUMNS}
            row.update(run_id=f"run.{seed}", seed=seed, policy="fixed", edge_id="edge.market", sim_time_s=i*5,
                       slowdown_now=i/100, target_120=min(1, i/100+0.2), target_180=min(1,i/100+0.3), target_300=min(1,i/100+0.5))
            rows.append(row)
    return pd.DataFrame(rows)


def test_whole_seed_split_and_overlap_rejection():
    train, val, test = split_by_seed(dataset(), {100}, {200}, {300})
    assert set(train.seed) == {100}
    assert set(val.seed) == {200}
    assert set(test.seed) == {300}
    with pytest.raises(ValueError):
        split_by_seed(dataset(), {100, 300}, {200}, {300})


def test_trains_three_models_without_test_seed_leakage(tmp_path):
    report = train_models(dataset(), tmp_path, train_seeds={100}, validation_seeds={200}, test_seeds={300})
    assert set(report["horizons"]) == {"120", "180", "300"}
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["train_seeds"] == [100]
    assert manifest["test_seeds"] == [300]
    for h in [120,180,300]:
        assert (tmp_path / f"forecast-{h}.joblib").exists()
    assert ForecastService.from_directory(tmp_path).models.keys() == {120,180,300}
