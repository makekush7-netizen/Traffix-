import json
import pandas as pd
import pytest
from eval.merge import merge_run_logs


def test_run_metadata_enrichment_and_source_isolation(tmp_path):
    run=tmp_path/'run.fixed';run.mkdir()
    (run/'manifest.json').write_text(json.dumps(dict(run_id='run.fixed',seed=100,policy='fixed',data_source='sumo',scenario_id='rain')))
    pd.DataFrame([dict(run_id='run.fixed',edge_id='e',sim_time_s=0,coverage='unknown',slowdown=None)]).to_csv(run/'observations.csv',index=False)
    pd.DataFrame([dict(run_id='run.fixed',edge_id='e',sim_time_s=0,slowdown_true=.2)]).to_csv(run/'truth.csv',index=False)
    obs,truth=merge_run_logs(tmp_path)
    assert obs.seed.tolist()==[100] and obs.data_source.tolist()==['sumo']
    assert 'slowdown_true' not in obs and 'slowdown_true' in truth
    pd.DataFrame([dict(run_id='wrong',edge_id='e',sim_time_s=0,slowdown_true=.2)]).to_csv(run/'truth.csv',index=False)
    with pytest.raises(ValueError,match='metadata'):
        merge_run_logs(tmp_path)
