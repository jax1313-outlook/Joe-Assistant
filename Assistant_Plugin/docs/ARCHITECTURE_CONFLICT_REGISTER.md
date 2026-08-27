# Architecture Conflict Register

**Mission:** BOOTSTRAP THE DISPATCH COPILOT AGENT, §10.C
**Type:** Analysis only. **Nothing was modified.** §7 is explicit: identify
conflicts, do not modify them during this planning mission.
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

---

## The largest conflict, stated first

### C-1 — Joe's authority model is proposal-only. The new mission adds EXECUTE.

**Severity: HIGH. This is a doctrine change, not a code change.**

Every prior mission built Joe on a single rule: **Joe proposes, Mike disposes.**
That rule is not a comment. It is enforced in five separate places:

| Where | What it does |
| --- | --- |
| `contracts/__init__.py::AssistantResponse` | `approved`, `decided`, `acted_on`, `operational_write` default `False` |
| `governance/__init__.py::Governor.review` | forces any true flag back to `False` and records a **CRITICAL** breach |
| `governance/__init__.py::Governor.enforce` | a critical breach replaces the whole response with a refusal — it is not softened or reworded |
| `adapters/outlook_com.py::FORBIDDEN_COM_CALLS` | 21 write-capable calls scanned and refused before any script runs |
| `adapters/mailbox_registry.py` | `WRITE_AUTHORITY = "none"`, and a test asserts no send, delete, or move path exists |

Plus doctrine: `JOE_CONSTITUTION_v1.md`, the Driver Manual's "MAY NOT" list, and
proof step 23 which asserts drafting is marked DRAFT ONLY / NOT SENT and that
nothing can send.

**The new §7 requires Joe to execute a bounded workflow when a voice command
carries explicit sending authority, without a redundant approval loop.**

These are not reconcilable by adjusting a flag. The current design has **no send
path at all** — which the salvage matrix notes is stronger than any parser rule,
because there is nothing to authorise.

**Recommended disposition: HUMAN DECISION REQUIRED.**

What Mike is actually deciding:

1. Does `acted_on = True` become legal when Dispatch confirms an action, or does
   Joe keep reporting Dispatch's outcome without ever claiming the action?
2. Does the governance gate stop treating a true authority flag as a critical
   breach, or does EXECUTE live outside the flags entirely?
3. Does proof step 23 change, or does it narrow to "Joe cannot send *directly*"?

**My recommendation, offered as a recommendation only:** keep the flags meaning
what they mean, and let **Dispatch** be the thing that acted. Joe requests,
Dispatch executes, Joe reports a verified Dispatch outcome. `acted_on` stays
`False` because Joe did not act — Dispatch did. That satisfies §7's flow without
dismantling five layers of enforcement, and it keeps the Card-Centric rule
intact: the deterministic workflow performs the business action.

---

## C-2 — "No second source of truth" versus Joe's retention engine

**Severity: MEDIUM.**

Joe's Level 3 "formal record" is a durable conversation artifact stored in
`runtime_data/memory/`. §2 of the mission forbids durable copies of Mission Card
or Opportunity Card state, duplicate operational memory, and separate
operational databases.

**No conflict today** — Joe has no card data to store. **The conflict appears
the moment Joe reads a card**, if a Level 3 record captures card content.

**Recommended: KEEP the engine, ADD a boundary rule.** Conversation records may
store *what was said and answered* and a *card reference*. They must never store
card field values as durable state. Needs a test that enforces it.

---

## C-3 — Joe indexes the Company Library. Dispatch owns Library.

**Severity: MEDIUM.**

`adapters/library_fs.py` walks the filesystem and indexes 34 documents directly.
The Card-Centric mission assigns Library to Librarian, and says Joe is a
"discoverer, explainer, and router" that must not place material into the
Library itself.

Joe does not *write* to the Library, so the prohibition is not breached. But Joe
maintaining its own index **is** a second retrieval path over Dispatch-owned
material.

**Recommended: SUPERSEDE when Dispatch's Library interface exists. RETAIN AS
LEGACY until then** — it works, and turning it off before a replacement exists
removes a proven capability for no gain.

---

## C-4 — Research ownership is unassigned

**Severity: MEDIUM. Genuinely unresolved.**

The Card-Centric mission says *"Research Scout remains separate from Dispatch and
Joe."* Joe currently has live web-grounded research through Copilot, proven with
11 real attributions.

Three readings all fit the doctrine:

1. Joe's research is Knowledge Navigator work (Job 3) and stays
2. Joe's research is Research Scout work and moves out
3. Both exist — Joe does immediate operational lookups, Scout does long-range

**Recommended: HUMAN DECISION REQUIRED.** This is a role boundary, not a
technical question, and guessing would either delete a working capability or
entrench one that belongs elsewhere.

---

## C-5 — Joe owns its own process. Inside Dispatch it will not.

**Severity: MEDIUM, and it is the biggest *code* risk.**

`app/service.py` is 1,128 lines and assumes it is the application: it builds
every adapter, owns startup and shutdown, and holds the capability table. §2
requires Joe to start when Dispatch starts and stop when Dispatch stops.

**Recommended: REWRITE the lifecycle, KEEP the internals.** Split into an agent
façade plus capability handlers. **This is the single work package most likely
to break the 329-test safety net**, and it should not be attempted before the
Dispatch plugin lifecycle is known.

---

## C-6 — The UI assumes Joe has a window

**Severity: LOW to MEDIUM.**

`ui/window.py` is a standalone tkinter application with its own launcher and
desktop shortcut. Inside Dispatch, Joe is a panel.

**Recommended: ADAPT.** The VOICE button states, response pane, history list,
and retention buttons are directly reusable. The window shell is not.

**Do not treat this as cosmetic.** §11 says no screen-first work, and Mike has
already reported the current screen is visually poor and that some controls do
not work.

---

## C-7 — Voice is inside Joe. The new architecture puts it outside.

**Severity: LOW. Clean separation already exists.**

`app/driver_voice.py` and `adapters/voice_sapi.py` live inside Joe. The target
architecture makes Voice a separate dock between Mike and Joe.

**Recommended: KEEP both, relocate them.** The loop is already provider-neutral —
it takes injected `listen`, `speak`, and `ask` callables and is fully testable
without hardware. That is exactly the Voice Dock shape.

**One real constraint moves with it:** `System.Speech` cannot bind a chosen
capture device, which is why Joe cannot reliably use Mike's Bluetooth headset.
The Voice Dock must own capture for that to be fixed.

---

## C-8 — Manager: no conflict, and the guards should stay

**Severity: NONE.**

Audited: 18 occurrences of the word across the repository, **zero functional
Manager code.** All are guards asserting its absence, doctrine stating it, or the
phrase "records manager" inside a retrieved Library document.

**Recommended: KEEP every guard.** `proof/run_proof.py` step 18 scans every
source file for `class *Manager` on every run. That guard is worth more inside
Dispatch than it was in the sandbox.

---

## C-9 — `Voice LIVE` was a false status indicator

**Severity: RESOLVED, recorded for the register.**

One chip covered voice input and voice output — output proven and audible, input
never having heard a person. **Fixed in the previous step:** now reported as
`Voice out LIVE` and `Voice in NOT CONNECTED` with the blocker named.

**Recommended: KEEP.** The vocabulary discipline behind it — `LIVE` means a real
service answered, `READY` means reachable but unused, `UNKNOWN` never collapses
into absent — should govern every Dispatch status Joe reports.

---

## C-10 — Audio-activity detection does not exist

**Severity: MEDIUM for operation, LOW for architecture.**

§9 requires audio-activity detection in the Voice Dock. Joe has none. Stage 2 of
the voice pipeline is uninstrumented, so **a dead microphone and a silent room
look identical.**

**Recommended: REWRITE as part of the Voice Dock.** Azure Voice Live supplies
noise suppression and echo cancellation; activity detection is still needed
locally to gate the session, which is also the main cost control.

---

## C-11 — Every conflict below this line needs the Dispatch repository

**These cannot be assessed and are listed so their absence is visible.**

| Unassessed | Why |
| --- | --- |
| Joe doctrine versus **Dispatch code** | Dispatch code has not been reviewed |
| Opportunity Card First versus Joe's drafting | no card interface known |
| Card-Centric flow versus Joe's capability dispatch | no card model known |
| Transaction Log versus `app/logbook.py` | Dispatch's log is unknown — §10 of the prior mission warns against asserting a log exists before confirming it |
| Storage ownership | unknown |
| Plugin lifecycle versus Joe's startup | **the highest-risk unknown** (see C-5) |
| Dispatch's own UI versus Joe's panel | unknown |

---

## Disposition summary

| ID | Conflict | Disposition |
| --- | --- | --- |
| C-1 | Proposal-only versus EXECUTE | **HUMAN DECISION REQUIRED** |
| C-2 | Retention versus no-second-truth | KEEP + add boundary rule |
| C-3 | Joe's Library index | SUPERSEDE later, RETAIN now |
| C-4 | Research ownership | **HUMAN DECISION REQUIRED** |
| C-5 | Joe owns its process | REWRITE lifecycle, KEEP internals |
| C-6 | Standalone window | ADAPT |
| C-7 | Voice inside Joe | KEEP, relocate to Voice Dock |
| C-8 | Manager | KEEP the guards |
| C-9 | `Voice LIVE` | KEEP the fix and the vocabulary |
| C-10 | No audio-activity detection | REWRITE in the Voice Dock |
| C-11 | Everything Dispatch-side | **BLOCKED — repository not available** |

**Two conflicts require Mike personally: C-1 and C-4.** C-1 is the one that
changes what Joe fundamentally is.

---

Mike Zachary remains final authority.
