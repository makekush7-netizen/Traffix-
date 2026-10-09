# Prakhyat LIG implementation plan

Spec: `docs/prakhyat-work.md`, handoff commit `a7978da`.
Work branch: `feat/prakhyat-lig-work`. Preserve contracts, phone backend, sim/ and web/.

1. Repair integrity accounting and bracketed forecast-history eligibility.
   Tests: arrived-but-invalid/colliding/missing-integrity exports, clean exports,
   irregular history, excessive gaps, stale current samples. Verify the entire suite.
2. Reproduce LIG faults, save diagnostics, repair the responsible signal/vehicle
   assumptions without disabling collision checks/teleport safeguards, add bounded
   drain and reproducible configuration. Validate development seeds and preserve stress faults.
3. Add deterministic LIG registry/demand/export/headless batch adapters. Freeze
   reference speeds, allowlisted observation masks and emulated-probe assignments.
   Export independent truth, full scheduled lifecycle/trips, diagnostics and manifests.
   Tests: no probes means unknown, same seed means same demand, masks, clocks,
   collision rejection and compatibility with existing data transforms.
4. Freeze LIG scenario/demand/seed plans, generate actual fixed-policy SUMO data,
   fit three boosting models, tune validation only and evaluate held-out data
   against persistence/trend. Preserve raw evidence, versions, hashes and losses.
5. Integrate intelligence and matched bounded policies in the owned harness,
   preserve browser controls and expose source/model/coverage/abstention labels.
   Run development policy checks, freeze on validation, then held-out comparisons.
   Deliver launch/batch/train/evaluate commands, results and explicit limitations.

Pre-flight: collect/report share cohort validity; both must use one integrity merge.
Forecast history gating is shared by dataset eligibility and harness integration.
Runner metadata/logs must match eval.generate/merge/train and policy fingerprints.
Common policy bounds and observation masks remain identical in A/B/C.

Review focus: hidden-truth leakage; collisions and unfinished cohorts; policies
changing exogenous demand or incident schedules; permissive phase transitions;
fixed references under restrictions; empty roads/missing future bins; lifecycle
and CO2 units; deterministic assignments; held-out leakage; live zero-uplink behavior.
