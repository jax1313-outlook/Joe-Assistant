# JOE - Known Limitations

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0

Stated without understatement, per mission section 22. Where a word is
forbidden by the evidence standard, it is not used.

---

## 0. Both remaining proofs are one command away

Neither can be run by JOE. Both are now a single double-click for
Mike, and both refuse to report a pass they did not earn:

| Command | Proves | Exit 2 means |
| --- | --- | --- |
| `launchers\PROVE_COPILOT.cmd` | reasoning is live | blocked on the Entra app registration |
| `launchers\PROVE_VOICE_INPUT.cmd` | voice input works | no recognition engine, or run with nobody present |

`PROVE_VOICE_INPUT.cmd` refuses to run unattended rather than record an empty
result as an outcome of any kind. `PROVE_COPILOT.cmd` fails a fluent answer that
claims a Company Library, Outlook, Route Risk, or Dispatch source class.

Steps to unblock Copilot: [COPILOT_ACTIVATION_STEPS.md](COPILOT_ACTIVATION_STEPS.md).

## 0b. Mailbox discovery reads Accounts only

The Outlook adapter enumerates `Namespace.Accounts`. A **shared mailbox**
appears in `Namespace.Stores` and `Namespace.Folders` but not in `Accounts`, so
a shared mailbox is invisible to discovery. On the current profile all three
views agree, so the gap does not bite today — and it would silently hide a
mailbox on a profile where they diverge.

Reconciling all three views is EMAIL_CONNECTION_LAYER_v1, which is approved and
not being built yet. Evidence:
[MAILBOX_DISCOVERY_EVIDENCE.md](../proof/MAILBOX_DISCOVERY_EVIDENCE.md).

## 1. Reasoning is LIVE — Microsoft 365 Copilot, PILOT / PREVIEW

**`Reasoning LIVE`.** Signed in as `Ops@l1truck.com` on 2026-08-25. A real
prompt was sent to the Microsoft 365 Copilot Chat API and a real answer came
back, followed by a second turn on the same conversation. Evidence:
[COPILOT_LIVE_PROOF.md](../proof/COPILOT_LIVE_PROOF.md).

**It is still a PILOT.** Microsoft states the Copilot Chat API is a `/beta`
endpoint and is not supported for production use. Endpoints and response shapes
can change without notice.

### What live reasoning does not mean

- **Copilot is constrained to approved material.** In the follow-up turn it
  declined to answer, saying the supplied context did not cover the question.
  That is JOE refusing to answer a company question from general
  knowledge. Whether that constraint is right for every capability is a
  doctrine question for Mike.
- **Research is still SAMPLE.** Live reasoning did not make research live.
- **Nothing gained authority.** Copilot still cannot approve, decide, send,
  schedule, modify Outlook, or touch Dispatch. Every boundary flag is `False`.

### The wording that stood here before

## 1. The largest limitation: no reasoning provider

**No reasoning or language provider is connected.** JOE cannot
compose an original answer to an open question.

What happens instead: it searches approved Library material for what you asked,
and if it finds nothing it says there is no source. It does not produce
something that reads like an answer.

This means "Summarize what I need to know" and "Explain that in plain
language" work only to the extent that Library material exists to quote. There
is no summarization of arbitrary text, because summarizing requires reasoning.

**Consequence:** the program is genuinely useful for finding, reading,
watching, and keeping. It is not useful for thinking. That gap is the honest
shape of this build.

## 2. Research is fixture-only

`NOT CONNECTED` to any research service. No provider, no credential, no
network.

Research returns supplied sample briefs, labelled `SAMPLE DATA` in the status
strip, in the response notices, and in the provenance line. It is never
presented as live research.

**Blocker:** an approved research provider and a credential. The adapter is
built and a provider can be bound without touching the Research capability.

## 3. Voice input is not proven

The recognition engine binds (`MS-1033-80-DESK`), a microphone is present, and
the Listen button is wired to a real recognizer.

**But no automated run can prove speech recognition** - it needs a person to
speak. So voice input is **IMPLEMENTED BUT NOT OPERATIONALLY PROVEN**.

Voice **output** is proven: the engine was bound, rendered to a WAV file
(115,546 bytes), and spoke aloud during the local proof.

## 4. Printing is not implemented

No printing service is bound. Print marks a record `PRINT_READY` and records a
request.

The program states: *"Print request recorded. Nothing was physically printed."*
It will not say a document was printed, because none was.

## 5. Dispatch integration does not exist

Only an **interface contract** exists. No approved Dispatch interface has been
published to connect to, and none was contacted.

Per the evidence standard: **it is not correct to say Dispatch integration
exists.** A contract exists. Those are different things.

## 6. No background expiration timer

Records expire when a sweep runs, not on a clock. `history()` sweeps before
returning, so opening the window is enough for normal use.

**If the program is never opened, nothing expires.** A record past its three
hours sitting in an unopened folder is stale, not yet marked.

This is stated rather than described as continuous automatic deletion, which it
is not.

## 7. Outlook limitations

- **Read-only, permanently.** No send, reply, forward, accept, decline,
  schedule, move, delete, or mark-read. Not disabled - absent.
- **First use is slow.** It starts Outlook if it is not running: 10-25 seconds.
  Subsequent reads are faster.
- **Calendar is date-ordered within a window.** Fixed after the first build,
  which returned folder order. The calendar is now sorted by start time, has
  recurring series expanded, and is restricted to `calendar_window_days`
  (default 14) starting at midnight today. Entries outside that window are not
  returned - raise the setting to look further ahead.
- **Item cap.** 60 items per read by default (`outlook.max_items`). Within the
  date window that is the *soonest* 60, not an arbitrary 60.
- **Mail and contacts are still in folder order.** Only the calendar was
  fixed. Inbox order is whatever Outlook returns, which is usually but not
  guaranteed to be by received time.
- **All times are shown as Outlook returns them**, not normalized to UTC.
- **If the date filter fails** - a non-US locale date format, for instance -
  the adapter falls back to a plain date-sorted view without recurrence
  expansion, and reports `date_no_recurrences`. If sorting itself fails it
  falls back to folder order and says `folder order, NOT chronological`
  in the response. It never silently degrades.

## 8. Library limitations

- **Whole-word matching only.** `policies` will not find `policy`. No stemming,
  no synonyms, no fuzzy matching.
- **Formats:** `.md`, `.markdown`, `.txt`, `.docx` only. **No PDF, no
  `.xlsx`, no `.pptx`, no `.doc`.** Skipped files are counted and reported.
- **Index is rebuilt every launch** and held in memory. Fine at 34 documents;
  unmeasured at thousands.
- **Score formula** is `5 x title matches + 1 x body matches`, with company
  material breaking ties above sample material. Predictable, and sometimes
  wrong for a long document that discusses a term throughout.

## 9. Driver mode is partial

Spoken responses are shortened and long text defers to the written copy. But:

- **There is no hands-free activation.** Listen is a button. No wake word, no
  push-to-talk hardware binding.
- **The 60-word limit is a judgement**, not a measurement against real speech
  rates at road speed.
- Driver mode is not automatically detected from motion or context; it is
  inferred from phrasing or set in configuration.

## 10. UI limitations

- **No automated UI test.** Clicks, typing, and rendering were exercised by
  hand and in the local proof, not by an automated driver.
- **One window, one conversation.** No tabs, no multiple sessions.
- **No message editing, search, export, or copy-to-clipboard.**
- **Verified at one screen size and DPI.** Rendering elsewhere is unverified.
- **The status strip shows short chips**; full detail requires hovering.

## 11. Data and security limitations

- Records are **plain readable JSON with no encryption** and no access control
  beyond Windows file permissions.
- **Purged content is unrecoverable.** Delete and expiry have no undo.
- `runtime_data` accumulates tombstones indefinitely. **No pruning policy.**
- **One operator at a time is assumed.** Two instances writing the same record
  simultaneously is untested and unguarded.

## 12. Capabilities permitted by doctrine but not built

The governing Constitution permits these; this build does not implement them:

- **Summarize** (needs reasoning)
- **Draft** (needs reasoning)
- **Train** and **procedure assistance** (needs content and reasoning)
- **Monitor** in the continuous sense - it reads when asked, it does not watch

## 13. Verified on one machine only

Windows 11 Pro 26200, Python 3.14.5, tkinter 8.6, Outlook 16.0.0.20326, two
SAPI voices, one display. Nothing is verified on any other machine.

## 14. What it cannot tell you

JOE cannot tell you whether a document is current, whether a rate is
good, or whether to take a load. It finds, reports, and keeps.

**Every operational decision stays with Mike Zachary.**
