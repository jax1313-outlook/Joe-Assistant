# Dispatch — Discovery and Value Report

**Repository:** `D:\Dispatch Operations` — confirmed authoritative by Mike, 2026-08-26
**Type:** Read-only inspection. **Nothing in Dispatch was modified.**
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

---

## 1. Headline: this is a real program, and it is bigger than expected

| | |
| --- | --- |
| Python source files | **138** |
| **Test functions** | **2,186** across 78 test files |
| Git commits | **74**, clean working tree, on `main` |
| Last commit | 2026-08-03 |
| **REST API paths** | **90 distinct** |
| Largest modules | `dispatch_api.py` 1,640 loc · `services.py` 1,853 loc · `store.py` 1,675 loc |

**Test result, run today:** the full suite executes to 100%. **One failure** —
`test_sync.py::TestEngine::test_incremental_sync`.

**That failure is test-order pollution, not a broken feature.** Run on its own,
`test_sync.py` passes all 48 of its tests. It fails only in the full-suite run,
which means shared state is leaking between test files. Worth fixing, but it is
a test-hygiene defect rather than a functional one — and the distinction matters
before anyone reads "1 failed" as "sync is broken".

For comparison, Joe has 329 assembly tests. **Dispatch has roughly six and a
half times Joe's test coverage.**

---

## 2. The finding that matters most

### Dispatch is **Load-centric**, not Card-centric

The governing doctrine describes `CARD → WORKFLOW → CARD`, with Opportunity
Cards, Mission Cards, and Alert Cards as the authoritative operational objects.

**The implemented models are these:**

```
Load                   LoadVisibilityRecord    MilestoneEvent
EvidenceItem           ExceptionNotice         PODPackage
RetentionArchive       RateConfirmation        Expense
Settlement             Driver                  Equipment
MaintenanceSchedule    ComplianceDocument      LoadActivity
DetentionEvent         IFTATripLeg             IFTAFuelPurchase
LaneTemplate           DriverPay
```

**There is no `OpportunityCard` class. No `MissionCard`. No `AlertCard`. No
`ConfigReview`. No `TransactionLog`.**

Where the word "card" appears in the code, it means something else entirely:

| Occurrence | What it actually is |
| --- | --- |
| `medical_card`, `twic_card` | driver compliance documents |
| `"Business Card"` | a document inside a broker packet manifest |
| `check_dispatch_card(card_data, sandbox_id)` | **operates on a load dict** — "dispatch card" is a *view of a load*, not a distinct entity |
| `opportunity card data when booking a load` | load-board data used to create a RateConfirmation |

**I am stating this carefully because I got the previous version of this
question wrong.** Last time I saw absent card structures and framed it as
possible evidence they were unimplemented — in a workspace that had never been
given the repository. That was wrong and Mike corrected it.

**This is different.** This is the authoritative repository, confirmed by Mike,
inspected directly. The finding is not "cards are missing"; it is that
**Dispatch models operational truth as a `Load` with a rich object graph around
it**, and the Card-Centric vocabulary is a design layer that has not been
implemented under those names.

**That is not a defect.** A `Load` with visibility records, milestones,
evidence, exceptions, and a settlement chain *is* an operational truth object.
It is what the doctrine describes, wearing a different name.

---

## 3. The second finding: two architectures are in play

The repository's own `CLAUDE.md` describes a **different system** from the
Card-Centric doctrine:

> **DISPATCH** is a contract-locating, intelligence-processing, and
> archive-building platform… contracts are acquired, passed through
> deterministic rule modules that extract intelligence as JSON, then the user is
> emailed a checkbox prompt to decide the contract's fate.

Its five named layers are **Acquisition → Processing → Control → Archive →
Automation**, and `cin_lite/acquisition.py` fetches from **SAM.gov** — US
government contract opportunities.

**So the repository contains two overlapping visions:**

| | |
| --- | --- |
| **CIN-Lite** (`cin_lite/`) | government contract acquisition, rule-based intelligence extraction, email approval gate, archive |
| **L2-COS Operations Portal** (`portal/`, `dispatch/`) | a full trucking operations platform — loads, drivers, equipment, settlements, IFTA, compliance, detention |

The trucking platform is by far the larger and more developed of the two.

**This needs Mike's ruling, not my guess:** is CIN-Lite still live, superseded,
or a separate product sharing a repository?

---

## 4. What is genuinely valuable here — the salvage inventory

### Tier 1 — Directly usable by a Copilot Agent, today

| Asset | Where | Why it matters |
| --- | --- | --- |
| **90 REST API paths** | `portal/routes/dispatch_api.py` | **This is the bounded service interface.** Joe has been designing contracts against a hypothetical one for weeks. It exists, it is tested, and it is exactly the seam the architecture requires — Joe calls HTTP, never touches storage |
| **Deterministic scoring engine** | `dispatch/scoring.py`, 315 loc | `compute_route_risk`, `compute_hos_risk`, `compute_tomorrow_position_risk`, `compute_economic_opportunity`, `compute_deadhead_miles`, `compute_fuel_estimate`, `compute_score`. **This is the deterministic engine Joe must never duplicate** — and Joe explaining its output is Job 1 |
| **The Load object graph** | `dispatch/models.py`, 27 loc of classes | 20 dataclasses with validation. This is the operational truth Joe reads and never copies |
| **Notification engine** | `dispatch/notifications.py`, 569 loc | 8+ `notify_*` functions with **signed action tokens** and approval buttons. This is an existing, working human-in-the-loop gate |
| **2,186 tests** | `tests/` | Joe can be integrated against a codebase that will tell you when you break it |
| **Git history** | `.git`, 74 commits | The version control Joe's own tree lacks entirely |

### Tier 2 — Repurposable with adaptation

| Asset | Where | Repurpose as |
| --- | --- | --- |
| **Agent layer** | `cin_lite/agents/` — `router.py` 160 loc, `extractor.py` 208, `summarizer.py` 78, `proposal_writer.py` 108 | An existing agent pattern. Joe's deterministic router and reasoning capabilities do the same jobs more maturely — **compare before rebuilding either** |
| **Control layer** | `cin_lite/control.py`, 218 loc | **The email approval gate.** This is already an Inform/Review/Draft/**Execute** authority model in production form. It is the closest thing in either codebase to the authority model the new mission requires |
| **Publisher** | `portal/models/publisher.py` | Broker and direct-shipper packet manifests. Joe drafts, Publisher produces |
| **Library** | `portal/models/library.py` | Document classes. Joe routes to it, per doctrine |
| **Archive** | `cin_lite/archive.py` | Retention and storage |
| **Conflict checker** | `portal/models/conflict.py`, 243 loc | `check_dispatch_card(load, sandbox_id)` — validation Joe explains rather than performs |
| **Sandbox model** | `portal/models/sandbox.py` | A staging surface for evaluating loads before commitment |

### Tier 3 — Present but empty, and worth knowing

**Six top-level folders contain zero files:**

```
Launchers\   Config\   Constitution\   Context\   Deployment\   Temp\
```

Commits #70, #71, and #73 created a `D:\` ownership folder structure. **The
folders were created; nothing was put in them.** That is worth naming because a
reader could easily assume deployment or configuration exists there.

---

## 5. How Joe and Dispatch actually fit together

**They barely overlap, which is the good news.**

| Capability | Dispatch has | Joe has |
| --- | --- | --- |
| Load / operations data model | **yes, mature** | none |
| Deterministic scoring | **yes** | none, and must never build it |
| REST service surface | **yes, 90 paths** | none |
| Settlement, IFTA, compliance, maintenance | **yes** | none |
| Notifications with approval tokens | **yes** | none |
| Web portal UI | **yes** | its own tkinter window |
| **Conversation** | **none** | **yes** — router, six reasoning modes, multi-turn |
| **Voice in / out** | **none** | **yes** — output proven, input unproven |
| **Live LLM reasoning** | **no LLM call anywhere** | **yes** — Copilot signed in, live, proven |
| **Web-grounded research** | none | **yes, proven with attributions** |
| **Provenance discipline** | none | **yes** — per-entry source classes |
| **Governance / authority gate** | the email control layer | **yes** — enforced in five places |
| Outlook read | none | **yes**, read-only, mailbox registry |
| Company Library retrieval | document classes | **yes**, live index |

**Dispatch has no LLM integration anywhere.** No OpenAI, no Anthropic, no
Copilot. `cin_lite`'s "agents" are rule-based extractors, not model calls.

**Joe is precisely the missing layer**, and Dispatch is precisely the
operational substrate Joe has been missing. Neither duplicates the other in any
significant way.

---

## 6. What can be salvaged, repurposed, altered — the direct answer

### From Dispatch, use as-is

1. **The 90-path REST API** as Joe's only route to operational truth
2. **`dispatch/scoring.py`** as the deterministic engine Joe explains
3. **The Load object graph** as the thing Joe reads and never copies
4. **The test suite** as the regression net for every integration change
5. **Git** as the version control the whole effort currently lacks

### From Dispatch, repurpose

6. **`cin_lite/control.py`** — the email approval gate is a working authority
   model. It should inform Joe's Execute design rather than being reinvented
7. **`notifications.py` signed action tokens** — a proven pattern for
   authorising a consequential action without a second approval loop, which is
   exactly what mission §7 asks for
8. **Publisher manifests** for Joe's drafting outputs

### From Joe, contribute

9. **The conversation layer** — router, reasoning modes, multi-turn
10. **Live Copilot reasoning and web research** — Dispatch has none
11. **The provenance model** — `DISPATCH_FACT` is already reserved and produced
    by nothing, waiting for exactly this
12. **The governance gate** — Dispatch has no equivalent truth discipline
13. **Voice** — Dispatch has none
14. **The status vocabulary** — LIVE / READY / UNKNOWN, a timeout never cached
    as absence. Directly reusable for monitoring Dispatch's own health

### Alter, do not adopt

15. **Joe's standalone lifecycle** — becomes a Dispatch plugin
16. **Joe's Library index** — supersede with Dispatch's Library
17. **Joe's tkinter window** — becomes a portal surface
18. **`cin_lite/agents/`** — compare against Joe's equivalents; keep the better
    of each rather than running two agent layers

---

## 7. Reusability, restated with Dispatch in view

My previous estimate — **~45% of Joe directly reusable, ~76% with adaptation** —
was made without seeing Dispatch. **It holds, and one part of it firms up.**

`app/service.py`, the 1,128-line file classified ADAPT, was the largest
uncertainty because Dispatch's plugin lifecycle was unknown. It is now partly
knowable: Dispatch is a **Flask application** started by `run_portal.bat` →
`portal/app.py`. That means Joe integrates as a **blueprint or service inside a
Flask app**, not as a desktop process — a well-understood shape.

**This makes the ADAPT work more predictable, and it makes Joe's tkinter window
less reusable than estimated.** Roughly balanced.

---

## 8. On "Level 4 Copilot Agent"

**I do not know what Level 4 means here, and I will not guess.**

Joe's existing doctrine uses Level 1 / 2 / 3 for **record retention** —
temporary, saved, formal. A "Level 4 Agent" could mean a fourth retention tier,
or an autonomy tier, or something else entirely.

The distinction matters because it determines whether the target is *more
capability* or *more authority* — and those need very different work. **This
needs Mike's definition before it can be planned against.**

---

## 9. What must be settled before integration work begins

1. **Card-Centric doctrine versus the Load-centric implementation.** Does the
   doctrine get implemented, or does it get restated in terms of `Load`? This
   changes the whole integration surface
2. **Is CIN-Lite live, superseded, or a separate product?**
3. **What does "Level 4" mean?**
4. **The single failing test** — `test_incremental_sync`. It passes in
   isolation and fails in the full run, so it is test-order pollution rather
   than a broken feature. Low priority, but it will mask a real regression in
   that area if left
5. **The six empty folders** — is deployment expected to live there?

---

## 10. Migration to `D:\Joe Assistant` — what it actually requires

Mike states the build needs to move to `D:\Joe Assistant`, backed up to
`Copilot WorkSpace\Joe Assistant`. **Not performed** — the preservation mission
ended with a stop condition, and this is a relocation, not a backup.

**What the move breaks, and must be repaired with it:**

| Depends on the current path | Count |
| --- | --- |
| `configuration/joe.config.json` — library source paths | several |
| Launcher scripts using `%~dp0..` | 26 (mostly relative, likely safe) |
| **Desktop shortcuts** — absolute `TargetPath` and `WorkingDirectory` | **4** |
| Proof scripts resolving `PLUGIN_ROOT` from `__file__` | 8 (relative, safe) |
| Documents citing the development path | ~12 |

**The shortcuts and the config are the two that will actually break.** The
shortcut installer can simply be re-run; the config needs its library paths
checked.

**Recommended order:** move, re-run `INSTALL_JOE_SHORTCUTS.cmd`, verify config
paths, run the 329 tests and 24 proof steps, then re-run the backup and re-verify
by hash. **Say the word and I will do it as its own bounded task.**

---

Mike Zachary remains final authority.
