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
from .protocol import Command, Login, Lease, Registration, Approval
from .coordination import Conflict
from backend.harness.engine import WORLD, ROOT
from backend.harness.mobile import MobileBridge
from backend.app import ClaimRequest

LOCATIONS=[{'id':'lig','name':'LIG Square, Indore','status':'prepared','version':'osm-existing-v1',
            'calibrated':False,'review':'Existing repository geometry; field calibration unavailable'},
           {'id':'vijay-nagar','name':'Vijay Nagar, Indore','status':'awaiting_topology_review'},
           {'id':'palasia','name':'Palasia, Indore','status':'awaiting_topology_review'}]

def create_app(engine=None, accounts=None, account_store=None):
    if engine is None:
        from .engine import UnifiedEngine
        engine=UnifiedEngine()
    auth=Auth(accounts if accounts is not None else json.loads(os.getenv('TRAFFIX_ACCOUNTS','{}')),
              storage_path=account_store if account_store is not None else (ROOT/'.cache/private/accounts.json' if accounts is None else None))
    @asynccontextmanager
    async def lifespan(app):
        await asyncio.to_thread(engine.start)
        from .phone import UnifiedMobileBridge
        app.state.mobile=UnifiedMobileBridge(engine)
        try: yield
        finally: await asyncio.to_thread(engine.stop)
    app=FastAPI(title='Traffix unified API',version='2.0',lifespan=lifespan)
    app.state.engine=engine; app.state.auth=auth
    engine._actor_validator=auth.validate_actor
    def identity(request):
        origin=request.headers.get('origin')
        if origin:
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc!=request.headers.get('host'): raise HTTPException(403,'origin_forbidden')
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        try: return auth.command_actor(token)
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
    def public_origin(request):
        from urllib.parse import urlsplit
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'): raise HTTPException(403,'origin_forbidden')
    @app.post('/api/v2/auth/register')
    async def register(body:Registration,request:Request):
        public_origin(request)
        try: return auth.register(body.username,body.password,request.client.host,body.request_operator)
        except ValueError as exc:
            reason=str(exc); code=429 if reason.endswith('rate_limited') else 409 if reason=='username_unavailable' else 422
            raise HTTPException(code,reason) from exc
        except OSError as exc: raise HTTPException(503,'account_store_unavailable') from exc
    @app.get('/api/v2/auth/users')
    async def users(request:Request):
        try: return {'accounts':auth.list_users(identity(request)),'audit':list(auth.audit)[-100:]}
        except ValueError as exc: raise HTTPException(403,str(exc)) from exc
    @app.post('/api/v2/auth/users/{username}/approve')
    async def approve(username:str,body:Approval,request:Request):
        try: return auth.approve(identity(request),username)
        except ValueError as exc: raise HTTPException(403 if str(exc)=='owner_required' else 409,str(exc)) from exc
        except OSError as exc: raise HTTPException(503,'account_store_unavailable') from exc
    @app.post('/api/v2/auth/request-operator')
    async def request_operator(body:Approval,request:Request):
        try: return auth.request_operator(identity(request))
        except ValueError as exc: raise HTTPException(409,str(exc)) from exc
        except OSError as exc: raise HTTPException(503,'account_store_unavailable') from exc
    @app.get('/api/v2/auth/identity')
    async def who(request:Request): return {k:v for k,v in identity(request).items() if not k.startswith('_')}
    @app.post('/api/v2/auth/revoke')
    async def revoke(request:Request):
        identity(request); auth.revoke(request.headers.get('authorization','').removeprefix('Bearer ')); return {'status':'revoked'}
    @app.post('/api/v2/auth/renew')
    async def renew(request:Request):
        identity(request)
        return auth.renew(request.headers.get('authorization','').removeprefix('Bearer '))
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
    @app.get('/api/v2/runs')
    async def run_catalog(request:Request):
        identity(request)
        from .engine import saved_runs
        return {'api_version':'2.0','runs':saved_runs(),'active_run_id':engine.state()['run'].get('run_id')}
    def load_saved(run_id,filename):
        from .engine import saved_run_path
        try: return json.loads((saved_run_path(run_id)/filename).read_text(encoding='utf-8'))
        except FileNotFoundError as exc: raise HTTPException(404,'run_not_found_or_not_saved') from exc
        except (ValueError,OSError) as exc: raise HTTPException(422,'invalid_run_or_record') from exc
    @app.get('/api/v2/runs/{run_id}/results')
    async def saved_results(run_id:str,request:Request):
        identity(request); return load_saved(run_id,'manifest.json')
    @app.get('/api/v2/runs/{run_id}/replay')
    async def replay(run_id:str,request:Request):
        identity(request)
        return {'api_version':'2.0','read_only':True,'source':'saved_simulation_recording',
                'recording':load_saved(run_id,'recording.json')}
    @app.get('/api/v2/runs/{run_id}/comparable')
    async def comparable(run_id:str,request:Request):
        identity(request)
        from .engine import comparable_runs
        return {'api_version':'2.0','runs':comparable_runs(load_saved(run_id,'manifest.json'))}
    @app.get('/api/v2/runs/{response_run_id}/compare/{baseline_run_id}')
    async def paired_comparison(response_run_id:str,baseline_run_id:str,request:Request):
        identity(request)
        from .results import compare_records
        return compare_records(load_saved(response_run_id,'recording.json'),load_saved(baseline_run_id,'recording.json'))
    @app.get('/api/v2/observations')
    async def observations(request:Request): identity(request); return app.state.mobile.status()
    def adapter_store():
        from .observations import ObservationStore
        state=engine.snapshot()
        store=getattr(app.state,'observation_store',None)
        if store is None or store.run_id!=state['run_id']:
            store=app.state.observation_store=ObservationStore(state['run_id'])
        return store,state
    @app.post('/api/v2/observations/ingest')
    async def ingest_adapter(request:Request):
        actor=identity(request)
        if actor['role']!='operator': raise HTTPException(403,'operator_required')
        data=await request.json()
        if not isinstance(data,dict) or data.get('api_version')!='2.0': raise HTTPException(422,'unsupported_version')
        observation=data.get('observation')
        if not isinstance(observation,dict): raise HTTPException(422,'missing_observation')
        # Phone observations must retain the existing server-issued-frame validation.
        if observation.get('source_type')=='phone_sample': raise HTTPException(422,'phone_gateway_required')
        store,state=adapter_store()
        import time
        try: result=store.ingest(observation,now_sim_s=state['sim_time_s'],now_wall_s=time.time())
        except ValueError as exc: raise HTTPException(422,str(exc)) from exc
        return {'api_version':'2.0','status':'accepted','usable_for_control':False,
                'reason_code':'adapter_stored_not_connected_to_controller','observation':result}
    @app.get('/api/v2/observations/health')
    async def adapter_health(request:Request):
        identity(request); store,state=adapter_store()
        import time
        return {'api_version':'2.0','run_id':state['run_id'],
                **store.snapshot(now_sim_s=state['sim_time_s'],now_wall_s=time.time()),
                'phone_gateway':app.state.mobile.status(),'usable_for_control':False}
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
    @app.get('/api/v2/phones/state')
    async def own_trip(request:Request,session_id:str,run_id:str):
        bridge=app.state.mobile; bridge.same_origin(request); state=bridge.sync()
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        try: session=bridge.sessions.authenticate({'sender_id':session_id,'run_id':run_id,'payload':{'token':token}})
        except ValueError as exc: raise HTTPException(401,str(exc)) from exc
        offers=[]
        for offer in bridge.offers.values():
            if offer['vehicle_id']!=session.vehicle_id: continue
            row=dict(offer)
            if row['status']=='pending' and state['sim_time_s']>=row['expires_sim_s']: row['status']='expired'
            offers.append(row)
        return {'api_version':'2.0','run_id':run_id,'vehicle_id':session.vehicle_id,'reporting':session.reporting,
                'connected':session.connected,'sim_time_s':state['sim_time_s'],
                'vehicle':next((v for v in state['vehicles'] if v['id']==session.vehicle_id),None),
                'guidance_enabled':state.get('guidance_enabled',False),'advisories':offers,
                'source':'SUMO simulated own vehicle; sensor sharing requires phone uplinks'}
    @app.websocket('/api/v2/phones/ws')
    async def phones(ws:WebSocket): await app.state.mobile.serve(ws)
    @app.websocket('/api/v2/stream')
    async def stream(ws:WebSocket):
        from urllib.parse import urlsplit
        origin=ws.headers.get('origin')
        if origin and urlsplit(origin).netloc!=ws.headers.get('host'):
            await ws.close(code=1008); return
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
