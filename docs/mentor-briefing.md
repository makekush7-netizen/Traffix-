# Traffix — mentoring briefing and technical plan

**Read first:** Traffix is an operator congestion-response system. The simulation
harness is our test bench, not the product. Our first 12 hours established a working
observation → recommendation → driver acceptance → simulated action loop. Early
prediction, realistic demand and selection of the best response are not finished.

## 1. The product and the problem it addresses

Authorities need to notice congestion developing, understand whether a response
can help, and avoid pushing the queue onto another road. Our proposed product combines:

- **Operator dashboard:** map, measured vehicle counts/speeds where sensors exist,
  phone-sampled slowdown elsewhere, source/freshness/confidence, forecast and action log.
- **Response service:** recommend a bounded signal adjustment, limited diversion or
  advisory, with downstream capacity and fairness checks.
- **Driver app:** contribute optional observations; receive relevant guidance; accept
  or decline a route proposal. No app is required to benefit from improved signals.
- **Evaluation harness:** repeat the same demand/incidents under fixed, reactive and
  predictive policies. Verify whether interventions actually reduce delay.

We are not proposing to eliminate every cause of congestion. We propose a common
response layer whose action depends on the cause and the evidence available.

| Situation | Evidence to seek | Appropriate response to test |
|---|---|---|
| Peak demand / poorly balanced signals | Rising arrivals, queues that survive green, unequal approach pressure | Bounded green allocation with minimum service and downstream-space checks |
| Breakdown / parking / roadworks | Local speed collapse, lost discharge, camera or verified incident report | Limit diversion to verified-capacity alternatives; upstream advisory; dispatch/operator review |
| Waterlogging / rain | Reduced speeds across approaches, verified weather/incident context | Cautious advisory and capacity-aware diversion; extra green cannot remove a flooded bottleneck |
| Bus stop / pickup / turning friction | Repeated local slowdowns and movement conflicts | Targeted advisory/operational intervention; compare signal change only where relevant |
| Event surge / pedestrian crossing | Demand surge and crossing demand | Preserve pedestrian clearance; bounded traffic response and authority coordination |
| Sensor/network outage | Missing, stale or inconsistent observations | Show unknown; retain safe fixed timing; no confident automated diversion |

Congestion detection alone does not establish its cause. Show “suspected blockage”
until corroborated; do not claim the model can diagnose a pothole from speed alone.

## 2. What we have built in these 12 hours

| Component | Current evidence / boundary |
|---|---|
| LIG map and traffic engine | Offline OSM road/building geometry, SUMO vehicle motion, six visual vehicle types, 3D/top view. Real geometry, **not live real traffic**. |
| Phone/operator apps | QR claim, authenticated vehicle binding, sharing off by default, WebSockets, own route display and operator map. Browser apps; no native APK or real GPS collection yet. |
| Observation gateway | Admits only samples matching server-issued frames and the authenticated vehicle; rejects altered/stale/duplicate/wrong-run input. Zero uplinks means zero phone observations. |
| Live detection | Two fresh contributors, >=45% slowdown relative to an assumed reference for 30 simulated seconds. This is a reactive demo rule, not prediction. |
| Diversion | Pre-validated Route B, eligible vehicle only, explicit driver acceptance, expiry/decision-point/capacity guards, worker acknowledgement and audit. No defensible faster-route estimate yet. |
| Repeatability / comparison | Three 12-vehicle fixed runs completed without collisions/teleports. Matched saved complete cohorts only. 164 pre-extension regression tests passed. |
| ML branch | Three trained forecasting artifacts plus feature, evaluation and provenance code. Selected 19 incoming integrity/policy tests passed locally. Full training/evaluation reproduction and live integration remain outstanding. |
| Additional response experiment | Separate port 8003: 72 assumed departures, per-driver desired-speed variation, ideal simulated lane sensors, signal recommendations and operator-approved green extension. Verification details are recorded below after testing. |

The 8002 phone demo remains the reliable interaction demonstration. Its small
cohort does not model realistic peak-hour LIG demand. The earlier heavy-demand lab
has known collisions/incomplete journeys; it must not supply performance headlines.

## 3. How we obtain and match Indian / LIG traffic data

**Indian datasets exist; none automatically supplies current LIG traffic.**

| Source checked | Useful for | Limitation / access |
|---|---|---|
| [IIT Roorkee ITD](https://github.com/teg-iitr/ITD-Indian-traffic-dataset) | Indian vehicle classes, camera detection/tracking and turning-count research | Authors describe annotated images/video from multiple Indian locations. Dataset access is upon research request; published models have non-commercial attribution terms. Not a LIG live speed/count feed. |
| [IITM-Hetra](https://rbcdsai.iitm.ac.in/software/iitm-hetra/) | Candidate Indian heterogeneous-traffic perception resource | The official IIT Madras listing establishes the resource. Verify download, annotations and terms before choosing it; not evidence of LIG coverage. |
| [METEOR paper](https://arxiv.org/abs/2109.07648) | Research on dense, heterogeneous, unusual driving behaviour | Indian driving-video research resource; not a junction flow time series or a calibration substitute for Indore. |
| [Indore Smart City ICCC](https://www.smartcityindore.org/pan-city-initiative/) | Potential local authority partner for camera/count/phase data | Official site describes the command centre. We have **not verified an openly accessible live LIG API**. Ask for an anonymised export or a permitted observation pilot. |
| [Google Routes traffic options](https://developers.google.com/maps/documentation/routes/traffic-opt) | Optional route travel-time / traffic-category sanity check | Provider access, billing and usage terms apply. A travel-time estimate does not reveal lane counts, vehicle mix or signal phases. No integration is currently enabled. |

**A practical LIG calibration campaign:** obtain permitted videos/manual counts at
all approaches, in normal and busy periods on more than one day. In 5-minute bins
record arrivals by class and turn, queue extent, discharge during green, actual
signal phase timing, incidents and weather. Record repeated end-to-end travel times
on the same route, direction and time period. Use the existing field observation sheet.

Fit demand/turning proportions first, then free-flow speed distributions, then
headways/start-up behaviour. Compare class-wise counts, speed percentiles, queue
extent and travel-time distributions. Reserve different time periods/days for
validation. Report discrepancies and sensitivity; do not tune everything to one ETA.
Geometry from OSM, class proportions from a count survey and speed from a journey
measurement are different evidence sources and should retain their provenance.

If field access is unavailable, say **“LIG geometry with assumed demand”**. More
simulated cars do not turn it into real traffic data.

## 4. Mixed traffic: what speeds and appearances mean

The renderer has distinct motorcycle, auto, e-rickshaw, car, bus and delivery models.
Appearance is only identification; SUMO controls their motion. Current type inputs:

| Type | Length m | Acceleration m/s² | Maximum speed km/h |
|---|---:|---:|---:|
| Motorcycle | 2.0 | 3.2 | 50.0 |
| Auto | 2.7 | 1.9 | 36.0 |
| E-rickshaw | 2.8 | 1.3 | 25.2 |
| Car | 4.3 | 2.4 | 50.0 |
| Bus | 10.5 | 1.1 | 39.6 |
| Delivery | 5.2 | 1.8 | 43.2 |

These are **assumed simulation inputs**, not measured Indore averages. Maximum speed
is a ceiling, not a constant velocity. Road limits, a leader's gap, acceleration,
braking, signals and rain restrict actual speed. The separate response experiment
assigns reproducible speed factors in [0.85, 1.05]; drivers keep their factors rather
than receiving meaningless random speed jumps each frame. The original 12-vehicle
demo deliberately suppresses driver variation and applies a uniform initial rain
restriction. That explains its initially similar speeds.

Future calibration should fit distributions by vehicle class, including headway,
standstill gap, lateral clearance, stop duration and turning behaviour. Sublane
filtering is a later validated experiment: our earlier high-demand setup was unstable.
Do not disable collision checks to imitate weak lane discipline. See the official
[SUMO speed model](https://sumo.dlr.de/docs/Simulation/VehicleSpeed.html) and
[vehicle parameters](https://sumo.dlr.de/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html).

## 5. Exact sensing and detection proposal

**At equipped junctions:** camera detector + multi-object tracker, radar or loop
adapter supplies timestamped lane/approach aggregates. Count unique tracks crossing
an entry line in interval Δt; flow = 3600 × crossings / Δt vehicles/hour. Vehicles
currently in a lane are a stock, not that flow. Estimate speed from calibrated ground
coordinates and elapsed time; pixels/frame alone is not km/h. Record stopped count,
queue extent, occupancy, phase and downstream capacity. Evaluate detection by class
and weather; image detection is a different ML task from congestion forecasting.
Our new interface currently uses ideal SUMO lane sensors, not a trained camera model.

**On unequipped roads:** consenting phones would supply map-matched location/speed,
accuracy and time. Aggregate recent distinct contributors using a robust median or
trimmed mean; retain sample count, age and coverage. Today's phones instead echo
validated simulated vehicle frames. A phone contributes one observed trajectory;
it does **not** count surrounding vehicles without additional sensing. We cannot
recover exact total volume without a justified penetration-rate model and uncertainty.

For road e, proposed slowdown score `s_e = clip(1 - median_speed / reference_speed, 0, 1)`.
Use a class/time/road-aware reference so a naturally slower e-rickshaw is not itself
a jam. Proposed 5-second observation buckets carry sensor source and quality.
Keep camera/fixed-sensor and probe estimates separate before any calibrated fusion;
avoid double counting vehicles observed by both.

**Signal-aware detection:** test queue growth, high occupancy and poor discharge
*during service*, or a queue persisting across cycles. Normal red-light waiting is
not automatically congestion. Phones near signals need phase/location context or
conservative suppression of normal stops. Our current 30-second phone rule does not
yet resolve all such false positives. No fresh source means unknown, not green.

## 6. What Prakhyat built and the prediction plan

His `ca98c4b` branch contains scikit-learn **HistGradientBoostingRegressor** models
for 120, 180 and 300 seconds. Each predicts normalised future slowdown; it is not a
vehicle recogniser, a signal optimiser or a calibrated jam probability. The pipeline
uses training-fitted constant imputation with missingness indicators.

Ten inputs: current slowdown; 30/60/120-second mean slowdown; 60-second slope;
distinct probes in 60 seconds; sample age; fixed-sensor queue ratio; history span;
and fresh fraction in 60 seconds. Declared train seeds 100–107, validation 200–202,
test 300–304. Labels use the fixed/no-action policy; simulation truth is for offline
labels, never secret online features. Forecast eligibility requires fresh, sufficient
history and contributor coverage; missing coverage does not become a prediction.

**Useful work, but not yet a reliable early-warning result.** His saved report gives
180-second test MAE about 0.01713, versus persistence 0.08554 and trend 0.18128; these
are normalised slowdown errors, not minutes or “98% accuracy”. About 99.56% of eligible
180-second targets are already severe. The warning evaluation reports 0/3 matched
jam episodes. This population can reward predicting “still jammed” without learning
clear-to-jam transitions. Reported policy comparisons show no consistent predictive
journey advantage. We checked artifact hashes and selected tests; the raw full
experiment has not been independently reproduced here.

Next: collect complete clear/building/jammed/recovering runs across causes and sensor
penetration levels. Split by whole runs/seeds, with separate validation/test incident
conditions; never randomly mix neighbouring time rows. Compare boosting with persistence,
trend and a training-mean constant. Report per-state error, onset precision/recall,
false alerts/hour and warning lead time, as well as cohort delay under each policy.
Investigate eligibility/label selection bias and the event-matching failures before
retraining. If adding 30/60-second horizons, generate new labels and artifacts; the
existing 120-second model is not automatically a 30-second predictor.

A forecast after intervention is not the same as the no-action counterfactual the
model learned. Mark it ineligible or use a separately validated action-conditioned
model. Roll out forecasts in shadow mode before allowing them to influence actions.

## 7. Signal response, selective diversion and mobile advice

Proposed signal priority uses observed approach queue/arrivals minus downstream
blocking pressure, with minimum service and maximum red constraints. Start by
comparing a simple bounded reactive controller with fixed timing. Do not call the
current queue heuristic optimal or full max-pressure control.

The new mentoring experiment recommends **up to +5 seconds of current protected
green**, after 10 seconds, capped at 40 seconds total; at most once per phase. It
requires at least two stopped vehicles served by that green, receiving occupancy
below an assumed 35%, and no larger opposing queue. Worker rechecks the run/phase
and evidence on approval, changes duration only, and logs the action. Existing yellow
and all-red transitions remain. This is simulated, operator-approved control;
continuous automatic control and real signal hardware are future work.

Diversion selection should consider affected route/destination, a still-valid turn,
route legality by vehicle type, estimated bypass capacity and an allocation cap.
Offer to a small eligible subset, observe acceptances and downstream conditions,
then reassess; do not route everyone to the same shortcut. The current app already
supports addressed offers, decline/accept, expiry and server-confirmed application.
Lane-closure or slow-ahead advisories can follow the same channel. “Switch lane now”
needs lane localisation and manoeuvre safety evidence that phone GPS alone does not
supply. For real driving use voice/pre-trip guidance, not distracting tap prompts.

**“Follow the driver ahead” is a research hypothesis.** Drivers may follow for a
short distance but have different destinations or miss a turn. Non-users cannot
receive our app notification. Model an explicit assumed follower fraction (for
example 0%, 25%, 50%) among route-compatible vehicles and measure bypass overload,
network delay and equity. Those are sensitivity scenarios, not measured Indian
psychology. The system must still have value at zero following and low app adoption.

## 8. What to show and say in the mentoring round

**90-second pitch:** “Traffic jams have different causes, but fixed signals and
uncoordinated diversions often respond too late. Traffix is an operator response
system combining junction sensors and optional driver observations. We are building
an evidence trail from sensing through prediction and bounded actions to outcomes.
In our first 12 hours we built the LIG simulation, authenticated phone contribution,
operator/driver interfaces and a real accepted-route-change loop. Our new experiment
shows simulated sensor counts/speeds and a guarded signal extension. Our teammate has
trained forecasting models, but their early-warning evidence is not strong enough yet,
so we are transparent about the current rule. Next we need local calibration, better
jam-onset data and matched multi-scenario policy evaluation. We would value your advice
on the smallest credible field-data pilot and the most useful response to prioritise.”

Show the 8002 phone loop first. Then open `http://localhost:8003/response` on the
laptop for the separately labelled response experiment: Start, 4x, sensor rows,
recommendation, approve only when available, audit. Empty junctions correctly show
zero count and unavailable mean speed. Do not pretend a disabled recommendation is a
fault: it explains why the controller should wait. This additional run has different
inputs and deliberately cannot use the small demo's baseline.

For a final evaluation compare A fixed/no action, B reactive bounded response and
C predictive response with the same bounds, demand, incidents, seeds and compliance.
Report every scheduled journey, completion/collisions/teleports, mean and tail delay,
throughput, queue spillback and fairness. Reproduce multiple seeds and include failures.
Use modeled emissions only with explicit uncalibrated vehicle proxies.

**Ask mentors:**

1. Which intervention makes the strongest first pilot: one-junction green allocation
   or a capacity-limited diversion corridor?
2. Can you connect us with Indore traffic police/ICCC or a campus for permitted
   counts, signal timing and anonymised video/aggregates?
3. What evidence would convince you of useful early warning: lead time, false alerts,
   or measured improvement over a reactive controller?
4. Is partial phone penetration plus fixed junction sensors a sensible deployment
   assumption, and what fallback would you require?
5. How should we test the follower hypothesis ethically without encouraging unsafe
   turns or claiming effects on non-users we cannot observe?

**Next order of work:** stable moderate-demand scenarios → sensor/probe provenance
and phase-aware detection → shadow ML and onset evaluation → matched reactive/predictive
responses → local calibration → real-device/operator usability. Real GPS, native APK,
production signal integration and broad autonomy follow those gates.
