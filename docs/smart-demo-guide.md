# Traffix smart traffic demonstration

Open http://localhost:8004/response on the laptop. Start with
`./scripts/run_response.ps1` from PowerShell in the repository. The original
scenario lab remains at http://localhost:8001/ and the small phone demo at
http://localhost:8002/dashboard. Do not compare numbers across these different demands.

## Presentation sequence

1. Show the original lab's everyday, rush, rain and roadworks scenarios as exploratory
   scenarios. High-demand runs have previously produced faults; they are not benchmark evidence.
2. Open the new response view. Explain the real OSM geometry, assumed 72 departures,
   six vehicle types, different desired speeds and SUMO car-following behavior.
3. Start at 4x with Smart coordination off. Inspect junction vehicle counts, stopped
   vehicles and speed. Use View junction to see actual signal colours and vehicles.
4. Turn Smart coordination on. Show an eligible green extension in Action evidence.
   It is not an instant switch to green: clearance and minimum service remain intact.
   In the deterministic seed-42 test, the first extension occurred at simulation
   time 338 seconds: 18 queued vehicles, zero opposing queued vehicles, 20 seconds
   remaining increased to 25. This demonstrates application, not reduced delay.
5. For phones, use Link phones on this same server, create fresh codes using
   http://192.168.137.1:8004 as the laptop address. The operator phone dashboard and
   response page share the same simulation. Its small-demo story labels are inherited;
   use the response page to explain the 72-vehicle experiment.
6. Enable sharing and Traffix guidance on the phone dashboard if demonstrating route
   proposals. Existing offers still require fresh phone evidence, route eligibility,
   available bypass capacity and driver acceptance. A signal change does not itself
   create a route offer. An eligible phone must join before passing its decision point.

## The algorithm implemented today

This is a bounded queue-responsive green-extension rule, not RL, a trained ML controller,
or a coordinated green-wave optimizer. The UI switch enables this rule on each monitored
junction. All decisions and TraCI calls execute on the single simulation owner thread.

At every simulation step, obtain simulated lane counts, stopped counts, mean speed and
occupancy. For the current protected green, extend by at most five seconds only when:

- No yellow is active and the phase has served at least ten seconds.
- At least two stopped vehicles remain on its protected approaches.
- Their queue is at least as large as the opposing queue.
- All receiving-lane occupancy measurements exist and maximum occupancy is below 35%.
- This phase has not already received an extension and total green stays within 40 seconds.

The rule never jumps directly across phases. Switching it off leaves the current
approved duration to finish, after which the original phase program continues. Reset
starts with smart mode off. Thresholds are assumptions for the experiment. Downstream
occupancy considers adjacent receiving space; this is not network-wide coordination.

## Phone scope

Implemented: live simulated speed, current route, conditional in-app rerouting offer,
explicit acceptance, general speed/gap advice and traffic-learning material.
The advice does not command a numerical speed or control the simulated vehicle.
Signal-arrival prediction, safe speed envelopes and field validation are needed before
recommending a numerical speed. No native background push notification is implemented.

The dashboard shows SUMO modelled tailpipe CO2 accumulated in this run. This is not
carbon saved. A savings estimate requires complete matched fixed-control and smart-control
runs with the same demand, seed, incident and network, and compatible emission models.
Electric-vehicle lifecycle emissions are outside this estimate. The phone says not yet
measured rather than inventing savings.

## Next algorithms to evaluate

Use this harness to compare fixed timing against the current reactive rule. Then test
a pressure-based controller using incoming demand and downstream capacity, with fairness
and clearance constraints. Predict arrivals and queues 2–5 minutes ahead using recent
speed, queue, trend and observation freshness. Prakhyat's gradient-boosted slowdown
forecast models are candidate inputs, not enabled live decision makers.

Evaluate on held-out complete runs: warning lead time, false alerts, mean and tail delay,
throughput, spillback and faults. Calibrate vehicle mix, turning demand, speeds and
signal timing from permitted LIG observations before claiming real-world benefit.
