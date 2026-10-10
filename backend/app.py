"""Offline fixture server. No SUMO connection and no performance claims."""
import asyncio
import contextlib
import json
import os
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from jsonschema import Draft202012Validator, ValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.probes import ProbeGateway
from backend.session import SessionStore

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'contracts/contracts.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    join_code: str = Field(min_length=1, max_length=128)


def create_app():
    sessions = SessionStore()
    gateway = ProbeGateway(sessions.run_id)
    started = time.monotonic()
    sequence = 0

    def sim_time():
        return int((time.monotonic() - started) // 5) * 5

    def event(kind, payload, stamp=None):
        nonlocal sequence
        sequence += 1
        result = dict(v=1, type=kind, msg_id=f'msg.server.{sequence}', run_id=sessions.run_id,
                      sender_id='server', seq=sequence, sim_time_s=sim_time() if stamp is None else stamp, payload=payload)
        VALIDATOR.validate(result)
        return result

    def snapshot(session):
        return dict(mode='fixed', paused=False, rate=1, observations=[], forecasts=[], signals=[],
                    drivers=[dict(session_id=session.session_id, vehicle_id=session.vehicle_id,
                                  connected=True, reporting=session.reporting, last_seen_wall_ms=time.time() * 1000)],
                    counts=dict(scheduled=0, departed=0, arrived=0, active=0, pending=0, teleported=0, removed=0),
                    metrics=dict(complete=False, mean_journey_s=None, p95_journey_s=None,
                                 total_wait_s=0, co2_kg_so_far=0, co2_kg_final=None), active_guidance=[], proposals=[],
                    simulation_view=dict(label='SIMULATION GROUND TRUTH - DISPLAY ONLY', roads=[]),
                    baseline=dict(status='unavailable', recording_id=None, sim_time_s=None, roads=[], counts=None, metrics=None))

    async def send_frame(ws, session):
        stamp = sim_time()
        frame = event('vehicle.frame', dict(frame_id=f'frame.{session.vehicle_id}.{stamp}',
                      vehicle_id=session.vehicle_id, state='active',
                      pose=dict(edge_id='edge.market', x_m=200 + stamp % 100, y_m=100, speed_mps=2.0)), stamp)
        gateway.issue(session.session_id, frame)
        await ws.send_json(frame)

    @asynccontextmanager
    async def lifespan(app):
        yield

    app = FastAPI(title='Traffix fixture server', lifespan=lifespan)
    hosts = ['localhost', '127.0.0.1', '::1', 'testserver']
    with contextlib.suppress(OSError):
        hosts.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    hosts.extend(h.strip() for h in os.environ.get('TRAFFIX_ALLOWED_HOSTS', '').split(',') if h.strip())
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    app.state.sessions = sessions
    app.state.gateway = gateway

    @app.get('/healthz')
    def health():
        return dict(status='ok', source='FAKE FIXTURE', run_id=sessions.run_id)

    @app.get('/api/bootstrap')
    def bootstrap():
        return dict(v=1, run_id=sessions.run_id, scenario_id='scenario.fixture',
                    scenario_label='FAKE FIXTURE — no SUMO', ws_path='/ws')

    @app.post('/api/claim')
    def claim(body: ClaimRequest):
        try:
            return sessions.claim(body.join_code)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    def local_only(request):
        if request.client.host not in ('127.0.0.1', '::1', 'testclient'):
            raise HTTPException(403, 'Open the setup page on the laptop at localhost.')

    @app.get('/setup', response_class=HTMLResponse)
    def setup(request: Request):
        local_only(request)
        return (ROOT / 'backend/fixture_setup.html').read_text(encoding='utf-8')

    @app.post('/api/fixture/join/{role}')
    def join(role: str, request: Request):
        local_only(request)
        try:
            return dict(join_code=sessions.issue('veh.role.' + role), expires_in_wall_s=120)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get('/driver', response_class=HTMLResponse)
    def driver():
        return (ROOT / 'backend/fixture_driver.html').read_text(encoding='utf-8')

    @app.get('/api/fixture/qr')
    def qr(request: Request, url: str):
        local_only(request)
        address = urlsplit(url)
        if (address.hostname not in hosts or address.scheme not in ('http', 'https')
                or address.path != '/driver' or not address.fragment.startswith('join=') or len(url) > 512):
            raise HTTPException(422, 'Use an allowed laptop address and driver join link.')
        try:
            import qrcode
            import qrcode.image.svg
        except ImportError as exc:
            raise HTTPException(503, 'Install requirements with the project virtual environment.') from exc
        image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
        return Response(image.to_string(), media_type='image/svg+xml')

    @app.get('/api/fixture/status')
    def status(request: Request):
        local_only(request)
        gateway.prune_samples(sim_time())
        return dict(source='FAKE FIXTURE', sim_time_s=sim_time(), accepted_samples=len(gateway.samples),
                    drivers=[dict(vehicle_id=s.vehicle_id, connected=s.connected,
                                  reporting=s.reporting) for s in sessions.sessions.values()])

    @app.websocket('/ws')
    async def websocket(ws: WebSocket):
        origin = ws.headers.get('origin')
        if origin and (urlsplit(origin).netloc != ws.headers.get('host') or urlsplit(origin).scheme not in ('http', 'https')):
            await ws.close(code=1008)
            return
        await ws.accept()
        session = None
        producer = None

        async def receive():
            raw = await ws.receive_text()
            if len(raw.encode('utf-8')) > 16384:
                raise ValueError('message_too_large')
            data = json.loads(raw)
            VALIDATOR.validate(data)
            return data

        async def produce():
            last = sim_time()
            while True:
                await asyncio.sleep(.25)
                if time.monotonic() - session.last_seen > 6:
                    await ws.close(code=1008, reason='heartbeat_timeout')
                    return
                if sim_time() != last:
                    last = sim_time()
                    await send_frame(ws, session)

        try:
            hello = await asyncio.wait_for(receive(), timeout=6)
            if hello.get('type') != 'session.hello':
                raise ValueError('hello_required')
            session = sessions.authenticate(hello)
            if session.socket is not None:
                await session.socket.close(code=1000, reason='replaced_by_reconnect')
            session.socket = ws
            session.connected = True
            session.last_seen = time.monotonic()
            await ws.send_json(event('session.ready', dict(session_id=session.session_id, role='driver',
                                                         vehicle_id=session.vehicle_id, mode='fixed')))
            await ws.send_json(event('world.snapshot', snapshot(session)))
            await send_frame(ws, session)
            producer = asyncio.create_task(produce())
            received = []
            while True:
                msg = await receive()
                now = time.monotonic()
                received = [t for t in received if now - t < 1]
                received.append(now)
                if len(received) > 20:
                    raise ValueError('rate_limit')
                if msg['sender_id'] != session.session_id or msg['run_id'] != sessions.run_id:
                    raise ValueError('wrong_session_or_run')
                session.last_seen = now
                kind = msg['type']
                status, reason = 'applied', 'accepted'
                if msg['seq'] <= session.last_seq:
                    status, reason = 'duplicate', 'sequence_already_processed'
                else:
                    session.last_seq = msg['seq']
                    try:
                        if kind == 'heartbeat':
                            continue
                        if kind == 'probe.toggle':
                            session.reporting = msg['payload']['enabled']
                        elif kind == 'probe.sample':
                            if not session.reporting:
                                raise ValueError('reporting_disabled')
                            gateway.accept(session.session_id, session.vehicle_id, msg, sim_time())
                        else:
                            raise ValueError('unsupported_in_fixture_server')
                    except ValueError as exc:
                        reason = str(exc)
                        status = 'duplicate' if reason == 'duplicate' else 'rejected'
                await ws.send_json(event('ack', dict(in_reply_to=msg['msg_id'], status=status, reason=reason)))
        except (ValueError, KeyError, ValidationError, asyncio.TimeoutError):
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await ws.close(code=1008, reason='invalid_or_unauthenticated_message')
        except WebSocketDisconnect:
            pass
        finally:
            if producer:
                producer.cancel()
                with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                    await producer
            if session and session.socket is ws:
                session.connected = False
                session.socket = None

    return app


app = create_app()
