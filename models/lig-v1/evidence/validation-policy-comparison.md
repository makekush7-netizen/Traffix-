# Paired policy evidence

Positive percentages mean improvement; negative percentages mean worse performance.

Missing, incomplete or invalid runs cannot produce a gain. Supply the expected plan to count entirely missing seeds.

| Scenario | Demand | Source | Compliance | Sensor mask | Metric | Valid / attempted seeds | Wins | Median % | Range % |
|---|---|---|---:|---|---|---:|---:|---:|---:|
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 1 | -0.16 | -0.70 to 1.73 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 2 | 1.39 | -0.26 to 1.73 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 2 | 0.43 | 0.00 to 1.55 |
| lig.everyday | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 3 | 0.91 | 0.04 to 1.58 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 2 | 0.06 | 0.00 to 2.86 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 2 | 0.07 | -0.62 to 6.71 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 2 | 0.07 | -0.69 to 3.96 |
| lig.everyday | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 1 | -0.03 | -0.63 to 5.41 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 3 | 3.41 | 1.43 to 4.48 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 3 | 4.48 | 0.93 to 5.06 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 1 | 0.00 | -0.50 to 1.71 |
| lig.rain | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 3 | 3.37 | 0.86 to 3.38 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 2 | 0.96 | -0.21 to 2.52 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 2 | 0.17 | -0.74 to 6.84 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 1 | -0.53 | -0.80 to 4.43 |
| lig.rain | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 2 | 0.34 | -0.71 to 5.14 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 3 | 6.57 | 6.17 to 8.87 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 3 | 6.57 | 6.17 to 8.87 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 0 | 0.00 | 0.00 to 0.00 |
| lig.roadworks | demand.lig.busy | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 3 | 4.75 | 4.24 to 7.06 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | reactive_vs_fixed_pct | 3 / 3 | 2 | 5.65 | -1.08 to 11.93 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_fixed_pct | 3 / 3 | 2 | 5.65 | -1.08 to 11.93 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_vs_reactive_pct | 3 / 3 | 0 | 0.00 | 0.00 to 0.00 |
| lig.roadworks | demand.lig.ordinary | sumo | 0.6 | mask.lig.probes | predictive_co2_vs_fixed_pct | 3 / 3 | 2 | 3.35 | -1.40 to 9.85 |

## Missing or invalid runs

None in the supplied results/expected plan.

Prediction benefit is predictive versus reactive journey time. Forecast MAE alone is not evidence of traffic benefit. Modelled CO2 uses the declared emission assumptions.
