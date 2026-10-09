# LIG harness validation

SUMO 1.28.0, seed 42, 1200 simulated seconds per scenario. These are
engineering diagnostics on synthetic demand, not measured Indore traffic or
policy-comparison results.

41 automated tests passed, with one Starlette/httpx deprecation warning.
Browser checks covered playback, rate, pause, reset, top-down camera, zoom,
vehicle picking, follow camera and manual restriction recovery; no browser
JavaScript errors were observed during these checks.

| Scenario | Scheduled | Arrived | Active at horizon | Stopped at horizon | Collision involvements | Teleports |
|---|---:|---:|---:|---:|---:|---:|
| everyday | 500 | 255 | 245 | 170 | 8 | 0 |
| rush | 894 | 263 | 631 | 529 | 10 | 0 |
| rain | 894 | 290 | 604 | 512 | 10 | 0 |
| roadworks | 894 | 297 | 597 | 538 | 10 | 0 |

All four cohorts are **incomplete** and contain collision diagnostics. The
interface and manifests expose this. Remaining junction and sublane tuning
is required before credible quantitative comparison. Rain and obstruction
restrictions began at 60 seconds and restored speeds at 360 seconds.

The LIG import correction joins OSM nodes 2023505360, 2023505361,
2023505364 and 8389132295. Previously the same physical intersection had
external links of 0.2 m and 1.34 m, causing a downstream signal to block
vehicles still occupying the preceding junction. The explicit join and
approach phases address that import defect; other modeled collisions remain.

Network SHA256: `5e1ba257cf9f0d2e8352bd0461d139c9a85db2a18ceaeba4f776a94f59522e62`.

Saved runs (under the repository’s ignored `runs/` directory):

- `lig.6c84d9e82ca2`: everyday
- `lig.d2e6cce221df`: rush
- `lig.4bcdfcb866fa`: rain
- `lig.25069c176d36`: roadworks

Each directory retains demand XML, diagnostics, trip output, manifest and
recording. Aggregate evidence: `runs/lig-validation.json`; test output:
`runs/lig-final-pytest.txt`. No trip or collision data was discarded to make
these checks look successful.
