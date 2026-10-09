# Traffix: LIG Square simulation harness

This is the real-road browser harness Kush requested. It is isolated in
`backend/harness/` so the existing phone backend and the team's `sim/` and
`web/` modules remain usable. It extends the original synthetic-corridor scope
with OSM geometry and a local 3D renderer; it does not add RL.

## Run on Windows

From the repository root:

```powershell
.venv/Scripts/python.exe -m pip install -r backend/harness/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.harness.app:app --host 127.0.0.1 --port 8001 --workers 1
```

Open http://localhost:8001. All runtime assets are local, including Three.js.
Use one server worker: exactly one simulation thread owns TraCI. HTTP handlers
enqueue commands and WebSocket clients share that simulation. This is a local,
single-operator demonstration service, not a production multi-user deployment.

## Mentor walkthrough

1. Show LIG Square's OSM road network and building footprints. Orbit, zoom,
   switch to top-down, and click a vehicle to inspect or follow it.
2. Start Everyday flow. Pause and single-step to demonstrate that the view
   follows the actual SUMO engine, rather than a decorative animation.
3. Choose Evening rush, Monsoon slowdown, or Curbside obstruction. Each reset
   creates a new recorded run using the visible seed. Runs start paused at
   120 seconds after warming the network; demand ends at 900 seconds and the
   horizon is 1200 seconds.
4. Point out live vehicle count, stopped vehicles (speed below 0.1 m/s), mean
   speed, finished journeys, pending departures, collisions and teleports.
5. Export the run. Resetting or shutting down also saves a manifest and
   recording under `runs/lig.<id>/`, with demand XML, SUMO diagnostics and trip
   output. The manifest contains seed, network/demand hashes and completion.

## What is real, and what remains a model

- Real: OSM street geometry and building footprints around LIG Square,
  Indore (22.73360 N, 75.89011 E); actual SUMO positions, speeds and signals.
- Synthetic: arrivals, route selection, fleet shares and driving parameters.
  Six explicit vehicle types cover cars, motorcycles, autos, e-rickshaws,
  buses and delivery vans. Left-hand traffic and sublane movement are enabled.
- Inferred: lane defaults, signal plans and missing building heights. The fixed plan serves incoming approaches separately with 30-second greens,
  3-second yellow and 8-second clearance. An explicit import join combines
  four OSM nodes at the square to remove sub-vehicle-length external links;
  its UTM coordinates are retained in `lig-joins.nod.xml`. These choices
  have not been surveyed at the intersection. The 3D models are stylized.
- Rain is a scripted local speed reduction; obstruction is a slow approach
  lane. Restrictions start at 60 seconds and clear at 360 seconds, or manually.
  They are surrogates, not validated rain physics or an actual parked obstacle.
- Lane-independent Indian driving, deliberate red-light violations, pedestrian
  interactions and calibrated illegal movements are not implemented.
- Imported junctions can produce collision warnings. The UI and exports expose
  them. A collision-bearing or unfinished run is not marked complete and must
  not be used to claim policy improvement. CO2 is SUMO's uncalibrated model
  output, not measured local emissions.

The harness shows simulation truth for inspection. It is not wired into the
phone-observation detector and must not feed hidden truth into that detector.
No Google ETA, live traffic, phone integration or learned controller is included.
Later ETA data can help constrain travel-time calibration, but will not alone
identify turning demand, vehicle mix or rule-breaking rates.

## Rebuild and verify

```powershell
.venv/Scripts/python.exe scripts/build_lig.py
.venv/Scripts/python.exe -m pytest tests/test_harness.py -q
.venv/Scripts/python.exe scripts/check_lig.py
```

The builder uses the checked-in OSM extract; no map service is needed at runtime
or during rebuild. Validation runs all four scenarios to the 1200-second
horizon and writes `runs/lig-validation.json`, preserving each experiment.
Tests cover real SUMO reproducibility, pause/step, invalid controls and export.

## Attribution

Map data © OpenStreetMap contributors, available under the ODbL:
https://www.openstreetmap.org/copyright . The source extract and derived
network/geometry are supplied in `backend/harness/data/`. Downloaded 2026-10-09
from the OSM API, bbox `75.882,22.727,75.898,22.741`. Database derivatives remain
subject to ODbL; application source licensing is separate.

Three.js 0.180.0 is vendored from the official npm package under its MIT
license, retained in `static/vendor/THREE-LICENSE.txt`. SUMO is installed via
its official `eclipse-sumo` package, pinned to 1.28.0.
