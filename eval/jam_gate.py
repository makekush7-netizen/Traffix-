"""Offline hour-six gate: baseline jams through green, then recovers.

All thresholds are initial assumptions to validate against the actual network.
Truth and phase context are offline evidence only, never model inputs.
"""
import argparse
import json
from pathlib import Path
import pandas as pd


def check_baseline_jam(truth, *, slowdown_threshold=.7, min_jam_length_m=50, min_duration_s=60, recovery_s=30, max_gap_s=10, green_evidence_s=10):
    required={'run_id','policy','edge_id','sim_time_s','slowdown_true','jam_length_m','serving_green','phase_age_s'}
    if not required.issubset(truth):
        raise ValueError(f'jam gate missing columns: {sorted(required-set(truth.columns))}')
    if not truth.policy.eq('fixed').all():
        raise ValueError('baseline gate requires fixed no-action run')
    if truth.duplicated(['run_id','edge_id','sim_time_s']).any():
        raise ValueError('duplicate jam-gate rows')
    if not truth.serving_green.isin([True,False]).all():
        raise ValueError('serving_green must be boolean')
    evidence=[]
    for (run,edge),group in truth.groupby(['run_id','edge_id']):
        start=None;green_start=None;green_seen=False;previous=None;event=None;candidate=None;recovery_start=None;last_phase_age=None
        for row in group.sort_values('sim_time_s').to_dict('records'):
            now=float(row['sim_time_s'])
            if previous is not None and now-previous>max_gap_s:
                start=None;green_start=None;green_seen=False;event=None;recovery_start=None
            previous=now
            high=row['slowdown_true']>=slowdown_threshold and row['jam_length_m']>=min_jam_length_m
            if high:
                if start is None:
                    start=now;green_start=None;green_seen=False
                if not row['serving_green'] or row['phase_age_s']<5 or (last_phase_age is not None and row['phase_age_s']<last_phase_age):
                    green_start=None
                elif green_start is None:
                    green_start=now
                if green_start is not None and now-green_start>=green_evidence_s:
                    green_seen=True
                if now-start>=min_duration_s and green_seen:
                    if event is None:
                        event={'run_id':run,'edge_id':edge,'start_s':start,'duration_s':now-start,'recovery_seen':False}
                        evidence.append(event)
                        candidate=event
                    event['duration_s']=now-event['start_s']
                recovery_start=None
            else:
                start=None;green_start=None;green_seen=False;event=None
                if candidate is not None and row['slowdown_true']<=.3 and row['jam_length_m']<min_jam_length_m:
                    recovery_start=now if recovery_start is None else recovery_start
                    if now-recovery_start>=recovery_s:
                        candidate['recovery_seen']=True;candidate['recovery_s']=now
                else:
                    recovery_start=None
            last_phase_age=row['phase_age_s'] if row['serving_green'] else None
    return {'passed':any(e['recovery_seen'] for e in evidence),'jam_seen':bool(evidence),'evidence':evidence,
            'thresholds_unvalidated':{'slowdown':slowdown_threshold,'jam_length_m':min_jam_length_m,'duration_s':min_duration_s,'recovery_s':recovery_s,'green_evidence_s':green_evidence_s}}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--truth',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    result=check_baseline_jam(pd.read_csv(a.truth))
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: jam and recovery observed' if result['passed'] else 'NO GO: baseline jam/recovery not demonstrated')
    return 0 if result['passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
