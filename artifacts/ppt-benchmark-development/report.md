# Traffix measured benchmark

Synthetic SUMO results; not field-calibrated. Negative outcomes and faults retained.

| Seed | Policy | Cohort | Integrity | Mean journey (s) | Modelled CO2 (kg) |
|---|---|---|---|---|---|
| 42 | fixed | 63/63 | complete | 327.84587301587305 | 49.2681 |
| 42 | actuated | 63/63 | complete | 320.8696825396826 | 48.2422 |
| 42 | pressure | 63/63 | complete | 287.7784126984127 | 45.2237 |

## Matched improvements

| Seed | Policy | Valid comparison | Journey reduction % | CO2 reduction % |
|---|---|---|---|---|
| 42 | actuated | complete_matched_cohorts | 2.1278872331123475 | 2.0822804207996657 |
| 42 | pressure | complete_matched_cohorts | 12.221431964013298 | 8.208962797428754 |

actuated: 1 valid pairs; mean per-seed journey reduction 2.13%; range 2.13% to 2.13%. This is not a confidence interval.

pressure: 1 valid pairs; mean per-seed journey reduction 12.22%; range 12.22% to 12.22%. This is not a confidence interval.
