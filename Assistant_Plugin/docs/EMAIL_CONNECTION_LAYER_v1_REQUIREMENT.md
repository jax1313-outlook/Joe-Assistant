# Email Connection Layer v1 — Approved Requirement

**Status: RECORDED. NOT STARTED.**
**Approved by:** Mike Zachary, 2026-08-25
**Sequenced behind:** Copilot proof, then Voice proof — by Mike's explicit
instruction. Nothing in this document has been built.

---

## Why this is not started

Mike set the order himself:

> Do not combine this work with Copilot activation.
> Finish Copilot proof first. Finish Voice proof second.
> Then build multi-account email support.

Both prerequisites are behind the human authority gate. Copilot proof needs an
Entra app registration, admin consent, a licensed work account, and a sign-in.
Voice proof needs Mike at the microphone. Neither is something JOE
may do on his behalf, so this work has a start condition that has not been met.

This document exists so the requirement is not lost while that gate is closed.

## The requirement, as approved

| # | Requirement |
| --- | --- |
| 1 | Multiple mailbox support |
| 2 | Friendly account names |
| 3 | Separate account status display |
| 4 | Read-only operation |
| 5 | Search one account |
| 6 | Search all enabled accounts |
| 7 | Explicit account provenance |
| 8 | `Ops@l1truck.com` support |
| 9 | `Admin@l1truck.com` support |
| 10 | Future mailbox expansion without code edits |
| 11 | No sending |
| 12 | No mailbox modification |
| 13 | No Outlook dependency for launch |
| 14 | Failure of one mailbox must not disable JOE |

## Mike's assessment is correct

> JOE currently demonstrates a single Outlook connection. This is not
> equivalent to the approved multi-account email architecture.

That is accurate. What exists today is a **single-mailbox reader with an
account parameter** — it can be pointed at any one mailbox in the Outlook
profile, one call at a time. It has no notion of a *set* of mailboxes, no
friendly names, no per-account status, and no search. Enumerating three
accounts in a report is not multi-account architecture, and it should not have
read as one.

## Honest gap assessment against the fourteen

| # | Requirement | Today | Gap |
| --- | --- | --- | --- |
| 1 | Multiple mailboxes | **Partial** | `account=` parameter on calendar, mail, and contacts targets any mailbox in the profile — but one per call. Configuration holds a single `"account"` string, not a set. |
| 2 | Friendly names | **No** | Only raw SMTP addresses and Outlook's own display names. |
| 3 | Separate account status | **No** | One `Outlook READY` chip for the whole connection. A mailbox that is failing is invisible. |
| 4 | Read-only | **Yes** | 21 write-capable COM calls scanned for and refused before any script runs; zero present. |
| 5 | Search one account | **Partial** | Folders can be *read* from one account. There is no search of any kind over mail. |
| 6 | Search all enabled accounts | **No** | No concept of an enabled set exists. |
| 7 | Explicit account provenance | **Partial** | Every read returns and reports the `account` it came from. The provenance *class* is `LOCAL_OUTLOOK` without the mailbox identity carried in it, so two mailboxes are indistinguishable at the class level. |
| 8 | `Ops@l1truck.com` — **APPROVED** | **Reachable** | Present in the profile; readable via `account=`. Not enabled as a first-class mailbox. |
| 9 | `Admin@l1truck.com` — **APPROVED** | **Not possible today** | Active in Outlook Web; **not mounted in Outlook Desktop**. Four-way enumeration returns NOT PRESENT. See below. |
| 10 | Expansion without code edits | **No** | A single account string is configurable. Adding a mailbox with a friendly name and an enabled flag would require code today. |
| 11 | No sending | **Yes** | No send path exists anywhere in the program. |
| 12 | No mailbox modification | **Yes** | Enforced by the same guard as #4. |
| 13 | No Outlook dependency for launch | **Yes** | Proven — proof step 14 runs the whole program with Outlook unavailable. |
| 14 | One mailbox failing must not disable JOE | **Partial** | Outlook failing *as a whole* is handled and proven. Per-mailbox isolation does not exist, because per-mailbox reads are never orchestrated together. |

Four of fourteen are already satisfied, and all four are the constraints —
read-only, no sending, no modification, no launch dependency. Every capability
requirement is partial or absent.

## Mike's rulings, 2026-08-25

1. **`Admin@l1truck.com` — question withdrawn.** Mike is loading the mailbox
   into Outlook today. Requirement 9 stands; it stops being blocked the moment
   the account appears in the profile. Not present as of this writing
   (`knows_account("Admin@l1truck.com")` returns `False`).
2. **`Ops@l1truck.com` is the default mailbox.** Applied — see below.
3. **`System@l1truck.com`** — ruled **CLOSED**. Not approved for planning,
   requirements, architecture, or future Email Connection Layer design. The
   investigation is closed and is not to be reopened.

### On `System@l1truck.com`

**Closed. Not approved for planning, requirements, architecture, or any future
Email Connection Layer design.**

The narrative that stood here — profile counts, a withdrawn guess about what the
mailbox might be, and a note that the question was open — is removed. It was
planning-adjacent content about a mailbox that is not a planning input.

The measurements taken before closure are preserved as a historical record in
[SYSTEM_MAILBOX_INVESTIGATION.md](../proof/SYSTEM_MAILBOX_INVESTIGATION.md).
That document is closed and is not to be reopened.

The mailbox remains untouched in the Outlook profile — not removed, disabled,
renamed, or altered.

## What was applied now, and what was not

**Applied — a configuration change to what already exists:**

`outlook.account` is now `Ops@l1truck.com` in both the machine configuration
and the deployment template. Verified live: JOE reads Ops@l1truck.com
and reports it as the account in use.

This is not Email Connection Layer v1. It is setting the single existing
account value, which has always been configurable. No multi-mailbox code was
written.

**The consequence Mike should see before deciding it is right:**

One configured account covers **all three folders**. Ops@l1truck.com holds
127 messages, no calendar, and no contacts. So with Ops@ as the default:

- Mail questions read Ops@ — 127 messages. This is the intent.
- **Calendar questions now return "Nothing on the calendar."** Truthfully — Ops@
  has an empty calendar. Mike's 601 appointments are on jax1313@outlook.com.
- **Contact questions now return nothing**, for the same reason. The 145
  contacts are on the personal account.

Reading mail from one mailbox and calendar from another is precisely
requirement 1, and it is not built. Until it is, this is one setting with one
answer, and the choice is Mike's:

- leave `Ops@l1truck.com` and accept an empty calendar and contact list, or
- set it back to the personal account and accept that mail is the personal
  inbox, or
- change it per question, by hand, in configuration.

## Approved mailboxes — Mike, 2026-08-25 (final)

| Mailbox | Status | Visible in Outlook Desktop |
| --- | --- | --- |
| `Ops@l1truck.com` | **APPROVED** | yes |
| `Admin@l1truck.com` | **APPROVED** | **no — not mounted** |
| `System@l1truck.com` | **CLOSED — not approved, not a planning input** | present in profile, ignored |

Two approved mailboxes. Nothing was enabled — EMAIL_CONNECTION_LAYER_v1 is not
being built.

### `System@l1truck.com` — CLOSED

Mike's final ruling is **Ignore**. The investigation is closed and no further
queries will be run against it.

Two facts that were requested and remain unretrieved — `ExchangeServer` and the
newest Inbox message date — **will not be pursued.** The gathered facts are
preserved in
[SYSTEM_MAILBOX_INVESTIGATION.md](../proof/SYSTEM_MAILBOX_INVESTIGATION.md) so
the work is not lost if the question is ever reopened, but that document is
closed.

It is excluded from every candidate list, every default, and all planning. It
appears in enumeration tables only because it is genuinely in the Outlook
profile and hiding it would make those tables false. It remains untouched — not
removed, disabled, renamed, or altered.

### `Admin@l1truck.com` — approved, and not yet reachable

Approved as a mailbox. Confirmed live in Outlook Web by screenshot. **Still not
mounted in Outlook Desktop**, verified by four-way enumeration — `Accounts`,
`Stores`, `Folders`, and a direct name probe all return NOT PRESENT.

Approval does not mount it, and nothing is hard-coded waiting for it. Discovery
will find it when Outlook Desktop exposes it. Evidence:
[MAILBOX_DISCOVERY_EVIDENCE.md](../proof/MAILBOX_DISCOVERY_EVIDENCE.md).

**One thing to watch when the layer is built:** if Admin@ is mounted as a
*shared* mailbox rather than a full account, it will appear in `Stores` but not
in `Accounts` — and the adapter reads `Accounts` only. See the discovery rule
below.

## Discovery must not assume — including about how to discover

> Mailbox registration must be discovered from the actual Outlook profile and
> not assumed.

Recorded as a governing rule. One finding matters for building it:

**Enumerating `Accounts` is itself an assumption** — that every mailbox is an
account. It is not. Shared mailboxes and "open these additional mailboxes"
entries appear in `Namespace.Stores` and as top-level `Folders`, but **not** in
`Namespace.Accounts`. An `Admin@` address is very commonly a shared mailbox.

The adapter enumerates `Accounts` only. On this profile all three views happen
to agree, so the gap is invisible today — and it would silently hide a shared
mailbox on any profile where they diverge. Discovery in
EMAIL_CONNECTION_LAYER_v1 must reconcile **Accounts, Stores, and top-level
Folders**, and report anything found in one view but not another rather than
picking a winner.

Not fixed now. This layer is not being built.

## Mail, Calendar, and Contact sources are distinct

> Do not assume one mailbox owns all three.

Recorded as a governing rule, and already demonstrably true on this profile:

| Mailbox | Mail source | Calendar source | Contact source |
| --- | --- | --- | --- |
| `Ops@l1truck.com` — **approved** | **127** | 0 | 0 |
| `Admin@l1truck.com` — **approved** | not known | not known | not known |
| jax1313@outlook.com — not approved, shown for contrast | 222 | **602** | **145** |

`Ops@l1truck.com` is a mail source and nothing else. Every calendar item and
every contact on this machine lives on the personal account, which is not an
approved mailbox.

Only approved mailboxes appear here. `System@l1truck.com` is closed and is not
a planning input, so it has no row.

`Admin@l1truck.com` is approved but not mounted, so what it holds — mail,
calendar, contacts, or some combination — **is not known and is not assumed.**
It gets no presumed row in this table until Outlook Desktop exposes it.
A design that treated a mailbox as owning all three would answer calendar
questions with silence — which is exactly what the current single-account
setting does today with `Ops@l1truck.com` selected.

Mail Sources, Calendar Sources, and Contact Sources are therefore three
separate registries in this layer, each independently populated from discovery.

## Constraints to maintain — restated at Mike's direction

- Read-only mode
- Per-mailbox status
- Per-mailbox provenance
- Per-mailbox failure isolation
- No sending
- No mailbox modification

Four of these already hold program-wide. **Per-mailbox status, per-mailbox
provenance, and per-mailbox failure isolation do not exist** and are the
substance of this layer — see the gap assessment above.

## Boundaries that carry forward unchanged

These are not restated as new constraints. They already govern this program and
will govern this layer:

- Read-only. No operational writes, ever.
- Dispatch is not connected and is never contacted.
- No mailbox contents in logs, reports, fixtures, or screenshots beyond what
  proof genuinely requires.
- No credential of any kind in source, configuration, logs, or reports.
- Degradation is permitted. Incapacity is not — JOE must open and
  operate with every mailbox unreachable.
- Silence is never consent.

---

Mike Zachary remains final authority.
