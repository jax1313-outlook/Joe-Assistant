# BUILD SUMMARY — Claude build

**Destination: `D:\Claude-Build`.** This package is produced for transfer into
that folder. See `TRANSFER_TO_D_DRIVE.md`.

**Authority: Mike Zachary.** Nothing here decides anything. Every finding below
is a recommendation or a measurement, and the three items that need a person are
named in §5.

---

## What this build is

Three phases and a mission review against one question: what is wrong with
Dispatch that is hard to see from inside it, and what is the strongest thing
that can be done about it.

| Phase | What it produced |
|---|---|
| 1 | Ten findings, each with a measurement rather than an opinion |
| 2 | Twelve corrections to Dispatch, plus the sandbox's own governance registry, worker bus, Joe conversation layer and Microsoft 365 adapter layer |
| 3 | The two open items Phase 2 recorded as unfinished, plus two more found on the way — all closed and measured |
| Review | One material capability gap found and closed: the worker bus had no host |

Phase 2's corrections are open as a **thirteen-PR stack** against production
Dispatch (#130–#142), CI green on every one, waiting on Mike in number order.
Phase 3's corrections are patches `0013`–`0017` in
`Dispatch_Corrections/patches/`, held here rather than pushed. See
`MERGE_PLAN.md`.

---

## The numbers

| | Baseline | Now |
|---|---|---|
| Dispatch suite | 3,696 at `main` | **4,221** |
| Dispatch gated coverage | 94.74% **line**, 3 packages, launcher exempt | **91.48%** **branch**, 4 packages, launcher inside |
| Sandbox suite | 681 | **738** passed, 12 skipped, 1,055 subtests |
| 12 processes queueing one action each | store held **2** | store holds **12** |
| Capacity checks reachable from a real load | **0** | stop ceiling, out-of-route, window validity, appointment order, forward walk |
| Mutating store functions under a lock | 0 of 41 | **41 of 41** |
| Governance documents registered | 23 | **44** |
| Worker duties reachable outside a test | **0 of 3** | **3 of 3** |

Every "before" was measured, not estimated. The coverage figure went *down* and
the gate got stronger — line coverage counts an `if` whose false path never runs
as covered, and the false paths are where the refusals live. Full record:
`TEST_EVIDENCE.md`.

---

## The recurring finding, which is the most useful thing in this build

Four separate times, in four separate subsystems, the same defect shape:

| Subsystem | The shape |
|---|---|
| The proof path | Twenty documented steps. Three of the commands did not exist. |
| The capacity engine | 1,861 lines of stop-sequence and appointment logic with unit tests and **no caller** — `scoring.assess_capacity()` never passed `stops=`. |
| The worker bus | Three workers with bounded contracts, constructed **only in their own tests**. |
| The JSON stores | `atomic_write_json` guaranteed no reader sees half a file, and could not stop two writers overwriting each other. |

**Passing tests over code nothing calls.** It is the hardest defect to see from
inside a repository, because every signal a builder normally trusts — green
suite, coverage, documentation — reports success. It is worth naming as a class,
because the next one will look like the last four.

---

## What each phase closed

### The capacity engine's appointment checks had never run  *(Phase 3)*

`dispatch/capacity.py` could evaluate stop sequences and appointment windows
from the day it was written. None of it ran.

`dispatch/load_stops.py` is the missing constructor. Most of it is about
refusing to invent what the load does not record:

- **No naive timestamp reaches the engine.** It treats one as BLOCKING and is
  right to — `06:00` is not an instant. But Dispatch's own `pickup_datetime` is
  routinely naive, so passing those raw would have turned a correct refusal into
  a false alarm on nearly every load.
- **A single recorded time is not a window.** Setting `end = start` would have
  produced a "complete" window demanding arrival to the second.
- **An unknown distance is `None`, not `0.0`.** Zero drive hours claims the
  truck arrives the instant it leaves. Patch `0015` then found the distance one
  join away, on `RateConfirmation` — miles somebody committed to, rather than an
  estimate.
- **An unrecorded dwell stays `None`.** Zero would make every appointment look
  reachable.

### The JSON stores lost concurrent updates  *(Phase 3)*

Twelve processes, twelve records queued, **two** in the store. Nothing corrupt;
ten records simply absent, with nothing anywhere saying so.

`store_lock()` and `guarded()` hold an exclusive cross-process lock across the
whole read-modify-write, applied to all 41 mutating functions across all 11
stores. Twelve of twelve afterwards, repeatably.

### Evidence over 4 MB was refused by name  *(Phase 3)*

A driver photographing a bill of lading produces 3–8 MB routinely, so the
refusal declined the ordinary case. Graph upload sessions now handle it, in
5 MiB chunks, resuming from `nextExpectedRanges`. Writing the tests found two
false-success defects — reporting `LIVE` when Graph never returned the finished
item, and when it returned a `200` with no `id`. Both now `UNVERIFIED` with the
session cancelled.

### The registry's scope was asserted, never checked  *(Phase 3)*

23 registered, the rest called "context, matrices and reports" — unchecked, and
unchecked in the direction that costs most. **44 registered now.** Nine were
production Dispatch doctrine, two issued by Mike personally on 30 August 2026,
and the largest was in this repository: the Assistant Plugin Constitution,
"Binding on all Assistant work" by its own statement, governing this work the
whole time without being registered.

The screening tool **failed as a classifier**, and that failure is the finding
worth keeping: `Dispatch/CLAUDE.md` scores 38, a registered CURRENT document
scores 0, and a document that states "NOT an approved controlling document"
scores 65. Authority is structural, not lexical. The tool ranks; a person reads.

### The workers could not be reached  *(mission review)*

`Workers/worker_bus/` defined Intelligence, Publisher and Joe with bounded
contracts and a mediator. Nothing constructed the bus outside its own tests, so
no worker could perform a constitutional duty against a real Dispatch.

`Workers/worker_bus/host.py` builds it. The reader it hands the workers is a
frozen dataclass exposing exactly nine read functions and nothing else, and a
test walks all nine and fails if any resolves to a `dispatch.store` function
that writes — `CLAUDE.md` §5.4's *"No direct Dispatch write authority may be
granted to Assistant"* enforced rather than commented. A second test fingerprints
every table's row count before and after all three duties run.

Against a real load: `INTELLIGENCE assess_load` `LIVE`, `PUBLISHER
check_readiness` `LIVE`, `JOE read_back_load` `LIVE` — *"Next is delivery
2026-07-30 16:00 - 20:00 in Houston TX."*

`python -m worker_bus` then makes that reachable by a person rather than only by
code, because a `build_bus()` nothing invokes is the same defect one layer up.
`status` says what the workers can do on this machine without running one; `ask`
runs exactly one capability and prints the status word first. There is
deliberately **no `--authorized-by` flag**: §4.3 forbids manufacturing a Mike
attribution, and a name typed at a prompt is not an authenticated action, so the
one capability requiring a recorded decision refuses from the command line and
names what would satisfy it.

Writing it also found a live defect: Joe imported his conversation layer at call
time with no guard, so on a machine without it installed a driver asking for a
read-back got a `ModuleNotFoundError` traceback. It now reports `UNCONFIGURED`
with a sentence a person can act on. §5.4 again: *"Degradation is permitted.
Incapacity is not."*

### The transfer package was carrying runtime state  *(mission review)*

Found by regenerating the manifest for `TEST_EVIDENCE.md`: the file count jumped
574 → 708, and the new entries were memory records written into the tree by test
runs. `Assistant_Plugin/runtime_data/` holds the DPAPI-encrypted Microsoft 365
token cache and, in `.gitignore`'s own words, "memory records carrying real
driver requests and assistant responses". Git ignored them correctly; a
filesystem walk does not know what "untracked" means.

**The archive built for `D:\Claude-Build` already contained 129 of them.**
Nothing was leaked — it was never copied anywhere — which is the only reason
this is a finding and not an incident.

The walk now reads `.gitignore` rather than restating it, `--archive` builds the
zip from the manifest so the two cannot describe different sets of files, and 11
tests pin both. Rebuilt: 452 files, 0 runtime files, every archive entry
matching its manifest hash.

---

## §5 — what still needs Mike

1. **The thirteen pull requests.** #130–#142 against `jax1313-outlook/Dispatch`,
   CI green on all thirteen, no open review threads. They merge in number order.
   `MERGE_PLAN.md` groups them into three merges and names the two that are not
   a clean revert.

2. **`DISPATCH_CONSTITUTION_v3`'s ratification status.** It is headed "Current
   Controlled Constitution – v3 Replacement Draft", which is contradictory, and
   no repository holds an approval record. Registered ADVISORY, which is true
   under either reading. Inferring it was ratified would be the manufactured
   approval `CLAUDE.md` §4 forbids outright.

3. **`Claude/` and `Publisher/` each need a `GOVERNANCE.md` pointer.** The drift
   detector reports both as BLOCKING and is correct. This build may only write
   to its own folder, so the files are generated into `Governance/pointers/` and
   placing them is a human action.

---

## What is not claimed

Nothing here has run on Mike's laptop. No Microsoft call has been made from any
repository. The twenty-step proof path now *runs*; it has not been *walked*.

`CLAUDE.md` §6: the repository test suite is evidence of software behaviour
only, and is never operational proof.

Full list: `KNOWN_LIMITATIONS.md`. Full evidence: `TEST_EVIDENCE.md`.
