# Traffix final presenter guide

1. **Traffix:** “We built a shared traffic response testing environment around LIG Square. SUMO runs locally. The illustrations are concepts, not field photographs.”
2. **Problem:** “Changing a signal without checking downstream space can move the queue. Mixed vehicle classes and sparse observations make the response harder.”
3. **Solution:** “We connect observation, congestion evidence, bounded response and matched comparison. One bound vehicle identity joins phone and dashboard. Missing data stays unknown.”
4. **Architecture:** “One worker owns TraCI. Authenticated API requests enqueue commands. The dashboard and phones share the host, while the submission frontend is separate.”
5. **Pressure algorithm:** “For each safe phase we score normalized upstream queue minus downstream occupancy. The worker preserves clearance and checks the target again. This is reactive pressure control.”
6. **Detection and prediction:** “The detector needs sustained fresh slowdown, including evidence through a serving green. We already have forecasting candidates at 120/180/300 seconds, but useful accuracy and predictive-control benefit still need held-out validation.”
7. **Results:** “Across held-out seeds 51 and 52, pressure reduced mean journey time 11.31% and modeled CO2 7.48%. Every scheduled trip completed under each policy. Those are averages of paired reductions in finite synthetic cohorts. We exclude the incomplete stress baseline.”
8. **Demo:** Show policy selection, a new worker-confirmed action, bound driver identity and consent, then saved pressure seed 51 or52 with its same-seed fixed baseline. Say recorded for playback. The saved screenshot shows the UI, not the benchmark performance. Verify latest native integration status before claiming a real handset demonstration.
9. **Roadmap:** “The next gates are native device integration, sustained-overload and fairness tests, validated forecasts, and field calibration.”

If asked for 15–20%: “A later handoff reports a selected 15.28% flow case, but its source and evidence were unpushed on another laptop. Our independently inspected local headline is 11.31% across two held-out seeds.”

If asked whether phones measured Indian roads: “Real connected phones relay simulated vehicle observations in this prototype. Field GPS validation remains.”

If asked whether every driver benefits: “No. We retain P95 waiting and negative cases. Development seed 42 worsened tail waiting despite improving the average.”
