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

## Additive read-only and adapter surface (v2.0)

Authenticated GET `/api/v2/runs` lists saved manifests, with `active_run_id`. GET
`/api/v2/runs/{run_id}/results` loads its saved manifest; `/replay` returns a
`read_only:true` saved recording and cannot execute commands. `/comparable` only
lists unchanged scenarios with identical seed, network hash, cohort hash, settings
and scenario label. It does not itself establish integrity or a gain. Run IDs are
strict `lig.` plus 12 lowercase hexadecimal characters. Missing records return404;
invalid IDs return422. Old demo IDs are intentionally outside this new catalog.

POST `/api/v2/observations/ingest` requires an operator token and the object
`{api_version:"2.0",observation:{source_type,source_id,run_id,sim_time_s,wall_time_s,
confidence,coverage,units,values}}`. Camera/simulated/emulated/manual adapters are
stored independently; `phone_sample` is rejected and must use the validated phone
frame gateway. For example `values:{count:2,speed_mps:null}` and
`units:{count:"vehicles",speed_mps:"m/s"}` retain unavailable calibration.
Manual reports stay unverified. Duplicate, wrong-run, future or stale values reject.
GET `/api/v2/observations/health` returns fresh adapter measurements plus separate
phone-gateway health. These externally submitted measurements are currently
`usable_for_control:false`; installed simulated lane measurements drive the worker
controller. Reset creates a fresh adapter store.

## Unified phone guidance and execution identity

Enable the observed phone rule explicitly with a leased, revisioned command
`{action:"guidance",enabled:true}`. Default/reset is off. Two fresh authenticated
phone probes, slowdown≥0.45 for30 simulated seconds are untested starting thresholds.
The engine only offers the existing reviewed bypass when the current approach,
class permissions and matching destination support it. Other approaches produce
no route offer. Guidance uses frozenv1 `guidance` and `driver.decision` messages;
Accept ACK follows worker confirmation. Decline keeps the route. Worker validates
run/expiry/current route and class, decision distance, receiving space and current
phone consent/evidence immediately before applying. Phone views may GET
`/api/v2/phones/state?session_id=...&run_id=...` with the scoped driver bearer token;
this returns only that binding's simulated vehicle and advisory state, including
expiry/cancellation. Admin tokens cannot impersonate driver sessions.

Run comparability now additionally requires saved `execution_sha256` and complete
integrity. The fingerprint includes engine, policy, demand and phone adapter source;
older runs lacking it are unverified and excluded. Pace accepts finite target rates
0.25..20 simulated seconds per wall second; it does not guarantee achieved throughput.

## Registration and owner approval

POST `/api/v2/auth/register` accepts `{username,password,request_operator:true}`.
Registration creates a viewer only; client-supplied role fields reject. Usernames
normalize to lowercase ASCII, 3..32 characters, begin with a letter and permit
letters/digits/underscore/dot/hyphen. Passwords require at least8 characters (up to256).
At most5 registration attempts per remote address per60 wall seconds and256 total
accounts are allowed. Duplicate normalized names return409; weak/invalid fields422;
rate limits429. Browser cross-origin registration rejects.

Configured bootstrap accounts in `TRAFFIX_ACCOUNTS` remain protected. An existing
operator with `can_takeover:true` may GET `/api/v2/auth/users` (public account metadata
and bounded approval audit only) and POST `/api/v2/auth/users/{username}/approve` with
`{}`. Approval grants operator, never owner, revokes target sessions, and requires
login again. Ordinary operators/viewers cannot approve. No first-registration owner.

Production registration records persist as salted scrypt hashes in ignored
`.cache/private/accounts.json`; no plaintext passwords or bootstrap credentials are
written there. Registration/approval file writes are atomic and failed writes roll
back. Protect this local directory with your OS user permissions; it is not a public
asset or an export. Sessions remain ephemeral across restart. Explicit test account
maps use in-memory storage unless an isolated `account_store` path is provided.


## Dashboard flow repair endpoints

POST `/api/v2/auth/request-operator` with `{}` lets a registered viewer request operator access. It persists the pending request; the owner still approves it. Login/identity include `operator_requested`. Protected host-configured viewers cannot change their bootstrap configuration.

GET `/api/v2/runs/{response_run_id}/compare/{baseline_run_id}` is authenticated and read-only for viewers/operators. The baseline must be a distinct fixed-policy run. Both cohorts must be complete, fault-free and share network, demand, execution fingerprint, seed, settings and scenario. Edited event scenarios reject comparison. Missing lifecycle metrics reject old evidence. The response contains `available`, `reason_code`, `baseline`, `response`, nullable `differences` and explicit assumptions. Negative reductions remain negative.

Measured summary fields: `mean_journey_s` (scheduled departure to arrival, including insertion delay), `mean_travel_s`, `mean_insertion_delay_s`, `co2_kg`, and `sampled_peak_queued`. Lifecycle events are observed at 0.25-second simulation steps; queue peaks are sampled from recordings. CO2 is SUMO model output with an unreviewed fleet mapping. These are not field measurements.

Live state includes `run.progress` with scheduled/arrived counts, completion fraction, insertion backlog, future departures, running/draining/ended phase and integrity. A paused or running cohort is unfinished, not a final failed result. `run.action_log` exposes the latest 60 simulation actions. Saved catalogs add `saved_wall_s` for human-readable ordering.


### Results summary addition · 10 October 2026

`GET /api/v2/results?summary=true` returns the current snapshot manifest, the
last 60 host actions, an empty `frames` array, `summary_only: true` and
`event_window: "last 60 host actions"`. Authentication is unchanged. This avoids
copying a long live replay merely to inspect cohort status. The existing default
full export stays compatible. The operator Results overview uses its already
received authenticated state snapshot; saved comparisons still use the saved-run
endpoints. Exporting the live overview exports a labelled summary, not full replay.
Restart the host to load the new optional server query; refreshing the operator
page is sufficient for its snapshot-based Results overview.
