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
