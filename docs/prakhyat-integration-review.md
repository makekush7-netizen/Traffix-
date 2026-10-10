# Traffix unified simulation: coordinator integration review

Reviewed 10 October 2026 by Kush's coordinator agent.

## Decision

The build is a useful simulation/admin foundation, **not the complete agreed product and not yet compatible with the installed native app**. Keep PR #3 in draft until the driver integration and device gate pass. Preserve the current coordinator app and old demos while integrating; do not replace them with the browser probe page.

Reviewed branch: `feat/prakhyat-unified-simulation`, commit `6778fe8`.
PR: https://github.com/makekush7-netizen/Traffix-/pull/3
Fetched and checked out separately in `../prakhyat-review`; it has not been merged into the coordinator branch or main.

## Evidence from this review

- 72 targeted Python tests passed, one Starlette TestClient deprecation warning, 98.33 seconds. Covered v2 coordination/auth, registration, adapters, results, demand, signal worker, real-SUMO phone guidance, launcher and summary.
- 18 Node tests passed: operator protocol, vehicle motion and vehicle picking.
- Additional real-SUMO/FastAPI TestClient smoke: login, control lease, worker stepping, one-use invite, claim, scoped own-state and v1 vehicle frame over the v2 phone WebSocket passed. Reclaiming the same invite returned 409.
- The compatibility smoke reproduced legacy `/api/world` and `/api/claim` returning **404**, and `/api/v2/world` with a claimed driver's bearer token returning **401**. Own-state is missing the current app's `role`, `route_id`, `route_path`, `paused`, `ended` fields.
- Review used the existing Python 3.11 / FastAPI 0.139.2 environment and SUMO 1.28.0. Prakhyat specifies Python 3.12 and different pinned dependencies. This is compatibility evidence, not a fresh-install verification of those pins.
- Initial test invocation lacked a parent `.cache` directory; creating it and rerunning resolved the setup errors. These were review setup errors, not product failures.
- Reviewed source, API docs, saved comparison and supplied UI screenshots. This review did **not** perform fresh browser interaction, a physical handset test, multi-laptop test, GPU benchmark, public HTTPS deployment or full Python suite.
- Prakhyat reports a broader suite with one legacy baseline/network-hash incompatibility in `tests/test_demo_end_to_end.py:93`. This review did not independently rerun that long test. Do not weaken the compatibility guard to make it pass; regenerate a correctly matched reference or explicitly retire that stale fixture.

Reproduction (from the reviewed checkout using an environment with SUMO):

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
python -m pytest tests/test_simulation_v2.py tests/test_simulation_adapters.py tests/test_simulation_registration.py tests/test_simulation_results.py tests/test_simulation_demand.py tests/test_simulation_signal_worker.py tests/test_unified_phone_guidance.py tests/test_unified_launcher.py tests/test_unified_summary.py -q --tb=short --basetemp=.cache/review-pytest
node --test web/src/operator/protocol.test.mjs web/src/shared/vehicle-motion.test.mjs web/src/shared/vehicle-picking.test.mjs
```

## Fit against our requirements

| Area | What exists | Remaining work |
|---|---|---|
| Local host and team dashboard | Single SUMO owner; worker commands; roles, owner approval, revisions, lease, idempotency and authenticated stream | Two real admin laptops; lease expiry/takeover/reconnect under an actual network; clean setup on Prakhyat's laptop |
| Map and scene | Existing OSM LIG geometry, local Three.js, six vehicle classes, picking, follow/first person, clickable minimap | Only LIG is ready. Other Indore locations are pending. Building forms are mostly coloured extrusions; improve road visibility and occlusion, identifiable building types and landmarks |
| Interface | Hawk-like charcoal rail, white panels, five meaningful tools, drawer, advanced pace and completion/restart flow | Supplied screenshot starts with a low horizon view dominated by buildings. Prefer a readable top-oblique road overview; test it live at laptop resolutions. Consistency and network-stale controls need device validation |
| Traffic | Seeded arrivals and mixed classes, stable per-driver speed factors, Explore vs finite experiment | Default mix is fixed; routes are sampled uniformly. Need approach/turn demand, time profiles, bus dwell and reviewed Indian sublane/noncompliance fidelity. Current SUMO lateral resolution is disabled; this remains lane-following simulation |
| Signal response | Fixed, bounded queue extension, actuated and capacity-aware pressure heuristic; worker yellow/all-red transition and target recheck | Receiving capacities/saturation are assumptions. No established neighbour-arrival coordination or emergency preemption/recovery. Validate fairness and spillback on completed congested runs |
| Events | Preview/apply/end, source labels, overlapping speed restrictions and sensor outages | Rain, rally, roadworks and blockage currently share a speed-restriction effect. They do not simulate rally crowds, physical lane closures or ambulance priority |
| Phone integration | Server-assigned vehicle, one-use code, scoped driver token, exact issued frames, consented probes and worker-confirmed route acceptance | Browser client only at present. Native HTTP paths, map/route/lifecycle and invitation parsing must be integrated |
| Detection / forecast / camera | Source-preserving observation adapter; simulated lane sensors; optional local YOLO/tracking wrapper | No demonstrated field-camera pipeline or useful live ML forecast. Camera ingestion is not enabled for control. Auto/e-rickshaw recognition needs reviewed class-specific data/weights; the line counter currently recognizes standard vehicle classes or unknown |
| Results and carbon | Complete/fault-free matched-cohort comparison, saved results and explicit modeled emissions | Saved two-vehicle fixed/bounded comparison shows **0% benefit**. Pressure smoke is incomplete. No per-driver matched savings API; do not assign total network savings to a user's profile |
| Online operation | Local/hotspot listener configuration | No verified internet deployment. Persistent simulation/WebSockets need a reachable host and authenticated HTTPS gateway; a static frontend deployment alone will not run SUMO |

## P0: freeze a usable native-driver API with Kush

Relevant host code: `backend/simulation/app.py`, `backend/simulation/phone.py`.
Relevant coordinator app: `mobile-app/src/client.ts`, `mobile-app/src/protocol.ts`.

The native adapter currently bootstraps `/api/world`, claims `/api/claim`, streams `/ws`, and polls `/api/driver/state`. The host offers `/api/v2/world`, `/api/v2/phones/claim`, `/api/v2/phones/ws`, `/api/v2/phones/state`. Its world endpoint is for admins, so changing four URL strings alone is insufficient. Never put an admin token into the driver app or remove operator authentication to solve this.

Agree and document these additive v2 capabilities before implementation:

1. **Host discovery:** a small non-secret capabilities/version endpoint that the app can call before joining. Advertise phone protocol, prepared location, transport and relevant paths. Do not return live vehicle/admin state or credentials.
2. **Driver map after claim:** a scoped authenticated map endpoint with road shapes/widths, location identity and explicit coordinate origin/projection/units. The app must claim first, then load its map. Confirm own-frame coordinates align with map coordinates and minimap orientation.
3. **Own trip:** server-confirmed current route identity and ordered route geometry, vehicle class/display role, paused/ended status and explicit lifecycle (`active`, `arrived`, `run_reset`, unavailable as appropriate). A null vehicle alone cannot explain all these states. Keep advisories scoped to the bound driver. The coordinator can map new fields into its internal `Own` model rather than demanding old demo names.
4. **Invitation:** support a native `traffix://join?code=...&server=...` link alongside the web join URL. Host web URLs use `#code=...`; the native HTTP invitation parser currently expects `#join=...`. Accept both reviewed forms in the app, including expired/consumed codes and correct host handling. No phone-selected vehicle IDs.
5. **Route acceptance:** preserve explicit consent, simulation-time expiry, passed-turn/class/destination/receiving-space checks and worker-confirmed ACK. The app must display “applied” only after `route_applied`, and must render the actual applied route rather than hardcoded `route.demo.A/B` labels.
6. **Speed advice:** current speed comes from own frames. Recommended speed needs an explicit nullable advisory field, units, valid road/run/time and reasoning; current guidance only implements reviewed rerouting. Hide unavailable recommendations rather than manufacturing them.
7. **Personal impact:** expose only a defensible bound-trip result with matched baseline identity and modeled-emission assumptions, or return unavailable with a reason. Until then profile carbon remains unavailable; never reuse the network aggregate as personal savings.
8. **Recovery:** expired/revoked token, application background/resume, replaced socket, host restart, reset, completed journey, lost hotspot and sharing withdrawal must have explicit app states. Reconnect does not silently resume consent.

Prakhyat owns the additive v2 host/map/trip contract and API tests. Kush owns native endpoint selection, invitation parsing, own-trip mapping, route rendering, app states and Android integration. Preserve the frozen v1 message schema.

## P1: repair the browser phone's acknowledgement UX

`web/src/operator/phone.js` currently checks the sharing switch immediately and removes advice as soon as Accept/Ignore is clicked. It does not display a successful route-action confirmation after ACK, and a rejected sharing request does not restore the switch to confirmed state. Server validation still protects the action; the UI can mislead the presenter.

Track pending message IDs, disable duplicate decisions, show pending/confirmed/rejected states, restore the last confirmed consent state on rejection, and show route-applied only after the matching worker ACK. Test delayed/rejected ACKs, disconnect during acceptance, advisory expiry and reset during pending action. The native app already follows acknowledgement-driven consent/action behavior; preserve it in the v2 adapter.

## P1: prove response efficacy before more visual scope

Run fixed, actuated and pressure policies against identical frozen congested demand and identical event schedules. Save complete, fault-free cohorts and report delay, insertion delay, throughput, queue/fairness and modeled CO2, including negative results. Review whether per-movement pressure counts duplicate the same incoming lane's queue across turns; lane aggregates need a justified movement allocation before calibration claims.

Do not claim that the RTX GPU makes SUMO faster: SUMO/TraCI is the simulation worker; GPU resources principally help rendering and optional vision/training. Benchmark actual pace and observer performance on Prakhyat's machine. Train/enable forecasting only after held-out simulation scenarios beat a simple baseline using permitted observations. The current pressure policy is a heuristic, not a trained model.

## End-to-end integration acceptance gate

1. Fresh documented install on Prakhyat's host; start one simulation process. Record commit, Python/SUMO versions and reachable private host address.
2. Open two admin laptops against that host. Owner approves member; viewer cannot mutate; exactly one control lease holder; simultaneous conflicting commands return a clear conflict; all viewers see the same run while their cameras remain independent.
3. Install the new native APK on two phones. Bind different simulated vehicles. Verify both route maps, current speeds and lifecycle on the same run. Without opt-in there must be zero phone observations, even while simulated fixed sensors work.
4. Opt in, confirm fresh validated uplinks, then withdraw/background/disconnect one phone and observe its data becoming unavailable. Never display stale speed as live.
5. Create an eligible slowdown scenario, deliver a scoped offer, accept on the correct phone, and demonstrate worker ACK plus only that vehicle's changed route. Wrong-phone, expired, wrong-run, duplicate and passed-turn decisions must fail safely.
6. Reset, finish and restart. Old tokens/codes/offers cannot attach to the new run. The app explains arrival vs disconnection and asks for a new invite when needed.
7. Export a complete matched comparison. Phone/profile emissions show supported per-trip modeled values or an explicit unavailable state. Keep the saved zero-benefit example honest.
8. Exercise host interruption and recovery without reopening the old “Finished” trap or losing saved result evidence. Record physical-device evidence separately from in-process tests.

## Follow-up prompt for Prakhyat

> Read AGENTS.md, docs/prakhyat-final-build.md, docs/prakhyat-integration-review.md and docs/integration-api-v2.md. Continue your existing unified branch/PR; do not replace Kush's native app or merge main. First implement and test the P0 additive driver capabilities, scoped map and own-trip API so the native client can connect without admin credentials. Preserve frozen v1 messages and one TraCI owner. Include invitation/lifecycle/route geometry/ACK examples and failure reason codes. Fix browser consent/action acknowledgement UX. Then provide completed matched congested fixed/actuated/pressure runs; no improvement claims from incomplete runs. Report changed files, exact tests, setup requirements and physical-device limitations. Ask Kush to integrate the native adapter against the frozen additive API, then complete the two-phone/two-admin acceptance gate together.
