# Verification plan — what to check, in what order, and what it proves

Ordered so a failure stops the next step rather than being discovered after it.
Each item says what a pass actually establishes, because several of them
establish less than they appear to.

---

## Phase 1 · In the repository, before anything is merged

| # | Check | Command | A pass means |
|---|---|---|---|
| 1 | The series applies to a clean checkout | `git checkout -b v 3c03ab2 && git am Dispatch_Corrections/patches/*.patch` | The patches are coherent against `main`. Nothing about behaviour. |
| 2 | The suite | `python -m pytest -o addopts="" -q` | **4,171 passed.** Software behaviour only — never operational proof. |
| 3 | The gate | `python -m pytest -o addopts="" -q --cov --cov-config=.coveragerc` | **≥ 90%** branch coverage over four packages. |
| 4 | Every scripted proof command parses | `python -m pytest tests/test_proof_command_contract.py` | Steps 18–20 are commands the programs accept. This is the check that was missing. |
| 5 | Governance drift | `python -m dispatch_governance check <workspace>` | Exit 0 once the two pointers are placed. Currently **2 BLOCKING**, correctly. |
| 6 | Sandbox suites | `python -m pytest -o addopts="" -q` in `Joe-Assistant` | **681 passed**, 12 skipped (Tk, stated). |

**What phase 1 does not establish:** anything about Mike's machine. `CLAUDE.md`
§6 — the suite is evidence of software behaviour and is never operational proof.

## Phase 2 · On the laptop, before a real load

| # | Check | How | A pass means |
|---|---|---|---|
| 7 | It starts | `DISPATCH_START_HERE.cmd` | The launcher runs on Windows. |
| 8 | The schema upgrades | open any page | `SCHEMA_REVISION` 1 → 5 applied. Additive only; no table rewritten. |
| 9 | A backup can be taken | launcher → `[B] Back Up Now` | An archive exists. **Not** that it can be restored. |
| 10 | The archive is intact | `dispatch_backup.py verify <archive>` | Every hash matches. **Not** that it restores. |
| 11 | It restores | launcher → `[R] Prove a Restore` | It restored into an isolated destination and every hash matched. Status stays **UNVERIFIED** — correctly. |
| 12 | The restored copy works | open it, look at it | Only now: `prove-restore --confirmed-by "Mike"` → **VERIFIED**. |

Steps 9–12 are the sequence the previous state of the repository could not
perform at all.

## Phase 3 · One real load, end to end

| # | Check | Watch for |
|---|---|---|
| 13 | Create a load, typing the appointment the way you normally would | It appears **on the calendar**. Before this work, `9/14/2026 08:00` silently did not. |
| 14 | Look at the load page | Times read `tomorrow at 14:00`, not `2026-09-14T14:00:00-04:00`. |
| 15 | Record a capacity profile for the truck | The panel moves from `UNCONFIGURED` to an assessment. Before: `UNCONFIGURED` forever, because nothing could store a profile. |
| 16 | Assign the truck | A capacity finding, not a `TIMESTAMP_NAIVE` blocking refusal. |
| 17 | Walk the twenty-step proof | Steps 18, 19, 20 **run**. |

## Phase 4 · Money, once there are real figures

| # | Check | How |
|---|---|---|
| 18 | Totals are exact | `/maintenance` → *Stored money*: 10 of 10 columns covered, no fractional-cent findings. |
| 19 | Two reports agree | The financial dashboard total and the sum of the chart's monthly revenue, to the cent. |
| 20 | An IFTA quarter | Compare the computed tax against the same arithmetic done on paper. |

## Phase 5 · Microsoft, if and when it is connected

| # | Check | A pass means |
|---|---|---|
| 21 | `connect-microsoft` | The token exchange worked. **Not** that anything was delivered. |
| 22 | `transports` | `LIVE -- Microsoft Graph as <address>`. |
| 23 | Send one real message | Look in **Sent Items**. This is the first thing that proves delivery. |
| 24 | `/maintenance` → Outbound messages | Zero needing attention after a real send. |

Until 23, every Microsoft capability is `UNVERIFIED` however green anything else is.

## Phase 6 · The things that should fail

A check that cannot fail proves nothing. Each of these **should** fail, and the
suite asserts each one:

| What | Expected |
|---|---|
| Change an evidence file's bytes, run `dispatch_proof.py verify` | **exit 1**, naming the file. Run for real in the evidence report. |
| Fire 12 concurrent wrong PINs | The card **locks**. It did not before. |
| Break a store call mid-operation | The whole operation rolls back. |
| Take the SMTP host away and complete a load | `/home` shows messages that reached nobody. |
| Ask Joe to record something half-heard | He says nothing. |
| Ask a worker to approve something | Refused: `reserved_identity_cannot_authorize`. |
| Point `dispatch_governance check` at a worker repository with no pointer | **BLOCKING**. |

## What is still not proven after all of it

- Dispatch has never run on Mike's Windows laptop.
- No Microsoft call has been made from any repository.
- The capacity engine's stop-sequence and appointment-window paths have no
  production caller.
- Eleven JSON stores still lose a concurrent update.
