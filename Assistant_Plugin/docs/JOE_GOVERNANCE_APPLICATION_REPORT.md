# JOE — Governance Application Report

**Mission:** CLAUDE_CODE_MISSION_JOE_CARD_CENTRIC_DISPATCH, Step 1
**Scope:** the JOE sandbox only. Dispatch was not modified and was not read.
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

Applies the governing mission's role boundaries, capability-truth standards, and
drift protections to JOE. No Dispatch card structure was created inside JOE to
satisfy the architecture — the mission forbids it, and building a second source
of operational truth is the specific harm that prohibition prevents.

---

## 1. Manager assumptions — audited and reported

**Result: no functional Manager code exists in JOE.**

Searched every Python, Markdown, JSON, and CMD file in the sandbox. Eighteen
occurrences of the word, none of them a Manager component.

| Location | Occurrence | Kind | Disposition |
| --- | --- | --- | --- |
| `tests/test_joe.py:909` | `re.search(r"\bclass\s+\w*Manager\b", ...)` | **guard** — a test asserting no Manager class exists | keep |
| `proof/run_proof.py:638-644` | scans every source file for `class *Manager` | **guard** — proof step 18 | keep |
| `docs/JOE_CONSTITUTION_v1.md:100-133` | "There is no Manager component… Do not add a Manager." | **doctrine** | keep |
| `docs/JOE_BUILD_REPORT_v1.md:315` | "0 Manager classes" | reporting | keep |
| `docs/JOE_BUILD_REPORT_v2.md:30,397` | "No Manager component exists" | reporting | keep |
| `docs/JOE_LOCAL_PROOF_REPORT_v1.md:281` | "PASS No Manager component created" | proof output | keep |
| `docs/JOE_REVIEW_HANDOFF_v1.md:142` | "No Manager component created, referenced, or implied" | reporting | keep |
| `docs/JOE_TEST_REPORT_v1.md:40` | test-group description | reporting | keep |
| `runtime_data/memory/.../MEM-*.json` | the phrase "records manager" inside a Library search result | **incidental prose** in a retrieved document, not JOE's own text | keep — it is a record of what a document said |

**Nothing was deleted.** Every occurrence is either a guard that enforces the
prohibition or a statement of it. No Manager remnant requires disposition.

**No orchestration agent exists under another name.** JOE has no module that
routes work between other modules, holds authority over them, or arbitrates
between them. Capabilities are dispatched by a deterministic table in
`app/service.py::_dispatch_capability` — a lookup, not an orchestrator.

---

## 2. Role boundaries — applied

The mission's Section 5 defines what JOE is not. Checked against the code.

| JOE is not | Evidence in the sandbox |
| --- | --- |
| a Manager | §1 above |
| a dispatcher | no load, mission, or dispatch decision path exists |
| a Librarian | JOE reads the Library. It has no classify, catalog, index, or store path. `adapters/library_fs.py` is read-only |
| Publisher | no document production path |
| Intelligence | no analysis-product path |
| Route Risk | `ROUTE_RISK_EVENT` is a defined source class with **nothing producing it** |
| Outlook | JOE reads Outlook through a read-only adapter; 21 write calls are refused before any script runs |
| QuickBooks / ELD / GPS | not present |
| a voice technology company | voice is an adapter (`adapters/voice_sapi.py`) behind a replaceable interface |
| an autonomous business operator | every authority flag is a literal `False`; the governance gate forces them false and records a critical breach if one is set |
| a self-expanding general agent | capabilities are a fixed table; the router is regex, ordered, first match wins, with no model in the loop |

### Authority flags, enforced not asserted

`contracts/__init__.py::AssistantResponse` carries `approved`, `decided`,
`acted_on`, `operational_write` — all default `False`. `Governor.review` forces
any true value back to `False` and records a **CRITICAL** finding. A critical
breach is not softened or reworded; the whole response is replaced with a
refusal, because a reworded claim still reached the page once.

### The four command classes

The mission's Section 12 requires JOE to distinguish Inform, Review, Draft, and
Execute. **Partially present:**

| Class | State |
| --- | --- |
| Inform | present — LIBRARY, EXPLAIN, ANSWER, OPERATIONS capabilities |
| Review | **not present** — no deterministic review service exists to trigger |
| Draft | present — `_handle_draft`, always marked `DRAFT ONLY / NOT SENT` |
| Execute | **not present, and deliberately so** — there is no send, no write, no commit path anywhere in JOE |

A command to prepare, draft, or show cannot become authority to send, because
no send path exists to be authorised. That is stronger than a parser rule.

---

## 3. Truthful capability reporting — changed in this step

**Defect found and fixed: `Voice LIVE` covered two capabilities of different
maturity.** Voice output is proven and audible. Voice input binds an engine and
has never heard a person. One green chip across both is precisely the false
status indicator Section 11 names.

Now reported separately:

```
Voice out LIVE
Voice in  NOT CONNECTED
          the engine binds, but no person has spoken to it.
          Run the microphone test to prove it.
```

`Voice in` is hard-coded never to report LIVE from a binding alone, and states
what is blocking it. Five tests hold the distinction, including one asserting
the conflated chip is gone.

### Status vocabulary, and what each word is allowed to mean

| Word | Permitted meaning |
| --- | --- |
| `LIVE` | a real service answered during this session |
| `READY` | installed and reachable, nothing read yet — Outlook uses this deliberately rather than claiming LIVE |
| `SAMPLE` | fixture data, labelled on the answer itself |
| `NOT CONNECTED` | no service, and the blocker is named |
| `UNKNOWN` | could not be asked — **never** collapsed into absent |

The `present / absent / unknown` distinction is enforced in
`adapters/outlook_com.py::knows_account` (tri-state, `None` for unknown) and in
`adapters/mailbox_registry.py::Discovery.classify`. A failed enumeration is
never cached, so a transient outage cannot become a permanent "gone".

---

## 4. Drift protections — checked

The mission's Section 19 drift test, answered for the JOE sandbox as it stands.

| Question | Answer |
| --- | --- |
| Does this recreate Manager? | No. Nothing was added that routes or arbitrates |
| Does this turn JOE into Librarian, Publisher, Intelligence, Route Risk, Outlook, accounting, GPS, or a voice provider? | No. All external systems remain behind read-only adapters |
| What becomes the source of truth? | Nothing new. JOE holds interaction records only, and no operational truth |
| Could the result be achieved by reusing an existing module? | The voice split reused the existing `CapabilityStatus` contract. No new module was created |
| Is this the circumference of the Moon? | The voice split serves Section 11 directly. The Manager audit serves Section 4 directly |

### Guards that run on every proof

| Guard | Where |
| --- | --- |
| No Manager component | proof 18 scans every source file |
| Dispatch never contacted | proof 16 |
| No writes outside the plugin root | proof 17, `assert_within_plugin` |
| No credential in any shipped file | credential sweep across 218+ files |
| Copilot may never wear a local or Dispatch source class | `Governor.review`, and `SourceClass.NEVER_FROM_COPILOT` |
| Sample data never labelled live | `Governor.review` adds the notice |

---

## 5. What this step deliberately did NOT do

The mission is explicit, and these are recorded so a later reader does not read
their absence as an oversight:

- **No Opportunity Card, Mission Card, Alert Card, Config Review engine, or
  Transaction Log was created inside JOE.** Building them here to satisfy the
  architecture would create a second source of operational truth — the exact
  harm Section 13 prohibits.
- **Dispatch was not modified.** It was not read beyond counting files and
  searching for symbol names during the earlier survey.
- **No existing working functionality was removed.** The only behavioural change
  is that one status chip became two, and both are now truthful.
- **Step 2 was not begun.**

---

## 6. Regression after this step

| | Before | After |
| --- | --- | --- |
| Assembly tests | 324 | **329**, 328 passed, 1 skipped |
| Local proof | 24/24 | **24/24** |
| Control audit | 20/20 | **20/20** |
| Component suites | 350 OK | unchanged, untouched |

Files changed: `app/service.py`, `tests/test_joe.py`, `proof/run_proof.py`,
`docs/JOE_CURRENT_STATE_EVIDENCE.md`.

---

Mike Zachary remains final authority.
