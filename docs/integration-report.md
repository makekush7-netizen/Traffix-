# Traffix v1.0 integration report

Updated 2026-10-09; coordinator Kush; branch `feat/kush-demo-polish`.
The final mentor-demo request supersedes the earlier inventory-only stop.

## Built

One offline LIG Square flow: real OpenStreetMap geometry; a deliberately small,
assumed evening-monsoon scenario; 12 differentiated simulated vehicles; QR-bound
phone roles; sharing off by default; phone-only road observations; a two-phone,
45% slowdown / 30 simulated-second rule; a pre-validated alternate route; and a
route change only after the addressed driver accepts and the TraCI worker confirms.
The scene is allowed to show simulation truth. Observation colours and detection
are fed only by admitted phone samples. Unknown roads remain grey.

The DEMO guidance toggle starts off. Bypass capacity comes from a **simulated
installed lane-area sensor**, explicitly disclosed in Advanced. It is not a field
measurement or an additional phone observation. Route B starts beyond the shared
approach; this demo does not establish that it is faster. No estimated saving is
shown. Signal timings are unchanged. Trained models are not enabled.

The simplified dashboard has four event-driven stages, Start/Pause, 1x/2x/4x,
QR invitations, one guidance toggle, offline status, camera controls and reduced
effects. The phone browser app has Join, Driving and Guidance states. Route B
appears only after the applied acknowledgement. The result panel requires complete,
fault-free saved cohorts with matching seed, scenario, network and demand hashes.
A recorded baseline and downloadable walkthrough replay provide labelled backups.

New `sim/assumptions.json` and `sim/README-assumptions.md` were explicitly requested
in the preceding coordinator task. Existing Nandani simulation files, Prakhyat's ML
implementation, frozen contracts and the old harness implementation were preserved.
Coordinator adapters supply the bounded demo. No new dependency was installed.

## Verified locally

- Full regression suite: **164 passed, 2 warnings, 59.55 seconds**. Warnings concern
  the existing Starlette/httpx deprecation and joblib CPU discovery.
- Real SUMO integration tests cover phone frame validation, driver binding,
  observed evidence, default-off guidance, explicit acceptance, worker confirmation,
  wrong vehicle, late/expired actions, toggle-off, stale truth rejection, unknown
  colouring and comparison integrity. Existing tests were not weakened.
- Three consecutive seed-42 fixed-policy runs: **12 scheduled / 12 arrived,
  0 collisions, 0 teleports, 0 unfinished** in every run. End time 409.75 simulated
  seconds; mean cohort journey 239.770833 seconds. Summary: `demo-validation.json`.
- `scripts/demo_check.ps1`: SUMO 1.28 / TraCI, LAN URLs, actual server/configuration,
  and a separate complete headless smoke run all PASS.
- Browser UI testing used two separate phone sessions. Sharing started off; both
  opted in; a sustained real uplink slowdown produced the rider offer; tapping
  Take Route B returned `Route B applied`; only that addressed vehicle rerouted.
- Browser guided run `lig.demo.e7d7e605ae84`: complete saved export, 12 arrived,
  zero collisions/teleports; matched mean journey 234.625 seconds versus recorded
  239.770833 seconds. These are one synthetic pair, not a general savings claim.
- Responsive dashboard checks at 390, 1366 and 1920 pixels showed no horizontal overflow.
  Rendering samples: 55.8 fps at the 1366-pixel live view, 56.3 fps at 1920 pixels,
  and 57.1 fps with reduced effects after completion. These brief samples on this
  laptop are not a benchmark or guaranteed device minimum.
- The full walkthrough download contains the actual four-stage browser story.
  The bundled baseline replay visibly displays RECORDED and disables live actions.
- Incoming Prakhyat branch `ca98c4b`: **19 selected policy/integrity/review-fix tests
  passed in 14.13 seconds** in this Python 3.11 environment. This is not a complete
  clean-environment reproduction of his training/evaluation reports.

The tracked fixed baseline is `backend/harness/data/demo-baseline.json`, labelled
RECORDED BASELINE. Raw local runs and phone-guidance audit JSONL live under ignored
`runs/`. Reproduce them with the commands in `demo-runbook.md`; do not confuse a
tracked summary with newly reproduced raw evidence.

## Still unverified / limitations

Two physical phones over the actual hotspot remain a human acceptance gate.
Browser sessions establish software behaviour, not phone radio reliability or
sunlight usability. Native APK packaging is a separate deliverable. This is a
conservative staged scenario, not calibrated Indian traffic, free-lane behaviour,
real monsoon observation or a city traffic engine. The original larger demand's
known failures remain documented in `lig-validation.md`.

Prakhyat supplied pushed model artifacts and provenance, but his full 197-run
experiment and artifact inference in their intended Python/sklearn environment
were not reproduced here. His reported evaluation does not establish consistent
held-out advantage or a valid matched three-policy headline. Keep those models out
of live control. The historical inventory below retains the detailed evidence gaps.

## Safe claims

- Real LIG geometry, simulated vehicles and assumed traffic conditions.
- Real authenticated phone uplinks can reveal otherwise unobserved roads.
- A simple rule proposes an alternate route; driver consent and server validation
  are required before that simulated vehicle changes route.
- A small repeatable scenario completed three runs without recorded simulation faults.
- Saved complete matched cohorts can be compared for this synthetic demonstration.

## Do not claim

- Measured real-world savings, emissions reduction, calibrated demand or validated
  Indian driving behaviour; a general traffic improvement from one demo pair.
- Route B is faster, an unavailable ETA, or that it avoids the shared approach.
- AI/trained-model decisions, proven predictive benefit, autonomous signal control,
  real GPS sensing, actual roadside sensors, RL readiness or a native production app.
- Two real phones passed until the physical hotspot gate has actually been performed.

---

# Historical Step 1 inventory (superseded by the v1.0 update above)

Inventory date: 2026-10-09. Coordinator: Kush.

**Historical checkpoint at e408bc3: STOP after Step 1.** No incoming code was run, no model was
deserialized, no environment/dependency was installed, and no new test or
simulation was executed. Steps 2–7 remain pending. No application integration,
automatic control, assumptions changes, UI polish or merge to main occurred.

Working branch: `feat/kush-demo-polish`, created from `feat/kush-mobile-app`
at `bd4d26df862d33ae4d8f3a90804dbb6d793b53d5`. The existing untracked
`docs/claude-mvp-handout.md` was preserved. The checked-out app source is unchanged.

Read the planning context at `C:/Users/makew/Downloads/context.md`, `AGENTS.md`,
`OWNERS.md`, and the four requested mobile/validation/Prakhyat documents. The
original context uses old names and scope; the user's current request and later
LIG/mobile approvals take precedence.

## Incoming release

`git fetch --all` found **`origin/feat/prakhyat-lig-work`**, head
`ca98c4bb000c595059084962a17a7331b5d7d671`. It contains six commits beyond
the LIG handoff, changing 58 files. These include code, regression tests,
three model binaries and saved evaluation summaries/provenance.

The old ML foundation, LIG handoff and mobile branch still point to their
specified baselines. This supersedes the earlier handout's statement that no
newer Prakhyat branch was present: that statement described the earlier fetch.

`docs/Prakhyat-LIG-Results.md` still says "No remote branch has been pushed";
that sentence is stale. Fetch proves this release is pushed. Its results remain
author-reported until independently reproduced.

## Claims and evidence inventory

Status vocabulary: **verified** means the stated inventory fact was checked
directly; **unverified** means a claimed runtime/result exists in source or
reports but has not been independently reproduced; **missing** means the
required evidence or integration is absent from the fetched tracked release.

| Item | What it claims | Evidence found | Status |
|---|---|---|---|
| New pushed work | Six commits after the agreed handoff | Fetched branch head and Git log; exact commits below | verified |
| Model binaries | Three horizon artifacts supplied intact | Git blob byte counts and SHA256 values match model manifest; no deserialization | verified |
| Model provenance | Genuine SUMO training, fixed-policy labels, 96 runs, 299,860 dataset rows | `manifest.json` declares `data_source: sumo`; `run-provenance.json`, data-integrity JSON and training code exist; raw training dataset is not tracked | unverified |
| Evaluation integrity repair | Collisions, teleports, invalid or missing integrity cannot produce valid headlines | New `eval/integrity.py`; collection/report/merge changes; new regression tests | unverified |
| Irregular history fix | Bracket the history boundary without requiring an exact timestamp | `ml/forecast.py` change and `tests/test_lig_review_fixes.py` | unverified |
| Ordinary-flow stability | Seeds 42/43/44 complete without collisions or teleports | Freeze/results docs report 145/142/157 journeys, lane-based 500 vehicles/hour and drain bound 2400 s; raw development runs not tracked | unverified |
| Original stress failures | High-demand geometry/sublane faults remain disclosed | Freeze doc explicitly retains failure counts and explains lower-demand conditions; not independently rerun | unverified |
| Batch runner and data separation | Separate observations, offline truth, trips, lifecycle and diagnostics | `eval/lig_runner.py`, registry/pipeline modules and export tests exist; genuine raw output planes are absent from Git | unverified |
| Declared seed partitions | Manifest lists train 100–107, validation 200–202, test 300–304 | Parsed manifest arrays are pairwise disjoint; this checks declarations, not actual fitting behavior | verified |
| Feature causality | No truth, future incident schedule or TraCI input to ML features | Ten declared feature names, source allowlist/batch separation and integrity tests; execution/data audit deferred | unverified |
| Three-horizon accuracy | Boosting beats persistence/trend on held-out slowdown error | Validation and held-out score JSONs plus target-distribution/warning reports are tracked; dataset/evaluation reproduction pending | unverified |
| Forecast weaknesses | Narrow population and weak incident classification | Results disclose 99.56% severe eligible 180-second targets, 0/3 matched jam episodes and false alerts; underlying output not reproduced here | unverified |
| Policy comparison | 197 complete runs, 29,332 experimental journeys; reactive gains in obstruction; no consistent predictive benefit | Detailed test/validation comparison JSON/Markdown, ablation, freeze and roadworks detail files | unverified |
| Control guards | Bounded extensions/diversions, observed downstream/bypass evidence, identity binding | `backend/harness/policy.py` plus policy/integrity/selection tests; no live-control permission granted | unverified |
| Incoming test result | Author reports 176 passing tests in a fresh Python 3.12 environment | Results doc gives command, count, warning and duration; no independent run in this step | unverified |
| Full raw experiment evidence | Reproduce every dataset/trip/lifecycle/diagnostic record locally | No tracked `runs/lig-training`, `runs/lig-response` or `runs/lig-data` trees; author says ignored raw runs remain on his machine | missing |
| Same-run physical-phone integration | Feed authenticated validated phone samples into new worker intelligence | Queue boundary `HarnessEngine.accept_validated_probe()` documented; incoming release says coordinator wiring is still needed | missing |
| Physical two-phone gate / incoming visual QA | Devices and screens checked end to end | Incoming report explicitly leaves physical integration and visual browser QA unverified; mobile baseline has browser tests only | missing |
| Indian parameter provenance registry | Values with observed/published/assumed provenance and field collection | New configuration documents synthetic values; requested `sim/assumptions.json` and field-observation template are absent | missing |

## What the results say — not independently validated here

- Conservative ordinary flow uses lane-based movement at 500/hour; 750/hour is
  a separate experimental condition. This is not repair/calibration of the
  original high-demand sublane network.
- The author reports 96 fixed runs, 96 response runs and five ablations. Batch
  sensing and 60% compliance are **emulated**, not physical-phone participation.
- Boosting at 180 s is selected by validation MAE. Reported held-out MAE is
  0.01713 versus persistence 0.08554 and trend 0.18128, on a narrow imbalanced
  eligible population. This is not proof of reliable clear-to-jam prediction.
- Reported predictive policies show no consistent journey benefit over reactive
  policies. Ordinary obstruction reactive-versus-fixed median gain is reported
  as 3.76%; this is a synthetic experimental result awaiting reproduction.
- CO2 uses unvalidated SUMO proxies, including a petrol proxy for e-rickshaws.
  No field calibration, measured Indore emissions or real-world saving is established.

## Integration hazards and Step 2 preparation

No integration choice is approved at this checkpoint. The following need review:

1. The new work branches from `a7978da`, before the mobile bridge. Overlapping
   paths are listed below. Preserve existing authenticated routes and probe
   checks; do not replace the app with the incoming older HTTP/WebSocket layout.
2. Our mobile map uses numeric `edge.lig.<index>` aliases; the incoming registry
   uses approach/exit aliases such as `edge.lig.approach.0`. These are not
   interchangeable. Same-run bindings, reference speeds and frame aliases must
   agree before forwarding accepted samples to the worker.
3. Incoming `set_autonomy` is a new behavior. It stays disabled/unintegrated until
   the requested guard/evidence checks and user confirmation. Emulated inputs
   must never silently become phone observations.
4. Local baseline is Python 3.11.0 / scikit-learn 1.9.0. Incoming artifacts and
   requirements expect Python 3.12 / scikit-learn 1.9.1. Exact-version checks must
   remain active. A separate clean environment is needed for Step 2; no package
   was added or installed in this step.
5. `ml/requirements-training.txt` newly declares `httpx==0.28.1`. Flag this
   dependency change for approval before adopting it, per the user's rule.
6. Four existing test files add explicit zero collision/teleport fixture metadata.
   No existing assertion was removed in those diffs. The stated rationale is
   stricter integrity evidence; Step 2 must check missing/invalid evidence remains
   covered rather than merely accepting easier fixtures. We changed no tests.
7. Raw data must be supplied or regenerated in Step 2 before treating published
   metrics as reproduced. Do not deserialize model artifacts during inventory.

## Verification commands used in Step 1

All Git commands use the checked workspace's `safe.directory` setting:

```text
git switch -c feat/kush-demo-polish feat/kush-mobile-app
git fetch --all
git for-each-ref refs/remotes/origin
git log --reverse --format=<hash and subject> <baseline>..<remote>
git diff --name-status a7978da origin/feat/prakhyat-lig-work
git diff --numstat a7978da origin/feat/prakhyat-lig-work
git cat-file -s <remote>:<path>
git show <remote>:<path>
git ls-tree -r --name-only origin/feat/prakhyat-lig-work
```

Model checksums were computed from Git blob bytes with Python's standard-library
SHA256. Evidence was inspected as text/JSON. Detailed machine inventory is saved
locally at ignored `runs/demo-step1-inventory.json`; the report below retains the
complete branch/commit/file/binary inventory without relying on that ignored file.

## Remote branches and commits relative to the three baselines

`A..B` means commits reachable from B but not A. For divergent histories this
does not mean chronological work added after A; ancestry is explicitly marked.
`origin/HEAD` is a symbolic pointer to main, not an additional branch.

| Remote branch | Head | New vs d2202bd | New vs a7978da | New vs bd4d26d |
|---|---|---:|---:|---:|
| `origin/feat/kush-lig-harness` | `1fb808772729236e26186baf21217ca8a8ac6663` | 4 | 0 | 0 |
| `origin/feat/kush-ml-review` | `9058d568e6571ef2d85ae2e7388a27ba64b03d26` | 5 | 0 | 0 |
| `origin/feat/kush-mobile-app` | `bd4d26df862d33ae4d8f3a90804dbb6d793b53d5` | 7 | 1 | 0 |
| `origin/feat/kush-sim-validation` | `2a63e4e8cc9c7280dec641a758a2b3235ccee79c` | 2 | 0 | 0 |
| `origin/feat/nandani-sim` | `5e7b35e764504f0ee582d7e2a0cee5a2ac7f2eab` | 1 | 0 | 0 |
| `origin/feat/prakhyat-lig-handoff` | `a7978da9e3df35a612814b7e8d1b47334d6a7f0a` | 6 | 0 | 0 |
| `origin/feat/prakhyat-lig-work` | `ca98c4bb000c595059084962a17a7331b5d7d671` | 12 | 6 | 6 |
| `origin/main` | `310ca324930a60116506c7d8a17a3256ccad890a` | 0 | 0 | 0 |
| `origin/prakhyat/ml-foundation` | `d2202bda5c1ef633a08395252789be766a2f6c22` | 0 | 1 | 1 |

### origin/feat/kush-lig-harness

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`, `6e729f0`, `1fb8087`.
- Since `a7978da` (LIG handoff; divergent or older branch): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/feat/kush-ml-review

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`, `6e729f0`, `1fb8087`, `9058d56`.
- Since `a7978da` (LIG handoff; divergent or older branch): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/feat/kush-mobile-app

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`, `6e729f0`, `1fb8087`, `9058d56`, `a7978da`, `bd4d26d`.
- Since `a7978da` (LIG handoff; baseline is ancestor): `bd4d26d`.
- Since `bd4d26d` (mobile app; baseline is ancestor): none.

### origin/feat/kush-sim-validation

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`.
- Since `a7978da` (LIG handoff; divergent or older branch): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/feat/nandani-sim

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`.
- Since `a7978da` (LIG handoff; divergent or older branch): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/feat/prakhyat-lig-handoff

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`, `6e729f0`, `1fb8087`, `9058d56`, `a7978da`.
- Since `a7978da` (LIG handoff; baseline is ancestor): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/feat/prakhyat-lig-work

- Since `d2202bd` (ML foundation; divergent or older branch): `5e7b35e`, `2a63e4e`, `6e729f0`, `1fb8087`, `9058d56`, `a7978da`, `50f3f4d`, `4c75dac`, `5ce2691`, `2f390f8`, `92eeae1`, `ca98c4b`.
- Since `a7978da` (LIG handoff; baseline is ancestor): `50f3f4d`, `4c75dac`, `5ce2691`, `2f390f8`, `92eeae1`, `ca98c4b`.
- Since `bd4d26d` (mobile app; divergent or older branch): `50f3f4d`, `4c75dac`, `5ce2691`, `2f390f8`, `92eeae1`, `ca98c4b`.

### origin/main

- Since `d2202bd` (ML foundation; divergent or older branch): none.
- Since `a7978da` (LIG handoff; divergent or older branch): none.
- Since `bd4d26d` (mobile app; divergent or older branch): none.

### origin/prakhyat/ml-foundation

- Since `d2202bd` (ML foundation; baseline is ancestor): none.
- Since `a7978da` (LIG handoff; divergent or older branch): `d2202bd`.
- Since `bd4d26d` (mobile app; divergent or older branch): `d2202bd`.

### Commit subjects (unique commits in the comparisons)

| Commit | Subject |
|---|---|
| `5e7b35e764504f0ee582d7e2a0cee5a2ac7f2eab` | feat(sim): Nandani's SUMO network, demand, ID registry, and validation suite |
| `2a63e4e8cc9c7280dec641a758a2b3235ccee79c` | Audit Nandani SUMO handoff and record integration blockers |
| `6e729f01935c01e070bb21168eebd70b70953b45` | Build offline LIG Square SUMO harness with 3D browser controls |
| `1fb808772729236e26186baf21217ca8a8ac6663` | Preserve imported asset bytes across Windows checkouts |
| `9058d568e6571ef2d85ae2e7388a27ba64b03d26` | Audit Prakhyat ML handoff and reproduce evaluation defects |
| `a7978da9e3df35a612814b7e8d1b47334d6a7f0a` | Bundle LIG harness and ML foundation with Prakhyat work brief |
| `bd4d26df862d33ae4d8f3a90804dbb6d793b53d5` | Build mobile driver app and authenticated LIG phone bridge |
| `50f3f4d52798e06ec65aca6fc1ca5306789cfc29` | Preserve simulation integrity and bracket forecast history windows |
| `4c75dac49fc52df5f63468cd3dcb2640dd8fb455` | Freeze conservative ordinary LIG flow and preserve bounded drain diagnostics |
| `5ce269146c5a28627d08a5f5f55437056e9ce398` | Export causal LIG observations and isolated SUMO batch evidence |
| `2f390f84f6131ac66f381826df7754b5ae6b3c9d` | Integrate guarded LIG policies and validation-only forecast analysis |
| `92eeae12b40cb061e947026f5d58c817750f7b4f` | Bind experiment execution identities and reject teleport evidence |
| `ca98c4bb000c595059084962a17a7331b5d7d671` | Publish genuine SUMO model artifacts and honest held-out LIG results |
| `d2202bda5c1ef633a08395252789be766a2f6c22` | ml-foundation |

## Changed files versus a7978da

Change codes: A added, M modified. Sizes are committed Git blob bytes.

| Change | Path | Bytes |
|---|---|---:|
| M | `backend/harness/app.py` | 3,481 |
| A | `backend/harness/configuration.py` | 3,168 |
| M | `backend/harness/engine.py` | 22,403 |
| A | `backend/harness/policy.py` | 6,747 |
| M | `backend/harness/static/index.html` | 7,641 |
| M | `backend/harness/static/main.js` | 22,337 |
| A | `docs/Prakhyat-LIG-Implementation-Plan.md` | 2,302 |
| A | `docs/Prakhyat-LIG-Results.md` | 12,392 |
| A | `docs/Prakhyat-LIG-Runbook.md` | 5,749 |
| A | `docs/Prakhyat-LIG-Simulation-Freeze.md` | 2,850 |
| M | `eval/collect.py` | 3,273 |
| M | `eval/compare.py` | 7,099 |
| A | `eval/integrity.py` | 2,350 |
| M | `eval/jam_gate.py` | 4,243 |
| A | `eval/lig_analysis.py` | 11,898 |
| A | `eval/lig_pipeline.py` | 5,359 |
| A | `eval/lig_registry.py` | 1,956 |
| A | `eval/lig_runner.py` | 13,364 |
| M | `eval/merge.py` | 2,881 |
| M | `eval/report.py` | 5,519 |
| A | `ml/artifacts.py` | 1,197 |
| M | `ml/forecast.py` | 5,558 |
| M | `ml/requirements-training.txt` | 257 |
| A | `models/lig-v1/evidence/data-integrity.json` | 57 |
| A | `models/lig-v1/evidence/policy-freeze.json` | 310 |
| A | `models/lig-v1/evidence/roadworks-reactive-detail.json` | 1,391 |
| A | `models/lig-v1/evidence/selection.json` | 514 |
| A | `models/lig-v1/evidence/test-forecast-scores.json` | 5,883 |
| A | `models/lig-v1/evidence/test-policy-comparison.json` | 678,687 |
| A | `models/lig-v1/evidence/test-policy-comparison.md` | 3,741 |
| A | `models/lig-v1/evidence/test-sensor-ablation.json` | 4,799 |
| A | `models/lig-v1/evidence/test-target-distribution.json` | 2,814 |
| A | `models/lig-v1/evidence/test-warning-scores.json` | 64,861 |
| A | `models/lig-v1/evidence/validation-baseline-jam.json` | 649 |
| A | `models/lig-v1/evidence/validation-policy-comparison.json` | 411,382 |
| A | `models/lig-v1/evidence/validation-policy-comparison.md` | 3,738 |
| A | `models/lig-v1/evidence/validation-trigger-scores.json` | 231,034 |
| A | `models/lig-v1/forecast-120.joblib` | 194,521 |
| A | `models/lig-v1/forecast-180.joblib` | 194,041 |
| A | `models/lig-v1/forecast-300.joblib` | 194,793 |
| A | `models/lig-v1/manifest.json` | 1,175 |
| A | `models/lig-v1/run-provenance.json` | 40,889 |
| A | `models/lig-v1/validation.json` | 707 |
| M | `scripts/check_lig.py` | 2,505 |
| A | `scripts/run_lig_ml.py` | 1,924 |
| M | `tests/test_audit_review.py` | 3,450 |
| M | `tests/test_collection.py` | 1,921 |
| M | `tests/test_evaluation.py` | 3,009 |
| A | `tests/test_lig_batch.py` | 1,054 |
| A | `tests/test_lig_collection.py` | 1,048 |
| A | `tests/test_lig_configuration.py` | 1,432 |
| A | `tests/test_lig_exports.py` | 2,459 |
| A | `tests/test_lig_harness_ml.py` | 1,165 |
| A | `tests/test_lig_ml_integrity.py` | 2,677 |
| A | `tests/test_lig_policy.py` | 1,548 |
| A | `tests/test_lig_review_fixes.py` | 2,636 |
| A | `tests/test_lig_selection.py` | 534 |
| M | `tests/test_merge.py` | 1,010 |

## Model binary integrity

Matching a manifest checksum verifies transport integrity, not model accuracy or training provenance.

| Binary | Bytes | SHA256 | Matches manifest |
|---|---:|---|---|
| `models/lig-v1/forecast-120.joblib` | 194,521 | `9291cc6eede8aa2a0748897ba78c07153c07eea07202076812682754d3900e0a` | yes |
| `models/lig-v1/forecast-180.joblib` | 194,041 | `0b8b2c739888c693ff627eaaa5841d1530bbe153fd09d70fa4ae74a207fc46aa` | yes |
| `models/lig-v1/forecast-300.joblib` | 194,793 | `1d2c6515127ed7caaa997e89416b908d8412eb8ee81ba5cc1885fcdbebfe479b` | yes |

Total model binary bytes: 583,355. No other added/modified binaries were reported by Git numstat.

## Paths changed by both mobile and incoming work

- `backend/harness/app.py`
- `backend/harness/engine.py`
- `backend/harness/static/index.html`
- `backend/harness/static/main.js`

## Checkpoint outcome

Step 1 is complete. The incoming work exists and its model bytes match the
manifest. Its runtime behavior, training provenance, stability, guard behavior
and evaluation results are not independently verified at this checkpoint.
Proceed only when Kush asks to continue to Step 2. No behavior change is approved.
