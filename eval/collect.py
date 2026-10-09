"""Collect finalized run exports; compute metrics from raw trips, not headline fields."""
import argparse
import json
from pathlib import Path
import pandas as pd
from eval.cohort import summarize_cohort, fingerprint
from eval.io import read_trips_csv
from eval.network import summarize_network, summarize_actions, read_events

REQUIRED_METADATA={'run_id','scenario_id','seed','policy','compliance','sensor_mask_id','data_source',
                   'cohort_sha256','network_sha256','incident_sha256','teleported','scheduled_cohort_size'}


def collect_results(root):
    root=Path(root);results=[];errors=[]
    for run in sorted(path for path in root.iterdir() if path.is_dir()):
        try:
            metadata=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
            if not REQUIRED_METADATA.issubset(metadata):
                raise ValueError(f'missing manifest fields {sorted(REQUIRED_METADATA-set(metadata))}')
            if metadata['data_source'] not in {'sumo','fixture'}:
                raise ValueError('run data_source must declare sumo or fixture')
            trips=read_trips_csv(run/'trips.csv')
            if len(trips)!=metadata['scheduled_cohort_size']:
                raise ValueError('trips export does not match scheduled cohort size; preserve pending vehicles')
            metrics=summarize_cohort(trips,teleported=metadata['teleported'],excluded_vehicle_ids=metadata.get('excluded_metric_vehicle_ids',[]))
            audit={field+'_sha256':fingerprint(metadata[field]) if metadata.get(field) is not None else None
                   for field in ['emission_assumptions','comparison_config','probe_assignment']}
            secondary={}
            if (run/'truth.csv').is_file():
                truth=pd.read_csv(run/'truth.csv')
                if 'jam_length_m' in truth:
                    secondary.update(summarize_network(truth,bypass_edges=metadata.get('bypass_edge_ids',[])))
            if (run/'events.jsonl').is_file():
                secondary.update(summarize_actions(read_events(run/'events.jsonl'),run_id=metadata['run_id']))
            results.append({**metadata,'demand_id':metadata.get('demand_id','demand.reference'),**metrics,**audit,**secondary})
        except (OSError,ValueError,KeyError,TypeError) as exc:
            errors.append({'run_id':run.name,'reason':str(exc)})
    return {'results':results,'errors':errors}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(argv);report=collect_results(a.runs)
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.collection.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    if not report['results']:
        raise ValueError('no finalized run exports available; see collection JSON')
    # Nested model/emissions configuration stays in collection JSON, not CSV cells.
    rows=[{k:v for k,v in row.items() if not isinstance(v,(list,dict))} for row in report['results']]
    pd.DataFrame(rows).to_csv(output,index=False)


if __name__=='__main__':
    main()
