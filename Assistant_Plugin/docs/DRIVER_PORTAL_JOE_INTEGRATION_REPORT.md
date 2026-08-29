# Driver Portal → JOE Presentation Layer

**Architecture impact review. Analysis only — no code, no redesign.**

**Requested by:** Mike Zachary, 28 August 2026
**Subject under review:** `D:\Dispatch Operations\Code\cin-hybrid`
**Assumption, as instructed:** the Mission Record doctrine and the ownership
split are accepted and intentional. Nothing below proposes replacing them.

> This document analyses the **Dispatch** portal but is written into the JOE
> workspace, because Dispatch `main` is protected and takes changes by pull
> request. Move it into the Dispatch repository whenever that is convenient;
> nothing depends on where it sits.

---

## Headline finding

**The Mission Record doctrine is already implemented.** It is not something to
be built — it is something to be *named*, and then extended.

`dispatch/services.py` → `get_load_bundle(load_id)` assembles **one** record
from **one** store and returns sixteen facets of it:

    load          visibility     milestones    evidence
    exceptions    pods           retention     financials
    settlement    assigned_driver assigned_equipment activities
    active_drivers active_equipment lane_history detentions

Collected once, stored once, reused by view. That is the doctrine, in code,
today. The work ahead is smaller than it looks.

---

## 1. What remains unchanged

| component | file | why it is untouched |
| --------- | ---- | ------------------- |
| Mission Record store | `dispatch/store.py` | it *is* the Mission Record |
| Mission Record models | `dispatch/models.py` | vocabulary is already complete (see §3) |
| Bundle assembly | `dispatch/services.py` — `get_load_bundle()` | one record, many facets |
| Mission REST API | `portal/routes/dispatch_api.py` (1,996 lines, `dispatch_bp`) | already exposes `/loads`, `/loads/<load_id>` |
| Scoring incl. Route Risk | `dispatch/scoring.py` — `compute_route_risk()` at line 213 | already produces the value |
| Facility / broker intelligence | `portal/models/intelligence.py` | broker, customer, location, facility, route, return-route |
| Calendar Display | `portal/routes/pages.py:288` → `dispatch_svc.get_load_calendar()` | **already sources from the Mission Record** |
| Publisher queue | `portal/models/publisher.py` | Publisher owns production, per doctrine |
| Page shell / navigation | `portal/templates/base.html` (223 lines, 24 nav items) | extended, not rewritten |

## 2. What already aligns with the doctrine

Five things align without any change at all:

1. **One store for committed missions.** `dispatch/store.py` is the single
   source. Nothing else writes mission state.
2. **Assembly, not duplication.** `get_load_bundle()` gathers facets by
   `load_id`; it copies nothing into a second record.
3. **Calendar is already a view, not a database.** It calls
   `get_load_calendar()` on the same service. This is the clearest existing
   proof that "One Mission Record, Many Views" already works here — the
   pattern the new filters should copy.
4. **Ownership is already separated.** `dispatch/` holds workflow and data;
   `portal/` holds presentation; they meet at a service call and a REST API.
5. **Route Risk and Facility Intelligence already exist** and are already
   rendered (`brief.html:151` shows Route Risk today).

## 3. How CURRENT / PICKUP / DELIVERY should be added

**As a filter over fields that already exist. No schema change is required,
and none should be made.**

The Mission Record already carries a pickup/delivery axis in three places:

**Load fields** (`dispatch/models.py`, `Load` dataclass):

    pickup_location    delivery_location
    pickup_datetime    delivery_datetime

**Load statuses** — eleven, and they already sort onto the axis:

    created  dispatched
    en_route_pickup  at_pickup  picked_up      <- PICKUP phase
    in_transit                                  <- between
    at_delivery  delivered                      <- DELIVERY phase
    completed  archived  cancelled

**Milestone types** — eleven, same axis:

    dispatched  en_route_pickup  arrived_pickup  loaded  departed_pickup
    in_transit  checkpoint
    arrived_delivery  delivered  pod_received  completed

And `DETENTION_LOCATIONS = ["pickup", "delivery"]` is already a literal
pickup/delivery discriminator on the detention records.

So the three filters are **derivable**, not stored:

- **PICKUP** — reveals `pickup_location` / `pickup_datetime`, milestones from
  `en_route_pickup` through `departed_pickup`, detentions where
  `location_type == "pickup"`, pickup-side evidence (BOL), and pickup-facing
  communications.
- **DELIVERY** — reveals `delivery_location` / `delivery_datetime`, milestones
  from `arrived_delivery` through `pod_received`, delivery-side detentions,
  POD records, and delivery-facing communications.
- **CURRENT** — derived from `load["status"]`, resolving to whichever phase the
  mission is actually in. It is the other two, selected by state rather than by
  the driver's thumb.

**This matters for the recommendation:** CURRENT is not a third data set. It is
PICKUP or DELIVERY chosen by status. Implementing it as a third branch would
create the duplication the doctrine forbids.

## 4. Code changes required for the view filters

Stated as scope, not as implementation.

| # | change | scale |
| - | ------ | ----- |
| 4.1 | A phase resolver — status → `PICKUP` \| `DELIVERY`, one function, pure, no I/O | small |
| 4.2 | A facet filter over an assembled bundle — given a bundle and a phase, return the subset. Reads the bundle; does not re-query | small |
| 4.3 | Filter state in the route as a query parameter (`?view=current\|pickup\|delivery`), defaulting to `current` | small |
| 4.4 | Three filter controls in the template, rendering the same bundle | small |
| 4.5 | Tests that the same `load_id` under all three filters yields **one** record and never a second fetch | small, and the important one |

**4.5 is the guard that keeps the doctrine true.** A test that asserts one
store read per request is what stops "many views" quietly becoming "many
records" a year from now.

## 5. Code changes required to embed JOE

JOE already exists as a working assistant with its own service boundary. The
integration is a **panel that calls it**, not a port of it.

| # | change | notes |
| - | ------ | ----- |
| 5.1 | JOE communication panel — a region in the portal shell | new region in `base.html`; no page rewritten |
| 5.2 | JOE dialogue display — question in, response out, interaction history | JOE already returns a written form and a spoken form separately |
| 5.3 | A request path from portal to JOE | JOE exposes `--headless "question"` today; a small local endpoint is the honest seam. **JOE must not be imported into the portal process** — that would put mission data and communication in one address space and break the ownership split |
| 5.4 | Mission context passed *in*, never held | the panel sends `load_id`; JOE reads the Mission Record through the existing REST API and keeps nothing |
| 5.5 | Voice interaction | JOE owns this already. The portal exposes a control; it does not implement speech |
| 5.6 | COMI communication status display | read-only rendering of COMI state: POU, POD, draft status, approval status, delay and Route Risk notifications |

**The constraint that keeps this clean:** the panel is a *window onto* JOE, not
a copy of JOE. Everything JOE knows about a mission, it reads from the Mission
Record when asked. Nothing about a mission is stored in the panel.

## 6. Existing functions that already satisfy the named capabilities

| capability | already satisfied by | state |
| ---------- | -------------------- | ----- |
| **Facility Intelligence** | `portal/models/intelligence.py` — broker, customer, location, facility, route, return-route records; surfaced in `brief.html` as *Location Intel* and *Broker Intel* | **exists, reusable as-is** |
| **Route Risk** | `dispatch/scoring.py:213` `compute_route_risk()`; surfaced at `brief.html:151` | **exists**; needs surfacing in the phase views |
| **Delay visibility** | `EXCEPTION_TYPES` includes `delay`, with `SEVERITY_LEVELS` and `EXCEPTION_STATUSES`; `get_visibility()` in `dispatch/store.py`; detentions carry `location_type` | **exists**, and already phase-aware through `location_type` |
| **Mission awareness** | `get_load_bundle()` — status, milestones, evidence, exceptions, PODs, financials, settlement, activities, lane history | **exists**, and is the strongest asset in the system |

## 7. Reusable directly, without change

- `dispatch/store.py`, `dispatch/models.py`, `dispatch/services.py`
- `portal/routes/dispatch_api.py` — the REST surface JOE should read through
- `dispatch/scoring.py` — including Route Risk
- `portal/models/intelligence.py`
- `portal/models/publisher.py`
- The calendar view — **and its pattern**, which is the template for the filters
- `portal/templates/base.html` as the shell

## 8. Requires enhancement

| component | enhancement | why |
| --------- | ----------- | --- |
| `portal/templates/dispatch_detail.html` (**1,226 lines**) | phase filtering; likely decomposition into includes | it renders every facet at once. It is the largest single obstacle to a clean phase view, and the file most likely to resist change |
| `portal/routes/pages.py` — `dispatch_detail()` | accept and pass a view filter | small |
| `portal/templates/brief.html` (266 lines) | see §9 — decide its future first | it is the closest thing to a driver-facing mission view today |
| `portal/templates/base.html` | host the JOE panel | additive |
| Notifications (`dispatch/notifications.py`) | surface delay and Route Risk into the panel | additive |

## 9. Architectural conflicts

**One real conflict, and it is worth fixing before anything else is built.**

### 9.1 Two mission stores, with no link between them

There are two independent record stores:

- `portal/models/sandbox.py` — the **opportunity card** store. `brief.html`
  reads from it: origin, destination, broker, rate, RPM, pickup, delivery,
  equipment, detention history, Location Intel, Broker Intel, Route Risk.
- `dispatch/store.py` — the **committed mission** store, behind
  `get_load_bundle()`.

Measured: `dispatch/` never references sandbox except in one docstring
(`acquisition.py:4`), and `sandbox.py` never references dispatch. The `Load`
dataclass carries **no field pointing back to the card it came from**, and
there is no promote/commit path from one store to the other.

**Why this matters under the doctrine.** Mike's own words: *"The Load Card is
created through intelligence collection… enriched during negotiation… becomes
authoritative when the load is committed."* That is one record crossing a
threshold. The code has two records that never meet. Whatever happens at
commitment today either re-keys the mission by hand or loses the card's
history — and either way the intelligence gathered during acquisition and
negotiation does not travel with the mission it belongs to.

**Recommendation:** add a link, not a merge. The `Load` record should carry the
originating card identifier, so the Mission Record can reach back to the
intelligence that created it. This is a small field and a small write, and it
is the difference between "one Mission Record" and "two records that resemble
each other". **It should be settled before the view filters are built**,
because the filters will otherwise be built over half a mission.

### 9.2 Two candidates for "the Driver Portal"

`brief.html` reads the card store; `dispatch_detail.html` reads the Mission
Record. Both are legitimate; they serve different lifecycle stages. The
doctrine says the Driver Portal is retained and enhanced — so **which one is
being retained needs to be stated explicitly**, or the enhancement will land on
the wrong file. This is a decision for Mike, not an implementation choice.

My reading: `brief.html` is the driver-facing view by content and size, but
`dispatch_detail.html` is the one attached to the authoritative record. If 9.1
is fixed, the distinction narrows considerably.

### 9.3 No JOE integration point exists yet

Measured: the word "JOE" and "assistant" appear **nowhere** in `portal/`. This
is not a defect — it is a clean insertion point, and it means the panel can be
added without unpicking anything.

### 9.4 A boundary to hold deliberately

JOE owns communication; the Mission Record owns mission data. The panel will
sit inches from both. The temptation will be to let JOE cache a little mission
state "just for the panel". Doctrine forbids it, and the safeguard is
structural: JOE reads through the REST API and holds nothing.

## 10. Simplest migration path

Enhancement only. Five steps, each independently useful, each leaving a working
portal behind it.

**Step 0 — settle §9.1 and §9.2.** Link the card to the Load; name which
template is the Driver Portal. No new features. Everything after this is
cheaper and safer for it.

**Step 1 — add the phase resolver and facet filter.** Pure functions over an
existing bundle. Nothing visible changes. Fully testable in isolation, and this
is where 4.5 belongs.

**Step 2 — add the three filter controls to the named Driver Portal template.**
Same record, three views, following the calendar's existing pattern. This is
the first step Mike can see, and it delivers the doctrine's headline —
*One Mission Record. Many Views.*

**Step 3 — add the JOE panel to the shell, read-only.** Question in, answer
out, interaction history. No mission context passed yet. Proves the seam works
before anything depends on it.

**Step 4 — pass mission context and surface COMI status.** The panel sends a
`load_id`; JOE reads the Mission Record through the REST API. COMI state
renders read-only: POU, POD, draft, approval, delays, Route Risk.

**Step 5 — enable voice in the panel.** JOE already owns voice. The portal
exposes the control.

**Rename last, not first.** "JOE Presentation Layer" should be adopted once
steps 1–4 are real. Renaming a thing before it changes is how a directory ends
up describing an intention rather than a system.

---

## What this report does not claim

- I have **not** read all 1,226 lines of `dispatch_detail.html`, nor all 1,996
  of `dispatch_api.py`. Structure and entry points were established; the
  interiors were not audited. §8's decomposition estimate is therefore a
  judgement, not a measurement.
- I have **not** run the portal. Every finding above is from reading source.
- COMI does not exist in this codebase yet, so §5.6 describes a display of
  state that has no producer today.
- Whether `brief.html` or `dispatch_detail.html` is "the Driver Portal" is
  **Mike's call**, and §9.2 is written as a question rather than an answer.

**Mike Zachary remains final authority.**
