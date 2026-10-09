# Prakhyat's work: LIG Square harness and genuine SUMO-trained ML

Kush requests this handoff for **Traffix**. The branch is
`feat/prakhyat-lig-handoff` in https://github.com/makekush7-netizen/Traffix- .
It combines the coordinator's working backend and LIG Square harness with
Prakhyat's ML foundation from commit `d2202bda5c1ef633a08395252789be766a2f6c22`.
The unrelated deletions from the ML branch were not imported. Its contract
test was added as `tests/test_ml_contracts.py` to retain the existing tests.
Its ML-only `pyproject.toml` was not imported; use the combined environment below.
The combined `pytest.ini` collects only `tests/`, excluding generated runs and
temporary review copies. The fixture launcher initializes SUMO's binary path
and writes generated fixtures under ignored `runs/prakhyat-fixture-demo/`.

## Pull and launch

From your existing repository:

```powershell
git fetch origin
git switch -c feat/prakhyat-lig-work --track origin/feat/prakhyat-lig-handoff
```

Use your existing Python 3.12 environment, or create a fresh one. Virtual
environments and ignored `runs/` files do not transfer through Git.

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r ml/requirements-training.txt
.venv/Scripts/python.exe scripts/check_env.py
.venv/Scripts/python.exe -m uvicorn backend.harness.app:app --host 127.0.0.1 --port 8001 --workers 1
```

Open http://localhost:8001. The OSM extract, derived network/buildings and
Three.js assets are checked in: runtime map downloads are unnecessary. The
phone fixture backend remains at `backend.app:app`, normally on port 8000.

For tests, initialize the packaged SUMO binary path in the same process:

```powershell
.venv/Scripts/python.exe -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q']))"
```

Do not replace the coordinator environment's requirements with the ML lockfile
alone. `ml/requirements-training.txt` combines both sets and SUMO 1.28.0.
Supplied fixture artifacts were saved with scikit-learn 1.9.1; exact version
checks remain enabled. Rebuild artifacts in the chosen environment if needed.

## Verified handoff baseline

The combined source passed **142 tests**, including from a fresh export of the
exact tracked files with no copied virtual environment or cached run data.
The full fixture pipeline also ran from that fresh source. These checks used
Kush's existing Python 3.11/scikit-learn 1.9.0 environment; the documented
Python 3.12 lockfile is Prakhyat's supplied environment, not a new installation
validated on Kush's machine. The remaining correctness findings below still
need new regression tests and fixes; passing the existing suite does not
resolve them. No genuine LIG ML training or valid policy improvement is claimed.

## Read this context first

1. `AGENTS.md`, `OWNERS.md`, the observation/forecast definitions and examples
   in `contracts/`.
2. `docs/lig-harness.md` and `docs/lig-validation.md`.
3. `docs/prakhyat-ml-review.md`, then the relevant implementation details in
   `docs/Prakhyat-Implementation-and-Handoff.md` and the feature audit.
4. Only the applicable module sections of `docs/astra-build-plan.md`: modules
   9, 11, 12, 13 and 17. Do one bounded task at a time.

Kush authorizes changes to the ML/evaluation paths, their tests and the existing
LIG harness/batch/export paths identified in `AGENTS.md`. Preserve other teams'
modules and contracts. Keep the browser harness working throughout this work.

## Current state: treat these as starting points

- LIG Square, Indore, is centered at 22.73360 N, 75.89011 E. Real OSM street
  geometry/building footprints, stylized 3D vehicles and actual SUMO motion.
- Six explicit types: car, motorcycle, auto, e-rickshaw, bus and delivery van.
  Left-hand traffic and sublane movement are enabled. Rule violations and
  fully lane-independent Indian traffic are not yet modeled or calibrated.
- Presets: everyday, rush, rain and roadworks. Rain/obstruction are speed
  restriction surrogates; their current timings are 60–360 simulated seconds.
  The visual server starts paused after a 120-second warmup. Demand ends at
  900 seconds and the current horizon is 1200 seconds.
- An explicit join fixes extremely short external links at LIG Square.
  Remaining junction collisions and unfinished journeys still occur.
  Four seed-42 runs reached the horizon; **all were incomplete and had faults**.
  The checked-in validation document records the results. Raw runs are ignored
  locally; rerun `scripts/check_lig.py` to reproduce them on your machine.
- Prakhyat's 101 provided tests and the complete fixture pipeline passed in
  the coordinator's existing environment. Fixture models correctly cannot
  authorize live control. Genuine SUMO training and A/B/C experiments remain.
- Original experiment-plan JSON uses the older corridor's scenario/mask IDs.
  Resolve or replace those plans explicitly for LIG; do not silently call a
  LIG speed restriction a validated market blockage or procession.

## Task 1: fix ML/evaluation correctness

Write meaningful regression cases before implementation:

- In `eval/collect.py` and `eval/report.py`, combining computed cohort metrics
  with metadata must preserve existing run-integrity failures. An arrived
  cohort with `valid=False` or collision evidence must not become valid or
  produce a final journey/CO2 headline. Distinguish cohort completion from
  simulation validity; record missing integrity evidence explicitly.
- In `ml/forecast.py`, support a history window bracketed by observations
  without requiring a sample exactly 60 seconds ago. Fresh times
  0,10,15,...,65, with a permitted max gap of 15 seconds, should not be rejected
  solely because the boundary sample at 5 seconds is missing. Excessive gaps,
  stale samples and insufficient history must still cause abstention.
- Preserve zero-uplink/unknown behavior, vehicle deduplication, seed isolation,
  fixture-model rejection and forecast shutdown after intervention.
- Run the combined tests from a fresh checkout. Keep the original backend
  tests and shared contract examples. The broken ML-only pytest temp-directory
  configuration is deliberately absent from this combined branch.

The coordinator's diagnostic helper is `scripts/verify_prakhyat.py`; its input
is an isolated snapshot path, not the live application. Its constructed
fixtures are diagnostic inputs, never traffic evidence.

Acceptance: combined tests pass; collision/invalid metadata cannot produce
valid metrics or improvement percentages; irregular-window tests preserve
the intended abstention rules. Commit the fixes before proceeding.

## Task 2: stabilize and freeze the LIG simulation

Inspect `backend/harness/engine.py`, `scripts/build_lig.py` and the existing
diagnostic runs. Identify remaining collision/deadlock causes and preserve
the imported road geometry and its explicit join correction. Use saved SUMO
warnings and vehicle/route diagnostics to guide changes.

Validate everyday flow, incident progression and post-incident recovery on
seed 42 and additional development seeds. Use an explicit bounded drain
period when necessary; report pending insertion, active, arrived, removed,
collision and teleport counts. Freeze demand, routes, signal assumptions,
step length, warmup, horizon/drain rule and incident timing in manifests.
Changes to synthetic demand must be explained and retained consistently
across policies. Preserve faults and stress cases; do not disable collision
checking, remove problematic vehicles, or enable teleports to manufacture a
clean completion. Keep the UI and saved records truthful.

Acceptance: a repeatable ordinary-flow cohort drains without collisions or
teleports; incident effects and restoration have saved evidence; genuine
stress-run incompleteness remains visible. If a remaining blocker prevents
valid benchmarking, document its exact cause and continue unaffected work.

## Task 3: add a real batch runner and separate observations from truth

Implement a reusable LIG headless runner/export adapter in an owned path,
such as `eval/lig_runner.py`, compatible with `eval.generate execute`.
Exactly one thread/process owner uses each TraCI connection. The online
intelligence receives an observation history, never that connection.

Export the data that the existing ML/evaluation modules require:

Create a LIG-specific registry from the actual generated network for edge,
lane, signal and route mappings. Resolve contract IDs explicitly; Nandani's
original corridor registry does not describe LIG. Keep the permitted reference
speeds frozen rather than changing them with incident speed restrictions.

- `manifest.json`: run/scenario/demand IDs, seed, fixed/reactive/predictive
  policy, sensor mask, probe assignment, compliance, clock/step configuration,
  scheduled cohort size, network/demand/incident/probe/config hashes, vehicle
  and emissions assumptions, integrity flags and completion status.
- `observations.csv`: causal five-second observations from selected permitted
  sensors only, including freshness, distinct/fresh probes and signal context.
- `truth.csv`: full-state road slowdown and independent queue/jam labels for
  offline scoring. Empty roads have null slowdown. Never feed these columns
  back into the online feature generator.
- Explicit demand, `trips.csv`, lifecycle evidence for pending/unfinished
  vehicles, SUMO diagnostic output and control/incident event logs. Preserve
  scheduled departure times for entry-delay accounting and emission units.

Batch probing may use a deterministic emulator for a frozen vehicle assignment.
Label it `emulated_probe`, record participation/transport assumptions and apply
the same allowed-sensor rules to all policies. Do not relabel all rendered
vehicle truth as phone observations. A live run with zero authenticated phone
uplinks must still have zero phone-sourced market observations. Phone-gateway
integration remains through the existing validated-frame boundary; contracts
and phone authentication remain unchanged.

Do not feed one policy's probe readings into another policy's run. Freeze
the exogenous demand and incident schedule across the matched A/B/C runs,
while allowing their observed trajectories to differ naturally. Record any
change of scenario timing for training; do not leak future incident schedules
into features or treat predictable scripted timing as real forecasting skill.

Parallel batches, if useful after measuring a working sequential run, must
use independent processes with their own SUMO connection, port and run folder.
Do not share a TraCI connection across threads.

Acceptance: a small real-SUMO smoke batch reproduces scheduled cohorts for
the same seed, exports all required planes, passes the zero-observation and
causality checks, and imports through the existing dataset/evaluation modules.

## Task 4: train and evaluate genuine SUMO models

Yes, training is still required. Use the existing HistGradientBoostingRegressor
pipeline; the expensive work is generating valid simulation runs and checking
the data, rather than inventing a new model family.

Start with a small smoke batch to establish the runner, then freeze and expand
the experiment plan. Use disjoint complete seeds: training 100–107, validation
200–202, final held-out test 300–304; retain 42 for the demo. Resolve LIG's
actual scenarios, demand levels and masks explicitly. Train first-response
models only on fixed-policy runs. No test seed participates in fitting,
tuning, horizon/model selection or controller selection.

Train all three horizons (120, 180, 300 seconds). The target is full-state
road slowdown averaged over the 30-second window ending at `t+h`; unavailable
future bins or empty roads produce missing labels. Collision-corrupted runs
are unsuitable training evidence. A collision-free run truncated by a declared
horizon may still supply valid causal forecast labels before that horizon,
but its unfinished cohort cannot support journey/CO2 improvement claims.

Compare against persistence and trend, including per-seed MAE, coverage and
abstention, warning lead time, misses and false alerts per simulated hour.
Tune using validation only, then evaluate the frozen choice on held-out seeds.
If boosting fails to beat a baseline, retain and report that outcome; use the
better validated choice. Save genuine model artifacts, feature/schema version,
training provenance, environment version and checksums. Never promote or
rename fixture models into production models.

Acceptance: three models fitted from actual SUMO-derived observations and
offline labels; all three evaluated against both baselines; source/version
checks remain active; no fabricated improvement or unobserved future knowledge.

## Task 5: integrate and prove behavior

Wire the validated observation pipeline and selected model into the LIG
harness, with explicit source/model/coverage labels. Preserve the existing
browser controls, vehicle rendering and run export. Missing coverage shows
unknown, and forecasts abstain with a reason. No-action forecasts become
counterfactual/inactive after intervention and cannot silently govern renewal.

For policy evaluation, use the same bounded signal/diversion rules and
downstream guards for reactive and predictive control. Keep phase clearance,
min/max green and class restrictions. Use saved matched runs for fixed versus
reactive versus predictive; forecast contribution is predictive versus
reactive, not merely predictive versus fixed. Only complete, integrity-valid,
matched cohorts may produce improvement percentages. Preserve losing seeds,
missing runs and incomplete denominators. Keep modeled CO2 distinct from
real-world emissions claims.

Acceptance: cold launch, repeatable batch command, a visible mentor demo,
correct observation/forecast behavior, and an auditable report of actual
results and limitations. Commit small, tested changes and push
`feat/prakhyat-lig-work`; do not overwrite another owner's branch.

## Final handback

Report changed files, exact test commands/output, dataset/run counts and
provenance, simulation integrity, per-horizon validation/test results, model
location/hashes, repeatable launch/train/evaluate commands, and remaining
limitations. Distinguish completed work from plans and fixture evidence.

Do not add RL, an LSTM, another map provider, a native app, a cloud service or
new UI polish while these gates remain. A working, honestly evaluated harness
and forecast pipeline is the deliverable.
