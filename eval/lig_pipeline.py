"""Resumable subprocess batches and frozen LIG data/selection exports."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
from eval.generate import experiment_grid, build_dataset
from eval.merge import merge_run_logs

SCENARIOS=['lig.everyday','lig.rain','lig.roadworks']
TRAIN=list(range(100,108));VALIDATION=list(range(200,203));TEST=list(range(300,305))

def training_plan():
    return experiment_grid(SCENARIOS,TRAIN+VALIDATION+TEST,policies=['fixed'],
                           sensor_masks=['mask.lig.probes'],demand_ids=['demand.lig.ordinary','demand.lig.busy'])

def execute_jobs(jobs,root,*,workers=3,models=None,selection=None):
    """Threads manage child processes only. Each child is its own sole TraCI owner."""
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    if workers not in [1,2,3,4]: raise ValueError('workers must be 1 to 4')
    (root/'plan.json').write_text(json.dumps(jobs,indent=2),encoding='utf-8')
    def execute(job):
        folder=root/job['run_id'];manifest=folder/'manifest.json'
        required=['observations.csv','truth.csv','trips.csv','lifecycle.csv','events.json','sumo.log']
        if manifest.exists() and all((folder/name).is_file() for name in required):
            saved=json.loads(manifest.read_text(encoding='utf-8'))
            if any(saved.get(k)!=v for k,v in job.items()): raise ValueError('resume job mismatch')
            return saved
        folder.mkdir(exist_ok=False)
        (folder/'job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
        cmd=[sys.executable,'-m','eval.lig_runner','--job',str((folder/'job.json').resolve()),'--output-dir',str(folder.resolve())]
        if models: cmd+=['--models',str(Path(models).resolve())]
        if selection: cmd+=['--selection',str(Path(selection).resolve())]
        result=subprocess.run(cmd,capture_output=True,text=True,check=False)
        (folder/'runner.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode: raise RuntimeError(f"{job['run_id']} failed: {folder/'runner.log'}")
        saved=json.loads(manifest.read_text(encoding='utf-8'))
        if any(saved.get(k)!=v for k,v in job.items()) or not all((folder/name).is_file() for name in required):
            raise RuntimeError('runner export/job mismatch')
        return saved
    results=[];failures=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(execute,job):job for job in jobs}
        for task in as_completed(tasks):
            job=tasks[task]
            try:
                result=task.result();results.append(result)
                print(json.dumps({k:result[k] for k in ['run_id','valid','training_eligible','scheduled','arrived','collisions','wall_time_s']}),flush=True)
            except Exception as error:
                failures.append(dict(run_id=job['run_id'],error=str(error)))
                print(json.dumps(failures[-1]),flush=True)
            (root/'batch-status.json').write_text(json.dumps(dict(completed=len(results),failures=failures,requested=len(jobs)),indent=2),encoding='utf-8')
    if failures: raise RuntimeError(f'{len(failures)} runner failures; inspect batch-status.json')
    return results

def prepare_dataset(root,output):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    jobs=json.loads((root/'plan.json').read_text(encoding='utf-8'))
    accepted=[];excluded=[]
    for job in jobs:
        folder=root/job['run_id'];manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        if manifest['training_eligible']: accepted.append(folder)
        else: excluded.append(dict(run_id=job['run_id'],seed=job['seed'],scenario_id=job['scenario_id'],demand_id=job['demand_id'],reasons=manifest['invalid_reasons']))
    (output/'data-integrity.json').write_text(json.dumps(dict(requested=len(jobs),accepted=len(accepted),excluded=excluded),indent=2),encoding='utf-8')
    obs,truth=merge_run_logs(root,run_dirs=accepted)
    obs.to_csv(output/'observations.csv',index=False);truth.to_csv(output/'truth.csv',index=False)
    data=build_dataset(obs,truth)
    data.to_csv(output/'dataset.csv',index=False)
    return data

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['training','dataset','execute'])
    p.add_argument('--runs',default='runs/lig-training');p.add_argument('--output',default='runs/lig-data')
    p.add_argument('--workers',type=int,default=3);p.add_argument('--plan');p.add_argument('--models');p.add_argument('--selection')
    a=p.parse_args(argv)
    if a.command=='dataset': prepare_dataset(a.runs,a.output)
    else:
        jobs=training_plan() if a.command=='training' else json.loads(Path(a.plan).read_text(encoding='utf-8'))
        execute_jobs(jobs,a.runs,workers=a.workers,models=a.models,selection=a.selection)

if __name__=='__main__': main()
