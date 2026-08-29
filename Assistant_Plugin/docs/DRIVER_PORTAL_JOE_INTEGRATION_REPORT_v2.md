# Driver Portal → JOE Presentation Layer, v2

**Architecture impact review. Analysis only — no code, no redesign, no
replacement portal.**

**Requested by:** Mike Zachary, 28 August 2026
**Subject under review:** `D:\Dispatch Operations\Code\cin-hybrid`
**Supersedes:** `DRIVER_PORTAL_JOE_INTEGRATION_REPORT.md` (v1, 27 August)

**Assumption, as instructed:** the Mission Record doctrine, the ownership
split, and the view-filter doctrine are accepted and intentional.

> v1 said plainly that it had not audited the interiors of
> `dispatch_detail.html` (1,226 lines) or `dispatch_api.py` (1,996 lines).
> **This version has read both.** Three findings below could not have been made
> without doing so, and one of them changes the recommended approach.

---

## Headline

**Two of the three things being asked for already exist in working form.**

1. The Mission Record is implemented — `get_load_bundle()` assembles one record
   from one store and returns sixteen facets of it.
2. **A deterministic view filter is already implemented and working** —
   `filterActivities()` at `dispatch_detail.html:996`. CURRENT / PICKUP /
   DELIVERY is that same mechanism at a wider scope, not a new one.
3. A 132-route REST API over the Mission Record already exists, including
   `GET /loads/<load_id>/bundle` — the exact door JOE needs.

What is genuinely missing is the JOE panel, the COMI display, and one link in
the record lifecycle (§8).

---

## 1. What remains unchanged

| component | file | why untouched |
| --------- | ---- | ------------- |
| Mission Record store | `dispatch/store.py` | it *is* the Mission Record |
| Mission Record models | `dispatch/models.py` | vocabulary already complete (§4) |
| Bundle assembly | `dispatch/services.py` — `get_load_bundle()` | one record, sixteen facets |
| Mission REST API | `portal/routes/dispatch_api.py` — **132 routes** | already sufficient for JOE to read |
| Scoring, incl. Route Risk | `dispatch/scoring.py:213` | already produces the value |
| Facility / broker intelligence | `portal/models/intelligence.py` | broker, customer, location, facility, route, return-route |
| Calendar Display | `pages.py:288` → `get_load_calendar()` | already a view over the Mission Record |
| Publisher queue | `portal/models/publisher.py` | Publisher owns production |
| Page shell | `portal/templates/base.html` (223 lines) | extended, not rewritten |
| **Activity filter mechanism** | `dispatch_detail.html:996–1012` | **the pattern the new filters should copy** |

## 2. What already aligns with each doctrine

### Mission Record Doctrine — aligned

`get_load_bundle(load_id)` gathers by key and copies nothing into a second
record. Sixteen facets: load, visibility, milestones, evidence, exceptions,
pods, retention, financials, settlement, assigned driver, assigned equipment,
activities, active drivers, active equipment, lane history, detentions.
Collected once, stored once.

### View Filter Doctrine — **already demonstrated twice**

This is the finding that most changes the shape of the work.

**`filterActivities(type)`** — `dispatch_detail.html:996`, with its controls at
line 533. Buttons carry `data-filter` attributes; the function toggles
visibility over data that is **already rendered**. No re-fetch. No second
query. No second record. Active state is reflected in the button styling.

**The calendar** — `get_load_calendar()` renders a different shape of the same
mission data through the same service.

Between them, the doctrine's headline — *One Mission Record, Many Views* — is
not an aspiration in this codebase. It is an existing habit, in two places,
that simply has not yet been applied to mission phase.

### JOE Communication Doctrine — aligned by absence

Measured: the strings `joe` and `assistant` appear **nowhere** in `portal/`.
The portal today owns display and holds no communication logic. That is exactly
the starting position the doctrine describes, and it means JOE is added by
insertion rather than by unpicking.

## 3. Existing functionality supporting the four named capabilities

| capability | where it already lives | state |
| ---------- | ---------------------- | ----- |
| **Route Risk** | `dispatch/scoring.py:213` `compute_route_risk()`; carried on sandbox cards; rendered at `brief.html:151` | **exists**; not yet surfaced in the mission detail view |
| **Facility Intelligence** | `portal/models/intelligence.py` — typed records for broker, customer, location, facility, route, return-route; rendered as *Location Intel* / *Broker Intel* | **exists, reusable unchanged** |
| **Delay visibility** | `EXCEPTION_TYPES` includes `delay`, with `SEVERITY_LEVELS` and `EXCEPTION_STATUSES`; `get_visibility()`; a dedicated **Exceptions** section and a **Detention** section in the detail view; detentions carry `location_type` | **exists, and already phase-aware** |
| **Mission awareness** | the *Status Progress*, *Load Progress / Event Feed*, *Timeline*, and *Activity* sections, over `get_load_bundle()` | **exists**; the strongest asset in the system |

Additional risk signals already computed and carried on the card, not currently
surfaced in the mission view: `hos_risk`, `position_impact`,
`tomorrow_position_risk`, `return_home_required`, `economic_opportunity_flag`.

## 4. Modifications required for CURRENT / PICKUP / DELIVERY

**No schema change. No new store. No new record.**

### The axis already exists, three times over

**Load fields:** `pickup_location`, `pickup_datetime`, `delivery_location`,
`delivery_datetime`.

**Load statuses** (11) already sort onto the axis:

    created  dispatched
    en_route_pickup  at_pickup  picked_up      <- PICKUP
    in_transit                                 <- transit
    at_delivery  delivered                     <- DELIVERY
    completed  archived  cancelled

**Milestone types** (11) do the same: `en_route_pickup`, `arrived_pickup`,
`loaded`, `departed_pickup` | `in_transit`, `checkpoint` | `arrived_delivery`,
`delivered`, `pod_received`.

And `DETENTION_LOCATIONS = ["pickup", "delivery"]` is a literal discriminator
already present on detention records.

### The fourteen sections, mapped to phase

`dispatch_detail.html` renders these sections. This is what a phase filter
would reveal or conceal — nothing is deleted, only hidden:

| section | CURRENT | PICKUP | DELIVERY |
| ------- | ------- | ------ | -------- |
| Load Information | always | always | always |
| Status Progress | always | always | always |
| Fleet Assignment | always | — | — |
| Visibility | always | always | always |
| Load Progress / Event Feed | always | always | always |
| Timeline (milestones) | phase-filtered | pickup milestones | delivery milestones |
| Evidence | phase-filtered | BOL | POD |
| Exceptions | open only | pickup-side | delivery-side |
| Detention | by state | `location_type == pickup` | `location_type == delivery` |
| Activity | recent | pickup-tagged | delivery-tagged |
| POD Packages | if present | — | always |
| Financials | summary | — | — |
| Settlement | — | — | on delivered |
| Lane History | — | — | — |

**CURRENT is not a third data set.** It resolves to PICKUP or DELIVERY by
`load["status"]`. Implementing it as a third branch would create precisely the
duplication the doctrine forbids — this is the single most important
implementation constraint in this report.

### Required modifications

| # | modification | scale | notes |
| - | ------------ | ----- | ----- |
| 4.1 | phase resolver: status → PICKUP \| DELIVERY | small | pure function, no I/O |
| 4.2 | facet filter over an assembled bundle | small | reads the bundle; never re-queries |
| 4.3 | three filter controls | **very small** | `filterActivities` is the working precedent; same `data-filter` pattern |
| 4.4 | `data-phase` attributes on the section markup | medium | mechanical, but touches a 1,226-line file |
| 4.5 | a test that all three filters cause **one** store read | small | the guard that keeps the doctrine true over time |

## 5. Modifications required for JOE, voice, and COMI display

### 5.1 JOE Communication Area

A region in `base.html`, present on every page. The portal renders it; JOE
supplies its content. Nothing in the portal learns how JOE works.

### 5.2 Reaching JOE

JOE runs as a separate program with its own service boundary and already
supports a headless single-question mode. The honest seam is a **local request
path**, not an import.

**JOE must not be imported into the portal process.** That would place mission
data and communication in one address space and dissolve the ownership split
the doctrine exists to protect. This is the one architectural rule in §5.

### 5.3 Mission context — passed, never held

The panel sends a `load_id`. JOE reads what it needs through
`GET /loads/<load_id>/bundle` — which already exists — and retains nothing.
Every mission fact JOE speaks is read at the moment it is asked.

This is what keeps "Joe does not own Mission Records" true in practice rather
than only on paper.

### 5.4 Voice interaction

JOE owns voice and already implements it, including local recognition that
works without signal. The portal exposes a control and displays the result.
The portal must not implement speech.

> **Current state, stated plainly:** JOE's voice *input* is not yet proven on
> this machine — the microphone test has not been completed since hearing-proof
> recording was added, and JOE reports `Voice in: NOT CONNECTED` honestly as a
> result. Voice output is live. This affects sequencing in §9, not design.

### 5.5 COMI display integration

Portal displays, JOE communicates, COMI owns the workflow. The panel renders,
read-only: pickup communication, delivery communication, POU status, POD
status, email status, draft status, approval status, exception notifications.

**COMI does not exist in this codebase.** There is a `publisher` queue and an
`inquiry_draft` field on cards, but no COMI producer. §5.5 therefore describes
a display whose data source is not yet built — it can be designed now and
populated later, and should not block §4.

## 6. Reusable directly, without change

- `dispatch/store.py`, `dispatch/models.py`, `dispatch/services.py`
- `portal/routes/dispatch_api.py` — all 132 routes, in particular `/bundle`
- `dispatch/scoring.py`, including Route Risk
- `portal/models/intelligence.py`
- `portal/models/publisher.py`
- The calendar view and its pattern
- **`filterActivities()` — the view-filter pattern itself**
- The `load-info-view` / `load-info-edit` show-hide pattern
- `base.html` as the shell

## 7. Requiring enhancement

| component | enhancement | note |
| --------- | ----------- | ---- |
| `dispatch_detail.html` (1,226 lines) | `data-phase` attributes; likely decomposition into includes | the largest obstacle; mechanical but broad |
| `pages.py` — `dispatch_detail()` | accept and pass the view filter | small |
| `base.html` | host the JOE panel | additive |
| `brief.html` (266 lines) | resolve its future — see §8.2 | decision before work |
| `dispatch/notifications.py` | surface delay and Route Risk into the panel | additive |
| **`style.css` (732 lines)** | **touch sizing — see below** | newly in scope |

### Touch, now that the portal explicitly owns it

The v2 doctrine assigns *touch interaction* to the portal. Measured:

- `<meta name="viewport">` is present — the baseline is right.
- Responsive CSS is **one `@media (max-width: 800px)` block, at line 725 of
  732** — the last eight lines of the stylesheet.
- Tap targets are mouse-sized: `.btn` is `padding: 6px 14px` at 13px (≈26px
  tall); `.btn-sm` smaller; **`.btn-xs` is `0.15rem 0.4rem` at 0.7rem — roughly
  18px tall.** The common guidance for touch is ~44px.

`.btn-xs` is the class the existing filter buttons use — so the CURRENT /
PICKUP / DELIVERY controls, if they copy that pattern faithfully, will be the
smallest targets in the system and will be pressed by a driver, in a cab,
possibly moving. **Copy the filter mechanism; do not copy its sizing.**

## 8. Architectural conflicts

### 8.1 The Mission Record is not authoritative across the whole lifecycle

**This is the one conflict that should be settled before any of §4 is built.**

The v2 doctrine states the Mission Record *"remains the authoritative
operational object throughout the entire mission lifecycle"*, and that the Load
Card *becomes* authoritative on commitment. The code has two unconnected
stores:

- `portal/models/sandbox.py` — the opportunity card
- `dispatch/store.py` — the committed mission

Measured: `dispatch/` references sandbox only in one docstring
(`acquisition.py:4`); `sandbox.py` never references dispatch; the `Load`
dataclass carries **no field pointing back to the card**; there is no promote
path between them.

**What the card holds that the Load record has nowhere to put:**

| card field | what is lost at commitment |
| ---------- | -------------------------- |
| `intelligence` | broker, facility and lane intelligence gathered during acquisition |
| `decision` | the Go / No-Go record and its reasoning |
| `events[]` | the acquisition and negotiation history |
| `score` | why this load was taken |
| `route_risk` | **the Route Risk this report is asked to surface** |
| `hos_risk` | hours-of-service exposure |
| `position_impact`, `tomorrow_position_risk`, `return_home_required` | positioning consequences |
| `flags`, `summary`, `notes` | the human reading of the load |

The `Load` record carries: load_id, customer, broker_shipper, pickup and
delivery location and datetime, equipment, driver, equipment ids, status,
source, notes, timestamps. Nothing else.

So at the moment a mission becomes real, everything explaining *why it was
taken* and *what it risks* stops travelling with it — including the Route Risk
that §3 is asked to display.

**Recommendation: add a link, not a merge.** The Load record should carry the
originating card identifier so the Mission Record can reach back to the
intelligence that produced it. One field, one write. It is the difference
between one Mission Record with a history and two records that resemble each
other.

### 8.2 Two candidates for "the Driver Portal"

`brief.html` reads the card store and already shows Route Risk, Location Intel
and Broker Intel. `dispatch_detail.html` reads the Mission Record and holds the
fourteen operational sections. Both are legitimate; they serve different
lifecycle stages.

**Which one is being retained and enhanced must be stated**, or the work lands
on the wrong file. This is Mike's decision, not an implementation choice.

Reading the code: `dispatch_detail.html` is the one attached to the
authoritative record and is where the phase filters belong. `brief.html` is
closer to what a driver reads before committing. If 8.1 is fixed, the two stop
competing — the brief becomes a view of the same record, and the doctrine
resolves the question by itself.

### 8.3 COMI has no producer

§5.5 designs a display for state nothing currently emits. Not a blocker, but it
should not be scheduled as though the data exists.

### 8.4 A boundary that will be under constant pressure

The panel will sit inches from both mission data and communication. The
temptation will be to let JOE keep "just a little" mission state for
responsiveness. The doctrine forbids it and the safeguard must be structural:
JOE reads through the API and holds nothing. A cache added for speed is how
this architecture would quietly acquire its second mission record.

## 9. Recommended migration path

Enhancement only. Each step leaves a working portal behind it.

**Step 0 — settle §8.1 and §8.2.** Link the card to the Load; name the Driver
Portal. No new features. Everything afterwards is cheaper, and Route Risk
becomes available to the mission view as a side effect.

**Step 1 — phase resolver and facet filter.** Pure functions over an existing
bundle. Nothing visible changes. This is where the one-store-read test belongs.

**Step 2 — the three filter controls.** Copy `filterActivities`'s mechanism;
size them for a thumb, not a mouse (§7). First step Mike can see, and it
delivers the doctrine's headline.

**Step 3 — `data-phase` attributes across the fourteen sections.** The broad,
mechanical step. Best done after Step 2 proves the mechanism on one section.

**Step 4 — JOE panel in the shell, no mission context.** Question in, answer
out. Proves the seam before anything depends on it.

**Step 5 — pass `load_id`; JOE reads `/bundle`.** Mission-aware communication,
with JOE still holding nothing.

**Step 6 — COMI display**, when COMI produces state.

**Step 7 — voice in the panel.** Deliberately last: JOE's voice input is not
yet proven on this machine (§5.4). Proving hearing is a five-minute test, not a
build — but it is a precondition, and putting voice earlier would mean shipping
a control that cannot be trusted.

**Rename last.** "JOE Presentation Layer" should be adopted once steps 1–5 are
real. Renaming before the change is how a directory ends up describing an
intention rather than a system.

---

## What this report does not claim

- `dispatch_detail.html` and `dispatch_api.py` were read for **structure,
  section inventory and route inventory**. Every line of business logic inside
  them was not audited.
- The portal was **not run**. All findings are from reading source.
- The fourteen-section phase mapping in §4 is a **proposal for Mike to correct**,
  not a derived truth. It is the one table here most likely to be wrong in
  detail, because it encodes operational judgement about what a driver needs to
  see at a dock — and that is his knowledge, not mine.
- COMI does not exist in this codebase.
- Whether `brief.html` or `dispatch_detail.html` is the Driver Portal remains
  open (§8.2).

**Mike Zachary remains final authority.**
