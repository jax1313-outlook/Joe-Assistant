# JOE Presentation Layer — file selection

**Implementation review. Analysis only — no code, no redesign.**

**Requested by:** Mike Zachary, 28 August 2026
**Follows:** `DRIVER_PORTAL_JOE_INTEGRATION_REPORT_v2.md`
**Question:** which file becomes the JOE Presentation Layer —
`brief.html` or `dispatch_detail.html`?

---

## Correction to v2, first

v2 stated: *"there is no promote path between them"* and that the two stores
never meet. **That was wrong, and the error mattered — it overstated the
conflict.**

Measured now:

| what exists | where |
| ----------- | ----- |
| on booking, the card is linked to the load | `portal/routes/api.py:66` — `sandbox.link_engine_load(sandbox_id, engine_load["load_id"])` |
| the card stores the link | `portal/models/sandbox.py:170–180` — `engine_load_id`, with an event written |
| double-booking is prevented | `api.py:46` — *"Load already booked"*, HTTP 409 |
| the card resolves its load | `api.py:346–349` — `dispatch_svc.get_load(engine_load_id)` |
| load status flows back to the card | `pages.py:842` — `_sync_booked_entries()` |
| `brief.html` shows it | line 132 — `{% if entry.engine_load_id %}` → *Engine Load* section |

So the lifecycle **is** connected. A promote path exists and is guarded.

**What remains true, and is the finding that actually matters:**

The link is **one-directional**. The card knows its load. The `Load` record has
no field naming its card, and there is **no reverse lookup** anywhere in the
codebase — from a `load_id` you cannot find the card that produced it without
scanning every sandbox entry. And only one field, `status`, syncs back.

That asymmetry is not academic. It decides this report.

---

## 1. Recommendation

### `dispatch_detail.html` becomes the JOE Presentation Layer.

### `brief.html` is retained, unchanged in purpose, as the pre-commitment view.

This is not a close call, but it is close enough that the reasoning should be
visible rather than asserted.

---

## 2. Why

### The deciding principle

> **What `dispatch_detail.html` has cannot be migrated.
> What it lacks can be.**

`dispatch_detail.html` is bound to the Mission Record. That binding *is* the
file — remove it and nothing is left. `brief.html` is bound to the card.

Facility Intelligence and Route Risk are **lookups plus a render**. They move.
Sixteen facets of live mission state, fourteen operational sections, and the
milestone/evidence/exception/detention data that phase filters act upon do not
move — they would have to be rebuilt, which is the replacement Mike forbade.

### Scored against the eight requirements

| requirement | `brief.html` | `dispatch_detail.html` |
| ----------- | ------------ | ---------------------- |
| Present Mission Record information | card snapshot + `engine_status` only | **native** — `get_load_bundle()`, 16 facets |
| CURRENT / PICKUP / DELIVERY filters | no phase data to filter | **has the data and the pattern** (`filterActivities()`, line 996) |
| Facility Intelligence | **renders it today** — Location Intel, Broker Intel, Intelligence Modules | absent — migrate |
| Route Risk | **renders it today** (line 151) | absent — migrate |
| Delay visibility | detention history only | **Exceptions + Detention + Visibility sections** |
| COMI communication display | `publisher_actions`, `inquiry_draft` | POD Packages, Evidence, Activity |
| Embedded JOE layer | neither | neither |
| Touch-first | 266 lines, card-shaped — **closer** | 1,226 lines of dense forms — **harder** |

Four to three, with one tie — but the count is not the argument. **The two
requirements `dispatch_detail.html` wins are the two that cannot be migrated.**

### The honest cost of this choice

Two, stated plainly rather than buried:

1. **Touch-first is materially harder here.** 1,226 lines built around
   fourteen editing forms, with tap targets at `.btn` ≈26px and `.btn-xs` ≈18px
   against a ~44px guideline. `brief.html` is already closer to a card the
   thumb can drive. Choosing `dispatch_detail.html` accepts the larger touch
   problem in exchange for the correct data foundation.
2. **Route Risk cannot be migrated until the reverse link exists.** Route Risk
   is computed during acquisition and lives on the card. The Mission Record
   cannot currently reach it. This is a precondition, not a preference — see
   §5, Step 0.

### Why `brief.html` is retained rather than absorbed

It serves a genuinely different lifecycle stage. In Mike's own card lifecycle —
Intake → Scoring → Dashboard → Go/No-Go → Brief → Archive — the Brief is what
he reads **before committing**. It answers *should I take this?* The
Presentation Layer answers *how is this mission going?*

It also carries something the mission view has no business holding: SAM
solicitation rendering (agency, NAICS, set-aside, response date), for
government contract opportunities that are not loads at all.

Folding one into the other would produce a screen answering two unrelated
questions at two unrelated moments. Both survive.

---

## 3. What to preserve in `dispatch_detail.html`

Preserve all fourteen sections. Nothing here is dead weight.

| section | preserve because |
| ------- | ---------------- |
| Load Information (+ `load-info-view` / `load-info-edit` toggle) | the mission identity, and a working show/hide pattern the phase filter can reuse |
| Status Progress | drives CURRENT — the phase resolver reads `load["status"]` |
| Fleet Assignment | driver and equipment binding |
| Visibility | customer-facing vs internal notes; a COMI-adjacent surface |
| Load Progress / Event Feed | mission awareness |
| Timeline (milestones) | **the primary phase-filterable facet** — 11 milestone types across the pickup/delivery axis |
| Evidence | BOL is pickup-side, POD delivery-side |
| Exceptions | delay visibility |
| Detention | already carries `location_type` ∈ {pickup, delivery} — **phase-aware today** |
| Activity + `activity-filters` | **the working view-filter precedent** — preserve the mechanism above all |
| POD Packages | delivery execution, and a COMI display anchor |
| Financials | rate, expenses |
| Settlement | closeout |
| Lane History | comparative context |

**Preserve `filterActivities()` specifically.** It is the proof that
deterministic view filtering already works in this file, and the new phase
controls should be built as a second instance of it — not as a new invention
alongside it.

**Preserve the edit forms.** They are workflow, owned by Dispatch. JOE must not
absorb them; the panel sits beside them.

---

## 4. What to migrate from `brief.html`

Migrate **display**, never storage. Four things.

| # | migrate | source | depends on |
| - | ------- | ------ | ---------- |
| 4.1 | **Facility / Location Intelligence** | `portal/models/intelligence.py`, rendered in `brief.html` | nothing — `intelligence.py` is keyed independently and reusable as-is |
| 4.2 | **Broker Intelligence** | same | nothing |
| 4.3 | **Route Risk** | `dispatch/scoring.py:213`, carried on the card, rendered `brief.html:151` | **the reverse link (§5 Step 0)** |
| 4.4 | **Risk context** — `hos_risk`, `position_impact`, `tomorrow_position_risk`, `return_home_required` | card, via scoring | same reverse link |

Do **not** migrate: the Go/No-Go decision block, flags, the card score, the
solicitation/SAM rendering, or `card_visual`. Those belong to the
pre-commitment moment and stay where they are.

**The pattern for all four:** the Presentation Layer *reads* these and displays
them. It does not store them, and it does not become their owner. Intelligence
stays owned by `intelligence.py`; risk stays computed by `scoring.py`.

---

## 5. Recommended implementation sequence

Seven steps. Each leaves a working portal behind it.

**Step 0 — add the reverse link.** One field on the `Load` record naming the
card it came from, populated at the existing link point (`api.py:66`, where
`link_engine_load` is already called — both identifiers are in hand at that
moment). This is the smallest possible change and it unblocks 4.3 and 4.4.
Without it, Route Risk cannot reach the Mission Record and requirement 4 cannot
be met in the chosen file.

**Step 1 — phase resolver and facet filter.** Pure functions over an assembled
bundle: status → PICKUP | DELIVERY, and bundle + phase → subset. Nothing
visible changes. The test that all three filters cause **one** store read
belongs here.

**Step 2 — phase filter on the Timeline section only.** One section, following
`filterActivities()` exactly. Proves the mechanism in the real file before it
is applied broadly — and Timeline is the richest phase-filterable facet.

**Step 3 — `data-phase` across the remaining sections.** The broad mechanical
step, done only after Step 2 has proven the approach on one section.

**Step 4 — migrate Intelligence and Route Risk in** (4.1–4.4). Now possible
because of Step 0. This is the point at which the Presentation Layer becomes
strictly better than either file was alone.

**Step 5 — touch pass.** Tap targets, the single media query, and the phase
controls sized for a thumb rather than a mouse. Deliberately after Step 4, so
the layout being sized is the final one — sizing twice is wasted work.

**Step 6 — JOE panel in the shell.** Question in, answer out, no mission
context. Proves the seam. Then pass `load_id` and let JOE read
`GET /loads/<load_id>/bundle`, holding nothing.

**Step 7 — COMI display, then voice.** COMI when it produces state. Voice last,
because JOE's voice input is still unproven on this machine — a five-minute
microphone test, but a genuine precondition.

**Rename at the end.** `dispatch_detail.html` becomes the JOE Presentation
Layer when steps 1–6 are real, not before.

---

## What this report does not claim

- The eight-requirement scoring in §2 is **judgement**, not measurement. The
  file inventories behind it are measured; the weighting is mine, and the
  weighting is what produced the answer.
- I have not audited every line of business logic in either template.
- The portal was not run.
- COMI still has no producer in this codebase.
- Whether the Brief should *also* eventually read from the Mission Record —
  once Step 0 makes that clean — is a further question I have not answered
  here, and it is not required to proceed.

**Mike Zachary remains final authority.**
