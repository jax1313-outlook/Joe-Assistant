# Workstream 2 - Assistant Memory - Test Report

**Component:** Assistant Memory
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, standard library only

---

## Result

**45 tests. 45 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\2\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_memory.py`.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestCreation` | 6 | Records begin `TEMPORARY` at Level 1, expire exactly three hours after creation, carry all 14 fields, survive a round trip, land inside the folder, and get unique ids. |
| `TestLevel1` | 3 | Level 1 resets the window, keeps the record temporary, and is refused on a preserved record. |
| `TestLevel2` | 4 | Level 2 saves and raises the level, stops expiration, survives a ten-hour sweep, preserves load and destination references. |
| `TestLevel3` | 4 | Level 3 marks formal, preserves the destination, stops expiration, produces nothing, and upgrades cleanly from `SAVED`. |
| `TestPrintReady` | 6 | Print Ready sets the state, **does not change the level** from Level 1 or Level 2, stops expiration, never claims printing, and does not downgrade a formal record. |
| `TestDelete` | 4 | Delete sets the state, purges content, records the reason, leaves the active set, and refuses every later operation. |
| `TestExpiration` | 7 | Survives to 2h59m, expires past 3h, leaves the active set, purges content, refuses later operations, sweeps before listing, and is idempotent. |
| `TestStore` | 5 | Refuses writes outside the folder, rejects unknown states, raises on missing records, keeps every record inside the folder, and leaves no duplicate when a record changes bucket. |
| `TestBoundaries` | 6 | No workstream import, no network/email/printing/vendor import, standard library only, no routing or sending method, expired records never promoted, unknown operations refused. |

## Operator verification

The CLI was exercised end to end against the real store:

- created a record - `TEMPORARY` / `LEVEL_1`, expiring three hours out
- `level-2` with `--related-load "Load 123"` - `TEMPORARY -> SAVED`,
  `LEVEL_1 -> LEVEL_2`, expiry cleared, reference kept
- `level-3 --destination "Ideas"` - `FORMAL` / `LEVEL_3`
- `print-ready` - `PRINT_READY` while still reading `L1`
- `delete --reason "driver asked to forget it"` - content purged
- `sweep --advance-hours 3.1` - expired 1 record, content purged, not promoted
- `list` after the sweep - 3 active records, the expired one absent
- `doctor` - writes outside blocked `True`, 5 records on disk, 0 outside folder

## Test data containment

Every test writes only into `Tests\_workspace\<random>\`, removed in
`tearDown`. No test writes to `Data\`, to any other folder, or to anywhere
outside `ASST\2`. Asserted directly by `test_record_lands_inside_the_folder` and
`test_all_records_stay_inside_the_folder`.

## Boundary verification

Imports across the whole package: `__future__`, `argparse`, `dataclasses`,
`datetime`, `json`, `os`, `pathlib`, `re`, `sys`, `uuid`. Nothing else. No third
party, no networking module, no workstream 1 or 3-6 import, no import of the
existing Sandbox Engine.

---

## PROVEN CAPABILITIES

1. Records are created `TEMPORARY` at Level 1 with a three-hour expiry.
2. The expiry is exactly three hours after creation.
3. Level 1 resets the window and refuses to downgrade a preserved record.
4. Level 2 produces `SAVED` / `LEVEL_2` and stops expiration.
5. Level 3 produces `FORMAL` / `LEVEL_3` and stops expiration.
6. Print Ready produces `PRINT_READY`, stops expiration, and leaves the level
   unchanged from both Level 1 and Level 2.
7. Delete produces `DELETED`, purges content, and records a reason.
8. Records expire past three hours and not before.
9. Expired records leave the active set and are never promoted.
10. Expired and deleted content is purged; tombstones remain for audit.
11. Terminal records refuse every further operation.
12. State never downgrades.
13. Expiration is provable on a simulated clock without waiting.
14. The store refuses to write outside `ASST\2`.
15. A record changing bucket leaves no duplicate behind.
16. The component imports nothing from any other workstream.
17. Level 3 produces no work product and says so.
18. Print Ready contacts no printer and says so.

## IMPLEMENTED BUT NOT PROVEN

1. **Real three-hour expiration.** Every expiration test uses a simulated clock.
   Expiration after three hours of real elapsed time has never been observed.
2. **The CLI.** Exercised by hand as recorded above, but no automated test drives
   `cli.py`. Its rendering and argument parsing are unproven by the suite.
3. **`ASSISTANT_MEMORY_ROOT` environment override.** Implemented in
   `default_folder_root()`; the tests pass an explicit root instead.
4. **Behavior with a large store.** The largest test set is a few dozen records.
   Listing performance past that is unmeasured.
5. **Recovery from a partially written or corrupt JSON file.** No test induces
   one; the store would raise rather than repair.
6. **Non-default `retention_hours`.** The constructor accepts it; only the
   three-hour default is tested.

## NOT IMPLEMENTED

1. **A background scheduler.** Records expire only when a sweep runs.
2. **Natural-language command recognition.** Operations are explicit and named.
3. **Routing, filing, promotion, or archiving** into any other system.
4. **Artifact or report production.**
5. **Printing.** `PRINT_READY` is a state and nothing more.
6. **Any user interface.** Command line only.
7. **Any library, research, email, calendar, contact, or voice capability.**
8. **Any network capability.**
9. **Concurrency control, locking, or multi-user access.**
10. **Encryption, access control, or redaction beyond content purging.**
11. **Backup, synchronization, or replication.**
12. **Search across records** beyond listing by state.
13. **Undo.** Delete and expiry purge content irreversibly.

## KNOWN LIMITATIONS

1. **No timer.** If the engine is never run, nothing expires. `list` sweeps
   first, so opening the list is enough - but a record sitting in an unopened
   folder past its time is stale, not yet marked. This is a real gap, not a test
   gap.
2. Purged content is unrecoverable. There is no undo.
3. One operator at a time is assumed. Two processes writing the same record
   simultaneously is untested and unguarded.
4. Records are plain readable JSON on a local disk with no access control beyond
   the file system.
5. `Data\` accumulates tombstones indefinitely. No pruning policy exists.
6. Verified on Windows 11 with Python 3.14.5 only.
7. The component cannot tell you whether a record *should* be preserved. That
   judgement stays with Mike Zachary.
