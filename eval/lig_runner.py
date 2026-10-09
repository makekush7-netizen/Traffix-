"""Real SUMO LIG export worker. One process owns TraCI; ML receives observations only."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
import re
import time
import xml.etree.ElementTree as ET
import pandas as pd
from backend.harness.engine import HarnessEngine
from eval.cohort import fingerprint, summarize_cohort
from eval.integrity import merge_integrity
from eval.io import import_tripinfo
from eval.lig_registry import load_registry, probe_assignment, FOCUS
from ml.integration import TrafficIntelligence
from ml.observations import ProbeSample

DEMAND={'demand.lig.ordinary':500,'demand.lig.busy':750}
MASKS={'mask.lig.probes','mask.lig.boundary','mask.lig.none'}

def execution_identity(job,model_dir=None,selection=None):
    from ml.artifacts import execution_artifacts
    return fingerprint(dict(configuration=resolve_job(job),artifacts=execution_artifacts(model_dir,selection),
                            runner_version=2,probe_participation=.6,observation_step_s=5))

def resolve_job(job):
    if job.get('scenario_id') not in {'lig.everyday','lig.rain','lig.roadworks','lig.rush'}:
        raise ValueError('unsupported LIG scenario')
    if job.get('sensor_mask_id') not in MASKS:
        raise ValueError('unsupported LIG sensor mask')
    if job.get('data_source')!='sumo':
        raise ValueError('real runner requires sumo source')
    if job.get('demand_id') not in DEMAND or job.get('policy') not in {'fixed','reactive','predictive'}:
        raise ValueError('unsupported demand/policy')
    if not re.fullmatch(r'run\.[A-Za-z0-9_.:-]+',job.get('run_id','')) or type(job.get('seed')) is not int or not 0<=job['seed']<=999999:
        raise ValueError('invalid run/seed')
    if isinstance(job.get('compliance'),bool) or not isinstance(job.get('compliance'),(int,float)) or not 0<=job['compliance']<=1:
        raise ValueError('invalid compliance')
    rng=random.Random(job['seed']+97001)
    start=rng.randrange(180,361,5)
    return dict(profile='conservative',sublane=False,step_s=.25,warmup_s=0,
                demand_end_s=900,horizon_s=1200,max_end_s=2400,
                demand_per_hour=DEMAND[job['demand_id']],incident_start_s=start,
                incident_end_s=start+360,incident_ramp_s=120 if job['scenario_id']=='lig.rain' else 0,
                incident_edge=FOCUS)

class Sampler:
    """Offline truth and permitted sensor channels remain separate even in-process."""
    def __init__(self,run_id,registry,mask,assignment,forecaster=None):
        self.registry=registry;self.mask=mask;self.assignment=set(assignment)
        self.fixed={edge for edge in registry['edges'] if edge!=registry['focus_edge']} if mask!='mask.lig.none' else set()
        self.intelligence=TrafficIntelligence(run_id,{e:r['reference_speed_mps'] for e,r in registry['edges'].items()},
                                             allowed_fixed_edges=self.fixed,forecaster=forecaster)
        self.observations=[];self.truth=[];self.last=None;self.latest=None
        self._jam={};self.forecasts=[];self.detections=[];self.capacity=[]

    def sample(self,conn,t,*,intervention_active=False):
        if self.last==t or t%5:
            return None
        self.last=t
        state=conn.trafficlight.getRedYellowGreenState(self.registry['tls_sumo_id'])
        age=conn.trafficlight.getSpentDuration(self.registry['tls_sumo_id'])
        context={};capacity={}
        for edge,entry in self.registry['edges'].items():
            ids=list(conn.edge.getLastStepVehicleIDs(entry['sumo_id']))
            values=[(v,conn.vehicle.getSpeed(v),conn.vehicle.getLaneID(v)) for v in ids]
            mean=sum(speed for _,speed,_ in values)/len(values) if values else None
            stopped=[v for v,s,_ in values if s<.1]
            occupied={lane:0 for lane in entry['lanes']}
            for v,s,lane in values:
                if s<.1:
                    occupied[lane]+=conn.vehicle.getLength(v)+conn.vehicle.getMinGap(v)
            jam_length=sum(min(length,entry['length_m']) for length in occupied.values())
            queue_ratio=jam_length/(entry['length_m']*entry['lane_count'])
            green=bool(entry['signal_indices']) and any(state[i] in 'Gg' for i in entry['signal_indices'])
            context[edge]=dict(serving_green=green,phase_age_s=age if green else 0)
            if edge in self.fixed:
                capacity[edge]=dict(edge_id=edge,sim_time_s=t,queue_ratio=queue_ratio,vehicle_count=len(ids),source='fixed')
                self.capacity.append(dict(run_id=self.intelligence.run_id,**capacity[edge]))
            if edge in self.fixed and mean is not None:
                self.intelligence.aggregator.add_fixed(edge,t,mean,queue_ratio)
            if self.mask=='mask.lig.probes':
                for v,s,_ in values:
                    if v in self.assignment:
                        self.intelligence.ingest_emulated_probe(ProbeSample(v,edge,t,s,'emulated_probe'))
            slowdown=max(0,min(1,1-mean/entry['reference_speed_mps'])) if mean is not None else None
            jam=self._jam.setdefault(edge,dict(start=None,green_start=None,served=False))
            high=slowdown is not None and slowdown>=.7 and jam_length>=50
            if not high:
                jam.update(start=None,green_start=None,served=False)
            else:
                if jam['start'] is None: jam['start']=t
                if not green or age<5: jam['green_start']=None
                elif jam['green_start'] is None: jam['green_start']=t
                if jam['green_start'] is not None and t-jam['green_start']>=10: jam['served']=True
            label=bool(high and t-jam['start']>=60 and jam['served'])
            self.truth.append(dict(run_id=self.intelligence.run_id,edge_id=edge,sim_time_s=t,
                                   slowdown_true=slowdown,jam_length_m=jam_length,jam_label=label,
                                   vehicle_count=len(ids),queued_count=len(stopped),**context[edge]))
        methods=('persistence','trend','boosting') if self.intelligence.forecaster.models else ('persistence','trend')
        self.latest=self.intelligence.tick(t,context,intervention_active=intervention_active,methods=methods)
        self.latest['fixed_capacity']=capacity
        self.detections.extend(dict(run_id=self.intelligence.run_id,sim_time_s=t,**state) for state in self.latest['detections'].values())
        self.observations.extend(self.latest['log_rows'])
        self.forecasts.extend(dict(run_id=self.intelligence.run_id,sim_time_s=t,**f) for f in self.latest['forecasts'])
        return self.latest

def run_job(job,output_dir,*,model_dir=None,selection=None):
    from scripts.verify_nandani import prepare_environment
    prepare_environment()
    from ml.forecast import ForecastService
    config=resolve_job(job);registry=load_registry();directory=Path(output_dir)
    identity=execution_identity(job,model_dir,selection)
    service=ForecastService.from_directory(model_dir) if model_dir else None
    if job['policy']=='predictive' and (selection is None or service is None):
        raise ValueError('predictive run requires frozen validation selection and genuine models')
    engine=HarnessEngine(run_config=config,requested_run_id=job['run_id'],output_directory=directory)
    started=time.monotonic();lifecycle={};sampler=None;policy=None
    try:
        engine._reset(job['scenario_id'].split('.')[1],job['seed'])
        demand=ET.parse(directory/'demand.rou.xml').getroot()
        vehicles=demand.findall('vehicle')
        lifecycle={v.get('id'):dict(vehicle_id=v.get('id'),status='pending',actual_depart_s=None,arrival_s=None) for v in vehicles}
        assignment=probe_assignment(lifecycle,job['seed'],.6) if job['sensor_mask_id']=='mask.lig.probes' else []
        sampler=Sampler(job['run_id'],registry,job['sensor_mask_id'],assignment,service)
        if job['policy']!='fixed':
            from backend.harness.policy import BoundedPolicy
            policy=BoundedPolicy(job['policy'],registry,selection=selection,compliance=job['compliance'],seed=job['seed'])
            if selection:
                from ml.detect import DetectionEngine
                sampler.intelligence.detector=DetectionEngine(**selection['reactive'])
        conn=engine._conn
        emissions={v.get('id'):conn.vehicletype.getEmissionClass(v.get('id')) for v in demand.findall('vType')}
        while not engine._ended(conn.simulation.getTime()):
            engine._step(publish=False)
            t=conn.simulation.getTime()
            for v in conn.simulation.getDepartedIDList():
                lifecycle[v].update(status='active',actual_depart_s=conn.vehicle.getDeparture(v))
            for v in conn.simulation.getArrivedIDList():
                lifecycle[v].update(status='arrived',arrival_s=t)
            latest=sampler.sample(conn,t,intervention_active=bool(policy and policy.intervened))
            if latest and policy:
                policy.tick(conn,t,latest,sampler.intelligence)
        engine._publish();engine._save()
    finally:
        if engine._conn:
            engine._conn.close();engine._conn=None
    if sampler is None:
        raise RuntimeError('runner did not initialize')
    # SUMO XML is final only after close. Its exact times supersede stepped lifecycle times.
    parsed={v.get('id'):v for v in ET.parse(directory/'trips.xml').getroot().findall('tripinfo')}
    for v,row in lifecycle.items():
        if v in parsed:
            element=parsed[v];depart=float(element.get('depart'));arrival=float(element.get('arrival'))
            row.update(actual_depart_s=depart if depart>=0 else None,arrival_s=arrival if arrival>=0 else None,
                       status='arrived' if arrival>=0 else 'active' if depart>=0 else 'pending')
    pd.DataFrame(lifecycle.values()).to_csv(directory/'lifecycle.csv',index=False)
    trips=import_tripinfo(directory/'demand.rou.xml',directory/'trips.xml',lifecycle_csv=directory/'lifecycle.csv')
    pd.DataFrame([asdict(trip) for trip in trips]).to_csv(directory/'trips.csv',index=False)
    for name,rows in [('observations',sampler.observations),('truth',sampler.truth),('forecasts',sampler.forecasts),('detections',sampler.detections),('capacity',sampler.capacity)]:
        frame=pd.DataFrame(rows)
        for key in ['seed','policy','data_source','scenario_id','demand_id']: frame[key]=job[key]
        frame.to_csv(directory/f'{name}.csv',index=False)
    metrics=summarize_cohort(trips,teleported=engine.teleports)
    common=dict(config=config,signals='imported fixed phases, clearance preserved',
                control=dict(min_green_s=10,max_green_s=40,extension_s=5,downstream_max_queue=.8),
                probe=dict(source='emulated_probe',participation=.6,period_s=5,max_age_s=15))
    manifest={**engine._manifest,**job,'registry':registry,'scheduled_cohort_size':len(trips),
              'teleported':engine.teleports,'collisions':engine.collisions,'integrity_valid':engine.collisions==0 and engine.teleports==0,
              'cohort_sha256':fingerprint([(v.get('id'),v.get('depart'),v.get('type'),v.get('route')) for v in vehicles]),
              'incident_sha256':fingerprint({k:v for k,v in config.items() if k.startswith('incident')}),
              'comparison_config_sha256':fingerprint(common),'probe_assignment_sha256':fingerprint(assignment),
              'emission_assumptions_sha256':fingerprint(emissions),'emission_classes':emissions,
              'probe_assignment':assignment,'probe_source':'emulated_probe' if assignment else 'none',
              'probe_participation':.6 if assignment else 0,'authenticated_phone_uplinks':0,
              'clock':'simulated_seconds','step_s':config['step_s'],'label_step_s':5,
              'max_end_s':config['max_end_s'],'actual_end_s':engine.snapshot()['sim_time_s'],
              'wall_time_s':round(time.monotonic()-started,3),'assumptions':common,
              'policy_selection':selection,'training_eligible':engine.collisions==0 and engine.teleports==0,
              'comparison_config':common,'emission_assumptions':emissions,'execution_sha256':identity,
              'bypass_edge_ids':[edge for edge in registry['edges'] if '.exit.' in edge]}
    manifest=merge_integrity(manifest,metrics)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding='utf-8')
    events=[*engine._events,*(policy.events if policy else [])]
    (directory/'events.json').write_text(json.dumps(events,indent=2,allow_nan=False),encoding='utf-8')
    (directory/'registry.json').write_text(json.dumps(registry,indent=2),encoding='utf-8')
    return manifest

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--models');p.add_argument('--selection')
    args=p.parse_args(argv)
    selection=json.loads(Path(args.selection).read_text(encoding='utf-8')) if args.selection else None
    result=run_job(json.loads(Path(args.job).read_text(encoding='utf-8')),args.output_dir,model_dir=args.models,selection=selection)
    print(json.dumps({k:result[k] for k in ['run_id','scheduled','arrived','active','pending','collisions','teleported','valid','training_eligible','wall_time_s']}))

if __name__=='__main__':
    main()
