# Known limitations, and what is not claimed

Written to the standard `Dispatch/CLAUDE.md` §6 sets: *never represent an
interface definition as a working integration, or test success as operational
deployment proof.*

---

## 1. Nothing here has been run on Mike's machine

The Dispatch suite is 4,221 passing tests and the sandbox suite is 738 passing
with 12 environment-conditional skips. Both are evidence of **software
behaviour**. Neither says whether Dispatch starts on a
Windows laptop, finds the `D:` drive, or keeps a load across a restart.

The twenty-step proof path now *runs*, which it did not before. It has not been
*walked*.

## 2. No Microsoft call has been made by the adapter layer built here

**Corrected 2026-09-13.** This section previously read *"No Microsoft call has
been made from any repository."* That was false, and two preserved proofs in
this repository say so:

| Record | Date | What it says |
|---|---|---|
| `Assistant_Plugin/proof/EMAIL_LAYER_PROOF.md` | 2026-08-26 | *"Source: the live Outlook Desktop profile. Not fixtures."* 3 accounts, 3 stores, 2 configured mailboxes read. 18 checks PASS. |
| `Assistant_Plugin/proof/RESEARCH_PROOF.md` | 2026-08-25 | *"PASS -- research is LIVE and attributed."* 8 attributions, provider Microsoft 365 Copilot. |

Live Microsoft capability has therefore existed in this programme. The sentence
generalised from the code written during this mission to the whole programme,
in a document whose purpose is not doing that. It is corrected rather than
quietly rewritten, per `CLAUDE.md` §7.

**What is true, stated at its real scope.** The M365 layer built here -- the
device-code flow, the Graph client, the six adapters, the transports -- has
made no call to Microsoft. It is implemented to Microsoft's published protocols
and exercised through injected openers against recorded response shapes, which
proves request shapes, paging, delta handling, retry rules, error translation
and refusals, and proves **nothing about connectivity**. Every capability in
that layer reports `UNCONFIGURED`, and no test in either repository claims
otherwise.

**Current connectivity is separately unestablished.** The most recent Microsoft
record, `Assistant_Plugin/proof/COPILOT_LIVE_PROOF.md` dated 2026-09-12, reads
**BLOCKED -- no tenant id**, and states plainly that no live prompt was sent.
Historical live capability and current live capability are two different
claims; only the first has evidence.

## 3. What is deliberately not built

| Not built | Why |
|---|---|
| A calendar mirror / `sync` | `CLAUDE.md` §5.5 forbids a second scheduling system. |
| A Teams bot | A bot answering in a channel is a second interface to Dispatch with its own authority story, and no doctrine covers one. |
| `.docx` authoring | Graph converts an uploaded document to PDF; it does not author one. Writing OOXML is a dependency and a body of work not taken. A `.docx` request is refused **by name**. |
| Azure Speech adapters | Status reporting is written; the adapters are not. Unlike the upload limit above, this one cannot be proved here at all — speech is a network service with no recorded protocol shape to test against, and no credentials exist in this environment. Writing it would produce code no test could distinguish from a stub. |
| ~~Resumable uploads~~ | **Built in Phase 3.** Files over 4 MB now use a Graph upload session, in 5 MiB chunks, resuming from `nextExpectedRanges` after a dropped connection. The old 4 MB refusal was not declining an edge case: a driver photographing a bill of lading produces 3-8 MB routinely, so the ordinary case was the one being refused. |
| A local SharePoint or Teams substitute | A folder on this laptop is not a shared site, and writing a file does not tell anybody. Both report `ABSENT`. |
| ~~Locking on the remaining JSON stores~~ | **Built in Phase 3.** All 41 mutating functions across all 11 stores hold a cross-process lock across the whole read-modify-write. See §5. |

## 4. The capacity engine is wired, and its stops are now built  *(Phase 3)*

`DynamicCapacity` can be reached: a profile per truck, a load-page panel, an
API. Phase 2 exercised the **physical** dimension only, and recorded that
"the stop-sequence and appointment-window paths take a `CapacityStop`, and
nothing in production constructs one. That is the next piece of this work."

It is built. `dispatch/load_stops.py` constructs the load's own pickup and
delivery stops and `scoring.assess_capacity()` passes them, so the engine's
stop-sequence and appointment checks run against real loads instead of sitting
unreachable behind passing unit tests.

Two checks now fire with no new data recorded at all: a delivery whose
appointment opens before its pickup, and a window that closes before it opens.
Both are BLOCKING.

**Still not built, and deliberately:**

| Not built | Why |
|---|---|
| Intermediate stops | A load records a pickup and a delivery. Deriving stops between them is route planning, and `CLAUDE.md` §5.5 forbids a second scheduling system. |
| A projected arrival on today's data | The forward walk needs a drive time and a dwell. No load carries `distance_miles` -- `Load` has no such field -- and no stop records a dwell. Both are `None` rather than `0.0`, so the engine declines rather than reporting every appointment as comfortably reachable. |

The walk turns itself on with no code change the day a distance is recorded and
`DISPATCH_DEFAULT_DWELL_HOURS` is set. Demonstrated: with 600 miles and a
1.5-hour dwell it projects both arrivals and reports a delivery window five and
a half hours out of reach.

## 5. The JSON stores no longer lose a concurrent update  *(Phase 3)*

Phase 2 left this stated rather than fixed, on the grounds that fixing it
properly meant moving eleven stores into SQLite. It did not.

Measured before the fix: **twelve processes each queued one publisher action and
the store held two.** Ten records gone, nothing corrupt, nothing anywhere saying
so. `atomic_write_json` guaranteed no reader sees half a file; it could not stop
two writers overwriting each other, because the damage is done before either
write begins.

`store_lock()` and the `guarded()` decorator hold an exclusive cross-process
lock across the whole read-modify-write. Applied to all **41** mutating
functions across all **11** stores. After: twelve of twelve, repeatably.

The decorator was chosen over restructuring because every mutator already reads,
edits and saves -- one line above each fixes the race without touching 138 call
sites and inventing 138 chances to get it wrong. It mirrors the `@atomic`
decorator the service layer already uses, so the codebase has one idiom for this
rather than two.

**What this does not do:** it does not make the stores transactional across
*different* stores. An operation that writes a conflict notice and a publisher
entry can still be interrupted between the two. Only the service layer's
`@atomic`, which is SQLite-backed, gives that, and these stores are not in
SQLite.

## 6. `verify_money_integrity` reports; it does not correct

An amount that was never a whole number of cents — a third-party import, a
four-decimal per-mile rate — is reported on `/maintenance` and left alone. Which
way `10.007` should go is a decision about somebody's invoice.

## 7. The registry covers 35 documents, and its scope is now checked  *(Phase 3)*

Phase 2 registered 23 and said the rest were "context, matrices and reports".
That was a reasonable reading and it had never been checked, which made it
exactly the kind of unverified claim the truth vocabulary exists to prevent --
and it failed in the worst direction, because a document that quietly asserts
authority and is not registered is invisible to the drift detector and to
anyone asking what governs.

`Governance/tools/screen_authority.py` scores every document by how binding its
language is, and reading what it surfaced found real gaps. **44 documents are
now registered**, up from 23.

The largest gap was in this repository: the **Assistant Plugin Constitution**,
which says of itself "Doctrine. Binding on all Assistant work", whose Article II
the decision log cites when ruling that JOE cannot transmit — and which was
governing the Assistant work here the whole time without being registered.

Also added: CF-04's adjudicated lifecycle ruling, cited by `CLAUDE.md` §5.1 and
unregistered; and `Claude/DISPATCH_PROGRAM_MAP.md`, registered ADVISORY
*because* it reads as authoritative and explicitly is not.

**The screen is a reading list, not a classifier, and the numbers say why.**
`Dispatch/CLAUDE.md`, the programme authority, scores 38. A registered CURRENT
document scores **0**. `DISPATCH_PROGRAM_MAP.md`, which states "NOT an approved
controlling document", scores **65** — higher than the constitution of the
programme. Authority is structural, not lexical: `CLAUDE.md` governs because it
declares itself the entry point and its clauses fail a build, not because of the
words it uses. Nothing was registered by score; the screen only decided what got
read.

A second pass replaced the word-count screen with the structural one ADR-22
argues for: what a document says about itself in its own status line. That took
a useless queue of 171 down to **22 documents that declare themselves binding
and are not registered** — and nine of them were production Dispatch doctrine,
including two issued by Mike personally on 30 August 2026, and
`DISPATCH_SYSTEM_INDEPENDENCE_DOCTRINE`, which was named as a standing criterion
for this entire mission and had never been registered.

One of them, `DISPATCH_CAPACITY_PLAN_DOCTRINE`, governs the capacity stop work
built earlier in this same phase — written before the doctrine had been read.
The code complied; compliance is now measured and pinned by a test rather than
assumed.

Still open: the remaining 13 self-declaring documents on that list, mostly in
`Hold/` and `Dispatch-Old/`, have not each been read and adjudicated. The screen
ranks; a person decides. And the count is now against 425 Markdown files across the
clones, not the 87 Phase 2 cited; that figure was scoped to a narrower set and
is corrected here.

## 8. Two governance findings are outstanding and correct

`Claude/` and `Publisher/` each carry a superseded constitution and no
`GOVERNANCE.md` saying so. The drift detector reports both as **BLOCKING**. This
work may only write to the sandbox; the exact files are generated into
`Governance/pointers/` and placing them is a human action.

## 9. `DISPATCH_CONSTITUTION_v3`'s status is unresolved

Its header reads *"Current Controlled Constitution - v3 Replacement Draft"* —
contradictory — and no repository holds an approval record. Registered `ADVISORY`,
which is true under either reading. **Requires Mike.**

## 10. The benchmark is one machine

7,786 ms → 47 ms at 2,000 loads was measured on this container with the real
portal test client. The *shape* of the improvement — constant connection count
rather than two per load — is what
`tests/test_dashboard_scaling.py` pins, because a wall-clock assertion on a
shared runner tests the runner.

## 11. Joe's voice has never heard anything

`voice/providers.py` reports what is installed. On any machine without Azure
credentials or a Whisper model that is the text engines, which report
`SIMULATED`: text in, text out. Nothing was heard and nothing was said aloud.

## 12. The worker bus is in-process, and now has a host  *(mission review)*

Intelligence, Publisher and Joe are separate *programs* with separate
repositories, connected here by an in-process mediator. That is the right shape
for a single-operator laptop and it is not a distributed system: there is no
queue, no retry across a restart, and no way for a worker to run on another
machine. Making it one is a different design and nothing here assumes it.

Until the mission review, nothing built the bus outside its own tests.
`Workers/worker_bus/host.py` builds it with a read-only view of Dispatch, and
`python -m worker_bus` runs it from a command line. Against a real load all
three primary duties answer `LIVE`. See `TEST_EVIDENCE.md` §4.

**Still not built, and deliberately:**

| Not built | Why |
|---|---|
| A long-running worker process | There is nothing to serve. The bus answers one question and exits, which is what a single-operator laptop needs; a daemon needs a supervisor, a restart policy and a story about what happens when it dies mid-answer, and none of that is warranted yet. |
| A call from Dispatch itself | Dispatch must run without its plug-ins (`CLAUDE.md` §5.4), and adding a call site inside Dispatch is a change to Dispatch, not to this sandbox. The host is the seam that makes such a call a few lines when Mike wants one. |
| Authorisation from the command line | Deliberate refusal, not a gap. §4.3 forbids manufacturing a Mike attribution, and a name typed at a prompt is not an authenticated action. The one capability that needs a recorded decision refuses from here and says what would satisfy it. |

## 13. The sandbox suite writes runtime state into its own tree  *(mission review)*

Running the suite leaves files under `Assistant_Plugin/runtime_data/` -- a token
cache directory and memory records. They are correctly `.gitignore`d and never
committed, and `Dispatch_Corrections/verify_manifest.py` now refuses to package
or archive anything `.gitignore` names, so they cannot reach `D:\Claude-Build`.

The tests writing there rather than into a temporary directory is the underlying
defect and it is **not fixed**. It spans a large number of plug-in tests, the
fix is a fixture change in each, and the risk it created -- shipping a token
cache -- is closed at the packaging boundary where it can be pinned by one test
rather than by remembering. Named here so the next person does not conclude the
tree-writing is intentional.

## 14. The Library is wired, and the Library forgets  *(Phase A)*

`build_bus()` now hands `LibraryWorker` a real `LibraryService` when the Library
repository is on the machine, and LIBRARY reports `LIVE` instead of
`UNCONFIGURED`. Publisher asks that Library for its templates; Phase A placed
two approved templates on the shelf and Publisher found them. See
`TEST_EVIDENCE.md` §8.

**The shelf is a dict in memory.** `dispatch_library.registry.ObjectRegistry`
writes nothing to disk, so every object placed in the Library lives exactly as
long as the process that placed it. A template accepted by one command is not
there for the next one. That is why the walkthrough is one script rather than a
sequence of `python -m worker_bus` invocations: run it as separate commands and
Publisher correctly reports `TEMPLATE_NOT_IN_LIBRARY` every time.

This is **not fixed here**, and the reason is a boundary rather than effort.
Persistence is a decision about the Library's own storage — what format, where
on disk, what happens to version history, who may write — and the Library is a
separate repository under THE MIKE RULE. Choosing its storage from inside the
Assistant sandbox would be exactly the kind of cross-repo decision §5.4 exists
to prevent. What is fixed is the part that was a plain defect: one process now
holds **one** Library rather than one per `build_bus()` call.

**What this means in practice:** the Library is usable within a single program
run and unusable across runs. Anything that needs templates to survive a
restart needs the Library to gain storage first. Until then, treat an empty
Library after a restart as correct behaviour, not a bug.

> **Update 2026-09-13 — closed when the catalog is configured.** Mike Zachary
> authorised the Library v2 build. The Library repository now has a persistent
> SQLite catalog (`dispatch_library.catalog`, schema version 2). With
> `DISPATCH_LIBRARY_CATALOG` set, `library_service()` holds that catalog, and
> `library_persistent()` / `worker_bus status --json` say so. Phase A now passes
> as separate processes (`Testing/phase_a_separate_processes.py`,
> `TEST_EVIDENCE.md` §10).
>
> **Still true:** with `DISPATCH_LIBRARY_CATALOG` unset, the Library is the
> in-memory shelf and forgets on exit — reported, not hidden. A Library asset
> that is current but REVIEW_DUE is now `UNAVAILABLE` to the bus, and Publisher
> reports `TEMPLATE_NOT_USABLE` rather than counting it present; before this, any
> non-ABSENT answer counted as a template.

## 15. Two things that were wrong and are now right  *(Phase A)*

Both were found by running the walkthrough, and both had passing tests over
them. Recorded here because the pattern matters more than either defect:
**every one of them was a seam between two components that no test crossed.**

| Was | Is |
|---|---|
| `library_service()` returned a new `LibraryService` per call, so each `build_bus()` held its own shelf and Publisher could not see a template the caller had just accepted. | One Library per process. Pinned by `Workers/tests/test_worker_host.py::TestTheLibraryIsOneShelf`. |
| The default transport's status named `Archive/Outbox`. Every `.eml` this program has ever written landed in `Archive/CIN/Outbox`, because with nothing configured the writer is `cin_lite`, not `FileOutboxTransport` — `dispatch.outbound.install()` engages only for Graph and XOAUTH2. An operator following the status found an empty directory. | Both ask `cin_lite.email_delivery.outbox_dir()`. The sentence and the file are the same sentence. |

Neither changes what Dispatch *does*. The second changes only what it *says*,
which is the thing the transport layer was built to get right.
