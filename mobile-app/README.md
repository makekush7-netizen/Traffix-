# Traffix native driver app

Kush's Android client; Prakhyat owns the unified simulation host/admin module.
This client already works against the existing **v1 phone bridge**. It is a
simulation app: the phone is bound to a SUMO vehicle, rather than measured by GPS.
No frozen contract or existing dashboard is changed.

## User flow

**Home → Join ride → scan or paste operator invitation → Ride → optionally share
samples → review an offered route → accept → wait for server confirmation.**
Four Expo Router destinations: Home, Ride, Learn and Settings, with a persistent
root session owner. Cream surfaces, violet primary
actions, coral/mint/yellow supporting cards, consistent spacing and native safe
areas. Illustrations and the app icon are original generated assets; icons and the
local route map are SVG. QR camera access is requested only after choosing Scan.
Manual joining remains available if camera access is denied.

The Ride screen shows the assigned vehicle's fresh position, current simulated
speed, current route, sharing consent, optional reroute offer and unverified
slow-traffic report. Learn contains four short traffic tips. CO₂ savings and time
saved remain unavailable until the host provides a valid matched comparison.
Numeric recommended speed also awaits reliable signal-arrival data.

## Run on the connected Android phone

From the repository root:

```powershell
./scripts/run_response.ps1 -Port 8004
# In another terminal; use your SDK platform-tools/adb.exe if adb is not on PATH:
adb devices
adb -s YOUR_DEVICE reverse tcp:8004 tcp:8004
adb -s YOUR_DEVICE install -r mobile-app/builds/traffix-preview.apk
adb -s YOUR_DEVICE shell am start -n in.traffix.driver/.MainActivity
```

Open the operator dashboard at `http://localhost:8004/dashboard`. If an old run
has completed, reset it before inviting a phone. Add phone → choose a role → copy
its join code. In the app use `http://127.0.0.1:8004` as the USB host and paste the
code. For Wi-Fi, use the laptop's reachable LAN address and the same port; USB
forwarding is unnecessary. The laptop server must remain running.

Invitations expire after two minutes and are single-use. An occupied role requires
another unbound vehicle or a run reset. Joining does not enable sharing. Start the
simulation to see changing speed and position. Guidance requires the operator to
enable it and enough fresh phone evidence; a single phone does not guarantee an
offer. The existing demo rule is not a trained ML controller.

Deep links use `traffix://join?code=CODE&server=ENCODED_ORIGIN`. They prefill the
invitation and still require the user to press Join. The QR scanner also accepts
the existing dashboard HTTP invitation with `#join=CODE`.

## Development and rebuild

```powershell
cd mobile-app
npm ci
npm run typecheck
npm run lint
npm test
cd ..
./scripts/build_native_mobile.ps1 -Install -Device YOUR_DEVICE
```

Prerequisites: Node 22, Android Studio's JDK 21, Android SDK 36/build tools/NDK,
authorized USB debugging. The script copies the app into a short physical temporary folder to avoid
Windows CMake/Ninja path and drive-alias problems, builds ARM64, copies the APK
back and removes its successful build snapshot afterward. Expo
prebuild regenerates ignored `android/`; the local config plugin preserves the
network permission and CMake path setting. The standalone APK includes JS and
assets and needs no Metro process. It uses a **development signing key** despite
the Gradle release build type; it is a local preview, not a store release. iOS and
web have not been built or verified.

## Verification

- `npm run typecheck`: app and adapter TypeScript.
- `npm test`: wrong vehicle/run/pose, stale/expired advice, consent acknowledgment,
  duplicate frame echo prevention, rejected decisions, reconnect and run reset.
- `node tests/live-smoke.cjs`: actual adapter against a **disposable** response
  host on `127.0.0.1:8005`; this test plays, pauses and resets that host. It checks
  zero uplinks before consent, accepted samples, withdrawal, reconnect and reset.
  These are **emulated probes**, not proof of two physical phone connections.
- Existing backend phone bridge and demo tests remain independent.

## Integration boundary and remaining work

`src/client.ts` is the v1 transport adapter. It authenticates the session, keeps
monotonic message sequence numbers, echoes only issued frames with consent and
waits for server acknowledgments. `src/protocol.ts` validates origins, invitations,
vehicle frames and offer eligibility. SecureStore persists credentials and the
sequence. Backgrounding, socket replacement and reset withdraw local sharing and
action eligibility. Stale updates hide the live marker and invalidate advice.

Prakhyat must return the versioned API/mock in `docs/prakhyat-final-build.md`.
Then replace/extend this adapter for trips, scoped team access, calibrated
forecast/incident provenance, checked speed recommendations and saved comparison
results. Do not let the app submit vehicle identities, routes, signal commands or
timestamps independently. Native background push notifications, real GPS trips,
local YOLO camera inference and authenticated internet deployment are later work;
this build provides foreground offers over the existing WebSocket.

The preview permits local HTTP and rejects cleartext public hosts in the client.
Production needs server HTTPS, native network hardening, release signing and
dependency remediation. The dependency audit reported 28 findings
(18 high, 10 moderate); automatic suggested major downgrades are not applied.
Review the saved local audit before any public release.


## Personal preview 1.1.0

Home now greets the saved local profile name. Open the greeting or Settings →
Edit profile to choose a name, avatar and usual vehicle. This is device-local
personalization, not a server/cloud account. The operator still assigns your
simulated vehicle. Name validation accepts Unicode; no email or password needed.

Learn has four original offline illustrations, a quick check per lesson and
persisted completion. A correct answer enables saving the lesson; revisits are
allowed. Settings controls illustration visibility, Home tips and live speed
units (km/h or m/s), with connection help, privacy and profile erasure.

Activity records the last 20 simulation vehicles on this device, observed
arrivals and acknowledged sample counts. Reconnects/duplicate frames do not
create extra trips. An arrival counts only after an arrived frame is observed.
Counters are local records, not an official host history. Carbon saved remains
unavailable until a validated matched completed-trip comparison is supplied.

A short logo introduction appears on cold launch and dismisses after about one
second. It does not wait for the laptop network, loop, or play distracting motion.
The current lesson assets are static PNGs, not GIFs. All artwork is bundled.

Erase local profile clears personalization, preferences, learning and activity;
it does not leave the bound vehicle or erase operator records. To stop sharing
and leave, use the separate Leave vehicle action. Storage failures are displayed
without discarding credentials. No cloud login, real GPS or background push is
implemented in this revision.

Generated lesson images and full prompts: `assets/lesson-sources.json`.
