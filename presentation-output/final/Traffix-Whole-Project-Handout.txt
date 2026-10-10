# Traffix: whole-project handout for teammates and new AI agents

Version: 10 October 2026. This is a self-contained learning and onboarding document. It explains the project and the evidence available at this snapshot. It is not a claim that every planned feature is complete. Implementation and installation status can change after this date.

## 1. Upload this file to your AI and paste this prompt

> Read the entire attached Traffix handout before explaining it. First ask my preferred language, such as Hindi, Hinglish or English, and whether I want a beginner, presentation or technical explanation. Teach me the project step by step in that language using familiar traffic examples. Explain the problem, the product, how the simulation, admin dashboard and phone connect, how signals choose phases, detection versus forecasting, and what the results actually prove. Explain every percentage with its policy, seed group and evidence status. Keep verified results, handoff-reported experiments and future plans separate. Do not invent features, accuracy, field results or successful device tests. Give me a short presentation script, answers to likely judge questions, and five comprehension questions. If I am a coding agent, first explain the architecture and constraints, then inspect the actual repository and current status before proposing changes. This upload alone does not authorize code changes, deployment, public access or new experiments.

The AI may translate explanations, but must preserve numbers, units, algorithm names and the distinctions between measured, reported and planned work. It can teach one section at a time. A teammate does not need to understand every code detail to present the product honestly.

## 2. The project in one minute

**Traffix is a traffic congestion response prototype and testing environment.** It models roads around LIG Square in Indore, creates simulated mixed traffic, gives an operator a shared dashboard, connects a phone to one simulated vehicle, and evaluates bounded responses against fixed signal timing.

The central question is: **Can this traffic response reduce journey delay without creating unacceptable queues or safety problems elsewhere?**

The implemented pressure controller reacts to current upstream queues and downstream space. It changes signals through the simulation worker with timing and clearance protections. The project also has a congestion detector and forecasting candidates, but the demonstrated signal-control savings come from the reactive heuristic.

The final PPT headline is **11.31% shorter mean journey time and 7.48% lower modeled CO2**, averaged across two held-out matched simulation seed pairs. These are small-sample simulation results. They are not measured improvements on Indian roads.

## 3. The traffic problem we address

Traffic demand changes over time. A fixed signal schedule may give green to a lightly used approach while another approach builds a queue. A downstream road can be full, so giving the upstream queue more green may simply push vehicles into another blockage.

Mixed vehicles add complexity: motorcycles, cars, auto-rickshaws, e-rickshaws, buses and delivery vehicles have different dimensions and movement behavior. The project includes these classes in its assumed simulation demand. Their inclusion does not prove that the simulator reproduces all Indian driving behavior.

Observations also have limits. A few participating phones can provide speed samples, but do not count every road user. A stopped vehicle may be waiting at a normal red light rather than stuck in a persistent jam. Old or missing observations cannot justify confident control.

Traffix therefore combines a visible experiment, source-labelled observations, bounded actions and saved comparisons. The road map alone does not reveal today's traffic demand or correct field signal settings.

## 4. What each part does

| Part | Plain explanation | Boundary |
|---|---|---|
| SUMO simulation | A traffic engine advances vehicles along legal roads and routes | Vehicles and traffic demand are simulated |
| OpenStreetMap geometry | Supplies the road geometry used for the LIG environment | Geometry is not a measured traffic dataset |
| Operator dashboard | Lets an authorized operator inspect the scene, configure runs, choose policies and inspect results | Its 3D appearance does not establish effectiveness |
| Phone/browser probe | Joins a server-assigned simulated vehicle and can share its issued observations with consent | The prototype observations are not handset GPS traffic measurements |
| Native companion | React Native/Expo driver application with a built Android preview | An APK build or transfer does not prove physical end-to-end success |
| Detector | Looks for persistent usable slowdown evidence | Does not identify the incident cause from slowdown alone |
| Pressure policy | Chooses eligible signal phases using queues and receiving space | Reactive heuristic, not trained predictive AI |
| Forecast pipeline | Candidate predictions of future slowdown | Useful forecast accuracy and predictive-control benefit remain unvalidated |
| Evaluation and saved evidence | Compares matching complete baseline and response runs | Invalid, incomplete and negative outcomes must remain visible |

The public submission frontend is at `https://traffix-demo.vercel.app/`. It is separate from the persistent local SUMO host. Do not describe the static frontend as a publicly running full simulation backend.

## 5. Who uses it, and what they can do

**Operator/admin:** inspect traffic, configure a run, choose a supported policy, introduce supported demonstration events and inspect worker-confirmed outcomes. Shared commands require authentication and appropriate control authority.

**Driver participant:** join an assigned vehicle, view the own trip and route, choose whether to share probe data, and accept or decline eligible guidance. A driver cannot choose an arbitrary vehicle or manipulate traffic signals.

**Observer/mentor:** view the scene or a labelled recording without control permissions.

**Researcher/developer:** prepare location packs and reproducible demand, run comparisons, inspect evidence and validate models. This role is distinct from a driver using the app.

An important product distinction is shared simulation state versus local viewing state. Admin commands can change shared physics. Camera zoom, Follow or First person change the viewer's own view and should not change traffic.

## 6. How the system connects

```text
SUMO traffic engine
    controlled by one worker through TraCI
        |
        +-- simulated sensor observations and vehicle frames
        +-- authoritative signal/route actions and saved run records
        |
FastAPI host
    authentication, permissions, sessions and observation validation
    queues commands for the worker
        |
        +-- operator dashboard: shared state and controls
        +-- bound driver client: own frame, route, consent and guidance
        +-- detection/forecast adapters: permitted observation histories
        +-- Results: saved complete matching cohorts
```

**SUMO** is the microscopic traffic simulator. **TraCI** is the interface through which the host reads and controls it. **FastAPI** serves the backend API. **Three.js** renders the operator scene. **React Native/Expo** powers the native companion. **scikit-learn** supplies the gradient-boosting candidate.

Exactly one thread owns TraCI. HTTP or WebSocket handlers validate requests and enqueue commands; they do not directly change SUMO. This prevents multiple clients from issuing conflicting simulator operations independently.

Run IDs, vehicle binding, frame provenance, revision checks, command identifiers and control leases help reject stale, duplicate or unauthorized actions. Simulated time drives traffic and action expiry. Wall-clock time measures connection heartbeat freshness. Those clocks are different.

## 7. Where the traffic and observations come from

The evaluated network uses OSM road geometry with assumed seeded demand. A seed is a reproducible random-generation identifier. Using the same seed and saved demand helps make two policy runs comparable. A different seed can create a different traffic cohort and different outcomes.

The handoff's assumed default fleet proportions are cars 32%, motorcycles 35%, autos 15%, e-rickshaws 8%, buses 4% and delivery vehicles 6%. These are assumptions, not surveyed local fleet shares. Finite generated counts vary with the seed. Benchmark sublane behavior was disabled, so motorcycle filtering and lane-free behavior have not been validated by these results.

Distinguish data sources:

- **Simulated fixed sensors:** SUMO-derived lane measurements used by the pressure benchmark.
- **Consented phone probes:** accepted messages from connected clients relaying their assigned simulated vehicle frames.
- **Emulated probes:** scripted clients or experiment participants, explicitly labelled.
- **Offline truth:** simulator information used for training labels or evaluation, not silently supplied to an online phone-only detector.

Zero accepted phone uplinks means zero phone observations. A disconnected phone is unknown, not evidence of clear traffic. Optional object detection is a separate adapter; detecting a vehicle or person does not automatically diagnose an incident.

## 8. Signal algorithms, in understandable terms

### Fixed timing

Runs the configured signal programme without adaptive interventions. This is the reference comparison. It has not been established as the best possible real-world fixed plan.

### Bounded queue response

Can briefly extend an existing green when a queue exists and downstream space is available. It is a simple reactive rule. Earlier tiny or incomplete demonstrations should not become strong effectiveness claims.

### Actuated comparison

Uses lane presence, a two-second gap criterion, receiving-space checks and green bounds to extend an existing phase. It averaged 0.54% journey reduction on held-out seeds 51/52, with a slight regression on seed 52. This result describes our comparator, not every possible actuated system.

### Original capacity-aware pressure controller

Imagine two approaches. One has a large queue but its exit is nearly full. Another has a smaller queue and room downstream. Serving the first queue without considering its exit may spread the blockage. Pressure scores both upstream demand and downstream load.

```text
phase score = sum over its configured movements:
    saturation flow ×
    (upstream queued vehicles / upstream storage capacity
     − downstream occupied vehicles / downstream storage capacity)
```

Dividing by capacity expresses how full a road is relative to its storage. Saturation flow is an assumed discharge-rate weight. Current worker assumptions estimate storage from lane length divided by 7.5 m and use 0.5 vehicles/s saturation. These values need calibration for mixed traffic.

The controller evaluates eligible phases, checks receiving space, respects minimum green, uses a maximum-green bound, prioritizes sufficiently overdue safe alternatives and applies hysteresis. Hysteresis means a small score fluctuation should not cause constant switching.

Defaults are 10 s minimum green, 60 s nominal maximum green, 120 s maximum red and a 0.1 score hysteresis. The worker normally permits one bounded extension of up to five seconds per phase occurrence. It handles configured yellow/all-red clearance and rechecks a target before applying it. A maximum-red preference cannot guarantee service when the alternative is unsafe.

Signals use local upstream/downstream conditions. This does not establish a corridor-wide optimizer or guaranteed green wave. The benchmark's measured benefit belongs to this original reactive pressure controller.

### Later experimental alternatives

The other-laptop handoff describes flow pressure, which deduplicates incoming lanes and uses an upstream-queue minus downstream-occupancy score, and stopped-queue pressure, which subtracts stopped downstream vehicles while retaining a total-occupancy receiving-space guard.

It also describes approach-speed advice estimating a target approach speed from the next signal and an assumed queue-discharge allowance. These source files were absent from the inspected pushed base. Treat them as handoff-described experiments until their actual source and evidence are inspected. Their results are listed separately below.

## 9. Detection, prediction and control are different jobs

**Detection:** Is congestion present now? The implemented detector requires usable fresh slowdown evidence to persist rather than treating one red-light stop as a jam. Default high slowdown is at least 0.7 for 30 simulated seconds, plus ten seconds of evidence through a serving green after its first five seconds. A fresh fixed source or at least two fresh probes is required. Gaps above 15 s reset persistence. Recovery requires slowdown below 0.3 for 60 s. These are uncalibrated defaults. Insufficient evidence makes the detector unusable for control.

**Forecasting:** What might slowdown be in two, three or five minutes? The candidate pipeline contains persistence, trend and `HistGradientBoostingRegressor` models for 120/180/300 s. Inputs include recent slowdown, rolling means, trend, observation age, contributor count, history coverage and fixed queue ratio where available.

**Control:** Which safe action should the system take? The measured controller reacts to current queue pressure. A forecasting model's existence does not mean it produced those control savings.

Training uses fixed-policy no-action labels and separate whole seeds/runs. Preprocessing fits only on training data; selection uses validation data. Configured default split ranges are training 100–107, validation 200–202 and test 300–304. These configuration ranges are not evidence of a validated real-network dataset.

Next validation must report MAE, meaning average absolute prediction error, and usable coverage at every horizon against persistence and trend. If forecasts trigger alerts, also evaluate false alerts, lead time and event precision/recall. Forecast regression is not automatically a calibrated jam probability. Forecast-assisted control then needs its own matched comparison against reactive control. No useful real-network forecast accuracy or predictive-control improvement has been established by the cited batches.

## 10. How the phone and guidance should work

1. An operator creates a one-use invitation for a server-assigned vehicle.
2. The driver joins using the code/link through the appropriate host.
3. The host binds the session and issues scoped own-vehicle frames.
4. Sharing starts off. The driver explicitly consents before sending probes.
5. The backend validates messages against the issued frame and session.
6. An eligible diversion requires fresh supporting evidence and a reviewed route.
7. The driver accepts or declines. Accepting submits a decision; it is not immediate proof of application.
8. The worker checks and applies a valid action at an eligible decision point, then confirms the result.

A route restriction alert is not the same as automatic rerouting. Current additive driver endpoints expose world geometry, own route, route events and active speed-restriction alerts. They do not establish automatic lane closure or rerouting for every event.

App penetration, consent to share probes, acceptance of guidance and adherence to advice are four different things. The speed-advice experiment collapses participation/acceptance into an emulated binary selection. A requested 30% rate is not a 30% saving, an exact finite-cohort participant count, or proof of real human compliance.

## 11. Results: which percentage means what?

Read a result as: **policy + comparison + traffic cohort + metric + evidence status**. A percentage without those details can mislead.

| Figure | Meaning | Evidence status in this handout |
|---|---|---|
| 0% journey/CO2 | Earlier tiny fixed-versus-bounded example with two vehicles per arm | Old comparison-plumbing example. Superseded as the presentation headline, not disproved |
| 11.31% journey, 7.48% modeled CO2 | Original pressure versus fixed, mean paired reductions on held-out seeds 51/52 | Locally inspected saved evidence. Final PPT headline |
| 0.54% journey | Implemented actuated comparator versus fixed on seeds 51/52 | Same inspected held-out report |
| 12.22% journey, 8.21% modeled CO2 | Original pressure on development seed 42 | Saved development result, excluded from held-out mean |
| 12.04% journey, 8.04% modeled CO2 | Original pressure on fresh seeds 61/62/63 | Other-laptop handoff-reported, not independently inspected local artifacts |
| 10.59% journey, 7.27% modeled CO2 | Experimental flow pressure on seeds 61/62/63 | Handoff-reported experiment |
| 11.87% journey, 8.06% modeled CO2 | Flow plus requested 30% emulated speed-advice participation on seeds 61/62/63 | Handoff-reported experiment |
| 12.93% journey, 8.15% modeled CO2 | Stopped-queue pressure on development seeds 42/43 | Handoff-reported development result, not held-out validation |
| 15.28% journey, 10.44% modeled CO2 | Selected favorable flow-pressure seed 61 case | Handoff-reported single selected case, not a multi-seed mean |

**Why can the PPT say 11.31% while another handoff says 12.04%?** Both refer to original pressure, but they use different seed groups. The final PPT uses the group whose saved evidence was locally inspected. The newer group was reported in an unpushed handoff. Their averages must not be combined casually.

**Why not headline 15.28%?** It is one selected favorable case. The broader reported flow mean is 10.59%. Selecting the best run does not establish general 15–20% performance.

**Why is stopped-queue pressure not the proven winner?** Its reported 12.93% comes from development seeds. Fresh independent held-out validation had not been completed. Development data helps build a policy; test data judges a frozen policy.

### The verified PPT comparison

| Held-out seed | Vehicles per policy | Fixed mean journey | Pressure mean journey | Journey reduction | Fixed modeled CO2 | Pressure modeled CO2 | CO2 reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| 51 | 49 | 291.83 s | 259.67 s | 11.02% | 38.4030 kg | 35.8072 kg | 6.76% |
| 52 | 79 | 329.67 s | 291.43 s | 11.60% | 61.5328 kg | 56.4836 kg | 8.21% |

Each policy completed all 128 scheduled trips across these two seeds. Saved manifests show zero collisions and teleports. The averages use unrounded per-seed reductions: 11.3103% journey and 7.4825% modeled CO2. Round to 11.31% and 7.48%. They are arithmetic means of paired seed percentages, not pooled vehicle-weighted percentages or confidence intervals.

## 12. What the metrics and fair comparison mean

**Journey time:** arrival minus scheduled departure. It includes waiting to enter the network. **Travel time:** time after actual insertion. Ignoring insertion delay could make a congested controller look better by leaving cars outside the network.

```text
reduction (%) = 100 × (fixed metric − response metric) / fixed metric
```

Positive means reduction. Negative means regression. Current dashboard speed is a snapshot of active vehicles and is not the same as whole-cohort journey improvement.

**Modeled CO2:** SUMO supplies an emission rate in mg/s. Integrating over time and converting units produces kg. It is model output, not a field carbon measurement. Fleet/emissions calibration remains unresolved.

**Matched comparison:** same network, generated demand, seed, scenario, settings and execution fingerprint; only the intended treatment differs. Mid-run source/policy/event changes invalidate attribution. A run must complete its whole scheduled cohort with zero collisions and teleports before supporting headline savings. Keep failed and negative cases.

The cited normal benchmark schedules 1,400 vehicles/hour for 180 simulated seconds, then allows up to 900 s of drain. The actual cohort is finite. Drain means departures stop and existing trips get time to finish. It does not delete stuck cars. A rate of 1,400 vehicles/hour does not mean 1,400 vehicles were scheduled in a three-minute run.

XML trip files and lifecycle metrics use a consistent 0.25 s timestamp difference. The PPT uses saved worker lifecycle journey means throughout. Six held-out XML checksums and completion counts were independently checked. CO2 and fault totals were inspected in saved report/manifests. Full recording contents were unavailable locally, so this handout does not claim a complete local replay audit or a new rerun.

## 13. Limitations the team must understand

Two held-out seeds do not prove city-wide effectiveness. The fixed plan is configured rather than proven field-optimal. OSM geometry, assumed demand and mixed classes do not make the simulation field-calibrated.

Improving the average does not guarantee every driver benefits. Development seed 42 pressure increased P95 stopped waiting from 171.95 to 186.08 s. P95 describes the waiting-time level reached by roughly 95% of trips. In held-out seed 51 it improved from 168.05 to 120.60 s, and seed 52 from 253.60 to 171.22 s. Tail waiting and per-approach service need continued evaluation.

Stress seed 53 fixed completed 133/135 trips. Adaptive arms completed 135/135, but the incomplete baseline cannot support a valid percentage saving. A separate long-running Explore session accumulated overload and collision involvements. Finite-cohort success does not establish sustained-overload robustness.

No claim of real GPS road sensing, validated predictive AI, guaranteed green wave, general 15–20% saving, or measured field carbon reduction is supported here. Optional camera work and emergency priority require separate validation.

## 14. Build and integration snapshot

The benchmark evidence and inspected original pressure source come from pushed commit `7733a08b1defe6bf6c90c2e797829fc2fedb2f1e`. The final deck/documents were pushed as `e0ef135` on `feat/kush-final-deck`.

The newer simulation status reports additive driver world/route/events/alerts implemented in local commit `b7f8541`, with 13 focused acceptance tests passing and 24 focused Node tests passing. Its expanded Python run reported 73 passed and one paired-comparison rejection because source changed between the two fingerprints; a stable-source rerun was pending in that snapshot. These are reported focused checks, not a full-suite success claim. Publication and later verification must be checked by a new agent.

The earlier native build report records a standalone preview APK build and emulated adapter checks, but physical installation/visual testing was not completed in that report. This handout does not promote that old report into a current device-success claim. Root final-app status was unavailable in the inspected snapshot. Verify the current native release, actual host, physical devices and latest integration report before presenting them as complete.

The unified driver world includes a registry mapping frozen `edge.lig.N` frame IDs to raw SUMO road IDs. Route and event paths use raw IDs. Code must resolve that mapping rather than assume the IDs are interchangeable. A driver endpoint reveals own state and allowed geometry, not the full fleet/admin state.

Later other-laptop flow, speed-advice and stopped-queue source/artifacts had not been imported into the inspected base. Do not advertise their launcher or replay as available merely because an old handoff names a file path.

## 15. A presentation and demo teammates can explain

The final nine-slide flow is:

1. Traffix and LIG Square.
2. Changing demand, mixed vehicles and blocked exits.
3. Connected observation, response and comparison.
4. One authoritative host and connected clients.
5. Implemented pressure controller.
6. Detection and forecast-validation plan.
7. Verified held-out results.
8. Operator and driver walkthrough.
9. Integration and validation roadmap.

The first five slides retain generated concept illustrations. They are not photographs of a deployment. The operator image is a saved UI screenshot, not the benchmark cohort. The PPT's Results table and newer text slides are editable. The PDF is a flattened version for stable viewing.

For a demo, show an admin selecting a supported policy, a new worker-confirmed action, bound driver identity and explicit consent, and a saved pressure seed 51 or 52 against its matching fixed baseline. Label playback recorded. Demonstrating a control during Explore is useful for understanding the UI, but it is not a fresh fair performance comparison. If a host is disconnected or stale, retained car positions do not prove the run completed.

### A short spoken explanation

“Traffix helps us test congestion responses before making effectiveness claims. We built a local traffic simulation around LIG Square, connected an operator dashboard and a driver companion, and implemented a pressure controller that considers both waiting queues and downstream space. Across two held-out matched simulation seed pairs, it reduced mean journey time by 11.31% and modeled CO2 by 7.48%. Every scheduled trip completed. Our next gates are physical-device integration, stronger overload and fairness testing, forecasting validation, and field calibration.”

## 16. Likely questions and honest answers

**What makes this different?** The integrated experiment links operator control, mixed-traffic simulation, scoped driver participation and auditable comparisons through shared vehicle identity. This is our product approach, not a claim that competitors lack similar features.

**Where is the AI?** Gradient-boosting forecast candidates exist. The measured pressure controller is a reactive heuristic. A useful model needs validation before forecast-assisted control.

**Why use simulation?** It creates reproducible demand and lets us compare responses while recording faults and unfinished trips. It also has assumptions that require field calibration.

**Does the phone measure my GPS?** The described demo relays the assigned simulated vehicle's observations. Field GPS sensing is not demonstrated by this evidence.

**How do you avoid serving a blocked road?** Receiving-space checks constrain eligible phases and the worker rechecks the target after clearance. These protections do not prove universal collision or overload safety.

**Did you reduce pollution by 7.48%?** We reduced SUMO modeled CO2 by that mean paired percentage in the cited two-seed simulation comparison. No field emissions reduction is established.

**Why not use the highest percentage?** Different policies and seed groups have different evidence. A favorable selected run does not replace the held-out multi-seed headline.

**What happens when data disappears?** Unknown stays unknown; unusable observations do not authorize confident decisions. The system must expose freshness and fallbacks.

**What is next?** Verify native devices against the shared host, broaden independent matched testing, study tail fairness and sustained overload, validate forecasts and calibrate with observed traffic data.

## 17. New coding agent onboarding

Do not infer the installed state from this portable document. Inspect the actual checkout, branch, uncommitted changes, `AGENTS.md`, `OWNERS.md`, relevant contracts and current integration reports first. Old product requirements describe targets and must not override newer verified implementation evidence.

Module map:

- `backend/simulation/`: unified host, authoritative worker, policies, driver adapters and Results.
- `backend/harness/`: existing LIG adapters/demonstrations.
- `web/src/operator/` and `web/src/shared/`: unified dashboard and shared presentation/protocol helpers.
- `mobile-app/`: native companion.
- `ml/`, `eval/`, `models/`: permitted observations, detection, forecast candidates and evaluation.
- `sim/`: original simulation assets; location preparation requires topology review.
- `contracts/`: frozen v1 schemas and additive versioned contracts.
- `scripts/`, `tests/`, `artifacts/`, `docs/`: launchers, acceptance checks, saved evidence and specifications.

Team scope at this snapshot: Kush coordinates native/mobile and integration; Prakhyat owns the unified simulation/operator and ML work under the approved scope; Nandani owns original simulation assets; Urvashi owns other web work unless a newer scoped assignment overrides it. Inspect current ownership before editing.

Preserve these invariants: one TraCI owner; server-bound vehicle identity; explicit consent; scoped authentication; worker-confirmed actions; freshness and unknown handling; separate simulation/wall clocks; frozen v1 compatibility; source-labelled emulation; no fixture-trained live-control claims; no invented results; preserve incomplete/faulted evidence. Avoid changing unrelated teammates' modules or silently staging private account/runtime files. Do not expose TraCI or an admin bootstrap publicly.

For evidence, find the manifests and source version before reproducing a claim. Use new output filenames so reruns cannot overwrite original evidence. Establish a frozen matched comparison and ownership authorization before starting experiments. Do not tune on test seeds and continue calling them held-out.

## 18. Source and artifact map

Repository: `https://github.com/makekush7-netizen/Traffix-/`.

Final presentation branch: `feat/kush-final-deck`. Files: `presentation-output/final/Traffix-Final.pptx` and `Traffix-Final.pdf`. Companion notes: `docs/final-algorithm-answers.md`, `final-presenter-guide.md`, `final-submission-summary.md`, `final-deck-status.md` and `final-deck-evidence-verification.json`.

Verified benchmark source branch: `feat/prakhyat-unified-simulation`, evidence commit `7733a08`. Saved sources: `artifacts/ppt-benchmark-heldout/report.json`, `artifacts/ppt-benchmark-evidence/heldout-normal.json`, checksum list and held-out trip XML, plus development/stress reports. Explanations: `docs/ppt-improvement-report.md`, `docs/prakhyat-build-return.md`, `backend/simulation/policies.py`, relevant worker code and inspected `ml/` code.

Latest inspected integration source: `prakhyat-review/docs/final-sim-status.md` in the shared workspace. Earlier native snapshot: `docs/native-mobile-build.md`. Product target: `docs/traffix-harness-prd-v1.md`, explicitly a requirements baseline, not a completed-feature list.

Later experimental numbers: root `Traffix-complete-agent-handoff.md`, explicitly local/unpushed at its creation. This handout carries its numbers for reconciliation, not as independently verified artifacts. A receiving AI should request actual newer evidence before upgrading those claims.

This handout deliberately contains enough explanation to teach the whole project without repository access. Repository access is still required to establish current implementation or make code changes.
