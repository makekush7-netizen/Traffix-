# Traffix UI direction — accepted direction, revision 2

Status: Kush accepted the revision-2 visual and interaction direction on 9 October
2026. The generated images are composition references, not screenshots of implemented
functionality. The harness PRD and handoff requirements govern behavior and edge cases.
References: `design-reference/simulation-hawk-v2.png` and
`design-reference/admin-hawk-v2.png`.

**Revision 2 supersedes the original generated concepts.** Kush supplied screenshots
showing Hawk's actual light workspace with a charcoal rail. The late overrides in
Prayas/frontend/src/workspace.css (lines 216–231) agree with those screenshots.
Use those final tokens, not the earlier navy/cyan variables in that file.

## Shared design system

| Token | Proposed value |
|---|---|
| Page background | #f7f7f8 |
| Panel / drawer | #ffffff |
| Secondary surface | #f0f0f3 |
| Main text | #25262c |
| Secondary text | #70717d |
| Border | #e1e1e7 |
| Primary action | #344653 with white text |
| Navigation rail | #24262e |
| Selected rail surface | #eaf0f3 with pale-cyan icon |
| Spacing | Multiples of 8px |
| Panel corners | 8px |

Use one local font family with one icon family and shared controls. Check actual
contrast and keyboard/touch accessibility during implementation; image concepts
cannot establish accessibility. Avoid using semantic signal colours as generic
button accents. Signal state, congestion, selected route and data freshness have
distinct meanings and legends.

## Concept 1: simulation workspace

The simulation occupies the viewport. A collapsed overlay rail has five tools:
Location, Traffic, Events, Control and Results. Clicking opens a single drawer;
hover/focus supplies explanations. Core functionality is never hover-only.

The top bar contains selected location, connection/provenance, New scenario and
Compare. Starting is part of completing scenario preparation, not a permanent giant
Start button. Simulation state stays visible as concise contextual text; do not
hide a genuinely paused/disconnected system. A pause-for-inspection command remains
available in the overflow or Control drawer with Resume when applicable.

Remove the prototype's prominent 1x/2x/4x controls from this design. Advanced simulation
pace is a target with measured achieved simulated-seconds/wall-second, overload feedback
and explicit limits. It must be implemented and tested, not just illustrated. Replay
transport is separate from live simulation pace. Do not increase actual vehicle speeds
to imitate faster simulation. Explore mode can use continuing scheduled arrivals;
experiment mode must end, drain and retain valid cohort results. New scenario has
explicit behavior around existing sessions and results. Camera controls remain separate
from traffic controls.

The minimap stays bottom right with north, selected vehicle, route and camera footprint.
Map clicks move the camera; they do not teleport vehicles. An expandable junction
overlay shows movement arrows and current indications instead of a row of raw dots.

## Concept 2: an event task

An Events drawer uses Choose event, Choose route/area, Schedule, Preview, Apply.
The generated image shows the Preview stage. Nothing changes in the engine before
the operator applies the validated event. Advanced parameters stay folded.

Only one task drawer is open. The minimap and top controls remain in stable positions.
Cancel removes the draft, not existing events. A preview has a visible not-applied label.

## Concept 3: administration

Overview, Locations, Scenarios, Runs and Access form the admin navigation. The central
workflow is selecting inputs and opening a run. Detailed run evidence and comparison
are available from Runs, rather than dominating the simulation viewport.

Comparison stays unavailable until selected runs have compatible manifests and are
complete/integrity-valid. Host connectivity is separate from simulation run state.

## Consistency requirements

- Same tokens, control sizes, focus states, icons and terminology across both modules.
- Same location ID, run ID, vehicle ID and advisory identity across connected views.
- Start/Pause, New run, Preview and Apply always have the same meaning.
- State is acknowledged by the server; colour changes cannot imply an unconfirmed action.
- Advanced settings follow the same expandable pattern everywhere.
- Keep controls reachable at smaller widths; map overlays reposition rather than overlap.
- Operator and driver interfaces share meaning and state, while their layouts suit their tasks.

## Implementation sequence after approval

1. Shared tokens and primitives, simulation shell and existing state integration.
2. Readable roads, movement-linked signals, camera controls and minimap.
3. Location/traffic/event drawers with validated server commands.
4. Admin run preparation and evidence views.

The composition and interaction direction is accepted. Small generated details
such as icon shapes or example scene geometry are illustrative, not exact build assets.
Correct the generated simulation's selected Events item when its Response drawer is
open: Control must be selected. Both views must share one Traffix logo and control
component system. A closed drawer restores the map beneath it; do not reserve a large
empty white gutter. Preserve map position when drawers open or close.

## Interaction rationale and review

- Prioritize selecting a location, creating traffic, adding an event and examining the
  controller response. Surface these tasks rather than internal engine switches.
- Secondary settings use progressive disclosure; retain accessible click and keyboard
  access, never hover-only controls. [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/).
- Display authoritative status and action feedback, including real pauses and failures.
  Removing a large pause badge must not conceal a stopped system. [NN/g system status](https://www.nngroup.com/articles/visibility-system-status/).
- Draft events offer Cancel and explicit Apply; explain how applied events can be ended.
  [NN/g user control](https://www.nngroup.com/articles/user-control-and-freedom/).
- Generated graphics are a composition reference only. Validate contrast, motion,
  screen-reader labels, camera navigation, signal meaning and live functionality in code.
