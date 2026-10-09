# Traffix mobile app and phone-to-LIG bridge

This release runs the driver screens, operator dashboard, and existing 3D LIG
simulation in one FastAPI process. It is a mobile browser application, not an
Android APK. It uses bundled assets and OSM geometry without online map tiles,
phone GPS, or cloud services. Phone positions are explicitly simulated.

## Launch and two-phone rehearsal

From this repository, run `./scripts/run_mobile.ps1` in PowerShell. It uses the
existing virtual environment and listens on all interfaces at port 8002, leaving
the earlier fixture on 8000 and older lab on 8001 available. Dependencies are
`requirements.txt`, `sumo-requirements.txt`, and `backend/harness/requirements.txt`.
Run exactly one worker. Only that process's SUMO owner thread calls TraCI.

1. Open `http://localhost:8002/dashboard` on the laptop. Keep this page open.
2. Connect both phones and laptop to the same hotspot or Wi-Fi. In the dashboard,
   enter `http://<laptop's hotspot/Wi-Fi IPv4>:8002` in Phone access address.
   Address discovery may list multiple adapters: choose the one phones can reach.
3. Select an active vehicle, create a code, and scan the QR using the phone camera.
   The code is prefilled; tap Join the drive. Alternatively type the code manually.
4. Repeat with a different vehicle for the second phone. Each vehicle has only one
   claimed session. Codes are single-use and expire after 120 wall seconds.
5. Both phones begin with sharing off. The dashboard must show zero uplinks and
   unknown roads, although cars remain visible in the separate simulation view.
6. Enable sharing on one phone, then the other. Exact server frames return as
   `probe.sample`; only accepted samples produce observations. Play the simulation
   to see new positions and uplinks; paused time does not manufacture samples.
7. Submit a road report. It must appear in the dashboard as unverified. Send an
   operator note to one connected phone and acknowledge it there: the server
   confirms receipt; this does not reroute the vehicle.
8. Turn sharing off, reload a phone, then disconnect Wi-Fi. Withdrawal removes
   samples immediately on explicit off/disconnect, or after six wall seconds
   without heartbeat. Reload/reconnect keeps the same vehicle and starts sharing off.
9. Reset the scenario from the 3D lab. Existing sessions and codes become invalid;
   issue new ones. Export simulation and phone evidence from the dashboard.

If a phone cannot open `/driver`, check the laptop IPv4 and existing Windows
firewall permission for Python on the private demo network. Keep phones in the
foreground. This HTTP synthetic-data demonstration is not production deployment.

## Implemented behavior

- Operator credentials are generated per server launch and obtained only from
  loopback. Bearer authentication guards commands, join issuance, notes and phone
  evidence exports. Driver sessions cannot execute operator commands.
  Trusted Host checks allow loopback and discovered local IPv4 addresses. If a
  hotspot address was not discovered, set `TRAFFIX_ALLOWED_HOSTS` to that address
  before launching. Do not broaden it to arbitrary external hostnames.
- Session authentication and frame validation reuse the frozen shared contracts.
  Codes bind server-selected real SUMO IDs; phones cannot select pose/time/vehicle.
- `/ws` carries contracted phone events. `/ws/lab` is a separate, explicitly
  simulation-truth display stream. The fixture server remains independently usable.
- SUMO native edge IDs are mapped to stable `edge.lig.<index>` IDs because some
  native IDs contain characters forbidden by the contracts. Geometry includes
  `contract_edge_id`; evidence exports include the complete reverse lookup inputs.
- Samples must exactly echo frames issued to that session. Wrong run, vehicle,
  unknown frame, duplicate, altered, future and stale frames are rejected. Message
  size, origin, sequence, recent message IDs and wall-time rates are checked.
- ObservationAggregator and trend ForecastService consume only validated phone
  samples and static reference speeds. No hidden vehicle counts/speeds, scripted
  incident schedule, detector truth, or trained fixture artifact becomes a probe.
  Trend outputs are prototype estimates; all live control flags stay disabled.
- Heartbeats run every two wall seconds; samples expire after 15 simulated seconds.
  An independent server task updates coverage, expiry and prototype histories.
  Withdrawing consent also clears cached historical forecasts to avoid retained
  contributions. This conservatively resets other phones' forecast warm-up too.
- Dashboard coverage roads stay gray without fresh observations. The 3D lab's
  all-vehicle metrics remain separately labeled simulation truth. Reports and
  operator notes remain unverified and are never promoted to congestion facts.
- An incident note expires after 120 simulated seconds and only its bound driver
  can acknowledge it. Route decisions and automatic signal control are unavailable.
  Existing action guards are preserved; this release does not claim their live
  integration or a complete detect-to-reroute experiment.

## Verification and limitations

Final regression on 2026-10-09: **151 passed, 2 warnings in 37.96 seconds**.
Command: `.venv/Scripts/python.exe -c "from scripts.verify_nandani import
prepare_environment; prepare_environment(); import pytest; raise
SystemExit(pytest.main(['-q']))"` (join the displayed command into one line).
Warnings are existing Starlette/httpx deprecation and Windows physical-core
discovery fallback. Node syntax checks passed for both new browser modules and
the updated 3D entry point.

Browser rehearsal used two distinct vehicles, sharing switches, real accepted
frames, operator play/pause confirmations, an unverified report, an advisory
acknowledgment and reload retaining the same vehicle with sharing off. At the
390-by-844 phone viewport, layout and scroll widths matched (375 usable CSS
pixels, with the browser's scrollbar). The preview is saved under ignored
`runs/mobile-driver-preview.png`. No physical-phone test is claimed.

Acceptance tests exercise two real SUMO-bound WebSockets, zero uplinks, permission
withdrawal while paused, tampering, role separation, expiry, run reset, duplicate
IDs, and unverified advisory receipt. Existing gateway tests cover exact frame
binding and stale/future/wrong-run behavior. Browser rehearsal covers the phone
screens and operator flow; physical two-phone/hotspot testing still requires the
steps above. Browser device-size tests do not substitute for physical phones.

The earlier LIG congestion/collision/cohort limitations remain as recorded in
`docs/lig-validation.md`. No measured improvement, reliable ETA, trained live
controller, native APK, or full calibrated Indian driving model is claimed.

Changed files are the new `web/src/mobile/` screens and assets,
`backend/harness/mobile.py`, harness app/engine and lab entry points,
backward-compatible `backend/session.py`, `tests/test_mobile_bridge.py`, the
existing harness integration test, `scripts/run_mobile.ps1`, ownership notes,
this runbook and the README. Shared contracts and ML implementations are untouched.
