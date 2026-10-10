# Traffix algorithm and evidence answers

Prepared 10 October 2026. The inspected simulation source and benchmark artifacts are from pushed commit `7733a08b1defe6bf6c90c2e797829fc2fedb2f1e` in `../prakhyat-review`. The separate complete-agent handoff describes later unpushed work on another laptop. Do not present that work as installed or independently reproduced here.

## How do signals choose a phase?

The implemented controller is a reactive capacity-aware pressure heuristic. For each configured movement it computes:

```text
phase score = sum(saturation * (upstream queue / upstream capacity
                               - downstream occupancy / downstream capacity))
```

`backend/simulation/policies.py` chooses among legal phases with receiving space. It keeps a minimum green, prioritizes overdue safe alternatives, enforces a maximum green, and uses score hysteresis to avoid unnecessary switches. Defaults: 10 s minimum green, 60 s nominal maximum green, 120 s maximum red and hysteresis 0.1. These are uncalibrated assumptions. The worker estimates storage as lane length / 7.5 m and saturation as 0.5 vehicles/s. Mixed-vehicle calibration remains a limitation.

The single TraCI worker validates a transition, applies configured yellow/all-red clearance and checks receiving space again before serving the target. An unsafe or stale observation triggers fallback. The worker permits one bounded extension of up to five seconds per phase occurrence, so the nominal 60 s bound does not imply arbitrary repeated holding. Maximum-red priority applies only where safe and is not a guaranteed wait-time bound. Multiple signals use local movement conditions. No validated corridor optimizer or guaranteed green wave exists.

The benchmark inputs are simulated installed lane sensors. It does not demonstrate phone-only signal control. Pressure is a heuristic from an established algorithm family, not a trained neural model, reinforcement learning or an optimality proof.

## How does detection distinguish congestion from a red-light stop?

`ml/detect.py` maintains per-edge slowdown persistence. Defaults require slowdown at least 0.7 for 30 simulated seconds plus ten seconds of continued evidence during a serving green after its first five seconds. A fresh fixed observation or at least two fresh probes makes evidence usable. Gaps above 15 s reset persistence. Missing or stale evidence is unusable, even if the historical active flag remains set. Recovery requires slowdown below 0.3 for 60 s. These thresholds need calibration. Persistent slowdown detects a traffic condition, not its cause. Object detection alone cannot establish a crash or rally.

## What is the forecasting plan, and what already exists?

The candidate pipeline already implements persistence, trend and `HistGradientBoostingRegressor` forecasts at 120/180/300 s. `ml/features.py` allows current slowdown, 30/60/120 s rolling means, a 60 s slope, contributor count, sample age, fixed queue ratio, history span and fresh fraction. Inputs use causal permitted observations. Future simulator truth supplies offline labels only.

`ml/train.py` requires fixed-policy no-action labels. It separates whole seeds/runs, fits preprocessing on training data and selects against validation only. Default seed sets are training 100–107, validation 200–202 and test 300–304. These configured ranges do not establish that a real-network dataset has been collected or validated. Fixture-trained performance does not establish field accuracy. Coverage and freshness gates keep unknown input from authorizing control.

Next gate: collect representative runs, freeze the model using development/validation data, and report test MAE and usable coverage separately for every horizon against persistence and trend. If converting regression to alerts, report precision/recall, lead time and false alerts per hour. A slowdown regression is not a calibrated jam probability. Then compare a frozen forecast-assisted policy with the reactive policy on matched gradual-demand scenarios. Current measured savings establish reactive control only.

## How should the best policy be selected?

Select and tune on development seeds, freeze parameters, then evaluate on fresh held-out runs. Each arm must share network, generated demand, seed, scenario, simulation settings and execution fingerprint. Keep fixed timing and a simple actuated baseline. Retain negative and incomplete outcomes. Require every scheduled vehicle to arrive with zero collisions and teleports before reporting paired percentage savings. Do not select a policy from its single most favorable demonstration.

Locally inspected held-out seeds 51/52 favor original pressure over the implemented actuated comparator: 11.31% versus 0.54% average journey reduction. The fixed plan is configured, not proven field-optimal. Two seeds are a small sample without a general-performance guarantee.

The source handoff alone reports later seeds 61/62/63: original pressure 12.04% journey / 8.04% modeled CO2, flow 10.59% / 7.27%, and flow plus requested 30% speed-advice participation 11.87% / 8.06%. A selected flow seed 61 is 15.28%. Stopped-queue pressure reports 12.93% / 8.15% on development seeds 42/43 only. These later source files and artifacts were absent from the inspected base. They are handoff-reported results, excluded from our presentation headline. Do not combine means from different cohorts, add signal/advice percentages, or describe a selected case as a general 15–20% result.

## What do Results and CO2 mean?

Journey is arrival time minus scheduled departure, including insertion delay. Travel time starts at actual insertion. Reduction is `100 * (fixed - response) / fixed`. Positive means improvement. The headline averages paired per-seed percentage reductions equally, not by pooled vehicle weighting. Dashboard instantaneous speeds are not the journey metric. Aggregate effective speed, if used, is total route distance divided by total journey time, converted to km/h.

CO2 integrates SUMO mg/s output over simulation steps and converts to kg. It is modeled fleet output, not measured carbon. Geometry, demand, vehicle mix and emissions mapping are not field-calibrated. The benchmark uses 1,400 veh/h departures for 180 s followed by up to 900 s of drain. Drain allows the same finite cohort to finish after arrivals stop, without deleting vehicles. This does not establish sustained peak-hour robustness.

Held-out results: seed 51 fixed/pressure mean journey 291.83/259.67 s, reductions 11.02% journey and 6.76% modeled CO2. Seed52 329.67/291.43 s, reductions 11.60% and 8.21%. Each policy completes 49 + 79 = 128 vehicles, zero collisions/teleports in saved manifests. Mean reductions are 11.31% and 7.48%. Six trip XML checksums and completion counts were independently checked locally. XML duration plus insertion delay is consistently 0.25 s below lifecycle-event journey means, consistent with the worker's simulation-step timestamp convention. The slide uses the saved lifecycle metric consistently.

Fairness needs P95 stopped waiting and per-approach service alongside the average. Development seed 42 pressure increased P95 stopped waiting from 171.95 to 186.08 s. Held-out seed 51 improved 168.05 to 120.60 s and seed 52 improved 253.60 to 171.22 s. No claim that every driver benefits. Stress seed 53 fixed completed 133/135, so comparative percentage savings are withheld. The separate long-running Explore session had overload/collision problems and does not support the finite-cohort headline.

## Evidence and demo boundaries

Sources: `../prakhyat-review/artifacts/ppt-benchmark-heldout/report.json`, `../prakhyat-review/artifacts/ppt-benchmark-evidence/heldout-normal.json`, trip XML and checksum list, `docs/ppt-improvement-report.md`, `backend/simulation/policies.py`, `engine.py`, and inspected `ml/` code. No new simulations ran for this deck. Full recording contents were not available locally; saved recording checksums are not equivalent to inspecting replay content. Recorded playback must say recorded.

Show admin policy selection, a worker-confirmed action, bound phone identity and explicit consent, then a saved pressure run against its same-seed fixed baseline. Connected phones relay simulated observations, not field GPS. Native integration and physical multi-device success must follow the latest integration status, not an architecture illustration. The Vercel submission frontend is separate from the local SUMO host.
