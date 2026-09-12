# Rollback plan

The series is twelve commits, ordered so the suite is green after every one. That
ordering exists for this document: a series that only works as a block cannot be
partially reverted when one piece turns out wrong on Mike's machine.

---

## The general case

```bash
git revert --no-commit <sha>
python -m pytest -o addopts="" -q
git commit
```

Ten of the twelve revert cleanly with no data consequence. Two do not, and they
are §3 and §4 below.

**Take a backup first.** Commit 7 is what makes that possible from a menu, which
is a reason to merge it early (see `MERGE_PLAN.md`).

## 1 · Reverting the whole series

The database is the question, not the code. After a full revert:

| Added by the series | After a code-only revert |
|---|---|
| `schema_state` | orphaned. Harmless — the old `_init_db()` does not read it. |
| `auth_attempt_state` | orphaned. **Lockout state is lost** — see §3. |
| `<col>_cents` generated columns | **must be dropped** — see below. |
| `delivery_attempts` | orphaned. The record of failed sends survives; nothing reads it. |
| `capacity_profiles` | orphaned. Harmless. |

### The one that must be dropped

Generated columns appear in `SELECT *`. Commit 6 added `_model_kwargs()` to
filter them before a dataclass constructor; reverting removes the filter and
leaves the columns, so the **next `SELECT *` into a dataclass raises
`TypeError`**.

```sql
ALTER TABLE rate_confirmations    DROP COLUMN rate_amount_cents;
ALTER TABLE expenses              DROP COLUMN amount_cents;
ALTER TABLE settlements           DROP COLUMN invoice_amount_cents;
ALTER TABLE settlements           DROP COLUMN payment_amount_cents;
ALTER TABLE settlements           DROP COLUMN factoring_fee_cents;
ALTER TABLE detention_events      DROP COLUMN hourly_rate_cents;
ALTER TABLE ifta_fuel_purchases   DROP COLUMN amount_cents;
ALTER TABLE driver_pay            DROP COLUMN amount_cents;
ALTER TABLE driver_pay            DROP COLUMN rate_cents;
ALTER TABLE maintenance_schedules DROP COLUMN cost_estimate_cents;
```

**No money is lost by this.** The generated columns were never the storage — the
`REAL` columns are, and they were never modified. Dropping a derived view of a
value that never changed costs nothing.

## 2 · Reverting one commit

| Commit | Revert these first | Notes |
|---|---|---|
| 1 proof path | — | Restores three invalid command strings, so `tests/test_proof_command_contract.py` then **fails** — correctly. Revert that test too, or do not revert this. |
| 2 connection management | 3, 4, 9 | — |
| 3 dashboard rollups | — | Clean. `/home` returns to O(n). |
| 4 atomicity | 9 | Clean. Partial writes become possible again. |
| 5 lockout counters | — | **See §3.** |
| 6 money | — | Clean *after* the DROP COLUMN above. |
| 7 backup | — | Clean. Purely additive; no data. |
| 8 transport | — | Clean. Inert unless configured. |
| 9 delivery record | — | Clean. `delivery_attempts` is left behind, which is the right way round: the record of what failed outlives the code that wrote it. |
| 10 capacity + timestamps | — | Code reverts clean; **stored values do not** — see §4. |
| 11 coverage gate | — | Clean. Back to line-only over three packages. |
| 12 governance pointer | — | Clean. One file and a log entry. |

## 3 · Commit 5 — lockout counters

Reverting restores the JSON counter and orphans `auth_attempt_state`.

**PIN hashes never moved**, so no credential is lost. What is lost is **lockout
state**: anybody currently locked out becomes unlocked and every failure count
resets to zero.

On a single-operator system that is an inconvenience. It is written down because
a silent security-state reset is exactly what a revert should not do quietly.

```sql
-- Before reverting, record who is affected:
SELECT subject_kind, subject_id, failed_attempt_count, locked_until
  FROM auth_attempt_state WHERE locked_until IS NOT NULL;
```

## 4 · Commit 10 — appointment timestamps

After this commit, `create_load()` and `update_load()` store an offset-carrying
value: `"2026-09-14 08:00"` → `"2026-09-14T08:00:00-04:00"`.

Reverting stops the normalisation. It does **not** rewrite values already stored,
so the table holds a mixture — and the mixture is mostly safe:

- `capacity.parse_operational_timestamp` reads an offset-carrying value correctly
  (naive ones are what it refuses);
- pre-existing readers take `value[:10]`, which is unchanged;
- **but** `portal/models/conflict.py` reverts to its own parser, which has no
  offset format and reads the normalised values as `None` — so
  **booking-conflict detection silently stops working for every load created
  since the commit.**

That last point is the reason to be careful. If commit 10 must come out, either
revert `portal/models/conflict.py` separately — keeping the shared parser — or
accept that conflict detection is off and say so.

**This is the commit worth not reverting.** It is what makes the capacity engine
usable at all: the engine refuses a naive timestamp, correctly, and the form was
producing naive timestamps.

### If the values must be un-normalised

```sql
-- Reduces every appointment to its naive local form. Lossy, and the ambiguity
-- it restores is the defect. Only if something downstream demands it.
UPDATE loads SET pickup_datetime   = replace(substr(pickup_datetime, 1, 16), 'T', ' ')
  WHERE pickup_datetime LIKE '____-__-__T__:__%';
UPDATE loads SET delivery_datetime = replace(substr(delivery_datetime, 1, 16), 'T', ' ')
  WHERE delivery_datetime LIKE '____-__-__T__:__%';
```

## 5 · If the database is the problem, not the code

Restore, rather than repairing forward:

```bash
python scripts/dispatch_backup.py restore <archive> "D:\Restore Proof"
```

`restore` recomputes every hash in the archive before writing anything and
refuses on a mismatch. It also repoints stored absolute file paths at the
restored copies, so evidence links work after a restore to a different drive —
the case a hand-copied folder gets wrong.

## 6 · Rolling back the sandbox work

Nothing in `Joe-Assistant` is wired into Dispatch. `Governance/`, `Workers/` and
`Assistant_Plugin/m365/` are additive packages with their own tests, and deleting
any of them affects nothing else. One exception: `conftest.py` and `pytest.ini` at
the repository root make the three suites runnable in one command, and removing
them returns the repository to three directories and three commands.
