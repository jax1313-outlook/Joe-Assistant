# Database migration plan

`SCHEMA_REVISION` moves **1 → 5**. Every change is additive, applied by
`_init_db()` on the first connection after the upgrade, and **no table is
rewritten**. There is no migration window: the upgrade is instant on a database
of any size.

---

## What changes

| Rev | Change | Rows touched | Reversible |
|---|---|---|---|
| 1 | `schema_state` — the stamp that lets a connection skip the build | 0 | drop the table |
| 2 | `auth_attempt_state` — lockout counters | 0; counts start at zero | drop the table (**see §3**) |
| 3 | Generated `<col>_cents` on 7 tables, 10 columns | **0 — computed, never stored** | `DROP COLUMN` (**required on revert**) |
| 4 | `delivery_attempts` | 0 | drop the table |
| 5 | `capacity_profiles` | 0 | drop the table |

## 1 · The stamp

```sql
CREATE TABLE schema_state (id INTEGER PRIMARY KEY CHECK (id = 1),
                           revision INTEGER NOT NULL, stamped_at TEXT NOT NULL);
```

Read once per connection so the full schema build can be skipped. Three layers,
cheapest first: an in-process set, then this single-row read (for the case where
another process built the file since this one started), then the full build.

## 2 · Money, by generated column

```sql
ALTER TABLE expenses ADD COLUMN amount_cents INTEGER
  GENERATED ALWAYS AS (CAST(ROUND(amount * 100) AS INTEGER)) VIRTUAL;
```

Ten columns across seven tables: `rate_confirmations`, `expenses`, `settlements`
(×3), `detention_events`, `ifta_fuel_purchases`, `driver_pay` (×2),
`maintenance_schedules`.

**Why this rather than a backfill.** A generated column is computed by SQLite on
read. There is no write path to forget, no trigger to mis-order, no backfill that
can be interrupted half way, and no window in which the two disagree. Adding it
is pure DDL — no rows are rewritten, so it is instant on a large table.

**Why deriving cents loses nothing.** A double represents any 2-decimal amount to
far better than half a cent, so `ROUND(amount * 100)` returns the cent the
operator actually typed. Float drift is a property of **accumulation**, not of a
single stored value — which is why the fix is that every sum, product and
comparison now runs in cents.

**The `REAL` columns stay**, unchanged, so every existing reader is untouched.
One value with two views, never two values. When the last reader of a `REAL`
column is gone, the generated column can be materialised and the `REAL` one
dropped.

**Compatibility note that matters.** Generated columns **appear in `SELECT *`**.
Commit 6 adds `store._model_kwargs()` to filter them before a dataclass
constructor. **An older build of Dispatch will raise `TypeError` on a `SELECT *`
into a dataclass against an upgraded database.** Do not run an old build against
one.

**SQLite requirement:** 3.31+ (2020). Python 3.11 ships 3.34+. A database on an
older library falls back to computing cents in Python at the point of use —
slower, same answer — rather than failing to start, because refusing to run is a
worse outcome than a slow report on a machine that is otherwise fine.

**Verification:** `/maintenance` → *Stored money* shows `10 of 10` covered and
lists any amount that was never a whole number of cents. Those are **reported,
never corrected** — which way `10.007` should go is a decision about somebody's
invoice.

## 3 · Lockout counters

```sql
CREATE TABLE auth_attempt_state (
    subject_kind TEXT, subject_id TEXT,
    failed_attempt_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT, last_failure_at TEXT, last_success_at TEXT,
    updated_at TEXT NOT NULL, PRIMARY KEY (subject_kind, subject_id));
```

**No data migration.** The old JSON counters are left in place and simply stop
being read; `_public()` reads the two fields back from here, so every caller sees
the shape it always did. Counts start at zero, which means **a lockout in force
at the moment of upgrade is cleared**.

On a single-operator system that is an inconvenience. It is written down because
a silent security-state reset is exactly what an upgrade should not do quietly.

**PIN hashes and recovery words do not move.** Only the contended field did.

## 4 · Delivery attempts

```sql
CREATE TABLE delivery_attempts (attempt_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
    subject_ref TEXT, recipient TEXT, summary TEXT, transport TEXT,
    status TEXT NOT NULL DEFAULT 'QUEUED', attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT, receipt TEXT, next_retry_at TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX idx_delivery_status  ON delivery_attempts(status);
CREATE INDEX idx_delivery_subject ON delivery_attempts(subject_ref);
```

Starts empty. **Nothing is backfilled**, and nothing could be: the sends that
failed before this existed left one line on stderr and no record, which is the
defect.

## 5 · Capacity profiles

```sql
CREATE TABLE capacity_profiles (equipment_id TEXT PRIMARY KEY,
    capacity_id TEXT NOT NULL, driver_id TEXT,
    physical TEXT, time_capacity TEXT, position TEXT, reserve TEXT, cargo TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
```

Starts empty, and every truck reports `UNCONFIGURED` until Mike records one.
**Deliberate** — assuming a 53-foot dry van is how freight gets accepted onto a
trailer that cannot carry it.

Sections are JSON because they are a document: nothing queries inside them, and a
column per field would be forty columns that change whenever the engine grows
one. Hydration ignores unknown keys and tolerates unreadable JSON, because a
profile that cannot be read is a truck that silently stops being assessable.

**Utilization is not persisted.** `used_weight_lbs` describes what is on a
trailer now; a saved one comes back as a claim about today made from last week's
freight.

## Appointment values (not schema, but stored data)

`create_load()` and `update_load()` now record an offset-carrying value:
`"2026-09-14 08:00"` → `"2026-09-14T08:00:00-04:00"`, using
`DISPATCH_OPERATING_TIMEZONE`.

**No existing row is rewritten.** New and updated loads carry the offset; older
rows stay exactly as they were, and both are read correctly — the day is derived
by parsing rather than by slicing the string.

**Set the timezone before the first load is entered.** It defaults to
`America/New_York`; if that is wrong, every appointment entered after the upgrade
is wrong by the difference.

## Upgrading, and going back

```bash
# Upgrade: nothing to run. Start Dispatch; the first connection applies it.
python -m dispatch_launcher backup     # do this first, every time
python -m dispatch_launcher start
```

Going back is in `ROLLBACK_PLAN.md`. The one step that is not optional is
dropping the generated columns — see §2.
