# Operator UI evidence

Verified on 10 October 2026 (Asia/Calcutta), actual Chrome against laptop host
`http://127.0.0.1:8005`. The browser and SUMO engine were real; traffic,
sensors, incident effects and emissions were simulated. No physical phone or
second laptop was used in this browser test.

- Operator login loaded the actual offline Three.js scene and prepared LIG geometry.
- Before lease acquisition shared reset/resume controls were disabled.
- Acquired control and created quiet demand: seed 42, 600 vehicles/hour,
  20 seconds demand plus 120 seconds drain. Worker acknowledged revision 1.
- Event preview returned `event.990850e71a6d`, revision 2, with no apply yet.
- Applied the validated event at revision 3; resumed at revision 4.
- Browser showed Simulation running, 3.5 simulated seconds, 2 active vehicles,
  and 25.2 km/h mean simulated speed. This is an observed moment, not a benefit claim.
- Reload reconnected to the same shared run without resetting it.
- Control drawer lists incoming/outgoing lanes and protected/permissive indications;
  selecting a junction exposes lane-mapped schematic movement arrows.
- Sign out then reload returned the sign-in dialog and did not restore access.
- The finite test ultimately reached its drain bound with 4 unfinished vehicles;
  Results correctly said Incomplete and showed no matched savings claim.

Actual screenshot: [operator-running.png](../artifacts/ui/operator-running.png).

After restarting the host, catalog/replay verification succeeded:

- `/api/v2/runs` populated 53 saved run entries, each showing reported integrity
  or explicitly unverified integrity.
- Opened the actual saved `lig.77356c3a5c8f` record. Scene status became
  Recorded simulation / read only; snapshot showed 140 simulated seconds and four
  unfinished vehicles. No comparison or savings was claimed.
- Request control and Resume buttons were disabled in replay.
- Persistent Return to live restored the live paused host at revision zero;
  no reset or shared command was submitted by replay.
- The selected record contained only one frame, so its slider max was zero.
  The replay interface does not invent missing history. This capture provides
  a final-frame replay, not a video of that run.
- Saved actual screenshot: [operator-replay.png](../artifacts/ui/operator-replay.png).

Automated local browser-independent checks:
`node --test web/src/operator/protocol.test.mjs`: 4 passed.
`node --check web/src/operator/app.js` and shared scene syntax checks passed.
These tests validate causal source gaps, LAN command IDs, event-preview normalization
and scenario setting rejection. They do not replace multi-device, slow-viewer or
long-duration visual/performance tests.
