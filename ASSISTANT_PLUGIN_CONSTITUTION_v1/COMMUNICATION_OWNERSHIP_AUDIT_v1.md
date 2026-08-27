# Communication workflow ownership — audit and implementation plan

**Requested by:** Mike Zachary, 27 August 2026
**Subject:** JOE / Publisher / COMI / Email Helper ownership boundaries
**Status:** **AUDIT AND PLAN ONLY. NOTHING BUILT.**

---

## 0. The error being corrected, stated plainly

My previous audit reported that packet assembly, attachment handling and draft
persistence "do not exist" and listed them as work to do — under a heading that
implied JOE would do it. That was wrong twice over:

1. **Ownership.** Those are Publisher's and Email Helper's jobs. Their absence
   from JOE is correct, not a gap.
2. **Architecture.** Building them inside JOE would have created exactly the
   parallel architecture the knowledge doctrine §44 forbids — a second document
   production engine, a second routing authority, a second record holder.

The mission correction is right and this document proceeds from it.

---

## 1. The locked model

| owner | owns |
| ----- | ---- |
| **JOE** | conversation |
| **Publisher** | artifact and packet production |
| **COMI** | communication workflow, routing, pending-approval state, transmission records |
| **Email Helper** | Outlook mechanics, under COMI |
| **Outlook** | mailbox operations and delivery |
| **Dispatch** | the durable operational record |
| **Mike Zachary** | final authority |

JOE must not become a packet builder, a document production engine, a
recipient-routing authority, an Outlook adapter, or a permanent communication
record holder.

---

## 2. Audit — `app/transmission.py`

Written 27 August 2026, before this correction. 355 tests pass against it and
its inertness is proven four ways. The question is not whether it works; it is
whether each piece is standing in the right house.

| element | verdict | why |
| ------- | ------- | --- |
| `BindingFact` + `origin` | **REUSE in JOE** | Condition 2.3.3 is about what Mike *said*. Mike says it to JOE. The rule belongs where the speech is |
| `stage()` — fact validation | **REUSE in JOE** | rejecting a JOE-originated value before it can be read aloud |
| `stage()` — recipients, subject, body, attachments | **MOVE to COMI** | this makes JOE the envelope builder and recipient validator. Recipient routing is COMI's, explicitly |
| `read_back()` | **REUSE in JOE** | this is conversation, spoken to Mike. JOE's core job |
| `approve()` — 2.3.1 per-message binding | **REUSE in JOE** | the approval *event* originates in conversation |
| `approve()` — 2.3.2 read-back currency | **REUSE in JOE** | JOE knows what it read back and when |
| `approve()` — 2.3.6 confidence floor | **REUSE in JOE** | hearing is JOE's; only JOE knows how well it heard |
| `is_approval()` / `is_withdrawal()` phrase matching | **REUSE in JOE** | utterance interpretation is conversation |
| `withdraw()` | **SPLIT** | JOE emits the withdrawal *utterance*; **COMI** holds the authoritative pending state that gets withdrawn |
| `arming_state()` — transport, guard, config blockers | **MOVE to COMI / Email Helper** | whether transmission is possible is not JOE's to know or report as fact |
| `arming_state()` — condition 6.1 hearing proof | **REUSE in JOE** | hearing is measured on JOE's machine, by JOE |
| `transmit()` | **PREMATURE — stays inert, then deletes** | JOE must not be the Outlook adapter. Email Helper submits, under COMI |
| `provisional_record()` | **MOVE to COMI** | COMI owns transmission records. JOE keeps a *temporary review copy* that expires (workflow step 12) — not a record |
| `State` machine | **SPLIT** | JOE tracks its review copy; COMI owns the PENDING HUMAN APPROVAL envelope state |

**Net:** roughly the conversational half is correctly placed and directly
reusable. The envelope half was JOE reaching into COMI's house, and
`transmit()` was JOE reaching into Email Helper's.

### `app/mailbox_authority.py`

| element | verdict | why |
| ------- | ------- | --- |
| `APPROVED_SENDERS` (the Amendment 1 list) | **MOVE enforcement to COMI / Email Helper** | enforcement belongs where transmission happens. JOE keeps a **read-only view** so it can say "from ops@l1truck.com" in a read-back |
| `EXPLICITLY_NOT_APPROVED` + `refusal_for()` | **REUSE in JOE** | this is explaining a boundary in plain language — conversation |
| "not read from configuration" reasoning | **REUSE, and carry it to COMI** | the argument holds wherever the list lives: a settings edit must not widen transmission authority |

**Important:** `stage()` currently *refuses* an unapproved mailbox. That refusal
is correct but it is being made in the wrong house. It stays as a JOE-side
sanity check, and COMI must make the same check independently — JOE's check is
a courtesy, COMI's is the control.

---

## 3. Existing seams to reuse — before any code is written

This is the part the mission asked for first, and it is the most useful finding
in this document: **the JOE → COMI handoff seam already exists.**

| seam | where | what it gives |
| ---- | ----- | ------------- |
| **`DispatchPort.submit(kind, detail)`** | `adapters/dispatch_port.py:145` | the outbound proposal channel. Validates against a fixed `SUBMITTABLE` tuple, returns an `ActionRequest`, and **nothing drains the queue** |
| **`SUBMITTABLE`** | `adapters/dispatch_port.py:46` | `finding, recommendation, draft, explanation, question, action_request, proposed_change`. An approval event needs **one new kind**, not a new channel |
| **`ActionRequest`** | `contracts/__init__.py:420` | already carries `kind, detail, requested_at, submitted, accepted=False, performed=False, auto_execute=False, decision_required_from="Mike Zachary"`. This *is* the approval-handoff contract |
| **`DispatchPort` has no write path** | `adapters/dispatch_port.py`, asserted by tests | no `write/update/create/delete/accept_load/book/commit`. Their absence is test-enforced |
| **`CapabilityStatus`** | `contracts/__init__.py:375` | `LIVE / READY / UNKNOWN`, never collapsing UNKNOWN into absent. The integration map calls this "the strongest reusable asset". Reuse for COMI and Email Helper status |
| **`Provenance` + `SourceMode`** | `contracts/__init__.py:214` | every artifact JOE displays can be labelled with where it came from — including "Publisher review copy" |
| **`RetentionEngine`** | `assistant_memory/retention.py`, wired at `app/service.py:98` | 3-hour expiry. **This is workflow step 12** — JOE's review copy expires like any Level 1 record. Nothing new needed |
| **`Logbook`** | `app/logbook.py` (46 loc, **0 tests**) | append-only local events. Usable for JOE-side approval events; needs tests before it is trusted |
| **`_handle_draft`** | `app/reasoning_capabilities.py` | already mapped to "Publisher requests" in `docs/DISPATCH_AGENT_INTEGRATION_MAP.md:61`. It composes and marks DRAFT ONLY / NOT SENT — the right shape for *requesting* production, not performing it |
| **Amendment 1 six conditions** | `AMENDMENT_1_TRANSMISSION_PROPOSED.md` | in force, unaltered |
| **`FORBIDDEN_COM_CALLS` + `_assert_read_only()`** | `adapters/outlook_com.py:46,432` | the guard Email Helper will need to open *precisely, per call* — not switch off |
| **Publisher** | Dispatch repo, `portal/models/publisher.py` | per `docs/DISPATCH_DISCOVERY_VALUE_REPORT.md:130` — "Joe drafts, Publisher produces" |

**Conclusion: no new architecture is required for the JOE side.** One new
`SUBMITTABLE` kind and a JOE-side review-copy holder that expires. Everything
else is reuse.

---

## 4. Implementation plan

Mission-sized. Ordered so that nothing depends on something unbuilt, and so
each stage is provable on its own.

### A. Richer Email Helper reads

**Owner:** Email Helper. **JOE:** consumer only.
**Governance:** none needed — read-only.

Today a mail read returns `subject, sender NAME, received, unread,
has_attachments` (`adapters/outlook_com.py:228`). Missing: **body, sender
address, message/thread identity, attachment names**.

- A1. Extend the read projection with `EntryID`, `ConversationID`,
  `SenderEmailAddress`, `Body`, and attachment *names* (names only — no file
  extraction yet).
- A2. Keep every addition inside the existing `_assert_read_only()` guard. All
  are property reads; **no forbidden call is needed**, which is the proof this
  stage adds no authority.
- A3. Redaction pass before anything reaches a reasoning provider — a body may
  contain rates, contacts and terms. Reuse the truth-class COMPANY framing.
- A4. Proof: read a real message and show body + address + identity, with the
  guard still refusing `.Send(`.

**Risk:** message bodies are the largest privacy surface JOE has touched.
Doctrine §28 governs what may leave the tenant in a query.

### B. Publisher dual-copy production

**Owner:** Publisher. **JOE:** requests, then displays.
**Governance:** none new — JOE already may draft and request.

- B1. Define the **production request** JOE emits: structured supplied facts,
  each carrying `origin` (reuse `BindingFact` — 2.3.3 enforced at the source).
- B2. Publisher emits **two matched outputs in parallel**: a JOE review copy
  and a COMI operational copy marked `PENDING HUMAN APPROVAL`, sharing an
  `artifact_id`.
- B3. **JOE never relays the operational copy.** JOE receives only its review
  copy. This is the structural guarantee that JOE cannot become the production
  path.
- B4. JOE's review copy is held under `RetentionEngine` and expires (step 12).
- B5. Publisher writes its own append-only production audit entry. **Not JOE's
  record.**
- B6. Proof: kill the JOE review copy and show the COMI copy unaffected —
  demonstrating they are genuinely parallel, not sequential through JOE.

### C. COMI pending-approval envelopes

**Owner:** COMI.
**Governance:** the six conditions attach here.

- C1. COMI holds the envelope: recipients, subject, body, attachments,
  `artifact_id`, state `PENDING HUMAN APPROVAL`.
- C2. COMI independently validates the sending mailbox against Amendment 1.
  JOE's check is a courtesy; **this one is the control**.
- C3. COMI owns the transmission record — 2.3.5. JOE holds none.
- C4. Until Dispatch is bound, COMI's record is marked provisional and handed
  over when Dispatch arrives *(open ruling 5 from the previous audit)*.
- C5. Envelopes expire unapproved rather than waiting indefinitely.

### D. JOE review / read-back / approval handoff

**Owner:** JOE. **This is the only stage where JOE holds authority-adjacent
logic, and it is the stage most of `app/transmission.py` already implements.**

- D1. Keep `read_back()`, `approve()`, `is_approval()`, the confidence floor,
  read-back staleness, and the JOE-originated-fact refusal.
- D2. Drop envelope construction from JOE. JOE reads back **COMI's** envelope
  summary; it does not build one.
- D3. On approval, JOE emits **only** the five fields the mission names:
  approval event, `artifact_id`, approving human, approval utterance,
  timestamp. Nothing else — not the body, not the recipients.
- D4. Emit it through `DispatchPort.submit()` with **one new `SUBMITTABLE`
  kind**, `approval_event`. Reuses the existing bounded channel and inherits
  `accepted=False, performed=False, auto_execute=False`.
- D5. Withdrawal emits a matching `withdrawal_event`; COMI acts on it.
- D6. Condition 6.1 stays JOE-side: no approval event is emitted at all until
  hearing is proven on this machine.
- D7. Proof: plant a fault at each condition and show the approval event is not
  emitted — the same method used for the truth classes.

### E. Reversible mail movement

**Owner:** Email Helper under COMI. **Ruling received:** move to Junk Email or
Deleted Items is allowed and reversible; permanent purge and automatic emptying
are not authorized.

- E1. Open `_assert_read_only()` for `.Move(` **only**, and only to Junk Email
  or Deleted Items, and only under Email Helper.
- E2. `.Delete(` stays forbidden. `EmptyFolder`, `DeleteAll` and any purge stay
  forbidden and must be named in the guard so their absence is asserted.
- E3. Every move is logged with the origin folder so it can be undone.
- E4. Proof: move a message, restore it from the log, and show `.Delete(` still
  refused.

---

## 5. What is not built, and stays that way

- **Packet production inside JOE** — never. Publisher's.
- **Sending** — not enabled. `transmit()` stays inert until COMI and Email
  Helper exist, then it is *deleted from JOE*, not armed.
- **Permanent deletion** — not implemented, and I will not implement it.
- **A second record store** — JOE holds a review copy that expires. COMI and
  Dispatch hold history.

---

## 6. Recommended first step

**Stage A**, because it is the only stage that depends on nothing else, needs no
governance change, adds no authority, and unblocks B, C and E. It is also the
stage whose absence most limits JOE today: without a message body or a sender
address, JOE cannot usefully discuss the mail it can already read.

**Mike Zachary remains final authority.**
