import json
from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from backend.app import create_app
from backend.session import SessionStore

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'contracts/contracts.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def message(claim, kind, payload, seq=0, time=None):
    return dict(v=1, type=kind, msg_id=f'msg.phone.{seq}', run_id=claim['run_id'],
                sender_id=claim['session_id'], seq=seq, sim_time_s=time, payload=payload)


def test_claim_expiry_single_use_and_role_binding():
    now = [0.0]
    store = SessionStore(clock=lambda: now[0])
    code = store.issue('veh.role.rider')
    claim = store.claim(code)
    assert claim['vehicle_id'] == 'veh.role.rider'
    with pytest.raises(ValueError):
        store.claim(code)
    with pytest.raises(ValueError):
        store.issue('veh.role.rider')
    with pytest.raises(ValueError):
        store.issue('operator')
    code = store.issue('veh.role.auto')
    now[0] = 120
    with pytest.raises(ValueError):
        store.claim(code)


def test_two_bound_connections_and_reconnect():
    app = create_app()
    with TestClient(app) as client:
        VALIDATOR.validate(client.get('/api/bootstrap').json())
        claims = [client.post('/api/claim', json={'join_code': app.state.sessions.issue(v)}).json()
                  for v in ['veh.role.rider', 'veh.role.auto']]
        with ExitStack() as stack:
            for claim in claims:
                ws = stack.enter_context(client.websocket_connect('/ws'))
                ws.send_json(message(claim, 'session.hello', {'token': claim['token'], 'last_server_seq': 0}))
                assert ws.receive_json()['payload']['vehicle_id'] == claim['vehicle_id']
                ws.receive_json()
                assert ws.receive_json()['payload']['vehicle_id'] == claim['vehicle_id']
            assert all(s.connected for s in app.state.sessions.sessions.values())
        for claim in claims:
            VALIDATOR.validate(claim)
            for _ in range(2):
                with client.websocket_connect('/ws') as ws:
                    ws.send_json(message(claim, 'session.hello', {'token': claim['token'], 'last_server_seq': 0}))
                    ready, snapshot, frame = [ws.receive_json() for _ in range(3)]
                    for event in [ready, snapshot, frame]:
                        VALIDATOR.validate(event)
                    assert ready['payload']['vehicle_id'] == claim['vehicle_id']
                    assert frame['payload']['vehicle_id'] == claim['vehicle_id']
                    assert snapshot['payload']['observations'] == []
                    assert all(d['vehicle_id'] == claim['vehicle_id'] for d in snapshot['payload']['drivers'])


def test_reject_unauthenticated_socket_and_unknown_claim_fields():
    with TestClient(create_app()) as client:
        assert client.post('/api/claim', json={'join_code': 'bad', 'vehicle_id': 'veh.role.rider'}).status_code == 422
        with client.websocket_connect('/ws') as ws:
            ws.send_json({'type': 'probe.sample'})
            assert ws.receive()['type'] == 'websocket.close'


def test_host_origin_and_local_setup_protection():
    with TestClient(create_app()) as client:
        assert client.get('/healthz', headers={'host': 'attacker.example'}).status_code == 400
        with pytest.raises(Exception):
            with client.websocket_connect('/ws', headers={'origin': 'http://attacker.example'}):
                pass
    with TestClient(create_app(), client=('192.168.1.2', 1234)) as remote:
        assert remote.get('/setup').status_code == 403
        assert remote.post('/api/fixture/join/rider').status_code == 403


def test_qr_and_fixture_pages():
    with TestClient(create_app()) as client:
        for page in ['/setup', '/driver']:
            assert client.get(page).status_code == 200
        response = client.get('/api/fixture/qr', params={'url': 'http://localhost:8000/driver#join=test'})
        assert response.status_code == 200
        assert '<svg' in response.text
        assert client.get('/api/fixture/qr', params={'url': 'https://attacker.example/driver#join=test'}).status_code == 422


def test_sharing_off_then_valid_probe_and_duplicate():
    app = create_app()
    with TestClient(app) as client:
        claim = client.post('/api/claim', json={'join_code': app.state.sessions.issue('veh.role.rider')}).json()
        with client.websocket_connect('/ws') as ws:
            ws.send_json(message(claim, 'session.hello', {'token': claim['token'], 'last_server_seq': 0}))
            ws.receive_json()
            ws.receive_json()
            frame = ws.receive_json()
            payload = {k: frame['payload'][k] for k in ['frame_id', 'vehicle_id', 'pose']}
            ws.send_json(message(claim, 'probe.sample', payload, 1, frame['sim_time_s']))
            assert ws.receive_json()['payload']['status'] == 'rejected'
            ws.send_json(message(claim, 'probe.toggle', {'enabled': True}, 2))
            assert ws.receive_json()['payload']['status'] == 'applied'
            sample = message(claim, 'probe.sample', payload, 3, frame['sim_time_s'])
            ws.send_json(sample)
            assert ws.receive_json()['payload']['status'] == 'applied'
            ws.send_json(sample)
            assert ws.receive_json()['payload']['status'] == 'duplicate'
            assert len(app.state.gateway.samples) == 1

