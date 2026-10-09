"""Bounded actions driven by permitted observations; the worker alone applies TraCI."""
from hashlib import sha256
from backend.control import SignalState, extension_remaining, validate_diversion
from ml.trigger import FirstResponseTrigger
from ml.observations import EdgeObservation

def plan_extension(state,elapsed,remaining,receiving_capacity):
    kind='green' if any(c in 'Gg' for c in state) and not any(c in 'yY' for c in state) else 'clearance'
    return extension_remaining(SignalState(kind,elapsed,remaining),receiving_capacity)

def visible_forecasts(forecasts,*,intervened):
    return [dict(forecast,predicted_slowdown=None,usable_for_control=False,
                 reason='intervention_active_no_action_forecast_disabled') if intervened else dict(forecast) for forecast in forecasts]

def validated_selection(selection):
    if not selection or selection.get('selection_split')!='validation_only' or set(selection.get('validation_seeds',[]))!={200,201,202}:
        raise ValueError('policy selection must be frozen on validation seeds')
    if selection.get('method') not in {'boosting','persistence','trend'} or selection.get('horizon_s') not in {120,180,300}:
        raise ValueError('invalid policy selection')
    return selection

class BoundedPolicy:
    def __init__(self,policy,registry,*,selection=None,compliance=.6,seed=42):
        if policy not in {'reactive','predictive'}: raise ValueError('unsupported response policy')
        if selection: validated_selection(selection)
        if policy=='predictive': validated_selection(selection)
        self.policy=policy;self.registry=registry;self.selection=selection
        self.compliance=compliance;self.seed=seed
        self.trigger=FirstResponseTrigger(**(selection['predictive'] if selection else {}))
        self.intervened=False;self.events=[];self.extended=set();self.diverted=set();self.last_advisory=-1e9
        self.reverse={v['sumo_id']:e for e,v in registry['edges'].items()}

    def tick(self,conn,t,latest,intelligence,*,enabled=True):
        focus=self.registry['focus_edge'];entry=self.registry['edges'][focus]
        observation=intelligence.history[focus][-1]
        detection=latest['detections'][focus]
        reactive=bool(detection['active'] and detection['usable_for_control'])
        eligible=reactive;reason='reactive_persistence'
        if self.policy=='predictive' and not self.intervened:
            selection=self.selection
            forecast=intelligence.forecaster.predict(intelligence.history[focus],selection['horizon_s'],method=selection['method'])
            row=next(row for row in latest['log_rows'] if row['edge_id']==focus)
            decision=self.trigger.update(observation,forecast,serving_green=row['serving_green'],phase_age_s=row['phase_age_s'])
            if decision.eligible: eligible=True;reason='predictive_first_response'
        if not eligible or not enabled: return
        if t-self.last_advisory>=30:
            self.events.append(dict(sim_time_s=t,kind='advisory',edge_id=focus,reason=reason,
                                    message='Congestion on the LIG approach; a diversion requires a safe observed bypass.'))
            self.last_advisory=t
        tls=self.registry['tls_sumo_id'];state=conn.trafficlight.getRedYellowGreenState(tls)
        age=conn.trafficlight.getSpentDuration(tls);phase=conn.trafficlight.getPhase(tls)
        key=(phase,round(t-age,3))
        capacities=latest.get('fixed_capacity',{})
        receiving=[capacities.get(self.reverse[actual]) for actual in entry['receiving_edges']]
        capacity_ok=bool(receiving) and all(r and t-r['sim_time_s']<=15 and r['queue_ratio']<=.8 for r in receiving)
        serves=any(state[i] in 'Gg' for i in entry['signal_indices'])
        if key not in self.extended and serves:
            try:
                remaining=conn.trafficlight.getNextSwitch(tls)-t
                new_remaining=plan_extension(state,age,remaining,capacity_ok)
                if new_remaining>remaining:
                    conn.trafficlight.setPhaseDuration(tls,new_remaining)
                    self.extended.add(key);self.intervened=True
                    self.events.append(dict(sim_time_s=t,kind='signal_extension',tls_id='tls.lig',reason=reason,
                                            phase=phase,elapsed_s=age,previous_remaining_s=remaining,remaining_s=new_remaining))
            except ValueError as error:
                self.events.append(dict(sim_time_s=t,kind='guard_rejected',action='signal_extension',reason=str(error)))
        self._divert(conn,t,capacities,reason)

    def _divert(self,conn,t,capacities,reason):
        # Emulated background compliance is explicit. This never represents phone acceptance.
        if len(self.diverted)>=10: return
        focus=self.registry['edges'][self.registry['focus_edge']]['sumo_id']
        candidates=[(self.registry['edges'][edge]['sumo_id'],row['queue_ratio']) for edge,row in capacities.items()
                    if '.exit.' in edge and t-row['sim_time_s']<=15 and row['queue_ratio']<=.35]
        if not candidates: return
        for vehicle in sorted(conn.vehicle.getIDList()):
            if vehicle in self.diverted: continue
            if int(sha256(f'{self.seed}|compliance|{vehicle}'.encode()).hexdigest()[:16],16)/2**64>=self.compliance: continue
            route=list(conn.vehicle.getRoute(vehicle));index=conn.vehicle.getRouteIndex(vehicle)
            current=conn.vehicle.getRoadID(vehicle)
            if current.startswith(':') or current==focus or focus not in route[index+1:index+4]: continue
            for waypoint,ratio in candidates:
                first=conn.simulation.findRoute(current,waypoint,vType=conn.vehicle.getTypeID(vehicle))
                second=conn.simulation.findRoute(waypoint,route[-1],vType=conn.vehicle.getTypeID(vehicle))
                if not first.edges or not second.edges: continue
                alternate=list(first.edges)+list(second.edges[1:])
                if focus in alternate or len(set(alternate))!=len(alternate) or alternate==route[index:]: continue
                validate_diversion(vehicle_id=vehicle,addressed_vehicle=vehicle,accepted=True,now=t,expiry=t+15,
                                   current_edge=current,decision_edge=current,queue_ratio=ratio,route_valid=True)
                conn.vehicle.setRoute(vehicle,alternate)
                self.diverted.add(vehicle);self.intervened=True
                self.events.append(dict(sim_time_s=t,kind='diversion_applied',vehicle_id=vehicle,reason=reason,
                                        source='emulated_compliance',decision_edge=current,route=alternate))
                return # At most one accepted diversion per five-second tick.
