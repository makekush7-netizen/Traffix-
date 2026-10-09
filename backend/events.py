import json
import threading
from pathlib import Path


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()
                if key not in ('token', 'join_code', 'authorization')}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class EventLog:
    """Append-only JSONL audit sink; authentication secrets are never serialized."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ids = set()
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                self._ids.add(json.loads(line)['msg_id'])

    def append(self, event):
        with self._lock:
            if event['msg_id'] in self._ids:
                return False
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(redact(event), allow_nan=False) + '\n')
                stream.flush()
            self._ids.add(event['msg_id'])
            return True
