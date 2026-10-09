# Feature and metric audit

## Online information boundary

`ml/` does not import TraCI. `TrafficIntelligence` accepts only gateway-validated phone samples, explicitly labelled emulated probes, and fixed sensors on an explicit edge allowlist. Authentication and frame validation belong to the backend; this class must not be exposed directly as an unauthenticated endpoint.

Each vehicle contributes its latest sample once. Its old edge loses that vote after it reports from another edge. A phone disconnect creates no new observations; the last accepted sample expires after 15 simulated seconds. The default fixed-sensor allowlist is empty.

The schema's `mean_speed_mps` field carries **median fresh probe speed** on a probe-only edge, as specified in the build plan. On an allowed fixed-sensor edge it carries that sensor's measured mean speed. Slowdown is `clip(1 - speed/reference_speed, 0, 1)`, a proxy rather than an exact queue count. The reference speed is a frozen registry assumption, not the incident-adjusted speed limit. No fresh evidence means null slowdown, never zero.

## Exact model feature allowlist

| Column | Source and meaning |
|---|---|
| `slowdown_now` | Current permitted observation |
| `slowdown_mean_30` | Mean of fresh permitted samples in the past 30 s |
| `slowdown_mean_60` | Same, past 60 s |
| `slowdown_mean_120` | Same, past 120 s |
| `slowdown_slope_60` | Linear trend from fresh samples, per simulated second |
| `distinct_probes_60s` | Unique vehicles in the aggregation window |
| `sample_age_sim_s` | Age of the chosen speed evidence; a newer probe cannot freshen an older selected fixed reading |
| `fixed_queue_ratio` | Optional queue/capacity ratio from an allowed fixed sensor |
| `history_span_s` | Span of the same retained 120-second window online and offline |
| `fresh_fraction_60` | Fraction of recent logged snapshots with fresh evidence |

Actual signal state is used by the detector and trigger gates, not by this first forecast feature set. Boundary-edge interactions are not included in the first regressor. This deliberately small feature set must prove itself against trend/persistence before expansion.

No feature reads truth, route arrival times, future demand, weather schedules, incident start/end times, future speed limits or hidden market detectors. Seed/run/scenario/provenance fields are metadata only. Dataset construction is causal and per run/edge. Future labels are averages over the 30-second window ending at `t+h`; missing future bins produce missing labels. Empty roads must have null truth slowdown, not zero.

Missing model inputs use a training-fitted imputer with explicit missingness indicators. Those internal fill values are never sent as traffic observations. Current unknown/stale coverage and insufficient history still block control. Sixty seconds of history must contain no observation gaps above 15 s. Probe-only control also requires two **currently fresh** vehicles; the 60-second count alone is insufficient.

## Forecast interpretation

Training/validation rows use fixed/no-action runs. Entire seeds are split: train 100–107, validation 200–202, test 300–304. Demo seed 42 never enters those sets. Three independent gradient-boosting pipelines predict 120, 180 and 300 seconds ahead. Persistence and clipped linear trend are evaluated on the same eligible rows.

A forecast can suggest only the first intervention. After an action starts, these no-action forecasts return unavailable and cannot renew control. Recovery uses current observations. Fixture or unverified boosting artifacts cannot authorize control. Version/feature/horizon/policy/checksum checks run before loading trusted local model artifacts.

## Accounting and evidence

| Number | Definition / restriction |
|---|---|
| Mean journey | Mean of `arrival - scheduled_depart`; includes entry waiting and detours |
| P95 journey | 95th percentile of the same full-cohort journeys |
| Completeness | Every scheduled evaluation vehicle arrived; pending/active/removed retained |
| Validity | Complete, no removal and no teleport; invalid runs have no headline journey gain |
| CO2 final | Sum of vehicle whole-trip `co2_mg / 1e6`; all records must have emissions |
| CO2 so far | Sum of known records only; may omit missing/ongoing records; not final benefit |
| CO2 rate integration | Sum of rates in mg/s times each simulated step duration, divided by 1e6 |
| Waiting | Sum of each vehicle's final cumulative `waiting_s` once; does not include entry delay |
| Predictive value | Paired journey improvement of predictive **versus reactive**, not MAE alone |

The finalized-run collector requires `scheduled_cohort_size` and rejects CSV exports with fewer records. The XML importer starts from explicit demand and requires lifecycle evidence for vehicles absent from tripinfo. Artificial blockers may be excluded only using the declared ID list. Never omit incomplete vehicles to make a result look better.

The paired report checks cohort/network/incident checksums, keeps negative outcomes and exposes missing policies. Pass the expected job plan so entirely missing seeds stay in the denominator. Hold compliance and sensor mask fixed within a policy comparison. Produce separate comparisons for compliance 0/.2/.6 and sensor ablations.

Comparison now also freezes demand level, actual metric-cohort/exclusion fingerprints, shared control configuration, participating probes and emission assumptions. The collector derives actual cohort fingerprints from raw trips, preventing exclusions from manufacturing a gain. Cross-mask ablation deliberately permits different probe assignments. Missing audit fields suppress gains. Event scoring reports missed independent jams and false alerts per network simulated hour. Queue and bypass areas, peaks and applied-action counts are exported separately; missing evidence is unavailable.

## Verified source and remaining assumptions

The [official SUMO TripInfo documentation](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html) confirms that `depart` is actual insertion time, `departDelay` is entry delay, default output is generated on arrival, `--tripinfo-output.write-unfinished` enables unfinished output, and nested emissions `CO2_abs` is milligrams for the whole trip. The importer also requires frozen scheduled departure times from demand rather than assuming `duration` is total journey time.

SUMO's [TripInfo implementation](https://github.com/eclipse-sumo/sumo/blob/main/src/microsim/devices/MSDevice_Tripinfo.cpp) writes `vType` and textual `vaporized` reasons. The importer handles `end` as unfinished and known removal reasons (including `traci`/`teleport`) as removal; a teleport count is still mandatory for real-run headline evidence. This was checked against source and XML fixtures, not an installed SUMO executable. Validate actual output before the final experiment.

The following remain unverified until actual runs exist: all congestion thresholds; real baseline jams and recovery; which horizon/model helps; controller gains; two-wheeler stability; real mixed-fleet emission assumptions; and physical-phone coverage quality. The supplied scenario's bike/auto passenger-car emission proxies are placeholders, not a verified India fleet calibration.
