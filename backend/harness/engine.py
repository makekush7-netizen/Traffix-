"""Single-thread SUMO owner for the real-road visual harness."""
from concurrent.futures import Future
from collections import deque
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import random
import threading
import time
import uuid
import xml.etree.ElementTree as ET

DATA = Path(__file__).parent / 'data'
ROOT = Path(__file__).resolve().parents[2]
WORLD = json.loads((DATA / 'world.json').read_text(encoding='utf-8'))
SCENARIOS = {
    'everyday': dict(name='Everyday flow', description='500 vehicles/hour synthetic arrivals; bounded cohort drain.', demand=500, incident=None),
    'rush': dict(name='Evening rush', description='Higher arrivals meet fixed signal plans.', demand=3400, incident=None),
    'rain': dict(name='Monsoon slowdown', description='Rush demand; reduced speeds around the junction.', demand=3400, incident='rain'),
    'roadworks': dict(name='Curbside obstruction', description='A narrowed approach exposes queue spillback.', demand=3400, incident='obstruction'),
}
TYPES = {
    'car': dict(vClass='passenger', length='4.3', width='1.75', accel='2.4', decel='4.5', maxSpeed='13.9', minGap='2.0'),
    'motorcycle': dict(vClass='motorcycle', length='2.0', width='.7', accel='3.2', decel='5.0', maxSpeed='13.9', minGap='1.0', minGapLat='.25', latAlignment='arbitrary'),
    'auto': dict(vClass='passenger', length='2.7', width='1.4', accel='1.9', decel='4.0', maxSpeed='10', minGap='1.4', minGapLat='.35', latAlignment='arbitrary'),
    'erickshaw': dict(vClass='passenger', length='2.8', width='1.2', accel='1.3', decel='3.5', maxSpeed='7', minGap='1.2', minGapLat='.3', latAlignment='arbitrary'),
    'bus': dict(vClass='bus', length='10.5', width='2.5', accel='1.1', decel='3.5', maxSpeed='11', minGap='2.5'),
    'delivery': dict(vClass='delivery', length='5.2', width='1.9', accel='1.8', decel='4', maxSpeed='12', minGap='2'),
}


class HarnessEngine:
    def __init__(self, *, run_config=None, output_root=None, requested_run_id=None, output_directory=None, ml_options=None):
        from .configuration import normalized_config
        self.run_config=normalized_config(run_config or {'profile':'conservative','max_end_s':2400,'sublane':False})
        self.output_root=Path(output_root) if output_root is not None else ROOT/'runs'
        self.requested_run_id=requested_run_id
        self.output_directory=Path(output_directory) if output_directory is not None else None
        self.ml_options=dict(enabled=ml_options is not None,probe_mode='phone',policy='fixed',model_dir=None,selection=None,**{})
        self.ml_options.update(ml_options or {})
        if self.ml_options['probe_mode'] not in {'phone','emulated','none'}:
            raise ValueError('invalid probe mode')
        if self.ml_options['policy'] not in {'fixed','reactive','predictive'}:
            raise ValueError('invalid policy')
        if self.ml_options['policy']=='predictive' and not (self.ml_options['model_dir'] and self.ml_options['selection']):
            raise ValueError('predictive mode requires genuine models and frozen selection')
        self._sampler=None;self._policy=None;self._ml_latest=None
        self._phone_uplinks=0;self.autonomy_enabled=True;self._has_intervention=False
        self._queue = queue.Queue(maxsize=64)
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._snapshot = {'ready': False, 'error': None}
        self._thread = None
        self._conn = None
        self.failure = None
        self.paused = True
        self.rate = 1
        self._frames = deque(maxlen=1201)
        self._events = []

    def start(self):
        self._thread = threading.Thread(target=self._run, name='lig-sumo-owner', daemon=True)
        self._thread.start()
        if not self._ready.wait(45): raise RuntimeError('SUMO startup timed out')
        if self.failure: raise RuntimeError(str(self.failure)) from self.failure

    def command(self, command):
        future = Future()
        if self._stop.is_set() or self.failure:
            future.set_exception(RuntimeError('Simulation unavailable'))
            return future
        try: self._queue.put_nowait((command, future))
        except queue.Full: future.set_exception(RuntimeError('Command queue full'))
        return future

    def snapshot(self):
        with self._lock: return deepcopy(self._snapshot)

    def export(self):
        with self._lock:
            return dict(manifest=deepcopy(self._manifest), frames=deepcopy(list(self._frames)), events=deepcopy(self._events))

    def _save(self):
        """Persist the experiment before reset or shutdown, including incomplete runs."""
        if not hasattr(self, '_manifest'): return
        record = self.export()
        (self.run_dir/'manifest.json').write_text(json.dumps(record['manifest'],indent=2),encoding='utf-8')
        (self.run_dir/'recording.json').write_text(json.dumps(record,separators=(',',':')),encoding='utf-8')
        if self._sampler:
            import pandas as pd
            for name,rows in [('observations',self._sampler.observations),('truth',self._sampler.truth),
                              ('forecasts',self._sampler.forecasts),('detections',self._sampler.detections),('capacity',self._sampler.capacity)]:
                pd.DataFrame(rows).to_csv(self.run_dir/f'{name}.csv',index=False)
            (self.run_dir/'actions.json').write_text(json.dumps(self._policy.events if self._policy else [],indent=2),encoding='utf-8')

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(15)
            if self._thread.is_alive(): raise RuntimeError('SUMO owner did not stop')

    def _reset(self, scenario, seed):
        if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
        if not isinstance(seed,int) or not 0<=seed<=999999: raise ValueError('Invalid seed')
        if self.ml_options.get('batch_profile'):
            from eval.lig_runner import resolve_job
            from .configuration import normalized_config
            batch=resolve_job(dict(run_id='run.lig.live',scenario_id=f'lig.{scenario}',seed=seed,
                                  policy='fixed',compliance=.6,sensor_mask_id='mask.lig.probes',
                                  data_source='sumo',demand_id='demand.lig.ordinary'))
            self.run_config=normalized_config({**batch,'warmup_s':120})
        import traci
        import traci.constants as tc
        import sumo
        if self._conn:
            self._save()
            self._conn.close()
            self._conn = None
        self.run_id = self.requested_run_id or 'lig.' + uuid.uuid4().hex[:12]
        self.scenario, self.seed = scenario, seed
        self.paused, self.rate = True, 1
        self.run_dir = self.output_directory or self.output_root / self.run_id
        if self.output_directory is not None and self.run_dir.exists():
            if any(p.name!='job.json' for p in self.run_dir.iterdir()):
                raise ValueError('Batch output already contains run artifacts')
        self.run_dir.mkdir(parents=True,exist_ok=self.output_directory is not None)
        from .configuration import create_demand
        demand=create_demand(seed,self.run_config,demand_per_hour=SCENARIOS[scenario]['demand'])
        self.scheduled=len(demand.findall('vehicle'))
        ET.ElementTree(demand).write(self.run_dir/'demand.rou.xml',encoding='utf-8',xml_declaration=True)
        args=[str(Path(sumo.SUMO_HOME)/'bin'/('sumo.exe' if os.name=='nt' else 'sumo')),
              '-n',str(DATA/'lig.net.xml'),'-r',str(self.run_dir/'demand.rou.xml'),
              '--seed',str(seed),'--step-length',str(self.run_config['step_s']),
              '--time-to-teleport','-1','--collision.action','warn','--collision.check-junctions',
              '--no-step-log','--duration-log.disable','--tripinfo-output',str(self.run_dir/'trips.xml'),
              '--tripinfo-output.write-unfinished','--device.emissions.probability','1',
              '--error-log',str(self.run_dir/'sumo.log')]
        if self.run_config['sublane']:
            args.extend(['--lateral-resolution','.7'])
        traci.start(args,label=self.run_id,doSwitch=False,verbose=False)
        self._conn=traci.getConnection(self.run_id)
        self._tc=tc
        self._subscriptions=set()
        self.departed=self.arrived=self.collisions=self.teleports=0
        self.co2_kg=0.0
        self._incident=False
        self._incident_started=False
        self._original_speeds={}
        with self._lock:
            self._frames.clear()
            self._events=[]
            self._manifest=dict(run_id=self.run_id,scenario=scenario,seed=seed,calibrated=False,
                            source='OSM geometry + synthetic demand',warmup_s=self.run_config['warmup_s'],sumo_version=self._conn.getVersion()[1],scheduled=self.scheduled,
                            network_sha256=hashlib.sha256((DATA/'lig.net.xml').read_bytes()).hexdigest(),
                            demand_sha256=hashlib.sha256((self.run_dir/'demand.rou.xml').read_bytes()).hexdigest(),
                            provenance=WORLD['provenance'],complete=False,configuration=deepcopy(self.run_config))
        (self.run_dir/'manifest.json').write_text(json.dumps(self._manifest,indent=2),encoding='utf-8')
        self._signals=[]
        nodes={n['id']:n for n in WORLD['junctions']}
        for tls in self._conn.trafficlight.getIDList():
            links=self._conn.trafficlight.getControlledLinks(tls)
            lane_positions=[]
            for group in links:
                if group:
                    lane=group[0][0]
                    shape=self._conn.lane.getShape(lane)
                    pos=shape[-1]
                    lane_positions.append([pos[0]-WORLD['center'][0],pos[1]-WORLD['center'][1]])
                else: lane_positions.append(None)
            self._signals.append(dict(id=tls,positions=lane_positions))
        self._sampler=None;self._policy=None;self._ml_latest=None
        self._phone_uplinks=0;self._has_intervention=False
        if self.ml_options['enabled']:
            from eval.lig_registry import load_registry,probe_assignment
            from eval.lig_runner import Sampler
            from ml.forecast import ForecastService
            registry=load_registry()
            mode=self.ml_options['probe_mode']
            assignment=probe_assignment([v.get('id') for v in demand.findall('vehicle')],seed,.6) if mode=='emulated' else []
            service=ForecastService.from_directory(self.ml_options['model_dir']) if self.ml_options['model_dir'] else None
            if service and service.data_source!='sumo':
                raise ValueError('Harness requires genuine SUMO model artifacts')
            self._sampler=Sampler(self.run_id,registry,'mask.lig.probes' if mode=='emulated' else 'mask.lig.boundary',assignment,service)
            if self.ml_options['policy']!='fixed':
                from .policy import BoundedPolicy
                self._policy=BoundedPolicy(self.ml_options['policy'],registry,selection=self.ml_options['selection'])
                if self.ml_options['selection']:
                    from ml.detect import DetectionEngine
                    self._sampler.intelligence.detector=DetectionEngine(**self.ml_options['selection']['reactive'])
            self._manifest['intelligence_configuration']=dict(probe_mode=mode,policy=self.ml_options['policy'],
                                  model_data_source=service.data_source if service else 'baseline_only',probe_assignment=assignment,
                                  registry=registry,selection=self.ml_options['selection'])
        for _ in range(int(self.run_config['warmup_s']/self.run_config['step_s'])): self._step(publish=False)
        self._publish()

    def _step(self,publish=True):
        conn=self._conn
        conn.simulationStep()
        self.departed+=conn.simulation.getDepartedNumber()
        self.arrived+=conn.simulation.getArrivedNumber()
        self.collisions+=conn.simulation.getCollidingVehiclesNumber()
        self.teleports+=conn.simulation.getStartingTeleportNumber()
        ids=set(conn.vehicle.getIDList())
        for vehicle in ids-self._subscriptions:
            conn.vehicle.subscribe(vehicle,[self._tc.VAR_POSITION,self._tc.VAR_ANGLE,self._tc.VAR_SPEED,
                                            self._tc.VAR_TYPE,self._tc.VAR_CO2EMISSION,self._tc.VAR_WAITING_TIME])
        self._subscriptions=ids
        t=conn.simulation.getTime()
        if not self._incident_started and t>=self.run_config['incident_start_s'] and SCENARIOS[self.scenario]['incident']:
            self._apply_incident()
        if self._incident and t>=self.run_config['incident_end_s']: self._clear_incident()
        elif self._incident and self.run_config['incident_ramp_s'] and round(t/self.run_config['step_s']) % round(5/self.run_config['step_s'])==0:
            self._advance_incident(t)
        values=conn.vehicle.getAllSubscriptionResults()
        self.co2_kg+=sum(v.get(self._tc.VAR_CO2EMISSION,0) for v in values.values())*self.run_config['step_s']/1e6
        if self._sampler:
            latest=self._sampler.sample(conn,t,intervention_active=self._has_intervention)
            if latest:
                self._ml_latest=latest
                if self._policy:
                    self._policy.tick(conn,t,latest,self._sampler.intelligence,enabled=self.autonomy_enabled)
                    self._has_intervention=self._has_intervention or self._policy.intervened
        if publish: self._publish(values)
        if self._ended(t):
            self.paused=True

    def _apply_incident(self):
        conn=self._conn
        near=[r for r in WORLD['roads'] if not r['internal'] and r['lanes'] and
              min((p[0]**2+p[1]**2 for p in r['shape']),default=1e9)<250**2]
        lanes=[lane['id'] for r in near for lane in r['lanes']]
        if self.run_config['incident_edge'] and self.scenario=='rain':
            lanes=[lane['id'] for r in WORLD['roads'] if r['id']==self.run_config['incident_edge'] for lane in r['lanes']]
        elif self.scenario=='roadworks':
            lanes=[(self.run_config['incident_edge'] or WORLD['incident_edge'])+'_0']
        for lane in lanes:
            self._original_speeds[lane]=conn.lane.getMaxSpeed(lane)
            if not self.run_config['incident_ramp_s']:
                conn.lane.setMaxSpeed(lane, 3.0 if self.scenario=='rain' else .7)
        self._incident=True
        self._incident_started=True
        self._events.append(dict(sim_time_s=conn.simulation.getTime(),kind='incident_started',scenario=self.scenario,
                                 explanation='Lane speed restriction; obstruction represented as a slow lane.',lanes=lanes))

    def _advance_incident(self,t):
        fraction=min(1,max(0,(t-self.run_config['incident_start_s'])/self.run_config['incident_ramp_s']))
        target=3.0 if self.scenario=='rain' else .7
        for lane,original in self._original_speeds.items():
            self._conn.lane.setMaxSpeed(lane,original+(target-original)*fraction)

    def _clear_incident(self):
        for lane,speed in self._original_speeds.items(): self._conn.lane.setMaxSpeed(lane,speed)
        self._original_speeds.clear()
        self._incident=False
        self._events.append(dict(sim_time_s=self._conn.simulation.getTime(),kind='incident_cleared'))

    def _publish(self,values=None):
        conn=self._conn
        values=values if values is not None else conn.vehicle.getAllSubscriptionResults()
        tc=self._tc
        vehicles=[]
        for vehicle,v in sorted(values.items()):
            px,py=v[tc.VAR_POSITION]
            vehicles.append(dict(id=vehicle,type=v[tc.VAR_TYPE],x=round(px-WORLD['center'][0],3),
                                 y=round(py-WORLD['center'][1],3),angle=round(v[tc.VAR_ANGLE],2),
                                 speed=round(v[tc.VAR_SPEED],3),waiting=round(v[tc.VAR_WAITING_TIME],1)))
        speeds=[v['speed'] for v in vehicles]
        signals=[dict(id=s['id'],positions=s['positions'],state=conn.trafficlight.getRedYellowGreenState(s['id'])) for s in self._signals]
        t=conn.simulation.getTime()
        metrics=dict(active=len(vehicles),queued=sum(s<.1 for s in speeds),mean_speed_kph=round(sum(speeds)/len(speeds)*3.6,1) if speeds else None,
                     scheduled=self.scheduled,departed=self.departed,arrived=self.arrived,
                     not_departed=self.scheduled-self.departed,collisions=self.collisions,teleports=self.teleports,
                     co2_kg=round(self.co2_kg,4))
        snapshot=dict(ready=True,error=None,run_id=self.run_id,scenario=self.scenario,seed=self.seed,
                      source='SUMO simulation truth',sim_time_s=t,paused=self.paused,rate=self.rate,
                      vehicles=vehicles,signals=signals,metrics=metrics,incident_active=self._incident,events=self._events[-12:],
                      ended=self._ended(t),horizon_s=self.run_config['horizon_s'],max_end_s=self.run_config['max_end_s'],
                      configuration=deepcopy(self.run_config))
        if self._sampler:
            visible={key:value for key,value in (self._ml_latest or {}).items() if key in {'run_id','sim_time_s','observations','forecasts','detections'}}
            from .policy import visible_forecasts
            visible['forecasts']=visible_forecasts(visible.get('forecasts',[]),intervened=self._has_intervention)
            snapshot['intelligence']=dict(**visible,probe_mode=self.ml_options['probe_mode'],
                authenticated_phone_uplinks=self._phone_uplinks,policy=self.ml_options['policy'],
                model_data_source=self._sampler.intelligence.forecaster.data_source,
                control_forecast_method=(self.ml_options['selection'] or {}).get('method'),
                control_forecast_horizon_s=(self.ml_options['selection'] or {}).get('horizon_s'),
                autonomy_enabled=self.autonomy_enabled,intervention_active=self._has_intervention,
                actions=self._policy.events[-20:] if self._policy else [])
        with self._lock:
            self._snapshot=snapshot
            self._manifest['complete']=self.arrived==self.scheduled and not self.collisions and not self.teleports
            self._manifest['final_counts']=metrics
            if not self._frames or t-self._frames[-1]['sim_time_s']>=1:
                self._frames.append(deepcopy(snapshot))

    def _ended(self,t):
        return t>=self.run_config['max_end_s'] or (t>=self.run_config['demand_end_s'] and self._conn.simulation.getMinExpectedNumber()==0)

    def _execute(self,c):
        action=c['action']
        if action=='reset': self._reset(c.get('scenario',self.scenario),c.get('seed',42))
        elif action=='play':
            if self._snapshot.get('ended'): raise ValueError('Run ended; reset to start another run')
            self.paused=False
        elif action=='pause': self.paused=True
        elif action=='step':
            if not self.paused: raise ValueError('Pause before stepping')
            if self._snapshot.get('ended'): raise ValueError('Run ended')
            self._step()
        elif action=='set_rate':
            if c.get('rate') not in (1,2,4,8): raise ValueError('Invalid playback speed')
            self.rate=c['rate']
        elif action=='clear_incident': self._clear_incident()
        elif action=='set_autonomy':
            if type(c.get('enabled')) is not bool: raise ValueError('enabled must be boolean')
            self.autonomy_enabled=c['enabled']
            self._events.append(dict(sim_time_s=self._conn.simulation.getTime(),kind='operator_override',enabled=self.autonomy_enabled))
        elif action=='validated_probe':
            if not self._sampler or self.ml_options['probe_mode']!='phone': raise ValueError('phone observation mode unavailable')
            accepted=self._sampler.intelligence.ingest_probe(c['message'])
            if accepted: self._phone_uplinks+=1
        else: raise ValueError('Unknown command')
        self._publish()
        return self.snapshot()

    def accept_validated_probe(self,message):
        """Internal gateway boundary only: caller already authenticates/binds/validates frame echoes.

        Do not expose this as an unauthenticated HTTP/WebSocket endpoint. The current
        phone fixture backend uses a separate simulation and must not feed this run.
        """
        return self.command(dict(action='validated_probe',message=deepcopy(message)))

    def _run(self):
        try:
            self._reset(self.ml_options.get('initial_scenario','rush'),42)
            self._ready.set()
            deadline=time.monotonic()+.25
            while not self._stop.is_set():
                timeout=.1 if self.paused else max(0,min(.1,deadline-time.monotonic()))
                try:
                    command,future=self._queue.get(timeout=timeout)
                    if future.set_running_or_notify_cancel():
                        try: future.set_result(self._execute(command))
                        except Exception as exc: future.set_exception(exc)
                    deadline=time.monotonic()+.25/self.rate
                except queue.Empty: pass
                if not self.paused and time.monotonic()>=deadline:
                    self._step()
                    deadline=time.monotonic()+.25/self.rate
        except Exception as exc:
            self.failure=exc
            with self._lock: self._snapshot['error']=str(exc)
        finally:
            self._ready.set()
            if self._conn:
                try:
                    self._save()
                finally:
                    self._conn.close()
            while not self._queue.empty():
                _,future=self._queue.get_nowait()
                if not future.done(): future.set_exception(RuntimeError('Simulation stopped'))
