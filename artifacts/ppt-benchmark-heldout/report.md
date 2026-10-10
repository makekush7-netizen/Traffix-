# Traffix measured benchmark

Synthetic SUMO results; not field-calibrated. Negative outcomes and faults retained.

| Seed | Policy | Cohort | Integrity | Mean journey (s) | Modelled CO2 (kg) |
|---|---|---|---|---|---|
| 51 | fixed | 49/49 | complete | 291.83408163265307 | 38.403 |
| 51 | actuated | 49/49 | complete | 288.675918367347 | 38.2866 |
| 51 | pressure | 49/49 | complete | 259.67081632653066 | 35.8072 |
| 52 | fixed | 79/79 | complete | 329.6720253164557 | 61.5328 |
| 52 | actuated | 79/79 | complete | 329.7005063291139 | 61.536 |
| 52 | pressure | 79/79 | complete | 291.43151898734175 | 56.4836 |

## Matched improvements (positive = better; negative = worse)

| Seed | Policy | Valid comparison | Journey reduction % | CO2 reduction % |
|---|---|---|---|---|
| 51 | actuated | complete_matched_cohorts | 1.0821776701466392 | 0.3031013202093553 |
| 51 | pressure | complete_matched_cohorts | 11.021079212608214 | 6.7593677577272535 |
| 52 | actuated | complete_matched_cohorts | -0.008639196070971947 | -0.005200478444016277 |
| 52 | pressure | complete_matched_cohorts | 11.599560591289622 | 8.205704924853084 |

## Waiting, tails and sampled queues

P95 uses the inclusive linear percentile of completed trip XML values. Queue peaks are sampled from saved frames, not continuous maxima.

| Seed | Policy | Mean stopped waiting (s) | P95 stopped waiting (s) | P95 journey (s) | Sampled peak queue |
|---|---|---|---|---|---|
| 51 | fixed | 73.45 | 168.05 | 412.52 | 23.00 |
| 51 | actuated | 70.03 | 156.95 | 423.52 | 22.00 |
| 51 | pressure | 41.51 | 120.60 | 357.17 | 17.00 |
| 52 | fixed | 109.77 | 253.60 | 510.16 | 49.00 |
| 52 | actuated | 109.79 | 253.57 | 489.00 | 48.00 |
| 52 | pressure | 66.82 | 171.22 | 441.32 | 40.00 |

actuated: 2 valid pairs; mean per-seed journey reduction 0.54%; range -0.01% to 1.08%. This is not a confidence interval.

pressure: 2 valid pairs; mean per-seed journey reduction 11.31%; range 11.02% to 11.60%. This is not a confidence interval.
