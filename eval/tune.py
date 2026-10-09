"""Validation-only first-alert tuning. Does not optimize actual journey outcomes."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
from statistics import median
import pandas as pd
from ml.detect import DetectionEngine
from ml.forecast import ForecastService
from ml.observations import EdgeObservation
from ml.trigger import FirstResponseTrigger
from eval.events import episodes, exposure_hours, score_alerts
from eval.generate import validate_run_metadata


def tune_triggers(observations, truth, *, validation_seeds=(200,201,202), horizon_s=180, method='trend', model_dir=None):
    if observations.empty or not set(observations.seed).issubset(set(validation_seeds)):
        raise ValueError('only declared validation seeds may tune triggers')
    required={'run_id','edge_id','sim_time_s','policy','serving_green','phase_age_s','coverage','slowdown','fresh_probes'}
    if not required.issubset(observations) or not {'run_id','edge_id','sim_time_s','jam_label'}.issubset(truth):
        raise ValueError('missing observation signal-context or independent truth labels')
    if not observations.policy.eq('fixed').all():
        raise ValueError('first-alert tuning requires fixed no-action traces')
    if not truth.jam_label.isin([True,False]).all() or not observations.serving_green.isin([True,False]).all():
        raise ValueError('truth/phase flags must be boolean')
    if observations.duplicated(['run_id','edge_id','sim_time_s']).any() or truth.duplicated(['run_id','edge_id','sim_time_s']).any():
        raise ValueError('duplicate tuning timestamps')
    validate_run_metadata(observations,truth)
    service=ForecastService.from_directory(model_dir) if model_dir else ForecastService()
    if method=='boosting' and not service.models:
        raise ValueError('boosting requires trained artifacts')
    traces=[]
    for (run,edge),group in observations.groupby(['run_id','edge_id']):
        labels=truth[truth.run_id.eq(run)&truth.edge_id.eq(edge)].sort_values('sim_time_s')
        records=group.sort_values('sim_time_s').to_dict('records')
        if labels.empty or not {r['sim_time_s'] for r in records}.issubset(set(labels.sim_time_s)):
            raise ValueError('truth timeline missing tuning rows')
        history=[];trace=[]
        for row in records:
            o=EdgeObservation.from_mapping(row);history.append(o)
            f=service.predict(history,horizon_s,method=method)
            trace.append((o,f,row['serving_green'],row['phase_age_s']))
            history=[sample for sample in history if sample.sim_time_s>=o.sim_time_s-120]
        traces.append((run,edge,trace,episodes(labels,'jam_label')))
    scores=[]
    for policy in ['reactive','predictive']:
        for danger in [.6,.7,.8]:
            for persistence in ([20,30,40] if policy=='reactive' else [10,20,30]):
                alert_list=[];all_jams=[];jam_edges=0
                for run,edge,trace,jams in traces:
                    engine=DetectionEngine(danger=danger,persistence_s=persistence) if policy=='reactive' else FirstResponseTrigger(danger=danger,persistence_s=persistence)
                    first=None
                    for o,f,green,phase_age in trace:
                        if policy=='reactive':
                            state=engine.update(o,serving_green=green,phase_age_s=phase_age)
                            eligible=state.active and state.usable_for_control
                        else:
                            eligible=engine.update(o,f,serving_green=green,phase_age_s=phase_age).eligible
                        if eligible:
                            first=o.sim_time_s;break
                    jam_edges+=bool(jams);all_jams.extend(jams)
                    if first is not None:
                        alert_list.append({'run_id':run,'edge_id':edge,'sim_time_s':first})
                event_score=score_alerts(all_jams,alert_list,sim_hours=exposure_hours(observations),allowed_lead_s=horizon_s)
                missed_edges=len({(event['run_id'],event['edge_id']) for event in event_score['missed_event_details']})
                scores.append({'policy':policy,'danger':danger,'persistence_s':persistence,'run_edge_traces':len(traces),
                               'jam_edges':jam_edges,'alerts':len(alert_list),'false_alert_edges':event_score['false_alerts'],'missed_jam_edges':missed_edges,
                               'median_lead_s':event_score['median_warning_lead_s'],**event_score})
    recommendations={}
    for policy in ['reactive','predictive']:
        candidates=[score for score in scores if score['policy']==policy]
        recommendations[policy]=min(candidates,key=lambda s:(s['false_alert_edges'],s['missed_events'],-(s['median_lead_s'] if s['median_lead_s'] is not None else -1e9)))
    return {'split':'validation_only','validation_seeds':sorted(set(observations.seed)),
            'horizon_s':horizon_s,'method':method,'scores':scores,'recommendations':recommendations,
            'limitation':'First-alert screening only. No proof of controller benefit; compare validation policy runs before freezing.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observations',required=True);p.add_argument('--truth',required=True);p.add_argument('--output',required=True)
    p.add_argument('--method',choices=['trend','persistence','boosting'],default='trend');p.add_argument('--models')
    p.add_argument('--horizon-s',type=int,choices=[120,180,300],default=180)
    a=p.parse_args(argv)
    report=tune_triggers(pd.read_csv(a.observations),pd.read_csv(a.truth),method=a.method,model_dir=a.models,horizon_s=a.horizon_s)
    output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
