# Final presentation status

Completed 10 October 2026 in `feat/kush-final-deck`. No primary submission files or simulation code changed.

## Deliverables

- `presentation-output/final/Traffix-Final.pptx`: 1,901,346 bytes, nine white 16:9 slides. Retains original image slides 1–5, adds editable detection/forecasting, Results table, demo and roadmap slides. Page markers updated. Presenter notes carry sources and claim boundaries.
- `presentation-output/final/Traffix-Final.pdf`: 1,881,853 bytes, same nine-slide sequence. Flattened image PDF for stable portal rendering.
- `docs/final-algorithm-answers.md`: signal selection, detection, forecast plan, evaluation split, policy selection, Results metrics, fairness and CO2 assumptions.
- `docs/final-submission-summary.md`: copy-ready form text and upload links.
- `docs/final-deck-evidence-verification.json`: local trip XML checksum/count audit and paired headline calculation.

Both presentation files are below 5,000,000 bytes. First five slides retain generated concept illustrations, not field photographs. The Results table and new slide text remain editable in PPTX. No new simulation experiments or research batches ran.

## Supported headline

Original capacity-aware pressure: **11.31% shorter mean journey and 7.48% lower modeled CO2**, arithmetic average of paired reductions on held-out seeds 51/52 versus fixed timing. All 128 scheduled vehicles completed under each policy, zero collisions/teleports in saved manifests. Synthetic finite cohorts, small sample, no field calibration or predictive-control claim.

## Evidence inspected

`../prakhyat-review` HEAD is `7733a08b1defe6bf6c90c2e797829fc2fedb2f1e`, contained in its tracked remote branch `origin/feat/prakhyat-unified-simulation`. Inspected saved `artifacts/ppt-benchmark-heldout/report.json`, `artifacts/ppt-benchmark-evidence/heldout-normal.json`, `file-checksums.json`, all six held-out trip XML files, development/stress report limitations and `docs/prakhyat-build-return.md`. Also inspected `backend/simulation/policies.py`, relevant worker code, and `ml/detect.py`, `features.py`, `train.py` and `forecast.py`.

Six trip files match saved SHA256 values. XML counts and arrival status match scheduled completion. XML duration plus departDelay is consistently 0.25 s below saved lifecycle-event journey means, consistent with worker-step timestamps. The deck uses the lifecycle metric consistently. CO2 and fault totals come from saved report/manifests. Full recording contents were unavailable locally. No rerun independently reproduces the simulation physics or emissions.

## Excluded and unresolved claims

The complete-agent handoff says later flow, speed-advice and stopped-queue experiments are unpushed on another laptop. Their source files are absent from this verified base. Later numbers appear only as handoff-reported in algorithm notes, never in the deck headline. The selected 15.28% flow case is not a general mean. Development queued-pressure results are not held-out validation. Do not combine cohorts or add percentages.

Stress seed 53 fixed completed 133/135, so no percentage comparison. Development seed 42 worsened P95 stopped waiting. Long-running Explore overload/collisions remain unresolved. CO2 is uncalibrated SUMO output. No forecast accuracy or predictive-control improvement established.

## Integration snapshot

At authoring, `../prakhyat-review/docs/final-sim-status.md` reports additive driver world/own-route/event/alert integration implemented with 13 focused tests passing. Its final commit/expanded tests were pending. Root `../docs/final-app-status.md` was not yet available. The deck says native integration and physical multi-device checks require verification. Do not infer Android physical-device success from browser screenshots or backend tests. The operator screenshot is a saved UI demonstration, not a benchmark frame or replay audit.

## Verification

PPTX structural integrity, slide count/geometry, font policy, editable table presence and Artifact Tool re-import passed. All nine authored slide previews inspected. PDF contains nine 16:9 pages, with portal-oriented compressed images. PDF runtime export had a missing standard-font module, so the PDF uses the reviewed rendered slides through ReportLab. No native PowerPoint execution claimed. Build/validation intermediates remain private under `presentation-output/build-final` and are excluded from the commit.

## Git handoff

Documents and final presentation files are intended for `feat/kush-final-deck` only. No main merge. See the final response for the pushed commit hash.
