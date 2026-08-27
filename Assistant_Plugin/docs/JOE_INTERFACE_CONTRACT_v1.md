# JOE - Interface Contract

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Status:** Contract only. **No Dispatch connection exists.** Nothing here is
connected, and nothing was contacted.

Governing doctrine:
`..\..\JOE_CONSTITUTION_v1\03_ARCHITECTURE_v1.md` sections 3 and 4

---

## 1. Who owns this contract

**Dispatch owns it.**

Per governing Architecture 3.8, the interface is defined, versioned, and
published by Dispatch. JOE consumes it and **may not expand its own
access**.

This document is therefore a **statement of what JOE would consume,
and the shape it expects** - not a specification JOE imposes. When
Dispatch publishes a real interface, Dispatch's definition governs and this
document is corrected to match.

## 2. Current state

```
  interface:            none
  endpoint:             (empty)
  enabled:              false
  connected:            false
  dispatch contacted:   false
  operational writes:   0
```

`adapters/dispatch_port.py` contains no endpoint, no credential, no database
handle, and no path into Dispatch. `DispatchPort.connected` is `False` by
construction, and every read returns unavailable rather than a guess.

## 3. Direction of dependency

```
    Assistant  ------ depends on ------>  Dispatch
    Assistant  <----- does NOT ---------  Dispatch
```

Dispatch contains no reference to JOE. JOE bears the entire
cost of adapting to any Dispatch change.

## 4. Read surface - a closed list

JOE may request these, and only these:

| Fact | Meaning |
| --- | --- |
| `loads` | current load information |
| `schedule` | authoritative schedule information |
| `capacity` | current capacity |
| `route` | current route information |
| `mission` | current mission information |
| `status` | current operational status |
| `reference_documents` | approved reference material |

**What is not on this list is not requestable.** `DispatchPort.read()` raises
`DispatchPortError` for anything else, with the message *"JOE may not
widen its own access"*.

Every read returns a copy with provenance and an as-of time. A copy is never
authoritative. Where a copy disagrees with Dispatch, **Dispatch is correct** -
immediately, with no reconciliation step.

## 5. Submission surface - proposals only

JOE may submit these toward Dispatch:

| Kind | Meaning |
| --- | --- |
| `finding` | something research established |
| `recommendation` | what appears worth doing |
| `draft` | prepared text for review |
| `explanation` | an explanation of something |
| `question` | a question needing an answer |
| `action_request` | a request for an authorized action |
| `proposed_change` | a proposed operational change |

**Submitting is not doing.** Every submission returns:

```json
{
  "accepted": false,
  "performed": false,
  "auto_execute": false,
  "decision_required_from": "Mike Zachary"
}
```

Those four are emitted as **literals**. No code path sets them true.

## 6. The write pattern

```
  1. Assistant proposes or requests
  2. Dispatch validates                 (treating the plugin as untrusted input)
  3. Mike or authorized Dispatch logic approves
  4. Dispatch performs the authoritative change
```

JOE participates in step 1 only.

**There is no step where JOE writes.** `DispatchPort` has no `write`,
`update`, `create`, `delete`, `accept_load`, `book`, `dispatch`, `commit`,
`pay`, `approve`, or `post` method. Their absence is asserted by test and by
local proof step 16.

## 7. Silence is never consent

Nothing JOE submits executes by default, on a timer, after a delay,
or through inaction.

**Nothing drains the submission queue.** That is not an oversight - there is no
authorized consumer, so a submitted request stays submitted and reports that it
is not accepted.

## 8. Trust

Dispatch must validate everything arriving at its boundary exactly as it would
validate any external input. The plugin gets no standing, no elevated
credentials, and no assumption of good behavior.

This is not suspicion of JOE. It is what makes the boundary hold when
the thing on the other side is broken or absent.

## 9. What connecting would require

Not authorized by this mission. Listed so the gap is exact:

1. **Dispatch publishes an interface** - named, versioned, documented, with an
   enumerated read surface. Dispatch's decision, on Dispatch's terms.
2. **A transport is chosen** by Dispatch (file drop, local service, whatever
   Dispatch decides).
3. **An adapter is written** in `adapters/` implementing that interface. No
   other file changes.
4. **`configuration/joe.config.json`** gets `dispatch.interface` and
   `dispatch.enabled: true`.
5. **The removability test is re-run** - remove the plugin, confirm Dispatch is
   whole.

Step 1 is the gate. JOE does not initiate it, does not specify it,
and waits.

## 10. Internal contracts

Between the application core and its own capabilities, the shapes in
`contracts/__init__.py` are the only things that cross a boundary:

| Contract | Carries |
| --- | --- |
| `AssistantRequest` | text, channel, driver mode |
| `AssistantResponse` | answer, written, spoken summary, provenance, uncertainty, recommendation, notices, authority flags |
| `Provenance` | source, mode (LIVE / SAMPLE / READY / UNAVAILABLE / NONE), as-of, detail |
| `CapabilityStatus` | name, available, mode, live_connection, blocker |
| `ActionRequest` | kind, detail, and the four false flags |

A capability never returns a raw internal object, and the core never reaches
into a capability's internals.
