# Worker contracts — Intelligence, Publisher, Joe (and Library)

**The mission said: implement bounded contracts and working connections among
the workers and Dispatch, and do not create a monolithic agent.**

The second half is the harder one, and it is not a style preference.
`Dispatch/CLAUDE.md` §5.4 requires Dispatch to start and run without any plug-in;
§5.1 gives lifecycle authority to the Spine alone. A single agent that could do
all of it would break both on its first useful day, because the cheapest way to
satisfy any request is always to reach into the next component's data.

So the boundary is a **message**, and there is a **mediator** that refuses the
shortcuts.

---

## The shape

```
                        ┌───────────────┐
      Dispatch ───────► │   WorkerBus   │ ──► INTELLIGENCE   advises, decides nothing
                        │               │ ──► PUBLISHER      assembles, approves nothing
                        │  guards       │ ──► JOE            speaks, writes nothing
                        │  audit        │ ──► LIBRARY        holds approved assets
                        └───────────────┘
                              ▲    │
                              └────┘  declared dependencies only
                                      (PUBLISHER ──► LIBRARY)
```

`Workers/worker_bus/` · contracts, bus, audit · `workers/` · the four adapters.

## What the bus refuses, and why each rule exists

| Refusal | Why |
|---|---|
| `worker_to_worker_call` | The rule that keeps three workers from becoming one. A worker that needs another declares a **dependency**; the bus makes the hop, so the traffic is in one audit trail under the caller's correlation id instead of inside an import. |
| `undeclared_capability` | A worker answers only what it declared up front. |
| `human_authorization_required` | A capability marked `requires_human_authorization` gets a named human or nothing. |
| `reserved_identity_cannot_authorize` | `PUBLISHER`, `SYSTEM`, `AUTOMATION`, `INTELLIGENCE`, `LIBRARY`, `JOE`, `CRON`, `BACKGROUND_JOB`, `DISPATCH_DAEMON` are the program, not a person. |
| `authorization_reference_required` | A name with nothing referenced is an **assertion** that somebody approved, not a **record** that they did. `CLAUDE.md` §4. |
| `dependency_cycle` | Two workers that need each other are one worker with the seam drawn in the wrong place. |
| `dependency_depth_exceeded` | A long chain means a worker is orchestrating, which is Dispatch's job. |

A worker that raises is reported `UNAVAILABLE` and does not take the caller down:
*degradation is permitted, incapacity is not.*

## What no response may carry

`WorkerResponse.__post_init__` **raises** on `approved`, `approved_by`,
`decision` or `authorized_by` in the artifacts. Workers advise. A recommendation
that reads like a decision is a decision made without authority.

Every `status` and every finding `confidence` must be one of the eight truth
words, checked at construction.

---

## INTELLIGENCE

| Capability | Produces | Never |
|---|---|---|
| `assess_load` | findings, ordered | decides whether to take the load |
| `assess_broker` | findings | a trust score |
| `summarise_risk` | the same findings, ordered | anything added or inferred |

The boundary here is epistemological rather than technical, and the constitutions
say it in their own words: research is not truth, and a recommendation is not an
approval. The highest confidence an unverified observation reaches is
`UNVERIFIED` — a real answer, not a failure.

**With no reader it returns nothing and says `UNCONFIGURED`.** It does not reason
from an empty set.

A rate below the lane's history is a finding whose own detail says *"History is
not a rate floor and this is not a refusal."* A broker with no record is
`ABSENT` — first time doing business with them — not risky.

## PUBLISHER

| Capability | Produces | Authority |
|---|---|---|
| `check_readiness` | findings naming what is missing | none needed |
| `assemble_completion_package` | a **draft** for human review | `requires_human_authorization` |

**Invents nothing.** Everything comes from a Dispatch record or a Library asset.
A missing POD produces a notice, not a plausible sentence in its place — and the
response says so: *"A package is built from facts that exist; the missing ones
are named above rather than written in."*

**Approves nothing.** The result carries `review_required: True` and the detail
says it is a draft until a person reviews and submits it.

**The Library hop goes through the bus.** Publisher does not import Library; the
audit shows `PUBLISHER -> LIBRARY` under the caller's own correlation id, which
is what makes "which worker read what" answerable.

## JOE

| Capability | Produces | Never |
|---|---|---|
| `read_back_load` | one spoken sentence | a list to scan |
| `answer_question` | an answer with provenance | an answer to something not on file |
| `propose_capture` | a proposal + the words to confirm it | a write |

`CLAUDE.md` §5.4: **no direct Dispatch write authority may be granted to
Assistant.** The artifacts carry `applies_itself: False` and the proposal carries
`applied: False` — present so anything consuming one has to look, rather than
there being no statement either way.

Read-back is D2 in code: most important fact first, times as *"tomorrow at
14:00"*, and a missing fact **said** rather than skipped — silence about the
delivery time is indistinguishable from there being no appointment.

## LIBRARY

| Capability | Produces |
|---|---|
| `fetch_asset` | the approved asset, or `ABSENT` |
| `list_assets` | asset references |

An asset is either approved and in the Library, or it is not in the Library.
Nothing here promotes a draft.

---

## The audit

Every exchange is recorded **before the answer is used**, including refusals — a
refusal nobody can see is indistinguishable from a question nobody asked.

Payloads are recorded by **shape**: `{driver_phone, load_id}`, never `555-0100`.
An audit that copies the data is a second place the data has to be protected, and
it is usually the place nobody remembers to protect.

```
  2026-09-12T20:41:03Z     DISPATCH -> PUBLISHER      assemble_completion_package  REFUSED
                 rule: authorization_reference_required -- Mike is named as the
                 authoriser but nothing is referenced.
```

## Connecting it to Dispatch

The workers take an injected **reader** — a read-only view with no write methods
on it at all. That is what makes "a worker cannot write to Dispatch" a property
of the code rather than a promise in a document.

```python
bus = WorkerBus(audit=AuditLog(path=Path("Artifacts/worker-audit.jsonl")))
bus.register(IntelligenceWorker(reader=dispatch_reader))
bus.register(PublisherWorker(reader=dispatch_reader))
bus.register(JoeWorker(reader=dispatch_reader, reasoner=orchestrator))
bus.register(LibraryWorker(assets=library_assets))

answer = bus.ask("INTELLIGENCE", WorkerRequest(
    capability="assess_load", payload={"load_id": load_id}))
```

The bus is **in-process**. That is the right shape for a single-operator laptop
and it is not a distributed system: no queue, no retry across a restart, no way
for a worker to run elsewhere. Making it one is a different design, and nothing
here assumes it.
