# Amendment 1 revision — audit report

**Requested by:** Mike Zachary, 27 August 2026
**Subject:** Human-in-the-loop transmission
**Status:** **AUDIT ONLY. NOTHING IMPLEMENTED.** (mission item 5)

---

## 0. The premise is right, and the old framing was mine

The mission says transmission was treated as a binary — cannot send, or sends
autonomously. That framing was in my work, not in yours, and it was wrong.

The workflow you describe is neither. When you say *"broker approved $2.10
instead of $1.95, update the rate con, rebuild the packet, get it ready"* and
then *"looks good, send"*, **two human decisions have already been made**: the
rate, and the transmission. JOE originated neither. It assembled, it read back,
and it waited.

That is not autonomy. It is a clerk with a stamp it cannot use until told.

---

## 1. Current Amendment 1 design

Signed 27 August 2026. You ruled the same day that the signature grants the
authority while six conditions govern each transmission:

| | condition | how the revision relates |
| - | --------- | ------------------------ |
| 2.3.1 | explicit authorisation, per message | **same thing** — your "approval event" |
| 2.3.2 | read-back of the binding content before authorisation | **same thing** — your "readback summary" |
| 2.3.3 | nothing supplied that Mike did not state | **still needed** — JOE must not originate the $2.10 |
| 2.3.4 | a withdrawal window between authorisation and transmission | **the one real difference** — see §4.3 |
| 2.3.5 | Dispatch owns the transmission record | **same thing** — your "audit log", plus who owns it |
| 2.3.6 | an unheard command is not a command | **still needed** — see §4.4 |

**Finding: the revision is not in conflict with the six conditions.** Your
Operational Transmission tier *is* the six conditions, expressed operationally.
The revision's genuine addition is the **Administrative Authority** tier, which
does not exist in Amendment 1 at all and is where the real work lies.

---

## 2. Where transmission is blocked today

Four independent blocks. All four are ours, and none is accidental.

| # | block | where | reversible? |
| - | ----- | ----- | ----------- |
| 1 | **No send path exists.** No SMTP, no `MailItem` creation, no outbox, no transport of any kind | nowhere in the program | n/a — nothing to disable |
| 2 | **The read-only guard.** `_assert_read_only()` refuses to run any generated script containing a forbidden call | `adapters/outlook_com.py:432` | deliberate opening required |
| 3 | **`outlook.read_only: true`** | `configuration/joe.config.json` | a config flag |
| 4 | **`write_authority: "none"`** on both approved mailboxes | mailbox registry, measured today | per-mailbox |

The guard's forbidden list is the important one, because it blocks the
Administrative tier as well as the Operational one:

    .Send(  .Save(  .Delete(  .Move(  .Reply(  .ReplyAll(  .Forward(
    .Add(   .CreateItem(  .Respond(  .Accept(  .Decline(  .MarkAsTask(  .SaveAs(

Every capability in your Administrative Authority list is in that tuple:
creating a draft needs `.CreateItem(` and `.Save(`; replying needs `.Reply(`;
forwarding needs `.Forward(`; moving needs `.Move(`; deleting junk needs
`.Delete(`; attaching files needs `.Add(`.

**So the Administrative tier is blocked by exactly one mechanism**, which is
good news: it can be opened precisely, per call, rather than by turning the
guard off.

---

## 3. What JOE supports today

Measured, not assumed.

| capability | supported? | what actually exists |
| ---------- | ---------- | -------------------- |
| **draft creation** | **text only** | `_handle_draft` composes a message and returns it in the response, headed `DRAFT ONLY / NOT SENT`. It never touches Outlook. No draft item is created, so there is nothing in your Drafts folder afterwards |
| **draft modification** | **no** | nothing persists to modify. Each draft is a fresh composition |
| **reply generation** | **text only, and under-informed** | JOE can compose reply *text*, but a mail read returns only `subject, sender NAME, received, unread, importance, has_attachments`. **No body, no sender email address, no message identity.** JOE cannot quote what it is replying to, cannot address the reply, and cannot attach the reply to its thread |
| **packet assembly** | **no** | no POP builder, no POD builder, no carrier or broker packet builder, no attachment handling of any kind. The only attachment code in the program reports whether a message *has* attachments |
| recipient lookup | **partial** | contacts reads return `Email1Address`, so a recipient can be resolved from Contacts — but not from the mail thread being replied to |

**Finding: the Administrative tier is not "mostly built and blocked". It is
largely unbuilt.** The guard is the smaller half of the problem. Your worked
example — rebuild the packet, identify recipients, attach required files —
depends on three subsystems that do not exist yet: a packet builder, attachment
handling, and richer mail reads.

---

## 4. Proposed governance changes

Not implemented. Offered for your ruling.

### 4.1 Adopt the three tiers as the governing structure

Administrative / Operational Transmission / Business Authority is a better
model than Amendment 1's single transmission gate, because it puts the gate
where the consequence is. Building a packet is reversible; sending it is not.

Recommended: add the three tiers to Article II, with the six conditions
attaching to the **Operational** tier only.

### 4.2 Administrative writes need their own rule, not silence

Two items on your Administrative list are **writes to a record that Dispatch or
you may later rely on**:

- **Move email** — changes where a record lives.
- **Delete confirmed spam/junk** — destroys a record.

Article III currently says JOE may not alter operational truth. Moving and
deleting mail in an approved mailbox is arguably exactly that, so this needs
your explicit ruling rather than an implementation guess.

**My recommendation, and my own limit:** I will build *move* (including move to
Junk, which is reversible). I will **not** build permanent deletion, and I would
ask you to perform any irreversible deletion yourself. "Confirmed spam" is a
judgement, and a wrong one is unrecoverable. Moving to Junk achieves the
cognitive-load goal — the mail leaves your inbox — without the irreversibility.

### 4.3 The withdrawal window (2.3.4) should be reconsidered

This is the one place the revision and the conditions genuinely pull apart.
A mandatory pause between "send" and transmission fights *"snooze you lose"*.

Recommended: keep a **short, interruptible** window rather than a fixed delay —
JOE transmits immediately on approval, but a "stop" or "cancel" during the
send is honoured. You get the speed; the window becomes a brake rather than a
red light. Your ruling.

### 4.4 The approval phrase is the weakest link

You wrote: *"The approval phrase is the control."* Agreed — which is why it
needs hardening.

`"Send"` is one syllable, common in ordinary speech, and your cab is untested
for microphone accuracy. Three mitigations, all cheap:

1. **Approval is only valid against a pending read-back.** A stray "send" with
   nothing staged does nothing. This alone removes most of the risk.
2. **Approval expires.** A read-back not approved within a short window must be
   re-read before it can be approved.
3. **Low-confidence hearing is not approval** (condition 2.3.6). If the
   recognizer is not confident, JOE asks again rather than sending.

### 4.5 The audit log, and who owns it

Your list — sender mailbox, recipient, timestamp, approval event — matches
condition 2.3.5, with one addition it makes: **Dispatch owns that record.**

JOE may hold a temporary interaction record showing transmission occurred, and
must never become the authoritative source of transmission history. Those are
your words.

**This is a real dependency:** Dispatch is currently unbound (`enabled: false`,
`interface: "none"`). Until Dispatch can receive a transmission record, JOE
would be the *only* holder of it — which 2.3.5 forbids as a permanent state.
Options: (a) hold transmission until Dispatch can receive, (b) write an
append-only local record explicitly marked provisional and hand it over when
Dispatch arrives. **(b) is workable; it needs your ruling.**

---

## 5. What I recommend building, in order

1. **Transmission core, inert** — read-back, approval, audit record, and a send
   function that is present but cannot fire. *(authorised; starting now)*
2. Richer mail reads — body, sender address, message identity. Read-only, no
   governance change needed.
3. Attachment handling — read first, then attach.
4. Packet builders — POP, POD, broker, carrier.
5. Administrative tier — drafts as real Outlook items, replies, forwards, move.
6. Arm transmission — only after the cab microphone test passes (condition 6.1).

Steps 2 to 4 are the bulk of the work and need **no** governance change. That
is worth knowing: most of what your worked example requires is ordinary
engineering, not new authority.

---

## 6. Open rulings needed from you

| | question | my recommendation |
| - | -------- | ----------------- |
| 1 | Adopt the three tiers into Article II? | yes |
| 2 | May JOE **move** mail (including to Junk)? | yes — reversible |
| 3 | May JOE **permanently delete** mail? | **no** — I will not build it; do it yourself |
| 4 | Withdrawal window: fixed pause, or interruptible send? | interruptible |
| 5 | Provisional local transmission record until Dispatch is bound? | yes, marked provisional |
| 6 | Approval only valid against a pending read-back? | yes |

Nothing in §4 or §6 is implemented. **Mike Zachary remains final authority.**
