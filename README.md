# Trafixx

Prediction-driven traffic incident response for sensor-poor Indian corridors.
Built for the Agnitia 36-hour hackathon, TERRA track, problem statement
"Intelligent Traffic Congestion Response System".

**Status:** hackathon prototype. The LIG Square lab now uses real OpenStreetMap
geometry with simulated traffic, a mobile driver app, and an authenticated phone
bridge. Native APK packaging, calibrated traffic, and live automatic routing or
signal control are not complete. No real-world performance claim yet.

**Current mobile demo:** run `./scripts/run_mobile.ps1` on Windows, then open
`http://localhost:8002/dashboard` on the laptop. Invite phones on the same Wi-Fi
through QR codes. Read [the mobile runbook](docs/mobile-app.md) for setup,
verification and limitations. The 3D simulation is at `/`; driver screens at `/driver`.

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
