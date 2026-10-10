# Ownership (one owner per path; do not edit paths you do not own)

| Path | Owner |
|---|---|
| `contracts/` | Coordinator only (changes need coordinator approval) |
| `backend/`, `scripts/`, `tests/test_sessions.py`, `tests/test_worker.py`, `tests/test_probes.py`, `tests/test_control.py`, `tests/test_events.py`, `tests/test_replay.py` | Coordinator |
| `sim/` | Nandani |
| `ml/`, `eval/`, `models/`, `tests/test_detection.py`, `tests/test_forecast.py`, `tests/test_cohort.py`, `tests/test_generate.py`, `tests/test_compare.py` | Prakhyat |
| `web/` | Urvashi |
| `docs/` | Everyone (append, do not rewrite others' files) |

Branches: `main` is always runnable. Work on `feat/<owner>-<module>` and merge small, often.
