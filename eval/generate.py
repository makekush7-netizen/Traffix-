"""Offline causal labels and batch jobs. Existing backend owns policy/SUMO execution."""
from hashlib import sha256
from itertools import product
import argparse
import json
from pathlib import Path
import subprocess
import re
import pandas as pd
import numpy as np
from ml.observations import EdgeObservation
from ml.features import build_features
from ml.forecast import HORIZONS, ForecastService, validate_label_step


def validate_run_metadata(observations, truth):
    for run,group in observations.groupby('run_id'):
        matching=truth[truth.run_id.eq(run)]
        if matching.empty:
            raise ValueError('missing truth run metadata/timeline')
        for field in ['seed','policy','data_source','scenario_id','demand_id']:
            if field in group:
                if group[field].isna().any() or group[field].nunique()!=1:
                    raise ValueError(f'observation run metadata changed: {field}')
                if field in matching and not matching[field].eq(group[field].iloc[0]).all():
                    raise ValueError(f'cross-plane run metadata mismatch: {field}')


def build_dataset(observations, truth, *, step_s=5):
    step_s=validate_label_step(step_s)
    forbidden = {"slowdown_true","jam_length_m","future_incident","next_incident_s","target_120","target_180","target_300"}
    if forbidden.intersection(observations.columns):
        raise ValueError("privileged truth/future fields in observation plane")
    obs_required = {"run_id","seed","policy","edge_id","sim_time_s","coverage","slowdown"}
    truth_required = {"run_id","edge_id","sim_time_s","slowdown_true"}
    if not obs_required.issubset(observations.columns) or not truth_required.issubset(truth.columns):
        raise ValueError("missing observation or truth columns")
    if observations.duplicated(["run_id","edge_id","sim_time_s"]).any() or truth.duplicated(["run_id","edge_id","sim_time_s"]).any():
        raise ValueError("duplicate timestamps")
    validate_run_metadata(observations,truth)
    labels = {(r,e):g.set_index("sim_time_s")["slowdown_true"] for (r,e),g in truth.groupby(["run_id","edge_id"])}
    rows = []
    gate = ForecastService(label_step_s=step_s)
    for (run,edge),group in observations.groupby(["run_id","edge_id"]):
        if group.seed.nunique()!=1 or group.policy.nunique()!=1:
            raise ValueError("run metadata changed within stream")
        history = []
        target_series = labels.get((run,edge),pd.Series(dtype=float))
        for record in group.sort_values("sim_time_s").to_dict("records"):
            history.append(EdgeObservation.from_mapping(record))
            now = history[-1].sim_time_s
            row = {"run_id":run,"edge_id":edge,"seed":int(record["seed"]),"policy":record["policy"],"sim_time_s":now,**build_features(history)}
            row["data_source"] = record.get("data_source", "unverified_external_logs")
            row['label_step_s']=step_s
            row['forecast_eligible'] = gate.predict(history,120,method='persistence').usable_for_control
            for field in ["scenario_id", "demand_id", "fresh_probes"]:
                if field in record:
                    row[field] = record[field]
            for h in HORIZONS:
                times = [now+h-offset for offset in range(0,30,step_s)]
                values = target_series.reindex(times)
                if values.notna().all():
                    if not values.between(0,1).all():
                        raise ValueError("invalid truth slowdown")
                    row[f"target_{h}"] = float(values.mean())
                else:
                    row[f"target_{h}"] = np.nan
            rows.append(row)
            history = [o for o in history if o.sim_time_s >= now-120]
    return pd.DataFrame(rows)


def experiment_grid(scenarios, seeds, *, policies=("fixed","reactive","predictive"), compliance_values=(0.6,), sensor_masks=("mask.market_gap",), demand_ids=('demand.reference',)):
    rows=[]
    for scenario,seed,policy,compliance,mask,demand in product(scenarios,seeds,policies,compliance_values,sensor_masks,demand_ids):
        if policy not in {"fixed","reactive","predictive"} or not 0<=compliance<=1:
            raise ValueError("invalid policy/compliance")
        suffix=sha256(f"{scenario}|{seed}|{policy}|{compliance}|{mask}|{demand}".encode()).hexdigest()[:10]
        rows.append({"run_id":f"run.{scenario}.{policy}.{seed}.{suffix}","scenario_id":scenario,"seed":int(seed),"policy":policy,"compliance":compliance,"sensor_mask_id":mask,'data_source':'sumo','demand_id':demand})
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    dataset=commands.add_parser("dataset")
    dataset.add_argument("--observations",required=True)
    dataset.add_argument("--truth",required=True)
    dataset.add_argument("--output",required=True)
    grid=commands.add_parser("plan")
    grid.add_argument("--scenarios",nargs="+",default=["rain_ramp","market_block","procession"])
    grid.add_argument("--seeds",nargs="+",type=int,default=list(range(300,305)))
    grid.add_argument('--policies',nargs='+',choices=['fixed','reactive','predictive'],default=['fixed','reactive','predictive'])
    grid.add_argument('--compliance-values',nargs='+',type=float,default=[.6])
    grid.add_argument('--sensor-masks',nargs='+',default=['mask.market_gap'])
    grid.add_argument('--demand-ids',nargs='+',default=['demand.reference'])
    grid.add_argument("--output",required=True)
    execute=commands.add_parser("execute")
    execute.add_argument("--plan",required=True)
    execute.add_argument("--output-dir",required=True)
    execute.add_argument("--runner",nargs=argparse.REMAINDER,required=True,help="Command receives --job <json> --output-dir <dir>; no shell interpolation")
    args=parser.parse_args(argv)
    if args.command=="dataset":
        output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
        build_dataset(pd.read_csv(args.observations),pd.read_csv(args.truth)).to_csv(output,index=False)
    elif args.command=="plan":
        output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(experiment_grid(args.scenarios,args.seeds,policies=args.policies,compliance_values=args.compliance_values,sensor_masks=args.sensor_masks,demand_ids=args.demand_ids),indent=2)+"\n",encoding="utf-8")
    else:
        if not args.runner:
            parser.error("provide the team's real runner after --runner")
        root=Path(args.output_dir); root.mkdir(parents=True,exist_ok=True)
        for job in json.loads(Path(args.plan).read_text(encoding="utf-8")):
            if not re.fullmatch(r'run\.[A-Za-z0-9_.:-]+', job.get('run_id','')):
                raise ValueError('unsafe run_id')
            target=root/job["run_id"]; target.mkdir(exist_ok=False)
            jobpath=target/"job.json"; jobpath.write_text(json.dumps(job,indent=2),encoding="utf-8")
            completed=subprocess.run([*args.runner,"--job",str(jobpath.resolve()),"--output-dir",str(target.resolve())],capture_output=True,text=True,check=False)
            (target/"runner.log").write_text(completed.stdout+completed.stderr,encoding="utf-8")
            if completed.returncode:
                raise RuntimeError(f"runner failed for {job['run_id']}; see {target/'runner.log'}")
            required=['manifest.json','observations.csv','truth.csv','trips.csv']
            missing=[name for name in required if not (target/name).is_file()]
            if missing:
                raise RuntimeError(f"runner produced missing exports for {job['run_id']}: {missing}")
            manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
            if any(manifest.get(key)!=value for key,value in job.items()):
                raise RuntimeError('runner manifest does not match requested job')
            for name in required[1:]:
                pd.read_csv(target/name, nrows=1)


if __name__=="__main__":
    main()
