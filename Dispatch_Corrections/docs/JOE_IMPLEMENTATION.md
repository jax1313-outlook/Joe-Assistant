# Joe — reasoning and voice, and the line neither of them crosses

**The cab is the constraint.** Every design decision below traces to one
sentence in `DRIVER_FIRST_DOCTRINE_v2` D2:

> *Can the driver obtain the needed information within seconds during real-world
> operations? If the answer is no, redesign the feature.*

The driver is moving, is tired, and has one hand. A voice assistant that gets
this wrong is worse than no voice assistant, because it takes attention it
promised to give back.

---

## What was already there

`Assistant_Plugin/` is 27,662 lines and none of it was rebuilt. The
`SpeechToTextEngine` / `TextToSpeechEngine` ports, the voice session with
barge-in, the `ReasoningProvider` port with `Answer`/provenance, the SAPI and
Whisper adapters, the memory and retention engines — all of it stands.

What was added is the layer between them: **what a conversation is**, and what
Joe is allowed to do with what he hears.

## `conversation/` — five modules

| Module | What it settles |
|---|---|
| `mission_record.py` | What Joe may read, and that reading changes nothing |
| `readback.py` | What he says out loud, and in what order |
| `orchestrator.py` | When a provider is called at all, and when the turn ends |
| `capture.py` | What happens to something the driver said |
| `session.py` | Turns, interruption, confirmation, audit |

## Retrieval is retrieval (D9)

`MissionRecordRetrieval` has **no write method to call by mistake**, holds no
database handle of its own — the reader is injected — and has **no cache**. A
cached answer to "where am I going" is the one kind of stale that sends somebody
to the wrong dock.

`MissionRecord.unknown` carries the fields that are **empty**. That field is the
one that matters: an assistant answering only from what it has will confidently
describe a load with no delivery appointment as though the appointment merely
went unmentioned.

`context_for_reasoning()` hands a provider **six named fields**. A provider given
the whole record answers from anything in it, and one of the fields is a driver's
phone number.

## The read-back contract

| Rule | Because |
|---|---|
| Most important fact **first** | A sentence heard at speed is often only half heard. *"Delivery is tomorrow at 14:00 in Dallas"* survives being cut off; *"For load LD-4471, which is currently in transit, the delivery is…"* does not. |
| **No list** | A list is a thing you scan, and scanning is a thing you do with your eyes on a screen. `everything` states the **count first** — *"4 things."* — so the driver knows how long this will be before it starts. |
| A missing fact is **said** | Silence about the delivery time is indistinguishable from there being no appointment, and a driver who assumes the wrong one loses a load. |
| Times are **relative and dayed** | *"tomorrow at 14:00"*. A bare `14:00` sounds precise and does not say which day. An ISO string is not an answer a moving driver can use. |

Joe renders times himself when Dispatch is not installed beside him — a plug-in
must run standalone (`CLAUDE.md` §5.4), and falling back to reading out the
storage format would fail D2 outright.

## Bounded reasoning — four bounds and a fifth property

**Scope.** A question matching the Mission Record is answered **from the record**
and no provider is called. Faster, free, exact, and it cannot hallucinate a date
the database knows exactly. Twenty-three patterns cover what a driver actually
asks.

> A regex bug here was found by the tests and is worth recording: `deliver\b`
> does not match before the "y" in *"delivery"*, so `"when's delivery"` fell
> through to the provider — which answered correctly, slowly, and for money, from
> a stored fact. It failed silently, in the direction that looks like it works.

**Turns.** One provider call per driver utterance. No chains, no self-directed
follow-ups. A driver who asks and hears nothing for six seconds has already
looked at the screen.

**Time.** A deadline, after which the turn ends with what it has. An answer that
arrives late is **said to be late** — *"That took too long, so I'll leave it"* —
rather than delivered into a gap the driver already filled.

**Authority.** Nothing a provider returns becomes a change.

**And the property usually missing: it may return nothing.** `UNCONFIGURED` —
*"I can tell you what's on the load, but I'm not set up to answer that one"* — is
a real answer a driver can act on, where a confident-sounding guess is not.

## Capture — speech never becomes a write

`CLAUDE.md` §5.4: **no direct Dispatch write authority may be granted to
Assistant.** This is the shape of that rule.

Joe hears a sentence and produces a **proposal**: what he thinks was meant, how
sure he is, and the exact words that would confirm it. Dispatch applies it, or
does not.

The reason is not governance theatre. A cab at 70 MPH is the worst listening
environment this software will ever run in, and a speech-to-write path fails
silently: the driver says "picked up", the recogniser hears "pick up", a load
advances a state nobody chose. **This repository has already shipped that
failure** — `driver_step_milestone` once swallowed a refused transition inside
`except Exception: pass`, so a driver tapped Picked Up at a dock, nothing was
recorded, and the screen said it worked.

| Guard | Behaviour |
|---|---|
| Below the confidence floor (0.55) | **Nothing.** A wrong proposal costs a confirmation the driver has to listen to and refuse while driving — worse than not offering. |
| Below 0.85 | The whole sentence is repeated back. A driver confirming something he half heard is how a misheard sentence becomes a record. |
| Trouble vs. milestone | A delay is not a state change. Trouble becomes an **exception** proposal carrying the driver's own words, unedited — a paraphrase loses the detail that made it worth reporting. |
| Conversation | *"Nice weather out here"* proposes nothing. The first version matched a bare mention of weather and opened an exception, which is worse than missing one. |
| Confirmation | Only an unambiguous yes. *"Uh"* is not consent. |

## The session

**Interruption is normal, not an error.** A driver who cuts Joe off has decided
the answer is not what he needed. The turn is recorded as `INTERRUPTED`, not as
delivered — a record saying Joe told the driver something he did not hear is
worse than no record.

**A session forgets when it ends.** No cross-session memory. Dispatch is the
system of record and a second memory in the assistant is a second truth (D4).
What persists is the audit — what was asked, what was answered, what was proposed
— **not a model of the driver**.

**Every turn is recorded before it is spoken**, so a turn that is interrupted,
times out or crashes still leaves a trace.

## Voice providers

`voice/providers.py` answers the question an operator always has: *is it actually
listening?*

| Provider | STT | TTS | Needs |
|---|---|---|---|
| `azure_speech` | ✓ | ✓ | key + region — **status only; adapters not written** |
| `whisper_local` | ✓ | — | the model files |
| `windows_sapi` | — | ✓ | Windows |
| `text` | ✓ | ✓ | nothing |

**Nothing is `LIVE` until it is exercised.** A key in the environment makes a
provider `CONFIGURED`. `LIVE` requires a round trip that actually happened, and
this module has never made one.

**There is always a working pair.** The text engines are last and always
available, reporting `SIMULATED`: text in, text out — nothing was heard and
nothing was said aloud.

## What Joe still cannot do

- Hear anything on this machine. The selected engines are the text substitutes.
- Reach Azure Speech. Status reporting exists; the adapters do not.
- Write to Dispatch. By design, and there is no field through which he could.
- Remember you between sessions. By design.
