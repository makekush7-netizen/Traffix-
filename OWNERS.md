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
