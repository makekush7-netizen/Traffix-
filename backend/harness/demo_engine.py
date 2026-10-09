"""Small deterministic demo adapter. The inherited worker is the sole TraCI owner."""
from copy import deepcopy
import hashlib
import json
import os
import threading
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from backend.control import validate_diversion
from .engine import HarnessEngine, DATA, ROOT, TYPES, WORLD

CONFIG_PATH=DATA/'demo-config.json'
BASELINE_PATH=DATA/'demo-baseline.json'


class DemoEngine(HarnessEngine):
    def __init__(self):
        super().__init__()
        self._lock=threading.RLock()
        self.config=json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        self.demo_mode=True

    def _reset(self, scenario=None, seed=None):
        import traci
        import traci.constants as tc
        import sumo
        import sumolib
        if self._conn:
            self._save(); self._conn.close(); self._conn=None
        config=self.config
        self.scenario='rain'; self.seed=config['seed']; self.run_id='lig.demo.'+uuid.uuid4().hex[:12]
        self.paused=True; self.rate=1
        self.run_dir=ROOT/'runs'/self.run_id; self.run_dir.mkdir(parents=True)
        net=sumolib.net.readNet(str(DATA/'lig.net.xml'))
        for name in ('route_a','route_b'):
            route=config[name]
            for kind in set(config['cohort']):
                vclass=TYPES[kind]['vClass']
                if any(not net.getEdge(e).allows(vclass) for e in route): raise ValueError('Route class permission failed')
                for a,b in zip(route,route[1:]):
                    links=net.getEdge(a).getOutgoing().get(net.getEdge(b),[])
                    if not any(link.allows(vclass) for link in links): raise ValueError('Disconnected demo route')
        demand=ET.Element('routes')
        for name,attrs in TYPES.items():
            params={**attrs,'minGap':'2.5','latAlignment':'center','minGapLat':'.5'}
            ET.SubElement(demand,'vType',id=name,sigma='0',speedDev='0',lcPushy='0',lcAssertive='.5',tau='2.5',**params)
        ET.SubElement(demand,'route',id='route.demo.A',edges=' '.join(config['route_a']))
        ET.SubElement(demand,'route',id='route.demo.B',edges=' '.join(config['route_b']))
        self.roles={}; self.arrival_times={}; self.applied=set(); self.routes={}
        for i,kind in enumerate(config['cohort']):
            vehicle=('veh.role.rider','veh.role.auto','veh.role.delivery')[i] if i<3 else f'{kind}.demo.{i}'
            self.roles[vehicle]=('Rider','Auto driver','Delivery driver')[i] if i<3 else kind.title()
            ET.SubElement(demand,'vehicle',id=vehicle,type=kind,route='route.demo.A',depart='0',
                          departLane=str(i%2),departPos=str(5+(i//2)*23),departSpeed='0')
            self.routes[vehicle]='route.demo.A'
        ET.ElementTree(demand).write(self.run_dir/'demand.rou.xml',encoding='utf-8',xml_declaration=True)
        self.sensor_lanes=net.getEdge(config['route_b'][1]).getLanes()
        sensors=ET.Element('additional')
        for i,lane in enumerate(self.sensor_lanes):
            ET.SubElement(sensors,'laneAreaDetector',id=f'demo.bypass.{i}',lane=lane.getID(),pos='0',
                          length=str(lane.getLength()),freq='1',file=str(self.run_dir/'bypass-sensors.xml'))
        ET.ElementTree(sensors).write(self.run_dir/'sensors.add.xml',encoding='utf-8',xml_declaration=True)
        args=[str(Path(sumo.SUMO_HOME)/'bin'/('sumo.exe' if os.name=='nt' else 'sumo')),
              '-n',str(DATA/'lig.net.xml'),'-r',str(self.run_dir/'demand.rou.xml'),
              '-a',str(self.run_dir/'sensors.add.xml'),'--seed',str(self.seed),'--step-length',str(config['step_s']),
              '--time-to-teleport','-1','--collision.action','warn','--collision.check-junctions',
              '--no-step-log','--duration-log.disable','--tripinfo-output',str(self.run_dir/'trips.xml'),
              '--tripinfo-output.write-unfinished','--error-log',str(self.run_dir/'sumo.log')]
        traci.start(args,label=self.run_id,doSwitch=False,verbose=False)
        self._conn=traci.getConnection(self.run_id); self._tc=tc; self._subscriptions=set()
        self.scheduled=len(config['cohort']); self.departed=self.arrived=self.collisions=self.teleports=0; self.co2_kg=0
        self._incident=True; self._incident_started=True; self._original_speeds={}; self._signals=[]
        for edge in config['route_a'][:2]:
            for lane in net.getEdge(edge).getLanes():
                self._original_speeds[lane.getID()]=self._conn.lane.getMaxSpeed(lane.getID())
                self._conn.lane.setMaxSpeed(lane.getID(),config['rain_speed_mps'])
        with self._lock:
            self._frames.clear(); self._events=[]
            self._manifest=dict(run_id=self.run_id,scenario=config['scenario_id'],seed=self.seed,calibrated=False,
                                source='OSM geometry + assumed staged monsoon demonstration',warmup_s=0,
                                sumo_version=self._conn.getVersion()[1],scheduled=self.scheduled,complete=False,
                                network_sha256=hashlib.sha256((DATA/'lig.net.xml').read_bytes()).hexdigest(),
                                demand_sha256=hashlib.sha256((self.run_dir/'demand.rou.xml').read_bytes()).hexdigest(),
                                scenario_sha256=hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
                                assumptions=config,mean_journey_s=None)
        self._step()

    def _step(self,publish=True):
        conn=self._conn; conn.simulationStep(); tc=self._tc
        self.departed+=conn.simulation.getDepartedNumber(); self.arrived+=conn.simulation.getArrivedNumber()
        self.collisions+=conn.simulation.getCollidingVehiclesNumber(); self.teleports+=conn.simulation.getStartingTeleportNumber()
        t=conn.simulation.getTime()
        for vehicle in conn.simulation.getArrivedIDList(): self.arrival_times[vehicle]=t
        ids=set(conn.vehicle.getIDList())
        for vehicle in ids-self._subscriptions:
            conn.vehicle.subscribe(vehicle,[tc.VAR_POSITION,tc.VAR_ANGLE,tc.VAR_SPEED,tc.VAR_TYPE,
                                            tc.VAR_CO2EMISSION,tc.VAR_WAITING_TIME,tc.VAR_ROAD_ID])
        self._subscriptions=ids
        if self._incident and t>=self.config['rain_end_s']: self._clear_incident()
        values=conn.vehicle.getAllSubscriptionResults()
        self.co2_kg+=sum(v.get(tc.VAR_CO2EMISSION,0) for v in values.values())*self.config['step_s']/1e6
        if conn.simulation.getMinExpectedNumber()==0 or t>=self.config['horizon_s']: self.paused=True
        if publish: self._publish(values)

    def _publish(self,values=None):
        # The snapshot and demo metadata become visible as one atomic update.
        with self._lock: self._publish_complete(values)

    def _publish_complete(self,values=None):
        super()._publish(values)
        conn=self._conn; t=conn.simulation.getTime()
        vehicles={v:self.routes[v] for v in conn.vehicle.getIDList()}
        decision=self.config['route_a'][0]
        eligible=[v for v in vehicles if v not in self.applied and conn.vehicle.getRoadID(v)==decision and
                  conn.lane.getLength(conn.vehicle.getLaneID(v))-conn.vehicle.getLanePosition(v)>self.config['decision_margin_m']]
        ratios=[conn.lanearea.getJamLengthMeters(f'demo.bypass.{i}')/lane.getLength() for i,lane in enumerate(self.sensor_lanes)]
        ended=conn.simulation.getMinExpectedNumber()==0 or t>=self.config['horizon_s']
        with self._lock:
            self._snapshot['ended']=ended
            self._snapshot['demo']=dict(name=self.config['name'],roles=self.roles,routes=vehicles,eligible_vehicles=eligible,
                                       decision_edge=decision,bypass_queue_ratio=max(ratios,default=None),
                                       capacity_source='SIMULATED INSTALLED BYPASS SENSOR',route_a=self.config['route_a'],
                                       route_b=self.config['route_b'],applied_vehicles=sorted(self.applied))
            self._manifest['mean_journey_s']=(sum(self.arrival_times.values())/self.scheduled if self._manifest['complete'] else None)
            self._snapshot['result']=deepcopy(self._manifest)
            # Replace the recorded truth frame with the fully decorated version.
            if self._frames and self._frames[-1]['sim_time_s']==t: self._frames[-1]=deepcopy(self._snapshot)

    def _execute(self,c):
        if c['action']=='demo_reroute':
            conn=self._conn; now=conn.simulation.getTime(); vehicle=c['vehicle_id']
            if c['run_id']!=self.run_id: raise ValueError('wrong_run')
            if vehicle not in conn.vehicle.getIDList(): raise ValueError('journey_finished')
            if c.get('accepted') is not True: raise ValueError('accept_required')
            if vehicle in self.applied: raise ValueError('duplicate')
            current=conn.vehicle.getRoadID(vehicle); decision=self.config['route_a'][0]
            if conn.lane.getLength(conn.vehicle.getLaneID(vehicle))-conn.vehicle.getLanePosition(vehicle)<=self.config['decision_margin_m']:
                raise ValueError('too_late_for_safe_turn')
            ratios=[conn.lanearea.getJamLengthMeters(f'demo.bypass.{i}')/lane.getLength() for i,lane in enumerate(self.sensor_lanes)]
            validate_diversion(vehicle_id=vehicle,addressed_vehicle=c['addressed_vehicle'],accepted=c['accepted'],
                               now=now,expiry=c['expires_sim_s'],current_edge=current,decision_edge=decision,
                               queue_ratio=max(ratios,default=None),route_valid=True)
            conn.vehicle.setRoute(vehicle,self.config['route_b'])
            if list(conn.vehicle.getRoute(vehicle))!=self.config['route_b']: raise RuntimeError('Route not confirmed by SUMO')
            self.routes[vehicle]='route.demo.B'; self.applied.add(vehicle)
            self._events.append(dict(kind='driver_route_applied',vehicle_id=vehicle,sim_time_s=now,
                                     advisory_id=c['advisory_id'],explanation='Driver accepted. Route applied.'))
            self._publish(); self._save()
            return self.snapshot()
        return super()._execute(c)
