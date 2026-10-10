"""Paired boundary-only versus phone-probe sensing; same policy and traffic cohort."""
import argparse
import json
from pathlib import Path
from statistics import median
from collections import defaultdict
from eval.compare import value, percentage, validate_pair

FIELDS=('scenario_id','demand_id','seed','policy','compliance','data_source')
SUMMARY=('scenario_id','demand_id','policy','compliance','data_source')


def compare_sensor_results(results, *, baseline_mask, phone_mask, expected_jobs=None):
    if baseline_mask==phone_mask:
        raise ValueError('sensor ablation needs two distinct masks')
    groups=defaultdict(dict)
    for row in results:
        if row['sensor_mask_id'] not in {baseline_mask,phone_mask}:
            continue
        if type(row.get('complete')) is not bool or type(row.get('valid')) is not bool:
            raise ValueError('completion flags must be boolean')
        key=tuple(value(row,field) for field in FIELDS)
        if row['sensor_mask_id'] in groups[key]:
            raise ValueError('duplicate sensor ablation run')
        groups[key][row['sensor_mask_id']]=row
    for job in expected_jobs or []:
        if job['sensor_mask_id'] in {baseline_mask,phone_mask}:
            groups[tuple(value(job,field) for field in FIELDS)]
    pairs=[]
    for key,runs in groups.items():
        verified=validate_pair(list(runs.values()),sensor_ablation=True) if runs else False
        baseline=runs.get(baseline_mask);phones=runs.get(phone_mask)
        valid=bool(verified and baseline and phones and baseline['complete'] and baseline['valid'] and phones['complete'] and phones['valid'])
        co2_valid=valid and bool(baseline.get('emission_assumptions_sha256'))
        pairs.append({**dict(zip(FIELDS,key)),'missing_masks':sorted({baseline_mask,phone_mask}-set(runs)),
                      'valid':valid,'journey_improvement_pct':percentage(baseline.get('mean_journey_s'),phones.get('mean_journey_s')) if valid else None,
                      'co2_improvement_pct':percentage(baseline.get('co2_kg_final'),phones.get('co2_kg_final')) if co2_valid else None})
    summary=[]
    for key in sorted({tuple(row[field] for field in SUMMARY) for row in pairs}):
        group=[row for row in pairs if tuple(row[field] for field in SUMMARY)==key]
        values=[row['journey_improvement_pct'] for row in group if row['journey_improvement_pct'] is not None]
        summary.append({**dict(zip(SUMMARY,key)),'attempted_seeds':len(group),'paired_valid':len(values),'wins':sum(v>0 for v in values),
                        'median_journey_improvement_pct':median(values) if values else None,'min_pct':min(values) if values else None,'max_pct':max(values) if values else None})
    return {'baseline_mask':baseline_mask,'phone_mask':phone_mask,'pairs':pairs,'summary':summary}


def main(argv=None):
    import pandas as pd
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['results','baseline-mask','phone-mask','output']:
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--plan')
    args=parser.parse_args(argv)
    data=pd.read_csv(args.results).astype(object)
    data=data.where(pd.notna(data),None)
    jobs=json.loads(Path(args.plan).read_text(encoding='utf-8')) if args.plan else None
    report=compare_sensor_results(data.to_dict('records'),baseline_mask=args.baseline_mask,phone_mask=args.phone_mask,expected_jobs=jobs)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    pd.DataFrame(report['pairs']).to_csv(path.with_suffix('.pairs.csv'),index=False)
    lines=['# Sensor ablation','','Positive gain means the phone-probe configuration improved the whole-cohort result.','',
           '| Scenario | Demand | Source | Valid / attempted seeds | Wins | Median journey gain % |','|---|---|---|---:|---:|---:|']
    for row in report['summary']:
        gain='Unavailable' if row['median_journey_improvement_pct'] is None else f"{row['median_journey_improvement_pct']:.2f}"
        lines.append(f"| {row['scenario_id']} | {row['demand_id']} | {row['data_source']} | {row['paired_valid']} / {row['attempted_seeds']} | {row['wins']} | {gain} |")
    path.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
