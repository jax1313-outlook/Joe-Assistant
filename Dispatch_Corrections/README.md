# Dispatch corrections — the merge package

A twelve-commit series against `jax1313-outlook/Dispatch@3c03ab2`, the ten
accepted Phase 1 recommendations plus ten defects found while implementing them.

**Production Dispatch was read-only throughout.** Nothing was written to it,
pushed to it, or opened against it. The series lives here as patches.

---

## Verified, not asserted

The series was applied to a **freshly cloned checkout at `3c03ab2`** and the
suite was run there:

```
$ git checkout -b verify 3c03ab2
$ git am Dispatch_Corrections/patches/*.patch
$ python -m pytest -o addopts="" -q
4171 passed in 323.01s
```

`evidence/COMPLETION_EVIDENCE.md` is the output of `collect_evidence.py` against
that same checkout — real commands, real exit codes, verbatim output.

## Read in this order

| Document | What it answers |
|---|---|
| `docs/IMPLEMENTATION_SUMMARY.md` | What was done, and what the numbers are |
| `docs/ARCHITECTURAL_DECISIONS.md` | Seventeen ADRs — every decision the mission left open, what it was decided from, and what was rejected |
| `docs/MERGE_PLAN.md` | The twelve commits, three merges, and the two that are not a clean revert |
| `docs/MIGRATION_PLAN.md` | `SCHEMA_REVISION` 1 → 5, all additive, no migration window |
| `docs/ROLLBACK_PLAN.md` | How to undo each one, and what it costs |
| `docs/VERIFICATION_PLAN.md` | What to check, in what order, and what each pass actually proves |
| `docs/SECURITY_FINDINGS.md` | Ten findings, what an attacker gets, what was fixed |
| `docs/KNOWN_LIMITATIONS.md` | Twelve things not claimed |
| `docs/EXTERNAL_ACTIVATION.md` | Nine things only Mike can do |
| `docs/WORKER_CONTRACTS.md` | Intelligence, Publisher, Joe — the boundary and what the bus refuses |
| `docs/JOE_IMPLEMENTATION.md` | Reasoning and voice, and the line neither crosses |
| `../docs/M365_ACTIVATION.md` | Microsoft, and what has to be true before anything is `LIVE` |
| `../Governance/GOVERNANCE_RESOLUTION_v1.md` | The constitutional fork, and how it closes |
| `evidence/COMPLETION_EVIDENCE.md` | The sixteen completion-evidence items, run |

## The series

| # | Commit | What it fixes |
|---|---|---|
| 1 | Repair the operational proof path | All three Code-automated steps were rejected by their own parsers |
| 2 | Build the schema once, wait for a lock, allow a unit of work | 1.22 ms of DDL per connection; no `busy_timeout`; nothing could span two writes |
| 3 | Replace the dashboard's per-load queries with two rollups | `/home` was 7,786 ms at 2,000 loads and growing |
| 4 | Make multi-step service operations atomic | Sixteen operations could half-complete with no rollback |
| 5 | Move the PIN lockout counters where a transaction protects them | 12 concurrent failures recorded as 1; the lockout never tripped |
| 6 | Money becomes whole cents | Every monetary column was `REAL`; `Decimal` appeared nowhere |
| 7 | Give the operator a way to take a backup, and to prove one | 926 lines of backup engine, reachable from nothing |
| 8 | Provider-neutral transport with Microsoft-compatible auth | No HTTP client in the connector layer; both chosen auth methods are being closed |
| 9 | Record every outbound attempt, log it, bound the log | A failed broker email produced one line on stderr and nothing else |
| 10 | Wire the capacity engine; make appointment times readable | 1,861 lines with no production caller, and a form producing input it refuses |
| 11 | Measure branch coverage, and measure the launcher | The gate was line-only and excluded the thing that starts the product |
| 12 | Record what governs, and adjudicate the Manager contradiction | Five constitutions, two versions, one of them forbidden in CI |

## Running the evidence yourself

```bash
python Dispatch_Corrections/collect_evidence.py --dispatch /path/to/patched/Dispatch
```

Sixteen items. It runs the suite, the coverage gate, the repaired proof commands
against a real load, the benchmark, a real backup, a real restore, the failure
injections, the concurrency tests, a secret scan, and a diff check — and writes
what happened.

It also runs the **negative** case for proof step 18: it changes the bytes under
an evidence file, leaving the record perfect, and asserts the step **fails**. A
check that cannot fail proves nothing.
