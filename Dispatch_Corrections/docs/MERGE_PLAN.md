# Merge plan — production Dispatch

**Nothing here has been merged, pushed, or opened as a pull request against
`jax1313-outlook/Dispatch`.** The series exists as patches in
`Dispatch_Corrections/patches/`.

Base: `3c03ab2` — *"Merge pull request #127 from
jax1313-outlook/remove-broker-trust-scoring"*, the tip of `main` at the time this
work began.

---

## The series

Twelve commits, ordered so each one is independently reviewable and the suite is
green after every single one. That ordering is the whole plan: a series that only
works as a block cannot be reviewed, and cannot be partially reverted when one
piece turns out to be wrong on Mike's machine.

| # | Commit | Depends on | Risk | Revert |
|---|---|---|---|---|
| 1 | Repair the operational proof path | — | **Low** | Clean. Adds a subcommand and two tests; changes three strings. |
| 2 | Build the schema once per process, wait for a lock, allow a unit of work | — | **Medium** | Clean, but 3 and 7 sit on it. |
| 3 | Replace the dashboard's per-load queries with two rollups | 2 | Low | Clean. |
| 4 | Make multi-step service operations atomic | 2 | **Medium** | Clean. Behaviour change: partial writes stop happening. |
| 5 | Move the PIN lockout counters where a transaction protects them | 2 | **Medium** | **Not clean** — see below. |
| 6 | Money becomes whole cents | 2 | Low | Clean. Generated columns can be dropped; the REAL columns never changed. |
| 7 | Give the operator a way to take a backup, and to prove one | — | Low | Clean. Purely additive. |
| 8 | Provider-neutral transport with Microsoft-compatible auth | — | Low | Clean. Inert unless configured. |
| 9 | Record every outbound attempt, log it, bound the log | 2, 4 | Low | Clean. |
| 10 | Wire the capacity engine; make appointment times readable | 2, 6 | **Medium-high** | Clean in code; **stored values change** — see below. |
| 11 | Measure branch coverage, and measure the launcher | all | Low | Clean. |
| 12 | Governance pointer for the production repository | — | **Low** | Clean. One file. |

## Recommended order, in three merges

**Merge A — the safe half (1, 7, 8, 11, 12).** Independently useful, nothing
depends on them, every one revertible in isolation. Merging this first means the
proof path runs and a backup can be taken *before* anything about the data layer
changes — which is the correct order for a system whose backup has never been
exercised.

**Merge B — the data layer (2, 3, 4, 6, 9).** One merge, because 3, 4 and 9 all
rest on 2 and splitting them leaves the tree in a state no commit represents.
Take a backup first (Merge A makes that possible), and prove a restore first.

**Merge C — capacity and timestamps (5, 10).** Last, because 10 changes values
that are already stored and 5 changes where a security counter lives. Both want
their own attention.

## The two that are not a clean revert

### Commit 5 — lockout counters

Reverting restores the JSON counter, and the `auth_attempt_state` rows are
orphaned. The consequence is a **reset lockout state**, not lost credentials —
PIN hashes never moved. A driver who was locked out becomes unlocked. On a
single-operator system that is an inconvenience; it is stated because a silent
security-state reset is exactly the kind of thing a revert should not do
quietly.

*Before reverting:* note whether anybody is currently locked out
(`SELECT * FROM auth_attempt_state WHERE locked_until IS NOT NULL`).

### Commit 10 — appointment timestamps

`create_load()` and `update_load()` now store an offset-carrying value:
`"2026-09-14 08:00"` becomes `"2026-09-14T08:00:00-04:00"`. Reverting stops the
normalisation; it does not rewrite stored values back.

The result is a mixture, and the mixture is **safe**: `dispatch/timestamps.py`
and `capacity.parse_operational_timestamp` both read an offset-carrying value
correctly, and the pre-existing readers took the first ten characters, which are
unchanged. Nothing breaks; new loads simply go back to being ambiguous.

*This one is worth not reverting.* It is the commit that makes the capacity
engine usable at all.

## Applying the series

```bash
git checkout -b dispatch/phase-2-corrections 3c03ab2
git am Dispatch_Corrections/patches/*.patch
python -m pytest -o addopts="" -q
python -m pytest -o addopts="" -q --cov --cov-config=.coveragerc
```

Expected: **4,171 passed**, gated branch coverage **91.39%** over four packages.

## Schema changes, and why none of them needs a migration window

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
results, which is why commit 6 also adds `_model_kwargs()`; **an older build will
raise `TypeError` on a `SELECT *` into a dataclass.** Do not run an old build
against an upgraded database.

## What must happen on Mike's machine before any of this is "proven"

The suite is evidence of software behaviour. It is never operational proof.

1. `python -m dispatch_launcher backup` — take one.
2. `python -m dispatch_launcher prove-restore --confirmed-by "Mike"` — restore it,
   open the restored copy, confirm it works, and record that.
3. Walk the twenty-step proof path. Steps 18, 19 and 20 now run.
4. Enter one load through the portal and confirm it appears on the calendar and
   produces a capacity assessment rather than a blocking finding.
