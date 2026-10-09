# Ownership (one owner per path; do not edit paths you do not own)

Kush's 2026-10-09 mobile task also assigns `web/src/mobile/` and the phone-to-LIG
integration to the coordinator. The remainder of `web/` stays with Urvashi.

| Path | Owner |
|---|---|
| `contracts/` | Coordinator only (changes need coordinator approval) |
| `backend/`, `scripts/`, `tests/test_sessions.py`, `tests/test_worker.py`, `tests/test_probes.py`, `tests/test_control.py`, `tests/test_events.py`, `tests/test_replay.py` | Coordinator |
| `sim/` | Nandani |
| `ml/`, `eval/`, `models/`, `tests/test_detection.py`, `tests/test_forecast.py`, `tests/test_cohort.py`, `tests/test_generate.py`, `tests/test_compare.py` | Prakhyat |
| `web/` | Urvashi |
| `docs/` | Everyone (append, do not rewrite others' files) |

Branches: `main` is always runnable. Work on `feat/<owner>-<module>` and merge small, often.

For the LIG handoff approved by Kush on 2026-10-09, Prakhyat also owns changes
needed for simulation repair, exports and ML integration in `backend/harness/`,
`scripts/build_lig.py`, `scripts/check_lig.py`, new LIG batch/training scripts,
and `tests/test_harness.py`. The imported ML/evaluation tests belong to Prakhyat;
the pre-existing phone/backend tests keep their coordinator owner. This scoped
delegation preserves `sim/`, `web/`, shared contracts and the phone backend.


## Kush's final mentor-demo scope, 2026-10-09

The project name is Traffix. The coordinator's current approved scope includes
`web/src/mobile/`, new `backend/harness/demo_*` adapters, compatible app/mobile
bridge fixes, tests, scripts and runbooks on `feat/kush-demo-polish`. DEMO guidance
is explicitly authorized: off by default, observed phone rule only, driver Accept
required, worker-confirmed action at a valid decision point, all actions logged.
Do not enable trained models without evidence they beat the simple rule on held-out
runs. Frozen contracts and existing other owners' implementations stay preserved.
The preceding task explicitly authorized creating `sim/assumptions.json` and its
README; that exception does not authorize rewriting Nandani's simulation files.

## Final unified-build assignment, 9 October 2026

Kush assigns the scope in `docs/prakhyat-final-build.md` to Prakhyat, including
`backend/simulation/`, compatible harness extraction, `web/src/operator/`,
`web/src/shared/`, simulation scripts/tests, his ML/evaluation adapters and versioned
`contracts/v2/` with compatibility. Native mobile-client implementation and the
existing phone bridge remain with Kush. Original sim assets remain with Nandani;
coordinate generation/review of new packs. This scoped assignment supersedes earlier
web ownership only for the new operator/shared paths, not other Urvashi files.
