# Traffix measured benchmark

Synthetic SUMO results; not field-calibrated. Negative outcomes and faults retained.

| Seed | Policy | Cohort | Integrity | Mean journey (s) | Modelled CO2 (kg) |
|---|---|---|---|---|---|
| 53 | fixed | 133/135 | incomplete | None | 123.1019 |
| 53 | actuated | 135/135 | complete | 436.46474074074075 | 119.7109 |
| 53 | pressure | 135/135 | complete | 429.4036296296296 | 117.7666 |

## Matched improvements (positive = better; negative = worse)

| Seed | Policy | Valid comparison | Journey reduction % | CO2 reduction % |
|---|---|---|---|---|
| 53 | actuated | incomplete_or_faulted_cohort | None | None |
| 53 | pressure | incomplete_or_faulted_cohort | None | None |

## Waiting, tails and sampled queues

P95 uses the inclusive linear percentile of completed trip XML values. Queue peaks are sampled from saved frames, not continuous maxima.

| Seed | Policy | Mean stopped waiting (s) | P95 stopped waiting (s) | P95 journey (s) | Sampled peak queue |
|---|---|---|---|---|---|
| 53 | fixed | unavailable | unavailable | unavailable | unavailable |
| 53 | actuated | 188.29 | 505.10 | 815.39 | 90.00 |
| 53 | pressure | 164.35 | 481.52 | 809.52 | 74.00 |
