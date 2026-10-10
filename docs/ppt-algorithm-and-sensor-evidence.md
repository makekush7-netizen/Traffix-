# Traffix: algorithm, mentor feedback and sensor evidence

## Claims allowed now

Traffic geometry is from OpenStreetMap; demand and fleet behaviour are assumed in
SUMO. The implemented signal controller is a **capacity-aware pressure heuristic**,
not a proven optimal controller or neural-network signal controller. Benchmark
results must be taken from the completed report, not from screenshots or fixtures.

Pressure score sums assumed saturation flow multiplied by upstream queued-capacity
fraction minus downstream occupied-capacity fraction. It chooses among configured
phases, with minimum/maximum green, maximum-red priority where a safe phase exists,
hysteresis, receiving-space checks, yellow and all-red clearance. Missing/stale
observations require fallback. Current inputs are simulated installed lane sensors.
The code does not implement all assumptions or guarantees of theoretical max pressure.

Research basis: Lioris and Varaiya, *Adaptive Max Pressure Control of Network of
Signalized Intersections*, UC Berkeley, 2014, hosted by EPFL:
[Berkeley adaptive max-pressure paper, hosted by EPFL](https://transp-or.epfl.ch/heart/2014/abstracts/285.pdf)
The research motivates upstream/downstream queue balancing; its numerical results
are not Traffix results and must not be copied as our savings percentage.

## Mentor direction reflected in the build

- Demonstrate a human story: phone-bound drivers encounter queues and receive guidance.
- Make demand genuinely congested and repeatable before claiming benefit.
- Predict worsening conditions early enough to act; test 120/180/300-second horizons.
- Compare fixed, reactive and predictive policies; also test a competitive actuated baseline.
- Check downstream space and fairness; do not simply move the queue to another road.
- Keep source, freshness, uncertainty and an operator override visible.
- Report modelled CO2 with assumptions and matched complete-cohort accounting.
- Use one live simulation with a clearly labelled recorded matched baseline.

The prediction feature foundation includes causal slowdown history, 30/60/120-second
means, 60-second slope, contributor count, sample age, fresh fraction and optional
fixed-sensor queue ratio. Gradient boosting must beat persistence/trend on held-out
SUMO runs before enabling predictive control. Split by whole seed/run, train on
fixed-policy no-action runs, and report MAE separately at each horizon plus usable
coverage. Forecast error improvement does not prove traffic improvement: repeat
matched reactive-versus-predictive interventions to test that separately.
Current fixture model scores are not real-network forecasting evidence.

## How phones can cover roads without installed sensors

A participating moving vehicle is a probe. In deployment, opt-in GPS samples supply
position, time and speed. Map matching assigns the sample to a road; aggregation of
fresh distinct contributors estimates observed road speed and slowdown. Samples
must be quality-filtered and location data protected. Sparse or missing observations
stay unknown; phone speed alone does not establish exact lane queues, turning counts,
receiving capacity, a crash diagnosis or universal coverage.

Primary field evidence: UC Berkeley/Caltrans/Nokia's Mobile Century experiment used
GPS-equipped mobile phones in vehicles and validated traffic information against
video and loop detectors. The university states that phones alone reconstructed
traffic velocity maps under the conditions of that highway experiment:
[UC Berkeley Mobile Century field experiment](https://traffic.berkeley.edu/project/mobilecentury)
This supports probe-based traffic observation, not a guarantee for mixed Indian
urban traffic or a claim that our app has reproduced their field accuracy.

University project description: Mobile Millennium collected GPS phone traffic data,
processed it and distributed information back to phones; the broader system also
integrated taxis, radar, loops and historical data:
[UC Berkeley/CITRIS Mobile Millennium project](https://citris-uc.org/research/project/mobile-millenium/)

SUMO documents floating-car data as vehicle location and speed, analogous to a
high-frequency GPS device, with configurable sampling/equipment rates:
[SUMO floating-car-data documentation](https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html)

**Our demo:** real phones over local WiFi are bound to simulated vehicles. After
consent, the browser sends its assigned simulated vehicle observations back to the
validated gateway. This demonstrates real messaging and the probe pipeline; it is
not collection of the handset's real GPS. Only accepted phone uplinks populate the
phone observation plane. Phone observations support coverage and the observed
diversion rule; replacement of missing lane-sensor inputs in the pressure controller
is not established. Do not draw a phone-to-autonomous-signal causal arrow as if this
integration has been validated.

Suggested PPT sentence: "Phones can act as opt-in traffic probes on roads without
fixed sensors. Our prototype demonstrates that data path using real connected phones
and simulated vehicle positions; field GPS integration and coverage validation remain."

## Climate number boundary

SUMO CO2 rates are model outputs. At 0.25-second steps the host integrates mg/s times
0.25 then divides by 1,000,000 to report kg. Fleet emission-class mapping is unreviewed;
there is no measured climate saving or justified city-wide annual extrapolation.
[SUMO emissions documentation](https://sumo.dlr.de/docs/Simulation/Output/EmissionOutput.html)

## Benchmark discipline

Development seeds are for controller investigation. Freeze the chosen controller
before separate held-out seeds. Report every attempted run, incomplete cohort and
collision. Match network, frozen demand, seed, duration/drain, events and execution
fingerprint; only policy differs. Headline journey time includes waiting to enter the
network. Report percentage reduction as 100*(fixed-response)/fixed. Negative values
mean worse outcomes. A selected favourable scenario must be labelled as selected;
report the full tested range alongside it.


## Show the measured comparison in the dashboard

Keep the live Explore run separate from the evidence. Open Results, scroll to Saved
complete runs, find an Everyday run with seed 42 and policy pressure, then choose
Find matched comparison and its fixed baseline. The development pair contains 63
scheduled/arrived vehicles on each side. Inspect recorded run plays the actual saved
simulation frames. Do not describe that playback as live. The live dashboard can
continue demonstrating adaptive decisions while a recorded matched baseline supplies
the evidence. Later held-out runs appear in the same catalog using seeds 51–53.

## Forecast and fairness disclosure for the pitch

"Our measured traffic benefit comes from adaptive pressure control. We have a
separate forecasting foundation; predictive control is not yet validated. We also
track tail waiting, because an average gain must not conceal worse outcomes for
some drivers."

No real-network forecast accuracy, predictive-policy traffic benefit, field phone
accuracy, camera incident diagnosis or Indian fleet emissions validation has been
established by this signal-policy benchmark.
