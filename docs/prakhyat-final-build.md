# Prakhyat: Traffix simulation and admin build handoff

9 October 2026 · Human authorization: Kush requested this module split and accepted
the Hawk-based revision-2 UI. This is the specific implementation handoff. Product
reference: `docs/traffix-harness-prd-v1.md`. Design reference:
`docs/ui-direction-proposal.md` and its two images in `docs/design-reference/`.

**Your deliverable:** a runnable, tested simulation host and admin application on
Prakhyat's machine, accessible from other team laptops and Kush's mobile application.
Kush builds the native mobile client separately in the coordinator chat. Do not wait
for its UI: provide the documented API and an integration test client first.

## 1. How your agent obtains the work

Repository: https://github.com/makekush7-netizen/Traffix-
Coordinator source branch: `feat/kush-demo-polish`.
Your implementation branch: `feat/prakhyat-unified-simulation`.

In an existing checkout, inspect `git status`, current branch and remotes first.
Commit or preserve your own work before switching. Fetch origin; inspect this source
branch and this document. Create your implementation branch from the coordinator
source, or merge the source into your existing implementation branch after reviewing
conflicts. Do not reset, force-push, overwrite another branch, or blindly pull main.

For a new clean checkout:

```powershell
git clone --branch feat/kush-demo-polish https://github.com/makekush7-netizen/Traffix-.git Traffix
cd Traffix
git switch -c feat/prakhyat-unified-simulation
```

Read `AGENTS.md`, `OWNERS.md`, this file, the PRD and accepted UI direction. Read
`contracts/messages.example.json` and `contracts/contracts.schema.json`, plus the
scenario files. Do not load the whole 143 KB Astra plan: use only a needed module's
section and Appendix B as required. Inspect the existing code before replacing it.

The phrase “wilastra” in Kush's request has no verified tool definition in this
repository. Use the Astra build plan as reference where relevant; do not invent or
install a tool by that name. This handoff and the final PRD take priority over old
synthetic-corridor descriptions where Kush explicitly expanded scope.

## 2. Extract and preserve the useful repository assets

| Path | Reuse / inspect |
|---|---|
| `backend/harness/engine.py` | SUMO owner thread, snapshots, worker commands, original scenarios |
| `backend/harness/app.py` | Existing FastAPI routes and lifecycle; prototype auth is not remote admin auth |
| `backend/harness/demo_engine.py` | Repeatable small cohort, route validation and manifest integration |
| `backend/harness/mobile.py`, `demo_bridge.py` | Authenticated phone binding and validated observation/acceptance loop |
| `backend/harness/response_lab.py` | Existing bounded queue-extension rule; baseline comparator, not final controller |
| `backend/harness/data/` | LIG OSM/network/world, prepared demo assets and reference results |
| `web/src/mobile/scene.js` | Current Three.js geometry, cameras and rendering logic |
| `scripts/build_lig.py`, `check_lig.py` | Geometry preparation and checks |
| `ml/`, `eval/`, `models/` | Your earlier forecast work; inspect provenance before reuse |
| `docs/prakhyat-ml-review.md`, `mentor-briefing.md` | Known forecast and calibration limitations |
| `tests/test_response_lab.py`, mobile and guidance tests | Existing guards that must continue to pass |

Do not port laptop-specific absolute paths. Prepare install/setup scripts, pin supported
dependency versions and record the actual Python/SUMO/CUDA environment. No private keys
or local data enter Git. Large models/run data get checksummed download/setup instructions
or an authorized artifact location, not an accidental massive repository commit.

## 3. Module ownership and integration boundary

Kush explicitly assigns you the final simulation engine, detection/forecast adapters,
scenario/event editor, admin dashboard, host packaging, evaluation and corresponding
tests/docs. Prefer new code under `backend/simulation/`, `web/src/operator/`,
`web/src/shared/`, `scripts/` and your existing `ml/`, `eval/`, `models/`.

You may extract reusable scene code into shared modules while preserving the old
mobile demos. Keep `web/src/mobile/` and native mobile-client implementation with Kush.
Do not rewrite frozen `contracts/` in place. Add versioned schemas/API under
`contracts/v2/` with examples and compatibility adapters when needed. Document migration.
Coordinate new location-pack generation with Nandani; preserve reviewed original sim
files and mappings. There is one authoritative simulation host; browsers are clients.

Before engine expansion, publish `docs/integration-api-v2.md`, machine-readable OpenAPI,
JSON Schema examples, and a no-UI client script so Kush can start the mobile work.
Once published, version any breaking change. Never solve a client mismatch by making
authentication or frame validation optional.

## 4. Required product behavior

### Simulation and traffic

- Prepared location search: LIG first, then two reviewed Indore packs. Unsupported
  locations show preparation/unavailable status. Do not label fetched OSM data validated.
- Deterministic multi-approach demand: class mix, OD/turns, time profiles, bus stops,
  lane permissions, insertion backlog, warm-up and drain. Quiet/normal/busy must mean
  documented demand, not camera-dependent spawning. Traffic must visibly arrive from
  multiple appropriate approaches, not repeat one route for the entire cohort.
- Stable driver variation and correct left-hand movement. Begin with collision-free
  lane-following behavior; add sublane filtering only behind a fidelity setting and tests.
- Explore mode supports continuing demand; experiment mode uses finite frozen demand
  and produces complete matched results. Never hide faults, teleport cars or merge loops.
- No prominent prototype 1x/2x/4x toolbar. Advanced pace settings report target and
  actual simulated seconds/wall second, CPU pressure and overload. Separate scene FPS,
  vehicle speed and simulation throughput. Preserve valid engine time and observations.

### Admin and scene

- Full-screen readable road scene, differentiated low-poly buildings, orbit/pan/zoom,
  minimap bottom right, follow and car/bike/auto first-person camera on the same vehicle.
- Use the accepted charcoal rail, white header, grey workspace and slate buttons.
  Five consistent tools: Location(s), Traffic, Events, Control, Results. One drawer at
  a time, no dead white gutter. Same logo, shared tokens/icons, explicit labels.
- Scene/host state stays truthful. Scenario preparation opens the active simulation;
  Pause for inspection and Resume remain available in context. Reload reconnects and
  does not reset a shared run. Completion has Results and New scenario rather than a dead end.
- Signals map to controlled lanes and movements. Physical heads plus arrows/labels
  identify who has protected/permissive green. Congestion colour never changes signal colour.
  Adaptive countdowns show only committed timings or explicitly uncertain estimates.
- Rally, blockage/roadworks, rain, ambulance and sensor-outage events: draft → preview
  → validate → apply → audit. Seed random schedules. Compose overlapping restrictions.
  An event change in an experiment forks/marks the scenario; never falsify comparability.

### Controllers and evaluation

- Preserve fixed timing, current bounded rule and actuated baseline as selectable policies.
- Implement a capacity-aware pressure-inspired policy with minimum/maximum green,
  safe transitions, maximum-red/fairness and downstream receiving-space constraints.
  Use the PRD's explicit heuristic definition; do not claim published optimality.
- Add neighbor-arrival coordination only after independent junction policies work.
  Separate emergency preemption/recovery from ordinary queue control.
- Forecasts: causal features, whole-run held-out splits, persistence/trend baselines,
  jam-onset lead time/false alerts. Gate live forecast-assisted control on saved evidence.
- Compare paired seeds and identical demand/events/configuration; report delay/throughput,
  queues/spillback, unfinished/insertion delay, faults and class/approach fairness.

## 5. Local camera detection and app observations

Build source adapters that produce a common observation envelope while preserving
`source_type`, source ID, age, confidence/quality, coverage, units and run identity.
Sources are `simulated_sensor`, `phone_sample`, `camera_measurement`,
`operator_report` and `emulated_probe`. The renderer may use simulator truth; the
detector/controller only sees enabled observation adapters. Zero phone uplinks still
means zero phone observations even when camera data exists.

App settings supplied by Kush: sharing consent, trip identity, foreground/background
permission state, notification preference and report category. Configuration settings
are not traffic measurements. Manual reports remain unverified until corroborated.

YOLO pipeline, optional but required as an independently testable adapter:

1. Accept permitted prerecorded footage first. Camera input is optional, never required
   to boot the simulation. Pin model/runtime and record weights checksum/license.
2. Local detection plus tracking, initially compare ByteTrack/BoT-SORT as supported by
   the chosen runtime. Count unique tracks crossing a configured line; do not count
   every detection each frame as a new vehicle.
3. Calibrate camera ground-plane geometry before reporting km/h or queue metres.
   Without calibration report counts/quality and speed unavailable.
4. Generic pretrained classes may identify cars/bikes/buses but do not automatically
   distinguish auto-rickshaw, e-rickshaw, ambulance or an incident cause. Map unsupported
   classes to unknown; create a reviewed local dataset/evaluation before fine-tuning.
5. Persistent stationary tracks can raise a suspected-blockage candidate, with temporal,
   ROI, signal-context and confidence checks. A rally needs convoy/crowd/context evidence
   and operator confirmation; do not infer political intent from a detector. Ambulance
   priority requires a verified emergency source, not just a bounding box.
6. Object classification, incident classification and short-term forecasting have
   separate labels and tests. No plate/person identification or linking visual tracks
   to phone owners. Camera and phone identities remain separate unless explicitly bound.
7. GPU inference runs separately from the SUMO owner. Bound queues, drop stale image
   frames with counters, reduce camera frequency under load, and preserve traffic/control
   responsiveness. Record no-input/degraded status instead of treating it as free roads.

Provide vehicle-class precision/recall, count error, track stability and measured latency
on permitted held-out clips. Rendered simulation video is labelled synthetic and is
not evidence of real-camera accuracy. Missing footage/weights must leave a working
adapter interface and deterministic fixtures, with the limitation explicitly reported.

Primary references: [Ultralytics tracking](https://docs.ultralytics.com/modes/track),
[model/library licence](https://www.ultralytics.com/license). Check the actual chosen
distribution/weights terms and record them; do not assume every YOLO model is unrestricted.

## 6. Team admins on separate laptops

One host, initially one shared active interactive run, several authenticated clients.
Admin laptop renders locally; it does not run a second authoritative SUMO copy.
Separate per-client camera, selection, drawer and filters from shared scenario state.

Implement operator/viewer/driver roles. Shared edits require command ID, run ID,
expected scenario/control revision and identity. Serialize commands on the worker;
reject a stale revision with conflict and current state. Idempotency prevents a retried
command creating two ambulances or extending a phase twice.

Use a visible control lease for high-impact shared run/reset/controller settings:
holder, expiry, request control and privileged audited takeover. A disconnected holder
cannot block everyone forever. Lease protects mutations, not viewing. Scoped event edits
still validate conflicts. Provide an audit trail naming the actor and execution result.

Host outage, sleeping laptop or tunnel loss: clients show disconnected/stale and disable
actions. Reconnect requests a fresh snapshot and only authorized subscriptions; do not
replay old mutating commands silently. Independent runs later use isolated processes,
namespaces, directories and resource budgets. No multi-run claim without tests.

LAN is the final-demo fallback. Online access uses explicit remote authentication,
HTTPS/WSS and a documented tunnel or relay. Do not expose localhost operator bootstrap,
TraCI, shell execution or arbitrary file reading publicly. Native push notifications
are wake-up hints, not authoritative control messages.

## 7. Minimum v2 interface to publish first

Endpoint names below are the agreed starting surface; document exact schemas before
implementing clients. Use `/api/v2/` alongside compatible existing APIs.

| Surface | Operations |
|---|---|
| Auth | operator/viewer login, session renewal/revocation, role-limited identity |
| Locations | catalog/search, preparation status, pack version/geometry metadata |
| Scenarios | create/get/update with revision, seeded demand and event schedules |
| Runs | create/get, state/control, result/export, replay and comparable-run query |
| Team control | acquire/renew/release lease, conflict and takeover audit |
| Phone binding | issue one-use invite, claim, reconnect, own trip/state |
| Driver actions | consent update, incident report, accept/decline advisory, end trip |
| Observations | validated source ingestion, source health and permitted aggregates |
| Realtime | authorized run snapshots/deltas, own-vehicle frames, guidance and acknowledgements |

All mutation envelopes: API/schema version, command ID, run ID where applicable,
expected revision, payload. All replies: status, command ID, resulting revision,
reason code and acknowledged execution time. Units: m, m/s, simulated seconds, wall
timestamps explicitly named; emissions rate mg/s, integrated mass kg. Use monotonic
sequence and server-issued frame/advisory IDs. Opaque scoped tokens never appear in logs.

Phone advisory fields: ID, target binding/vehicle/trip/run, kind, source, evidence,
created/expiry simulation time, wall freshness, decision point, route version,
confidence/availability, acceptance requirements and status. Server validates eligibility
at acceptance. Advisory expiry/cancellation is pushed; acceptance ACK only after worker
application. No numeric speed or CO2 saving without its measurement/reference metadata.

Add a lightweight mock server/client fixture for Kush to develop independently. Its
responses must have the same schema as the real host. Provide examples for unavailable
forecast, declined/expired advice, reset, reconnect and missing baseline.

## 8. Required edge-case matrix

Implement tests and record the result for each group, not just a happy-path video.

| Group | Cases |
|---|---|
| Map | missing/ambiguous place, invalid topology, incomplete pack, cancelled preparation, wrong coordinate transform, asset load failure |
| Traffic | disconnected OD, class-forbidden route, zero demand, overcapacity backlog, invalid proportions, vehicle exits, stop blockage, deterministic regeneration |
| Signals | conflict movement, red/yellow/all-red transition, blocked receiving road, missing queue, min/max green, starvation, mode switch, emergency recovery |
| Events | draft cancel, duplicate retry, stale revision, overlap, early ending, failed partial apply, inaccessible ambulance route, multiple emergencies |
| Phones | invalid/expired/used code, wrong vehicle/run, altered/stale/duplicate/future sample, sharing off, delayed ACK, two decisions, passed turn, unavailable bypass |
| Team | concurrent reset/edit, expired lease, host/client disconnect, privilege violation, takeover, independent camera views, authorized reconnect |
| Vision | no clip, unsupported class, duplicate tracks, occlusion, no calibration, stale frames, confidence drop, GPU unavailable/out-of-memory |
| Performance | overloaded worker, slow viewer, bounded queues, simulation/frame-rate mismatch, memory leak, actual rate below target |
| Results | incomplete/faulted runs, mismatched seeds/demand, missing baseline, negative savings, electric class mapping, replay cannot execute actions |

## 9. Work sequence — complete milestones in order

1. Inventory/boot on your machine and baseline test report. Record CPU/GPU/runtime.
2. Versioned integration API/examples + mock client. Commit/push this early for Kush.
3. Unified LIG pack, multi-approach demand, signal mapping and headless run outputs.
4. Accepted UI shell, readable scene, minimap, shared state and team-control behavior.
5. Event engine and pressure-inspired controller, paired evaluation and action evidence.
6. Own-vehicle follow/FPV and real two-phone binding through the same server.
7. Vision adapter, degradation behavior and independent measured evaluation.
8. Additional reviewed locations, LAN/online access, soak/performance tests and return bundle.

Do not stop at placeholder screens. A button without a working endpoint is unfinished.
For externally unavailable input, implement the remaining path with labelled fixtures
and provide a precise blocked-input note; do not manufacture accuracy or field data.
The first complete demo must boot without optional YOLO/LLM components.

## 10. Return the build to Kush

Push your branch and open a draft PR into `feat/kush-demo-polish` (not main) when the
integration surface and runnable milestone are ready. Do not auto-merge. Include:

- Commit/branch, launch commands, dependency lock/setup and model/data checksums.
- `docs/prakhyat-build-return.md`: built vs remaining, exact API version, test commands
  and output, measured hardware envelope, known faults, LAN/remote URL configuration.
- Generated OpenAPI/schema examples and a script that tests the actual phone loop.
- Saved paired run manifests/results and a replay showing why a control action occurred.
- Two-laptop + two-phone smoke-test evidence; distinguish real devices from emulation.
- Source-tagged vision results and unavailable classes/inputs; no fabricated metrics.
- Screenshot/video of the actual running software and a short demo script.

Use GitHub as the source handoff; optionally attach a clean release ZIP without venv,
node_modules, secrets or unlimited run data. Kush pulls and integrates the mobile app.
There is no automatic cross-chat callback: report the PR/commit to the human. An agent
must not message another chat unless the human explicitly authorizes that action.

## Paste this into Prakhyat's new chat

> You are implementing Traffix's unified simulation host and admin dashboard on my
> laptop (RTX 5060 8 GB VRAM, 32 GB RAM; inspect CPU/OS). Repository:
> https://github.com/makekush7-netizen/Traffix-. Fetch `feat/kush-demo-polish` safely,
> preserve my existing work, and read `docs/prakhyat-final-build.md`, `AGENTS.md`,
> `OWNERS.md`, the final harness PRD and accepted UI direction referenced there.
> Work on `feat/prakhyat-unified-simulation`. Kush builds the native mobile app
> separately. Publish the versioned integration API, examples and mock fixture early,
> then implement the milestones through a runnable tested build. Reuse the engine,
> phone gateway and ML/evaluation assets; preserve compatibility and one TraCI owner.
> Follow the accepted charcoal/white/grey/slate design and its functional edge cases.
> Support multiple team laptops as clients of one authoritative host. Add local YOLO
> detection/tracking as an independent optional adapter with measured limitations.
> Do not invent real traffic data, prediction benefit, carbon savings or completed
> features. Commit/push small milestones, open a draft PR into `feat/kush-demo-polish`,
> and deliver `docs/prakhyat-build-return.md` with setup, API, actual test/performance
> evidence, paired runs and the end-to-end demonstration. Start with inventory and
> the integration interface, then continue until the required build is delivered.
