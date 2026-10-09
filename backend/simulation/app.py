"""HTTP gateway: all shared mutations are serialized by one SUMO owner."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from .auth import Auth
from .protocol import Command, Login, Lease
from .coordination import Conflict
from backend.harness.engine import WORLD, ROOT
from backend.harness.mobile import MobileBridge
from backend.app import ClaimRequest

LOCATIONS=[{'id':'lig','name':'LIG Square, Indore','status':'prepared','version':'osm-existing-v1',
            'calibrated':False,'review':'Existing repository geometry; field calibration unavailable'},
           {'id':'vijay-nagar','name':'Vijay Nagar, Indore','status':'awaiting_topology_review'},
           {'id':'palasia','name':'Palasia, Indore','status':'awaiting_topology_review'}]

def create_app(engine=None, accounts=None):
    if engine is None:
        from .engine import UnifiedEngine
        engine=UnifiedEngine()
    auth=Auth(accounts if accounts is not None else json.loads(os.getenv('TRAFFIX_ACCOUNTS','{}')))
    @asynccontextmanager
    async def lifespan(app):
        if not auth.accounts: raise RuntimeError('Set TRAFFIX_ACCOUNTS with explicit operator/viewer accounts before boot')
        await asyncio.to_thread(engine.start)
        app.state.mobile=MobileBridge(engine)
        try: yield
        finally: await asyncio.to_thread(engine.stop)
    app=FastAPI(title='Traffix unified API',version='2.0',lifespan=lifespan)
    app.state.engine=engine; app.state.auth=auth
    def identity(request):
        origin=request.headers.get('origin')
        if origin:
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc!=request.headers.get('host'): raise HTTPException(403,'origin_forbidden')
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        try: return auth.identity(token)
        except ValueError as exc: raise HTTPException(401,str(exc)) from exc
    async def submit(command):
        try: return await asyncio.wrap_future(engine.command(command))
        except Conflict as exc: raise HTTPException(409,{'reason_code':str(exc),'state':engine.state()}) from exc
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
        except RuntimeError as exc: raise HTTPException(503,str(exc)) from exc
    @app.post('/api/v2/auth/login')
    async def login(body:Login,request:Request):
        try: return auth.login(body.username,body.password,request.client.host)
        except ValueError as exc: raise HTTPException(401,str(exc)) from exc
    @app.get('/api/v2/auth/identity')
    async def who(request:Request): return identity(request)
    @app.post('/api/v2/auth/revoke')
    async def revoke(request:Request):
        identity(request); auth.revoke(request.headers.get('authorization','').removeprefix('Bearer ')); return {'status':'revoked'}
    @app.post('/api/v2/auth/renew')
    async def renew(request:Request):
        actor=identity(request)
        # Renewal rotates the opaque token; stolen old tokens are invalidated.
        import secrets,hashlib,time
        auth.revoke(request.headers.get('authorization','').removeprefix('Bearer '))
        token=secrets.token_urlsafe(32); actor['expires_wall_s']=time.time()+3600
        auth.sessions[hashlib.sha256(token.encode()).hexdigest()]=actor
        return {'token':token,**actor}
    @app.get('/api/v2/locations')
    async def locations(request:Request,q:str=''):
        identity(request); return [p for p in LOCATIONS if q.lower() in p['name'].lower()]
    @app.get('/api/v2/world')
    async def world(request:Request): identity(request); return WORLD
    @app.get('/api/v2/state')
    async def state(request:Request): identity(request); return engine.state()
    @app.post('/api/v2/commands')
    async def commands(body:Command,request:Request):
        return await submit({'action':'v2','actor':identity(request),'command':body.model_dump()})
    @app.post('/api/v2/lease')
    async def lease(body:Lease,request:Request):
        return await submit({'action':'lease','actor':identity(request),**body.model_dump(exclude={'action'}),'lease_action':body.action})
    @app.get('/api/v2/results')
    async def results(request:Request): identity(request); return engine.export()
    @app.get('/api/v2/observations')
    async def observations(request:Request): identity(request); return app.state.mobile.status()
    @app.post('/api/v2/phones/invites')
    async def invite(request:Request):
        actor=identity(request)
        if actor['role']!='operator': raise HTTPException(403,'operator_required')
        bridge=app.state.mobile; state=bridge.sync()
        bound={s.vehicle_id for s in bridge.sessions.sessions.values()}
        pending={v[0] for v in bridge.sessions.codes.values() if v[1]>bridge.sessions.clock()}
        available=[v['id'] for v in state['vehicles'] if v['id'] not in bound|pending]
        if not available: raise HTTPException(409,'no_available_vehicle')
        vehicle=available[0]
        return {'join_code':bridge.sessions.issue(vehicle),'vehicle_id':vehicle,'run_id':state['run_id'],'expires_wall_s':120}
    @app.post('/api/v2/phones/claim')
    async def claim(body:ClaimRequest,request:Request):
        bridge=app.state.mobile; bridge.same_origin(request); bridge.sync()
        try: return bridge.sessions.claim(body.join_code)
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
    @app.websocket('/api/v2/phones/ws')
    async def phones(ws:WebSocket): await app.state.mobile.serve(ws)
    @app.websocket('/api/v2/stream')
    async def stream(ws:WebSocket):
        await ws.accept()
        try:
            hello=await asyncio.wait_for(ws.receive_json(),5)
            actor=auth.identity(hello.get('token',''))
            token=hello.get('token',''); sequence=0
            while True:
                auth.identity(token); sequence+=1
                await asyncio.wait_for(ws.send_json({'api_version':'2.0','sequence':sequence,**engine.state()}),2)
                await asyncio.sleep(.2)
        except (ValueError,asyncio.TimeoutError,WebSocketDisconnect):
            try: await ws.close(code=1008)
            except RuntimeError: pass
    @app.get('/')
    async def home(): return RedirectResponse('/operator/index.html')
    web=ROOT/'web'/'src'
    for mount,path in [('operator',web/'operator'),('shared',web/'shared'),('mobile',web/'mobile'),('static',ROOT/'backend'/'harness'/'static')]:
        if path.exists(): app.mount('/'+mount,StaticFiles(directory=path),name=mount)
    return app

app=create_app()
