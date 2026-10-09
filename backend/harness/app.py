import asyncio
import contextlib
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .engine import HarnessEngine, WORLD, SCENARIOS
from .mobile import MobileBridge, attach_mobile

STATIC=Path(__file__).parent/'static'
WEB=Path(__file__).resolve().parents[2]/'web/src/mobile'


class Control(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action: Literal['play','pause','step','reset','set_rate','clear_incident']
    scenario: Literal['everyday','rush','rain','roadworks'] | None=None
    seed: int=Field(default=42,ge=0,le=999999)
    rate: Literal[1,2,4,8] | None=None


def create_app(engine_factory=HarnessEngine,bridge_factory=MobileBridge,demo=False):
    engine=engine_factory()
    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(engine.start)
        app.state.mobile=bridge_factory(engine)
        async def monitor():
            while True:
                try: app.state.mobile.status()
                except HTTPException:
                    pass  # Remain alive to expose the engine fault and permit safe shutdown.
                await asyncio.sleep(.2)
        monitor_task=asyncio.create_task(monitor())
        try:
            yield
        finally:
            monitor_task.cancel()
            try:
                with contextlib.suppress(asyncio.CancelledError): await monitor_task
            finally:
                await asyncio.to_thread(engine.stop)
    app=FastAPI(title='Traffix · LIG Square simulation lab',lifespan=lifespan)
    hosts=['localhost','127.0.0.1','::1','testserver']
    with contextlib.suppress(OSError): hosts.extend(socket.gethostbyname_ex(socket.gethostname())[2])
    hosts.extend(h.strip() for h in os.environ.get('TRAFFIX_ALLOWED_HOSTS','').split(',') if h.strip())
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=hosts)
    app.state.engine=engine
    app.mount('/static',StaticFiles(directory=STATIC),name='static')
    app.mount('/mobile',StaticFiles(directory=WEB),name='mobile')
    attach_mobile(app,engine)
    if demo:
        from .demo_bridge import attach_demo
        attach_demo(app,engine)
    @app.get('/driver')
    def driver(): return FileResponse(WEB/'driver.html')
    @app.get('/dashboard')
    def dashboard(): return FileResponse(WEB/'dashboard.html')
    @app.get('/')
    def index(): return FileResponse(WEB/'dashboard.html' if demo else STATIC/'index.html')
    @app.get('/api/world')
    def world():
        data={k:v for k,v in WORLD.items() if k not in ('routes','center','roads')}
        data['roads']=[dict(r,contract_edge_id=app.state.mobile.edge_ids[r['id']]) for r in WORLD['roads']]
        return data
    @app.get('/api/scenarios')
    def scenarios(): return SCENARIOS
    @app.get('/api/state')
    def state(): return engine.snapshot()
    @app.post('/api/control')
    async def control(body: Control,request:Request):
        app.state.mobile.authorize(request)
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):
            raise HTTPException(403,'Cross-origin control is disabled')
        try:
            return await asyncio.wait_for(asyncio.wrap_future(engine.command(body.model_dump(exclude_none=True))),timeout=40)
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
        except (RuntimeError,asyncio.TimeoutError) as exc: raise HTTPException(503,str(exc)) from exc
    @app.get('/api/export')
    def export():
        data=engine.export()
        return JSONResponse(data,headers={'Content-Disposition':f'attachment; filename="{data["manifest"]["run_id"]}.json"'})
    @app.websocket('/ws/lab')
    async def stream(ws:WebSocket):
        origin=ws.headers.get('origin')
        if origin and urlsplit(origin).netloc!=ws.headers.get('host'):
            await ws.close(code=1008);return
        await ws.accept()
        try:
            while True:
                await ws.send_json(engine.snapshot())
                await asyncio.sleep(.2)
        except (WebSocketDisconnect,RuntimeError): pass
    return app


app=create_app()


def create_demo_app():
    from .demo_engine import DemoEngine
    from .demo_bridge import DemoBridge
    return create_app(engine_factory=DemoEngine,bridge_factory=DemoBridge,demo=True)
