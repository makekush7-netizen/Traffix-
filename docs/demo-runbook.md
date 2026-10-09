# Traffix v1.0 mentor-demo runbook

Offline browser app; real LIG Square geometry, simulated vehicles and assumed
traffic. Demonstrates the observation-to-consent loop. No trained-model decisions
or real-world time savings are claimed.

## Start-up order

1. Open PowerShell in the inner `trafixx` repository. Plug in the laptop and join
   both phones to its hotspot. Keep it awake for the presentation.
2. Run `./scripts/run_mobile.ps1`. Leave that terminal open. The demo starts on
   port 8002, seed 42, paused and guidance off, with one TraCI worker.
3. Run `./scripts/demo_check.ps1` in a second terminal. Require four PASS lines.
   Read its LAN phone URL. Actual phones must use that address, not localhost.
4. Open `http://localhost:8002/dashboard`. Advanced → Reset demo returns to the
   same seed. After reset, issue fresh invitations and rejoin the phones.
5. Advanced → Reduced effects if rendering is slow. The displayed frame rate is
   a current rendering sample, not a guaranteed minimum on every device.

## Exact presentation flow

| Stage | Clicks | One sentence to say |
|---|---|---|
| Blind spot | Add phone → Rider → enter laptop LAN address → Create join code. Scan on phone 1 and tap Join the drive. Repeat for Auto driver on phone 2. Leave sharing off. | “These are simulated vehicles on real LIG streets; without phone uplinks, Traffix knows nothing about these roads.” |
| Phones see | Turn Share traffic samples on on both phones. Show two phones reporting and the coloured approach among grey roads. | “Drivers opt in, and only their validated samples make a road observed.” |
| Traffix decides | Turn Traffix guidance on, choose 4×, Start demo. After 30 simulated seconds of observed slowdown, the offer automatically pauses the simulation. | “Two fresh phones sustained slowdown for 30 seconds, so a simple rule proposes a pre-validated alternate route.” |
| Driver follows | On Rider, tap Take Route B. Wait for Route B applied, the new path and the operator log. Then Resume. | “The driver has the choice; only a valid acceptance and server confirmation change this vehicle’s route.” |
| Result | Continue at 4× until all 12 journeys finish; allow about two minutes. Show comparison only when available. | “These are complete matched synthetic cohorts; one pair is not evidence of general traffic savings.” |

Add phone pauses a running simulation so onboarding cannot consume the decision
window. Invitations are single-use and expire after two wall-clock minutes.
Join Rider first for a predictable presentation. An offer is addressed to an
eligible reporting driver. No thanks keeps Route A; reset/rejoin before showing
Accept. Keep the simulation paused while narrating the offer: its expiry and
decision-point checks use simulated time.

The phone says travel-time estimate unavailable. Do not invent a number. Phone
samples echo simulation frames through the real network; they are not phone GPS.
Bypass capacity uses a disclosed simulated installed sensor. Detection uses only
validated phone observations, never hidden scene traffic truth.

## If something fails

- Phone drops: keep the simulation paused. Restore Wi-Fi, let the bound session
  reconnect, then manually turn sharing on again. Reconnect starts sharing off.
  Two fresh phones are needed; missing/stale samples remain unknown.
- QR fails: check the address against demo_check. Open its LAN `/driver` URL
  manually and type the displayed code. Generate another code if expired.
- Wi-Fi fails: verify both phones share the laptop network. A localhost PASS does
  not prove LAN/firewall reachability. Keep security protections enabled; use the
  recording backup if network setup cannot be fixed before presenting.
- SUMO/server fails: the operator shows Offline after three seconds. Displayed
  positions are stale. Restart the script, reset, issue new codes and rejoin.
  demo_check rejects a server running an older configuration.
- Accept is late/expired/cancelled or evidence is insufficient: the phone shows
  a friendly rejection and keeps Route A. Reset for a fresh valid offer.
- Comparison unavailable: wait for all journeys. Incomplete runs, faults or
  mismatched hashes invalidate it. Do not force numbers. Changed assumptions
  require a newly recorded matched baseline.

## Recording backup

Before presenting, complete a walkthrough. Advanced → Save walkthrough replay
downloads a JSON recording of scene/operator states without tokens. Keep it local.
Open saved walkthrough loads it; the badge says RECORDED and live controls are
disabled. It replays saved visuals, cannot apply routes and does not provide live
phone interactions. Reload to return to the live dashboard.

Play recorded baseline uses the bundled fixed-policy recording. It has no phone
observations or guidance; it does not manufacture an acceptance story. Assets and
recordings are local. Keep the server available to serve the app and map files.

Screen-capture checklist: grey roads/sharing off; both phones opting in; two
reporting phones; evidence; offer before consent; applied acknowledgement/new
path; final integrity counts; RECORDED labels on the backup. Avoid exposing valid
invitation codes in a public video.

## Reproduce verification

```powershell
./scripts/demo_check.ps1
.venv/Scripts/python.exe -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q']))"
.venv/Scripts/python.exe scripts/check_demo.py --repeats 3
```

Headless checks write `runs/demo-validation.json`; raw runs are intentionally
ignored by Git. Export saved run saves the live evidence. Each run's
`phone-guidance.jsonl` records guidance/decisions, and the simulation recording
contains the worker's actual route-applied event.

Remaining physical-device gate: scan and bind two distinct roles; verify sharing
starts off; opt in; receive/accept the offer; confirm only its addressed phone
gets Route B; reconnect one phone and verify sharing turns off.
