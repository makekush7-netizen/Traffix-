"""Paired policy comparisons; preserve missing, invalid and negative outcomes."""
from collections import defaultdict
import argparse
import json
from math import isfinite
from pathlib import Path
from statistics import median

PAIR_FIELDS=('scenario_id','demand_id','seed','compliance','sensor_mask_id','data_source')
SUMMARY_FIELDS=('scenario_id','demand_id','compliance','sensor_mask_id','data_source')
FROZEN_FIELDS=('cohort_sha256','metric_cohort_sha256','excluded_vehicle_ids_sha256','network_sha256',
               'incident_sha256','comparison_config_sha256','probe_assignment_sha256','emission_assumptions_sha256')


def value(row,field):
    return row.get(field,'demand.reference' if field=='demand_id' else 'sumo' if field=='data_source' else None)


def validate_pair(runs, *, sensor_ablation=False):
    # Fixed labels predate controller selection; responding policies must share
    # the same resolved execution/model/selection identity when it is declared.
    responding=[row for row in runs if row.get('policy') in {'reactive','predictive'}]
    identities={row.get('execution_sha256') for row in responding}
    if not sensor_ablation and any(identities) and len(identities)>1:
        raise ValueError('mismatched response execution identity in paired comparison')
    for field in FROZEN_FIELDS:
        if sensor_ablation and field=='probe_assignment_sha256':
            continue
        fingerprints={row.get(field) for row in runs}
        if len(fingerprints)>1:
            raise ValueError(f'mismatched {field} in paired comparison')
    return all(row.get(field) not in {None,''} for row in runs for field in FROZEN_FIELDS
               if field!='emission_assumptions_sha256' and not (sensor_ablation and field=='probe_assignment_sha256'))


def percentage(reference,value):
    if reference is None or value is None or reference<=0 or not all(isfinite(float(v)) for v in [reference,value]):
        return None
    return 100*(reference-value)/reference


def compare_results(results, *, expected_jobs=None):
    groups=defaultdict(dict); invalid=[]
    for r in results:
        if not isinstance(r.get('complete'), bool) or not isinstance(r.get('valid'), bool):
            raise ValueError('complete and valid must be boolean values, not strings')
        if r['policy'] not in {'fixed','reactive','predictive'}:
            raise ValueError('unknown policy')
        key=tuple(value(r,k) for k in PAIR_FIELDS)
        if r["policy"] in groups[key]:
            raise ValueError("duplicate policy run for paired scenario")
        groups[key][r["policy"]]=r
        if not r["complete"] or not r["valid"]:
            invalid.append({"run_id":r["run_id"],"reason":"incomplete_or_invalid"})
    for job in expected_jobs or []:
        key=tuple(value(job,k) for k in PAIR_FIELDS)
        if job['policy'] not in groups[key]:
            invalid.append({'run_id':job['run_id'],'reason':'missing_requested_run'})
    pairs=[]
    for key,runs in groups.items():
        verified=validate_pair(list(runs.values())) if runs else False
        pair=dict(zip(PAIR_FIELDS,key));pair['frozen_configuration_verified']=verified
        def metric(policy,name):
            r=runs.get(policy)
            if name=='co2_kg_final' and r and not r.get('emission_assumptions_sha256'):
                return None
            return r.get(name) if verified and r and r["complete"] and r["valid"] else None
        for name,a,b,metricname in [
            ("reactive_vs_fixed_pct","fixed","reactive","mean_journey_s"),
            ("predictive_vs_fixed_pct","fixed","predictive","mean_journey_s"),
            ("predictive_vs_reactive_pct","reactive","predictive","mean_journey_s"),
            ("predictive_co2_vs_fixed_pct","fixed","predictive","co2_kg_final")]:
            pair[name]=percentage(metric(a,metricname),metric(b,metricname))
        pair["missing_policies"]=sorted({"fixed","reactive","predictive"}-set(runs))
        pairs.append(pair)
    summary=[]
    scenarios={tuple(p[k] for k in SUMMARY_FIELDS) for p in pairs}
    for key in sorted(scenarios):
        matching=[p for p in pairs if tuple(p[k] for k in SUMMARY_FIELDS)==key]
        for metric in ["reactive_vs_fixed_pct","predictive_vs_fixed_pct","predictive_vs_reactive_pct","predictive_co2_vs_fixed_pct"]:
            values=[p[metric] for p in matching if p[metric] is not None]
            summary.append({**dict(zip(SUMMARY_FIELDS,key)),"metric":metric,
                            "paired_valid":len(values),"attempted_seeds":len(matching),"wins":sum(v>0 for v in values),
                            "median_pct":median(values) if values else None,"min_pct":min(values) if values else None,"max_pct":max(values) if values else None})
    return {"pairs":pairs,"summary":summary,"invalid_runs":invalid}


def markdown_report(report):
    lines=['# Paired policy evidence','','Positive percentages mean improvement; negative percentages mean worse performance.','',
           'Missing, incomplete or invalid runs cannot produce a gain. Supply the expected plan to count entirely missing seeds.','',
           '| Scenario | Demand | Source | Compliance | Sensor mask | Metric | Valid / attempted seeds | Wins | Median % | Range % |',
           '|---|---|---|---:|---|---|---:|---:|---:|---:|']
    def fmt(value):
        return 'Unavailable' if value is None else f'{value:.2f}'
    for row in report['summary']:
        lines.append(f"| {row['scenario_id']} | {row['demand_id']} | {row['data_source']} | {row['compliance']} | {row['sensor_mask_id']} | {row['metric']} | {row['paired_valid']} / {row['attempted_seeds']} | {row['wins']} | {fmt(row['median_pct'])} | {fmt(row['min_pct'])} to {fmt(row['max_pct'])} |")
    lines.extend(['','## Missing or invalid runs',''])
    lines.extend(f"- {row['run_id']}: {row['reason']}" for row in report['invalid_runs'])
    if not report['invalid_runs']:
        lines.append('None in the supplied results/expected plan.')
    lines.extend(['','Prediction benefit is predictive versus reactive journey time. Forecast MAE alone is not evidence of traffic benefit. Modelled CO2 uses the declared emission assumptions.',''])
    return '\n'.join(lines)


def main(argv=None):
    import pandas as pd
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results",required=True); p.add_argument("--output",required=True)
    p.add_argument('--plan',help='Expected job JSON; retains entirely missing seeds')
    a=p.parse_args(argv)
    data=pd.read_csv(a.results)
    data=data.astype(object).where(pd.notna(data),None)
    plan=json.loads(Path(a.plan).read_text(encoding='utf-8')) if a.plan else None
    report=compare_results(data.to_dict("records"),expected_jobs=plan)
    output=Path(a.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    output.with_suffix('.md').write_text(markdown_report(report),encoding='utf-8')
    pd.DataFrame(report['pairs']).to_csv(output.with_suffix('.pairs.csv'),index=False)


if __name__=="__main__":
    main()
