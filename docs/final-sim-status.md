# Final simulation integration status

Contract frozen for native app integration (implementation/testing in progress).

- Public `GET /api/v2/capabilities`: `api_version`, `phone_protocol_version: 1`, `capabilities` object with `driver_world`, `own_route`, `route_events`, `driver_alerts` booleans; `endpoints` object.
- Driver bearer `GET /api/v2/phones/world?session_id=...&run_id=...`: existing WORLD object directly, with roads/routes/center; no fleet or admin state. Requires claimed session and matching run.
- Driver bearer `GET /api/v2/phones/state` same query: existing reply plus `route_id` (string or null), `route_path` (ordered SUMO edge ID strings), `vehicle_type` (string or null), `role` (rider/auto/delivery/driver), `paused`, `ended` (run booleans), `lifecycle` (active/arrived/unknown), `route_events` and `alerts` arrays.
- Event rows: `event_id`, `edge_id`, `kind`, `effect`, `start_s`, `end_s`, `severity`, `status`. `alerts` contains active speed restrictions only. `route_events` retains matching scheduled/active/ended events. No event-driven rerouting or lane closure. Claim reply and phone WebSocket v1 frames remain unchanged.
- `route_path` uses the same edge IDs as WORLD roads. Driver world is geometry; only own-state carries a bound vehicle.
- Base: origin/feat/prakhyat-unified-simulation 7733a08. Other-laptop experimental algorithms and reported evidence have not been imported.
- Core readiness: implemented. Focused acceptance: `../trafixx/.venv/Scripts/python.exe -m pytest tests/test_driver_v2.py tests/test_simulation_v2.py tests/test_unified_phone_guidance.py -q --tb=short` — 13 passed (11.95 s), one Starlette TestClient deprecation warning. Includes real SUMO operator Preview/Apply/End → driver alerts, frozen v1 frames, zero phone uplinks without consent, reset token rejection, driver map auth and own-route scope.
- Source files `flow_policy.py`, `speed_advice.py`, `queued_pressure.py` are absent in this verified base. Do not advertise other-laptop experiments or replay artifacts as installed here.
- Core commit and final expanded tests: pending.
