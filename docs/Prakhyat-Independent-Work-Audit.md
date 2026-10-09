# Prakhyat: independent-work audit

**Date:** 9 October 2026  
**Project:** `C:\Users\prakh\Desktop\Traffix`  
**Scope:** Prakhyat's ML, data and evaluation responsibilities in the connected-phone build plan. The planning documents were used as requirements, not as instructions to fabricate results or modify teammates' modules.

## Verdict

**It was not all complete or correct at the start of this audit.** The original 64 passing tests missed important faults in feature consistency, normal-red handling and paired metric integrity. Two-demand training planning, cross-mask sensor ablation, event metrics and network/action metrics were incomplete.

Those independent software gaps are now repaired or implemented. The current suite has **101 passing tests**, the complete fixture pipeline runs, and the command-line file workflows pass. This supports a verdict of **ready for the team handoff**, not a claim of a validated traffic system.

**Real training, calibration, controller-benefit experiments and final result slides remain unfinished.** They need actual simulation exports. Live phone integration also needs the coordinator's gateway and runner; that dependency is separate from Nandani. No real SUMO traffic improvement, CO2 reduction, forecast accuracy or physical-phone coverage result has been produced.

## Task-by-task status

| Prakhyat responsibility | Independent deliverable | Current status | What remains / who supplies it |
|---|---|---|---|
| Hand-calculated metric fixtures | Entry delay, detours, pending/active/removed trips, emissions units and bad records covered | Done; tested | Check real output against the fixtures after Nandani's first run |
| Feature allowlist and leakage audit | Causal per-edge features; privileged inputs excluded; matching live/offline history | Done; tested/documented | Verify the actual runner sends only permitted observations |
| Probe/fixed observation aggregation | Latest sample per vehicle; no hidden-state gap filling; allowlisted fixed sensors; missing/stale evidence | Done; tested | Coordinator's authenticated, vehicle-bound, frame-validated phone gateway |
| Jam detection | Persistence, recovery, freshness and continuing green-evidence guards | Done as configurable software | Nandani's normal-red/incident traces for calibration |
| No-action baseline gate | Separate sustained jam episodes, green evidence and later recovery | Done as offline checker | Genuine normal-flow and incident runs; H6 gate is not yet passed |
| Batch data pipeline | Job plans, serial runner invocation, export validation, manifest enrichment and causal labels | Done; tested | Frozen network/demand/incident files plus coordinator's runner |
| ML forecasting | Persistence, matching trend baseline, 120/180/300-second gradient boosting, whole-seed splits | Done on fixtures | Real fixed-policy logs; fixture models cannot authorize control |
| Model artifact integrity | Feature/version/horizon/policy/provenance/checksum checks; invalid predictions unavailable | Done; tested | Fit and freeze genuine models after data arrives |
| Reactive/predictive first-response rules | Starting settings, signal/freshness guards, forecasts disabled after intervention | Done; tested | Coordinator applies bounded commands; validation decides settings |
| Validation-only tuning | Threshold screening, independent event matching, missed events and false alerts/hour | Done; tested | Actual validation observations/truth and controlled outcome runs |
| Whole-cohort journey and CO2 | Raw trips/lifecycle import, scheduled-cohort size, exclusions and teleport checks | Done; tested | Nandani's actual fleet emission assumptions and complete exports |
| Held-out forecast/detection scoring | Per-method/horizon/seed scores, coverage, missing positives, event rates and lead/delay | Done; tested | Unseen real seed runs and independently defined jam labels |
| Fixed/reactive/predictive comparison | Frozen inputs, actual metric cohort, missing-seed denominator, losses preserved | Done; tested | Actual three-policy runs from coordinator's controller/runner |
| Sensor-gap ablation | Same-policy comparison across boundary-only vs phone-probe masks | Done; tested | Coordinator resolves masks/participation; genuine matched runs |
| Compliance study | Distinct seeded jobs for 0/.2/.6 compliance | Planning/reporting infrastructure done | Optional real rain runs; cut this before core evaluation |
| Queue/bypass/action evidence | Time-weighted queue burden, peaks/coverage, deduplicated applied action counts | Done; tested | Stable truth edge set, declared bypass edges and authoritative event logs |
| Report and evidence handoff | Run report, plots, machine-readable outputs, guide and evidence-card template | Done as templates/fixture exercise | Final numbers and Urvashi's slide/visual integration |
| Help Nandani's first run | Readiness checker, exact file handoffs and baseline acceptance command | Done independently | SUMO installation and valid simulation assets |

## Important defects found and repaired

| Defect before repair | Why it mattered | Repair / regression evidence |
|---|---|---|
| Live history feature could span 400 seconds while training used roughly 120 | Model input changed between training and deployment | Common retained 120-second feature window; equality regression |
| Long red queue could trigger immediately after green began | Ordinary signal waiting looked like persistent congestion | Continuing qualifying green evidence; discharge and predictive guard regressions |
| Trend predicted a single endpoint while ML labels averaged a future window | Baseline/model comparison used different targets | Both target the same 30-second window ending at each horizon |
| Fractional CSV probe counts silently became integers | Invalid evidence could satisfy control eligibility | Strict integer parsing; malformed-input regression |
| New phone sample freshened an older selected fixed reading | Reported speed and age referred to different evidence | Age follows the chosen fixed-speed reading |
| Invalid runtime configuration consumed the clock/history before failing | Corrected retry could corrupt or reject the next tick | Prevalidate methods/phase context before mutation |
| Partial or contradictory provenance was accepted | Fixture/test/policy data could contaminate model or tuning claims | Training/evaluation/label/tuning cross-plane checks |
| Original 48-job plan meant one demand level across all seed partitions | It did not implement the approved training experiment | Separate 48 train / 18 validation plans at two demands |
| Merge omitted manifest demand level | High/reference records could lose their identity | Enrich and validate `demand_id` in both planes |
| Different excluded trips could manufacture a positive paired result | Same demand hash did not guarantee the same metric population | Derive actual metric/exclusion hashes from raw trips; reject mismatches |
| Shared control/probe/emissions assumptions were not paired | Policies could differ in inputs beyond the intended intervention | Frozen configuration/probe/emission fingerprints; missing evidence suppresses gains |
| Standard textual SUMO removal/end markers and `vType` were mishandled | Unfinished/removed trips or fleet types could be miscounted | Source-checked parser behavior plus representative XML tests |
| Missing teleport evidence appeared as zero in real-run report | An invalid cohort could receive a headline | Real-run journey/CO2 headlines suppressed without teleport evidence |
| False early warning could hide a later missed jam | Tuning could reward a controller that never detected the real event | Independent event matching counts both the false alert and the miss |
| Jam gate bridged distinct episodes or used one green sample | Weak baseline could be presented as a sustained jam | Episodes scored separately; continuing green evidence required |
| Queue rows with no timestamp appeared as complete coverage | Untimed evidence was silently discarded | Reject missing clocks; missing queue values remain unavailable |
| No cross-mask comparator / event-rate / network-action summaries | Required proof could not be generated from exports | New ablation, event and network modules with missing-evidence guards |
| Demand groups were indistinguishable in Markdown | Reports could mix interpretations of separate workloads | Demand column included |
| Nonfinite model output was clipped to a usable value | A broken predictor could authorize control | Return unavailable instead |
| Fixture runtime re-inserted old aggregated samples as new uplinks | Smoke data made freshness look better than it was | Re-ingest only genuinely current fixture readings |

The independent reviewer reproduced the original exclusion bias and confirmed the repair rejects it. Their follow-up identified three additional issues in tuning metadata, queue timestamps and demand display; all three now have failing-before/passing-after regressions. This is code and fixture verification, not external validation of SUMO behavior or the final demo.

## Verification and reproducibility

Run from the project folder with its Python 3.12 virtual environment:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_prakhyat.ps1 -Mode all
& .\.venv\Scripts\python.exe scripts/verify_prakhyat_cli.py
& .\.venv\Scripts\python.exe scripts/build_experiment_plans.py
& .\.venv\Scripts\python.exe -m compileall -q ml eval scripts tests
& .\.venv\Scripts\python.exe scripts/doctor.py --output artifacts/prakhyat-preflight.json
```

| Check | Observed result |
|---|---|
| Automated suite after final code fixes | **101 passed** |
| Full fixture pipeline | Completed; 2,896 artificial observation/dataset rows; three fixture models; forecast/detection/tuning/report outputs |
| File/CLI boundaries | Passed: generate dataset, train, forecasts, tune, detection, collect, compare, ablation, network, report, merge |
| Honest incomplete-cohort reporting | Policy and sensor-ablation gains remain unavailable in the CLI smoke exercise |
| Experiment-plan generation | Correct counts and unique IDs within each plan; no SUMO jobs executed |
| Compilation | Passed for ML/evaluation/scripts/tests |
| Source scan | No TODO or NotImplemented stubs in ML/evaluation modules |
| Real-run readiness | **Not ready:** no detected SUMO binary, no importable TraCI client, and required scenario assets absent |

CLI logs and `verification.json` are saved under a new `.cache/cli-audit/<id>/` directory. They are fixture evidence. `artifacts/fixture-demo/summary.json` explicitly reports `traffic_improvement: null`. Never put fixture MAE, lead time or modelled trip values into the pitch as traffic results.

## Frozen experiment plans now available

| File in `artifacts/` | Planned jobs | Configuration |
|---|---:|---|
| `training-plan.json` | 48 | Three scenarios × two demand levels × eight training seeds; fixed policy |
| `validation-plan.json` | 18 | Same scenarios/demands × three validation seeds; fixed policy |
| `forecast-test-plan.json` | 15 | Three scenarios × five test seeds; fixed/reference demand |
| `policy-plan.json` | 45 | Three scenarios × five test seeds × three policies; reference demand |
| `sensor-ablation-plan.json` | 10 | Rain/predictive × five seeds × two masks |
| `compliance-plan.json` | 30 | Optional rain × five seeds × reactive/predictive × three compliance values |

Overlapping jobs deliberately share IDs and should be reused, not counted as additional unique executions. Demand and mask names are planned identifiers; the runner must map them to actual frozen assets. Demo seed 42 is excluded from fitting/tuning/testing.

## What happens next, in order

1. **Nandani:** deliver a working `.sumocfg`, network, explicit scheduled demand and actual ID/reference-speed registry. The readiness tool currently confirms these are missing.
2. **Coordinator:** deliver the serial batch-runner interface, fixed sensor masks and labelled probe replay schedule. Build the authenticated physical-phone gateway and single TraCI worker for the live demo separately.
3. **Nandani + Prakhyat:** inspect ordinary signal queues and run the genuine H6 incident baseline through `eval.jam_gate`; it must jam through service and later recover. Calibrate the initial 10-second green evidence rule and other thresholds before freezing them.
4. **Prakhyat:** execute fixed training/validation plans, fit real models, evaluate all horizons against persistence/trend, screen validation thresholds and compare validation controller outcomes. Freeze the chosen configuration.
5. **Coordinator + Prakhyat:** execute unseen three-policy runs with matched demand/cohort/incident/configuration/participation. Preserve invalid and unfinished runs. Run the mandatory sensor ablation if the core runner is stable.
6. **Prakhyat + Urvashi:** replace every unavailable evidence-card field with saved real results, including negative outcomes and denominators. If predictive control does not beat reactive control, say so.

There is no further Nandani-independent ML algorithm feature required before this handoff. Remaining setup/integration work is not exclusively Nandani's responsibility, and fixture success does not close those gates. The final system will still need cold-start, real-phone, controller-bound and replay rehearsals owned by the team.

## Sources and limits

The [SUMO TripInfo documentation](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html) documents trip output and emission units. The [SUMO TripInfo source](https://github.com/eclipse-sumo/sumo/blob/main/src/microsim/devices/MSDevice_Tripinfo.cpp) was checked for `vType` and textual `vaporized` markers. Parser fixtures do not replace testing the installed SUMO version's actual export.

All congestion/phase thresholds remain unvalidated starting settings. Real-phone sampling quality, baseline congestion, useful prediction horizon, controller improvement, two-wheeler stability and India fleet emission proxies remain unverified. The feature model does not include spatial upstream interactions; its simple scope is intentional until it has actual evidence.
