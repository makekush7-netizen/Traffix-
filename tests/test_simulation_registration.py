from backend.simulation.auth import Auth
import pytest


def test_registration_persists_hashes_and_never_grants_owner(tmp_path):
    path=tmp_path/'accounts.json'
    auth=Auth({'owner':{'password':'configured','role':'operator','can_takeover':True}},storage_path=path)
    assert auth.register('New.Driver','longpass123','local')['role']=='viewer'
    assert 'longpass123' not in path.read_text()
    fresh=Auth({'owner':{'password':'configured','role':'operator','can_takeover':True}},storage_path=path)
    token=fresh.login('NEW.DRIVER','longpass123','local')['token']
    assert fresh.identity(token)['role']=='viewer'
    owner=fresh.identity(fresh.login('owner','configured','owner')['token'])
    fresh.approve(owner,'new.driver')
    with pytest.raises(ValueError,match='session_expired'): fresh.identity(token)
    assert fresh.login('new.driver','longpass123','local')['role']=='operator'
    assert not fresh.accounts['new.driver']['can_takeover']
    third=Auth({},storage_path=path)
    assert third.accounts['new.driver']['role']=='operator'


def test_registration_duplicates_validation_and_privilege(tmp_path):
    auth=Auth({},storage_path=tmp_path/'users.json')
    for username,password in [('a','longpass123'),('../owner','longpass123'),('valid','short')]:
        with pytest.raises(ValueError): auth.register(username,password,'local')
    auth.register('driver','longpass123','local')
    with pytest.raises(ValueError,match='username_unavailable'): auth.register('DRIVER','differentlong','other')
    actor=auth.identity(auth.login('driver','longpass123','local')['token'])
    with pytest.raises(ValueError,match='owner_required'): auth.approve(actor,'driver')

def test_store_failure_rolls_back_registration_and_approval(tmp_path,monkeypatch):
    auth=Auth({'owner':{'password':'configured','role':'operator','can_takeover':True}},storage_path=tmp_path/'users.json')
    auth.register('driver','longpass123','local')
    owner=auth.identity(auth.login('owner','configured','owner')['token'])
    def fail(): raise OSError('disk denied')
    monkeypatch.setattr(auth,'save',fail)
    with pytest.raises(OSError): auth.register('other','longpass123','local')
    assert 'other' not in auth.accounts
    with pytest.raises(OSError): auth.approve(owner,'driver')
    assert auth.accounts['driver']['role']=='viewer'


def test_registration_concurrent_duplicate_and_rate_limit(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    auth=Auth({},storage_path=tmp_path/'users.json')
    def register(remote):
        try: return auth.register('driver','longpass123',remote)['status']
        except ValueError as exc: return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(register,['one','two']))==['registered','username_unavailable']
    for i in range(5): auth.register('user'+str(i),'longpass123','rate-limited')
    with pytest.raises(ValueError,match='register_rate_limited'): auth.register('user6','longpass123','rate-limited')


def test_registration_http_permissions_and_restart(tmp_path):
    from fastapi.testclient import TestClient
    from backend.simulation.app import create_app
    class Engine:
        def start(self): pass
        def stop(self): pass
        def snapshot(self): return {'ready':True,'error':None,'run_id':'run.1','sim_time_s':0,'vehicles':[],'scenario':'everyday','paused':True}
    accounts={'owner':{'password':'configured','role':'operator','can_takeover':True},'operator':{'password':'configured','role':'operator'}}
    path=tmp_path/'users.json'
    with TestClient(create_app(Engine(),accounts,account_store=path)) as client:
        assert client.post('/api/v2/auth/register',json={'username':'driver','password':'longpass123','role':'operator'}).status_code==422
        assert client.post('/api/v2/auth/register',json={'username':'driver','password':'longpass123'},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.post('/api/v2/auth/register',json={'username':'driver','password':'longpass123'}).json()['role']=='viewer'
        assert client.post('/api/v2/auth/register',json={'username':'DRIVER','password':'longpass123'}).status_code==409
        def login(username):
            password='longpass123' if username=='driver' else 'configured'
            return {'Authorization':'Bearer '+client.post('/api/v2/auth/login',json={'username':username,'password':password}).json()['token']}
        driver=login('driver'); owner=login('owner'); operator=login('operator')
        assert client.post('/api/v2/auth/request-operator',headers=driver,json={}).json()['status']=='requested'
        assert client.get('/api/v2/auth/identity',headers=driver).json()['operator_requested'] is True
        assert client.get('/api/v2/auth/users',headers=driver).status_code==403
        assert client.post('/api/v2/auth/users/driver/approve',headers=operator,json={}).status_code==403
        listing=client.get('/api/v2/auth/users',headers=owner).json()
        assert 'salt' not in str(listing) and 'hash' not in str(listing) and 'password' not in str(listing)
        assert client.post('/api/v2/auth/users/driver/approve',headers=owner,json={}).status_code==200
        assert client.get('/api/v2/auth/identity',headers=driver).status_code==401
        assert client.get('/api/v2/auth/identity',headers=login('driver')).json()['role']=='operator'
        assert client.post('/api/v2/auth/users/owner/approve',headers=owner,json={}).status_code==409
    with TestClient(create_app(Engine(),accounts,account_store=path)) as client:
        assert client.post('/api/v2/auth/login',json={'username':'driver','password':'longpass123'}).json()['role']=='operator'

def test_request_operator_persistence_and_rollback(tmp_path,monkeypatch):
    path=tmp_path/'accounts.json'; auth=Auth({},storage_path=path)
    auth.register('driver','longpass123','local',False)
    actor=auth.identity(auth.login('driver','longpass123','local')['token'])
    original=auth.save
    def fail(): raise OSError('disk denied')
    monkeypatch.setattr(auth,'save',fail)
    with pytest.raises(OSError): auth.request_operator(actor)
    assert auth.accounts['driver']['operator_requested'] is False
    monkeypatch.setattr(auth,'save',original)
    auth.request_operator(actor)
    assert Auth({},storage_path=path).accounts['driver']['operator_requested'] is True
    assert auth.login('driver','longpass123','local')['operator_requested'] is True
