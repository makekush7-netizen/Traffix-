"""Authenticated phone bridge. Reads snapshots; never owns or calls TraCI."""
import asyncio
from collections import deque
from copy import deepcopy
import contextlib
import json
import secrets
import socket
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from jsonschema import ValidationError

from backend.app import ClaimRequest, VALIDATOR
from backend.session import SessionStore
from backend.probes import ProbeGateway
from ml.observations import ObservationAggregator, ProbeSample
from ml.forecast import ForecastService, HORIZONS
from .engine import WORLD


class JoinRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vehicle_id: str = Field(min_length=1, max_length=128)


class AdvisoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_id: str = Field(min_length=1,max_length=128)
    message: str = Field(min_length=1,max_length=240)


class MobileBridge:
    def __init__(self, engine):
        self.engine = engine
        self.operator_token = secrets.token_urlsafe(32)
        self.edge_ids = {r['id']: f'edge.lig.{i}' for i,r in enumerate(WORLD['roads'])}
        self.references = {self.edge_ids[r['id']]:r['speed'] for r in WORLD['roads'] if r['speed']>0}
        self.sessions = None
        self.sequence = 0
        self.audit = deque(maxlen=2000)
        self.sync()

    def sync(self):
        state = self.engine.snapshot()
        if not state.get('ready'):
            raise HTTPException(503,'Simulation is starting')
        if state.get('error'):
            raise HTTPException(503,'Simulation unavailable; restart the demo and rejoin phones')
        if self.sessions is None or self.sessions.run_id != state['run_id']:
            self.audit.clear()
            self.sessions = SessionStore(vehicles=[v['id'] for v in state['vehicles']],run_id=state['run_id'])
            self.gateway = ProbeGateway(state['run_id'])
            self.aggregator = ObservationAggregator(self.references)
            self.history = {}
            self.forecaster = ForecastService()
            self.forecasts = []
            self.accepted = 0
            self.last_tick = -1
            self.guidance = {}
            self.seen_messages = {}
        self.sessions.vehicles = tuple(v['id'] for v in state['vehicles'])
        return state

    def authorize(self, request):
        self.same_origin(request)
        if not secrets.compare_digest(request.headers.get('authorization','').encode(), ('Bearer '+self.operator_token).encode()):
            raise HTTPException(403,'Operator authentication required')

    @staticmethod
    def same_origin(request):
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc != request.headers.get('host'):
            raise HTTPException(403,'Cross-origin access disabled')

    def event(self, kind, payload, stamp=None):
        self.sequence += 1
        message=dict(v=1,type=kind,msg_id=f'msg.server.{self.sequence}',run_id=self.sessions.run_id,
                     sender_id='server',seq=self.sequence,sim_time_s=self.engine.snapshot()['sim_time_s'] if stamp is None else stamp,payload=payload)
        VALIDATOR.validate(message)
        return message

    def withdraw(self, session):
        session.reporting=False
        vehicle=session.vehicle_id
        self.aggregator.samples=deque((s for s in self.aggregator.samples if s.vehicle_id!=vehicle),maxlen=100000)
        self.gateway.samples[:]=[s for s in self.gateway.samples if s['session_id']!=session.session_id]
        # Withdraw historical contribution too: cached forecasts cannot retain consented data.
        self.history.clear()
        self.forecasts=[]
        self.guidance={key:value for key,value in self.guidance.items() if value['vehicle_id']!=vehicle}
        self.last_tick=-1

    def observations(self, now):
        edges={s.edge_id for s in self.aggregator.samples} | set(self.history)
        return [self.aggregator.snapshot(edge,now).to_payload() for edge in sorted(edges)]

    def status(self):
        state=self.sync(); now=state['sim_time_s']
        for session in self.sessions.sessions.values():
            if session.connected and time.monotonic()-session.last_seen>6:
                session.connected=False
                self.withdraw(session)
        self.gateway.prune_samples(now)
        self.aggregator.samples=deque((s for s in self.aggregator.samples if now-s.sim_time_s<=60),maxlen=100000)
        observations=self.observations(now)
        if now-self.last_tick>=5:
            self.last_tick=now; self.forecasts=[]
            for row in observations:
                edge=row['edge_id']; history=self.history.setdefault(edge,deque(maxlen=120))
                history.append(self.aggregator.snapshot(edge,now))
                for horizon in HORIZONS:
                    self.forecasts.append(self.forecaster.predict(history,horizon,method='trend',intervention_active=False).to_payload())
        bound={s.vehicle_id for s in self.sessions.sessions.values()}
        coverage={row['edge_id']:row['coverage'] for row in observations}
        forecasts=deepcopy(self.forecasts)
        for forecast in forecasts:
            forecast['usable_for_control']=False
            if coverage.get(forecast['edge_id'])!='fresh':
                forecast.update(predicted_slowdown=None,reason='unknown_or_stale')
            elif forecast['reason']=='ready': forecast['reason']='live_control_disabled'
        return dict(run_id=state['run_id'],sim_time_s=now,paused=state['paused'],accepted_uplinks=self.accepted,
                    observations=observations,forecasts=forecasts,unobserved_roads='unknown',
                    sessions=[dict(session_id=s.session_id,vehicle_id=s.vehicle_id,connected=s.connected,reporting=s.reporting)
                              for s in self.sessions.sessions.values()],
                    available_vehicles=[dict(id=v['id'],type=v['type']) for v in state['vehicles'] if v['id'] not in bound],
                    audit=list(self.audit)[-80:],model='Prototype trend forecast; no automatic intervention')

    def frame(self, session):
        state=self.sync()
        vehicle=next((v for v in state['vehicles'] if v['id']==session.vehicle_id),None)
        pose=None
        if vehicle:
            pose=dict(edge_id=self.edge_ids[vehicle['edge_id']],x_m=vehicle['x'],y_m=vehicle['y'],speed_mps=vehicle['speed'])
        frame=self.event('vehicle.frame',dict(frame_id=f'frame.{session.vehicle_id}.{int(state["sim_time_s"]*4)}',
                         vehicle_id=session.vehicle_id,state='active' if vehicle else 'arrived',pose=pose),state['sim_time_s'])
        self.gateway.issue(session.session_id,frame)
        return frame

    def check_input(self, session, message):
        if message['run_id']!=self.sessions.run_id or message['sender_id']!=session.session_id:
            raise ValueError('wrong_session_or_run')
        if message['seq']<=session.last_seq:
            return 'duplicate','sequence_already_seen'
        session.last_seq=message['seq']
        seen=self.seen_messages.setdefault(session.session_id,deque(maxlen=512))
        if message['msg_id'] in seen: return 'duplicate','message_already_seen'
        seen.append(message['msg_id'])
        return None

    def apply(self, session, message):
        state=self.sync(); now=state['sim_time_s']; kind=message['type']; payload=message['payload']
        duplicate=self.check_input(session,message)
        if duplicate: return duplicate
        if kind=='heartbeat':
            session.last_seen=time.monotonic()
            return 'received','heartbeat'
        if kind=='probe.toggle':
            if payload['enabled']: session.reporting=True
            else: self.withdraw(session)
            return 'applied','sharing_on' if session.reporting else 'sharing_off'
        if kind=='probe.sample':
            if not session.reporting: raise ValueError('sharing_disabled')
            accepted=self.gateway.accept(session.session_id,session.vehicle_id,message,now)
            pose=accepted['pose']
            self.aggregator.add_probe(ProbeSample(session.vehicle_id,pose['edge_id'],accepted['sim_time_s'],pose['speed_mps']))
            self.accepted+=1
            return 'applied','sample_accepted'
        if kind=='driver.decision':
            advisory=self.guidance.get(payload['advisory_id'])
            if not advisory or advisory['vehicle_id']!=session.vehicle_id: raise ValueError('unknown_advisory')
            if now>=advisory['expires_sim_s']: raise ValueError('expired_advisory')
            if advisory['kind']!='incident': raise ValueError('route_action_unavailable')
            del self.guidance[payload['advisory_id']]
            self.audit.append(dict(run_id=state['run_id'],sim_time_s=now,vehicle_id=session.vehicle_id,
                                   category='advisory_'+payload['choice'],source='driver_decision',status='acknowledged'))
            return 'applied','advisory_acknowledged_no_route_change'
        if kind=='driver.report':
            frame=self.gateway.frames.get((session.session_id,payload['frame_id']))
            if payload['vehicle_id']!=session.vehicle_id: raise ValueError('wrong_vehicle')
            if not frame or frame['payload']['state']!='active': raise ValueError('unknown_frame')
            if not 0<=now-frame['sim_time_s']<=15 or message['sim_time_s']!=frame['sim_time_s']: raise ValueError('stale_or_altered_frame')
            self.audit.append(dict(run_id=state['run_id'],sim_time_s=now,vehicle_id=session.vehicle_id,
                                   category=payload['category'],source='driver_report',status='unverified'))
            return 'received','report_received_unverified'
        raise ValueError('action_not_available')

    async def dispatch(self, session, message):
        return self.apply(session,message)

    async def serve(self, ws):
        session=None; producer=None; store=None
        try:
            self.same_origin(ws)
            await ws.accept()
            raw=await asyncio.wait_for(ws.receive_text(),timeout=5)
            if len(raw)>16384: raise ValueError('message_too_large')
            message=json.loads(raw); VALIDATOR.validate(message)
            if message['type']!='session.hello': raise ValueError('hello_required')
            self.sync(); store=self.sessions; session=store.authenticate(message)
            if message['seq']<=session.last_seq: raise ValueError('replayed_hello')
            if session.socket:
                await session.socket.close(code=1000,reason='replaced')
            session.socket=ws; session.connected=True; session.last_seen=time.monotonic()
            self.withdraw(session)
            session.last_seq=message['seq']
            await ws.send_json(self.event('session.ready',dict(session_id=session.session_id,role='driver',vehicle_id=session.vehicle_id,mode='fixed')))
            async def produce():
                last_frame=None; delivered=set()
                while True:
                    try: self.sync()
                    except HTTPException:
                        await ws.close(code=1011,reason='simulation_unavailable'); return
                    if store is not self.sessions:
                        await ws.close(code=1008,reason='run_reset'); return
                    if time.monotonic()-session.last_seen>6:
                        await ws.close(code=1008,reason='heartbeat_timeout'); return
                    frame=self.frame(session)
                    key=frame['payload']['frame_id']
                    if key!=last_frame:
                        await ws.send_json(frame); last_frame=key
                    for advisory in list(self.guidance.values()):
                        if advisory['vehicle_id']==session.vehicle_id and advisory['advisory_id'] not in delivered and frame['sim_time_s']<advisory['expires_sim_s']:
                            await ws.send_json(self.event('guidance',advisory)); delivered.add(advisory['advisory_id'])
                    await asyncio.sleep(.2)
            producer=asyncio.create_task(produce())
            budget=deque()
            while True:
                raw=await ws.receive_text()
                if len(raw)>16384: raise ValueError('message_too_large')
                message=json.loads(raw); VALIDATOR.validate(message)
                now=time.monotonic()
                while budget and now-budget[0]>1: budget.popleft()
                if len(budget)>=20: raise ValueError('rate_limit')
                budget.append(now)
                try: status,reason=await self.dispatch(session,message)
                except ValueError as exc:
                    reason=str(exc); status='duplicate' if reason=='duplicate' else 'rejected'
                await ws.send_json(self.event('ack',dict(in_reply_to=message['msg_id'],status=status,reason=reason)))
        except (ValueError,ValidationError,json.JSONDecodeError,asyncio.TimeoutError,HTTPException):
            with contextlib.suppress(RuntimeError,WebSocketDisconnect): await ws.close(code=1008,reason='invalid_session_or_message')
        except (WebSocketDisconnect,RuntimeError): pass
        finally:
            if producer:
                producer.cancel()
                with contextlib.suppress(asyncio.CancelledError,RuntimeError,WebSocketDisconnect): await producer
            if session and session.socket is ws:
                session.socket=None; session.connected=False
                if store is self.sessions: self.withdraw(session)


def attach_mobile(app, engine):
    # Instantiate after the SUMO worker starts; handlers share one asyncio loop.
    def bridge(): return app.state.mobile

    @app.get('/api/operator/bootstrap')
    async def operator_bootstrap(request:Request):
        bridge().same_origin(request)
        if request.client.host not in ('127.0.0.1','::1','testclient'):
            raise HTTPException(403,'Open the dashboard on this laptop at localhost')
        return Response(json.dumps({'token':bridge().operator_token}),media_type='application/json',headers={'Cache-Control':'no-store'})

    @app.get('/api/operator/state')
    async def operator_state(request:Request):
        bridge().authorize(request)
        return bridge().status()

    @app.post('/api/operator/join')
    async def issue_join(body:JoinRequest,request:Request):
        bridge().authorize(request); bridge().sync()
        try: code=bridge().sessions.issue(body.vehicle_id)
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
        addresses=[]
        with contextlib.suppress(OSError):
            addresses=sorted((ip for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                              if not ip.startswith(('127.','169.254.'))),key=lambda ip:(not ip.startswith('192.168.'),ip))
        return dict(join_code=code,expires_wall_s=120,vehicle_id=body.vehicle_id,lan_addresses=addresses)

    @app.post('/api/operator/advisory')
    async def advisory(body:AdvisoryRequest,request:Request):
        bridge().authorize(request); state=bridge().sync()
        session=bridge().sessions.sessions.get(body.session_id)
        if not session or not session.connected: raise HTTPException(409,'Phone is not connected')
        result=dict(advisory_id='advisory.'+secrets.token_hex(8),vehicle_id=session.vehicle_id,kind='incident',
                    route_id=None,message='Operator note (unverified): '+body.message,expires_sim_s=state['sim_time_s']+120)
        bridge().guidance[result['advisory_id']]=result
        return result

    @app.get('/api/operator/export')
    async def export(request:Request):
        bridge().authorize(request)
        data=engine.export(); data['phone_bridge']=bridge().status(); data['phone_edge_registry']=bridge().edge_ids
        return Response(json.dumps(data),media_type='application/json',headers={'Content-Disposition':'attachment; filename=traffix-phone-run.json'})

    @app.get('/api/bootstrap')
    async def bootstrap():
        state=bridge().sync()
        return dict(v=1,run_id=state['run_id'],scenario_id='scenario.lig.'+state['scenario'],scenario_label='LIG Square · simulated traffic',ws_path='/ws')

    @app.post('/api/claim')
    async def claim(body:ClaimRequest,request:Request):
        bridge().same_origin(request); bridge().sync()
        try: result=bridge().sessions.claim(body.join_code)
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
        return Response(json.dumps(result),media_type='application/json',headers={'Cache-Control':'no-store'})

    @app.get('/api/join-qr')
    async def qr(request:Request,url:str):
        bridge().authorize(request)
        import qrcode
        import io
        out=io.BytesIO(); qrcode.make(url).save(out,format='PNG')
        return Response(out.getvalue(),media_type='image/png',headers={'Cache-Control':'no-store'})

    @app.websocket('/ws')
    async def phone_stream(ws:WebSocket): await bridge().serve(ws)
