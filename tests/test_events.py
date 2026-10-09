import json

import pytest

from backend.events import EventLog


def test_no_token_in_log_and_unique_ids(tmp_path):
    log = EventLog(tmp_path / 'events.jsonl')
    log.append(dict(msg_id='msg.1', payload=dict(token='secret', nested=dict(join_code='code'), status='applied')))
    assert not log.append(dict(msg_id='msg.1', payload={}))
    record = json.loads(log.path.read_text())
    assert record['payload'] == dict(nested={}, status='applied')
    assert 'secret' not in log.path.read_text()


def test_restart_preserves_duplicate_protection(tmp_path):
    path = tmp_path / 'events.jsonl'
    EventLog(path).append(dict(msg_id='msg.1'))
    assert not EventLog(path).append(dict(msg_id='msg.1'))
