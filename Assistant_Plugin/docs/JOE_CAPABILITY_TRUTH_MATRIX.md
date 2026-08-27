# JOE — Capability Truth Matrix

**Mission:** CLAUDE_CODE_MISSION_JOE_CARD_CENTRIC_DISPATCH, Step 1
**Measured:** 2026-08-26, by running the program
**Final authority:** Mike Zachary

Every row was measured, not read off a label. The mission's standard governs:

> Do not equate UI text with functionality, passing unit tests with operational
> readiness, existing function names with working integrations, configuration
> placeholders with active connections, or "LIVE" labels with verified service
> operation.

**Evidence classes used:**

| Class | Meaning |
| --- | --- |
| **PROVEN** | Implemented and operationally proven against a live service |
| **UNPROVEN** | Implemented, not operationally proven |
| **PARTIAL** | Works in part; the gap is named |
| **BLOCKED-HUMAN** | Cannot proceed without an action only Mike can take |
| **BLOCKED-EXTERNAL** | Cannot proceed without an external service or repository |
| **NOT IMPLEMENTED** | Does not exist |

---

## 1. What the status strip now says

```
Reasoning LIVE | Library LIVE | Outlook READY | Research LIVE |
Voice out LIVE | Voice in NOT CONNECTED | Dispatch NOT CONNECTED
```

**Changed in this step.** `Voice LIVE` previously covered voice input and voice
output together. Output is proven and audible; input has never heard a person.
One green chip across two capabilities of different maturity is exactly the
false status indicator the mission names. They are now reported separately, and
`Voice in` states what is blocking it.

---

## 2. The matrix

| Capability | Class | Symbol / file | What was measured | What it does NOT prove |
| --- | --- | --- | --- | --- |
| Launch by double-click | **PROVEN** | `START_JOE.cmd`, desktop shortcut **JOE** | window visible in 4.6 s, `pythonw`, 0 console windows | that Mike finds the screen usable — he reports it is visually poor |
| Written interaction record | **PROVEN** | `app/service.py::ask` | every request produces a record | — |
| Level 1 / 2 / 3, Print Ready, Delete | **PROVEN** | `memory/assistant_memory/retention.py` | proof steps 4–8; Print holds LEVEL_1 | — |
| 3-hour expiry, restart persistence | **PROVEN** | `MemoryStore` | proof 13 | — |
| Company Library retrieval | **PROVEN** | `adapters/library_fs.py` | 34 documents indexed, real documents returned | that the Library covers any given subject — it holds no detention or load-refusal procedure |
| Outlook read, read-only | **PROVEN** | `adapters/outlook_com.py` | live COM read; 21 write calls scanned and refused | — |
| Calendar date order and filtering | **PROVEN** | `_PREPARE["calendar"]` | chronological, item by item, on a mailbox that has a calendar | that Mike can ask JOE about his calendar — see below |
| Mail order, contact order | **PROVEN** | `_sort_contacts` | newest-first; alphabetical by the name shown | — |
| present / absent / **unknown** | **PROVEN** | `account_status()` | a timeout is unknown, never absent | — |
| Mailbox registry, 3-view discovery | **PROVEN** | `adapters/mailbox_registry.py` | Accounts + Stores + Folders reconciled | — |
| Per-mailbox failure isolation | **PROVEN** | `MailboxRegistry.source_for` | one mailbox failing does not disable another | — |
| **Calendar answers to Mike** | **PARTIAL** | — | **no approved mailbox holds a calendar.** JOE refuses and says why | JOE cannot answer calendar questions at all today |
| **Contact answers to Mike** | **PARTIAL** | — | same | — |
| Copilot authentication | **PROVEN** | `adapters/m365_copilot_auth.py` | MSAL public client, DPAPI blob verified byte-level | — |
| Copilot reasoning | **PROVEN** | `adapters/m365_copilot.py` | live prompt, live answer, signed in as Ops@ | production readiness — the API is `/beta` and Microsoft does not support it for production |
| Multi-turn conversation | **PARTIAL** | `prove_reasoning.py` | context carries; substantive answers are **non-deterministic** — 2/2, 1/2, 1/2, 0/2 across runs | that a follow-up will be answered on any given attempt |
| Six reasoning modes | **PROVEN** | `contracts::ReasoningMode` | enforced in the governance gate; a breach is refused | — |
| Web-grounded research | **PROVEN** | `adapters/research_provider.py` | 11 real attributions with URLs | that it replaces DOT or 511 — it states that it does not |
| Per-entry provenance | **PROVEN** | `contracts::Provenance` | Copilot and Library entries stay separate | — |
| **Voice output** | **PROVEN** | `adapters/voice_sapi.py::speak` | spoke aloud | — |
| **Voice input** | **BLOCKED-HUMAN** | `DriverVoiceLoop` | engine binds; microphone enumerated | **nothing.** No person has spoken to it |
| Microphone suppression while speaking | **UNPROVEN** | `DriverVoiceLoop.say` | 18 tests pass | that it holds against a real speaker in a real cab |
| **Audio-activity detection** | **NOT IMPLEMENTED** | — | — | JOE cannot distinguish a dead microphone from a silent room |
| Bluetooth headset operation | **BLOCKED-HUMAN** | `adapters/microphones.py` | the LEVN headset is known to Windows; not connected at last check | — |
| Continuous Driver Mode | **UNPROVEN** | `app/driver_voice.py` | loop, commands, and state machine tested headless | that it is usable while driving |
| Operator controls | **PARTIAL** | `ui/window.py` | 20/20 in a **headless** audit | **Mike reports some controls do not work. His finding stands.** |
| Physical printing | **NOT IMPLEMENTED** | — | `PRINT_READY` is a record state | nothing reaches a printer |
| Email send | **NOT IMPLEMENTED** | — | no send path exists anywhere | — |
| Teams chat writing | **NOT IMPLEMENTED** | — | not started | — |
| **Card access** | **NOT IMPLEMENTED** | — | JOE has no card model of any kind | — |
| **Dispatch connection** | **BLOCKED-EXTERNAL** | `adapters/dispatch_port.py` | contract and port only; `connected = False` | — |
| Config Review | **NOT IMPLEMENTED** | — | — | — |
| Transaction Log | **NOT IMPLEMENTED** | — | — | — |
| Route Risk | **NOT IMPLEMENTED** | — | deferred by instruction | — |
| GPS | **NOT IMPLEMENTED** | — | deferred by instruction | — |

---

## 3. Voice pipeline, stage by stage

The mission's Section 11 requires each stage reported separately. A failure at
one stage must never be reported as a general "Voice LIVE".

| Stage | State | Instrumented? |
| --- | --- | --- |
| 1. Input device selected | **works** — reads the Windows MMDevice registry | yes |
| 2. Audio signal received | **NOT IMPLEMENTED** | **no** |
| 3. Utterance recognized | engine binds; unproven with a voice | partly |
| 4. Command delivered to JOE | implemented — recognized text takes the typed path | yes |
| 5. Response produced | proven | yes |
| 6. Audio output started | proven | yes |
| 7. Audio output completed | proven | yes |

**Stage 2 is the honest gap.** Without signal detection, "JOE did not hear me"
and "the microphone is dead" look identical. That is a diagnostic Mike would
need on the road, and it does not exist.

---

## 4. Tests and proof — and what they cannot establish

| Suite | Count | Result |
| --- | --- | --- |
| Assembly tests | 329 | 328 passed, 1 skipped |
| Component suites (`ASST\1..6`) | 350 | all OK |
| Local operational proof | 24 steps | 24 passed |
| Control audit | 20 controls | 20 passed, **headless** |
| Email Connection Layer proof | 22 checks | all passed |
| Research proof | 23 checks | all passed |
| Copilot live proof | — | passed, live |

**None of this establishes that Mike can operate JOE.** Every run above
happened without him. Two things cannot be automated and are not claimed:
voice input with his voice, and operational acceptance.

---

Mike Zachary remains final authority.
