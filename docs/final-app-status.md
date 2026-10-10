# Final native app integration status

10 October 2026. Coordinator branch `feat/kush-demo-polish`.

- App version 1.2.0 / Android versionCode5. Local release APK build is in progress.
- Added public v2 capabilities discovery, driver-authenticated map loading after claim, v2 claim/WebSocket/own-state paths and native/web `#code` invitation support. Legacy response-host paths remain supported when discovery returns404.
- Driver world never uses an admin token. Own-state rejects another run/vehicle. Edge-ID route paths map to reviewed world geometry.
- Ride displays active/scheduled operator restrictions on its assigned route; active restricted roads highlight red. These events currently reduce simulated edge speed, not physically close a lane or automatically change the route. Route changes still need driver acceptance and worker ACK.
- Paused runs keep authenticated own-state fresh. Lost connection disables live guidance and probe sharing. Reconnect requires renewed consent. Reset/expired session requires a new invitation.
- 14 mobile tests passed; lint/typecheck passed. Real HTTP/WebSocket smoke using the actual TypeScript client and SUMO host passed: scoped map and route, preview no effect, apply alert, explicit consent/probe/withdrawal, event end clears alert, reconnect and reset. This is a network adapter test, not yet a physical handset claim.
- Host for this sprint: http://127.0.0.1:8013/operator/index.html. Phone reaches localhost8013 through `adb reverse tcp:8013 tcp:8013`. Existing8004/8005 services are preserved. Current machine has no active192.168.137.1 interface, so other laptop/hotspot access is not established.
- Private local demo account settings live in the host checkout's ignored `.cache/private/final-demo-accounts.json`. Do not publish passwords/tokens. Host must remain running.
- Tests: from mobile-app, `npm run test`, `npm run lint`, `npm run typecheck`; integration: set `TRAFFIX_TEST_HOST` and `TRAFFIX_TEST_ACCOUNTS`, then `node tests/unified-smoke.cjs` against a disposable demo run. The smoke resets the run and is unsuitable during a presentation.
- Native speed recommendations and personal carbon reduction remain unavailable unless the server supplies validated scoped evidence. Do not relabel emulated participation as real driver compliance.

Final build/physical device results will be appended after installation.
