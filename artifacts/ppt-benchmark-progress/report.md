# Traffix measured benchmark

Synthetic SUMO results; not field-calibrated. Negative outcomes and faults retained.

| Seed | Policy | Cohort | Integrity | Mean journey (s) | Modelled CO2 (kg) |
|---|---|---|---|---|---|
| 42 | fixed | ?/? | host experiment wall deadline | None | None |
| 42 | fixed | 63/63 | complete | 327.84587301587305 | 49.2681 |
| 42 | actuated | 63/63 | complete | 320.8696825396826 | 48.2422 |
| 42 | pressure | 63/63 | complete | 287.7784126984127 | 45.2237 |
| 51 | fixed | 49/49 | complete | 291.83408163265307 | 38.403 |
| 51 | actuated | 49/49 | complete | 288.675918367347 | 38.2866 |
| 51 | pressure | 49/49 | complete | 259.67081632653066 | 35.8072 |
| 52 | fixed | 79/79 | complete | 329.6720253164557 | 61.5328 |
| 52 | actuated | 79/79 | complete | 329.7005063291139 | 61.536 |
| 52 | pressure | 79/79 | complete | 291.43151898734175 | 56.4836 |
| 53 | fixed | 133/135 | incomplete | None | 123.1019 |
| 53 | actuated | 135/135 | complete | 436.46474074074075 | 119.7109 |
| 53 | pressure | 135/135 | complete | 429.4036296296296 | 117.7666 |

## Matched improvements (positive = better; negative = worse)

| Seed | Policy | Valid comparison | Journey reduction % | CO2 reduction % |
|---|---|---|---|---|
| 42 | actuated | complete_matched_cohorts | 2.1278872331123475 | 2.0822804207996657 |
| 42 | pressure | complete_matched_cohorts | 12.221431964013298 | 8.208962797428754 |
| 51 | actuated | complete_matched_cohorts | 1.0821776701466392 | 0.3031013202093553 |
| 51 | pressure | complete_matched_cohorts | 11.021079212608214 | 6.7593677577272535 |
| 52 | actuated | complete_matched_cohorts | -0.008639196070971947 | -0.005200478444016277 |
| 52 | pressure | complete_matched_cohorts | 11.599560591289622 | 8.205704924853084 |
| 53 | actuated | incomplete_or_faulted_cohort | None | None |
| 53 | pressure | incomplete_or_faulted_cohort | None | None |

## Waiting, tails and sampled queues

P95 uses the inclusive linear percentile of completed trip XML values. Queue peaks are sampled from saved frames, not continuous maxima.

| Seed | Policy | Mean stopped waiting (s) | P95 stopped waiting (s) | P95 journey (s) | Sampled peak queue |
|---|---|---|---|---|---|
| 42 | fixed | unavailable | unavailable | unavailable | unavailable |
| 42 | fixed | 106.61 | 171.95 | 470.64 | 38.00 |
| 42 | actuated | 99.38 | 171.43 | 429.45 | 36.00 |
| 42 | pressure | 66.05 | 186.07 | 445.69 | 29.00 |
| 51 | fixed | 73.45 | 168.05 | 412.52 | 23.00 |
| 51 | actuated | 70.03 | 156.95 | 423.52 | 22.00 |
| 51 | pressure | 41.51 | 120.60 | 357.17 | 17.00 |
| 52 | fixed | 109.77 | 253.60 | 510.16 | 49.00 |
| 52 | actuated | 109.79 | 253.57 | 489.00 | 48.00 |
| 52 | pressure | 66.82 | 171.22 | 441.32 | 40.00 |
| 53 | fixed | unavailable | unavailable | unavailable | unavailable |
| 53 | actuated | 188.29 | 505.10 | 815.39 | 90.00 |
| 53 | pressure | 164.35 | 481.52 | 809.52 | 74.00 |

actuated: 3 valid pairs; mean per-seed journey reduction 1.07%; range -0.01% to 2.13%. This is not a confidence interval.

pressure: 3 valid pairs; mean per-seed journey reduction 11.61%; range 11.02% to 12.22%. This is not a confidence interval.
