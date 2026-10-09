# Nandani's SUMO handoff: 9 October 2026

**Verdict: runnable on this Windows machine; not ready for the connected-phone demo or evaluation freeze.**

Source tested: `origin/feat/nandani-sim`, commit `5e7b35e`. Nandani's simulation source and tests were not edited. SUMO, TraCI and sumolib **1.28.0** were installed in the repository virtual environment, matching the registry/network version.

## What passed

- Entire supplied test suite: **37 passed**, one FastAPI TestClient dependency deprecation warning.
- Environment check: SUMO 1.28.0 executable and TraCI available. The checker now recognizes the project-local wheel installation without requiring a global PATH change.
- Full seed-42 no-incident run and supplied rain-plus-obstruction run both exited successfully at the requested 2400-second horizon.
- Both runs report **413 loaded/inserted/arrived vehicles**, zero running/waiting at the last summary, zero collisions, zero teleports and zero discarded vehicles.
- Registry edge/junction/signal IDs resolve. Main and bypass route connections and detector lanes resolve. The market detector is marked truth-only and excluded from the declared operational sensor list.
- Read-only QA telemetry confirms an incident queue through green: maximum market halted count **57**, and **54** during downstream market green. At sampled times 860–895, at least 17 market vehicles remained halted throughout the sampled green; at 950–985, at least 21. The seed-42 incident cohort finished arriving by second **1161**.

This establishes a useful seed-42 baseline-jams smoke result. It does not establish response improvement, repeatability across held-out seeds, correct India calibration, or the result after correcting vehicle types.

## Fixes required

1. **Phone roles leave before the reveal.** In both runs, `veh.role.rider` arrives at **111** and `veh.role.auto` at **174**; rain starts at **300**. Both are absent at rain onset. Reschedule the roles so two real phone vehicles occupy the market during the reveal, and delivery remains upstream long enough for a real accept. Test the actual role timeline, rather than checking only that IDs exist.

2. **The background mix is not the configured mixed fleet.** The distribution's child `<vType>` elements use `type="bg_moto"` / `type="bg_auto"`, which does not inherit those definitions. TraCI reports `mix_moto`, `mix_auto` and `mix_car` as `passenger`, length **5.0 m**, width **1.8 m**. The incident trips contain 125 `mix_moto`, 96 `mix_auto` and 189 `mix_car`, all using these default passenger specifications. Use `refId` or a distribution referencing the existing types with `vTypes` and `probabilities`, then verify the effective types through TraCI. See [SUMO vehicle type definitions](https://eclipse.dev/sumo/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html). Re-run the jam gate after this correction; it changes capacity and behavior.

3. **Demand duplicates and ordering warnings.** Each role vehicle is declared once in the main demand file and again in `roles.rou.xml`. SUMO currently ignores the first copies because they follow flows beginning at second 600; warnings explicitly say the route file should be sorted and the roles are ignored. The second file happens to rescue the role vehicles. Keep one declaration per role, with proper departure ordering, and make unexpected loader warnings fail validation.

4. **Obstruction timing and actor conflict.** The manifest declares a second-300 obstruction, but the runner schedules the delivery stop at **241** while it is still on `in`. The first sampled stopped state occurs at **280**, before rain; the last at **675**. Also, the phone delivery vehicle is the obstruction actor. Diverting that vehicle could remove/change the incident itself. Use a separate incident vehicle or another independently scheduled obstruction, and log actual apply/release times consistently across policies. Do not mark a failed stop request as successfully applied.

5. **Scenario contract mismatch.** `sim/scenarios/rain_ramp.json` fails `contracts/scenario.schema.json` with **25 validation errors**, including missing required fields and unexpected properties. Align the scenario with the shared contract; flag genuine schema omissions to Kush. Do not silently maintain a separate scenario contract.

6. **Traffic handedness.** The generated network has no `lefthand="true"`, and its netconvert provenance contains no `--lefthand`. This is the default right-hand build despite the source comments. Rebuild with `--lefthand`, inspect turns, and regenerate the registry/geometry if IDs or shapes change. [SUMO's netconvert documentation](https://github.com/eclipse-sumo/sumo/blob/main/docs/web/docs/netconvert.md) specifies this option for left-hand networks.

7. **Signal/controller bounds need alignment.** J1's fixed green is **82 s** and J4's greens are **42 s**; the scenario's controller maximum is **40 s**. These plans do not match the current control guard assumptions. Agree the phase plans and bounds before integrating responses, preserving every clearance phase and keeping policy comparisons consistent. Do not shorten arbitrary phases during an active run.

8. **Incomplete runs are incorrectly marked complete.** A supplied no-incident run truncated at **60 s** exits zero and receives `complete: true` despite unfinished/future scheduled journeys. The runner equates process success with cohort completion. Save final scheduled/departed/arrived/pending/active/removed/teleported counts and unfinished trip output; mark a run complete only when the cohort criteria pass. The incident runner also invents one halted vehicle when the network is empty because it substitutes speeds `[0]`.

9. **Evaluation/recording provenance is unfinished.** The supplied manifests lack network/demand/scenario/sensor-mask checksums. The baseline runner's reactive/predictive argument changes only the label, not behavior. The incident runner does not collect its detector outputs into its run folder. Freeze an explicit cohort with assigned IDs/types/departures, isolate every run's detector outputs, and do not treat policy labels as applied policies.

The current topology is a minimal directed corridor with two signalized junctions and two priority midpoints; cross traffic and the other supporting scenario presets are absent. This is acceptable as an explicitly documented intermediate handoff, not the full planned network/scenario set.

## Reproduce

```powershell
.venv\Scripts\python.exe -m pip install -r backend/sumo-requirements.txt
.venv\Scripts\python.exe scripts/check_env.py
.venv\Scripts\python.exe scripts/verify_nandani.py
.venv\Scripts\python.exe scripts/trace_sim_handoff.py
```

The verification script returns **1** when static integration defects are present, even if SUMO and pytest return 0. Generated outputs are ignored by Git. It does not alter the simulation source. Telemetry is labelled **SIMULATION TRUTH — QA ONLY** and is never passed to the phone gateway, detection or forecasting.

Saved local evidence:

- `runs/verify.nandani.20261009T023217Z/report.json`: static audit, exact simulation input hashes, test and process results.
- `runs/verify.nandani.20261009T023217Z/`: environment, pytest and runner stdout/stderr.
- `runs/run.bazaar.seed042.fixed.20261009T080226/`: full no-incident outputs.
- `runs/run.bazaar.seed042.incident.20261009T080230/`: supplied incident outputs.
- `runs/run.bazaar.seed042.incident.20261009T080241/output/qa_summary.json` and `qa_truth_telemetry.csv`: concrete type inspection, role presence, stop timing and market queue through green.
- `runs/run.bazaar.seed042.fixed.20261009T080343/`: truncated run demonstrating the incorrect completion flag.

## Message for Nandani

Kush tested commit 5e7b35e on SUMO 1.28.0. All 37 tests pass, and seed 42 clears with/without the incident, but the demo has blockers. Please first fix role timing (rider/auto already arrived at 111/174 before rain at 300), the mixed-fleet distribution (mix_moto and mix_auto load as 5 m passenger cars), duplicate/unsorted role definitions, and the delivery-as-obstruction timing/actor conflict. Then align the scenario JSON with contracts, rebuild for left-hand traffic, align signal bounds, and correct incomplete-run accounting/provenance. Add acceptance tests for these behaviors, rerun the baseline-jams gate, and push a new commit. Please use a separate obstruction actor so a real delivery acceptance cannot change the exogenous incident.
