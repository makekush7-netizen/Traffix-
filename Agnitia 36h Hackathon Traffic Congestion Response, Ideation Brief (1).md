# Agnitia 36h Hackathon: Intelligent Traffic Congestion Response System

**Ideation brief for the team (not a PRD)** Track: TERRA (Planet, Climate & Resilience) Purpose: give everyone the same context, research, and open questions so we can discuss our way to one final problem statement and one build plan. Status: draft for group discussion. Items marked **\[verify\]** come from memory or a single source and must be checked before we put them in a pitch.

---

## 1. How to read this document

1. Sections 2-4: what the problem statement asks, and why traffic jams happen in India.
2. Sections 5-6: what already exists, and where the gaps are.
3. Sections 7-10: our idea, explained with a worked example, plus the app and edge cases.
4. Sections 11-13: scope, risks, and the open questions we need to decide together.
5. Section 14: glossary, so no one gets stuck on a term.

If you only have 5 minutes, read sections 2, 7, 8 and 12.

---

## 2. The problem statement in plain words

**Title:** Intelligent Traffic Congestion Response System. Detect traffic jams early and suggest the best response.

**What the organisers say:** traffic jams waste time and fuel and raise pollution, yet most signals and diversions are fixed or managed by hand. Authorities need systems that notice congestion early and suggest actions that really work.

**Objective:** build a system that detects congestion and recommends actions to reduce it.

**What they list as main points:**

- Use simulated or public traffic data.
- Detect jams and predict them a little ahead.
- Suggest signal changes, diversions and advisories.
- Show the effect compared with doing nothing.

**What they want delivered:**

- A system running on a simulated road network.
- A demo that detects a jam and shows a response that cuts delay.
- A comparison against a no-action baseline.
- An architecture diagram, a code repository, and a short report.

**Suggested tools:** Python, SUMO (or similar), ML short-term forecasting, a mapping dashboard.

### The three pain points hidden in the statement

| Pain point | What it means today |
| --- | --- |
| Late detection | A jam is noticed after it has already formed and traffic is stuck |
| No prediction | Nobody sees the jam coming a few minutes earlier |
| React after damage | The response (a police officer, a signal change) arrives when delay has already happened |

### The loop every good solution must contain

**Sense, Detect, Predict, Decide, Act, Prove.**

1. **Sense:** get traffic data (from a simulation or public source).
2. **Detect:** notice a jam forming (speeds drop, queues grow).
3. **Predict:** estimate what will happen over the next 5-15 minutes.
4. **Decide:** choose a response (signal timing, diversion, advisory).
5. **Act:** apply it in the simulation.
6. **Prove:** compare against a run where nothing was done.

**The most important line in the whole statement is "show the effect compared with doing nothing."** A flashy dashboard with no measured saving will lose to a plain one with a clean before/after number.

---

## 3. Why traffic jams happen (general)

A road has a fixed capacity: only so many vehicles can pass a point each minute. A jam appears when more vehicles arrive than the road can pass. Once a queue forms, it grows faster than it clears, because vehicles at the back keep arriving while those at the front move slowly. This is why **early action is so valuable**: a small queue is cheap to fix, a big one takes a long time to clear even after the cause is gone.

Three common triggers:

- **Demand surge:** everyone travels at the same time (office and school hours).
- **Capacity loss:** an accident, breakdown, parked vehicle or flooded road blocks part of the road.
- **Poor control:** signals that do not match the traffic actually present.

---

## 4. Why India is different: the constraints

Most research and tools were built for the US or Europe. Indian conditions break many of their assumptions.

| Constraint | What it looks like | Can we do something? | In 36 hours? |
| --- | --- | --- | --- |
| **Mixed traffic** | Cars, bikes, autos, buses, trucks, cycles, e-rickshaws and pedestrians share one road at very different speeds | Yes. Model several vehicle types in the simulation | Yes |
| **No lane discipline** | Two-wheelers fill gaps between cars, so queues are wide and hard to measure | Partly. Simulator settings can approximate it | Partly |
| **More vehicles, less road** | Vehicle numbers grow faster than road space. Roads cannot easily be widened | We cannot build roads, but we can use spare capacity on alternate roads and spread demand over time | Yes, via diversions and advisories |
| **Poor, static signals** | Many signals run on fixed timers, are not coordinated, or are switched off | Yes. This is the main lever authorities control directly | Yes, core |
| **Peak hour and events** | Office hours, rain, festivals, processions, VIP movement | Yes, if we predict early | Yes, core |
| **Roadside problems** | Illegal parking, vendors, stopped buses and autos, cattle, potholes, waterlogging | We cannot remove them, but we can detect the blockage quickly and respond | Yes, as the demo incident |
| **Weak public transport** | Crowded or unreliable buses, limited metro, so people use own vehicles | Too big to fix. Possible small add-on: bus priority at signals | Stretch goal only |
| **Poor discipline** | Red-light jumping, wrong-side driving, ignoring advisories | Partly, through an awareness and rewards layer | Small part only |
| **Little sensor data** | Few loop detectors or cameras on most roads | Use cheap sources: cameras, GPS probes, driver reports | Yes, by design |

**Key insight for our pitch:** we should say clearly that we are *not* trying to solve all of India's traffic. We target the part software can actually influence: **how early we notice, how well we predict, and how we coordinate the response.**

---

## 5. What already exists (research summary)

### 5.1 Real systems in India

**Bengaluru Adaptive Traffic Control System (BATCS)**

- Launched in May 2024 and expanded to around 60 junctions at the time of the reports we found, with plans for 165 and more. **\[verify current numbers\]**
- Uses camera sensors to adjust signal timing live instead of using fixed timers. Built using C-DAC's CoSiCoSt application, described as tailored for India's mixed traffic.
- Three modes: manual (police override for ambulances or VIPs), vehicle-actuated (cameras count vehicles and adjust timing), and ATCS (synchronises signals across several junctions).
- Police say travel time at Hudson Circle fell by 33%, and other reports mention 20-30% reductions at three junctions. **These are official statements reported in the news, not independent studies.** Do not present them as proven fact.

**What this tells us:** adaptive signals work and are accepted in India. It also gives us a believable target range for our demo (roughly 20-33% improvement).

### 5.2 Research and student projects

- **IIIT Bangalore** built an adaptive traffic control project on SUMO for Electronic City, including a method to pick which traffic lights should be made adaptive. They open-sourced a package called Traffic Interventions on GitHub. A good code reference.
- **IIT Madras** has research on signal control for "heterogeneous, less lane-disciplined" traffic. Their reported results include up to 24% lower control delay from optimised timing, and up to 33% lower average intersection delay when combined with a real-time delay-based strategy. Another IIT Madras project used travel-time data from a small number of probe vehicles to set signal timings, which shows you do not need expensive sensors everywhere.

### 5.3 Open-source tools

- **SUMO** (Simulation of Urban Mobility): the standard open-source traffic simulator. We control it from Python through an interface called TraCI.
- **SUMO-RL:** a ready interface for training reinforcement-learning agents on traffic signals in SUMO.
- **RESCO benchmark:** ready scenarios plus three non-learning controllers (Fixed Time, Max Pressure, Max Wave) and several learning ones.
- **sumoITScontrol:** a collection of traffic controllers for SUMO.

### 5.4 Known problem: SUMO and Indian traffic

Older work notes that SUMO enforces lane discipline even on small vehicles like two-wheelers, which is unrealistic for India. IIT Bombay built a variant called SimTram that splits each lane into strips so several small vehicles can share space, but it targeted an old SUMO version. Other work shows SUMO can be calibrated for Indian mixed traffic with results comparable to the commercial tool VISSIM.

My own note, **\[verify\]**: newer SUMO versions have a "sublane" model that lets vehicles sit side by side within a lane. We should confirm in the SUMO documentation and test it early.

### 5.5 How signal control methods compare

| Method | Idea | Pros | Cons |
| --- | --- | --- | --- |
| Fixed timer | Preset cycle by time of day | Simple. What most cities use | Ignores live traffic |
| Actuated | Extend green when cars are waiting | Cheap, reacts locally | No view of the wider network |
| Adaptive (SCATS, SCOOT, India's ATCS) | Adjust timing from measured flow | Proven in real cities | Expensive sensors and integration |
| Max Pressure | Give green to the phase that relieves the biggest queue difference | Simple rule, strong results, easy to build | Not designed for lane-less traffic |
| Reinforcement learning | An agent learns by trial and error | Impressive results in papers | Slow training, fragile, risky in 36 hours |

**Our proposed choice:** fixed timer as the baseline, Max Pressure as our smart controller. RL only if the core is already finished.

---

## 6. The gaps: where we can stand out

This is **our analysis** from the limited search we did. We cannot promise no one has built the full combination.

| What existing solutions mostly do | What we can add |
| --- | --- |
| Focus **only on signals** | Signals **plus diversions plus advisories**, chosen together |
| **React** once traffic has built up | **Predict** the jam a few minutes ahead and act before it grows |
| Report "time saved" | Also report **fuel and CO2 saved** (matches our TERRA track) |
| Research code with no operator view | A **map dashboard** with a live before/after comparison |
| Tested on Western-style traffic | **Indian mixed traffic** and **incidents** like a blocked lane or waterlogging |
| Treat drivers as passive | A **driver app** that delivers official instructions and collects reports |

---

## 7. Our idea

**One-line version:** a prediction-driven traffic control system for Indian cities. Operators see jams before they form, the system coordinates signals, diversions and advisories, and a companion app delivers official instructions to drivers and collects their reports. Everything is proven against a no-action baseline.

### The flow

1. **Simulation (SUMO)** produces traffic data on a real map of a small area.
2. **Detection** watches speeds and queues and flags a jam as it starts.
3. **Prediction** estimates how the jam will grow over the next 5-15 minutes.
4. **Decision engine** picks a response: retime signals, split traffic across routes, issue advisories.
5. **Action** applies the response in the simulation.
6. **Operator dashboard** shows everything on a map and lets the operator approve actions.
7. **Driver app** receives the instructions and lets drivers report problems.
8. **Comparison** runs the same scenario with no action and shows the difference.

### Worked example (numbers are illustrative, not real results)

**Setting:** a small area with 6 junctions near a market. It is 6:30 pm, peak hour.

**Without our system (baseline):**

- At 6:35 a delivery truck stops on the main road and blocks one of two lanes (a typical roadside problem).
- Signals keep running their fixed timer.
- Queue on the main road grows; side roads fill up as people try to cut through. By 6:50 the area is gridlocked.
- Result for the demo: average trip time 18 minutes, total waiting time high, a lot of idling and CO2.

**With our system:**

- 6:35: truck stops. By 6:37 the **detection** module sees speed on that road drop below a threshold and the queue start to grow.
- 6:37: the **prediction** module estimates the queue will reach the next junction in about 8 minutes.
- 6:38: the **decision engine** proposes three things: (a) give the main road's upstream signal a longer green to drain it, and shorten greens that feed traffic into the blocked road; (b) divert about 35% of vehicles heading that way onto a parallel road that has spare capacity, not 100%, so the jam does not just move; (c) send an advisory to drivers in the area.
- 6:38: the operator sees the recommendation on the map, presses **Approve**.
- 6:39: the phone app of a driver on that road shows "Blockage ahead. Take Route B, saves about 6 min," and the signals change.
- Result: the jam stays smaller, clears sooner, and the average trip time drops to, say, 13 minutes. We show the side-by-side numbers and the CO2 saved.

**Why only 35% and not everyone?** If every driver is sent to the same alternate road, that road jams too. Good diversion means *splitting* traffic. This is a point where we can beat consumer navigation apps (see section 9).

---

## 8. What we measure (the "Prove" step)

Judges want a clear number. We report the same metrics for the baseline and our system:

- Average travel time per vehicle
- Total waiting time
- Average and maximum queue length
- Time to clear the jam after the incident
- Fuel used and CO2 emitted (SUMO can output emissions)
- Number of vehicles that finished their trip

**Fairness rule:** the baseline and our system must use the **same random seed, same demand, same incident**. Otherwise our comparison can be challenged as rigged.

---

## 9. The driver app idea (open for debate)

### Why add an app at all

Without it, a recommended diversion is only a suggestion on a screen. The app makes the system two-way:

- **Authority to driver:** official instructions reach people.
- **Driver to authority:** reports of blockages, waterlogging or breakdowns reach the control room. In India, where sensors are scarce, drivers can act as cheap sensors.

### How it differs from Google Maps

Google Maps already has incident reports and rerouting, so we must not claim it lacks those. The honest differences:

| Situation | Consumer navigation | Our system |
| --- | --- | --- |
| Many drivers pick the same shortcut | Each driver is routed separately, so a shortcut can overload | Authority assigns a split across routes |
| Planned closures (VIP movement, procession, roadworks) | Often learns after traffic changes | Authority enters it in advance |
| Signal changes | Cannot control or announce signals | Directly linked to signal control |
| Ambulance corridor | Not supported | Operator can clear a path |
| Vehicle type | Mostly car-focused | Different advice for two-wheeler, auto, bus, truck |

**One line:** consumer navigation helps one driver. We coordinate everyone, and we know what the signals will do.

### The discipline and awareness idea

The thought: repeated, well-designed messaging can slowly change behaviour, as seen in Indore's cleanliness campaign. In the app, that means short tips and rules shown at safe moments, plus a gamified section.

**Rules we should keep so the idea survives questions:**

1. **Nothing on screen while the vehicle is moving.** Use loading screens, pre-trip and post-trip screens. Live alerts while driving must be short voice messages.
2. **Reward real behaviour, not screen time.** Points for following an assigned diversion, a verified report, or choosing an off-peak departure.
3. **Make cheating hard,** for example confirm route-following from location data.
4. **Do not claim it works.** Call it a hypothesis and test it in simulation.

**How to make it measurable:** add a **compliance rate** setting to the simulation, meaning the share of drivers who follow an advisory. Run the scenario at 0%, 20% and 60% compliance and show the delay saved at each level. Then the message becomes: "Better awareness raises compliance, and here is what that is worth in minutes and CO2."

### Who is the user

- **Primary: the traffic control room operator** (dashboard). This is who the problem statement describes.
- **Secondary: drivers**, reached through the app, roadside boards, SMS or radio.

### How to keep it small

Build a simple **mobile web page (PWA)**, not a native app. Three screens: (1) alert and route, (2) one-tap report, (3) rewards with tips on the loading screen. In the demo, simulated vehicles represent app users, so no real users are needed.

---

## 10. India-specific edge cases we could simulate

We should research and pick only **three or four**.

| Edge case | How to build it in SUMO (idea) | Priority |
| --- | --- | --- |
| Illegal parking or breakdown | Stop a vehicle on a lane for several minutes | High |
| Waterlogging | Lower speed on, or close, a road section | High |
| VIP movement or procession | Close a road or hold signals for a set period | High |
| Ambulance | Emergency vehicle type, and the system clears its path | Medium |
| Bus stops blocking the road | Bus stops with long waiting time | Medium |
| School or office peak | Traffic demand that rises and falls with time | Medium |
| Speed control | Change a road's speed limit during the run | Low |
| Cattle on the road | A stopped obstacle, same as parking | Low |

**Vehicle "bad habits"** can be approximated using settings on each vehicle type, for example speed variation, impatience, random driving imperfection, and small vehicles using gaps between lanes. **\[verify exact setting names in the SUMO docs\]** We make a few driver personalities (careful, aggressive, two-wheeler, heavy truck) and mix them. We should say honestly that this is hand-calibrated, since detailed Indian vehicle-level data is hard to find.

---

## 11. Technical shape (high level)

| Piece | What it does | Tool idea |
| --- | --- | --- |
| Simulation | Road network, vehicles, signals, incidents | SUMO, network imported from OpenStreetMap |
| Control link | Read data and apply actions live | TraCI (Python) |
| Detection | Flag jams from speed, queue, occupancy | Simple thresholds |
| Prediction | Forecast near-future traffic | Gradient boosting or a small LSTM on recent history |
| Decision | Choose signal, diversion, advisory | Max Pressure plus a route-splitting rule |
| Backend | Connect everything, push live updates | Python, WebSocket |
| Dashboard | Operator map, recommendations, comparison | Web map (Leaflet or MapLibre) |
| Driver app | Alerts and reports | Mobile web page (PWA) |

**Same map everywhere:** import the area from OpenStreetMap into SUMO, and draw the same OpenStreetMap on the dashboard and the app. SUMO's Python library can convert between simulation coordinates and real latitude/longitude, so vehicles can be drawn at the right place on a normal web map. This also means we do not need the SUMO window in the demo, which gives a better-looking result without changing SUMO's code.

**Important design choice:** do not modify SUMO itself. Build around it. Modifying a simulator is slow and risky in 36 hours.

**Phone as a vehicle:** link a phone to one simulated vehicle ("Phone user 1"). The phone shows that vehicle's trip, receives alerts through a live connection, and its report button creates an event in the simulation. Feeding real phone GPS into the simulation is possible but fragile, so it is not for the first demo.

---

## 12. Scope: vision versus 36 hours

| Our full vision | What we build in 36 hours |
| --- | --- |
| Many Indian edge cases | 3-4 scenarios |
| Large real area | One small neighbourhood, a handful of junctions |
| Detailed driver behaviour | 3-4 driver types from settings |
| Phone as a live node | One or two phones linked to simulated vehicles |
| RL baseline and controllers | Fixed timer baseline, Max Pressure as our controller |
| Emergency and speed control | One ambulance scenario, one speed-limit change |
| Full gamification | Simple points screen and loading-screen tips |

**Priority order**

- **Must have:** SUMO network with mixed traffic, an incident, detection and prediction, signal and diversion response, baseline comparison, map dashboard.
- **Should have:** CO2 numbers, compliance-rate experiment, basic driver app.
- **Nice to have:** bus priority, ambulance corridor, voice alerts.
- **Skip:** a full navigation app, heavy RL.

**Build order:** simulation and baseline first, then detection and prediction, then the response, then the dashboard, then the app last. If the first three are weak, the app will not rescue the demo.

---

## 13. Risks and honest limits

1. **Time.** The vision is large. Fix the core before touching the app.
2. **A scenario that does not hurt the baseline.** If our incident does not create a real jam in the no-action run, there is nothing to improve. Test this in the first hours.
3. **Prediction that is not connected to action.** The forecast must trigger the response, not sit on a chart.
4. **Simulation realism.** Indian traffic is hard to model. We say so openly and call our setup a calibrated approximation.
5. **Adoption.** A real city needs many app users. Rollout idea: start with fleets (buses, autos, delivery), then the public.
6. **Unverified numbers.** Quote Bengaluru figures as police statements, not facts.
7. **Demo failure.** Record a backup video of a full run.
8. **Scope creep accusations.** Keep the dashboard as the star. The app is "how recommendations reach people."

---

## 14. Open questions for the group

Please discuss and write your answers in comments.

1. **Identity:** are we primarily (a) an operator decision-support system with a driver app as a supporting piece, or (b) a two-sided platform? My recommendation is (a).
2. **Area:** which small area do we simulate? A place we know (so we can describe real problems) is better than a random one.
3. **Incidents:** which three or four edge cases from section 10 do we commit to?
4. **Prediction:** simple model (trend plus gradient boosting) or a small neural network? Which are we able to finish and explain?
5. **Diversions:** how do we choose the split percentage? A fixed rule, or searched automatically?
6. **Compliance experiment:** do we include it? It is original but adds work.
7. **RL:** include it as an extra comparison, or skip it entirely?
8. **App:** web page only, or something more? Who builds it, and when do we cut it if we run behind?
9. **Pitch:** what is the single sentence we want judges to remember?
10. **Team split:** who owns simulation, ML, backend, dashboard, app, and report?

### Candidate pitch lines to react to

- "Bengaluru's system reacts at the signal. Ours predicts the jam, coordinates signals, diversions and advisories, and proves the saving including CO2."
- "Google tells you the way. We manage the road."
- "Less waiting means less fuel burned. We measure both."

---

## 15. Glossary

- **SUMO:** open-source software that simulates individual vehicles on a road network.
- **TraCI:** the interface that lets a Python program read from and control a running SUMO simulation.
- **OpenStreetMap (OSM):** free, community-made map data. We use it to create the road network.
- **Baseline:** the "do nothing" run we compare against. Here: fixed-timer signals and no advisories.
- **Fixed-timer signal:** a traffic light running a preset schedule.
- **Adaptive signal:** a traffic light that changes timing based on current traffic.
- **Max Pressure:** a simple rule that gives green to the direction where relieving traffic helps the most.
- **Reinforcement learning (RL):** a method where a program learns by trial and error. Powerful but slow to train.
- **Diversion:** sending some vehicles onto another route.
- **Advisory:** a message telling drivers what to do or avoid.
- **Compliance rate:** the share of drivers who actually follow an advisory.
- **PWA:** a website that behaves like an app on a phone.
- **Heterogeneous traffic:** traffic made of many different vehicle types.
- **CO2 saved:** the drop in carbon dioxide from less idling and less waiting. Ties to our TERRA track.

---

## 16. Sources we used (to re-check before presenting)

- News reports on Bengaluru's adaptive signals (Deccan Herald, Patrika, Cartoq, PTI via Siasat).
- IIIT Bangalore: adaptive traffic control project and the Traffic Interventions GitHub package.
- IIT Madras: seminar and article on signal control for heterogeneous, less lane-disciplined traffic.
- Papers on updating SUMO for lane-less traffic (SimTram) and calibrating SUMO for Indian traffic.
- GitHub: SUMO-RL, RESCO, sumoITScontrol.

**Next step after this discussion:** agree on the final problem statement in one paragraph, freeze scope, then write the architecture diagram and a 36-hour task plan.
