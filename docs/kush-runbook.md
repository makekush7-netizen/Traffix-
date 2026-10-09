# Traffix: Kush's coordinator handoff

The project is now **Traffix**. Existing starter filenames and historical specs retain their original spelling.

## Start the two-phone gate on Windows

From this repository directory:

```powershell
.venv\Scripts\python.exe -m pytest -q
ipconfig
.venv\Scripts\python.exe scripts/run_fixture.py --lan-ip <actual-laptop-hotspot-IP>
```

The prepared local virtual environment reuses the installed Python dependencies and includes qrcode.
For a fresh laptop, create a virtual environment and install `requirements.txt` plus `httpx` (FastAPI TestClient dependency).

1. Turn on the laptop hotspot and connect both physical phones. Recheck `ipconfig` after enabling the hotspot.
2. Open `http://localhost:8000/setup` on the laptop. Enter `http://<actual-IP>:8000`.
3. Generate rider and auto join codes. Scan each QR on a different phone, or open `/driver` and manually enter its code.
4. Both phones must show their distinct simulated role and a frame every five simulated seconds.
5. Sharing starts OFF. The laptop status must show zero accepted samples until a phone enables sharing.
6. Enable sharing; the accepted sample count must increase on new frames. Disable sharing and check it stops after any in-flight sample.
7. Switch a phone briefly to airplane mode, then reconnect. It must retain the same role. A reload uses sessionStorage; closing the tab or restarting the server requires a new claim.
8. Keep screens foreground and awake. Heartbeats occur every two wall seconds; the server closes idle sockets after six wall seconds.

If Windows prompts for firewall access, allow only the private demo network. Venue Wi-Fi can isolate clients; a laptop hotspot is preferred. No firewall settings are changed by the launcher.

Codes last 120 wall seconds and work once. Setup/code creation/status endpoints are laptop-loopback only. Generate a fresh code if one expired. An occupied role cannot be claimed again; reconnect with its existing browser session. Restart the fixture server to clear all roles and start a new run.

## Implemented and verified

- Contract examples validate against their schemas; invalid speed, extra fields, and invalid choices are rejected. Shared contracts were not changed.
- FastAPI fixture server: health, bootstrap, claims, authenticated WebSocket, bound frames, filtered reconnect snapshot, acknowledgments, reporting toggle, heartbeat expiry, message size/rate limit, Host/Origin checks.
- Disposable phone/setup pages inside `backend/`, leaving Urvashi's `web/` ownership available.
- Probe gateway retains issued frames and admits exact, fresh, once-only echoes for the authenticated session. Issuing a frame creates no observation. Accepted samples expose only phone data.
- Single-owner adapter worker with command queue, pause/rate controls and command-ID deduplication. Starts paused. Adapter construction, steps, commands and closure all run on the owner thread.
- JSONL event sink redacts secrets and preserves event-ID deduplication across reopening.
- Pure control guards preserve clearance and min/max green bounds, require receiving capacity and valid accepted diversion, and request safe-boundary restoration.
- Replay selects recorded frames at or before live time and rejects missing/mismatched provenance fields.

## Remaining integrations and limitations

This is a runnable **fake-frame gate**, not a completed SUMO traffic demo. No real-phone gate has been witnessed by Codex.

SUMO, SUMO_HOME and TraCI are absent on the current laptop. Nandani's network, actual-ID registry, demand, route eligibility and fixed detector feeds are not present. Prakhyat's observation/detection interface and Urvashi's production UI are also absent.

The worker, control guards, event sink and replay are independently tested foundations; they are not wired into the fixture clock/server. No autonomous policy or signal command is applied. Worker idempotency is in-memory within one run. The log is an audit sink, not a durable command transaction store.

Fixture snapshots deliberately show no aggregate observations/forecasts/roads and no baseline. Metrics are incomplete fixture placeholders, not results. Status lists accepted samples retained in the latest 60 simulated seconds. The gateway expires retained frames after 15 simulated seconds. A downstream observation aggregator is still required.

Production integration must add separate operator authentication, operator-only reset, complete mode/expiry/recovery state machine, worker-applied acknowledgments, advisory lifecycle, safe program switching at verified cycle boundaries, append-only run manifests/logs, and validated SUMO route execution. Replay manifest keys (`network`, `demand`, `scenario`, `sensor_mask`, `seed`, `sumo_version`) are a local interface to align with the team's actual recording format.

No tokens are printed or placed in QR links. The fixture uses plain HTTP for synthetic data on the local demo network. Run a single server process. All claims are volatile and invalidated by restart.
