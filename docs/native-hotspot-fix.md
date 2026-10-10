# Native hotspot integration repair

Confirmed locally: when capabilities returns 404, the 1.2.0 client incorrectly
assumes v1 and requests `/api/world` before claim. Its non-200 response produces
the reported map message. A failing regression reproduced this exact path;
the fixed client discovers existing v2 phone routes from public `/openapi.json`
without consuming a code or requesting operator geometry. This establishes the
compatibility defect, not the actual status of Prakhyat's running process.

Diagnostics log method, origin/path and HTTP status, never query strings,
request bodies, token headers, join codes or response bodies. Transport failures,
map 401/403/404 and invalid map JSON now have distinct messages.

The inspected Android manifest allows cleartext HTTP and INTERNET. Installed
phone was 1.2.0. QR parsing accepts `/operator/phone.html#code=...` and retains
the host port. Phone claims use actual run_id/session_id/vehicle_id/token fields.
Sharing remains off until a worker-confirmed consent ACK.

## Required host patch

The coordinator branch `feat/kush-demo-polish` includes compatible public
`/api/v2/capabilities` and driver-bearer `/api/v2/phones/world` handlers in
`backend/simulation/app.py`. `/api/v2/world` remains operator-authenticated.
Inspect and port those handlers into Prakhyat's newest local checkout; do not
reset, overwrite or blindly merge his unpushed experiments. Driver geometry
requires session_id and run_id plus the phone token, uses driver_context and
returns WORLD with phone_edge_registry only. Preserve existing worker ownership.
Missing driver geometry is now reported explicitly after claim.

Restart only the unified host after integrating Python changes. On Prakhyat's
hotspot laptop set TRAFFIX_PORT=8006 and TRAFFIX_LAN_ADDRESS=192.168.137.1 before
running `python -m scripts.run_unified` in its project environment. Provision
accounts privately. Confirm that interface actually exists and the private
firewall permits TCP 8006. Leave the other demo processes alone.

## Physical acceptance still required

Install the hotspot-fix APK as an update. Connect the handset to Prakhyat's
hotspot. Generate a NEW invitation (120 wall seconds, single use), scan, Join.
Confirm assigned vehicle and map, live motion, sharing initially off, then
enable and confirm accepted phone sample count on the host. Reset and request
a new invitation; disconnect must stop sharing, reconnect requires renewed
consent. Do not use USB reverse as proof of the hotspot path.

The coordinator's current machine has no 192.168.137.1 interface, so laptop or
mock-client tests here do not establish that physical hotspot gate.
