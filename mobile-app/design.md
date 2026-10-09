# Traffix driver experience — first native build

The mobile app uses its own colourful identity. The operator simulation retains
the previously approved white/grey/charcoal identity. Share terminology, data
meaning and interaction rules across both products.

## Visual system

| Token          | Value     | Use                                        |
| -------------- | --------- | ------------------------------------------ |
| Canvas         | `#FFFCF7` | Warm cream page background                 |
| Ink            | `#26243C` | Headings and primary information           |
| Secondary text | `#655D78` | Supporting explanation                     |
| Primary        | `#6C4DFF` | Main actions, selected tab, vehicle marker |
| Lavender       | `#EEE8FF` | Route guidance, hero, selected state       |
| Mint           | `#D8F5EA` | Impact and confirmed route surfaces        |
| Peach          | `#FFE4D6` | Sample participation card                  |
| Yellow         | `#FFF0BB` | Learning and driving advice                |

Use colour with text or icons; never rely on colour alone for connection or
route status. Original road-island art and road-shaped T icon are included in
assets. Generated imagery decorates onboarding; actual telemetry drives the map.

Layout: portrait, native safe areas, 22-point page inset, 12-point two-column gap,
20-point card padding, 54-point primary button minimum height. Cards use 22–28
point corners; actions 17. Native text sizes are 32 for page heading, 19 for card
heading, 14 for body and 12 for supporting details. Small labels never carry the
only explanation of an important state. Content scrolls; navigation remains at
the bottom. Large text remains enabled and buttons permit wrapped text.

## Navigation and priorities

| Destination | User's question                           | Main action                            |
| ----------- | ----------------------------------------- | -------------------------------------- |
| Home        | How do I get started?                     | Join a simulated ride / Open your ride |
| Ride        | Where is my vehicle and what should I do? | Review guidance and choose             |
| Learn       | What is one useful driving habit?         | Read a short lesson                    |
| Settings    | How do I connect and control my session?  | Check host / leave vehicle             |

The operator issues the vehicle invitation. The phone never asks the driver to
pick arbitrary simulation IDs. Scanning and pasting both lead to the same join
screen; a deep link prefills fields but cannot consent or claim automatically.
After Join, open Ride. Keep the map, current speed and current route above less
urgent reporting and learning content. A route offer gives two explicit choices;
show server confirmation before describing a changed route.

## State rules

| Condition                   | Display and behaviour                                     |
| --------------------------- | --------------------------------------------------------- |
| No invitation               | Explain how to ask the operator; allow manual host setup  |
| Expired/used invitation     | Explain failure and request a new unbound invitation      |
| Camera denied               | Preserve manual code entry                                |
| Joining                     | Single pending action; prevent duplicate claim            |
| Connected                   | Show fresh own-vehicle frame; sharing remains off         |
| Stopped vehicle             | Show **0 km/h**, not an unavailable dash                  |
| Paused simulation           | Explain that the operator paused it                       |
| Stale frame                 | Hide live marker and speed; invalidate route acceptance   |
| Sharing requested           | Wait for acknowledgment before showing On                 |
| Offer expired/wrong vehicle | Do not offer acceptance                                   |
| Accept sent                 | Say waiting; continue showing current assigned route      |
| Rejected action             | Explain reason; retain original route                     |
| Socket loss/background      | Withdraw sharing and action eligibility                   |
| Reconnect                   | Authenticate saved session; require new sharing opt-in    |
| Run reset/session invalid   | Clear old session; request a fresh invitation             |
| Arrived                     | Explain completed journey; disable active journey actions |
| Unavailable impact          | Show dash and reason; no fabricated CO₂/time saving       |

## Next integration

The shared API must define a trip, scoped identity, prediction timestamp/horizon,
source/confidence, advisory expiry, decision acknowledgment and baseline evidence.
Public access requires HTTPS. Background mobile notifications need separate
permission and delivery/expiry handling. Real trips require an explicit GPS
permission/consent flow and privacy model. Camera activity classification is not
added by simply requesting QR scan permission.

Replace prototype role/Route A/Route B labels with real trip destinations after
the host supplies verified names. Keep permission choices and unknown-data states
visible when extending the app. A local YOLO detector must label its observations
and uncertainty; it must not present an unverified report as a confirmed event.
