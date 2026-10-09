"""Demo guidance: validated phone evidence -> one offer -> explicit driver choice."""
import asyncio
from copy import deepcopy
import json
import secrets

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict
from .mobile import MobileBridge
from .demo_engine import BASELINE_PATH
from .demo_rules import DemoRules, road_colour, comparison, STAGES
from .engine import WORLD


class GuidanceToggle(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    enabled: bool


class DemoBridge(MobileBridge):
    def sync(self):
        previous=self.sessions.run_id if self.sessions else None
        state=super().sync()
        if previous!=state['run_id']:
            self.rules=DemoRules(); self.offers={}; self.offered=set(); self.alert=None; self.detected_once=False
            self.recording=json.loads(BASELINE_PATH.read_text(encoding='utf-8')) if BASELINE_PATH.exists() else None
        return state

    def set_guidance(self, enabled):
        self.sync(); self.rules.set_enabled(enabled); self.alert=None
        if not enabled:
            for key,offer in self.offers.items():
                if offer['status']=='pending':
                    offer['status']='cancelled'; self.guidance.pop(key,None)
                    self.log('guidance_cancelled',offer['vehicle_id'],'Guidance turned off. No route change.')
        self.log('guidance_enabled' if enabled else 'guidance_disabled',None,'Traffix guidance '+('on' if enabled else 'off'))

    def log(self, kind, vehicle, text):
        event=dict(run_id=self.sessions.run_id,sim_time_s=self.engine.snapshot()['sim_time_s'],
                   vehicle_id=vehicle,category=kind,source='demo_rule',status=text)
        self.audit.append(event)
        with (self.engine.run_dir/'phone-guidance.jsonl').open('a',encoding='utf-8') as output:
            output.write(json.dumps(event)+'\n')

    def status(self):
        data=super().status(); state=self.engine.snapshot(); now=state['sim_time_s']
        demo=state['demo']; decision=self.edge_ids[demo['decision_edge']]
        observation=self.aggregator.snapshot(decision,now)
        self.alert=self.rules.update({**observation.to_payload(),'fresh_probes':observation.fresh_probes},now)
        for key,offer in self.offers.items():
            if offer['status']=='pending' and now>=offer['expires_sim_s']:
                offer['status']='expired'; self.guidance.pop(key,None)
                self.log('guidance_expired',offer['vehicle_id'],'Offer expired. Original route continues.')
        pending=any(o['status']=='pending' for o in self.offers.values())
        if self.alert and not pending and not demo['applied_vehicles']:
            for session in self.sessions.sessions.values():
                if (session.connected and session.reporting and session.vehicle_id in demo['eligible_vehicles']
                        and session.vehicle_id not in self.offered and demo['bypass_queue_ratio'] is not None
                        and demo['bypass_queue_ratio']<=.35):
                    key='advisory.demo.'+secrets.token_hex(6)
                    offer=dict(advisory_id=key,vehicle_id=session.vehicle_id,kind='reroute',route_id='route.demo.B',
                               message='Slowdown ahead. Take Route B. It avoids the simulated waterlogged segment.',
                               expires_sim_s=now+self.engine.config['guidance_lifetime_s'])
                    self.guidance[key]=offer; self.offers[key]={**offer,'status':'pending'}
                    self.offered.add(session.vehicle_id); self.detected_once=True
                    self.log('guidance_offered',session.vehicle_id,self.alert['evidence'])
                    # Pause at the real event, giving the human time for a safe decision.
                    if not state['paused']: self.engine.command({'action':'pause'})
                    break
        scoped={self.edge_ids[e] for e in set(self.engine.config['route_a']+self.engine.config['route_b'])}
        observed=[o for o in data['observations'] if o['coverage']=='fresh' and o['edge_id'] in scoped]
        for o in data['observations']: o['colour']=road_colour(o)
        applied=demo['applied_vehicles']
        stage=3 if applied else 2 if self.detected_once else 1 if observed else 0
        data.update(demo_mode=True,name=self.engine.config['name'],guidance_enabled=self.rules.enabled,
                    stage=stage,stages=list(STAGES),alert=self.alert,roads_observed=len(observed),roads_total=len(scoped),
                    phones_reporting=sum(s.connected and s.reporting for s in self.sessions.sessions.values()),
                    freshest_age_s=min((o['sample_age_sim_s'] for o in observed),default=None),
                    integrity=dict(collisions=state['metrics']['collisions'],teleports=state['metrics']['teleports'],
                                   unfinished=state['metrics']['scheduled']-state['metrics']['arrived'],ended=state['ended']),
                    counts=state['metrics'],comparison=comparison(state['result'],self.recording),
                    offers=list(self.offers.values()),roles=demo['roles'],applied_vehicles=applied,
                    capacity_source=demo['capacity_source'],model='PROTOTYPE · phone slowdown rule; no trained-model decisions')
        return data

    async def dispatch(self, session, message):
        if message['type']!='driver.decision' or message['payload']['advisory_id'] not in self.offers:
            return await super().dispatch(session,message)
        try: return await self.route_decision(session,message)
        except ValueError as exc:
            self.log('driver_decision_rejected',session.vehicle_id,str(exc))
            raise

    async def route_decision(self, session, message):
        state=self.sync(); duplicate=self.check_input(session,message)
        if duplicate: return duplicate
        offer=self.offers[message['payload']['advisory_id']]
        if offer['vehicle_id']!=session.vehicle_id: raise ValueError('wrong_vehicle')
        if state['sim_time_s']>=offer['expires_sim_s']: raise ValueError('expired_advisory')
        if offer['status']=='applied': return 'duplicate','route_already_applied'
        if not self.rules.enabled or offer['status']!='pending': raise ValueError('guidance_turned_off')
        if message['payload']['choice']=='ignore':
            offer['status']='ignored'; self.guidance.pop(offer['advisory_id'],None)
            self.log('driver_ignored',session.vehicle_id,'Driver declined. Original route continues.')
            return 'applied','original_route_kept'
        observation=self.aggregator.snapshot(self.edge_ids[state['demo']['decision_edge']],state['sim_time_s'])
        if not session.connected or not session.reporting or observation.coverage!='fresh' or observation.fresh_probes<2 or observation.slowdown is None or observation.slowdown<.45:
            raise ValueError('phone_evidence_unavailable')
        future=self.engine.command(dict(action='demo_reroute',run_id=self.sessions.run_id,vehicle_id=session.vehicle_id,
                                        addressed_vehicle=offer['vehicle_id'],accepted=True,
                                        expires_sim_s=offer['expires_sim_s'],advisory_id=offer['advisory_id']))
        # Ack follows worker confirmation; the websocket handler never calls TraCI.
        try: await asyncio.wrap_future(future)
        except ValueError as exc:
            offer['status']='rejected'; self.guidance.pop(offer['advisory_id'],None)
            self.log('route_rejected',session.vehicle_id,str(exc)); raise
        offer['status']='applied'; self.guidance.pop(offer['advisory_id'],None)
        self.log('driver_route_applied',session.vehicle_id,'Driver accepted. Route applied.')
        return 'applied','route_applied'

    def driver_state(self, session):
        state=self.sync(); demo=state['demo']; vehicle=session.vehicle_id
        route=demo['routes'].get(vehicle,'route.demo.A')
        edges=demo['route_b'] if route=='route.demo.B' else demo['route_a']
        shapes={r['id']:r['shape'] for r in WORLD['roads']}
        own_offers=[o for o in self.offers.values() if o['vehicle_id']==vehicle]
        return dict(role=demo['roles'][vehicle],vehicle_id=vehicle,route_id=route,
                    route_path=[shapes[e] for e in edges],paused=state['paused'],reporting=session.reporting,
                    offer=deepcopy(own_offers[-1]) if own_offers else None,run_id=self.sessions.run_id,
                    ended=state['ended'],sim_time_s=state['sim_time_s'])


def attach_demo(app, engine):
    @app.post('/api/demo/guidance')
    async def guidance(body:GuidanceToggle,request:Request):
        app.state.mobile.authorize(request); app.state.mobile.set_guidance(body.enabled)
        return {'enabled':body.enabled}

    @app.get('/api/driver/state')
    async def driver_state(request:Request,session_id:str,run_id:str):
        bridge=app.state.mobile; bridge.same_origin(request); bridge.sync()
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        try:
            session=bridge.sessions.authenticate(dict(sender_id=session_id,run_id=run_id,payload={'token':token}))
        except ValueError as exc: raise HTTPException(403,str(exc)) from exc
        return bridge.driver_state(session)

    @app.get('/api/demo/recording')
    async def recording():
        if not BASELINE_PATH.exists(): raise HTTPException(404,'No recorded baseline available')
        return json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
