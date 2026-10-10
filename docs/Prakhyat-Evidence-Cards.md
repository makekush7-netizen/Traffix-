# Prakhyat's evidence cards and ML report draft

**Status: templates only. No real SUMO runs/results are available.** Replace fields only with saved genuine outputs; attach source paths and label live/recorded/simulated. Urvashi owns final visual layout.

## Card 1 — We know what we can observe

“The market road has no fixed detector. The system receives only accepted phone/probe samples and permitted boundary measurements.”

Show: physical phones currently reporting `[unavailable]`, unique fresh probes `[unavailable]`, sample age `[unavailable]`, observed coverage `[unavailable]`. Stop sharing and show evidence expire. Source: authoritative gateway/snapshot log. The role-play vehicle position is simulated; the uplink is a real phone interaction.

## Card 2 — Forecasting is tested against simple baselines

Show a table of persistence/trend/gradient boosting × 120/180/300 seconds. Values: held-out macro-seed MAE `[unavailable]`, eligible row count `[unavailable]`, seeds `[unavailable]`.

Source: `eval.forecasts` JSON from real fixed-policy runs. Model inputs are current/past permitted observations; targets are average slowdown in the 30-second window ending at each horizon. Entire seeds are partitioned; no test/demo seed enters training or tuning. Forecasts stop authorizing further action after intervention starts.

## Card 3 — Did prediction help beyond reaction?

Show fixed/reactive/predictive mean scheduled-to-arrival journey `[unavailable]`, p95 `[unavailable]`; predictive-versus-reactive paired gain median/range `[unavailable]`; wins/valid/attempted seeds `[unavailable]`.

Source: raw trip exports → collector → paired comparison with expected plan. A gain is `100 × (reference - response) / reference`. Negative values mean worse outcomes. Missing, removed, teleported or unfinished cohorts cannot produce a headline. Forecast accuracy alone does not establish traffic benefit.

## Card 4 — Did phone coverage change the outcome?

“Same rain scenario, same policy, same scheduled traffic. Only permitted market probe participation changes.”

Boundary-only versus boundary-plus-three-probes: journey change `[unavailable]`, valid/attempted seeds `[unavailable]`, observation coverage `[unavailable]`. Source: `eval.ablation` report plus coverage logs. Batch probes are labelled emulated; this comparison does not claim that three physical phones measure every real road user.

## Card 5 — Climate and network burden

Whole-cohort modelled CO2 `[unavailable]` kg and paired change `[unavailable]`; fleet class/proxy assumptions `[unavailable]`. Network queue burden `[unavailable]` m·s; bypass burden/peak `[unavailable]`; applied signal actions/reroutes `[unavailable]`.

Source: complete trip emissions, declared assumptions, stable truth queue edge set and authoritative action log. This is uncalibrated model output, not measured India emissions or a real-world climate benefit. Queue burden integrates logged sampled queue lengths; state the logged edge set and sampling convention.

## Card 6 — Reliability and limits

Independent software checks: **101 tests passed**, fixture pipeline and CLI workflow verified. Real SUMO/phones/controller checks: **pending**. Jam misses, false alerts per network simulated hour, warning lead and delay: `[unavailable]`.

Current thresholds are starting values. Claims about reducing congestion, CO2 or winning over reactive control are unavailable until real experiments finish. If the result is negative, retain it and explain the tested limit.

## Short-report ML/evaluation section

1. **Data:** identify actual SUMO version, network/demand/incident checksums, fleet assumptions, scenario/demand levels, probe masks/schedules and seed partitions. Include raw-export locations.
2. **Observations:** describe probe aggregation, fixed allowlist, freshness/coverage rules and the separation between permitted online inputs and offline full-state truth. State the independent jam-label definition.
3. **Methods:** describe detector guards, persistence, clipped trend and three gradient-boosting regressors; feature allowlist/version; identical future-window targets; validation-only threshold/horizon choice; first-response forecast limitation.
4. **Experiment:** fixed/reactive/predictive with identical shared bounds/information/cohorts; whole-seed held-out testing; expected jobs and missing/invalid outcomes; sensor ablation; optional compliance grid.
5. **Results:** populate the six cards from saved genuine outputs. Report every denominator, loss and unavailable number. Add ordinary-red/no-incident sanity checks and the genuine baseline-jams gate.
6. **Limits:** synthetic corridor, sparse probe sampling, emission proxy assumptions, uncalibrated road behavior and prediction benefit conditional on the tested scenarios. Separate software tests from simulation experiments and physical-phone connectivity tests.
