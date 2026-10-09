# Prakhyat LIG handback — actual build and experiment results

Work branch: `feat/prakhyat-lig-work`, based on handoff `a7978da`.
All implementation is in an isolated clone; the original Desktop folder is untouched.
Code, trained models and evidence are ready for review. No remote branch has been pushed.

## What was completed

| Handoff task | Delivered |
|---|---|
| 1 — correctness | Invalid/colliding/teleported metadata cannot produce valid headlines; missing integrity stays explicit; irregular forecast-history boundary fixed; regressions added. |
| 2 — ordinary flow | Conservative lane-based 500/hour profile drains on development seeds 42/43/44; bounded drain, original geometry/join and six types retained; original failures remain visible. |
| 3 — genuine batch | LIG aliases from actual network; executor-compatible headless worker; separate permitted observations/offline truth; explicit demand, lifecycle, trips, CO2 and event exports. |
| 4 — training | 96 fixed SUMO runs, three fitted HistGradientBoosting models, disjoint seed splits, validation-only selection, all three held-out comparisons and provenance/checksums. |
| 5 — integration/evidence | Harness observation/model labels; bounded signal/diversion rules; autonomy pause; immediate no-action forecast shutdown; 96 response runs; five sensor-ablation runs; cold live HTTP startup; honest results. |

Scope preserved: shared `contracts/`, Nandani's `sim/`, Urvashi's `web/`, original
phone backend and its acceptance tests are unchanged. Authorized harness paths
contain the LIG integration. Physical phone gateway wiring is still Kush's work.

## Simulation integrity and the ordinary-flow ruling

The original 1,900/hour sublane everyday case reproduced 255/500 arrivals,
8 collision involvements at 1,200 s. Conservative sublane at the same rate
still failed. Lane-based 1,900/hour still produced two collision involvements.
We therefore do **not** claim the high-demand imported network is repaired.

Ordinary flow is explicitly reduced to 500/hour, with 750/hour a separate
experimental demand. Development seeds 42/43/44 yielded 145/142/157 scheduled
and arrived, zero collisions, zero teleports; drains ended at 1488.25/1556.25/
1502.50 s. All original route choices and vehicle classes remain. No faulty
vehicle removal, teleport shortcut or disabled collision check was used.
Full assumptions and failed conditions: [simulation freeze](Prakhyat-LIG-Simulation-Freeze.md).

The final experiment contains **197 distinct runs**: 96 fixed + 96 responding
(36 validation, 60 test) + 5 boundary-only ablations. All 197 completed their
scheduled cohorts: **29,332 scheduled and arrived vehicle journeys**, zero
recorded collision involvements and teleports. These are repeated experimental
journeys, not unique real-world drivers. Smoke/development runs are additional.

## Dataset and model provenance

- 299,860 causal five-second dataset rows. All 96 fixed runs were accepted;
  zero corrupted runs were silently discarded.
- Training seeds 100–107; validation 200–202; final test 300–304; seed 42 held
  for the demo. Every partition contains all three LIG scenarios and two demands.
- Forecasts target the full-state slowdown mean across the 30-second window
  ending at t+120/180/300. Empty roads/missing future bins stay missing.
- Features: current/30/60/120-second slowdown, 60-second slope, distinct probes,
  sample age, permitted fixed queue ratio, history span and fresh fraction.
  No future incident schedule, truth column or direct TraCI access enters ML.
- Python 3.12.14, SUMO 1.28.0, scikit-learn 1.9.1; feature version 2.
- Dataset SHA256: `0fe29505e3f4735177ab8943da7950a5f466a0e36b2af37ce932ac7b4f865d48`.
  The saved dataset file's checksum matches the training manifest.
- Manifest: `models/lig-v1/manifest.json`; checksums and all contributing run
  manifest hashes are saved. Fixture models remain rejected for control.

| Horizon | Training rows | Validation rows | Validation boosting / persistence / trend MAE | Test boosting / persistence / trend MAE | Eligible labelled test rows / all test rows |
|---|---:|---:|---|---|---|
|120 s|17,775|6,778|0.02177 / 0.09086 / 0.18405|0.02312 / 0.09600 / 0.19560|10,608 / 88,640 (11.97%)|
|180 s|18,501|7,204|0.01609 / 0.07388 / 0.15727|0.01713 / 0.08554 / 0.18128|11,126 / 88,640 (12.55%)|
|300 s|14,295|5,252|0.02625 / 0.09174 / 0.23527|0.02782 / 0.09756 / 0.24907|8,376 / 88,640 (9.45%)|

MAE uses slowdown on a 0–1 scale. These fractions combine future-label
availability and online eligibility; they are not a physical phone uptime rate.
All per-seed MAEs, coverage and confusion counts are in the evidence JSON.

Validation selected **boosting, 180 s**, reactive danger 0.8/persistence 20 s,
predictive danger 0.6/persistence 10 s. The selection/model identities are bound
before execution, and resumed runs reject changed artifacts/configuration.
Validation policy comparisons were saved before the final response test runs.

### Forecast/detection weaknesses — do not hide these

99.56% of eligible 180-second test targets are already severe slowdown.
A training-mean constant predictor scores 0.03155 test MAE; boosting scores
0.01713. This is a narrow, strongly imbalanced conditional population. Low MAE
does **not** establish reliable prediction of clear-to-jammed transitions.

The strict independent jam labels produced only three test episodes and five
positive ticks. First-alert/event matching scored **0/3 matched episodes** for
both policies. False first alerts: reactive **6.93 per simulated network hour**;
predictive **9.78/hour**. Warning lead time is unavailable.
The full-timeline reactive detector covered all five positive ticks but also
8,386 negative ticks: precision approximately **0.060%**, recall 100% on this
tiny positive set. Its event-onset metric still matched 0/3 because warnings
started outside the episode window. This detector is **not validated for real
traffic**. Journey gains below demonstrate bounded queue management in these
synthetic conditions, not a dependable real-world jam classifier.

## Frozen held-out policy results

Each row has five complete, integrity-valid matched seeds. Positive percentages
mean faster whole-cohort journeys, including entry waiting and detours. Values
are medians of paired per-seed percentages, not percentages of pooled means.

| Scenario | Demand/hour | Reactive vs fixed % | Predictive vs fixed % | Predictive vs reactive % | Reactive wins / 5 |
|---|---:|---:|---:|---:|---:|
|Everyday|500|0.00|-0.75|-0.55|0|
|Everyday|750|0.61|1.04|0.00|4|
|Gradual rain surrogate|500|0.00|-0.47|0.00|2|
|Gradual rain surrogate|750|3.28|3.28|0.00|4|
|Obstruction surrogate|500|**3.76**|2.45|0.00|**5**|
|Obstruction surrogate|750|**7.22**|7.22|0.00|**5**|

There were no missing runs, invalid runs or collection errors in the final
comparison. All negative outcomes remain in the JSON/Markdown reports.
Prediction adds **no consistent demonstrated benefit** over reactive control.
Reactive is the recommended demo policy; trained forecasts can still be shown.
Different validation-selected alert thresholds are part of the compared
policies, so these comparisons do not isolate the model from all threshold effects.

For ordinary roadworks, reactive gains range **0.28%–9.89%**, median 3.76%,
five wins. Modeled CO2 reduction has median **1.39%**, range **−0.82% to 6.17%**;
four of five seeds reduce modeled CO2. Actual per-seed seconds/kg are saved in
`evidence/roadworks-reactive-detail.json`; seed 300: 377.23 → 363.04 s mean
journey and 107.54 → 106.05 kg modeled CO2.

Across the responding/ablation runs, event logs contain **358 signal extensions
and 428 applied diversions**. These are actual applied simulation actions,
not promised guidance. Guards preserve phase clearance, cap green at 40 s,
extend at most 5 s once per serving phase, require observed downstream capacity,
and restrict diversions to permitted connected routes with an observed bypass.
Compliance is explicitly emulated at 60%; diversion acceptance is not phone acceptance.

## Sensor-poor road evidence

The monitored LIG approach has no fixed detector in either mask. Both retain
simulated boundary capacity detectors. On five held-out ordinary-roadworks
seeds, boundary-only focus freshness is **0%**. Deterministic 60% emulated
probe assignment yields focus freshness **48.54%–79.77%**; two-fresh-probe
eligibility occurs **35.77%–72.52%** of ticks. Whole-cohort reactive journeys
improve by median **3.76%** versus boundary-only, five wins.

This supports the **emulated probe coverage** demonstration. There were **zero
authenticated physical phone uplinks** in these experiments. Three handsets
cannot be assumed to reproduce 60% participation. Phone mode stays unknown
on the focus edge until same-run authenticated validated uplinks arrive.

## CO2 assumptions

Tripinfo `CO2_abs` is mg and converted to kg; final values use the complete
scheduled cohort. SUMO reports these actual default classes:

| Type | Recorded class |
|---|---|
|Car / auto / e-rickshaw|HBEFA4/PC_petrol_Euro-4|
|Motorcycle|HBEFA4/MC_4S_gt250cc_preEuro|
|Bus|HBEFA4/UBus_Std_gt15-18t_Euro-VI_A-C|
|Delivery van|HBEFA4/LCV_diesel_N1-III_Euro-6ab|

The e-rickshaw petrol proxy is especially unrealistic. All these defaults are
unvalidated for the represented Indian fleet. Report **modeled proxy CO2 under
declared assumptions**; never call this measured Indore emissions or a calibrated
climate saving. The assumptions are identical across matched policies.

## Verification and launch

The fresh combined environment passed **176 tests**, one upstream
Starlette/httpx deprecation warning, 163.43 s. Exact command:

```powershell
python -c "from scripts.verify_nandani import prepare_environment; prepare_environment(); import pytest; raise SystemExit(pytest.main(['-q','--basetemp=.cache/pytest-reviewed','--tb=short']))"
```

The one independent review found four important issues; six regression cases
reproduced them before fixes. Teleport evidence, model/selection binding,
execution-safe resumption and missing-run reports are now covered. No deferred
minor findings remain. No second review was used as a substitute for tests.

Cold real HTTP check: **200, ready=True, t=120 s, emulated, SUMO-trained**.
The browser tool and cross-command localhost requests timed out; visual browser
QA is **unverified**. The successful HTTP probe ran with server/client in one
execution environment. Use the launch command from a normal local terminal:

```powershell
python scripts/run_lig_ml.py --probe-mode emulated --policy reactive --scenario roadworks --models models/lig-v1 --selection models/lig-v1/evidence/selection.json
```

Open `http://127.0.0.1:8001`. The selected source is labelled EMULATED. Use
8x playback, show the sensor-poor approach's observations, then signal/diversion
audit events, and pause autonomy. The geometry/rendered vehicles are simulation
truth, not automatic phone measurements. CLI batch-profile scenes use the
declared 500/hour ordinary rate; high-demand stress diagnostics use the raw
`check_lig.py` presets. See [runbook](Prakhyat-LIG-Runbook.md) for regeneration.

## Handoff and remaining team work

Kush must connect the existing authenticated phone gateway to the SAME LIG
run/frame producer and logical registry, then test real devices and reconnects.
`HarnessEngine.accept_validated_probe()` is ready as the queue boundary; do not
feed the separate port-8000 fixture simulation into port-8001 LIG. No public
unauthenticated ingest endpoint was added. Agent/API tests verify zero-uplink
honesty, not a completed physical phone integration.

Nandani does not need to supply new input to reproduce this LIG pipeline.
Original high-demand geometry/priority-junction failures, realistic sublane
mixed traffic, fleet calibration, reliable incident classification and broader
forecast generalization remain limitations. Do not retune thresholds against
these released test seeds and present the same seeds as fresh held-out proof.

Models/evidence are committed for sharing; raw ignored `runs/lig-*` data remain
in the working clone. Regeneration commands produce the complete audit planes.
Existing raw runs from before execution-identity enforcement are not silently
upgraded by resume; use a new run root if rerunning those fixed batches.
