# TEST EVIDENCE — Claude build

Destination: `D:\Claude-Build`. Authority: Mike Zachary.

Every figure below was produced by a command run in this container on the date
given. Nothing is estimated, and nothing is carried forward from an earlier run
without saying so.

**Read `Dispatch/CLAUDE.md` §6 first.** A test suite is evidence of *software
behaviour*. It is never operational proof. Nothing in this document says
Dispatch works on Mike's laptop, because nothing here was run there.

---

## 1. The two suites, as they stand today

Measured 2026-09-13.

### Sandbox — this repository

```
$ python -m pytest
738 passed, 12 skipped, 1055 subtests passed in 3.30s
```

Broken out, because "738" hides which program is being exercised:

| Suite | Result | What it covers |
|---|---|---|
| `Assistant_Plugin/tests` | 574 passed, 12 skipped, 1,000 subtests | Joe, the M365 adapter layer, transports, voice, conversation |
| `Workers/tests` | 74 passed | The worker bus, the four workers, the host and the command line |
| `Governance/tests` | 29 passed | The registry, the drift detector, the authority screen |
| `Testing` | 61 passed, 55 subtests | Cross-cutting contract tests, and the transfer package |

`pytest.ini` names those four paths explicitly rather than walking the tree.
`Play-Pen/` and `ASST/` hold archived copies whose tests are history; collecting
them reports failures about decisions superseded months ago. Running
`pytest .` — which ignores `testpaths` — collects them and reports
`1 failed, 1076 passed`. That failure is in `ASST/1/Tests/test_assistant_ui.py`,
an archived tree, and is **not** a regression in anything this build touched.
It is named here rather than left for somebody to find.

### The twelve skips are all environment-conditional, and all honest

| Count | Reason |
|---|---|
| 6 | `no token cache on this machine - nobody has signed in` |
| 5 | `tkinter is not installed on this interpreter` |
| 1 | `set ASSISTANT_TEST_OUTLOOK=1 to read live Outlook` |

None of them is a skip added to get a suite green — `CLAUDE.md` §7 forbids that.
Each is a test that requires a thing this container does not have, and each says
which thing.

### Dispatch — the patched checkout

```
$ python -m pytest -o addopts= -q
4221 passed in 641.41s (0:10:41)

$ python -m pytest -o addopts= -q --cov --cov-config=.coveragerc
Required test coverage of 90.0% reached. Total coverage: 91.48%
```

**Branch** coverage over four packages — `cin_lite`, `dispatch`, `portal`,
`dispatch_launcher`. The floor is 90%.

---

## 2. How the numbers moved, and what moved them

| | `main` at `3c03ab2` | after Phase 2 | now |
|---|---|---|---|
| Dispatch suite | 3,696 | 4,171 | **4,221** |
| Dispatch gated coverage | 94.74% **line**, 3 packages, launcher exempt | 91.39% **branch**, 4 packages | **91.48%** branch, 4 packages |
| Sandbox suite | 681 | 692 | **738** |

**The two coverage figures do not compare, and the drop is the improvement.**
Line coverage counts an `if` whose false path never runs as covered, and the
false paths are where the refusals live. `dispatch_launcher/` was also outside
the gate entirely at 87.75%; it is inside it now, with its Windows-only branches
marked `pragma: no cover` line by line rather than the package being exempt.

The sandbox's last jump is the one worth naming: **692 → 738**. Those 46 tests
came with `Workers/worker_bus/host.py` and `__main__.py` — the gap the mission
review found (§4) — and with the packaging guard in §5.

---

## 3. Phase 2 — the recorded evidence run

`Dispatch_Corrections/evidence/COMPLETION_EVIDENCE.md` is the verbatim record,
collected 2026-09-12T21:35:12Z by `Dispatch_Corrections/collect_evidence.py`.
Seventeen checks, all PASSED, each with the command and its untruncated output.
The machine-readable form is `COMPLETION_EVIDENCE.json`.

The four steps that measure a defect rather than a feature:

| Step | Before | After |
|---|---|---|
| Proof step 18 | `invalid choice: 'verify'` — the documented command did not exist | `RESULT: PASSED`, and `RESULT: FAILED` on tampered bytes |
| Home page at 2,000 loads | 7,786 ms | 48.0 ms |
| 12 concurrent PIN failures | recorded as **1**; the lockout never tripped | recorded as 12; it trips |
| Backup | nothing in the product could take one | taken, every hash verified, restore proven — and still reported `UNVERIFIED`, because a machine restored it |

That last row is the shape the whole build is written in. The restore *worked*
and the status is still `UNVERIFIED`, because `UNVERIFIED` is the true word
until a person opens the restored copy and confirms it.

---

## 4. The mission-review gap: the worker bus had no host, and no caller

**The finding.** `Workers/worker_bus/` defined three workers with bounded
contracts and a mediator to route between them. Nothing constructed the bus
outside its own tests. The workers could not perform their constitutional
duties, not because the duties were wrong, but because there was no way to
reach them with a real Dispatch behind them — the same failure shape as the
capacity engine in Phase 3 §4 and the proof path in Phase 2: **passing tests
over code with no caller.**

**The fix.** `Workers/worker_bus/host.py` — `build_bus()`, and a `DispatchReader`
that is a frozen dataclass exposing exactly nine read functions from
`dispatch.store` and nothing else.

**The evidence.** 17 tests for the host, none skipped:

```
$ python -m pytest -o addopts= -v Workers/tests/test_worker_host.py
TestTheReaderCannotWrite::test_no_method_on_the_reader_looks_like_a_write        PASSED
TestTheReaderCannotWrite::test_every_declared_read_is_a_real_dispatch_function   PASSED
TestTheReaderCannotWrite::test_none_of_the_declared_reads_is_a_write             PASSED
TestTheReaderCannotWrite::test_the_reader_exposes_exactly_what_it_declares       PASSED
TestBuildingTheBus::test_all_four_workers_are_registered                         PASSED
TestBuildingTheBus::test_it_does_not_raise_when_dispatch_cannot_be_imported      PASSED
TestBuildingTheBus::test_a_reader_can_be_injected                                PASSED
TestBuildingTheBus::test_joe_has_no_reasoner_unless_one_is_given                 PASSED
TestBuildingTheBus::test_describe_reports_status_without_running_anything        PASSED
TestThePluginPath::test_it_puts_the_plugin_where_joe_can_import_it               PASSED
TestThePluginPath::test_it_is_idempotent                                         PASSED
TestJoeDegradesRatherThanCrashing::test_a_missing_conversation_layer_is_
    unconfigured_not_a_traceback                                                 PASSED
TestTheDutiesAgainstARealLoad::test_dispatch_is_readable_from_the_host           PASSED
TestTheDutiesAgainstARealLoad::test_intelligence_analyses_a_real_load            PASSED
TestTheDutiesAgainstARealLoad::test_publisher_detects_the_gaps_in_a_real_load    PASSED
TestTheDutiesAgainstARealLoad::test_joe_reads_the_load_back_in_one_sentence      PASSED
TestTheDutiesAgainstARealLoad::test_no_worker_writes_anything                    PASSED

17 passed in 0.55s
```

`TestTheDutiesAgainstARealLoad` builds a real Dispatch database, creates a real
load, and runs each worker's primary duty against it:

| Worker | Duty | Status |
|---|---|---|
| `INTELLIGENCE` | `assess_load` | `LIVE` |
| `PUBLISHER` | `check_readiness` | `LIVE` |
| `JOE` | `read_back_load` | `LIVE` — *"Next is delivery 2026-07-30 16:00 - 20:00 in Houston TX."* |

Joe's sentence is the D2 test in one line: the most important thing first, no
list to scan, spoken by somebody with one hand on the wheel.

**Three refusals are proved, not asserted:**

- `test_none_of_the_declared_reads_is_a_write` walks the nine declared reads and
  fails if any resolves to a `dispatch.store` function that writes. This is
  `CLAUDE.md` §5.4 — *"No direct Dispatch write authority may be granted to
  Assistant"* — enforced by a test rather than by a comment.
- `test_no_worker_writes_anything` fingerprints every table's row count before
  and after all three duties run, and compares.
- `test_it_does_not_raise_when_dispatch_cannot_be_imported` is §5.4's other
  half: *"Degradation is permitted. Incapacity is not."* With no Dispatch
  importable the bus still builds and every worker reports `UNCONFIGURED`.

### And then a way for a person to run it

A `build_bus()` nothing invokes is the same defect one layer up, so
`Workers/worker_bus/__main__.py` makes the workers reachable from a shell.
**18 further tests**, every one calling `main()` with an argument list and
checking the exit code, the way a shell would:

```
$ python -m worker_bus status
Dispatch readable:  yes
Assistant plug-in:  present

INTELLIGENCE   LIVE
    assess_load          Notice anything about a load that is worth a person's attention.
    assess_broker        Report what the record says about a broker. Never a score, never a verdict.
    summarise_risk       Order existing findings for a person to read.
JOE            CONFIGURED
    read_back_load       Say what the driver needs about the current load, in one sentence.
    answer_question      Answer a question about what is on file. Refuses anything not on file.
    propose_capture      Turn something the driver said into a proposed change, with the words that would confirm it.
LIBRARY        UNCONFIGURED
    fetch_asset          Return an approved asset by id.
    list_assets          What is on the shelf, by kind.
PUBLISHER      LIVE
    check_readiness      Is everything a completion package needs actually on file?
    assemble_completion_package Build the package a person will review before it is sent.
```

`status` runs no worker — D9, retrieval is not modification — and a test
fingerprints every table before and after to prove it.

Three refusals, verbatim, each exiting non-zero so a script cannot read
"nothing here" as success:

```
$ python -m worker_bus ask MANAGER do_something                    # exit 1
MANAGER do_something: ABSENT
  refused under worker_not_registered: No worker 'MANAGER' is registered on this bus.
  Registered: INTELLIGENCE, JOE, LIBRARY, PUBLISHER.

$ python -m worker_bus ask JOE fly_the_truck                       # exit 1
JOE fly_the_truck: ABSENT
  refused under undeclared_capability: JOE does not declare 'fly_the_truck'.
  Declared: answer_question, propose_capture, read_back_load.

$ python -m worker_bus ask JOE read_back_load load_id=NOPE         # exit 1
JOE read_back_load: ABSENT
  refused under subject_not_found: There is no load 'NOPE' on file.
  Joe reads back what is recorded. He does not fill in a gap out loud.
```

**There is deliberately no `--authorized-by` flag**, and a test proves both
halves: passing one is an argument error, and
`ask PUBLISHER assemble_completion_package` — the one capability that requires a
recorded human decision — refuses with `human_authorization_required` and the
remedy *"Record the decision first"*. `CLAUDE.md` §4.3 forbids manufacturing a
Mike attribution "not as a default, not as a seed, not as a test fixture, not as
an inference", and a name typed at an unauthenticated prompt is all four. The
refusal is the feature.

`test_no_command_writes_a_single_row` runs five commands, including two that
refuse, and compares the row-count fingerprint of every table before and after.

**One defect the tests found.** Joe imported `conversation.readback` and
`conversation.capture` at call time with no guard. On a machine without the
conversation layer installed, a driver asking for a read-back got a
`ModuleNotFoundError` traceback. Both imports now return `UNCONFIGURED` with
*"Joe's conversation layer is not installed on this machine"* — a status a
person can act on, not a stack trace. `UNCONFIGURED`, not `UNAVAILABLE`: the
thing is not set up, as opposed to set up and unreachable.

**A second, smaller one.** An empty Library shelf answered `ABSENT` with no
detail and no findings, which on a terminal is one bare word and no reason. The
command now prints the artifacts that came back — `assets: []` — rather than a
sentence the worker never said.

---

## 5. The patch series is what it claims to be

`Dispatch_Corrections/patches/` holds seventeen patches. They were applied with
`git am` to a clean checkout of base `3c03ab2` and the affected tests run there:

- `0001`–`0012` — the Phase 2 series. Step 16 of the evidence run diffs the
  merge plan against the actual commit list; they agree.
- `0013`–`0016` — the Phase 3 series. Applied to the Phase 2 base with `git am`,
  tests run in that checkout: **49 passed**.
- `0017` — brings `CLAUDE.md` §8 up to date with the four above it. Documentation
  only; the figures in it are the ones measured in §1 of this document.

Applying them yourself:

```bash
git checkout -b dispatch/claude-corrections 3c03ab2
git am Dispatch_Corrections/patches/*.patch
python -m pytest -o addopts="" -q
```

`Dispatch_Corrections/verify_manifest.py` checks the package's own file list
against what is on disk and reports CHANGED / MISSING / EXTRA. It has no
dependencies, so it runs on a machine with nothing installed.

### The package was carrying runtime state, and now cannot

Regenerating the manifest for this document is what found it. The file count
jumped from 574 to 708, and the 134 new entries were **memory records written
into the source tree by test runs** — under `Assistant_Plugin/runtime_data/`,
which `.gitignore` describes as holding "the DPAPI-encrypted Microsoft 365 token
cache" and "memory records carrying real driver requests and assistant
responses". Git had them correctly ignored. The manifest walks the filesystem,
and a filesystem walk does not know what "untracked" means.

Checked against what was already built:

```
$ python -c "...count runtime files in the archive..."
129 runtime files in the current archive
```

**The archive already contained them.** 128 memory records and a runtime log,
in the zip written for `D:\Claude-Build`. Nothing was leaked — the package was
never copied anywhere — and that is the only reason this is a finding rather
than an incident.

Three changes:

1. The walk now reads `.gitignore` and honours it, so the rule lives in one
   place instead of being restated in a list that would drift. Only the plain
   forms are supported and negations are dropped, which means an unsupported
   rule can only exclude **more**, never less.
2. `--archive` builds the zip from the manifest's own file list rather than from
   a second walk, so the archive and the checksums cannot describe different
   sets of files again.
3. **11 tests** in `Testing/test_package_excludes_runtime_state.py` pin it,
   including that the guard still packages the program — a packager that ships
   nothing also ships no secrets.

Rebuilt: **452 files, 0 runtime files**, and every file in the archive matches
its manifest hash. `ROOT_MANIFEST.md` carries the byte count, and travels inside
the archive so an unpacked copy can check itself.

---

## 6. CI on the thirteen pull requests

The Phase 2 corrections are open as a thirteen-PR stack against
`jax1313-outlook/Dispatch`, #130 through #142, each based on the one before it
and the first based on `main` at `3c03ab2`.

Checked 2026-09-13 — every branch head's CI run is `completed / success`:

| PR | Branch | Head | CI |
|---|---|---|---|
| 130 | `claude/sqlite-busy-timeout` | `c2d6950` | success |
| 131 | `claude/init-db-once` | `ea521f9` | success |
| 132 | `claude/proof-command-contract` | `c9ff957` | success |
| 133 | `claude/dashboard-rollups` | `0a4c4c2` | success |
| 134 | `claude/atomic-operations` | `e3f3981` | success |
| 135 | `claude/auth-lockout-counters` | `26be9ca` | success |
| 136 | `claude/money-in-cents` | `2e299a3` | success |
| 137 | `claude/backup-activation` | `ac894a6` | success |
| 138 | `claude/provider-neutral-transport` | `a07afba` | success |
| 139 | `claude/delivery-visibility` | `7bea369` | success |
| 140 | `claude/capacity-and-timestamps` | `f5e241c` | success |
| 141 | `claude/branch-coverage` | `0416372` | success |
| 142 | `claude/governance-resolution` | `5fb1b27` | success |

No review threads are open on any of them. They are waiting on Mike, in number
order. #129 is not part of this stack.

**The one CI failure in the series, and what it taught.** #137 failed with
`database is locked` under an eight-thread schema race. The first fix — moving
`busy_timeout` ahead of `journal_mode` — still failed 1 run in 40. The actual
cause is that **`PRAGMA journal_mode` does not honour `busy_timeout`**: SQLite
returns `SQLITE_BUSY` immediately instead of invoking the busy handler.
`_ensure_wal()` reads the current mode first and only sets it when it must, with
a bounded manual retry. 2 failures in 40 became **0 in 150**.

That is recorded because the first fix passed the test suite and was still
wrong, which is the more useful half of the story.

---

## 7. What this evidence does not establish

- **Nothing has run on Mike's laptop.** Not Dispatch, not the launcher, not the
  portal, not the worker bus.
- **No Microsoft call has been made by the M365 layer built here.** Every
  capability in that layer is `UNCONFIGURED`. The adapters are exercised against
  recorded response shapes through injected openers, which proves request shapes,
  paging, delta handling, retry rules and refusals — and proves nothing about
  connectivity. *Corrected 2026-09-13: this line previously read "from any
  repository", which was false. `Assistant_Plugin/proof/EMAIL_LAYER_PROOF.md`
  (2026-08-26, live Outlook Desktop profile) and `RESEARCH_PROOF.md` (2026-08-25,
  8 Copilot attributions) are live Microsoft calls preserved in this repository.
  The most recent record, `COPILOT_LIVE_PROOF.md` (2026-09-12), reads BLOCKED —
  no tenant id, so current connectivity is separately unestablished. See
  `KNOWN_LIMITATIONS.md` §2.*
- **Joe's voice has never heard anything.** The text engines report `SIMULATED`.
- **The benchmark is one container.** 7,786 ms → 47 ms at 2,000 loads was
  measured here. `tests/test_dashboard_scaling.py` pins the *shape* of the
  improvement — constant connection count rather than two per load — because a
  wall-clock assertion on a shared runner tests the runner.
- **The twenty-step proof path runs. It has not been walked.**

Full list: `KNOWN_LIMITATIONS.md`.

---

## 8. Phase A — the walkthrough, and what it found

**Mike authorised this on 2026-09-13: "yes ops@l1truck.com is correct, wire the
real library and start phase A."**

Phase A is everything except delivery: Library → Publisher → COMI → Email Helper
→ a composed message addressed to `ops@l1truck.com`. No tenant, no credentials,
no Microsoft call. It is one script, `Testing/phase_a_walkthrough.py`, and it
uses the real components rather than doubles — the real `LibraryService`, the
real Dispatch store, the real worker bus, the real COMI sanitiser, the real
Email Helper. Run it:

```bash
PYTHONPATH=/path/to/Dispatch python Testing/phase_a_walkthrough.py
```

### It failed twice before it passed

Both failures were in code with passing tests over it. Both were seams between
two components that no test crossed. **This is the sixth and seventh instance of
that pattern in this build**, and it is now the most reliable predictor of where
a defect is: not inside a component, but between two of them.

**Run 1 — step 3.** Two templates were accepted into the Library. Publisher, asked
for one of them by name, answered:

```
  [ABSENT] TEMPLATE_NOT_IN_LIBRARY: Library has no approved template 'TPL-BROKER-CLOSEOUT'.
```

`LibraryService()` builds a fresh `ObjectRegistry` on every call, and
`library_service()` called it every time — so each `build_bus()` held a different
shelf. The template was on one; Publisher was holding another. Fixed: one
Library per process. Pinned by `TestTheLibraryIsOneShelf`.

**Run 2 — step 8.** The message was written, and the transport's own status line
pointed somewhere else:

```
  written to   .../Archive/CIN/Outbox/completion-LOAD-...-ops@l1truck.com.eml
  transport    "SIMULATED -- Archive/Outbox .eml fallback (.../Archive/Outbox)"
```

With nothing configured the writer is not `FileOutboxTransport` at all.
`dispatch.outbound.install()` engages only for Graph and XOAUTH2, so
`cin_lite._send_or_write` runs its own fallback and writes under
`Archive/CIN/Outbox`. `FileOutboxTransport.outbox()` computed its own answer and
was wrong, and `describe()` is the only thing read for the default transport —
so the one sentence an operator has to go on named an empty directory. Both now
ask `cin_lite.email_delivery.outbox_dir()`.

Neither defect changes what Dispatch does. The second changed only what it says,
which is the one thing the transport layer exists to get right.

### What the passing run establishes

| Step | Asked | Answer |
|---|---|---|
| 1 | Two templates into the real Library, accepted by Mike Zachary | Both `CURRENT` v1. `accepted_by="PUBLISHER"` **refused** — "must identify a real human or approved-workflow reviewer, not a system identity" |
| 2 | One complete load: rate confirmation 2850.00 flat / 142 mi, POD, 1 evidence item, 4 milestones | Seeded |
| 3 | `PUBLISHER check_readiness` with `template_id=TPL-BROKER-CLOSEOUT` | `LIVE` — "Ready to assemble" |
| 4 | `assemble_completion_package` with no authorisation | **`ABSENT`**, refused under `human_authorization_required` |
| 4 | Same, after recording the decision as a Dispatch checkpoint milestone and passing `authorized_by="Mike Zachary"`, `authorization_ref="milestone:MS-..."` | `LIVE` — "a draft until a person reviews and submits it", `review_required = True` |
| 5 | COMI `sanitize_payload_for_role(..., "broker")` | Withheld `profit`, `margin_pct`, `total_expenses`, `internal_note`. Passed `load_id`, `revenue`, both locations |
| 6 | Render the Library template with the load's own facts | Real load id, real POD id, real evidence count, real rate |
| 7 | `submit_package(submitted_by="PUBLISHER")` | **Refused** — "cannot be submitted without a real, external, non-system submitted_by identity" |
| 7 | `submit_package(submitted_by="Mike Zachary")` | `SUBMITTED`, one recipient: `ops@l1truck.com` |
| 8 | Open the file | A complete RFC 5322 message, `To: ops@l1truck.com`, correct subject, the rendered template as its body |

Four refusals fired on their own. Each one is a gate that would have to hold on
a real tenant, and each held here without being asked twice.

### What it does not establish

- **No email was delivered to `ops@l1truck.com` or to anyone else.** The
  transport reported `SIMULATED`, `delivering: false`, `simulated: true`. A
  `.eml` on disk is a record that Dispatch *would have* sent something. **Nobody
  received it.** Nothing in this section should be read as a successful send.
- **Nothing ran against Microsoft.** Phase B — `DISPATCH_MS_TENANT`,
  `DISPATCH_MS_CLIENT_ID`, `DISPATCH_EMAIL_FROM`, `DISPATCH_TRANSPORT=graph`,
  then a device-code sign-in — is Mike's to start and has not been started.
- **The Library forgot everything when the script exited.** See
  `KNOWN_LIMITATIONS.md` §14.
- **One load, one template, one lane.** A walkthrough is not a test suite.

---

## 9. Reproducing all of it

```bash
# Sandbox
cd D:\Claude-Build\Joe-Assistant
python -m pytest                              # 738 passed, 12 skipped

# Dispatch, patched
git checkout -b dispatch/claude-corrections 3c03ab2
git am Dispatch_Corrections/patches/*.patch
python -m pytest -o addopts="" -q             # 4221 passed
python -m pytest -o addopts="" -q --cov --cov-config=.coveragerc   # 91.48%

# The package itself
python Dispatch_Corrections/verify_manifest.py

# Phase A, end to end (§8)
PYTHONPATH=/path/to/Dispatch python Testing/phase_a_walkthrough.py
```
