import pandas as pd
import pytest
from eval.tune import tune_triggers


def test_tuning_refuses_heldout_and_training_seeds():
    for seed in [100,300,42]:
        with pytest.raises(ValueError,match='validation'):
            tune_triggers(pd.DataFrame([{'seed':seed}]),pd.DataFrame())
