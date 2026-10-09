"""Unified host adapter. Only the inherited owner thread may call TraCI."""
from copy import deepcopy
import hashlib
import json
import os
import random
import threading
import time
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
from backend.harness.engine import HarnessEngine, DATA, ROOT, WORLD, TYPES, SCENARIOS
from .coordination import Coordinator

class UnifiedEngine(HarnessEngine):
    def __init__(self):
        super().__init__()
        self._lock=threading.RLock()
        self.coordinator=Coordinator()
        self.settings={'mode':'experiment','demand_per_hour':1400,'duration_s':180,'drain_s':180,'location':'lig'}
        self.policy='fixed'
        self.active_events={}; self.event_base={}; self._phase_extension={}
        self._started_wall=time.monotonic(); self._started_sim=0
        self._control_view=self.coordinator.view()

    def state(self):
        with self._lock:
            return {'api_version':'2.0','run':deepcopy(self._snapshot),'scenario':deepcopy(self.settings),**deepcopy(self._control_view)}

    def _execute(self,c):
        try:
            if c['action']=='lease': return self.coordinator.acquire(c['actor'],c['lease_action'],c.get('takeover',False))
            if c['action']=='v2':
                if c['actor'].get('expires_wall_s',float('inf'))<=time.time(): raise ValueError('session_expired')
                return self.coordinator.execute(c['actor'],c['command'],self.run_id,self._apply_command)
            return super()._execute(c)
        finally:
            with self._lock: self._control_view=self.coordinator.view()

    def _apply_command(self,p):
        action=p.get('action')
        if action=='resume': return super()._execute({'action':'play'})
        if action=='pause': return super()._execute({'action':'pause'})
        if action=='rate': return super()._execute({'action':'set_rate','rate':p.get('value')})
        if action=='step': return super()._execute({'action':'step'})
        if action=='reset':
            from .demand import PRESETS,generate_demand
            settings={**self.settings,**p.get('settings',{})}
            if settings['location']!='lig': raise ValueError('location_not_prepared')
            if settings['mode'] not in ('experiment','explore'): raise ValueError('invalid_mode')
            if not 0<=settings['drain_s']<=3600: raise ValueError('invalid_drain')
            if 'preset' in p: settings['demand_per_hour']=PRESETS[p['preset']]
            generate_demand(WORLD['routes'],seed=p.get('seed',42),rate=settings['demand_per_hour'],duration=settings['duration_s'])
            self.settings=settings
            self._reset(p.get('scenario','everyday'),p.get('seed',42))
            return self.snapshot()
        if action=='controller':
            if p.get('policy') not in ('fixed','bounded','actuated','pressure'): raise ValueError('invalid_policy')
            if self._conn.simulation.getTime()>1: self._manifest['scenario_mutated']=True
            self.policy=p['policy']; self._manifest['policy']=self.policy
            self._events.append({'kind':'policy_selected','policy':self.policy,'sim_time_s':self._conn.simulation.getTime()})
            self._publish(); return self.snapshot()
        if action.startswith('event_'): return self._event_command(p)
        raise ValueError('unknown_action')

    def _reset(self, scenario, seed):
        if scenario not in SCENARIOS: raise ValueError('Unknown scenario')
        from .demand import generate_demand
        self.policy='fixed'
        self.active_events={}
        self.event_base={}
        self._phase_extension={}
        if not isinstance(seed,int) or not 0<=seed<=999999: raise ValueError('Invalid seed')
        import traci
        import traci.constants as tc
        import sumo
        if self._conn:
            self._save()
            self._conn.close()
            self._conn = None
        self.run_id = 'lig.' + uuid.uuid4().hex[:12]
        self.scenario, self.seed = scenario, seed
        self.paused, self.rate = True, 1
        self.run_dir = ROOT / 'runs' / self.run_id
        self.run_dir.mkdir(parents=True)
        rng = random.Random(seed)
        demand=ET.Element('routes')
        for name, attrs in TYPES.items():
            ET.SubElement(demand,'vType',id=name, sigma='0', speedDev='0', lcPushy='0', lcAssertive='1', tau='1.5', **attrs)
        for i,edges in enumerate(WORLD['routes']):
            ET.SubElement(demand,'route',id=f'route.{i}',edges=' '.join(edges))
        self.scheduled = 0
        # Explicit seeded cohort: route/type/departure fixed before simulation starts.
        rows=generate_demand(WORLD['routes'],seed=seed,rate=self.settings['demand_per_hour'],duration=self.settings['duration_s'])
        for row in rows:
            ET.SubElement(demand,'vehicle',id=row['id'],type=row['type'],route=f"route.{row['route']}",
                          depart=str(row['depart_s']),departLane='best',departSpeed='0',speedFactor=str(row['speed_factor']))
        self.scheduled=len(rows)
        (self.run_dir/'demand.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        ET.ElementTree(demand).write(self.run_dir/'demand.rou.xml',encoding='utf-8',xml_declaration=True)
        args=[str(Path(sumo.SUMO_HOME)/'bin'/('sumo.exe' if os.name=='nt' else 'sumo')),
              '-n',str(DATA/'lig.net.xml'),'-r',str(self.run_dir/'demand.rou.xml'),
              '--seed',str(seed),'--step-length','.25','--lateral-resolution','-1',
              '--time-to-teleport','-1','--collision.action','warn','--collision.check-junctions',
              '--no-step-log','--duration-log.disable','--tripinfo-output',str(self.run_dir/'trips.xml'),
              '--tripinfo-output.write-unfinished','--error-log',str(self.run_dir/'sumo.log')]
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
                            source='OSM geometry + synthetic demand',warmup_s=0,sumo_version=self._conn.getVersion()[1],scheduled=self.scheduled,
                            network_sha256=hashlib.sha256((DATA/'lig.net.xml').read_bytes()).hexdigest(),
                            demand_sha256=hashlib.sha256((self.run_dir/'demand.rou.xml').read_bytes()).hexdigest(),
                            provenance=WORLD['provenance'],complete=False)
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
        self._manifest['settings']=deepcopy(self.settings)
        self._manifest['policy']='fixed'
        self._manifest['scenario_mutated']=False
        self._started_wall=time.monotonic()
        self._started_sim=0
        self._step(publish=False)
        self._publish()

