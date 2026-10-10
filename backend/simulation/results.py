"""Complete, matched saved-run comparisons. Negative results remain visible."""
import math

MATCH_KEYS=('network_sha256','demand_sha256','execution_sha256','seed','settings','scenario_requested')


def summary(record):
    manifest=record['manifest']; counts=manifest.get('final_counts',{})
    frames=record.get('frames',[])
    return {'run_id':manifest.get('run_id'),'policy':manifest.get('policy'),'complete':manifest.get('complete',False),
            'scheduled':counts.get('scheduled'),'arrived':counts.get('arrived'),
            'mean_journey_s':manifest.get('mean_journey_s'),'mean_travel_s':manifest.get('mean_travel_s'),
            'mean_insertion_delay_s':manifest.get('mean_insertion_delay_s'),'co2_kg':counts.get('co2_kg'),
            'sampled_peak_queued':max((f.get('metrics',{}).get('queued',0) for f in frames),default=None),
            'measurement_source':manifest.get('journey_measurement_source','unavailable')}


def compare_records(response,baseline):
    r,b=response['manifest'],baseline['manifest']
    reply={'api_version':'2.0','available':False,'reason_code':'missing_or_unverified_evidence',
           'baseline':summary(baseline),'response':summary(response),'differences':None,
           'assumptions':['SUMO geometry and demand are not field-calibrated.',
                          'CO2 is unreviewed SUMO fleet-model output, not measured emissions.',
                          'Lifecycle event timestamps have 0.25-second simulation resolution.',
                          'Queue maximum is sampled from saved frames.']}
    if any(k not in r or k not in b for k in MATCH_KEYS): return reply
    if any(r[k]!=b[k] for k in MATCH_KEYS): reply['reason_code']='configuration_or_execution_mismatch'; return reply
    if r.get('scenario_mutated') or b.get('scenario_mutated'): reply['reason_code']='scenario_was_edited'; return reply
    if b.get('policy')!='fixed' or r.get('run_id')==b.get('run_id'):
        reply['reason_code']='distinct_fixed_baseline_required'; return reply
    for manifest in (r,b):
        counts=manifest.get('final_counts',{})
        if not manifest.get('complete') or manifest.get('integrity')!='complete' or counts.get('scheduled')!=counts.get('arrived') or counts.get('collisions')!=0 or counts.get('teleports')!=0:
            reply['reason_code']='incomplete_or_faulted_cohort'; return reply
        for key in ('mean_journey_s','mean_travel_s','mean_insertion_delay_s'):
            value=manifest.get(key)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0: return reply
    if b['final_counts']['scheduled']==0: reply['reason_code']='empty_cohort'; return reply
    reduction=b['mean_journey_s']-r['mean_journey_s']
    bc=b['final_counts'].get('co2_kg'); rc=r['final_counts'].get('co2_kg')
    co2_valid=all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 for v in (bc,rc))
    reply.update(available=True,reason_code='complete_matched_cohorts',differences={
        'journey_reduction_s':reduction,'journey_reduction_pct':100*reduction/b['mean_journey_s'] if b['mean_journey_s'] else None,
        'co2_reduction_kg':bc-rc if co2_valid else None,'co2_reduction_pct':100*(bc-rc)/bc if co2_valid and bc else None})
    return reply
