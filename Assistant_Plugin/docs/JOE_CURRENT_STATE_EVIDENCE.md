# JOE — Current State Evidence

**Mission:** CLAUDE_CODE_MISSION_JOE_CARD_CENTRIC_DISPATCH, §16.A
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

This document reports what JOE **actually does**, with file paths and symbols,
and separates that from what it **appears** to do. Every status here was
measured by running the program, not read off a label.

The mission's own standard governs: a `LIVE` label is not proof, passing unit
tests are not operational readiness, and a function name is not a working
integration.

---

## 1. Where JOE is, and how it starts

| | |
| --- | --- |
| Development path | `D:\SANDBOX\Assistan_Building\Assistant_Plugin` |
| Entry point | `joe_main.py` |
| Double-click launcher | `START_JOE.cmd`, and a desktop shortcut named **JOE** |
| Runtime | Python 3.14.5 via the `py` / `pyw` launcher. `python` on PATH is a Microsoft Store stub, not an interpreter |
| UI | tkinter 8.6, worker threads plus a queue so a slow call never freezes the window |
| Configuration | `configuration/joe.config.json` |
| Deployment template | `configuration/joe.config.template.json` — ships disconnected |
| Source files | 74 Python files, 10 adapters, 13 launchers, 8 proof scripts, 14 documents |

The six component packages — `assistant_library`, `assistant_memory`,
`assistant_outlook`, `assistant_research`, `assistant_ui`, `assistant_voice` —
came from the `ASST\1..6` workstreams and are deliberately **not** renamed.
Renaming them is cosmetic, would break component isolation, and changes nothing
an operator sees.

---

## 2. Capability status, measured 2026-08-26

```
Reasoning LIVE | Library LIVE | Outlook READY | Research LIVE |
Voice LIVE | Dispatch NOT CONNECTED
```

| Capability | State | Evidence | Honest reading |
| --- | --- | --- | --- |
| Reasoning | **LIVE** | Signed in as `Ops@l1truck.com`, state `SIGNED IN`. A real prompt returned a real answer. `proof/COPILOT_LIVE_PROOF.md` | **Implemented and operationally proven** — but PILOT/PREVIEW, see §7 |
| Library | **LIVE** | 34 documents indexed from the real Company Library | Implemented and proven |
| Outlook | **READY** | Installed, read-only, connects on demand. `READY` deliberately does not claim `LIVE` — nothing has been read yet this session | Implemented and proven |
| Research | **LIVE** | Live Copilot web grounding returned 11 real attributions with URLs. `proof/RESEARCH_PROOF.md` | Implemented and proven |
| Voice **output** | **LIVE** | System.Speech; spoke aloud during proof | Implemented and proven |
| Voice **input** | **NOT PROVEN** | Engine binds, microphone present. **Mike has never spoken to it.** | **Blocked by human action** |
| Dispatch | **NOT CONNECTED** | `dispatch.connected = False`. No interface published | Not implemented, by instruction |

---

## 3. What JOE actually does — with symbols

### Retention and memory — implemented and proven

| Function | Where | Proof |
| --- | --- | --- |
| Level 1 temporary records, 3-hour expiry | `memory/assistant_memory/retention.py` | proof 4 |
| Level 2 on "Save this" | `RetentionEngine.apply` | proof 5 |
| Level 3 formal record plus artifact request | same | proof 6 |
| Print Ready **without** changing interaction level | `_print_ready` | proof 7, Doctrine C4 |
| Delete, and refusal on terminal records | `_delete` | proof 8 |
| Survives restart | `MemoryStore` | proof 13 |

### Reasoning — implemented and proven

| Function | Where |
| --- | --- |
| MSAL public-client auth, DPAPI cache | `adapters/m365_copilot_auth.py` |
| Copilot Chat API `/beta` | `adapters/m365_copilot.py` |
| Six reasoning modes | `contracts/__init__.py::ReasoningMode` |
| Mode contract enforced | `governance/__init__.py::Governor.review` |
| Multi-turn conversation | `proof/REASONING_PROOF.md` |

### Outlook — implemented and proven, read-only

| Function | Where |
| --- | --- |
| Read-only COM via PowerShell | `adapters/outlook_com.py` |
| 21 write-capable calls scanned and refused | `FORBIDDEN_COM_CALLS` |
| Calendar in date order, recurrences expanded | `_PREPARE["calendar"]` |
| Mail newest-first, contacts alphabetical by shown name | `_sort_contacts` |
| present / absent / **unknown** | `account_status()` |
| Mailbox registry, three-view discovery | `adapters/mailbox_registry.py` |

### Voice — partly proven

| Function | Where | State |
| --- | --- | --- |
| Speech output | `adapters/voice_sapi.py::speak` | proven, audible |
| Continuous Driver Mode loop | `app/driver_voice.py` | **implemented, not proven with a human** |
| Microphone suppressed while speaking | `DriverVoiceLoop.say` | 18 tests; **not proven live** |
| Microphone enumeration and diagnostics | `adapters/microphones.py` | proven |
| VOICE button, lowercase off / uppercase on | `ui/window.py` | implemented |

---

## 4. What JOE appears to do but does not

This is the section the mission asks for most directly.

| Appears | Reality |
| --- | --- |
| **"Voice LIVE"** in the status strip | This reports **voice OUTPUT only**. Voice input has never been proven with Mike's voice. The single label covers two capabilities of different maturity — a real reporting defect, and the mission's §11 names it explicitly |
| Calendar questions work | **They do not.** Neither approved mailbox holds a calendar. JOE refuses and says why, which is correct — but a reader seeing `Outlook READY` might expect calendar answers |
| **"Research LIVE"** | True, but it is Copilot web grounding. It is **not** a research department, and it explicitly states it does not replace DOT or 511 monitoring |
| JOE knows about loads, missions, or cards | **It does not.** JOE has no card model, no mission concept, and no Dispatch connection. It answers from the Company Library, Outlook, and Copilot |
| Printing | `PRINT_READY` is a record state. **Nothing is sent to a printer.** No `PRINT_SUBMITTED`, `PRINT_FAILED`, or `PRINT_CONFIRMED` exists |
| Controls all work | The control audit passes 20/20 **headless**. Mike operated the real window and reported that some controls do not work. **His finding stands; the audit does not overrule it** |

---

## 5. Voice pipeline condition — stage by stage

The mission's §11 requires each stage reported separately. Current honest state:

| Stage | Condition | Evidence |
| --- | --- | --- |
| 1. Input device selected | **Works** | Reads the Windows MMDevice registry. Currently `Internal Microphone` |
| 2. Audio activity detected | **NOT INSTRUMENTED** | There is no signal-level detection. JOE cannot presently distinguish "silence" from "microphone dead" |
| 3. Utterance recognized | **Engine binds; unproven live** | `MS-1033-80-DESK` recognizer present |
| 4. Command reaches JOE | **Implemented** | Recognized text takes the same path as typed input, deliberately |
| 5. JOE produces a response | **Proven** | via the normal reasoning path |
| 6. Audio output heard | **Proven** | spoke aloud in proof |
| 7. Diagnostics identify the failing stage | **PARTIAL** | Device and engine problems are reported. Stage 2 is not instrumented, so a dead microphone and a silent room look identical |

**Bluetooth:** the `LEVN LE-HS015` headset is known to Windows, including its
Hands-Free endpoint. It was **not connected** at last check, so JOE would hear
the internal microphone.

**A constraint that shapes the whole design:** `System.Speech` exposes only
`SetInputToDefaultAudioDevice()`. There is no way to bind a chosen capture
device. A device preference is therefore remembered and reported, **never
silently enforced** — otherwise Mike speaks into a headset while JOE listens to
the laptop lid.

---

## 6. Dispatch connection condition

**Not connected. Never connected. No card access of any kind.**

| | |
| --- | --- |
| `dispatch.connected` | `False` |
| Interface | `adapters/dispatch_port.py` — a contract and port only |
| Dispatch files read | none |
| Dispatch databases touched | none |
| Card model in JOE | **none exists** |
| Proof | proof step 16 asserts Dispatch was never contacted during the run |

Every prior mission forbade contacting Dispatch. This mission authorises
**review** of the Dispatch codebase. See §9 — the authoritative path is not yet
established.

---

## 7. Known limitations and failures

1. **Voice input is unproven.** Blocked by human action.
2. **The Copilot Chat API is `/beta`.** Microsoft states it is not supported for
   production. Endpoints may change without notice.
3. **`Voice LIVE` conflates input and output.** A reporting defect.
4. **Audio-activity detection does not exist.** Stage 2 of the voice pipeline is
   uninstrumented.
5. **No approved mailbox holds a calendar or contacts.** Mike's 602 appointments
   and 145 contacts are on `jax1313@outlook.com`, which is not approved.
6. **Reasoning proof is non-deterministic.** Copilot answers substantively on
   some runs and hedges on others; across recent runs the two-conversation proof
   scored 2/2, 1/2, 1/2, and 0/2. **A retry was added and did not settle it.**
   This is a real robustness gap, not a passing result.
7. **No card model, no Opportunity Card, no Config Review, no Transaction Log.**
   None of the Card-Centric architecture exists in JOE.
8. **Mike's operator finding is unresolved:** some controls work, some do not,
   and the screen is visually poor.

---

## 8. Tests and proof — what they do and do not establish

| Suite | Count | Result |
| --- | --- | --- |
| Assembly tests | 324 | 323 passed, 1 skipped |
| Component suites (`ASST\1..6`) | 350 | all OK |
| Local operational proof | 24 steps | 24 passed |
| Control audit | 20 controls | 20 passed **headless** |
| Email Connection Layer proof | 22 checks | all passed |
| Research proof | 23 checks | all passed |

**What none of this establishes:** that Mike can operate JOE. Every one of
these ran without him. The mission's standard is explicit — *if Mike cannot
launch it and operate it, it is not operationally delivered.*

Two proofs are blocked on him and cannot be automated: voice input with his
voice, and operational acceptance.

---

## 9. The blocker on the rest of this mission

§15 requires the **current Dispatch repository path**. It has not been
established, and I will not guess.

Eight candidate trees exist on this machine:

| Path | Python files | Newest source | Card models found |
| --- | --- | --- | --- |
| `D:\Dispatch Operations` | 138 | 2026-08-03 | 1 file mentions an opportunity card |
| `D:\Level 1\cin-hybrid-claude-l2-cos-dispatch-refactor-c1ett1` | 75 | 2026-07-27 | none |
| `…\Copilot WorkSpace\dispatch` | 57 | 2026-08-01 | none |
| `D:\Level 1\Level 1 Dispatch` | 0 | — | — |
| `D:\Level 1\Dispatch-SAM` | 0 | — | — |
| `D:\DISPATCH_AND_SAM_RECOVERY\03_DISPATCH_PROGRAM` | 0 | — | — |
| `D:\Dispatch Operations` *(dup listing)* | — | — | — |
| `D:\SANDBOX\Play-Pen\Dispatch` | 0 | — | — |
| `D:\SANDBOX\Dispatch Architecture` | 0 | — | — |

**Searched across all three code-bearing trees for the locked architecture:**

| Looked for | Files found |
| --- | --- |
| Opportunity Card | **1**, in `D:\Dispatch Operations` |
| Mission Card | **0** |
| Alert Card | **0** |
| Config Review | **0** |
| Transaction Log | **0** |
| Legacy `Manager` references | 1 file per tree |

**Card-Centric Dispatch implementation status cannot yet be determined
because the authoritative Dispatch repository has not been reviewed.**

Mike has confirmed the authoritative repository is **not available to this
workspace**. JOE was intentionally developed in an isolated sandbox on an
external drive, so the trees surveyed above are not Dispatch and were never
expected to contain it.

The survey above therefore establishes exactly one thing: **these particular
locations do not contain the card structures.** It does not establish that the
structures do not exist. An earlier revision of this section framed the absence
as evidence that Card-Centric Dispatch might be unimplemented. That was wrong -
absence of evidence in a workspace that was never given the repository is not
evidence of absence, and the conclusion is withdrawn.

Documents §16.B, C, and D remain blocked until the authoritative repository is
made available for review.

Nothing in any Dispatch tree was modified, and nothing was read beyond counting
files and searching for the symbol names listed above.

---

Mike Zachary remains final authority.
