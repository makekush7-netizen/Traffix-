"""Enrich raw logs from frozen run manifests while preserving the observation plane."""
import argparse
import json
from pathlib import Path
import pandas as pd


def merge_run_logs(root, *, policies=('fixed',)):
    tables={'observations':[],'truth':[]}
    for run in sorted(path for path in Path(root).iterdir() if path.is_dir()):
        manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
        if manifest['policy'] not in policies:
            continue
        required=['run_id','seed','policy','data_source','scenario_id']
        if any(field not in manifest for field in required):
            raise ValueError('missing run metadata')
        manifest.setdefault('demand_id','demand.reference')
        required.append('demand_id')
        if manifest['data_source'] not in {'sumo','fixture'}:
            raise ValueError('unverified run provenance')
        for table in tables:
            frame=pd.read_csv(run/f'{table}.csv')
            if frame.empty:
                raise ValueError(f'empty {table} log')
            for field in required:
                if field in frame and not frame[field].eq(manifest[field]).all():
                    raise ValueError(f'log/manifest metadata mismatch: {field}')
                frame[field]=manifest[field]
            tables[table].append(frame)
    if not tables['observations']:
        raise ValueError('no matching run logs')
    return tuple(pd.concat(tables[table],ignore_index=True) for table in ['observations','truth'])


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--policies',nargs='+',choices=['fixed','reactive','predictive'],default=['fixed'])
    a=p.parse_args(argv);obs,truth=merge_run_logs(a.runs,policies=a.policies)
    output=Path(a.output_dir);output.mkdir(parents=True,exist_ok=True)
    obs.to_csv(output/'observations.csv',index=False);truth.to_csv(output/'truth.csv',index=False)


if __name__=='__main__':
    main()
