# Prakhyat unified build return

Build branch: `feat/prakhyat-unified-simulation`. Draft PR: https://github.com/makekush7-netizen/Traffix-/pull/3. Base: `feat/kush-demo-polish`. API version **2.0**. This report distinguishes implemented behavior from evidence still unavailable.

## Launch

Use Python 3.12 and install `backend/simulation/requirements.txt` into a virtual environment. SUMO 1.28.0 is supplied by its pinned wheel; no system-wide SUMO install is required. Node is needed only for the browser module tests. All scene assets are local.

```powershell
python -m pip install -r backend/simulation/requirements.txt
$env:TRAFFIX_ACCOUNTS = '{"operator":{"password":"REPLACE-WITH-YOUR-PASSWORD","role":"operator","can_takeover":true},"viewer":{"password":"REPLACE-WITH-ANOTHER-PASSWORD","role":"viewer"}}'
python -m scripts.run_unified
```

Open http://127.0.0.1:8005. Accounts are explicitly configured; there is no public bootstrap password. For LAN, set `TRAFFIX_HOST=0.0.0.0`, permit this Python process on the private network firewall and use the host's LAN address on clients. Permit only port 8005; do not expose TraCI or a shell. Plain LAN HTTP is for a trusted demo network. Online access requires HTTPS/WSS at an authenticated tunnel/reverse proxy, a secure configuration and a separate integration check; no public URL was deployed.

The sign-in screen now includes **Join this team · create an account**. Registration creates a viewer immediately and can request operator access. A configured owner (`operator` with `can_takeover:true`) approves requests in Control → Team access; the member signs in again after approval. Public signup cannot create an owner. Registered credentials persist as salted scrypt hashes in ignored `.cache/private/accounts.json`; bootstrap credentials remain configured by the host. Registration/approval/persistence and existing host/phone checks passed in a targeted 17-test run; the browser protocol suite now has 5 passing tests. No repeated full-suite claim is implied by this registration update.

On this laptop the exercised Python executable is `C:/Users/prakh/Documents/Codex/lig-venv/Scripts/python.exe`. The default system Python is 3.14 and was not the tested runtime. To create a project-local environment, run `scripts/setup_unified.ps1 -Python312 <path-to-Python-3.12>`; then use `.venv/Scripts/python.exe` for the commands above. The setup script has passed PowerShell parsing; installation into a fresh environment remains a separate reproducibility check.

## Short live demonstration

1. Log in as an operator, request the control lease and select LIG. The other prepared-location entries show their review status.
2. Configure a quiet finite scenario with a generous drain; start it. Select a vehicle, use Follow/First person, then inspect the same network in the minimap.
3. Preview a rain or roadworks restriction on an approach, then apply it separately. Show the revision and actor audit. The event effect is a simulated speed restriction.
4. Select the pressure heuristic. Inspect incoming/outgoing movement labels and action explanations. Clearance is worker-managed; displayed signal colours remain separate from congestion colours.
5. Enable phone guidance explicitly and issue one-use invites. A native client must opt into sharing server-issued simulated frames. A route offer requires fresh phone evidence and a safe reviewed bypass; an arbitrary vehicle is not promised an offer.
6. Accept an eligible offer and show the worker-confirmed acknowledgement. Without actual connected devices, use the automated two-client test and call it automated evidence.
7. Open Results and replay a saved run. Mutations are disabled during replay; Return to live preserves the shared host. Show unfinished vehicles and fault status before any comparison.

Do not improvise a savings number. The small matched smoke cohort completed under all three tested policies with identical modelled emissions; it establishes execution, not response effectiveness.

## Integration

Read `docs/integration-api-v2.md`, `contracts/v2/openapi.json`, `contracts/v2/command.schema.json` and `contracts/v2/examples.json`. Use `python -m scripts.mock_v2` and `scripts/client_v2.py` for independent client development. Shared mutations carry run identity, command identity and revision and execute on the sole SUMO owner. Retries are idempotent. Camera, selection and drawers remain local to each viewer.

The existing MobileBridge handles server-issued phone bindings and validated driver frames. Phone observations remain separate from simulated lane sensors and camera measurements. Synthetic detector fixtures never establish real-camera accuracy or real-phone coverage.

## Verification

See `docs/prakhyat-inventory.md` for measured hardware/runtime. Initial real SUMO host boot completed in **0.89 wall seconds**, with clean shutdown; this is startup evidence, not a throughput capacity guarantee. Final Python regression suite: **224 passed, one inherited failure, one upstream Starlette warning, 147.01 seconds**. The failure is explained below. Browser protocol tests: **4 passed**; app and shared scene syntax checks passed. Python compile checks and setup-script PowerShell parsing passed.

Reproduce with Python 3.12, initialized SUMO binary path and working localhost socket permissions:

```powershell
python -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q','--basetemp=.cache/pytest-local','--tb=short']))"
node --test web/src/operator/protocol.test.mjs
```

The execution sandbox blocks TraCI localhost sockets; real simulation checks were run with authorized elevation. Normal laptop launch does not require administrator privileges just to run SUMO.

The final two-client test uses real SUMO and two authenticated in-process client sessions. Server-issued probes with consent establish a fresh observation window; a delayed acceptance after consent withdrawal is rejected; explicit acceptance is acknowledged only after a reviewed, class-compatible route is worker-confirmed. This is a controlled route-A test scenario, not a physical-device or WebSocket-network test. Saved evidence: `artifacts/unified-phone-client-evidence.json`, including 35 recorded frames and one actual worker route event.

The real pressure-worker smoke scheduled 18 vehicles, completed 17 and retained one active vehicle at its 420-second bound, with zero collisions or teleports. It took **49.16 wall seconds** under an unpaced worker stepping test. This is one workload measurement, not maximum supported throughput or a memory-soak claim. The result is **incomplete**. Retained evidence: `artifacts/unified-pressure-worker-smoke.json`. An earlier short paired smoke completed 5/5 vehicles under fixed, bounded and the earlier pressure implementation, with identical emissions; it is explicitly labelled as predating the phase-selection upgrade in `artifacts/unified-paired-smoke-summary.json` and must not be used to claim the new policy improves journeys.

Actual Chrome UI checks and screenshots are recorded in `docs/prakhyat-ui-evidence.md`: operator login, control lease, reset, preview/apply, resume, reload preserving the run, sign-out, saved catalog and read-only replay. Replay mutation controls are disabled and Return to live preserves the shared host. The historical screenshot's single-frame recording exposed a retention bug; the new regression verifies the repaired one-second sampler and final frame. Physical multi-laptop rendering and prolonged memory/overload soak remain unverified.

Existing coordinator baseline regression: the preserved demo reference uses network hash `5e1ba257…`, while the source branch's current geometry produces `317fbe071…`. Its comparison correctly reports unavailable; `tests/test_demo_end_to_end.py` expects available and fails. This failure was present before this implementation. The compatibility hash guard must stay enforced; no old reference is silently relabelled.

## Limits to carry into the demo

- LIG uses existing OSM geometry and assumed demand. The additional Indore locations await reviewed topology packs; their status is shown explicitly.
- No calibrated city demand, real-world prediction benefit or measured carbon saving is established. ML-assisted control remains gated.
- No verified ambulance route/preemption/recovery was supplied. The UI marks that action unavailable.
- Real two-laptop/two-phone physical evidence and permitted held-out camera clips are unavailable in this session. Automated client tests are emulation, not physical-device proof.
- Vision supports independently testable local tracking/counting and an optional reviewed-weights adapter. Without calibration, speed is unavailable. Object detections do not establish incident cause.
- No reviewed local vehicle dataset, camera accuracy, CUDA inference capacity, public tunnel or independent multi-run hosting claim is established.
- Neighbor-arrival coordination, calibrated bus-stop dwell schedules, verified emergency recovery and reviewed additional location packs remain outside this delivered implementation. Event kinds currently compose explicit speed restrictions or sensor outages; they do not simulate rally crowd dynamics or diagnose an incident cause.
- Camera adapter ingestion is validated and source-tagged, but externally ingested camera observations remain disabled for live control until a reviewed calibrated mapping exists. Live pressure control uses explicitly simulated lane sensors; phone guidance uses consented phone observations.
- The dashboard uses authenticated polling with timeout/stale-state disabling; the versioned authenticated WebSocket stream is also published for clients. No automatic retry of a lost mutation occurs.

The build is runnable and the new host/phone/controller tests pass. The full suite is not all green because of the preserved legacy baseline incompatibility. Keep the PR in draft until the team reviews that compatibility decision and the remaining device/deployment checks.


## Dashboard repair following usability review, 10 October

The previous dashboard was runnable but not a finished operator flow. Viewer navigation led to a disabled scenario form, run controls were buried, Results foregrounded JSON, and camera controls overlapped the drawer. These were product defects.

The repaired flow is: sign in → Start simulation, or New scenario → choose demand and initial signal policy → Prepare and start simulation → Events preview/apply/end → Results → matched comparison or recording → Return to live. Start requests an available lease without taking control from another operator. Reset, initial policy selection and Resume wait for separate worker acknowledgements and refreshed revisions. Rejected commands do not produce a success message. Changing policy after the initial window or editing events invalidates a matched comparison; choose the initial policy in New scenario for the reproducible experiment.

New members have a persistent pending-access explanation. Registered viewers may request access; configured viewers are directed to the host owner or their own registration. Viewer Traffic shows an overview instead of an unusable mutation form. Follow and First person require selection. Events default to roads used by the demand routes, with explicit search for any network road and readable preview details. Results show live lifecycle/full-cohort counts, measured completed journey time and modelled CO2; raw evidence sits in Advanced. The default catalog shows recent complete records with execution fingerprints and lifecycle measurements. Replay uses the selected recording's results, disables mutations and preserves the live host.

Fresh verification: **233 passed, one inherited failure, one warning, 545.45 seconds** in the broader Python run. The remaining failure is still the preserved phone-demo baseline network mismatch in `tests/test_demo_end_to_end.py:93`; no matching guard was weakened. After final auth edits, **8 focused access/comparison tests passed** (one real-SUMO test deselected because it had already run in the broader suite). Final browser protocol suite: **11 passed**; app syntax passed. Logs: `artifacts/dashboard-flow-test-results.txt` and `artifacts/dashboard-access-comparison-test-results.txt`. The diagnostic test timings include a long Windows run and are not performance benchmarks.

Actual Chrome checks exercised operator sign-in, one-click Start/Pause, Follow/First person/Top view, scenario reset/start, initial bounded policy before resume, pace change, phone invite creation, event preview/apply/end, complete live cohort, matched comparison in both navigation directions, replay/return and viewer-only navigation. Final initial-policy manifest: bounded, `scenario_mutated=false`. No physical phones were used in this browser check.

A complete fixed/bounded two-vehicle smoke pair measured **284.24 seconds mean journey and 1.2014 kg modelled CO2 in both policies: 0% benefit**. See `artifacts/unified-complete-pair.json`. This is execution/comparison evidence, not congestion-response efficacy. Interactive runs with edited events remain ineligible for savings headlines. Current network ML advantage, calibrated fleet mapping, native phone integration, additional reviewed locations and secured public deployment remain unproved/unavailable as described above.

Host is running locally on port 8005 with the final code. Restart invalidates sessions; refresh and sign in again. Existing registered account hashes were preserved. Owners must explicitly approve real members; this repair does not silently grant control access. The draft integration PR remains open; nothing was merged.

### Direct vehicle selection (2026-10-10)

Click a visible simulated vehicle in the map to select it. An orange ring identifies the selection; the vehicle dropdown stays synchronized and Follow / First person become available. Selecting another vehicle stops following the old one without jumping the camera; press Follow for the new selection. A small CSS-pixel tolerance helps pick tiny visible vehicles in Overview. Orbit/pan drags, cancelled touches and multiple pointers do not select vehicles. Selection clears when its vehicle disappears or the run changes. No host commands or API changes are involved.

Verification: 15 frontend tests passed (11 existing protocol cases plus four picking/gesture cases); both application and scene syntax checks and git diff whitespace checks passed. Chrome checks selected motorcycle.6 and car.70 directly on the canvas, enabled Follow, confirmed camera movement, visible orange highlighting and unchanged selection after map dragging. The existing host run remained paused at 230.5 seconds with 102 active vehicles; live motion was not resumed for this check. No application console errors were observed; Grammarly extension errors are unrelated. Evidence: artifacts/ui/operator-click-select.png.

### Connection, continuous viewing and motion repair (2026-10-10)

Added a Reconnect button and cached drawer navigation while disconnected; host mutations stay guarded. Dashboard uses the authenticated 5-Hz stream with HTTP fallback, and a tested 240-ms position/angle buffer instead of frame-count-dependent bursts toward one-second poll targets. Static shadows are cached and render work capped at 30 fps (configuration, not a universal achieved FPS claim). Corrected road-colour keys to actual geometry IDs and explicitly mapped permitted phone bridge observations back to those IDs. Phone sessions receive PHONE markers; no hidden truth is labelled a phone uplink.

Added an operator browser phone adapter, selected-vehicle invites, QR/link presentation, real connected/sharing status and accepted uplink counts. The phone claims a one-use code, receives authenticated own-vehicle frames, sends probes only with consent, stops sharing on disconnect and rejoins after reset. Physical GPS and native-app implementation remain separate. Completed runs preserve results and offer Restart default simulation into continuous Explore; no auto-reset on a network fault.

Launch: Start-Traffix.cmd or scripts/start_unified.ps1. This laptop's private runtime/accounts/hotspot settings are ignored by Git. One Uvicorn/SUMO owner listens on localhost and the explicit 192.168.137.1 hotspot address, avoiding wildcard/campus listeners. Both URLs returned HTTP 200 on this laptop. No firewall rule changed; a physical phone over Wi-Fi remains unverified. Earlier statements that the host had stopped were corrected: sandbox checks were misleading, while an unrestricted HTTP check confirmed a healthy paused host. The exact cause of the user's Brave connection failure was not reproduced. A null-token WebSocket reconnect race was reproduced, fixed and regression-tested.

Verification: 18 focused Python tests passed with one existing TestClient deprecation warning, including a real SUMO completed-run test; 18 frontend tests cover protocol, picking, buffered motion and phone coverage mapping. Actual Chrome exercised operator login, Start, Control, QR invitation, browser phone claim/stream, more than 200 acknowledged probe samples, consent withdrawal confirmed by host status, completed-run restart and phone run-reset feedback. Screenshots include artifacts/ui/phone-probe-connected.png; the handset itself was not tested. See docs/phone-and-recovery-guide.md for exact launch and phone steps. Previous run evidence was preserved in ignored .cache/run-before-recovery.json and .cache/run-before-hotspot.json; saved run catalog remains available.

Final host was restarted with the tested stream guard and left running everyday/fixed Explore. The one-click launcher recognized the already-running host. Browser claiming through the explicit hotspot HTTP origin also succeeded; this confirms same-origin/token plumbing on that address from the laptop, not physical handset reachability. See artifacts/ui/operator-hotspot-ready.png.

Control actions now acquire an available lease automatically, including after expiry; conflicting operators are not taken over. Vehicle options and signal detail nodes are only rebuilt when their contents change, preventing the live stream from repeatedly replacing controls during interaction. Local probe sessions used for QA are closed after evidence capture; they are not permanent emulated traffic sensors.


## Adaptive signal visual distinction · 10 October 2026

The operator scene now distinguishes policy state without changing SUMO traffic,
demand, signal indications or measured results:

- Fixed timing: standard red/amber/green heads, neutral baseline badge.
- Bounded, actuated and pressure: cyan junction outline and halos around signal
  heads, with an explicit named policy badge. Cyan means policy enabled, not a
  proven improvement or a green indication.
- Only a newly received worker-confirmed `signal_extension` or
  `signal_transition_completed` produces a short outline pulse. Starting a
  transition, loading old history, duplicates and natural green changes do not.
- Missing fresh movement observations show amber markers; paused/completed or
  disconnected scenes show grey inactive markers. Reduced motion disables pulses.
- The Signals camera button focuses the junction with the most mapped signal
  heads. Detailed movement arrows remain available through Control indications.
- Last confirmed action shows its junction number and simulated timestamp.

Verification: 22 focused Node tests passed (signal presentation, motion, picking
and operator protocol); JS syntax checks and git diff whitespace check passed.
Actual Chrome browser check switched the existing Explore run from pressure to
fixed and back, verified the badge and outline change, and verified paused state.
No reset or new traffic cohort was required. This visual check is not a matched
performance comparison. Screenshots: `artifacts/ui/operator-signals-fixed.png`
and `artifacts/ui/operator-signals-adaptive.png`.

To see it: refresh the dashboard, choose Control > Signal policy >
Capacity-aware pressure heuristic > Apply policy, close the drawer, then click
Signals. Use Fixed timing to see the baseline appearance. Use separate finite
matched experiments for performance results.

## PPT benchmark evidence — 10 October 2026

See `docs/ppt-improvement-report.md` for the copy-ready results, limitations and
reproduction commands; `docs/ppt-algorithm-and-sensor-evidence.md` explains the
actual controller, prediction gap and primary phone-probe sources.

Frozen pressure control reduced mean journey time by 11.31% and modelled CO2 by
7.48%, averaging paired reductions over held-out seeds 51 and 52. Each policy
completed all 128 scheduled vehicles across those seeds, with no collisions or
teleports. Simple actuated extensions averaged 0.54% journey improvement.
Stress seed 53 fixed timing completed 133/135, so percentage savings are withheld.
Development seed 42 is reported separately and includes worse P95 stopped waiting.
The long-running live Explore session remains prone to overload and collision
involvements; these finite-cohort results do not validate sustained overload.

Saved batch manifests, trip XML and recording checksums are under
`artifacts/ppt-benchmark-evidence/`; slide PNG/SVG and run tables are under
`artifacts/ppt-benchmark-heldout/`. All attempted batch outcomes remain available,
including the initial wall-clock timeout. No new predictive accuracy is claimed.

Results now renders the existing snapshot instead of requesting the full live
recording. The authenticated API also supports `GET /api/v2/results?summary=true`;
full export remains available. The new backend endpoint requires host restart;
the client snapshot improvement takes effect on browser refresh.

Fresh verification: 30 Python tests passed (benchmark report, simulation API,
detection, forecast and probes), 22 Node tests passed, operator JS syntax and
`git diff --check` passed. One existing FastAPI/Starlette deprecation warning.
This is focused verification, not a claim that the entire repository suite passes.
