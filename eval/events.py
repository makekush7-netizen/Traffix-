"""Event matching on independent jam labels. Exposure uses simulated, not wall time."""
from statistics import median
from math import isfinite


def episodes(frame, column, *, max_gap_s=10):
    result=[]
    for (run,edge),group in frame.groupby(['run_id','edge_id']):
        current=None;last=None
        for row in group.sort_values('sim_time_s').to_dict('records'):
            now=float(row['sim_time_s'])
            if not isfinite(now) or now<0:
                raise ValueError('invalid event time')
            if last is not None and now-last>max_gap_s:
                current=None
            if bool(row[column]):
                if current is None:
                    current={'run_id':run,'edge_id':edge,'start_s':now,'end_s':now}
                    result.append(current)
                current['end_s']=now
            else:
                current=None
            last=now
    return result


def exposure_hours(frame):
    # A run's network clock counts once, regardless of how many edge traces it has.
    return sum(float(group.sim_time_s.max()-group.sim_time_s.min())/3600 for _,group in frame.groupby('run_id'))


def score_alerts(jams, alerts, *, sim_hours, allowed_lead_s=0):
    matched={};false=[];duplicate=0
    for alert in sorted(alerts,key=lambda a:(a['run_id'],a['edge_id'],a['sim_time_s'])):
        candidates=[i for i,event in enumerate(jams) if event['run_id']==alert['run_id'] and event['edge_id']==alert['edge_id']
                    and event['start_s']-allowed_lead_s<=alert['sim_time_s']<=event['end_s']]
        unused=[i for i in candidates if i not in matched]
        if unused:
            matched[unused[0]]=alert
        elif candidates:
            duplicate+=1
        else:
            false.append(alert)
    leads=[jams[i]['start_s']-alert['sim_time_s'] for i,alert in matched.items()]
    missed=[event for i,event in enumerate(jams) if i not in matched]
    return {'jam_events':len(jams),'warning_events':len(alerts),'matched_events':len(matched),'missed_events':len(missed),
            'missed_event_rate':len(missed)/len(jams) if jams else None,'false_alerts':len(false),'duplicate_alerts':duplicate,
            'exposure_sim_hours':sim_hours,'false_alerts_per_sim_hour':len(false)/sim_hours if sim_hours>0 else None,
            'median_warning_lead_s':median(leads) if leads else None,
            'median_detection_delay_s':median([max(0,-lead) for lead in leads]) if leads else None,
            'unmatched_alerts':false,'missed_event_details':missed}
