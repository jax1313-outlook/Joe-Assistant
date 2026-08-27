# Workstream 2 - Assistant Memory - Architecture

**Component:** Assistant Memory
**Version:** 1.0.0

---

## 1. Shape

```
      +-----------------------------------+
      |              cli.py               |  operator surface, rendering
      +-----------------+-----------------+
                        |
                        v
      +-----------------------------------+
      |          retention.py             |  THE ONLY MODULE THAT DECIDES
      |  create / apply / sweep           |  lifecycle rules, transitions
      +----+----------------+---------+---+
           |                |         |
           v                v         v
   +-------------+   +------------+  +-----------+
   |  record.py  |   |  store.py  |  | clock.py  |
   |  states,    |   |  JSON per  |  | real and  |
   |  levels,    |   |  record,   |  | simulated |
   |  purging    |   | containment|  |   time    |
   +-------------+   +------------+  +-----------+
```

Dependency direction is one way. `clock` and `record` know nothing about the
store or the engine, so each is testable alone.

## 2. Modules

| Module | Responsibility | Tests |
| --- | --- | --- |
| `clock.py` | Every time reading. `SystemClock` for real use, `FixedClock` for simulating elapsed time. | via expiration tests |
| `record.py` | `MemoryRecord`, `RetentionState`, `InteractionLevel`, state and level ranking, content purging. | 6 |
| `store.py` | JSON-per-record store. Active / expired / deleted buckets. Folder containment enforcement. | 6 |
| `retention.py` | Lifecycle rules: creation, the five operations, the expiration sweep. | 26 |
| `cli.py` | Operator surface: commands, rendering, boundary self-check. | exercised manually |

**Third-party dependencies: zero.** Imports across the package are
`__future__`, `argparse`, `dataclasses`, `datetime`, `json`, `os`, `pathlib`,
`re`, `sys`, `uuid`. Verified by test.

## 3. States

```
                    (creation)
                         |
                         v
                    TEMPORARY  ---- 3h untouched, sweep runs ----> EXPIRED
                     |  |  |                                       (terminal)
         Level 2 ----+  |  +---- Print Ready                       content purged
            |           |             |
            v           |             v
          SAVED         |        PRINT_READY
            |        Level 3          |
            |           |             |
            +---------> FORMAL <------+
                         |
     any non-terminal ---+---- Delete ----> DELETED (terminal, content purged)
```

| State | Expires? | Meaning |
| --- | --- | --- |
| `TEMPORARY` | Yes, 3h | The default. Everything starts here. |
| `SAVED` | No | Level 2 parked-review record. |
| `FORMAL` | No | Level 3. Nothing produced. |
| `PRINT_READY` | No | Held for print review. Nothing printed. |
| `DELETED` | n/a | Terminal. Content purged. Tombstone kept. |
| `EXPIRED` | n/a | Terminal. Content purged. Never promoted. |

**State and level are independent.** Level 2 and Level 3 raise both. Print Ready
raises only the state - print is a state, not a level. A Level 1 record that is
marked print ready reads `LEVEL_1` / `PRINT_READY`, and that is the one state
that does not expire while still carrying Level 1.

## 4. Operations

Explicit and named, not phrases to be interpreted:

| Operation | Effect |
| --- | --- |
| `LEVEL_1` | Stay temporary; reset the three-hour window. Refused on a preserved record. |
| `LEVEL_2` | State -> `SAVED`, level -> `LEVEL_2`, expiry cleared, references kept. |
| `LEVEL_3` | State -> `FORMAL`, level -> `LEVEL_3`, expiry cleared, destination kept. |
| `PRINT_READY` | State -> `PRINT_READY`, expiry cleared, **level unchanged**. |
| `DELETE` | State -> `DELETED`, content purged, reason recorded. |

Recognizing ordinary driver language is **not** this component's job and is not
implemented here. A retention store should not also be a parser.

## 5. Expiration

`expires_at = created_at + 3 hours`, set at creation. Only `TEMPORARY` records
carry an expiry; preserving a record sets `expires_at` to `null`.

Expiration is evaluated by `sweep()`, which runs automatically before every
active listing and can be run directly. On expiry the engine marks the record
`EXPIRED`, purges content, records the reason, and moves the file out of
`Data\active` into `Data\expired`.

**There is no background scheduler.** A record past its time is expired the next
time a sweep runs. Between the moment and the sweep it is stale but not yet
marked. Stated plainly rather than papered over.

Proving expiration does not require waiting three hours. Every time reading goes
through `Clock`, so tests and the operator substitute a `FixedClock`:

```bash
memory.cmd sweep --advance-hours 3.1
```

## 6. Storage

```
ASST\2\
  Data\active\    MEM-<stamp>-<id>.json   TEMPORARY, SAVED, FORMAL, PRINT_READY
  Data\expired\   MEM-<stamp>-<id>.json   EXPIRED tombstones, content purged
  Data\deleted\   MEM-<stamp>-<id>.json   DELETED tombstones, content purged
```

One JSON file per record, human-readable, no database. A record that changes
bucket is written to the new location and removed from the old one in the same
operation, so no duplicate can survive.

`assert_within_folder()` resolves every write path and refuses anything outside
`ASST\2`. That is why this workstream can state it stays in its assigned folder:
the store cannot write anywhere else.

Root resolution: `ASSISTANT_MEMORY_ROOT`, else `--folder-root`, else the folder
two levels above the package.

## 7. Record fields

`record_id`, `created_at`, `expires_at`, `updated_at`, `state`,
`interaction_level`, `source_channel`, `driver_request`, `assistant_response`,
`related_load`, `related_mission`, `destination`, `citations`,
`deletion_reason`.

Content fields purged on expiry or delete: `driver_request`,
`assistant_response`, `citations`.

## 8. What was deliberately left out

- **Natural-language command recognition.** Different job, different component.
- **A background scheduler.** Would need a service or task; out of scope and
  declared as a limitation rather than hidden.
- **Routing and artifact production.** Forbidden by the build matrix.
- **A database.** Plain JSON is reviewable by opening it.
- **Concurrency control.** One operator at a time is assumed and declared.
