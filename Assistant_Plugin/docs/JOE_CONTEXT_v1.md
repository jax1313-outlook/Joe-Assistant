# JOE - Context

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Location:** `D:\SANDBOX\Assistan_Building\Assistant_Plugin`
**Final authority:** Mike Zachary

Governing doctrine, not restated here:
`..\..\JOE_CONSTITUTION_v1\` (Documents 1-5, v1.0)

---

## 1. What this program is

The assembled Level 1 Assistant: one runnable Windows program that puts the six
bounded components behind a single window Mike can open from the desktop.

It is a **Dispatch Plugin**. Dispatch is the General Contractor, the System of
Record, and the Operational Authority. This program is a specialized staff
function whose one job is stated in
`JOE_CONSTITUTION_v1/01_CONTEXT_v1.md` section 4:

> Reduce Mike Zachary's owner/operator cognitive load while supporting Dispatch
> operations.

## 2. What it does

| Mike does this | The program does this |
| --- | --- |
| Double-clicks `START_JOE.cmd` | Opens a window. No console, no command line. |
| Types an ordinary sentence | Routes it to one bounded capability and answers |
| Reads the answer | Sees the direct answer first, then the full written response |
| Says "Save this" | Level 1 becomes Level 2, expiration cleared |
| Says "Level 3 this under Ideas" | Formal record, destination kept, artifact requested |
| Says "Print this" | Print Ready. Interaction level unchanged. Nothing printed. |
| Says "Delete this" | Content purged, removed from the active view |
| Presses Library search | Searches approved local Library locations |
| Presses Research | Returns findings, sources, uncertainty, recommendation |
| Presses Speak / Listen | Uses the local Windows speech engines |
| Closes the window | Dispatch is entirely unaffected |

## 3. What is actually connected on this machine

Measured during the build, not assumed:

| Capability | State | What that means |
| --- | --- | --- |
| **Library** | **LIVE** | Reads the real Company Library plus a labelled sample corpus |
| **Outlook** | **LIVE, read-only** | Real calendar, mail, and contacts via Windows COM |
| **Voice** | **LIVE (output)** | Windows System.Speech; two voices; speaks out loud |
| **Voice input** | Engine bound, unproven | A recognizer and microphone exist; recognising real speech needs a person |
| **Research** | **SAMPLE DATA** | No research provider is configured. Fixtures only, labelled everywhere |
| **Dispatch** | **NOT CONNECTED** | No approved interface exists. Port defined, nothing connected |

The window shows this state permanently, and the words are the ones above.
Nothing marked SAMPLE is ever presented as live.

## 4. What it will not do

- It will not approve, decide, or authorize anything.
- It will not write to Dispatch, or to any operational system.
- It will not act because Mike did not answer. Silence is never consent.
- It will not present sample data as live, or stale data as current.
- It will not claim an action it did not complete.
- It will not invent an answer. With no reasoning provider bound, it says so.

## 5. The reasoning gap, stated plainly

**No reasoning provider is connected.** This program cannot compose an original
answer to an open question.

What it can do is find, read, report, and remember - with the source attached.
Asked something it has no source for, it says there is no source rather than
producing something that reads like an answer.

That is a real limitation and it is the honest one. A helper that invents a
plausible rate is worse than one that says it does not know.

## 6. Who operates it

Mike Zachary, from the Windows desktop. No command line, no record IDs, no
JSON, no API syntax, no internal field names. Ordinary sentences.

Internal IDs exist and are visible in the history line, but nothing requires
typing one.

## 7. Runtime

Python 3.10 or newer via the Windows `py` / `pyw` launcher. Verified here:
Python 3.14.5, tkinter 8.6. Standard library only - no third-party package is
installed or required.

## 8. Relationship to the six workstreams

The six components in `..\ASST\1..6` were built in isolation and are packaged
into this program **unchanged**. Their bounded responsibilities are preserved:

| Folder | Component | Responsibility here |
| --- | --- | --- |
| `ui/` | Assistant UI | window rendering only |
| `memory/` | Assistant Memory | interaction records and retention states |
| `library/` | Assistant Library | approved reference material, read-only |
| `outlook/` | Assistant Outlook | read-only awareness models |
| `research/` | Assistant Research | findings, uncertainty, recommendations |
| `voice/` | Assistant Voice | speech transport and driver-mode shaping |

They do not import each other. Adapters and contracts carry everything between
them.

## 9. Removability

Deleting this folder removes JOE. Dispatch is unaffected, because
nothing in Dispatch references it, nothing in it writes to Dispatch, and the
Dispatch port has never been connected.

See `JOE_BUILD_REPORT_v1.md` for the independence result.
