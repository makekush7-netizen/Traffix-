"""Mentor-ready accounting/plots. Empty or incomplete evidence stays explicit."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from eval.cohort import summarize_cohort
from eval.io import read_trips_csv, import_tripinfo
from eval.integrity import merge_integrity


def number(value, unit=''):
    return 'Unavailable' if value is None else f'{value:.2f}{unit}'


def write_run_report(trips, metadata, output_dir, *, observations=None, excluded_vehicle_ids=None):
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    trips=list(trips)
    if excluded_vehicle_ids is None:
        excluded_vehicle_ids=metadata.get('excluded_metric_vehicle_ids',())
    result=merge_integrity(metadata,summarize_cohort(trips,teleported=metadata.get('teleported',0),excluded_vehicle_ids=excluded_vehicle_ids))
    size=metadata.get('scheduled_cohort_size')
    if size is not None and size!=len(trips):
        raise ValueError('trip records do not match declared scheduled cohort size')
    result['cohort_export_verified']=size is not None
    if metadata.get('data_source')=='sumo' and 'teleported' not in metadata:
        result.update(valid=False,mean_journey_s=None,p95_journey_s=None,co2_kg_final=None,teleported=None,
                      invalid_reason='teleport_evidence_missing')
    if metadata.get('data_source')=='sumo' and size is None:
        result.update(valid=False,mean_journey_s=None,p95_journey_s=None,co2_kg_final=None,
                      invalid_reason='scheduled_cohort_size_missing')
    (output/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    pd.DataFrame([asdict(t) for t in trips]).to_csv(output/'trips.csv',index=False)
    fig,ax=plt.subplots(figsize=(6,3))
    names=['pending','active','arrived','removed']
    ax.bar(names,[result[name] for name in names],color=['#94a3b8','#f59e0b','#059669','#dc2626'])
    ax.set(ylabel='Vehicles',title=f"{metadata.get('data_source','unverified')} • whole cohort")
    fig.tight_layout();fig.savefig(output/'cohort.png',dpi=160);plt.close(fig)
    plot_text=''
    if observations is not None and not observations.empty:
        fig,ax=plt.subplots(figsize=(8,3.5))
        for edge,group in observations.groupby('edge_id'):
            group=group.sort_values('sim_time_s')
            values=group.slowdown.where(group.coverage.eq('fresh'))
            ax.plot(group.sim_time_s,values,label=edge)
        ax.set(xlabel='Simulated seconds',ylabel='Observed slowdown proxy',ylim=(0,1),title=f"{metadata.get('data_source','unverified')} • gaps remain missing")
        ax.legend();fig.tight_layout();fig.savefig(output/'observations.png',dpi=160);plt.close(fig)
        plot_text='\n![Observed slowdown](observations.png)\n'
    text=f'''# Run evidence: {metadata.get('run_id','unknown')}

Data source: **{metadata.get('data_source','unverified')}**. These numbers describe this run only.
{'**FIXTURE — not SUMO results. Do not put these numbers in the pitch.**' if metadata.get('data_source')=='fixture' else '**Uncalibrated simulation — not measured real-world benefit.**'}

| Measure | Value |
|---|---:|
| Scheduled cohort | {result['scheduled']} |
| Arrived / active / pending / removed | {result['arrived']} / {result['active']} / {result['pending']} / {result['removed']} |
| Teleported | {result['teleported']} |
| Complete and valid | {result['complete']} / {result['valid']} |
| Mean journey, scheduled departure to arrival | {number(result['mean_journey_s'],' s')} |
| P95 journey | {number(result['p95_journey_s'],' s')} |
| Logged cumulative waiting (not entry delay) | {number(result['total_wait_s'],' s')} |
| Modelled CO2, final whole cohort | {number(result['co2_kg_final'],' kg')} |
| Known CO2 so far (may omit missing records) | {number(result['co2_kg_so_far'],' kg')} |

![Cohort accounting](cohort.png)
{plot_text}
## Interpretation

Journey time includes entry waiting and detours. Completed-only averages are suppressed when any cohort trip is unfinished, removed or teleported. CO2 is SUMO-modelled vehicle emissions with chosen emission classes; it is not a climate-impact measurement or a calibrated India fleet estimate. A paired fixed/reactive/predictive experiment is required before claiming improvement.
'''
    (output/'report.md').write_text(text,encoding='utf-8')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--trips');source.add_argument('--tripinfo')
    p.add_argument('--demand');p.add_argument('--lifecycle');p.add_argument('--metadata',required=True)
    p.add_argument('--observations');p.add_argument('--output-dir',required=True);p.add_argument('--exclude',nargs='*',default=None)
    a=p.parse_args(argv)
    if a.tripinfo and not a.demand:
        p.error('--demand is required with --tripinfo')
    trips=read_trips_csv(a.trips) if a.trips else import_tripinfo(a.demand,a.tripinfo,lifecycle_csv=a.lifecycle)
    metadata=json.loads(Path(a.metadata).read_text(encoding='utf-8'))
    if a.tripinfo:
        metadata.setdefault('scheduled_cohort_size',len(trips))
    observations=pd.read_csv(a.observations) if a.observations else None
    write_run_report(trips,metadata,a.output_dir,observations=observations,excluded_vehicle_ids=a.exclude)


if __name__=='__main__':
    main()
