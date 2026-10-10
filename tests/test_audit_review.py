import numpy as np
import pandas as pd
import pytest
from eval.tune import tune_triggers
from eval.network import summarize_network
from eval.compare import compare_results, markdown_report
from ml.forecast import ForecastService
from tests.test_compare import result
from tests.test_audit_runtime import obs


@pytest.mark.parametrize('field,value',[('seed',300),('policy','predictive'),('data_source','fixture')])
def test_tuning_rejects_contradictory_truth_metadata(field,value):
    observations=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=0,seed=200,policy='fixed',data_source='sumo',serving_green=True,phase_age_s=10,coverage='fresh',slowdown=.9,distinct_probes_60s=2,fresh_probes=2)])
    truth=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=0,jam_label=True,**{field:value})])
    with pytest.raises(ValueError,match='metadata'):
        tune_triggers(observations,truth)


def test_network_rejects_missing_timestamp():
    data=pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=t,jam_length_m=q) for t,q in [(0,10),(5,20),(None,30)]])
    with pytest.raises(ValueError,match='time'):
        summarize_network(data)


def test_policy_markdown_identifies_demand_level():
    report=compare_results([result('fixed',100),result('reactive',80),result('predictive',70)])
    text=markdown_report(report)
    assert '| Demand |' in text and 'demand.reference' in text


def test_nonfinite_model_prediction_is_unavailable():
    class BrokenModel:
        def predict(self,x):
            return np.array([np.nan])
    service=ForecastService({120:BrokenModel()},data_source='sumo')
    forecast=service.predict([obs(t,.5) for t in range(0,61,5)],120,method='boosting')
    assert forecast.predicted_slowdown is None and not forecast.usable_for_control


def test_selected_fixed_speed_keeps_its_own_measurement_age():
    from ml.observations import ObservationAggregator, ProbeSample
    sensor=ObservationAggregator({'e':10},allowed_fixed_edges=['e'])
    sensor.add_fixed('e',0,1)
    sensor.add_probe(ProbeSample('v','e',10,8))
    output=sensor.snapshot('e',10)
    assert output.mean_speed_mps==1 and output.sample_age_sim_s==10


def test_bad_runtime_configuration_does_not_consume_tick():
    from ml.integration import TrafficIntelligence
    runtime=TrafficIntelligence('r',{'e':10})
    with pytest.raises(ValueError):
        runtime.tick(0,{},methods=('invalid',))
    with pytest.raises(ValueError):
        runtime.tick(0,{'e':{'serving_green':'false','phase_age_s':10}})
    assert runtime.last_tick is None and not runtime.history['e']
    assert runtime.tick(0,{})['sim_time_s']==0


def test_merge_enriches_and_checks_demand_id(tmp_path):
    import json
    from eval.merge import merge_run_logs
    run=tmp_path/'r';run.mkdir()
    metadata=dict(run_id='r',seed=100,policy='fixed',data_source='sumo',scenario_id='rain',demand_id='demand.high')
    (run/'manifest.json').write_text(json.dumps(metadata))
    for name in ['observations','truth']:
        pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=0)]).to_csv(run/f'{name}.csv',index=False)
    observation,truth=merge_run_logs(tmp_path)
    assert observation.demand_id.tolist()==truth.demand_id.tolist()==['demand.high']
    pd.DataFrame([dict(run_id='r',edge_id='e',sim_time_s=0,demand_id='wrong')]).to_csv(run/'truth.csv',index=False)
    with pytest.raises(ValueError,match='metadata'):
        merge_run_logs(tmp_path)
