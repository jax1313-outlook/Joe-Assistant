# JOE — Future Dispatch Interface Contracts

**Mission:** CLAUDE_CODE_MISSION_JOE_CARD_CENTRIC_DISPATCH, Step 1
**Status:** **CONTRACTS ONLY. NOTHING IMPLEMENTED. NOTHING CONNECTED.**
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

These are the shapes JOE would need in order to consume Dispatch card state
**when the authoritative repository is made available**. They are written from
JOE's side only, and describe what JOE would **ask for** and **promise not to
do**.

**They are proposals, not specifications.** Dispatch owns the card schema.
Where a real schema exists in the authoritative repository, the real one wins
and these are discarded — that is the intended outcome, not a fallback.

Nothing here was implemented. `adapters/dispatch_port.py` remains a port with
`connected = False`, and creating card structures inside JOE is prohibited.

---

## 1. The governing shape

```
MIKE
  ↕
JOE
  ↕
DISPATCH CARD AND WORKFLOW INTERFACES
```

JOE reads card state through a bounded service interface. JOE does not read
Dispatch files, does not query a Dispatch database, and does not hold a copy of
card state that could drift from the original.

**The one rule under all of these:** JOE never becomes a second source of
operational truth. If JOE and Dispatch disagree, Dispatch is right and JOE is
stale, and JOE must be able to say which.

---

## 2. Contract A — Card read

The minimum useful interface, and the only one Step 2 should need.

**JOE asks for:**

| Field | Why JOE needs it |
| --- | --- |
| card type | to know what it is looking at |
| card identifier | to name it back to Mike unambiguously |
| human label | to speak it aloud — "XPO Load 123", not a UUID |
| current state | to answer "where does this stand" |
| last updated | to say how current the answer is |
| the fields Mike asks about | rate, detention, stops, appointment, equipment |
| a source stamp | so JOE can label provenance as `DISPATCH_FACT` |

**JOE promises:**

- read-only, always
- no caching beyond the life of one answer
- every answer names the card and the retrieval time
- if the read fails, JOE reports **unknown**, never "no cards"

**Provenance class:** `DISPATCH_FACT` — already defined in
`contracts/__init__.py`, produced by nothing today, and reserved so nothing
else can claim it.

---

## 3. Contract B — Card resolution

Before JOE can act on "XPO Load 123" it must resolve that phrase to exactly one
card.

**JOE asks for:** a resolver taking a human phrase and returning zero, one, or
many candidate cards with enough detail to disambiguate.

**JOE promises:**

- **zero matches** → say so; never invent a card
- **one match** → proceed, and read the identity back
- **many matches** → ask which, and never guess

Ambiguity is the case that matters. A voice command acting on the wrong load is
worse than a voice command that failed.

---

## 4. Contract C — Card mutation

**Not for Step 2.** Recorded because the negotiation workflow in the mission's
Section 8 depends on it.

**JOE asks for:** a validated mutation service that takes the card id, the
field, the **expected current value**, the new value, and an authority record —
and returns the resulting state or a refusal.

**JOE promises:**

- never write to storage directly
- always supply the expected current value, so Dispatch can reject a stale edit
- never retry a consequential change automatically
- report the actual outcome, never a predicted one

**The expected-value requirement is the important one.** If Mike says "change
the rate from $3.00 to $3.75" and the card already says $3.40, something has
changed underneath and the command must fail rather than overwrite.

---

## 5. Contract D — Card events

**JOE asks for:** a subscription or poll returning card state changes, so JOE
can announce an Alert Card without inventing one.

**JOE promises:**

- announce only what the card says
- never embellish beyond card data
- say "Intelligence created a high-priority Alert Card affecting the current
  mission", never "I think Intelligence may have found something"
- speak `ALERT` once, neutrally, then the short summary — no repetition, no
  urgency theatre

The alert voice doctrine is already specified in the governing mission's
Section 13 and is **not implemented**.

---

## 6. Contract E — Deterministic service invocation

**JOE asks for:** a way to trigger an approved deterministic service — Config
Review being the named example — and receive a structured result.

**JOE promises:**

- **JOE does not perform the calculation.** The deterministic engine does
- JOE reads the result, explains failures and warnings, and summarises verbally
- JOE never improvises a capacity, weight, or sequencing number
- JOE never commits a load

Config Review answers one question: **does this load actually work?** JOE's
entire role is to trigger it, read it, and explain it.

---

## 7. Contract F — Transaction record

**JOE asks for:** the ability to write a record of what it did, and to read
records back for reconciliation.

**JOE promises:**

- append only
- never make a governance decision from a log entry
- never assert a log entry exists without confirming it

The mission is explicit: *do not create a fictional log reference before
confirming the log exists.* JOE must never insist an uncreated file exists.

---

## 8. What JOE already has that these would reuse

Recorded so Step 2 favours reuse over creation, as the mission directs.

| Existing | Reusable for |
| --- | --- |
| `contracts::SourceClass.DISPATCH_FACT` | Contract A provenance — already defined and reserved |
| `contracts::SourceClass.ROUTE_RISK_EVENT` | Contract D — already defined and reserved |
| `contracts::Provenance` (per-entry) | keeping card facts distinct from Copilot reasoning |
| `governance::Governor` | refusing any response that claims authority JOE lacks |
| `adapters/dispatch_port.py` | the port itself — a contract with `connected = False` |
| `app/driver_voice.py` | speaking an alert; the loop already suppresses the microphone while talking |
| the retention engine | recording what Mike asked and what JOE answered |
| `ReasoningMode.ROUTE_EVENT_ANALYSIS` | already defined, produced by nothing |

**Six of the eight pieces Step 2 would need already exist as contracts.** What
is missing is the Dispatch side, and JOE must not build it.

---

## 9. What these contracts deliberately do not include

- **No card schema.** Dispatch owns it. Inventing one here would be the second
  source of truth the mission prohibits.
- **No card storage in JOE.** Not even a cache that outlives one answer.
- **No scoring logic.** JOE may not alter scoring rules.
- **No vehicle capacities.** The mission says the trailer is not finalised and
  must not be fabricated in code. Nothing in JOE names a pallet count.
- **No Manager.** These are contracts between JOE and Dispatch services, not an
  orchestration layer over them.

---

Mike Zachary remains final authority.
