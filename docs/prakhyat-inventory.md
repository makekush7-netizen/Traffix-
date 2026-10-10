# Local build inventory

Inspected on 10 October 2026 (Asia/Calcutta). This is measured machine/runtime inventory, not a performance claim.

- CPU: Intel Core Ultra 7 255HX; Windows reports 20 cores and 20 logical processors.
- Installed physical memory: 33,752,997,888 bytes.
- GPU: NVIDIA GeForce RTX 5060 Laptop GPU, Windows driver 32.0.16.1664; Intel Graphics also present (32.0.101.8991).
- Python used for initial verification: 3.12.14 in an existing external virtual environment. Default system Python is 3.14; use the supported setup instructions instead of assuming the default is suitable.
- Node: 24.18.0.
- Installed packages: eclipse-sumo 1.28.0, traci 1.28.0, FastAPI 0.143.0, Pydantic 2.14.0, NumPy 2.5.3, scikit-learn 1.9.1, pytest 9.1.1, httpx 0.28.1.

The working directory was an empty Git repository before fetching coordinator commit `4714e82`. The build branch is `feat/prakhyat-unified-simulation`; earlier Desktop and Codex checkouts were not modified. GitHub push access was verified. Hardware inventory required a read-only elevated CIM query because the sandbox denied CIM access.

Baseline test results are recorded in the final build return after completion. Initial plain pytest invocation did not initialize the bundled SUMO binary path; the corrected invocation calls `scripts.verify_nandani.prepare_environment()` first. Do not interpret environment setup errors as new implementation regressions.
