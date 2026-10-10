# Traffix — Prakhyat's ML and evaluation implementation

Detection, 120/180/300-second forecasting, training-data transformations, whole-cohort journey/CO2 accounting, validation-only trigger tuning, held-out evaluation, and report generation are implemented here.

**The runnable sample is an artificial software fixture. No SUMO traffic results or congestion improvements have been produced.** Real training and traffic experiments need Nandani's network/demand and the integration owner's simulation runner.

## Run now

From this folder in PowerShell, the local virtual environment is already prepared:

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m eval.pipeline --output-dir artifacts/fixture-demo
```

Or run both with `powershell -ExecutionPolicy Bypass -File scripts/run_prakhyat.ps1`. This sets execution policy only for that process.

The smoke run creates:

- `artifacts/fixture-demo/observations.csv`, `truth.csv`, `dataset.csv`;
- three trained **fixture-only** models and their checksums in `models/`;
- validation and held-out forecast scores;
- validation-only trigger screening and fixture detection scores;
- `mentor-report/report.md`, cohort and observation charts;
- `summary.json`, which explicitly leaves traffic improvement unavailable.

Fixture-trained boosting models cannot authorize live control. Persistence/trend work without loading any model. Unknown/stale coverage remains missing.

## Start on another computer

Use Python 3.12; this is the version tested here. Do not copy `.venv` between computers.

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
& .\.venv\Scripts\python.exe -m pytest -q
```

The pinned versions in `requirements-lock.txt` are the versions installed for this build. SUMO binaries are a separate prerequisite; the optional `traci`/`sumolib` clients do not themselves constitute a validated SUMO installation.

## Team handoff

Read [the implementation and handoff guide](docs/Prakhyat-Implementation-and-Handoff.md) for backend integration, Nandani's required files, exact CSV extensions, real-run commands, experiment gates, ownership and remaining work. Read [the feature audit](docs/Feature-and-Metric-Audit.md) before wiring any full-state simulation data into an online model.

The [independent-work audit](docs/Prakhyat-Independent-Work-Audit.md) records the defects repaired, checks performed and remaining external dependencies. To exercise file/command boundaries and regenerate the approved experiment plans:

```powershell
& .\.venv\Scripts\python.exe scripts/verify_prakhyat_cli.py
& .\.venv\Scripts\python.exe scripts/build_experiment_plans.py
```

The CLI audit uses labelled fixtures and saves its logs under a new `.cache/cli-audit/` directory. It does not run SUMO. Plans contain 48 training, 18 validation, 15 fixed-policy forecast-test, 45 core policy, 10 sensor-ablation and 30 optional compliance jobs. Overlapping jobs reuse their identical IDs; these counts must not be added as unique executions.

```powershell
& .\.venv\Scripts\python.exe scripts/doctor.py --output artifacts/prakhyat-preflight.json
```

Exit code 2 means the real SUMO prerequisites are still missing. The check does not start SUMO or alter the machine.

## Ownership

Prakhyat owns `ml/`, `eval/`, their tests and evidence outputs. The original three planning documents are preserved. The supplied schemas were extracted unchanged into `contracts/`; no shared message fields were renamed. `TrafficIntelligence` produces compatible observation/forecast payloads, not a WebSocket server or a traffic controller.

The integration owner supplies authentication, phone-to-vehicle binding, frame validation, the single TraCI worker, signals/diversions/overrides and broadcasting. Nandani supplies simulation assets and verified incidents. Urvashi consumes the resulting authoritative snapshots.
