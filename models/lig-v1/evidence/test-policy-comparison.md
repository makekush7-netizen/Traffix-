# Paired policy evidence

Positive percentages mean improvement; negative percentages mean worse performance.

Missing, incomplete or invalid runs cannot produce a gain. Supply the expected plan to count entirely missing seeds.

| Scenario | Demand | Source | Compliance | Sensor mask | Metric | Valid / attempted seeds | Wins | Median % | Range % |
|---|---|---|---:|---|---|---:|---:|---:|---:|
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 4 | 0.61 | 0.00 to 2.38 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 5 | 1.04 | 0.30 to 2.38 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 2 | 0.00 | -0.72 to 2.08 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 5 | 0.68 | 0.12 to 1.83 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 0 | 0.00 | -1.51 to 0.00 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 1 | -0.75 | -1.51 to 0.89 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 1 | -0.55 | -1.14 to 0.89 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 2 | -0.60 | -0.74 to 1.01 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 4 | 3.28 | -0.04 to 6.23 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 4 | 3.28 | -0.42 to 6.23 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 1 | 0.00 | -1.20 to 0.31 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 3 | 1.83 | -0.25 to 2.94 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 2 | 0.00 | -1.13 to 1.44 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 2 | -0.47 | -1.97 to 1.60 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 1 | 0.00 | -1.97 to 0.17 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 2 | -0.15 | -1.23 to 1.12 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 5 | 7.22 | 5.01 to 9.19 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 5 | 7.22 | 5.01 to 9.19 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 0 | 0.00 | -0.93 to 0.00 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 5 | 5.19 | 3.30 to 6.28 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 5 / 5 | 5 | 3.76 | 0.28 to 9.89 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 5 / 5 | 5 | 2.45 | 0.28 to 9.89 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 5 / 5 | 1 | 0.00 | -1.37 to 0.44 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 5 / 5 | 4 | 0.43 | -0.82 to 6.17 |

## Missing or invalid runs

None in the supplied results/expected plan.

Prediction benefit is predictive versus reactive journey time. Forecast MAE alone is not evidence of traffic benefit. Modelled CO2 uses the declared emission assumptions.
