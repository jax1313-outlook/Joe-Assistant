# Architectural decision records — Phase 2

Every decision the mission left open, what it was decided from, and what was
rejected. The criteria the mission named are cited by number where they applied:
1 governance · 2 Mission Record architecture · 3 Dispatch System Independence ·
4 human authority · 5 operational reliability · 6 security · 7 data integrity ·
8 portability · 9 driver-first usability · 10 Phase 1 evidence.

---

## ADR-01 · The sandbox is `Joe-Assistant`

**Decided from repository evidence.** `Joe-Assistant/READ ME.md`: *"This
repository exists to test workers, governance, coordination, GX protocols, and
prototype workflows. This is not production. This is not Hold. This is not
Dispatch."* — and it states the promotion path: Test-Grounds → Review → Hold →
Review → Dispatch.

It is also the only in-scope repository with substantial code (147 Python files,
38,585 lines), the Joe plug-in, and the worker scaffolding.

**Rejected:** `Hold` (staging, empty of code); `Claude`/`Claude-3` (document
repositories); writing to `Dispatch` (forbidden by the mission). *(1, 3)*

## ADR-02 · The Dispatch corrections ship as a patch series, not a fork

Copying 34,000 lines of freight code into the sandbox would create a second copy
of the system of record — the same defect as Recommendation 10, one layer down.
`CLAUDE.md` §5.4: "a plug-in's copy is a copy."

Developed on a local branch of a read-only clone, exported with `git
format-patch`, and **verified by re-applying to a clean checkout and running the
suite there**. *(3, 7, 10)*

## ADR-03 · `DynamicCapacity` is wired, not reserved

`docs/MANAGER.md` is the repository's precedent for formally reserving a
capability, and it is explicit about what it reserves: something *"named in
planning and never built"*. That does not reach 1,861 lines of working code with
1,000 lines of tests.

The Purpose Statement's second verb is **Evaluate Possibilities**, and this
engine is the only thing in the repository that does it. What was missing was one
table.

**Utilization is deliberately not persisted.** `used_weight_lbs` describes what
is on a trailer now; a saved one returns as a claim about today made from last
week's freight. **An unprofiled truck is `UNCONFIGURED`, never assumed** —
inventing a 53-foot dry van is how freight is accepted onto a trailer that
cannot carry it. *(1, 5, 7, 9)*

## ADR-04 · Money is integer cents, migrated by generated columns

**Cents, not `Decimal`:** SQLite stores `INTEGER` exactly; a `Decimal` would be
serialised to `TEXT` and parsed back on every read, and one bad parse silently
becomes a wrong number. `Decimal` is used only at the conversion boundary.

**ROUND_HALF_UP, not banker's:** `round(0.125, 2)` is `0.12`. An invoice, a
settlement and a state fuel-tax form all say `0.13`.

**Generated columns, not a backfill:** no rows are rewritten, so it is instant
and reversible; there is no write path to forget, no trigger to mis-order, and no
half-finished migration. A double represents any 2-decimal amount to far better
than half a cent, so `ROUND(amount * 100)` recovers the cent that was typed —
float drift is a property of *accumulation*, which is why every sum now runs in
cents and why deriving cents loses nothing.

**The REAL columns stay.** One value with two views, never two values. *(7, 5, 8)*

## ADR-05 · A machine-performed restore leaves the status `UNVERIFIED`

`dispatch_launcher/backups.py` states that nothing writes the verification record
*"by design: it is a record of a human action, and manufacturing it is precisely
the kind of claim this program forbids."*

That rule is kept and now enforced rather than merely unreachable: `prove_restore`
writes `performed_by`, and `backup_status()` reads it. `Code-automated` keeps the
state at `UNVERIFIED` with the detail upgraded to what was actually done. Only a
named person reaches `VERIFIED`.

A record with **no** `performed_by` keeps its `VERIFIED` meaning: until this work
the only way one could exist was a person writing it. *(4, 5, 10)*

## ADR-06 · Only the contended field moved out of the JSON stores

The lockout counter moved to SQLite. PIN hashes, recovery words, creation, reset
and revocation did not.

The defect is a lost update on a counter, not a flaw in the credential store.
Moving the credentials as well would be a migration of secrets with no security
benefit and real risk. `_public()` reads the two fields back, so every caller
sees the shape it always did. *(6, 7)*

## ADR-07 · Atomicity by joining, not by threading a connection

`unit_of_work()` makes nested `get_connection()` calls join one transaction. The
alternative — passing `conn` through every store function — would touch 164 call
sites and 127 functions in `store.py` alone, for the same guarantee.

**Sends are deferred past the commit.** Once these became atomic, sending inside
one would be wrong twice: an email must not go out for work that rolled back, and
a thirty-second SMTP timeout must not be served while holding a write lock. *(5, 7)*

## ADR-08 · Delegated device code, and no client secret

`outlook_connector.py` declares `oauth_client_credentials` — app-only Graph. It
requires an Entra tenant, **cannot authenticate a personal Microsoft account at
all**, and grants tenant-wide mailbox access to read one calendar.

Device code carries the operator's own permissions, works on `outlook.com`, and
needs no secret on the laptop. There is deliberately no `DISPATCH_MS_CLIENT_SECRET`
setting anywhere in the repository.

**`Mail.Read` is not requested.** Neither program reads the operator's mailbox
and the scope should say so. *(6, 3, 8)*

## ADR-09 · SMTP basic auth is kept, and labelled

It is what every non-Microsoft relay still accepts. Removing the path an operator
is currently using, to make a point about Microsoft's roadmap, breaks a working
install.

What changed: a `535` against an M365 mailbox now names the cause and the
remedy, because an operator cannot act on "authentication failed" alone. *(5, 8)*

## ADR-10 · Retry is bounded, and never automatic

1 / 5 / 15 / 60 / 240 minutes, then `ABANDONED`. Retrying an authentication
failure every minute forever is how an account gets locked, and a queue that
never gives up is a queue nobody reads.

**No background thread.** The launcher, a scheduled task or the Maintenance
button runs the sweep, so a resend is always something an operator can point at.
A freight email going out twice because two workers swept the same queue is worse
than one going out late.

**Replayed from the load, not from a stored body.** A broker receiving, hours
later, a description of a state the load has since left is worse than a message
that never arrived. *(5, 9)*

## ADR-11 · Governance: the constitutions are scoped, not merged

Merging two documents that disagree produces a third that governs nothing and
that nobody ratified. Deleting one is forbidden by `CLAUDE.md` §7.

Authority was determined from **what the repository obeys**, not from recency:
`CLAUDE.md` declares itself the entry point, its clauses are the only ones
enforced by a test that fails a build, and `Dispatch` is the only repository
containing the running program.

**Manager: neither created nor removed.** `docs/MANAGER.md` is the only document
stating its implementation status — *named in planning, never built, authorises
no code*. The constitutions describe an intended organisational shape; `CLAUDE.md`
governs what the running program may contain. Different questions, and the fork
existed because nothing recorded which question each document answers.

**`DISPATCH_CONSTITUTION_v3`'s status is left open (U-03).** Its header reads
*"Current Controlled Constitution - v3 Replacement Draft"*, no repository holds
an approval record, and inferring ratification is the manufactured approval §4
forbids. Registered `ADVISORY`, true under either reading, with no code decision
resting on it. *(1, 4)*

## ADR-12 · A mediator, not a shared library, between workers

Without one, "bounded contracts" is a naming convention. The bus refuses
worker-to-worker calls; a worker that needs another declares a **dependency** and
the bus makes the hop, so the traffic appears in one audit trail under the
caller's own correlation id instead of inside an import.

**No response may carry an approval** — the contract raises on
`approved_by`/`decision` in the artifacts. **The audit records payload *shape*,
never values**: an audit that copies the data is a second place the data has to
be protected. *(1, 3, 4, 6)*

## ADR-13 · Joe proposes; Dispatch applies

`CLAUDE.md` §5.4: "No direct Dispatch write authority may be granted to
Assistant." A cab at 70 MPH is the worst listening environment this software will
run in, and a speech-to-write path fails silently: the driver says "picked up",
the recogniser hears "pick up", a load advances a state nobody chose.

Below a confidence floor Joe **says nothing** — a wrong proposal costs a
confirmation the driver must refuse at speed. A proposal advances only on an
unambiguous yes: "uh" is not consent. *(4, 9, 6)*

## ADR-14 · A stored fact is never sent to a reasoning provider

"Where am I going" is answered from the Mission Record. Faster, free, exact, and
it cannot hallucinate a destination the database knows. The provider sees only
`context_for_reasoning()` — never the raw record, one of whose fields is a
driver's phone number. *(9, 6, 2)*

## ADR-15 · No local stand-in for SharePoint or Teams

Every other port has a substitute that does real local work and reports
`SIMULATED`. These two report `ABSENT`: a folder on this laptop is not a shared
site, and writing a file does not tell anybody in Teams. A substitute that
cannot be mistaken for the real thing is useful; one that can is a trap. *(1, 5)*

## ADR-16 · The operator's timezone is configuration, not a guess

A dispatcher who types `08:00` means eight in the morning **where they are**.
Recording that is not guessing; attaching UTC would be. A value that already
carries an offset is stored untouched, and one that cannot be read is kept
exactly as typed and reported — never rewritten, never dropped.

This is what let `DynamicCapacity` be wired at all: it refuses a naive timestamp,
correctly, and the form was producing naive timestamps. *(5, 7, 8, 9)*

## ADR-17 · The coverage gate measures branches, and measures the launcher

Line coverage counts a line covered the moment it runs once, so every `if` whose
false path was never taken read as covered — and in this repository the false
paths are the refusals. `dispatch_launcher/` (3,943 lines, and the thing that
starts the product) was outside the gate entirely, and the workflow and
`.coveragerc` named different packages, so CI and a local `pytest --cov`
enforced two different gates.

The number went from 94.74% to **91.39%** because it is measuring more, more
strictly, across more code. *(5, 10)*
