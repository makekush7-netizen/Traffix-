# Traffix

Prediction-driven traffic incident response for sensor-poor Indian corridors.
Built for the Agnitia 36-hour hackathon, TERRA track, problem statement
"Intelligent Traffic Congestion Response System".

**Status:** Traffix v1.0 mentor prototype. Real OpenStreetMap LIG Square geometry,
12 staged simulated vehicles, QR-bound phone browser apps, validated phone-only
observations and an explicitly enabled rule-based route offer. A driver must
accept before the server applies Route B. No live trained-model or signal control,
calibrated traffic, general savings claim or native APK.

Run `./scripts/run_mobile.ps1`, then `./scripts/demo_check.ps1`. Open
`http://localhost:8002/dashboard` on the laptop; invite two phones on the same
hotspot. Follow [the exact mentor flow](docs/demo-runbook.md): Blind spot → Phones
see → Traffix decides → Driver follows. See [verification and safe claims](docs/integration-report.md).

## Intended full system
1. Simulates a mixed-traffic market corridor in SUMO.
2. Real phones connect over the local network and act as probe devices for simulated vehicles.
3. A restricted gateway admits only phone-sent data as observations (missing uplink = unknown, not "clear").
4. Detection and short-term forecast flag worsening congestion.
5. Bounded signal changes, diversions and advisories are applied and logged.
6. Results are compared against a fixed-time, no-action baseline (journey time, modeled CO2).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/check_env.py
```
Run the server (once backend exists):
```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 1
```
Phones open `http://<laptop-LAN-IP>:8000/driver`. Dashboard: `/dashboard`.

## Layout
See `AGENTS.md` for ownership and rules. Specs live in `docs/`. Shared schemas live in `contracts/`.
