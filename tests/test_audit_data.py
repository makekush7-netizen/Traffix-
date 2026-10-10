import pandas as pd
import pytest
from tests_helpers import trained_dataset
from tests.test_dataset import frames
from ml.train import train_models
from eval.forecasts import evaluate_forecasts
from eval.generate import build_dataset


def test_partially_missing_provenance_cannot_promote_models(tmp_path):
    data=trained_dataset();data['data_source']='sumo';data.loc[0,'data_source']=None
    with pytest.raises(ValueError,match='provenance'):
        train_models(data,tmp_path)


def test_heldout_provenance_must_match_training_manifest(tmp_path):
    data=trained_dataset();train_models(data,tmp_path,max_iter=10)
    data.loc[data.seed.eq(300),'data_source']='sumo'
    with pytest.raises(ValueError,match='provenance'):
        evaluate_forecasts(data,tmp_path)


@pytest.mark.parametrize('field,value',[('policy','predictive'),('seed',300),('data_source','fixture')])
def test_cross_plane_metadata_mismatch_is_rejected(field,value):
    obs,truth=frames();obs['data_source']='sumo';truth[field]=value
    with pytest.raises(ValueError,match='metadata'):
        build_dataset(obs,truth)
