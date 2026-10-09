# AGENTS.md: rules for coding agents working on Trafixx

Read this first. Then read only the module spec you were given and `contracts/`.

## Project in one paragraph
Trafixx is a hackathon demo: one live SUMO simulation of a synthetic Indian market
corridor (Nandipur Bazaar), three real phones bound to simulated vehicles over a local
network, a detection and forecast pipeline that sees ONLY phone-sent observations, bounded
signal/diversion responses, and a comparison against a fixed-time baseline.
Full spec: `docs/astra-build-plan.md` (long; read only the sections you need).

## Hard rules
1. Edit only the paths you own (see `OWNERS.md`). Do not "clean up" other modules.
2. Do not rename or change anything in `contracts/`. If a field is missing, say so in your report.
3. Exactly one thread owns the TraCI connection. HTTP/WebSocket handlers enqueue commands; they never call TraCI.
4. Phones never choose their own vehicle ID, route, signal command or timestamp.
5. The detector and forecaster receive an observation window, never a TraCI connection and never hidden SUMO truth.
6. Unknown is not uncongested. Missing or stale data stays "unknown".
7. Simulated time and wall-clock time are different. Expiry of guidance/actions uses simulated time; heartbeats use wall time.
8. No invented numbers. All thresholds are untested starting values, not results.
9. Never claim improvement without saved run files. Incomplete runs are shown as incomplete.
10. No cloud services, CDNs, online fonts or map tiles. Everything runs offline on one laptop.
11. Do not add RL, LSTM, native apps, gamification, or real GPS/accelerometer features.
12. Do not modify SUMO itself.

## Workflow for every task
1. Read the module spec given to you and the relevant schemas in `contracts/`.
2. Write the failing acceptance test first (named in the spec).
3. Implement only your owned files.
4. Run the test. Report: changed files, test output, known limitations.
5. Keep changes small. Commit with a clear message.

## Units and IDs
- Time: seconds (simulated unless named `wall_`). Speed: m/s. Distance: m. CO2: mg/s from SUMO; report kg.
- IDs: `jct.*`, `tls.*`, `edge.*`, `type.*`, roles `veh.role.rider|auto|delivery`.
- SUMO may generate different junction/signal IDs than our names: the registry in `sim/net/id-registry.json` holds the REAL IDs.

## Commands
- Tests: `pytest`
- Env check: `python scripts/check_env.py`
- Server: `python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 1`
