# Integration API v2.0

Host: `python -m scripts.run_unified`, default port 8005, one worker. Configure
`TRAFFIX_ACCOUNTS` as a JSON object of username → password/role/can_takeover.
No default accounts and no public bootstrap. Roles are operator and viewer; drivers
receive separate scoped tokens only by one-use invitation. HTTPS/WSS is required
outside a trusted demo LAN. Tokens must never be put in URLs or logs.

Machine schema: `contracts/v2/openapi.json`; command JSON Schema and examples beside it.
Frozen v1 messages remain the own-vehicle phone stream protocol; this is explicit
compatibility, not permission to send arbitrary sensor positions.

## Early supported surface

- POST `/api/v2/auth/login` `{username,password}` → opaque token, role, expiry.
- GET identity, POST auth/renew (rotates token), POST auth/revoke.
- GET locations?q=, world, state, results, observations; bearer authentication required.
- POST lease `{action: acquire|renew|release,takeover:false}`; 30 wall seconds.
  Privileged takeover requires account `can_takeover:true`; it is audited.
- POST commands: API version, unique command ID, current run ID, expected revision,
  payload. Worker rejects wrong run, stale revision or expired/foreign lease.
  Identical retry returns prior receipt. Reusing an ID for different content rejects.
- Commands: pause, resume, step, reset, rate, controller, event_preview/event_apply/event_end.
  Reset: `{action:'reset',seed:42,preset:'normal',settings:{location:'lig',mode:'experiment',
  demand_per_hour:1400,duration_s:180,drain_s:180}}`. Settings are assumed simulation inputs.
  Controller policies: fixed, bounded, actuated, pressure. Pace value: 1,2,4,8.
- POST phones/invites allocates a server-selected unbound vehicle; no client vehicle ID.
  POST phones/claim `{join_code}` gives driver credentials. WebSocket phones/ws uses
  frozen `session.hello` first and existing consent/frame/probe/ACK messages.
  WebSocket `/api/v2/stream`: first JSON `{token}` then authorized latest snapshots.
  Sequence resets per connection; reconnect fetches fresh state and never replays edits.

Every applied mutation receipt has version/status/command_id/revision/reason_code and
acknowledged wall/simulation time. HTTP409 includes current state. Rejected validation
uses HTTP422. Queue saturation/host fault uses HTTP503. Login limits are per remote
address. Gateway disconnect must disable controls; views/cameras are local only.

## Mock and integration

`python -m scripts.mock_v2` serves the exact application routes on 8010 using a clearly
labelled deterministic fixture. Only pause/resume mutate this fixture. `python -m
scripts.client_v2 --url http://127.0.0.1:8010` uses `TRAFFIX_PASSWORD` for login.
It obtains a lease, checks a revisioned pause ACK and releases/revokes credentials.

## Units and limitations

Positions m, speeds m/s, timestamps simulation seconds except named wall fields;
SUMO CO2 rate mg/s integrates to kg. Phone observations remain zero with zero phone
uplinks. Forecasts cannot control signals without held-out evidence. Exported frames
are renderer truth, not detector inputs. Missing baseline means unavailable savings.
Locations awaiting review cannot start. Real-device smoke, reviewed additional packs,
remote tunnel credentials and held-out camera clips are external acceptance inputs.
Separate scenario CRUD/run catalog/replay endpoints are not yet published as implemented;
state/reset and result export are the initial integration surface. Breaking changes
require a new version.
