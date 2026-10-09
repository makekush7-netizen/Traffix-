# Traffix: judging demo in three minutes

## Which screen?

- Mentor flow: http://localhost:8002/dashboard. This is deliberately 12 staged
  vehicles, one monsoon scenario and one driver-approved route change. Vehicles
  spawn once; Reset demo starts a fresh run. Start demo makes them move.
- Earlier exploratory engine: http://localhost:8001/. This retains everyday,
  rush, rain and roadworks. Its heavy-demand runs can collide and remain unfinished.
  Use it only as an experimental map/traffic viewer, not proof of performance.

## Prepare before judges arrive

Run `./scripts/run_mobile.ps1` if port 8002 is not already running. Run
`./scripts/demo_check.ps1` in another terminal. Open one operator dashboard.
Connect two real phones to the laptop hotspot. In Advanced click Reset demo.
Add phone, choose Rider, use the LAN address printed by demo_check, create the QR,
scan and Join the drive. Repeat for Auto driver. Sharing starts off. Join both
before starting. On this machine the hotspot URL was http://192.168.137.1:8002/driver;
verify the current address rather than assuming it remains the same.

## Say and show

1. Show grey roads. Say: "Many roads lack sensors. Traffix explores whether
   drivers can help an operator see a developing slowdown. These are real LIG
   Square street shapes, with simulated vehicles and assumed traffic."
2. Turn sharing on on BOTH phones. Show two reporting phones and one observed
   road. Say: "The laptop sends each phone its own simulated vehicle frame.
   Only samples the phone actually sends back enter the traffic observations.
   Without those uplinks, a road stays unknown."
3. Turn Traffix guidance on, select 4x, click Start demo. Wait about eight real
   seconds for 30 simulated seconds of sustained slowdown. The offer pauses the
   run automatically. Say: "Two phones show sustained slowdown. Our current
   prototype uses a simple rule to propose a pre-validated alternate route."
4. Show the Rider phone's guidance card before tapping. Say: "This is a proposal.
   The driver chooses, and the server checks whether the turn is still valid."
   Tap Take Route B. Show Route B applied and the operator event log.
5. Click Resume. Say: "That simulated vehicle now follows the new route. Other
   drivers remain on their original routes." Let the run finish at 4x while
   explaining the architecture: SUMO → bound phone → validated observation →
   rule → driver choice → worker-confirmed route change.
6. Show complete results only when available. Say: "The comparison uses saved
   complete runs with matching scenario and seed. It is one synthetic experiment,
   not a claim of real-world savings."

## If asked about AI or Indian traffic

"Prakhyat has a separate ML training/evaluation branch. We have not established
that it improves on the simple rule, so this live demo does not use it. Mixed
vehicle appearances are implemented; realistic Indian driving and demand still
need field data and calibration."

## Backup

Advanced → Play recorded baseline shows a clearly labelled fixed-policy recording.
For the full recorded browser story, use Open saved walkthrough and the local
`runs/mentor-walkthrough.json` file produced during validation. Say "recording"
before showing it. This is a phone browser app; native APK packaging is pending.

The physical two-phone hotspot test remains required before claiming the demo
has passed on real devices. See demo-runbook.md for reconnect/reset troubleshooting.
