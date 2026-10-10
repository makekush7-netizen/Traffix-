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

## Discoverable registration follow-up

The login dialog now exposes Join this team / create an account. Actual Chrome
verification showed the viewer-account registration form, owner-approval explanation,
username format guidance, password confirmation and return-to-sign-in link.
Submitting mismatched passwords showed the inline error Passwords do not match;
no account creation request was sent. Screenshot:
[operator-signup.png](../artifacts/ui/operator-signup.png).

Registration payload tests now total **5 passed**. The new test verifies username
format, password length, matching confirmation and that clients request access
without selecting an administrator role. Successful account creation and owner
approval require the newly restarted host; this paragraph does not claim those
operations have already been verified.

### Actual signup and owner approval verified

After restarting the host with registration endpoints, an isolated QA account was
created through the actual Chrome form using a random password kept only in the
browser-control process. No password entered source files or screenshots.

- Registration signed the member in as **viewer** automatically.
- The visible notice said operator access was pending owner approval.
- The viewer's Request control button was disabled.
- The host owner signed in and saw the pending request in Team access.
- Only the newly created QA account was approved; existing users were untouched.
- The QA account signed in again and its header role became **operator**.
- Request control became enabled, while the owner-only Team access section was absent.
- Signed out after verification. This account remains in the host's ignored private
  local account store; no account secrets are distributed with the repository.
- Screenshot: [operator-registered-member.png](../artifacts/ui/operator-registered-member.png).

This is local browser registration/approval evidence; it does not establish a
physical handset, remote HTTPS deployment, email identity verification or
password recovery service.


## Functional flow repair evidence

Actual Chrome desktop, local port8005. Screenshots: `artifacts/ui/operator-flow-repaired.png`, `operator-viewer-flow-repaired.png`, `operator-matched-results-repaired.png`.

| Control | Observed result |
|---|---|
| Sign in / Sign out | Session entered and revoked; re-login tested |
| Start / Pause / Resume | Worker acknowledgements; visible simulation time and vehicle movement |
| New scenario / Prepare and start | Previous run saved; reset and initial policy precede resume; fresh revisions |
| Viewer Traffic | Readable overview and access guidance; no disabled scenario form |
| Locations | Local catalog and readiness; only LIG is prepared |
| Follow / First person / Top view | Vehicle selection enables cameras; views changed; unavailable selection has guidance |
| Preview / Apply / End event | Validated event identity, applied host event and ended status |
| Policy / Target pace | Active bounded policy and acknowledged target pace |
| Phone invite | One-use code assigned to a simulated vehicle; no physical handset proof |
| Results / comparison | Cohort counts and measured values; 0% difference preserved; fixed baseline direction checked |
| Recorded run / Return to live | Selected cohort metrics displayed; live mutations disabled during replay |

Protocol regressions also reject Resume/policy failure in the guided flow and ensure fixed-baseline comparison ordering. Loading controls stay unavailable until the local scene exists. Native phone and field camera journeys were not part of these checks.

### Click a vehicle, then Follow

`artifacts/ui/operator-click-select.png` shows car.70 highlighted in orange with synchronized dropdown selection and enabled camera buttons. Actual Chrome canvas clicks selected both a car and motorcycle; Follow moved the camera. Dragging the map preserved car.70. Tests cover click versus drag/pan/cancellation/multiple pointers and small-target ranking/clipping (15 combined frontend tests passed). Browser checks used the existing paused 102-vehicle scene, preserving the live run; movement was not resumed. No application console error appeared (only unrelated Grammarly extension errors).

### Hotspot and reconnect proof

`artifacts/ui/operator-hotspot-ready.png` shows active operator controls and the phone join panel. `artifacts/ui/phone-probe-connected.png` shows the browser adapter connected with acknowledged simulated probes. The host is configured for localhost plus 192.168.137.1; the hotspot URL was also opened, claimed and streamed in Chrome on this laptop. A physical handset and Windows firewall traversal from another device remain unverified. Finished-run Restart was exercised into continuous Explore, and consent withdrawal was confirmed in host status. Null-token stream reconnect now closes cleanly in a regression test.


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
