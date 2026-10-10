import pytest
from ml.train import train_models
from ml.forecast import ForecastService
from tests_helpers import trained_dataset


def test_mixed_fixture_and_sumo_rows_cannot_be_promoted(tmp_path):
    data=trained_dataset();data.loc[data.seed==100,'data_source']='sumo'
    with pytest.raises(ValueError,match='provenance'):
        train_models(data,tmp_path)


def test_changed_artifact_is_rejected_before_deserialization(tmp_path):
    train_models(trained_dataset(),tmp_path,max_iter=10)
    artifact=tmp_path/'forecast-180.joblib'
    artifact.write_bytes(b'not the trained model')
    with pytest.raises(ValueError,match='checksum'):
        ForecastService.from_directory(tmp_path)


def test_all_horizons_validate_before_any_model_is_written(tmp_path):
    data=trained_dataset();data['target_300']=float('nan')
    with pytest.raises(ValueError):
        train_models(data,tmp_path)
    assert not list(tmp_path.glob('*.joblib'))
