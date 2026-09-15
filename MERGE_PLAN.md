# Merge plan — production Dispatch

Base: `3c03ab2` — *"Merge pull request #127 from
jax1313-outlook/remove-broker-trust-scoring"*, the tip of `main` when this work
began.

The series exists in two forms, and they are **not** the same set:

| Form | What is in it | State |
|---|---|---|
| Pull requests **#130–#142** | the twelve Phase 2 corrections, split into thirteen reviewable PRs | **open** against `jax1313-outlook/Dispatch`, CI green on every one, no review threads |
| Patches `0001`–`0017` in `Dispatch_Corrections/patches/` | the same twelve, **plus** the five Phase 3 corrections | held here; **not pushed, not opened as a PR** |

So: Phase 2 is in front of Mike. Phase 3 is not, and merging the PRs does not
bring it. `git am` the last five patches, or ask for them as PRs.

Baseline for comparison, measured rather than quoted:

| | `main` at `3c03ab2` | after `0001`–`0012` | after `0013`–`0017` |
|---|---|---|---|
| Suite | 3,696 | 4,171 | **4,221** |
| Gated coverage | 94.74% **line**, 3 packages, launcher exempt | 91.39% **branch**, 4 packages | **91.48%** branch, 4 packages |

The coverage figure goes *down* and the gate gets stronger. Line coverage counts
an `if` whose false path never runs as covered, and the false paths are where
the refusals live. `dispatch_launcher/` is also no longer outside the
measurement. The two numbers do not compare and should not be compared.

---

## The thirteen open pull requests

Each is based on the one above it. The first is based on `main`. They merge in
number order; merging one out of order rebases the rest.

| PR | Branch | What it does | Patch | Risk | Revert |
|---|---|---|---|---|---|
| 130 | `claude/sqlite-busy-timeout` | Wait for a write lock instead of failing on it | `0002` (part) | Low | Clean. |
| 131 | `claude/init-db-once` | Build the schema once per process, not once per connection | `0002` (part) | **Medium** | Clean, but most of the stack sits on it. |
| 132 | `claude/proof-command-contract` | Repair the operational proof path and make it executable | `0001` | **Low** | Clean. Adds a subcommand and two tests; changes three strings. |
| 133 | `claude/dashboard-rollups` | Replace the dashboard's per-load queries with two rollups | `0003` | Low | Clean. |
| 134 | `claude/atomic-operations` | Make multi-step service operations atomic, defer their emails | `0004` | **Medium** | Clean. Behaviour change: partial writes stop happening. |
| 135 | `claude/auth-lockout-counters` | Move the PIN lockout counters where a transaction protects them | `0005` | **Medium** | **Not clean** — see below. |
| 136 | `claude/money-in-cents` | Money becomes whole cents | `0006` | Low | Clean. Generated columns can be dropped; the REAL columns never changed. |
| 137 | `claude/backup-activation` | A way to take a backup, and to prove one restores | `0007` | Low | Clean. Purely additive. |
| 138 | `claude/provider-neutral-transport` | Provider-neutral transport with Microsoft-compatible auth | `0008` | Low | Clean. Inert unless configured. |
| 139 | `claude/delivery-visibility` | Record every outbound attempt, log it, bound the log | `0009` | Low | Clean. |
| 140 | `claude/capacity-and-timestamps` | Wire the capacity engine; compare instants, not wall clocks | `0010` | **Medium-high** | Clean in code; **stored values change** — see below. |
| 141 | `claude/branch-coverage` | Measure branch coverage, and measure the launcher | `0011` | Low | Clean. |
| 142 | `claude/governance-resolution` | Record what governs this repository; adjudicate the Manager contradiction | `0012` | **Low** | Clean. Documentation only. |

Patch `0002` is two PRs because the busy-timeout fix and the schema-once fix are
independently revertible and one of them is far riskier than the other. That
ordering is the whole plan: a series that only works as a block cannot be
reviewed, and cannot be partially reverted when one piece turns out to be wrong
on Mike's machine.

### Recommended order, in three merges

**Merge A — the safe half (132, 137, 138, 141, 142).** Independently useful,
nothing depends on them, every one revertible in isolation. Merging this first
means the proof path runs and a backup can be taken *before* anything about the
data layer changes — the correct order for a system whose backup has never been
exercised.

**Merge B — the data layer (130, 131, 133, 134, 136, 139).** One merge, because
133, 134 and 139 all rest on 131 and splitting them leaves the tree in a state
no commit represents. Take a backup first (Merge A makes that possible), and
prove a restore first.

**Merge C — capacity and timestamps (135, 140).** Last, because 140 changes
values that are already stored and 135 changes where a security counter lives.
Both want their own attention.

Because the PRs are stacked, GitHub will want them in number order regardless.
The three groupings are about *when to stop and look*, not about re-ordering the
merges.

---

## The five Phase 3 patches, which are not PRs

| Patch | What it does | Depends on |
|---|---|---|
| `0013` | Build capacity stops from real loads, and refuse to invent the rest | `0010` |
| `0014` | Stop the JSON stores losing a concurrent update | — |
| `0015` | Take the transit distance from the rate confirmation | `0013` |
| `0016` | Pin the capacity assessment as advisory, per doctrine found afterwards | `0013`, `0015` |
| `0017` | Bring `CLAUDE.md` §8 up to date with the four above it | `0013`–`0016` |

`0013` is the one that matters: without it, the capacity engine's stop-sequence
and appointment checks remain unreachable code with passing unit tests, which is
the state `0010` leaves them in. **Merging PR #140 without `0013` ships the
wiring and not the thing it wires.**

---

## The two that are not a clean revert

### PR #135 — lockout counters

Reverting restores the JSON counter, and the `auth_attempt_state` rows are
orphaned. The consequence is a **reset lockout state**, not lost credentials —
PIN hashes never moved. A driver who was locked out becomes unlocked. On a
single-operator system that is an inconvenience; it is stated because a silent
security-state reset is exactly the kind of thing a revert should not do
quietly.

*Before reverting:* note whether anybody is currently locked out
(`SELECT * FROM auth_attempt_state WHERE locked_until IS NOT NULL`).

### PR #140 — appointment timestamps

`create_load()` and `update_load()` now store an offset-carrying value:
`"2026-09-14 08:00"` becomes `"2026-09-14T08:00:00-04:00"`. Reverting stops the
normalisation; it does not rewrite stored values back.

The result is a mixture, and the mixture is **safe**: `dispatch/timestamps.py`
and `capacity.parse_operational_timestamp` both read an offset-carrying value
correctly, and the pre-existing readers took the first ten characters, which are
unchanged. Nothing breaks; new loads simply go back to being ambiguous.

*This one is worth not reverting.* It is the commit that makes the capacity
engine usable at all.

---

## Applying the whole series without GitHub

```bash
git checkout -b dispatch/claude-corrections 3c03ab2
git am Dispatch_Corrections/patches/*.patch
python -m pytest -o addopts="" -q
python -m pytest -o addopts="" -q --cov --cov-config=.coveragerc
python Dispatch_Corrections/verify_manifest.py
```

Expected: **4,221 passed**, gated branch coverage **91.48%** over four packages.

---

## Schema changes, and why none needs a migration window

`SCHEMA_REVISION` moves 1 → 5. Every change is additive and applied by
`_init_db()` on the first connection after the upgrade:

| Revision | Change | Effect on existing rows |
|---|---|---|
| 1 | `schema_state` stamp table | none |
| 2 | `auth_attempt_state` | none; counters start at zero |
| 3 | Generated `<col>_cents` columns on 7 tables | **none** — computed, not stored |
| 4 | `delivery_attempts` | none |
| 5 | `capacity_profiles` | none |

No table is rewritten and no column is dropped, so the upgrade is instant on a
database of any size and a downgrade loses only the new tables.

**Backwards compatibility one way only.** An *older* Dispatch opening an upgraded
database works — it ignores tables it does not know — except that
`_schema_is_current()` will not exist to read the stamp, so it re-runs its own
`_init_db()`, which is idempotent. Generated columns appear in its `SELECT *`
results, which is why PR #136 also adds `_model_kwargs()`; **an older build will
raise `TypeError` on a `SELECT *` into a dataclass.** Do not run an old build
against an upgraded database.

---

## What must happen on Mike's machine before any of this is "proven"

The suite is evidence of software behaviour. It is never operational proof.

1. `python -m dispatch_launcher backup` — take one.
2. `python -m dispatch_launcher prove-restore --confirmed-by "Mike"` — restore
   it, open the restored copy, confirm it works, and record that.
3. Walk the twenty-step proof path. Steps 18, 19 and 20 now run.
4. Enter one load through the portal and confirm it appears on the calendar and
   produces a capacity assessment rather than a blocking finding.
