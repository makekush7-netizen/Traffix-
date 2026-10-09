import secrets
import time
from dataclasses import dataclass

VEHICLES = ('veh.role.rider', 'veh.role.auto', 'veh.role.delivery')


@dataclass
class Session:
    session_id: str
    vehicle_id: str
    token: str
    reporting: bool = False
    connected: bool = False
    last_seq: int = -1
    last_seen: float = 0
    socket: object = None


class SessionStore:
    def __init__(self, clock=time.monotonic, *, vehicles=VEHICLES, run_id=None):
        self.clock = clock
        self.vehicles = tuple(vehicles)
        self.run_id = run_id or 'run.' + secrets.token_hex(8)
        self.codes = {}
        self.sessions = {}

    def issue(self, vehicle_id):
        if vehicle_id not in self.vehicles:
            raise ValueError('wrong_role')
        if any(s.vehicle_id == vehicle_id for s in self.sessions.values()):
            raise ValueError('occupied_role')
        # Reissuing a code invalidates previous unclaimed codes for this role.
        self.codes = {c: item for c, item in self.codes.items() if item[0] != vehicle_id}
        code = secrets.token_urlsafe(9)
        self.codes[code] = (vehicle_id, self.clock() + 120)
        return code

    def claim(self, code):
        item = self.codes.pop(code, None)
        if not item or self.clock() >= item[1]:
            raise ValueError('invalid_or_expired_code')
        if any(s.vehicle_id == item[0] for s in self.sessions.values()):
            raise ValueError('occupied_role')
        session = Session('session.' + secrets.token_hex(8), item[0], secrets.token_urlsafe(32))
        self.sessions[session.session_id] = session
        return dict(run_id=self.run_id, session_id=session.session_id,
                    vehicle_id=session.vehicle_id, token=session.token)

    def authenticate(self, message):
        session = self.sessions.get(message['sender_id'])
        if (message['run_id'] != self.run_id or not session or
                not secrets.compare_digest(message['payload']['token'].encode(), session.token.encode())):
            raise ValueError('unauthenticated')
        return session
