"""Validation-only selection, held-out forecast evidence and matched policy audits."""
import argparse
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import platform
import pandas as pd
from eval.lig_pipeline import prepare_dataset,execute_jobs,SCENARIOS,VALIDATION,TEST
from eval.generate import experiment_grid
from ml.train import train_models
from ml.forecast import ForecastService
from ml.observations import EdgeObservation
from ml.detect import DetectionEngine
from ml.trigger import FirstResponseTrigger
from eval.tune import tune_triggers
from eval.forecasts import evaluate_forecasts
from eval.events import episodes,exposure_hours,score_alerts
from eval.detection import evaluate_detection
from eval.collect import collect_results
from eval.compare import compare_results,markdown_report
from eval.jam_gate import check_baseline_jam

def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def select_forecast(report):
    if report.get('selection_split')!='validation_only': raise ValueError('selection requires validation-only scores')
    choices=[]
    for horizon,scores in report['horizons'].items():
        for method in ['boosting','persistence','trend']:
            value=scores[f'{method}_mae']
            if value is None or not isfinite(value): raise ValueError('invalid validation MAE')
            choices.append((value,int(horizon)!=180,method!='boosting',int(horizon),method))
    mae,_,_,horizon,method=min(choices)
    return dict(selection_split='validation_only',validation_seeds=VALIDATION,method=method,horizon_s=horizon,
                validation_mae=mae,selection_basis='Lowest validation slowdown MAE across all methods/horizons; not journey benefit.')

def fit(runs,data_dir,model_dir):
    data=prepare_dataset(runs,data_dir)
    report=train_models(data,model_dir)
    root=Path(runs);jobs=json.loads((root/'plan.json').read_text(encoding='utf-8'))
    provenance=[]
    for job in jobs:
        path=root/job['run_id']/'manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
        provenance.append(dict(run_id=job['run_id'],manifest_sha256=sha256(path.read_bytes()).hexdigest(),
                               training_eligible=manifest['training_eligible'],collisions=manifest['collisions'],
                               complete=manifest['complete'],network_sha256=manifest['network_sha256'],
                               demand_sha256=manifest['demand_sha256']))
    save(Path(model_dir)/'run-provenance.json',dict(runs=provenance,python_version=platform.python_version(),
         note='All physical SUMO faults retained. Truncated collision-free labels are allowed; unfinished journeys cannot produce gains.'))
    return report

def select(data_dir,model_dir,evidence_dir):
    evidence=Path(evidence_dir)
    validation=json.loads((Path(model_dir)/'validation.json').read_text(encoding='utf-8'))
    chosen=select_forecast(validation)
    obs=pd.read_csv(Path(data_dir)/'observations.csv');truth=pd.read_csv(Path(data_dir)/'truth.csv')
    obs=obs[obs.seed.isin(VALIDATION)];truth=truth[truth.seed.isin(VALIDATION)]
    if set(obs.seed)!=set(VALIDATION): raise ValueError('missing declared validation seeds')
    tuning=tune_triggers(obs,truth,method=chosen['method'],horizon_s=chosen['horizon_s'],model_dir=model_dir)
    for policy in ['reactive','predictive']:
        recommendation=tuning['recommendations'][policy]
        chosen[policy]={k:recommendation[k] for k in ['danger','persistence_s']}
    chosen['model_manifest_sha256']=sha256((Path(model_dir)/'manifest.json').read_bytes()).hexdigest()
    save(evidence/'validation-trigger-scores.json',tuning)
    save(evidence/'selection.json',chosen)
    save(evidence/'validation-baseline-jam.json',check_baseline_jam(truth))
    return chosen

def frozen_warning_scores(obs,truth,selection,models):
    service=ForecastService.from_directory(models);alerts={'reactive':[],'predictive':[]};detections=[]
    for (run,edge),group in obs.groupby(['run_id','edge_id']):
        detector=DetectionEngine(**selection['reactive']);trigger=FirstResponseTrigger(**selection['predictive'])
        history=[];first={'reactive':False,'predictive':False}
        for row in group.sort_values('sim_time_s').to_dict('records'):
            observation=EdgeObservation.from_mapping(row);history.append(observation)
            forecast=service.predict(history,selection['horizon_s'],method=selection['method'])
            detection=detector.update(observation,serving_green=row['serving_green'],phase_age_s=row['phase_age_s'])
            decision=trigger.update(observation,forecast,serving_green=row['serving_green'],phase_age_s=row['phase_age_s'])
            detections.append(dict(run_id=run,edge_id=edge,sim_time_s=row['sim_time_s'],active=detection.active,usable_for_control=detection.usable_for_control))
            for policy,eligible in [('reactive',detection.active and detection.usable_for_control),('predictive',decision.eligible)]:
                if eligible and not first[policy]:
                    alerts[policy].append(dict(run_id=run,edge_id=edge,sim_time_s=row['sim_time_s']));first[policy]=True
            history=[o for o in history if o.sim_time_s>=observation.sim_time_s-120]
    jams=episodes(truth,'jam_label')
    return dict(reactive_first_alert=score_alerts(jams,alerts['reactive'],sim_hours=exposure_hours(obs)),
                predictive_first_alert=score_alerts(jams,alerts['predictive'],sim_hours=exposure_hours(obs),allowed_lead_s=selection['horizon_s']),
                full_timeline_detection=evaluate_detection(pd.DataFrame(detections),truth),
                limitation='First-alert scores on fixed no-action traces; these are not journey gains.')

def heldout(data_dir,model_dir,evidence_dir):
    evidence=Path(evidence_dir);selection=json.loads((evidence/'selection.json').read_text(encoding='utf-8'))
    if sha256((Path(model_dir)/'manifest.json').read_bytes()).hexdigest()!=selection['model_manifest_sha256']:
        raise ValueError('model changed after validation selection')
    data=pd.read_csv(Path(data_dir)/'dataset.csv')
    save(evidence/'test-forecast-scores.json',evaluate_forecasts(data,model_dir))
    obs=pd.read_csv(Path(data_dir)/'observations.csv');truth=pd.read_csv(Path(data_dir)/'truth.csv')
    obs=obs[obs.seed.isin(TEST)];truth=truth[truth.seed.isin(TEST)]
    save(evidence/'test-warning-scores.json',frozen_warning_scores(obs,truth,selection,model_dir))

def policy_plan(seeds):
    return experiment_grid(SCENARIOS,seeds,policies=['reactive','predictive'],sensor_masks=['mask.lig.probes'],
                           demand_ids=['demand.lig.ordinary','demand.lig.busy'])

def policy_report(fixed_runs,response_runs,seeds,evidence_path):
    fixed=collect_results(fixed_runs);response=collect_results(response_runs)
    expected=experiment_grid(SCENARIOS,seeds,policies=['fixed','reactive','predictive'],sensor_masks=['mask.lig.probes'],
                             demand_ids=['demand.lig.ordinary','demand.lig.busy'])
    results=[row for row in fixed['results']+response['results'] if row['seed'] in seeds]
    report=compare_results(results,expected_jobs=expected)
    report['collection_errors']=fixed['errors']+response['errors']
    report['actions']=[]
    for job in policy_plan(seeds):
        try:
            events=json.loads((Path(response_runs)/job['run_id']/'events.json').read_text(encoding='utf-8'))
            report['actions'].append(dict(run_id=job['run_id'],events=events))
        except (OSError,ValueError) as error:
            report['collection_errors'].append(dict(run_id=job['run_id'],reason=f'action_evidence_unavailable: {error}'))
    save(evidence_path,report)
    Path(evidence_path).with_suffix('.md').write_text(markdown_report(report),encoding='utf-8')
    return report

def policies(fixed_runs,response_runs,models,evidence,workers):
    evidence=Path(evidence);selection=evidence/'selection.json'
    # Controller/horizon selection is complete before final test trajectories run.
    frozen=selection.read_bytes()
    execute_jobs(policy_plan(VALIDATION),response_runs,workers=workers,models=models,selection=selection)
    policy_report(fixed_runs,response_runs,VALIDATION,evidence/'validation-policy-comparison.json')
    save(evidence/'policy-freeze.json',dict(selection_sha256=sha256(frozen).hexdigest(),test_seeds=TEST,
          validation_comparison_sha256=sha256((evidence/'validation-policy-comparison.json').read_bytes()).hexdigest(),
          parameters_changed_after_validation=False))
    execute_jobs(policy_plan(VALIDATION+TEST),response_runs,workers=workers,models=models,selection=selection)
    if selection.read_bytes()!=frozen: raise ValueError('selection changed while test ran')
    policy_report(fixed_runs,response_runs,TEST,evidence/'test-policy-comparison.json')

def ablation(response_runs,ablation_runs,models,evidence,workers):
    from eval.ablation import compare_sensor_results
    evidence=Path(evidence)
    jobs=experiment_grid(['lig.roadworks'],TEST,policies=['reactive'],sensor_masks=['mask.lig.boundary'],demand_ids=['demand.lig.ordinary'])
    execute_jobs(jobs,ablation_runs,workers=workers,models=models,selection=evidence/'selection.json')
    baseline=collect_results(ablation_runs);response=collect_results(response_runs)
    probes=[row for row in response['results'] if row['seed'] in TEST and row['scenario_id']=='lig.roadworks'
            and row['policy']=='reactive' and row['demand_id']=='demand.lig.ordinary']
    expected=jobs+experiment_grid(['lig.roadworks'],TEST,policies=['reactive'],sensor_masks=['mask.lig.probes'],demand_ids=['demand.lig.ordinary'])
    report=compare_sensor_results(baseline['results']+probes,baseline_mask='mask.lig.boundary',phone_mask='mask.lig.probes',expected_jobs=expected)
    coverage=[]
    for root,plan in [(ablation_runs,jobs),(response_runs,expected[len(jobs):])]:
        for job in plan:
            frame=pd.read_csv(Path(root)/job['run_id']/'observations.csv')
            focus=frame[frame.edge_id.eq('edge.lig.approach.0')]
            coverage.append(dict(run_id=job['run_id'],seed=job['seed'],sensor_mask_id=job['sensor_mask_id'],
                                  focus_fresh_fraction=float(focus.coverage.eq('fresh').mean()),
                                  focus_two_fresh_probe_fraction=float(focus.fresh_probes.ge(2).mean())))
    report.update(coverage=coverage,probe_source='emulated_probe',authenticated_phone_uplinks=0,
                  interpretation='Sensor-poor approach has no fixed sensor in either mask; simulated boundary capacity detectors remain. Emulated probes are not physical phones.',
                  collection_errors=baseline['errors']+response['errors'])
    save(evidence/'test-sensor-ablation.json',report)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['fit','select','heldout','policies','ablation'])
    p.add_argument('--runs',default='runs/lig-training');p.add_argument('--responses',default='runs/lig-policies')
    p.add_argument('--data',default='runs/lig-data');p.add_argument('--models',default='models/lig-v1')
    p.add_argument('--evidence',default='runs/lig-evidence');p.add_argument('--workers',type=int,default=3)
    a=p.parse_args(argv)
    if a.command=='fit': print(json.dumps(fit(a.runs,a.data,a.models),indent=2))
    elif a.command=='select': print(json.dumps(select(a.data,a.models,a.evidence),indent=2))
    elif a.command=='heldout': heldout(a.data,a.models,a.evidence)
    elif a.command=='policies': policies(a.runs,a.responses,a.models,a.evidence,a.workers)
    else: ablation(a.responses,'runs/lig-ablation',a.models,a.evidence,a.workers)

if __name__=='__main__': main()
