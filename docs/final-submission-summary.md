# Copy-ready Traffix submission

## Short description

Traffix is a traffic congestion response prototype for LIG Square, Indore. A local SUMO simulation on OpenStreetMap geometry connects a shared 3D operator dashboard with consent-based phone probes and scoped driver guidance. Its capacity-aware pressure heuristic uses simulated lane queues and downstream receiving space to choose bounded signal responses. Saved matched runs on two held-out seeds show 11.31% shorter mean journey time and 7.48% lower modeled CO2 versus fixed timing. Every scheduled vehicle completed under each policy, with zero collisions and teleports. These are synthetic finite-cohort results, not field effectiveness. Native companion integration and forecast validation are separate gates.

## Algorithm explanation

Each eligible signal phase receives a score from normalized upstream queue minus normalized downstream occupancy, weighted by assumed saturation flow. Minimum/maximum green, safe maximum-red priority and hysteresis constrain decisions. One worker applies configured yellow/all-red clearance and rechecks receiving space. This implemented reactive heuristic produced the measured benefit. Detection uses persistent fresh slowdown through a serving green. Forecasting candidates use HistGradientBoostingRegressor at 120/180/300 seconds and require held-out validation against persistence and trend before forecast-assisted control.

## Results statement

Across held-out seeds 51/52, original pressure control reduced mean journey time by 11.31% and modeled CO2 by 7.48%, averaging paired percentage reductions against identical fixed-timing cohorts. All 128 scheduled vehicles completed under each policy. No collisions or teleports occurred in the saved held-out manifests. Journey includes insertion delay. CO2 is uncalibrated SUMO output. The sample contains two seeds and finite demand. The incomplete stress baseline is excluded from percentage savings.

## Differentiation

Traffix combines shared operator control, reproducible mixed-vehicle simulation, consent-based phone guidance and auditable matched-baseline results. A bound vehicle identity links the phone and dashboard. Source labels distinguish simulated fixed sensors from phone probes, and missing observations remain unknown. This describes our implementation, without claiming competitor-wide exclusivity.

## Technology

Python, SUMO/TraCI, FastAPI, authenticated WebSockets, Three.js, OpenStreetMap, React Native/Expo and scikit-learn. One simulation worker owns TraCI. Authenticated queued commands and control leases coordinate shared operator changes. The full simulation runs on a local host.

## Links and upload

- Repository: https://github.com/makekush7-netizen/Traffix-/
- Submission frontend: https://traffix-demo.vercel.app/ (frontend illustration, separate from the local simulation)
- Presentation: `presentation-output/final/Traffix-Final.pptx`
- PDF: `presentation-output/final/Traffix-Final.pdf`
- Video URL: leave blank until an actual demonstration is uploaded.

## Limitations and next step

Validate native phones and multiple admin clients against the unified host, test sustained overload and per-approach fairness, validate short-term forecasting on disjoint seeds, and calibrate fleet emissions and field observations. Later flow, speed-advice and stopped-queue experiments in the complete-agent handoff were unpushed on another laptop and are excluded from this submission's measured headline.
