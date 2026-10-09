"""Isolated mentoring experiment; never changes the running 8002 demo."""
import asyncio
from collections import Counter
from copy import deepcopy
import hashlib
import json
import random
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from backend.control import SignalState, extension_remaining
from .demo_engine import DemoEngine


def extension_plan(row):
    if row['already_extended']: raise ValueError('Already extended this phase')
    if 'y' in row['state'].lower() or 'G' not in row['state']: raise ValueError('Preserve clearance / wait for protected green')
    if row['elapsed_s']<10: raise ValueError('Minimum green not reached')
    if row['queue']<2: raise ValueError('No sustained queue to serve')
    if row['opposing_queue']>row['queue']: raise ValueError('Larger opposing queue: retain fixed timing')
    occupancy=row['downstream_occupancy']
    if occupancy is None or not 0<=occupancy<.35: raise ValueError('Receiving lanes unknown or busy')
    return extension_remaining(SignalState('green',row['elapsed_s'],row['remaining_s']),True)


class ResponseEngine(DemoEngine):
    def _reset(self,scenario=None,seed=None):
        self._sensor_ready=False; self._varied=set(); self._extensions=set(); self._smart=False
        super()._reset(scenario,seed)
        # Additional departures are explicit, reproducible inputs, not fabricated observations.
        extra=[]
        for i in range(60):
            kind=self.config['cohort'][i%len(self.config['cohort'])]
            vehicle=f'{kind}.response.{i}'
            depart=5+i*2.5
            self._conn.vehicle.add(vehicle,'route.demo.A',typeID=kind,depart=str(depart),departLane='free',departSpeed='0')
            self.routes[vehicle]='route.demo.A';self.roles[vehicle]=kind.title()
            extra.append(dict(id=vehicle,type=kind,depart=depart,route='route.demo.A'))
        self.scheduled=72
        self.config["horizon_s"]=2400
        spec=dict(profile='mentoring-response-v1',extra_departures=extra,speed_factor_range=[.85,1.05],
                  sensing='SIMULATED FULL-LANE SENSORS',green_extension_s=5,max_green_s=40,
                  source_type='assumed',field_calibrated=False)
        (self.run_dir/'response-inputs.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
        self._manifest['scheduled']=72
        self._manifest['scenario']='scenario.lig.response.experimental.v1'
        self._manifest['response_inputs']=spec
        self._manifest['scenario_sha256']=hashlib.sha256(json.dumps([self.config,spec],sort_keys=True).encode()).hexdigest()
        self._manifest['demand_sha256']=hashlib.sha256((self.run_dir/'demand.rou.xml').read_bytes()+json.dumps(extra,sort_keys=True).encode()).hexdigest()
        import traci.constants as tc
        self._lane_variables=(tc.LAST_STEP_VEHICLE_NUMBER,tc.LAST_STEP_VEHICLE_HALTING_NUMBER,tc.LAST_STEP_MEAN_SPEED,tc.LAST_STEP_OCCUPANCY)
        self._signal_links={sid:self._conn.trafficlight.getControlledLinks(sid) for sid in self._conn.trafficlight.getIDList()}
        from .engine import WORLD
        self._signals=[]
        for sid,links in self._signal_links.items():
            positions=[]
            for group in links:
                if group:
                    x,y=self._conn.lane.getShape(group[0][0])[-1]
                    positions.append([x-WORLD['center'][0],y-WORLD['center'][1]])
                else:positions.append(None)
            self._signals.append(dict(id=sid,positions=positions))
        lanes={lane for links in self._signal_links.values() for group in links for link in group for lane in link[:2]}
        for lane in lanes:self._conn.lane.subscribe(lane,self._lane_variables)
        self._sensor_ready=True
        self._vary_drivers();self._publish()

    def _vary_drivers(self):
        for vehicle in sorted(set(self._conn.vehicle.getIDList())-self._varied):
            seed=int(hashlib.sha256((str(self.seed)+vehicle).encode()).hexdigest()[:16],16)
            self._conn.vehicle.setSpeedFactor(vehicle,random.Random(seed).uniform(.85,1.05))
            self._varied.add(vehicle)

    def _step(self,publish=True):
        super()._step(publish)
        if self._sensor_ready:
            self._vary_drivers()
            if self._smart and not self._snapshot.get('ended'):
                for row in self._signal_rows():
                    if row['recommended']:self._apply_extension(row,automatic=True)
                if publish:self._publish()

    def _signal_rows(self):
        conn=self._conn;now=conn.simulation.getTime();rows=[]
        lane_data=conn.lane.getAllSubscriptionResults()
        vn,vh,vs,vo=self._lane_variables
        for sid in conn.trafficlight.getIDList():
            state=conn.trafficlight.getRedYellowGreenState(sid)
            elapsed=conn.trafficlight.getSpentDuration(sid)
            links=self._signal_links[sid]
            incoming={link[0] for group in links for link in group}
            green_in={link[0] for i,group in enumerate(links) if state[i]=='G' for link in group}
            receiving={link[1] for i,group in enumerate(links) if state[i] in 'Gg' for link in group}
            if any(l not in lane_data or any(v not in lane_data[l] for v in self._lane_variables) for l in incoming):
                raise RuntimeError('Simulated approach sensor unavailable')
            lanes=[]
            for lane in sorted(incoming):
                data=lane_data.get(lane,{})
                n=data.get(vn,0)
                lanes.append(dict(lane=lane,count=n,stopped=data.get(vh,0),
                                  speed_kph=round(data[vs]*3.6,1) if n and vs in data else None))
            phase_key=f'{sid}:{conn.trafficlight.getPhase(sid)}:{now-elapsed:.3f}'
            row=dict(id=sid,state=state,phase=conn.trafficlight.getPhase(sid),phase_key=phase_key,
                     elapsed_s=elapsed,remaining_s=max(0,conn.trafficlight.getNextSwitch(sid)-now),
                     count=sum(x['count'] for x in lanes),stopped=sum(x['stopped'] for x in lanes),lanes=lanes,
                     queue=sum(x['stopped'] for x in lanes if x['lane'] in green_in),
                     opposing_queue=sum(x['stopped'] for x in lanes if x['lane'] not in green_in),
                     downstream_occupancy=max((lane_data[l][vo]/100 for l in receiving if l in lane_data and vo in lane_data[l]),default=None),
                     already_extended=phase_key in self._extensions)
            if any(l not in lane_data or vo not in lane_data[l] for l in receiving):row['downstream_occupancy']=None
            try:row['proposed_remaining_s']=extension_plan(row);row['recommended']=True;row['reason']='Serve the queued protected-green approach for up to 5 more seconds'
            except ValueError as exc:row['recommended']=False;row['reason']=str(exc)
            rows.append(row)
        return rows

    def _publish_complete(self,values=None):
        super()._publish_complete(values)
        if not self._sensor_ready:return
        self._snapshot['response']=dict(source='SIMULATED FULL-LANE SENSORS',smart_enabled=self._smart,
            mode='Queue-responsive control' if self._smart else 'Fixed timing / manual approval',
            signals=self._signal_rows(),vehicle_types=dict(Counter(v['type'] for v in self._snapshot['vehicles'])),
            audit=[e for e in self._events if e['kind']=='signal_extension'][-10:])
        self._snapshot['demo']['name']='LIG response experiment · 72 assumed departures'
        if self._frames:self._frames[-1]=deepcopy(self._snapshot)

    def _execute(self,c):
        if c['action']=='response_smart':
            if c['run_id']!=self.run_id:raise ValueError('Wrong run: refresh')
            self._smart=c['enabled']
            self._events.append(dict(kind='smart_mode',enabled=self._smart,sim_time_s=self._conn.simulation.getTime()))
            self._publish();self._save();return self.snapshot()
        if c['action']!='response_extend':return super()._execute(c)
        if c['run_id']!=self.run_id:raise ValueError('Wrong run: refresh')
        row=next((s for s in self._signal_rows() if s['id']==c['signal_id']),None)
        if not row or row['phase_key']!=c['phase_key']:raise ValueError('Phase changed: refresh recommendation')
        self._apply_extension(row,automatic=False)
        self._publish();self._save();return self.snapshot()

    def _apply_extension(self,row,automatic):
        remaining=extension_plan(row)
        self._conn.trafficlight.setPhaseDuration(row['id'],remaining)
        self._extensions.add(row['phase_key'])
        event=dict(kind='signal_extension',sim_time_s=self._conn.simulation.getTime(),signal_id=row['id'],
                   previous_remaining_s=row['remaining_s'],remaining_s=remaining,phase_key=row['phase_key'],
                   source='simulated_fixed_sensor',operator_approved=not automatic,
                   controller='queue_responsive' if automatic else 'manual',
                   queue=row['queue'],opposing_queue=row['opposing_queue'],
                   downstream_occupancy=row['downstream_occupancy'])
        self._events.append(event)
        with (self.run_dir/'response-actions.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')


class SmartRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    run_id:str
    enabled:bool


class ExtendRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    run_id:str
    signal_id:str
    phase_key:str


def create_response_app():
    from .app import create_app,WEB
    from .demo_bridge import DemoBridge
    app=create_app(engine_factory=ResponseEngine,bridge_factory=DemoBridge,demo=True)
    @app.get('/response')
    def page():return FileResponse(WEB/'response.html')
    @app.get('/api/response')
    def status(request:Request):
        app.state.mobile.authorize(request)
        state=app.state.engine.snapshot()
        if state.get('error'):raise HTTPException(503,'Simulation unavailable')
        return state
    @app.post('/api/response/extend')
    async def extend(body:ExtendRequest,request:Request):
        app.state.mobile.authorize(request)
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):raise HTTPException(403,'Cross-origin control disabled')
        try:return await asyncio.wait_for(asyncio.wrap_future(app.state.engine.command(dict(action='response_extend',**body.model_dump()))),10)
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        except (RuntimeError,asyncio.TimeoutError) as exc:raise HTTPException(503,'Simulation unavailable') from exc
    @app.post('/api/response/smart')
    async def smart(body:SmartRequest,request:Request):
        app.state.mobile.authorize(request)
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):raise HTTPException(403,'Cross-origin control disabled')
        try:return await asyncio.wait_for(asyncio.wrap_future(app.state.engine.command(dict(action='response_smart',**body.model_dump()))),10)
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        except (RuntimeError,asyncio.TimeoutError) as exc:raise HTTPException(503,'Simulation unavailable') from exc
    return app
