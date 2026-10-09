# LIG simulation development evidence

The imported OSM network and explicit LIG join are unchanged. The network SHA256 is
`5e1ba257cf9f0d2e8352bd0461d139c9a85db2a18ceaeba4f776a94f59522e62`.
These are synthetic driving/demand assumptions, not India calibration.

## Reproduced failures

The original 1,900 vehicles/hour seed-42 everyday run reproduced 500 scheduled,
255 arrived at 1,200 s, 8 collision involvements, zero teleports. Original rush,
rain and roadworks likewise remain invalid/incomplete. Saved original runs are
under `runs/lig.*` and `runs/lig-validation.json` on the development machine.

The conservative profile with sublane movement at 1,900/hour and a 2,400-second
bound produced 246/500 arrivals and 10 collision involvements. Lane-based movement
at the same rate produced 358/500 and 2 collisions. Collision diagnostics identify
priority junctions as well as very short/curved links; the precise geometry defect
has not been established. We do not claim the entire imported network is repaired.

## Ordinary-flow gate

Reducing the explicit synthetic ordinary arrival rate to 500/hour, keeping all
70 route choices and all six types, using lane-based movement with conservative
gaps, and draining to at most 2,400 s yielded:

| Development seed | Scheduled/arrived | End time s | Collision involvements | Teleports |
|---|---:|---:|---:|---:|
|42|145/145|1488.25|0|0|
|43|142/142|1556.25|0|0|
|44|157/157|1502.50|0|0|

No vehicle removal or teleport shortcut was enabled. Collision checking stays
enabled at junctions, with collision action `warn`; faults invalidate evidence.
Sublane remains an explicitly failing development option, disabled in the ordinary
profile. The original stress demand is preserved as the rush preset. Ordinary
clean completion is not proof of a baseline congestion event.

## Frozen batch assumptions

Batch scenario IDs are explicitly `lig.everyday`, `lig.rain`, `lig.roadworks`.
Rates are 500/hour (`demand.lig.ordinary`) and 750/hour (`demand.lig.busy`);
the second rate is an experimental condition, not a validated capacity.
Step 0.25 s; demand ends 900 s; nominal horizon 1,200 s; maximum drain 2,400 s;
batch warmup 0 to preserve all observations. UI warmup remains 120 s.
Seeded incident start varies from 180–360 s; duration 360 s. Rain ramps down
over 120 s to 3 m/s on the two lanes of actual edge `191621641#11`; obstruction
restricts its lane 0 to 0.7 m/s. This is a speed-restriction surrogate. Restoration
uses the saved original limits. Original wider rain/roadworks presets remain in
the interactive harness unless the batch configuration is selected.

All matched policies share demand XML, geometry, incident schedule, probe
assignment, emissions and common control guards. Each policy observes its own
trajectories. Future schedules are manifest-only and never model features.
