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


def saved_run_path(run_id):
    import re
    if not re.fullmatch(r'lig\.[a-f0-9]{12}',run_id): raise ValueError('invalid_run_id')
    path=ROOT/'runs'/run_id
    if not path.is_dir(): raise FileNotFoundError('run_not_found')
    if path.is_symlink(): raise ValueError('invalid_run_path')
    return path


def saved_runs():
    rows=[]
    for path in sorted((ROOT/'runs').glob('lig.*')):
        try:
            safe=saved_run_path(path.name)
            row=json.loads((safe/'manifest.json').read_text(encoding='utf-8'))
            row.setdefault('saved_wall_s',(safe/'manifest.json').stat().st_mtime)
            rows.append(row)
        except (ValueError,FileNotFoundError,OSError): continue
    return rows


def comparable_runs(reference):
    # Policy deliberately differs; geometry, frozen cohort and event history must not.
    keys=('network_sha256','demand_sha256','seed','settings','scenario_requested','execution_sha256')
    if any(key not in reference for key in keys) or reference.get('scenario_mutated') or reference.get('integrity')!='complete':
        return []
    return [row for row in saved_runs() if not row.get('scenario_mutated') and row.get('integrity')=='complete' and
            row.get('run_id')!=reference.get('run_id') and all(row.get(k)==reference[k] for k in keys)]

class UnifiedEngine(HarnessEngine):
    def __init__(self):
        super().__init__()
        self._lock=threading.RLock()
        self.coordinator=Coordinator()
        self.settings={'mode':'experiment','demand_per_hour':1400,'duration_s':180,'drain_s':600,'location':'lig'}
        self.policy='fixed'
        self.active_events={}; self.event_base={}; self._phase_extension={}
        self._started_wall=time.monotonic(); self._started_sim=0
        self._control_view=self.coordinator.view()

    def state(self):
        with self._lock:
            view=deepcopy(self._control_view)
            if view['lease'] and view['lease']['expires_wall_s']<=time.time(): view['lease']=None
            return {'api_version':'2.0','run':deepcopy(self._snapshot),'scenario':deepcopy(self.settings),**view}

    def export(self):
        record=super().export()
        record['team_control']=self.coordinator.view()
        record['limits']={'baseline_comparison':'unavailable until matched evaluator is run',
                          'co2':'SUMO model output; fleet emission mapping is unreviewed',
                          'forecast_control':'disabled pending saved held-out evidence'}
        return record

    def _execute(self,c):
        try:
            if c['action'] in ('lease','v2') and hasattr(self,'_actor_validator'):
                self._actor_validator(c['actor'])
            if c['action'] in ('phone_offer','phone_accept'):
                from .phone import worker_phone_command
                return worker_phone_command(self,c)
            if c['action']=='lease': return self.coordinator.acquire(c['actor'],c['lease_action'],c.get('takeover',False))
            if c['action']=='v2':
                if c['actor'].get('expires_wall_s',float('inf'))<=time.time(): raise ValueError('session_expired')
                return self.coordinator.execute(c['actor'],c['command'],self.run_id,self._apply_command)
            return super()._execute(c)
        finally:
            with self._lock: self._control_view=self.coordinator.view()

    def _apply_command(self,p):
        action=p.get('action')
        if not isinstance(action,str): raise ValueError('invalid_action')
        if action=='resume': return super()._execute({'action':'play'})
        if action=='pause': return super()._execute({'action':'pause'})
        if action=='rate':
            import math
            value=p.get('value')
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not .25<=value<=20:
                raise ValueError('invalid_rate')
            self.rate=value; self._publish(); return self.snapshot()
        if action=='guidance':
            if not isinstance(p.get('enabled'),bool): raise ValueError('invalid_guidance')
            self._guidance_enabled=p['enabled']; self._publish(); return self.snapshot()
        if action=='step': return super()._execute({'action':'step'})
        if action=='reset':
            from .demand import PRESETS,generate_demand
            settings={**self.settings,**p.get('settings',{})}
            if set(settings)-set(self.settings): raise ValueError('unknown_setting')
            if p.get('scenario','everyday') not in SCENARIOS: raise ValueError('unknown_scenario')
            if settings['location']!='lig': raise ValueError('location_not_prepared')
            if settings['mode'] not in ('experiment','explore'): raise ValueError('invalid_mode')
            import math
            for key in ('demand_per_hour','duration_s','drain_s'):
                value=settings[key]
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise ValueError('invalid_'+key)
            if not 0<=settings['drain_s']<=3600: raise ValueError('invalid_drain')
            if 'preset' in p:
                if p['preset'] not in PRESETS: raise ValueError('invalid_preset')
                settings['demand_per_hour']=PRESETS[p['preset']]
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
        self._next_explore=self.settings['duration_s']
        self._preview_event=None
        self.sensor_view=[]
        self._guidance_enabled=False
        self._phone_offers={}
        self._route_overrides={}
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
        self._scheduled_departures={row['id']:row['depart_s'] for row in rows}
        self._actual_departures={}
        self._arrivals={}
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
        self._manifest['scenario_requested']=scenario
        files=[Path(__file__),Path(__file__).with_name('policies.py'),Path(__file__).with_name('demand.py'),Path(__file__).with_name('phone.py')]
        self._manifest['execution_sha256']=hashlib.sha256(b''.join(p.read_bytes() for p in files)).hexdigest()
        self._manifest['scenario_effect']='Events are applied explicitly through preview/apply; legacy scenario names do not inject hidden restrictions'
        self._started_wall=time.monotonic()
        self._started_sim=0
        self._step(publish=False)
        self._publish()

    def _step(self,publish=True):
        conn=self._conn; conn.simulationStep(); tc=self._tc
        now=conn.simulation.getTime()
        for vehicle in conn.simulation.getDepartedIDList(): self._actual_departures[vehicle]=now
        for vehicle in conn.simulation.getArrivedIDList(): self._arrivals[vehicle]=now
        self.departed+=conn.simulation.getDepartedNumber(); self.arrived+=conn.simulation.getArrivedNumber()
        self.collisions+=conn.simulation.getCollidingVehiclesNumber(); self.teleports+=conn.simulation.getStartingTeleportNumber()
        ids=set(conn.vehicle.getIDList())
        for vehicle in ids-self._subscriptions:
            conn.vehicle.subscribe(vehicle,[tc.VAR_POSITION,tc.VAR_ANGLE,tc.VAR_SPEED,tc.VAR_TYPE,
                tc.VAR_CO2EMISSION,tc.VAR_WAITING_TIME,tc.VAR_ROAD_ID,tc.VAR_ROUTE_ID,tc.VAR_EDGES])
        self._subscriptions=ids
        values=conn.vehicle.getAllSubscriptionResults()
        self.co2_kg+=sum(v.get(tc.VAR_CO2EMISSION,0) for v in values.values())*.25/1e6
        self._update_events()
        self._control_signals()
        t=conn.simulation.getTime()
        if self.settings['mode']=='explore' and t>=getattr(self,'_next_explore',self.settings['duration_s']):
            self._next_explore=t+self.settings['duration_s']
            from .demand import generate_demand
            rows=generate_demand(WORLD['routes'],seed=(self.seed+int(t))%1000000,
                                 rate=self.settings['demand_per_hour'],duration=self.settings['duration_s'])
            for row in rows:
                vehicle=f"{row['type']}.{self.scheduled}"
                self._scheduled_departures[vehicle]=t+row['depart_s']
                conn.vehicle.add(vehicle,f"route.{row['route']}",typeID=row['type'],
                                 depart=str(t+row['depart_s']),departLane='best',departSpeed='0')
                self.scheduled+=1
        ended=self.settings['mode']=='experiment' and (t>=self.settings['duration_s']+self.settings['drain_s'] or
                    (t>=self.settings['duration_s'] and conn.simulation.getMinExpectedNumber()==0))
        if ended: self.paused=True
        if publish: self._publish(values)

    def _publish(self,values=None):
        super()._publish(values)
        t=self._conn.simulation.getTime()
        ended=self.settings['mode']=='experiment' and (t>=self.settings['duration_s']+self.settings['drain_s'] or
               (t>=self.settings['duration_s'] and self._conn.simulation.getMinExpectedNumber()==0))
        with self._lock:
            # The worker alone reads route truth. HTTP handlers only read this snapshot.
            route_values=values if values is not None else self._conn.vehicle.getAllSubscriptionResults()
            for vehicle in self._snapshot['vehicles']:
                row=route_values[vehicle['id']]
                vehicle['route_id']=row.get(self._tc.VAR_ROUTE_ID)
                vehicle['route_path']=list(row.get(self._tc.VAR_EDGES,()))
                vehicle.update(getattr(self,'_route_overrides',{}).get(vehicle['id'],{}))
            self._snapshot['arrived_vehicle_ids']=list(self._arrivals)
            self._snapshot['ended']=ended
            self._snapshot['policy']=self.policy
            self._snapshot['guidance_enabled']=self._guidance_enabled
            self._snapshot['policy_implementation']={'fixed':'fixed_program',
                'pressure':'pressure_worker_clearance_phase_selection',
                'actuated':'actuated_lane_presence_gap_extension',
                'bounded':'bounded_existing_green_extension'}[self.policy]
            self._snapshot['events']=deepcopy(list(self.active_events.values()))
            self._snapshot['action_log']=deepcopy(self._events[-60:])
            self._snapshot['simulated_sensors']=deepcopy(getattr(self,'sensor_view',[]))
            self._snapshot['performance']={'target_sim_s_per_wall_s':self.rate,
                'achieved_sim_s_per_wall_s':round(t/max(.001,time.monotonic()-self._started_wall),3),
                'command_queue_depth':self._queue.qsize(),'scene_fps':None}
            self._manifest['complete']=ended and self.arrived==self.scheduled and not self.collisions and not self.teleports
            self._manifest['integrity']='faulted' if self.collisions or self.teleports else ('complete' if self._manifest['complete'] else 'incomplete')
            self._manifest['emission_mapping_reviewed']=False
            complete=self._manifest['complete'] and self.scheduled>0 and len(self._arrivals)==self.scheduled and len(self._actual_departures)==self.scheduled
            self._manifest['journey_measurement_source']='worker_step_lifecycle_events_0.25s'
            self._manifest['mean_journey_s']=(sum(self._arrivals[v]-self._scheduled_departures[v] for v in self._arrivals)/self.scheduled if complete else None)
            self._manifest['mean_travel_s']=(sum(self._arrivals[v]-self._actual_departures[v] for v in self._arrivals)/self.scheduled if complete else None)
            self._manifest['mean_insertion_delay_s']=(sum(self._actual_departures[v]-self._scheduled_departures[v] for v in self._arrivals)/self.scheduled if complete else None)
            due=sum(stamp<=t for stamp in self._scheduled_departures.values())
            self._snapshot['progress']={'scheduled':self.scheduled,'arrived':self.arrived,
                'completion_fraction':self.arrived/self.scheduled if self.scheduled else None,
                'insertion_backlog':max(0,due-self.departed),'future_departures':max(0,self.scheduled-due),
                'phase':'ended' if ended else 'draining' if t>=self.settings['duration_s'] and self.settings['mode']=='experiment' else 'running',
                'integrity':self._manifest['integrity']}
            self._snapshot['result']=deepcopy(self._manifest)
            if self._frames and self._frames[-1]['sim_time_s']==t:
                self._frames[-1]=deepcopy(self._snapshot)
            elif ended:
                self._frames.append(deepcopy(self._snapshot))
        if ended and getattr(self,'_saved_end_run',None)!=self.run_id:
            self._save(); self._saved_end_run=self.run_id

    def _event_command(self,p):
        kind=p['action']; now=self._conn.simulation.getTime()
        if kind=='event_end':
            eid=p.get('event_id')
            if eid not in self.active_events: raise ValueError('unknown_event')
            self.active_events[eid]['end_s']=now
            self.active_events[eid]['status']='ended'
            self._events.append({'kind':'event_ended','event_id':eid,'sim_time_s':now})
            self._update_events(); self._publish(); return self.snapshot()
        event=deepcopy(p.get('event',{}))
        if event.get('kind') not in ('rain','blockage','roadworks','rally','sensor_outage'):
            raise ValueError('event_unavailable_ambulance_requires_verified_route_and_recovery')
        edge=event.get('edge_id')
        if edge not in {r['id'] for r in WORLD['roads']}: raise ValueError('invalid_edge')
        start=event.get('start_s',now); duration=event.get('duration_s',60); severity=event.get('severity',.5)
        import math
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (start,duration,severity)):
            raise ValueError('invalid_event_number')
        if start<now or not 0<duration<=1800 or not 0<=severity<=1: raise ValueError('invalid_event_schedule')
        event.update(event_id=event.get('event_id') or 'event.'+uuid.uuid4().hex[:12],start_s=start,end_s=start+duration,
                     severity=severity,status='preview',effect=('simulated sensor unavailable; no road restriction' if event['kind']=='sensor_outage'
                         else 'simulated edge speed restriction; no physical obstacle'))
        lanes=[f'{edge}_{i}' for i in range(self._conn.edge.getLaneNumber(edge))]
        if not lanes: raise ValueError('edge_has_no_lanes')
        if kind=='event_preview':
            self._preview_event=deepcopy(event)
            return {**self.snapshot(),'event_preview':event}
        if kind!='event_apply': raise ValueError('invalid_event_action')
        prior=getattr(self,'_preview_event',None)
        if not prior or any(prior.get(k)!=event.get(k) for k in ('kind','edge_id','start_s','end_s','severity')):
            raise ValueError('preview_required')
        event['event_id']=prior['event_id']; event['status']='scheduled'
        self.active_events[event['event_id']]=event
        self._preview_event=None
        self._manifest['scenario_mutated']=True
        self._events.append({'kind':'event_scheduled','event':deepcopy(event),'sim_time_s':now})
        self._update_events(); self._publish(); return self.snapshot()

    def _update_events(self):
        now=self._conn.simulation.getTime(); restrictions={}; self.outage_edges=set()
        for event in self.active_events.values():
            active=event['start_s']<=now<event['end_s']
            event['status']='active' if active else ('ended' if now>=event['end_s'] else 'scheduled')
            if not active: continue
            if event['kind']=='sensor_outage': self.outage_edges.add(event['edge_id']); continue
            factor=max(.05,1-event['severity'])
            restrictions[event['edge_id']]=min(restrictions.get(event['edge_id'],1),factor)
        lanes_to_set={}
        for edge,factor in restrictions.items():
            for i in range(self._conn.edge.getLaneNumber(edge)):
                lane=f'{edge}_{i}'
                self.event_base.setdefault(lane,self._conn.lane.getMaxSpeed(lane))
                lanes_to_set[lane]=self.event_base[lane]*factor
        for lane,speed in self.event_base.items(): self._conn.lane.setMaxSpeed(lane,lanes_to_set.get(lane,speed))

    def _control_signals(self):
        # Installed simulated lane sensors are an explicit adapter; phone count is unaffected.
        from .policies import choose_phase
        if not hasattr(self, '_signal_memory'): self._signal_memory={}
        conn=self._conn; now=conn.simulation.getTime(); sensors=[]
        for tls in conn.trafficlight.getIDList():
            state=conn.trafficlight.getRedYellowGreenState(tls)
            links=conn.trafficlight.getControlledLinks(tls)
            movements=[]
            for index,group in enumerate(links):
                if not group: continue
                incoming,outgoing,_=group[0]
                row={'id':str(index),'queue':conn.lane.getLastStepHaltingNumber(incoming),
                     'upstream_capacity':max(1,conn.lane.getLength(incoming)/7.5),
                     'downstream_occupied':conn.lane.getLastStepVehicleNumber(outgoing),
                     'downstream_capacity':max(1,conn.lane.getLength(outgoing)/7.5),'saturation':.5,
                     'fresh':conn.lane.getEdgeID(incoming) not in self.outage_edges,
                     'incoming_lane':incoming,'outgoing_lane':outgoing,'signal':state[index]}
                movements.append(row)
            sensors.append({'source_type':'simulated_sensor','source_id':tls,'sim_time_s':now,'movements':movements})
            phase=conn.trafficlight.getPhase(tls)
            logics=conn.trafficlight.getAllProgramLogics(tls)
            program=self._signal_memory.get(tls,{}).get('pending')
            program=program['program'] if program else conn.trafficlight.getProgram(tls)
            logic=next(l for l in logics if l.programID==program)
            phases={str(i):[str(j) for j,c in enumerate(p.state) if c in 'Gg'] for i,p in enumerate(logic.phases) if 'g' in p.state.lower() and 'y' not in p.state.lower()}
            memory=self._signal_memory.setdefault(tls, {'last_service':{p:now for p in phases}, 'pending':None, 'last_detection':now-3})
            if memory.get('run_id') != getattr(self,'run_id',None):
                memory.update(run_id=getattr(self,'run_id',None),last_service={p:now for p in phases},pending=None,last_detection=now-3)
            pending=memory['pending']
            if pending:
                # Finish clearance even if the operator changes mode during a transition.
                if now >= pending['deadline']:
                    if pending['stage']=='yellow':
                        conn.trafficlight.setRedYellowGreenState(tls,'r'*len(state))
                        pending.update(stage='allred',deadline=now+pending['allred_s'])
                    else:
                        target=pending['target']; ids=phases.get(str(target),[])
                        safe=bool(ids) and all(m['fresh'] and m['downstream_capacity']-m['downstream_occupied']>=1 for m in movements if m['id'] in ids)
                        conn.trafficlight.setProgram(tls,pending['program'])
                        # Unsafe target resumes the configured successor clearance phase;
                        # never choose a new green from incomplete sensor evidence.
                        conn.trafficlight.setPhase(tls,target if safe and self.policy=='pressure' else pending['yellow'])
                        memory['pending']=None
                        self._events.append({'kind':'signal_transition_completed' if safe and self.policy=='pressure' else 'signal_transition_cancelled',
                            'tls_id':tls,'sim_time_s':now,'target_phase':target,'reason':'pressure_clearance_complete' if safe and self.policy=='pressure' else 'target_no_longer_safe'})
                continue
            if self.policy=='fixed' or 'y' in state.lower() or 'g' not in state.lower(): continue
            for p, ids in phases.items():
                if p==str(phase): memory['last_service'][p]=now
            elapsed=conn.trafficlight.getSpentDuration(tls)
            remaining=conn.trafficlight.getNextSwitch(tls)-now
            key=(tls,phase,round(now-elapsed,2))
            current=[m for m in movements if m['id'] in phases.get(str(phase),[])]
            safe=current and all(m['fresh'] and m['downstream_capacity']-m['downstream_occupied']>=1 for m in current)
            should_extend=safe and sum(m['queue'] for m in current)>0 and elapsed<55
            if self.policy=='pressure':
                decision=choose_phase(movements=movements,phases=phases,current_phase=str(phase),green_elapsed_s=elapsed,
                                      red_elapsed_s={p:now-last for p,last in memory['last_service'].items()},clearance_complete=True)
                should_extend=should_extend and decision['action']=='keep' and decision['reason']!='minimum_green'
                if decision['action']=='request_transition':
                    yellow=(phase+1)%len(logic.phases)
                    yellow_phase=logic.phases[yellow]
                    # Only a reviewed configured successor yellow is usable. Never
                    # synthesize incompatible yellow movements or skip clearance.
                    old_green={i for i,c in enumerate(state) if c in 'gG'}
                    yellow_indices={i for i,c in enumerate(yellow_phase.state) if c in 'yY'}
                    if yellow_indices==old_green and 'g' not in yellow_phase.state.lower() and yellow_phase.duration>0:
                        allred_s=max([1.0]+[float(p.duration) for p in logic.phases if set(p.state.lower())=={'r'}])
                        conn.trafficlight.setPhase(tls,yellow)
                        # Prevent natural successor green before owner rechecks deadline.
                        conn.trafficlight.setPhaseDuration(tls,float(yellow_phase.duration)+86400)
                        memory['pending']={'target':int(decision['phase_id']),'yellow':yellow,'stage':'yellow',
                            'deadline':now+float(yellow_phase.duration),'allred_s':allred_s,'program':logic.programID}
                        self._events.append({'kind':'signal_transition_started','tls_id':tls,'sim_time_s':now,
                            'target_phase':int(decision['phase_id']),'reason':decision['reason'],'source_type':'simulated_sensor',
                            'yellow_s':float(yellow_phase.duration),'allred_s':allred_s,'scores':decision['scores']})
                        continue
                if decision['action']=='fallback':
                    should_extend=False
            elif self.policy=='actuated':
                # Explicit lane-presence detector with 2s gap-out, same min/max and
                # receiving-space bounds; distinct from the aggregate queue rule.
                if any(conn.lane.getLastStepVehicleIDs(m['incoming_lane']) for m in current if m['fresh']):
                    memory['last_detection']=now
                should_extend=safe and now-memory['last_detection']<2 and 10<=elapsed<60
                decision={'reason':'lane_presence_gap_under_2s','action':'keep'}
            else: decision={'reason':'observed_queue_and_receiving_space','action':'keep'}
            if remaining<=1 and should_extend and key not in self._phase_extension:
                # Extend only existing green; never jump past its configured yellow/all-red sequence.
                conn.trafficlight.setPhaseDuration(tls,min(5,60-elapsed))
                self._phase_extension[key]=True
                self._events.append({'kind':'signal_extension','source_type':'simulated_sensor','policy':self.policy,
                                     'tls_id':tls,'phase':phase,'sim_time_s':now,'reason':decision['reason'],'extension_s':min(5,60-elapsed)})
        self.sensor_view=sensors
