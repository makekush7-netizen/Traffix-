"""Offline queue/bypass burden and applied control counts. Missing evidence is null."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd


def summarize_network(truth, *, bypass_edges=(), max_gap_s=10):
    required={'run_id','edge_id','sim_time_s','jam_length_m'}
    if not required.issubset(truth):
        raise ValueError('missing queue truth columns')
    if truth.empty or truth.run_id.nunique()!=1 or truth.duplicated(['edge_id','sim_time_s']).any():
        raise ValueError('network summary needs one nonempty run and unique edge timestamps')
    data=truth.sort_values(['edge_id','sim_time_s']).copy()
    if data.sim_time_s.isna().any():
        raise ValueError('missing network timestamp')
    for column in ['sim_time_s','jam_length_m']:
        finite=data[column].dropna()
        if not np.isfinite(finite).all() or finite.lt(0).any():
            raise ValueError('invalid network time/queue measurement')
    expected=len(set(data.edge_id))*len(set(data.sim_time_s))
    coverage=float(data.jam_length_m.notna().sum()/expected)
    dt=data.groupby('edge_id').sim_time_s.diff().fillna(0)
    complete=coverage==1 and not dt.gt(max_gap_s).any()
    def area(part):
        if part.empty or part.sim_time_s.nunique()<2 or part.jam_length_m.isna().any():
            return None
        intervals=part.groupby('edge_id').sim_time_s.diff().fillna(0)
        if intervals.gt(max_gap_s).any():
            return None
        return float((part.jam_length_m*intervals).sum())
    bypass=data[data.edge_id.isin(set(bypass_edges))]
    bypass_complete=bool(bypass_edges) and set(bypass_edges).issubset(set(bypass.edge_id)) and len(bypass)==len(set(bypass_edges))*len(set(data.sim_time_s))
    total=data.groupby('sim_time_s').jam_length_m.sum(min_count=len(set(data.edge_id)))
    return {'queue_sample_coverage':coverage,'queue_edge_count':len(set(data.edge_id)),
            'peak_total_queue_m':float(total.max()) if complete else None,
            'network_queue_m_s':area(data) if complete else None,
            'bypass_queue_m_s':area(bypass) if bypass_complete else None,
            'peak_bypass_queue_m':float(bypass.groupby('sim_time_s').jam_length_m.sum(min_count=len(set(bypass_edges))).max()) if bypass_complete and bypass.jam_length_m.notna().all() else None,
            'queue_integration_assumption':'right-endpoint samples; only logged edges; gaps above max_gap are unavailable'}


def summarize_actions(events, *, run_id=None):
    seen={};applied={};rejected=0;rerouted=set()
    for wrapper in events:
        event=wrapper.get('event',wrapper)
        if event.get('type')!='control.event':
            continue
        if run_id is not None and event.get('run_id')!=run_id:
            raise ValueError('control event run mismatch')
        payload=event['payload'];action=payload['action'];status=payload['status']
        if status not in {'applied','rejected'}:
            raise ValueError('invalid control status')
        key=(event.get('run_id'),action['action_id'],status)
        if key in seen:
            if seen[key]!=action:
                raise ValueError('duplicate action ID has conflicting payloads')
            continue
        seen[key]=action
        if status=='rejected':
            rejected+=1
        else:
            kind=action['kind'];applied[kind]=applied.get(kind,0)+1
            if kind=='reroute':
                rerouted.add(action['vehicle_id'])
    return {'applied_signal_actions':applied.get('extend_green',0)+applied.get('end_green',0),
            'applied_reroutes':applied.get('reroute',0),'rerouted_vehicle_count':len(rerouted),
            'applied_mode_changes':applied.get('mode_change',0),'rejected_control_actions':rejected}


def read_events(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--truth',required=True);parser.add_argument('--events');parser.add_argument('--bypass-edges',nargs='*',default=[]);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    truth=pd.read_csv(args.truth);report=summarize_network(truth,bypass_edges=args.bypass_edges)
    if args.events:
        report.update(summarize_actions(read_events(args.events),run_id=truth.run_id.iloc[0]))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
