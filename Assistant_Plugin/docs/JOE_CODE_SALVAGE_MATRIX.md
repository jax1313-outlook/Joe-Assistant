# JOE — Code Salvage Matrix

**Mission:** BOOTSTRAP THE DISPATCH COPILOT AGENT, §10.A
**Type:** Analysis and planning only. **No code was written or modified.**
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

Every row was traced through actual code behaviour, not filenames or comments.
Line counts exclude blanks and comment-only lines. Test and proof reference
counts are symbol occurrences in `tests/test_joe.py` and `proof/run_proof.py`.

**Nothing is deleted or retired by this document.** Classification is a
recommendation about where code goes next, never permission to destroy it.

---

## Target architecture this is measured against

```
MIKE ↕ VOICE PROVIDER PLUGIN ↕ VOICE DOCK ↕ JOE COPILOT AGENT ↕ DISPATCH
```

Joe owns conversation. Dispatch owns operations.

The single test applied to every component: **does it help Joe converse, or
does it hold operational truth?** Anything holding operational truth is a
second source of truth once Joe is inside Dispatch, and cannot move across as-is.

---

## 1. The salvage summary

| Classification | Components | Lines |
| --- | --- | --- |
| **REUSE UNCHANGED** | 9 | ~2,050 |
| **ADAPT** | 6 | ~2,180 |
| **WRAP BEHIND INTERFACE** | 4 | ~1,110 |
| **REPLACE** | 2 | ~455 |
| **RETAIN AS LEGACY** | 3 | ~1,050 |
| **DO NOT USE** | 0 | 0 |

**Nothing in Joe is classified DO NOT USE.** Everything is either reusable,
adaptable, wrappable, or worth keeping as a working reference.

---

## 2. REUSE UNCHANGED

These move across as they are. They are conversation-layer or truth-discipline
code, they hold no operational state, and they carry real proof.

| Component | Path | Lines | Tests / proof | What it actually does | Future location | Dispatch dependency |
| --- | --- | --- | --- | --- | --- | --- |
| **Contracts, provenance, authority flags** | `contracts/__init__.py` | 344 | 74 / 5 | Defines `AssistantResponse`, per-entry `Provenance`, nine `SourceClass` values including `DISPATCH_FACT` and `ROUTE_RISK_EVENT` already reserved and unproduced, six `ReasoningMode` values, and authority flags that default `False` | `agent/contracts/` | none — `DISPATCH_FACT` is already the slot |
| **Governance gate** | `governance/__init__.py` | 244 | 8 / 1 | Reviews every response; forces authority flags false and records a CRITICAL breach; refuses rather than rewords; enforces the reasoning-mode contract; blocks Copilot wearing a local or Dispatch source class | `agent/governance/` | none |
| **Retention engine** | `memory/assistant_memory/retention.py` | 237 | 20 / 1 | Level 1/2/3, Print Ready without level change (Doctrine C4), Delete, terminal-record refusal, 3-hour expiry | `agent/conversation/retention/` | **none — see the warning below** |
| **Memory store** | `memory/assistant_memory/store.py` | 118 | 13 / 11 | File-backed conversation records; survives restart | same | none |
| **Driver Voice Loop** | `app/driver_voice.py` | 212 | 14 / 0 | Continuous listen→answer→speak→listen; microphone suppression while speaking; ordinary spoken commands; a question about a command is not the command | **Voice Dock** | none |
| **Microphone diagnostics** | `adapters/microphones.py` | 212 | 43 / 1 | Enumerates Windows capture endpoints; present/absent/unknown; loopback devices permanently excluded; preference remembered and reported, never silently enforced | **Voice Dock** | none |
| **Date parsing** | `app/when.py` | 93 | 12 / 4 | today / tomorrow / this week / next week / named date / weekday | `agent/conversation/` | none |
| **Logbook** | `app/logbook.py` | 46 | 0 / 0 | Append-only event log | `agent/` — **candidate input to Dispatch's Transaction Log** | see §6 |
| **Path containment** | `app/bootstrap.py` | 62 | 2 / 1 | `assert_within_plugin` refuses writes outside the root | `agent/` | none |

### The one warning in this group

**The retention engine holds conversation records, not operational records —
and that distinction must be enforced, not assumed.** Level 3 "formal record"
is currently a *conversation* artifact. Once Joe is inside Dispatch, anything
that looks like a durable operational record must be a Dispatch card, not a
Joe memory file. The engine is reusable; **what gets stored in it needs a
boundary review** before Joe goes near cards.

---

## 3. ADAPT

Sound code that needs changes for the new architecture.

| Component | Path | Lines | Tests / proof | Why it must change | Required adaptation | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| **AssistantService core** | `app/service.py` | 1,128 | 154 / 140 | It is the whole application today — it owns startup, adapters, capability dispatch, retention, and status. Inside Dispatch it must become a **component with a lifecycle**, not an application | Split into an agent façade plus capability handlers. Startup/shutdown driven by Dispatch's plugin lifecycle. Remove the assumption that Joe owns the process | **Highest in the repository.** It is the largest file and the most-referenced by tests. Splitting it risks the 329-test safety net if done in one move |
| **ReasoningCapabilities** | `app/reasoning_capabilities.py` | 423 | 2 / 1 | Explain / Summarize / Draft / Procedure / Answer are the right shapes, but they ground in Library and Outlook only. They must gain card grounding | Add a card-grounded mode; keep Library grounding; keep the ungrounded-retry behaviour | Medium — the retry logic is subtle and earned |
| **Deterministic router** | `app/router.py` | 228 | 3 / 0 | Regex, ordered, first-match-wins, no model. **Sound design.** But it has no card intents and no Inform/Review/Draft/Execute classification | Add command-class classification. Add card-target extraction. Keep it deterministic | Medium — low test coverage (3 refs) for a component this load-bearing |
| **Email Connection Layer** | `adapters/mailbox_registry.py` | 429 | 39 / 2 | Excellent as a mailbox registry. But Outlook transport is a **Dispatch-owned** function in the target architecture | Keep the registry and discovery; route send/transport through Dispatch's Outlook transport rather than owning it | Low |
| **Outlook adapter** | `adapters/outlook_com.py` | 561 | 63 / 1 | Read-only COM, 21 write calls refused. Solid. Same ownership question | Keep for read. Never add write — Dispatch owns transport | Low |
| **User interface** | `ui/window.py` | 631 | 58 / 21 | Joe's own window will not exist inside Dispatch. But the **VOICE button, the response pane, the history list, and the retention buttons** are all directly reusable as a Dispatch panel | Re-host as a Dispatch UI surface. Keep the VOICE button states verbatim | Medium — and see the operator finding in §7 |

---

## 4. WRAP BEHIND INTERFACE

Working code that must not be called directly by the agent.

| Component | Path | Lines | Why wrap | Interface required |
| --- | --- | --- | --- | --- |
| **M365 Copilot provider** | `adapters/m365_copilot.py` | 413 | Provider-specific. `/beta` endpoint Microsoft does not support for production — it will change | `ReasoningProvider` (already exists) |
| **MSAL auth** | `adapters/m365_copilot_auth.py` | 279 | Holds the only credential path. DPAPI-encrypted, no client secret, no readable token — **verified at byte level** | An auth interface. **Never hand this to the voice provider** |
| **Reasoning provider adapter** | `adapters/reasoning_provider.py` | 443 | Already the interface. Keep it as the seam | — |
| **Voice SAPI adapter** | `adapters/voice_sapi.py` | 243 | This is the **provider plugin** the Voice Dock replaces. It works and it is limited — see §5 | Voice provider interface inside the Voice Dock |

---

## 5. REPLACE

| Component | Path | Lines | Why | Replacement |
| --- | --- | --- | --- | --- |
| **Voice input capture** (inside `voice_sapi.py`) | `adapters/voice_sapi.py::listen` | ~80 | `System.Speech` exposes only `SetInputToDefaultAudioDevice()`. **There is no way to bind a chosen capture device.** This is why Joe cannot use Mike's Bluetooth headset unless Windows already defaults to it | A stream-based provider through the Voice Dock. Azure Voice Live is the leading candidate and adds echo cancellation, noise suppression, and end-of-turn detection |
| **Settings interface** | `ui/settings_panel.py` | 299 | **Zero test references, zero proof references.** It renders correctly in the control audit but nothing pins its behaviour. It also assumes Joe owns its own settings screen | Rebuild as a Dispatch settings surface, with tests this time |

**`ui/settings_panel.py` is the least-defended file in the repository.** It is
299 lines with no test coverage at all. That is worth naming plainly rather
than carrying forward on the strength of it having worked once.

---

## 6. RETAIN AS LEGACY

Preserve, do not migrate, do not delete.

| Component | Path | Lines | Why retained | Why not migrated |
| --- | --- | --- | --- | --- |
| **Library adapter** | `adapters/library_fs.py` | 168 | Working filesystem index over the real Company Library; 34 documents | **Dispatch owns Library.** Joe must route through Librarian, not index files itself. Keep as the reference implementation and as a fallback while Dispatch's Library interface is unavailable |
| **Research adapter** | `adapters/research_provider.py` | 209 | Live Copilot web grounding with real attributions; sample mode always labelled | Research Scout is separate from Dispatch and Joe. Ownership needs Mike's ruling — see the conflict register |
| **Proof scripts and launchers** | `proof/*.py`, `launchers/*.cmd` | ~2,400 total | 8 proof scripts and 13 launchers that genuinely exercise live services | They prove the **standalone** program. Dispatch will have its own lifecycle and its own proof harness. **Keep every one** — they are the historical evidence that these capabilities worked |

---

## 7. Components with a gap worth stating before anyone relies on them

| Component | Gap |
| --- | --- |
| `ui/settings_panel.py` | **0 tests, 0 proof references.** 299 lines |
| `app/logbook.py` | **0 tests, 0 proof references.** 46 lines — small, but it is the closest thing Joe has to a transaction record and nothing pins it |
| `app/router.py` | **3 test references** for 228 lines of load-bearing routing. It has been the source of several real defects — "how do I delete this" once executed a delete |
| `adapters/library_fs.py` | 5 test references for 168 lines |
| `app/reasoning_capabilities.py` | 2 direct references for 423 lines. It is exercised heavily but indirectly, through service tests |
| **Driver Voice Loop** | 14 tests, all headless. **Never proven with a human voice** |
| **The whole UI** | Control audit passes 20/20 **headless**. Mike operated the real window and reported some controls do not work. **His finding stands** |

---

## 8. What is not in Joe at all

Recorded so the build plan does not assume otherwise.

| Absent | Consequence |
| --- | --- |
| Card model of any kind | Joe has no Opportunity Card, Mission Card, or Alert Card representation |
| Config Review | No capacity, weight, or sequencing calculation exists — **and none should be built in Joe** |
| Transaction Log | `app/logbook.py` is an event log, not a transaction record |
| Scoring | Absent, and must stay absent |
| Publisher interface | Absent |
| Execute authority | **No send, write, or commit path exists anywhere in Joe.** This is stronger than a parser rule, and §7 of the mission changes it |
| Audio-activity detection | Joe cannot distinguish a dead microphone from a silent room |

---

## 9. Reusability calculation

**Method.** Non-blank, non-comment lines per component, classified, then summed.
Test and proof coverage is reported but **not** used to inflate the percentage —
a well-tested component that does not fit the architecture is still not reusable.

| Class | Lines | Share |
| --- | --- | --- |
| REUSE UNCHANGED | ~2,050 | 29% |
| ADAPT | ~2,180 | 31% |
| WRAP BEHIND INTERFACE | ~1,110 | 16% |
| REPLACE | ~455 | 6% |
| RETAIN AS LEGACY | ~1,050 | 15% |
| *(remainder: small modules, `__init__`, sample corpus)* | ~155 | 3% |

**Directly carried forward (REUSE + WRAP): ~45%.**
**Carried forward with work (adding ADAPT): ~76%.**

**This figure is honest but soft, and here is why.** `app/service.py` alone is
1,128 lines — 16% of the repository — and it is classified ADAPT because it is
currently *the application*. How much of it survives depends entirely on how
Dispatch's plugin lifecycle works, which **cannot be known without the Dispatch
repository.** If the split goes badly, the ADAPT share drops sharply.

**Treat 76% as an upper bound, not a forecast.**

---

## 10. What preserves the historical implementation

Recommended, not performed:

- The entire current tree stays at `D:\SANDBOX\Assistan_Building\Assistant_Plugin`
- Nothing is deleted, including everything classified RETAIN AS LEGACY
- The six `ASST\1..6` component workstreams stay untouched
- Every proof script and its evidence file is preserved as the record that these
  capabilities once genuinely worked

---

Mike Zachary remains final authority.
