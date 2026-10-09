"""Independent edge cases for Prakhyat's handoff; does not modify his modules."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


def audit(snapshot, output):
    sys.path.insert(0, str(Path(snapshot).resolve()))
    from eval.compare import compare_results, FROZEN_FIELDS
    from eval.collect import collect_results
    from eval.cohort import Trip
    from ml.integration import TrafficIntelligence
    from ml.forecast import ForecastService
    from ml.observations import EdgeObservation
    import pandas as pd

    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    base=dict(scenario_id='rain',demand_id='demand.reference',seed=300,compliance=.6,
              sensor_mask_id='mask',data_source='sumo',complete=True,valid=True,
              mean_journey_s=100,co2_kg_final=10)
    base.update({field:'same.'+field for field in FROZEN_FIELDS})
    runs=[dict(base,run_id='run.'+policy,policy=policy) for policy in ('fixed','reactive','predictive')]
    planned=[dict(row,seed=seed,run_id=row['run_id']+'.'+str(seed)) for seed in (300,301) for row in runs]
    report=compare_results(runs,expected_jobs=planned)
    denominator=dict(expected_attempted_seeds=2,actual_attempted_seeds=report['summary'][0]['attempted_seeds'],
                     listed_missing_runs=len(report['invalid_runs']))
    collision_root=output/'collision-case';collision_dir=collision_root/'run.collision'
    collision_dir.mkdir(parents=True,exist_ok=True)
    metadata=dict(runs[0],run_id='run.collision',scheduled_cohort_size=1,teleported=0,collisions=2,valid=False)
    (collision_dir/'manifest.json').write_text(json.dumps(metadata),encoding='utf-8')
    pd.DataFrame([asdict(Trip('veh.one',0,0,100,'arrived',co2_mg=1e6))]).to_csv(collision_dir/'trips.csv',index=False)
    collected=collect_results(collision_root)
    collision=dict(input_valid=False,input_collisions=2,output_valid=collected['results'][0]['valid'],
                   output_mean_journey_s=collected['results'][0]['mean_journey_s'])
    runtime=TrafficIntelligence('run.audit',{'edge.market':10})
    empty=runtime.tick(0,{})
    zero=dict(coverage=empty['observations'][0]['coverage'],slowdown=empty['observations'][0]['slowdown'],
              usable_forecasts=sum(row['usable_for_control'] for row in empty['forecasts']))
    history=[EdgeObservation('edge.market',t,'fresh',('phone',),5,.5,2,0,fresh_probes=2) for t in range(0,66,5) if t!=5]
    irregular=ForecastService().predict(history,120)
    cadence=dict(history_span_s=65,max_sample_gap_s=10,usable=irregular.usable_for_control,reason=irregular.reason)
    result=dict(comparison_denominator=denominator,collision_collection=collision,zero_uplinks=zero,
                skipped_boundary_tick=cadence)
    (output/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();audit(args.snapshot,args.output)
