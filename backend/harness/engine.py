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
    def __init__(self, *, run_config=None, output_root=None, requested_run_id=None, output_directory=None):
        from .configuration import normalized_config
        self.run_config=normalized_config(run_config or {'profile':'conservative','max_end_s':2400,'sublane':False})
        self.output_root=Path(output_root) if output_root is not None else ROOT/'runs'
        self.requested_run_id=requested_run_id
        self.output_directory=Path(output_directory) if output_directory is not None else None
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

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(15)
            if self._thread.is_alive(): raise RuntimeError('SUMO owner did not stop')

    def _reset(self, scenario, seed):
        if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
        if not isinstance(seed,int) or not 0<=seed<=999999: raise ValueError('Invalid seed')
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
                      ended=self._ended(t),horizon_s=self.run_config['horizon_s'],max_end_s=self.run_config['max_end_s'])
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
        else: raise ValueError('Unknown command')
        self._publish()
        return self.snapshot()

    def _run(self):
        try:
            self._reset('rush',42)
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
