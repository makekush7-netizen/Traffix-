import pytest

def test_selection_uses_validation_scores_only_and_keeps_losing_boosting():
    from eval.lig_analysis import select_forecast
    report=dict(selection_split='validation_only',horizons={str(h):dict(boosting_mae=.3,persistence_mae=.2,trend_mae=.1 if h==180 else .15) for h in [120,180,300]})
    selected=select_forecast(report)
    assert selected['method']=='trend' and selected['horizon_s']==180
    with pytest.raises(ValueError,match='validation'):
        select_forecast({**report,'selection_split':'test_only'})
