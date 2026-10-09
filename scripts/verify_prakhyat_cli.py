"""Exercise file/CLI boundaries with labelled fixtures; never launches SUMO."""
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import pandas as pd


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'.cache'/'cli-audit'/uuid4().hex
    root.mkdir(parents=True,exist_ok=False)
    fixture=project/'artifacts'/'fixture-demo'
    if not (fixture/'summary.json').is_file():
        raise SystemExit('Run eval.pipeline first; all CLI audit inputs are fixture-only.')
    checks=[]
    def run(module,*args):
        command=[sys.executable,'-m',module,*map(str,args)]
        completed=subprocess.run(command,cwd=project,capture_output=True,text=True)
        (root/(module.replace('.','-')+f'-{len(checks)}.log')).write_text(completed.stdout+completed.stderr,encoding='utf-8')
        if completed.returncode:
            raise RuntimeError(f'{module} failed; inspect {root}')
        checks.append(module)

    obs=pd.read_csv(fixture/'observations.csv');truth=pd.read_csv(fixture/'truth.csv')
    obs[obs.seed.isin([200,201,202])].to_csv(root/'validation-observations.csv',index=False)
    truth[truth.seed.isin([200,201,202])].to_csv(root/'validation-truth.csv',index=False)
    run('eval.generate','dataset','--observations',fixture/'observations.csv','--truth',fixture/'truth.csv','--output',root/'dataset.csv')
    run('ml.train','--dataset',root/'dataset.csv','--output-dir',root/'models')
    run('eval.forecasts','--dataset',root/'dataset.csv','--models',root/'models','--output',root/'forecasts.json')
    run('eval.tune','--observations',root/'validation-observations.csv','--truth',root/'validation-truth.csv','--output',root/'tuning.json')
    run('eval.detection','--detections',fixture/'detections.csv','--truth',fixture/'truth.csv','--output',root/'detection.json')
    runs=root/'runs';jobs=[]
    # Every policy has the same UNFINISHED cohort: gains must stay unavailable.
    for policy,mask in [('fixed','mask.market_gap'),('reactive','mask.market_gap'),('predictive','mask.market_gap'),('predictive','mask.boundary_only')]:
        run_id=f'run.fixture.{policy}.300.{mask}'
        target=runs/run_id;target.mkdir(parents=True)
        job=dict(run_id=run_id,scenario_id='scn.rain_ramp',demand_id='demand.reference',seed=300,policy=policy,compliance=.6,sensor_mask_id=mask,data_source='fixture')
        jobs.append(job)
        metadata={**job,'cohort_sha256':'FIXTURE-demand','network_sha256':'FIXTURE-network','incident_sha256':'FIXTURE-incident',
                  'scheduled_cohort_size':2,'teleported':0,'excluded_metric_vehicle_ids':[],
                  'emission_assumptions':{'fixture_only':True},'comparison_config':{'fixture_only':True},
                  'probe_assignment':{'mask':mask},'bypass_edge_ids':[]}
        (target/'manifest.json').write_text(json.dumps(metadata),encoding='utf-8')
        part_obs=obs[obs.seed.eq(300)].copy();part_truth=truth[truth.seed.eq(300)].copy()
        for frame in [part_obs,part_truth]:
            for key in ['run_id','policy','scenario_id','demand_id']:
                frame[key]=job[key]
        part_obs.to_csv(target/'observations.csv',index=False);part_truth.to_csv(target/'truth.csv',index=False)
        (target/'trips.csv').write_bytes((fixture/'mentor-report'/'trips.csv').read_bytes())
        (target/'events.jsonl').write_text('',encoding='utf-8')
    (root/'policy-plan.json').write_text(json.dumps(jobs[:3]),encoding='utf-8')
    (root/'ablation-plan.json').write_text(json.dumps(jobs[2:]),encoding='utf-8')
    run('eval.collect','--runs',runs,'--output',root/'results.csv')
    collected=json.loads((root/'results.collection.json').read_text(encoding='utf-8'))
    assert not collected['errors'] and len(collected['results'])==4
    pd.DataFrame(collected['results'][:3]).drop(columns=['emission_assumptions','comparison_config','probe_assignment','excluded_metric_vehicle_ids','bypass_edge_ids']).to_csv(root/'policy-results.csv',index=False)
    run('eval.compare','--results',root/'policy-results.csv','--plan',root/'policy-plan.json','--output',root/'comparison.json')
    run('eval.ablation','--results',root/'results.csv','--plan',root/'ablation-plan.json','--baseline-mask','mask.boundary_only','--phone-mask','mask.market_gap','--output',root/'ablation.json')
    fixed=runs/jobs[0]['run_id']
    run('eval.network','--truth',fixed/'truth.csv','--events',fixed/'events.jsonl','--output',root/'network.json')
    run('eval.report','--trips',fixed/'trips.csv','--metadata',fixed/'manifest.json','--observations',fixed/'observations.csv','--output-dir',root/'report')
    run('eval.merge','--runs',runs,'--output-dir',root/'merged')
    comparison=json.loads((root/'comparison.json').read_text(encoding='utf-8'))
    ablation=json.loads((root/'ablation.json').read_text(encoding='utf-8'))
    assert all(row['median_pct'] is None for row in comparison['summary'])
    assert all(row['median_journey_improvement_pct'] is None for row in ablation['summary'])
    result=dict(data_source='fixture',traffic_improvement=None,cli_checks=checks,all_passed=True,output_dir=str(root))
    (root/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
