import json
import pandas as pd
from eval.fixtures import write_fixture_logs
from eval.generate import build_dataset
from ml.train import train_models
from eval.forecasts import evaluate_forecasts


def test_fixture_pipeline_trains_evaluates_and_retains_provenance(tmp_path):
    write_fixture_logs(tmp_path,seeds=[100,200,300],duration_s=600)
    observations=pd.read_csv(tmp_path/'observations.csv')
    truth=pd.read_csv(tmp_path/'truth.csv')
    data=build_dataset(observations,truth)
    assert data.data_source.eq('fixture').all()
    assert data.forecast_eligible.any()
    models=tmp_path/'models'
    train_models(data,models,train_seeds=[100],validation_seeds=[200],test_seeds=[300],max_iter=10)
    assert json.loads((models/'manifest.json').read_text())['data_source']=='fixture'
    report=evaluate_forecasts(data,models)
    assert report['data_source']=='fixture' and report['horizons']['300']['eligible_rows']>0


def test_fixture_model_never_drives_live_control(tmp_path):
    from tests_helpers import trained_dataset
    from ml.forecast import ForecastService
    from tests.test_forecast import history
    train_models(trained_dataset(),tmp_path,train_seeds=[100],validation_seeds=[200],test_seeds=[300],max_iter=10)
    result=ForecastService.from_directory(tmp_path).predict(history(),180,method='boosting')
    assert not result.usable_for_control and result.reason=='fixture_model_not_for_control'
