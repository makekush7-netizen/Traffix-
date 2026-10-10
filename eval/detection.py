"""Score detection against independently logged truth labels on the full timeline."""
import argparse
import json
from pathlib import Path
import pandas as pd
from eval.forecasts import confusion
from eval.events import episodes, exposure_hours, score_alerts


def evaluate_detection(detections, truth):
    key=['run_id','edge_id','sim_time_s']
    if not set(key+['active','usable_for_control']).issubset(detections) or not set(key+['jam_label']).issubset(truth):
        raise ValueError('missing detection/truth columns')
    if detections.duplicated(key).any() or truth.duplicated(key).any():
        raise ValueError('duplicate detection/truth timestamps')
    for table,column in [(detections,'active'),(detections,'usable_for_control'),(truth,'jam_label')]:
        if not table[column].isin([True,False]).all():
            raise ValueError('labels/flags must be boolean')
    joined=truth[key+['jam_label']].merge(detections[key+['active','usable_for_control']],on=key,how='left')
    if joined.empty:
        raise ValueError('no truth labels')
    available=joined.usable_for_control.fillna(False).astype(bool)
    prediction=joined.active.fillna(False).astype(bool) & available
    report=confusion(joined.jam_label.to_numpy(),prediction.to_numpy())
    report.update(rows=len(joined),coverage_fraction=float(available.mean()),missing_detection_rows=int(joined.active.isna().sum()))
    joined['warning']=prediction
    jams=episodes(joined,'jam_label')
    alerts=[{'run_id':event['run_id'],'edge_id':event['edge_id'],'sim_time_s':event['start_s']} for event in episodes(joined,'warning')]
    report.update(score_alerts(jams,alerts,sim_hours=exposure_hours(joined)))
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--detections',required=True);p.add_argument('--truth',required=True);p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    report=evaluate_detection(pd.read_csv(a.detections),pd.read_csv(a.truth))
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
