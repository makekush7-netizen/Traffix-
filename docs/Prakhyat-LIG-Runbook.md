# Prakhyat LIG runbook

Run from this repository root using Python 3.12. The original synthetic phone
backend remains separate and unchanged. Shared contracts, `sim/`, and `web/`
are preserved. LIG geometry is imported OSM; demand, fleet weights, signal plans,
speed restrictions and probe participation are synthetic assumptions.

## Fresh installation and verification

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r ml/requirements-training.txt
.venv/Scripts/python.exe -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q']))"
```

On Windows a short checkout or short venv path avoids bundled SUMO package path
limits. On this machine the verified interpreter is
`C:/Users/prakh/Documents/Codex/lig-venv/Scripts/python.exe`.
Do not copy a virtual environment between machines.

## Real data, fit, freeze, evaluate

```powershell
python -m eval.lig_pipeline training --workers 3
python -m eval.lig_analysis fit
python -m eval.lig_analysis select
python -m eval.lig_analysis policies --workers 3
python -m eval.lig_analysis heldout
python -m eval.lig_analysis ablation --workers 3
```

Each child process owns its own TraCI connection, SUMO port and run directory.
Batches resume only completed matching jobs; a partial failed directory is
reported instead of overwritten. Use a new explicitly named output root to
retry a failed job after a repair. Training has 96 fixed jobs: three scenarios,
two demands, 16 disjoint seeds. Response evaluation has 36 validation jobs and
60 final test jobs. Fixed comparators reuse their own already saved runs.
The optional boundary-only ablation adds five held-out roadworks runs.

The executor-compatible smoke command is:

```powershell
python -m eval.generate plan --scenarios lig.everyday lig.rain lig.roadworks --seeds 42 --policies fixed --sensor-masks mask.lig.probes --demand-ids demand.lig.ordinary --output runs/smoke-plan.json
python -m eval.generate execute --plan runs/smoke-plan.json --output-dir runs/new-smoke --runner python -m eval.lig_runner
```

Dataset labels are offline full-state slowdown means across six five-second
bins ending at t+120/180/300. Empty roads and unavailable bins stay missing.
Features never include future incident timing or truth. Collision-corrupted
runs are retained and excluded. Collision-free truncated runs may provide
labels but cannot provide final journey or CO2 gains. All cohort CSVs include
every scheduled vehicle, entry delay, unfinished states and emission units.

## Mentor demo

```powershell
python scripts/run_lig_ml.py --probe-mode emulated --policy reactive --scenario roadworks --models models/lig-v1 --selection runs/lig-evidence/selection.json
```

Open `http://127.0.0.1:8001`. This is a LIVE SUMO run with explicitly EMULATED
probes; it is not a physical-phone demonstration. At 8x playback use pause,
step, reset, clear incident and the bounded-autonomy pause button. The default
phone mode can demonstrate the honesty gate:

Reactive is the recommended demo policy: validation showed little consistent
prediction benefit. Boosting forecasts remain visible before intervention.
Use `--policy predictive` to demonstrate the separately evaluated predictive
controller; do not claim it consistently beats reactive control.

For the checked-in pretrained release, use its matching packaged
`--selection models/lig-v1/evidence/selection.json`. After rerunning training,
use the newly generated `runs/lig-evidence/selection.json` as shown above;
model/selection checksum mismatches stop before SUMO starts.

```powershell
python scripts/run_lig_ml.py --probe-mode phone --policy fixed --models models/lig-v1
```

Zero authenticated uplinks show unknown on `edge.lig.approach.0`, even while
vehicles are rendered. Simulated fixed boundary detectors may still observe
other edges. Forecasts display eligibility and abstention reasons. After the
first applied action, no-action forecasts stop governing control; reactive
guards continue. The pause button prevents new actions; any current bounded
green finishes with its ordinary yellow/all-red sequence.

## Phone integration boundary for Kush

`HarnessEngine.accept_validated_probe(message)` enqueues a validated contract
`probe.sample` message for the worker. It is deliberately not a public ingest
endpoint. Kush must use the existing authenticated `ProbeGateway` with LIG
frames and the SAME run/vehicle bindings before calling it. Logical edge aliases
come from `eval.lig_registry.load_registry()`, not Nandani's corridor registry.
Do not feed the separate port-8000 fixture simulation into port-8001 LIG.
Physical-phone coverage remains unverified until that coordinator wiring and
real devices are tested. Prakhyat's pipeline boundary and zero-uplink gate are
implemented; no authenticated physical phone is claimed by these experiments.

## Files worth inspecting

- `runs/lig-training/plan.json` and every run's manifest, observations, truth,
  trips, lifecycle, diagnostics and incident/control events.
- `runs/lig-data/data-integrity.json` and `dataset.csv`.
- `models/lig-v1/manifest.json`, three joblib files, validation and provenance.
- `models/lig-v1/evidence/`: frozen selection, forecast/warning scores,
  policy comparisons and sensor ablation copied from the actual experiments.
- `docs/Prakhyat-LIG-Simulation-Freeze.md` for failed development conditions.

A forecast MAE improvement does not establish traffic improvement. Report
predictive versus reactive journeys separately from reactive versus fixed.
Modelled CO2 uses recorded SUMO emission classes, including unvalidated auto,
e-rickshaw and two-wheeler proxies. No calibrated climate claim is warranted.
