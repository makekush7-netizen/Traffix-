"""Unified phone guidance: permitted observations; worker-owned reviewed bypass."""
import asyncio
from copy import deepcopy
import secrets
from backend.harness.mobile import MobileBridge
from backend.harness.demo_rules import DemoRules
from backend.harness.demo_engine import load_demo_config
from backend.harness.engine import DATA,TYPES
from backend.control import validate_diversion


def worker_phone_command(engine,c):
    conn=engine._conn; now=conn.simulation.getTime(); vehicle=c['vehicle_id']
    if not getattr(engine,'_guidance_enabled',False): raise ValueError('guidance_disabled')
    if c['run_id']!=engine.run_id: raise ValueError('wrong_run')
    if vehicle not in conn.vehicle.getIDList(): raise ValueError('journey_finished')
    offers=getattr(engine,'_phone_offers',None)
    if offers is None: offers=engine._phone_offers={}
    for key in list(offers):
        if offers[key]['run_id']!=engine.run_id or offers[key]['expires_sim_s']<=now:
            del offers[key]
    current=conn.vehicle.getRoadID(vehicle)
    config=load_demo_config(); decision=config['route_a'][0]
    if current!=decision: raise ValueError('bypass_unavailable_on_this_approach')
    lane=conn.vehicle.getLaneID(vehicle)
    if conn.lane.getLength(lane)-conn.vehicle.getLanePosition(vehicle)<=config['decision_margin_m']:
        raise ValueError('too_late_for_safe_turn')
    if c['action']=='phone_offer':
        if len(offers)>=256: raise ValueError('offer_capacity')
        route=list(conn.vehicle.getRoute(vehicle)); index=conn.vehicle.getRouteIndex(vehicle)
        remaining=route[index:]; candidate=config['route_b']; match=None
        for j,edge in enumerate(candidate[1:],1):
            if edge in remaining[1:]: match=(j,remaining.index(edge)); break
        if match is None: raise ValueError('reviewed_bypass_has_no_matching_destination')
        j,k=match; bypass=candidate[:j]+remaining[k:]
        import sumolib
        net=sumolib.net.readNet(str(DATA/'lig.net.xml'))
        cls=TYPES[conn.vehicle.getTypeID(vehicle)]['vClass']
        for a,b in zip(bypass,bypass[1:]):
            if not net.getEdge(a).allows(cls) or not net.getEdge(b).allows(cls): raise ValueError('class_forbidden_route')
            links=net.getEdge(a).getOutgoing().get(net.getEdge(b),[])
            if not any(link.allows(cls) for link in links): raise ValueError('disconnected_bypass')
        offer={'advisory_id':'advisory.'+secrets.token_hex(10),'vehicle_id':vehicle,'kind':'reroute',
               'route_id':'route.unified.reviewed_bypass','message':'Phone-observed slowdown. Accept reviewed bypass?',
               'expires_sim_s':now+60}
        offers[offer['advisory_id']]={'run_id':engine.run_id,'route':bypass,'prior_route':route,'type':conn.vehicle.getTypeID(vehicle),'status':'pending',**offer}
        return deepcopy(offer)
    offer=offers.get(c['advisory_id'])
    if not offer or offer['run_id']!=engine.run_id or offer['vehicle_id']!=vehicle: raise ValueError('wrong_advisory')
    if offer['status']!='pending': raise ValueError('duplicate_or_cancelled_advisory')
    if list(conn.vehicle.getRoute(vehicle))!=offer['prior_route'] or conn.vehicle.getTypeID(vehicle)!=offer['type']:
        raise ValueError('route_or_class_changed')
    bypass=offer['route']; incoming=bypass[1]
    lanes=[f'{incoming}_{i}' for i in range(conn.edge.getLaneNumber(incoming))]
    ratio=max((conn.lane.getLastStepVehicleNumber(l)/max(1,conn.lane.getLength(l)/7.5) for l in lanes),default=None)
    validate_diversion(vehicle_id=vehicle,addressed_vehicle=offer['vehicle_id'],accepted=c.get('accepted'),
        now=now,expiry=offer['expires_sim_s'],current_edge=current,decision_edge=decision,queue_ratio=ratio,route_valid=True)
    validator=c.get('_validate_phone_accept')
    if not callable(validator): raise ValueError('phone_session_validation_required')
    validator(now)
    conn.vehicle.setRoute(vehicle,bypass)
    if list(conn.vehicle.getRoute(vehicle))!=bypass: raise RuntimeError('route_not_confirmed')
    offer['status']='applied'; engine._manifest['scenario_mutated']=True
    engine._events.append({'kind':'driver_route_applied','vehicle_id':vehicle,'advisory_id':offer['advisory_id'],
                          'sim_time_s':now,'source_type':'phone_sample','receiving_space_source':'simulated_sensor'})
    engine._publish(); engine._save(); return engine.snapshot()


class UnifiedMobileBridge(MobileBridge):
    def __init__(self,engine):
        self.enabled=False; self.rules={}; self.offers={}
        super().__init__(engine)
    def sync(self):
        previous=self.sessions.run_id if self.sessions else None
        state=super().sync()
        if previous!=state['run_id']:
            self.enabled=False; self.rules={}; self.offers={}
        self.enabled=state.get('guidance_enabled',False)
        for key,offer in list(self.offers.items()):
            if offer.get('status')=='pending' and state['sim_time_s']>=offer['expires_sim_s']:
                offer['status']='expired'; self.guidance.pop(key,None)
        while len(self.offers)>256:
            key=next(iter(self.offers)); self.offers.pop(key); self.guidance.pop(key,None)
        if not self.enabled:
            self.guidance.clear()
            for offer in self.offers.values():
                if offer.get('status')=='pending': offer['status']='cancelled'
        return state
    async def dispatch(self,session,message):
        kind=message['type']
        if kind=='driver.decision' and message['payload']['advisory_id'] in self.offers:
            duplicate=self.check_input(session,message)
            if duplicate: return duplicate
            state=self.sync(); offer=self.offers[message['payload']['advisory_id']]
            if offer['vehicle_id']!=session.vehicle_id: raise ValueError('wrong_vehicle')
            if offer.get('status')!='pending': raise ValueError('duplicate_or_cancelled_advisory')
            if state['sim_time_s']>=offer['expires_sim_s']: raise ValueError('expired_advisory')
            if message['payload']['choice']=='ignore':
                offer['status']='ignored'; self.guidance.pop(offer['advisory_id'],None)
                return 'applied','original_route_kept'
            observation=self.aggregator.snapshot(offer['evidence_edge'],state['sim_time_s'])
            if not self.enabled or not session.connected or not session.reporting or observation.coverage!='fresh' or observation.fresh_probes<2 or observation.slowdown is None or observation.slowdown<.45:
                raise ValueError('phone_evidence_unavailable')
            store=self.sessions
            def validate_current(now):
                current=self.aggregator.snapshot(offer['evidence_edge'],now)
                if store is not self.sessions or store.run_id!=state['run_id'] or not session.connected or not session.reporting or not self.enabled or offer.get('status')!='pending' or current.coverage!='fresh' or current.fresh_probes<2 or current.slowdown is None or current.slowdown<.45:
                    raise ValueError('phone_evidence_or_consent_withdrawn')
            result=await asyncio.wrap_future(self.engine.command({'action':'phone_accept','run_id':state['run_id'],
                'vehicle_id':session.vehicle_id,'advisory_id':offer['advisory_id'],'accepted':True,
                '_validate_phone_accept':validate_current}))
            offer['status']='applied'; self.guidance.pop(offer['advisory_id'],None)
            return 'applied','route_applied'
        result=await super().dispatch(session,message)
        if kind=='probe.sample' and result[1]=='sample_accepted' and self.enabled:
            state=self.sync(); edge=message['payload']['pose']['edge_id']
            observation=self.aggregator.snapshot(edge,state['sim_time_s'])
            row={**observation.to_payload(),'fresh_probes':observation.fresh_probes}
            rule=self.rules.setdefault(edge,DemoRules()); rule.enabled=True
            evidence=rule.update(row,state['sim_time_s'])
            if evidence and not any(o['vehicle_id']==session.vehicle_id and o.get('status') in ('pending','applied') for o in self.offers.values()):
                try: offer=await asyncio.wrap_future(self.engine.command({'action':'phone_offer','run_id':state['run_id'],'vehicle_id':session.vehicle_id}))
                except ValueError: return result
                self.offers[offer['advisory_id']]={**offer,'evidence_edge':edge,'status':'pending'}
                self.guidance[offer['advisory_id']]=offer
        return result
