# Operator workspace

Served by `backend.simulation.app` at `/operator/index.html`. All script, font,
geometry and Three.js assets are local. No package build or external CDN is needed.
The approved light workspace uses the existing local Traffix font and shared tokens.

The UI requires an explicitly configured host account. Viewer mutations are disabled;
the server is authoritative for role, lease, revision and execution validation.
Tokens live in session storage, not URLs. Signing out revokes the session. Reloading
fetches the current run without resetting it. Failed commands are shown and never
automatically retried. LAN HTTP uses `getRandomValues` for command IDs because
`randomUUID` may be unavailable outside a secure browser context.

One drawer opens at a time: Locations, Traffic, Events, Control and Results. Camera
orbit/pan/zoom, selected vehicle follow/first-person and minimap movement are local.
Vehicle classes use the existing low-poly model geometries. Simulator geometry and
signal indications are display truth, not detector inputs. Event preview is labelled
not applied; application needs a separate action. The host validates all event inputs.

Checks:

```text
node --test web/src/operator/protocol.test.mjs
node --check web/src/operator/app.js
node --check web/src/shared/scene.js
```

Current boundaries: the two additional locations display their unreviewed status;
there is no geometry preparation flow for those packs. The signal drawer identifies
movement indices, not named turn movements. The minimap shows the selected vehicle
and camera target footprint; route polylines require a route geometry API. Evidence
is displayed from the host manifest and exported as JSON; the UI does not invent a
matched comparison or forecast benefit. Camera/vision configuration, saved-scenario
editing, and a separate administration landing page are not implemented here.
