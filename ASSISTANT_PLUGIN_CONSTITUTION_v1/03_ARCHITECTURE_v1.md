# ASSISTANT PLUGIN CONSTITUTION v1
## Document 3 of 5 — Architecture

**Subject:** The shape all Assistant work must take
**Version:** 1.0
**Final authority:** Mike Zachary
**Status:** Doctrine. Architectural principle only — no interface specification,
no code, no integration.

---

## 1. The shape

```
                    +---------------------------------+
                    |          MIKE ZACHARY           |
                    |        FINAL AUTHORITY          |
                    +----+-----------------------+----+
                         |                       |
             decides on  |                       |  decides on
             operations  |                       |  advice
                         v                       v
      +-------------------------------+   +---------------------------+
      |          DISPATCH             |   |      ASSISTANT PLUGIN     |
      |                               |   |                           |
      |  General Contractor           |   |  Specialized staff        |
      |  System of Record             |   |  function                 |
      |  Operational Authority        |   |                           |
      |                               |   |  research   retrieve      |
      |  COMPLETE AND ENCAPSULATED    |   |  summarize  explain       |
      |                               |   |  draft      recommend     |
      |  Knows nothing about the      |   |  monitor    remember      |
      |  Assistant. Works without it. |   |                           |
      +---------------+---------------+   +-------------+-------------+
                      |                                 |
                      |   published, versioned          |
                      +-------  CONTROLLED  ------------+
                              INTERFACE
                      reads: one way, out of Dispatch
                      writes: proposals only, Dispatch decides
```

Two things to notice about that diagram:

**The Assistant does not sit between Mike and Dispatch.** It sits beside
Dispatch. Mike deals with Dispatch directly, always. The Assistant is reachable
from Mike, not interposed in front of anything.

**The arrow from Dispatch to the Assistant does not exist.** Dispatch has no
line pointing at the plugin, because Dispatch does not know the plugin is there.

## 2. Encapsulation

**2.1 Dispatch is complete and encapsulated.**

Dispatch is a finished system with a boundary. What is inside is Dispatch's own
business. The Assistant does not reach inside it, reason about its internals, or
depend on how it happens to work today.

**2.2 The dependency runs one way, and only one way.**

```
    Assistant  ------depends on------>  Dispatch
    Assistant  <-----does NOT----------  Dispatch
```

- The Assistant may depend on Dispatch's **published interface**.
- Dispatch may not depend on the Assistant in any way: no import, no call, no
  configuration entry, no assumption of presence, no feature that degrades when
  the plugin is absent.
- **If Dispatch source ever references the Assistant, encapsulation is broken**
  and the removability test has already failed.

**2.3 Dispatch is never held back by plugin compatibility.**

Dispatch changes when Dispatch needs to change. It does not wait for the plugin,
does not preserve an interface for the plugin's convenience, and does not carry
compatibility shims on the plugin's behalf.

**The plugin bears the entire cost of adaptation.** If a Dispatch change breaks
the Assistant, the Assistant is broken and the Assistant is fixed. That
asymmetry is deliberate and permanent: it is what keeps the General Contractor
free to build.

**2.4 The Assistant is never on a critical path.**

No Dispatch operation may wait on the Assistant, block on it, time out on it, or
require it to be reachable. If the plugin is slow, absent, or wrong, Dispatch
proceeds unaffected because it was never asking.

## 3. Controlled interfaces

"Plugin communications must occur through controlled interfaces." What
*controlled* has to mean:

### 3.1 Named
Every access path has a name. Anonymous access — reading a file because it
happens to be readable, querying a table because the credentials allow it — is
not an interface. It is a leak.

### 3.2 Published
The interface is documented before it is used. An access path discovered by
reading Dispatch's source is not published, and using it is a breach.

### 3.3 Versioned
Consumers state which version they were built against. Change is visible rather
than silent.

### 3.4 Enumerated
The interface is a **closed list**. What is not on the list is not available.
There is no "and anything else it can reach". Ambient access is the opposite of
a controlled interface.

### 3.5 The only contact surface
No shared database. No shared file system. No shared memory. No direct table
access. No back doors, no side channels, no "just this once" paths.
**If it is not the interface, it is not permitted.**

### 3.6 Reads and write-requests are different things

This is the structural distinction that carries most of the Constitution:

| | **Read path** | **Write-request path** |
| --- | --- | --- |
| Direction | out of Dispatch | a proposal toward Dispatch |
| What the Assistant gets | a copy | an outcome it does not control |
| Who decides | nobody — it is a view | **Dispatch, or Mike** |
| Assistant's power | none over the data | none over the outcome |

**The Assistant never writes to Dispatch.** It **submits a request** that
Dispatch — or Mike through Dispatch — accepts or rejects.

The Assistant does not know whether a request will be accepted, cannot make it
be accepted, cannot retry it into being accepted, and cannot treat submission as
success. A submitted request that has not come back confirmed is not a completed
action, and saying otherwise breaches Article VIII.

### 3.7 Dispatch does not trust the plugin

Dispatch validates everything arriving at its boundary, exactly as it would
validate any external input. It grants the plugin no standing, no elevated
credentials, and no assumption of good behavior.

This is not suspicion of the Assistant. It is what makes the boundary a boundary:
a validated edge holds whether the thing on the other side is correct, broken, or
absent.

### 3.8 The interface belongs to Dispatch

The controlled interface is **defined, owned, versioned, and published by
Dispatch**. It is not negotiated with the plugin and not designed to suit it.

**A plugin does not define the terms of its own access.** If the Assistant could
specify the interface it wanted, it would hold authority over Dispatch's
boundary — and the plugin would be shaping the General Contractor.

Publishing an interface is not the same as knowing about a consumer. Dispatch
publishes a surface; who reads it is not Dispatch's concern. Encapsulation holds.

## 4. Data doctrine

### 4.1 Three classes, always distinguishable

| Class | Owner | Authoritative? | Example |
| --- | --- | --- | --- |
| **Operational truth** | Dispatch | Yes | a load's rate, a mission's status |
| **Copy of operational truth** | Dispatch (held by Assistant) | **No** | a cached view of that load |
| **Derived material** | Assistant | No — and never becomes truth | research findings, a draft, a summary |

**4.2** These three must never blur. Any Assistant output that mixes them must
label which is which.

### 4.3 Provenance and as-of time are mandatory

Every Assistant statement about an operational fact carries:

- **where it came from**
- **as of when**

A figure with neither is prohibited output. A stale copy presented as current is
an alteration of operational truth (Article 3.3), and it is the most likely way
the Assistant causes real harm: not by being wrong, but by being right an hour
ago.

### 4.4 Conflict resolution is not a process

Where the Assistant's copy disagrees with Dispatch, **Dispatch is correct**.
Immediately. Automatically. There is no reconciliation step, no merge, no
adjudication, and nothing for anyone to weigh.

The Assistant's copy is simply wrong, and the correct response is to discard it
and re-read.

### 4.5 Assistant memory is working memory

The Assistant remembers so a person does not have to hold context in their head.
That is a permitted function and a valuable one.

It is **not** a record store. Assistant memory:

- holds context, not operational truth
- is not where anyone looks to settle a question
- may expire without operational consequence
- may be deleted entirely without Dispatch noticing

**If deleting Assistant memory would lose something operationally important,
that something was in the wrong place.**

## 5. Component shape

**5.1** Assistant work is built as **bounded components**, each independently
reviewable.

**5.2** A component:

- states its own purpose, boundaries, and prohibitions
- can be understood without reading another component
- can be removed without breaking the others
- carries its own tests and its own honest account of what is not proven

**5.3** Components communicate through declared internal contracts, not by
reaching into each other. The discipline that applies between the Assistant and
Dispatch applies between Assistant components, at lower stakes.

**5.4** **Prohibitions are enforced structurally wherever possible.**

A rule that depends on everyone remembering it will eventually be forgotten. A
rule with no code path to break cannot be.

Preferred, in order:

1. **Absence** — no method exists, so it cannot be called
2. **Refusal** — the attempt raises rather than being quietly reshaped
3. **Fixed output** — the honest value is emitted as a literal, not read from
   state someone could change
4. **Test** — the build fails if the rule is broken
5. **Documentation** — necessary, and the weakest of the five on its own

The Assistant components already built demonstrate all five. That standard is
the expectation, not the exception.

## 6. Degradation

**6.1** When Dispatch is unavailable, the Assistant reports that it cannot see
operational truth. It does **not** answer from a stale copy as though it were
current, and it does not guess.

**6.2** When the Assistant is unavailable, Dispatch is unaffected. Nothing
queues, nothing blocks, nothing fails.

**6.3** When the Assistant is wrong, operational truth is unaffected — because
the Assistant never wrote it. This is the practical payoff of Article 3.2 and
3.3: the blast radius of an Assistant error is bounded by design, not by care.

**6.4** When the Assistant is removed, Dispatch is complete. See Article V.

## 7. What this document deliberately does not specify

- **Any interface in technical detail.** Endpoints, schemas, transports, and
  authentication are Dispatch's to publish (3.8). This document states the
  properties such an interface must have.
- **Any implementation technology.** Nothing here depends on a language, a
  framework, a vendor, or a platform, and nothing in future Assistant work
  should make Dispatch depend on one.
- **Anything about Dispatch's internals.** Out of scope by encapsulation.
- **Any deployment, hosting, or operational arrangement.**

Repository shape is Document 5.
