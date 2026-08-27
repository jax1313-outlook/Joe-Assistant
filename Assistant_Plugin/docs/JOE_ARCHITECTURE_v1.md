# JOE - Architecture

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0

Governing architecture doctrine:
`..\..\JOE_CONSTITUTION_v1\03_ARCHITECTURE_v1.md` (v1.0)

---

## 1. Shape

```
                        +--------------------------------+
                        |   ui/window.py  (tkinter)      |  renders only
                        |   no business logic            |  worker thread for
                        +---------------+----------------+  slow work
                                        |
                                        v
                        +--------------------------------+
                        |   app/service.py               |  THE CORE
                        |   AssistantService             |  routes, dispatches,
                        |   ask / retention / status     |  records, governs
                        +--+----------+---------+--------+
                           |          |         |
              app/router.py|          |         | governance/  (the gate)
              language ->  |          |         | every response passes here
              capability   |          |         |
                           v          v         v
                 +---------------------------------------+
                 |            contracts/                 |  the only shapes
                 |  AssistantResponse, Provenance,       |  that cross a
                 |  CapabilityStatus, ActionRequest      |  boundary
                 +------------------+--------------------+
                                    |
                 +------------------+--------------------+
                 |            adapters/                  |  ALL provider code
                 |  outlook_com  voice_sapi  library_fs  |  lives here and
                 |  research_provider  dispatch_port     |  nowhere else
                 +------------------+--------------------+
                                    |
        +--------+--------+---------+--------+---------+---------+
        |        |        |                  |         |         |
     ui/     memory/  library/           outlook/  research/  voice/
   assistant_ui  assistant_memory  assistant_library  ...   (packaged
                                                             components,
                                                             unchanged)
                                    |
                                    v
                        +--------------------------------+
                        |         DISPATCH               |
                        |   NOT CONNECTED                |
                        |   port defined, never contacted|
                        +--------------------------------+
```

## 2. Layers, and what each may not do

| Layer | Owns | May not |
| --- | --- | --- |
| `ui/window.py` | drawing, events, threading | contain business logic, construct a component, decide anything |
| `app/service.py` | routing, dispatch, record lifecycle, status | know how a capability works internally |
| `app/router.py` | language to capability | perform work |
| `governance/` | constitutional review of every response | be bypassed |
| `contracts/` | the shapes that cross boundaries | contain logic |
| `adapters/` | provider-specific code | leak a provider name upward |
| packaged components | their own bounded responsibility | import one another |

A test asserts the UI constructs no component (`RetentionEngine(`, `Library(`,
`Governor(` etc. must not appear in `window.py`), and that no first-party module
outside `adapters/` contains `powershell`, `Outlook.Application`, `subprocess`,
or `win32com`.

## 3. Routing

Deterministic, ordered, first match wins. No model.

```
  1. RETENTION   save / keep / level 2 / level 3 / print / delete / level 1
                 recognized by memory/retention_language.py - reused verbatim
                 from Sandbox Engine v1, already covered by its own tests
  2. LIBRARY     explicit retrieval verbs: find, search for, look up, pull up,
                 where is, library
  3. RESEARCH    research, look into, dig into, compare ... options
  4. OPERATIONS  calendar, my schedule, my appointments, tomorrow/today,
                 mail/inbox/unread, who is, contact for, phone number
  5. LIBRARY     topical: packet, document, policy, procedure, template, doctrine
  6. EXPLAIN     explain, in plain language, what does X mean, how do I
  7. HELP        what can you do, help, commands
  8. ANSWER      nothing matched -> search Library, or say plainly it cannot answer
```

**Retention always wins.** "Save this and find the packet" is a retention
command, because the destructive-if-misread case is the one to get right.

**Explicit retrieval verbs outrank topical words.** "Look up the appointment
policy" is a Library request; "my appointments tomorrow" is calendar. This
distinction was added after the first build routed the former to the calendar.

## 4. The interaction path

```
  ask(text)
     |
     +-- route(text)                         which bounded capability
     +-- _dispatch_capability(...)           the capability does its work
     |      |
     |      +-- any exception -> isolated: an honest failure response,
     |                            the application stays open, other
     |                            capabilities keep working
     |
     +-- governor.enforce(response)          critical breach -> refusal
     +-- _shape_for_driver(response)         short spoken form, written kept
     |
     +-- RETENTION? -> act on the SELECTED record, create no new record,
     |                 do not move the selection
     |
     +-- otherwise  -> create a Level 1 record, select it
```

**Retention commands create no record of their own.** An early build did, which
meant "Save this. Print this." landed on two different records. Found by running
it; fixed; two tests now hold it.

## 5. Record lifecycle

Owned entirely by the packaged Memory component. This program adds no retention
logic of its own.

```
   new interaction
        |
        v
   TEMPORARY / LEVEL_1  (expires in 3 hours)
        |
        +-- "Save this"          -> SAVED       / LEVEL_2   expiry cleared
        +-- "Level 3 this"       -> FORMAL      / LEVEL_3   expiry cleared,
        |                                                   artifact requested
        +-- "Print this"         -> PRINT_READY / level UNCHANGED, expiry cleared
        +-- "Delete this"        -> DELETED     content purged
        +-- 3 hours, swept       -> EXPIRED     content purged, never promoted
```

**Print is a state, not a level** (doctrine C4). Held by three tests here and
by the Memory component's own suite.

**Expiration is sweep-on-access, not a timer.** `history()` sweeps before it
returns, so opening the window is enough. There is no background service. This
is stated in the UI documentation and in Known Limitations rather than dressed
up as continuous deletion.

## 6. Adapters

| Adapter | Provider | State | How it is constrained |
| --- | --- | --- | --- |
| `outlook_com` | Windows COM via PowerShell | **live, read-only** | scripts generated from a fixed template; scanned for 20 forbidden calls; refuses to run if one appears; lazy - never contacts Outlook on startup. Calendar is sorted by `[Start]`, recurrences expanded, restricted to a date window; the ordering actually achieved is reported, never assumed |
| `voice_sapi` | Windows System.Speech | **live output** | speaks only on explicit request; can render to WAV to prove binding without sound |
| `library_fs` | local filesystem | **live** | only configured paths; opens for reading; company material outranks sample at equal score |
| `research_provider` | none | **fixture** | `has_live_provider` is the single switch; a named-but-unimplemented provider fails loudly rather than silently stubbing |
| `dispatch_port` | none | **unconnected** | closed read list, closed submission list, no write method exists |

## 7. Provenance

Every operational statement carries where it came from and as of when.

```
  Outlook (read-only)  |  LIVE  |  as of 2026-08-25 12:05:14Z  |  Calendar, 601 items
  Library / Company Library  |  LIVE  |  as of ...  |  Constitutions/DISPATCH_CONSTITUTION_v3.md
  Research provider (fixture)  |  SAMPLE DATA  |  as of ...  |  brief: ...
```

A response mentioning an operational term with no provenance attached gets a
notice saying so. HELP text is exempt - naming a capability is not asserting a
fact.

## 8. Threading

Outlook reads take 10-25 seconds. The window would freeze without this.

```
  UI thread            worker thread              queue        UI thread
  _ask_text()  ---->   service.ask()   ---->   results  ---->  _drain() draws
  disable Ask                                                  re-enable Ask
```

`_drain()` polls every 120 ms on the main thread. No widget is touched from a
worker.

## 9. Storage

```
Assistant_Plugin\
  runtime_data\memory\active\    MEM-*.json    live records
  runtime_data\memory\expired\   MEM-*.json    tombstones, content purged
  runtime_data\memory\deleted\   MEM-*.json    tombstones, content purged
  logs\joe.log                           plain text event log
```

The log records event kinds, capability names, and record IDs. **It never
records the body of a document, an email, or a calendar entry** - the log is for
diagnosing JOE, not for accumulating a second copy of Mike's
information.

## 10. What was deliberately not built

- **A reasoning provider.** None is bound, and rather than stub one the program
  says it cannot answer. See Known Limitations.
- **A background expiration timer.** Would need a service or scheduled task;
  sweep-on-access is honest and stated.
- **A Dispatch connection.** No approved interface exists to connect to.
- **Any write path to anything.** By doctrine.
- **Summarize, draft, and train capabilities.** Permitted by doctrine, not built
  in v1, declared NOT IMPLEMENTED rather than half-present.
