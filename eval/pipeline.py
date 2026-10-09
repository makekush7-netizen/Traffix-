"""One-command fixture smoke run of Prakhyat's modules; no traffic claims."""
import argparse
import json
from pathlib import Path
import pandas as pd
from eval.fixtures import write_fixture_logs
from eval.generate import build_dataset
from eval.forecasts import evaluate_forecasts
from eval.report import write_run_report
from eval.cohort import Trip
from eval.tune import tune_triggers
from eval.detection import evaluate_detection
from ml.train import train_models
from ml.integration import TrafficIntelligence
from ml.observations import ProbeSample


def fixture_pipeline(output_dir):
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=True)
    write_fixture_logs(root)
    observations=pd.read_csv(root/'observations.csv');truth=pd.read_csv(root/'truth.csv')
    data=build_dataset(observations,truth);data.to_csv(root/'dataset.csv',index=False)
    train_models(data,root/'models')
    scores=evaluate_forecasts(data,root/'models')
    (root/'forecast-test.json').write_text(json.dumps(scores,indent=2,allow_nan=False),encoding='utf-8')
    val_obs=observations[observations.seed.isin([200,201,202])]
    val_truth=truth[truth.seed.isin([200,201,202])]
    tuned=tune_triggers(val_obs,val_truth)
    tuned['data_source']='fixture'
    (root/'trigger-validation.json').write_text(json.dumps(tuned,indent=2,allow_nan=False),encoding='utf-8')
    run='run.fixture.fixed.300'
    runtime=TrafficIntelligence(run,{'edge.market':10})
    events=[];detections=[]
    for row in observations[observations.run_id.eq(run)].to_dict('records'):
        t=row['sim_time_s']
        if row['coverage']=='fresh' and row['sample_age_sim_s']==0:
            for v in ['veh.fixture.a','veh.fixture.b']:
                runtime.ingest_emulated_probe(ProbeSample(v,'edge.market',t,row['mean_speed_mps'],source='emulated_probe'))
        out=runtime.tick(t,{'edge.market':{'serving_green':t%60<30,'phase_age_s':t%30}},methods=('persistence','trend'))
        events.append(out)
        for state in out['detections'].values():
            detections.append({**state,'run_id':run,'sim_time_s':t})
    (root/'runtime-internal.jsonl').write_text(''.join(json.dumps(event,allow_nan=False)+'\n' for event in events),encoding='utf-8')
    pd.DataFrame(detections).to_csv(root/'detections.csv',index=False)
    detection_scores=evaluate_detection(pd.DataFrame(detections),truth[truth.run_id.eq(run)])
    detection_scores['data_source']='fixture'
    (root/'detection-test.json').write_text(json.dumps(detection_scores,indent=2,allow_nan=False),encoding='utf-8')
    # Deliberately unfinished cohort proves that the report cannot invent a headline.
    trips=[Trip('veh.fixture.a',0,15,100,'arrived',waiting_s=10,co2_mg=1e6),Trip('veh.fixture.b',5,20,None,'active')]
    write_run_report(trips,dict(run_id=run,scenario_id='fixture',seed=300,policy='fixed',data_source='fixture',teleported=0),
                     root/'mentor-report',observations=observations[observations.run_id.eq(run)])
    summary={'data_source':'fixture','software_pipeline':'completed','observation_rows':len(observations),'dataset_rows':len(data),
             'trained_horizons_s':[120,180,300],'test_seeds':scores['test_seeds'],
             'traffic_improvement':None,'real_SUMO_validation':'pending Nandani network, demand and runner',
             'report':'mentor-report/report.md'}
    (root/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    return summary


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',default='artifacts/fixture-demo')
    a=p.parse_args(argv)
    print(json.dumps(fixture_pipeline(a.output_dir),indent=2))


if __name__=='__main__':
    main()
