# Parameter provenance

`assumptions.json` is the registry specifically requested by Kush. No existing
Nandani simulation files are changed. Every entry records value, unit,
observed/published/assumed source type, source note and date. Currently all traffic
parameters are **assumed**; do not call them field measurements. OSM street
geometry has its separate provenance in the checked-in world file.

The demo loader reads `demo.*` values on reset. Observed rain speed/duration,
cohort, reference speed, decision margin and rule thresholds can replace these
values without editing code. Each loaded registry is hashed into the scenario
manifest. A changed registry invalidates the old baseline; regenerate and test
it, never silently reuse mismatching comparison numbers.

Reference-only descriptions (exploratory weights, lane limits, existing signal
program, left-hand geometry and lane-based setting) document assumptions rather
than pretending to rebuild the OSM network automatically. Changing geometry,
signal plans or driving physics requires deliberate validation. This demo uses
12 staged vehicles, not a statistically representative evening peak.
