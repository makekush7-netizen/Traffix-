# Prakhyat ML handoff review

Reviewed `origin/prakhyat/ml-foundation`, commit `d2202bd`, independently on
2026-10-09. Verdict: useful, tested ML/evaluation foundation; **do not merge
the branch as delivered**, and do not use its fixture scores as traffic results.
The running backend and LIG harness were not changed by this review.

## Findings

1. **Merge blocker: deletes other owners' working modules.** Compared with
   `origin/main`, this branch removes `AGENTS.md`, `OWNERS.md`, the existing
   backend, backend acceptance tests, root requirements and coordinator
   runbooks. Restore those files and submit an additive branch containing
   owned ML/evaluation changes. Contracts themselves are retained and their
   examples validate; the problem is the unrelated deletions.

2. **High priority: invalid run evidence is overwritten.**
   `eval/collect.py:26` computes cohort metrics and line 36 expands them after
   manifest metadata. Consequently a manifest with `valid=False` and
   `collisions=2`, with one fully arrived trip and zero teleports, becomes
   `valid=True` and publishes `mean_journey_s=100`. This is a deliberately
   constructed diagnostic fixture, not a SUMO outcome. `eval/report.py:23`
   uses the same overriding pattern. Preserve run-integrity failures in
   addition to cohort completion and teleport checks; suppress final metrics
   and paired improvements for collision-bearing or otherwise invalid runs.
   Add regression cases for completed cohorts with invalid integrity evidence.

3. **Cold-launch test failure.** The documented fresh-clone `python -m pytest
   -q` command gives **74 passed, 27 setup errors** because
   `pyproject.toml:22` sets `--basetemp=.cache/pytest`, while its parent
   `.cache` does not exist. Creating that directory gives **101 passed**.
   Bootstrap it in the documented commands or use a temp-directory location
   that works from a clean checkout.

4. **Forecast gate unnecessarily requires a timestamp exactly 60 seconds ago.**
   `ml/forecast.py:81-82` drops the observation immediately before the window
   boundary, then requires the remaining observations to span the full window.
   Fresh observations at 0,10,15,...,65 seconds have 65 seconds of history and
   a maximum gap of 10 seconds (within the configured 15-second limit), but
   the forecast is marked unusable. Include the observation that brackets the
   boundary, while continuing to reject gaps exceeding the limit. The intended
   exact five-second cadence works; skipping a boundary tick exposes this case.

## What passed

- 101 provided tests after preparing `.cache`; one environment warning about
  physical-core detection. Tested using the coordinator's existing Python
  3.11, NumPy 2.3.5, pandas 3.0.6 and scikit-learn 1.9.0 environment.
- Full independent `eval.pipeline` run: 2,896 observation/dataset rows; three
  freshly trained fixture models; validation and held-out evaluation; reports.
- Zero probe uplinks leaves the market unknown, null slowdown and zero usable
  forecasts. Repeated vehicles, stale data, no-action forecast shutdown after
  intervention, seed partitions and hidden-feature allowlists have tests.
- Independent missing-seed check: two planned seeds with one entirely absent
  correctly reports two attempted seeds and three missing policy runs. An
  initial reading suggested otherwise; the reproduction disproved that concern.
- Fixture models are explicitly prevented from authorizing live control.
  The supplied evidence truthfully states zero executed real SUMO jobs and
  no verified physical-phone integration or traffic/CO2 improvement.

## Integration limitations

These models were trained on artificial slowdown curves. They do not validate
LIG Square traffic, Nandani's original network or congestion-response benefits.
Genuine fixed-policy observation/truth exports, frozen seed partitions,
validation tuning, held-out forecast comparisons and A/B/C policy runs remain.

The first feature set intentionally omits signal-state features and interactions
with neighboring boundary edges; the detector and trigger still use signal
context. This reduction is disclosed in the feature audit and needs evaluation
against persistence/trend on real simulation data.

The package declares Python >=3.12 and pins its own environment, while the
coordinator currently uses 3.11. Source tests pass here, but package installation
and supplied model artifacts require an agreed environment. Model loading
correctly enforces exact scikit-learn versions and checksums; retrain for the
chosen environment rather than bypassing those checks.

## Reproduce

The branch was archived into ignored `runs/prakhyat-review-d2202bd/`, without
checking it out over the working application. Logs:

- `runs/prakhyat-tests-original.txt`: clean-checkout test failure.
- `runs/prakhyat-tests-prepared.txt`: 101 passing tests.
- `runs/prakhyat-fixture-pipeline.txt`: independent full fixture run.
- `runs/prakhyat-independent-audit/verification.json`: diagnostic edge cases.

```powershell
.venv/Scripts/python.exe scripts/verify_prakhyat.py --snapshot runs/prakhyat-review-d2202bd --output runs/prakhyat-independent-audit
```

The audit helper does not change Prakhyat's source. Its synthetic manifests
exercise invalid-input handling and must not be presented as traffic evidence.
