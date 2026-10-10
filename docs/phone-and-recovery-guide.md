# Traffix: start, reconnect and connect a phone

## On this laptop

Double-click `Start-Traffix.cmd` in the project folder. If the host is already running, it prints the dashboard URL. Otherwise keep its terminal open. This laptop's ignored private settings select the installed Python runtime, the existing demo accounts and hotspot address; credentials are never committed.

Open http://127.0.0.1:8005/operator/index.html. Refresh after updates. A host restart invalidates sessions: sign in again. The configured local operator is `demo`; use the existing local demo password. Registered team accounts are preserved, but a viewer still needs owner approval for simulation control.

Start requests an available control lease. Continuous viewing uses **New scenario → Explore**. Finite experiments stop for result accounting. At completion, **Restart default simulation** saves the current run, resets to everyday/fixed Explore and starts it. Results remain available. Nothing resets automatically during a disconnect or silently discards a completed experiment.

If the connection fails, **Reconnect** retries loading the host; navigation remains readable from the cached scene, while mutations remain disabled until fresh state arrives. If the host has stopped, run `Start-Traffix.cmd`; a browser cannot restart a dead server. Sleeping the laptop also pauses a local demo.

## Real phone on the laptop hotspot

1. Join the laptop hotspot from the phone. Its host address currently is `192.168.137.1`.
2. Sign in as an operator and start traffic. Select a car first if you want to bind that specific vehicle.
3. Open **Control → Create one-use join code**. Scan the QR, or open the displayed link. The code expires after 120 wall seconds and can be claimed once.
4. On the phone, press **Join this journey**, then opt into **Share simulated probe data**. Speed and road come from the assigned SUMO vehicle; physical GPS is not used.
5. The dashboard displays connected/sharing status and accepted uplink counts. Connected phone vehicles receive a PHONE label; fresh phone observations can colour roads even without fixed-sensor observations. Consent withdrawal removes contributions. Two fresh probes are still required by the optional guidance rule, and a driver must Accept a reviewed route; a single connected phone is not proof that rerouting will occur.
6. After a run reset, the phone shows stale state and returns to the join form. Ask for a new code. A dropped connection disables sharing; reconnect, then consent again.

Host listeners are **127.0.0.1:8005 and 192.168.137.1:8005**, served by one process/TraCI worker. Campus/public interfaces are not bound. Windows firewall rules were not altered: if a handset cannot load the URL, check hotspot membership and a Private-network firewall allowance for the selected Python runtime. Do not disable the firewall or expose this HTTP demo publicly. Physical-handset reachability remains unverified until a teammate tests it.

## Another laptop

Use Python 3.12 and `scripts/setup_unified.ps1`. Configure operator credentials in an ignored local file, then:

```powershell
./scripts/start_unified.ps1 -Python './.venv/Scripts/python.exe' -LanAddress '192.168.137.1' -AccountsFile './.cache/private/host-accounts.json'
```

Replace the hotspot IP with that laptop's private Wi-Fi/hotspot IPv4. The launcher binds only localhost and the explicit private address. It rejects public, loopback, link-local and unspecified LAN addresses. Native mobile API integration remains Kush's separate client; this browser probe is an integration/demo adapter.

## Rendering and evidence

The dashboard now consumes the existing 5-Hz authenticated stream, with HTTP polling as fallback. Rendering interpolates a 240-ms buffered snapshot history, handles angle wrap and stops at the newest real sample during stale input. It does not extrapolate made-up vehicle positions. Scene rendering is capped at 30 fps and static building shadows are cached; these are targets/settings, not measured guarantees on every GPU.

API version remains 2.0. Additions: authenticated `GET /api/v2/phones/connection`, authenticated local PNG `GET /api/v2/phones/qr?url=...`, and optional `vehicle_id` in the existing invite POST. No frozen v1 phone message format changed. Example invite body: `{"vehicle_id":"car.70"}`. The QR join page uses a fragment code, strips it from the address after loading and keeps its claimed session token in memory. No phone observation is fabricated by the backend.
