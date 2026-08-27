# Workstream 2 - Assistant Memory - Build Report

**Component:** Assistant Memory
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\2`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build the Sandbox retention system: Level 1, Level 2, Level 3, Print Ready,
Delete, Expiration.

Use Sandbox Engine doctrine. No integration. No Outlook. No voice. No research.
The existing Sandbox Engine may be referenced but not modified outside this
workstream.

## FILES CREATED

```
ASST\2\
  README.md                                    reviewer entry point
  BUILD_REPORT_v1.md                           this file
  TEST_REPORT_v1.md                            full test results
  Context\CONTEXT_v1.md                        what this is and the doctrine it follows
  Constitution\CONSTITUTION_v1.md              binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md              module design, states, storage
  Operator_Guide\OPERATOR_GUIDE_v1.md          how Mike runs it
  Source\memory.cmd                            launcher
  Source\assistant_memory\__init__.py          package exports
  Source\assistant_memory\__main__.py          py -m assistant_memory entry
  Source\assistant_memory\clock.py             real and simulated time
  Source\assistant_memory\record.py            record model, states, levels, purging
  Source\assistant_memory\store.py             JSON store, folder containment
  Source\assistant_memory\retention.py         lifecycle rules and transitions
  Source\assistant_memory\cli.py               operator interface
  Tests\run_tests.cmd                          test launcher
  Tests\test_assistant_memory.py               45 tests
  Tests\_last_test_run.txt                     raw output of the last run
  Data\active\*.json                           live records (demonstration set)
  Data\expired\*.json                          expired tombstones
  Data\deleted\*.json                          deleted tombstones
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\2\Tests\run_tests.cmd
py -m assistant_memory new --request "..." --response "..."
py -m assistant_memory level-2 <id> --related-load "Load 123" --destination "Load 123"
py -m assistant_memory level-3 <id> --destination "Ideas"
py -m assistant_memory print-ready <id>
py -m assistant_memory delete <id> --reason "driver asked to forget it"
py -m assistant_memory sweep --advance-hours 3.1
py -m assistant_memory list
py -m assistant_memory doctor
```

## TEST RESULTS

**45 tests. 45 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestCreation` | 6 |
| `TestLevel1` | 3 |
| `TestLevel2` | 4 |
| `TestLevel3` | 4 |
| `TestPrintReady` | 6 |
| `TestDelete` | 4 |
| `TestExpiration` | 7 |
| `TestStore` | 5 |
| `TestBoundaries` | 6 |

Detail in `TEST_REPORT_v1.md`. Raw output in `Tests\_last_test_run.txt`.

Live operator run, against the real store:

```
  MEM-...-CAB7F2   SAVED        L2   (no expiration)   Broker offered 2.10 on the Charlotte run
  MEM-...-B66D22   FORMAL       L3   (no expiration)   Northbound lane idea
  MEM-...-24B90F   PRINT_READY  L1   (no expiration)   Maintenance summary
```

plus one deleted tombstone and one record expired by `sweep --advance-hours 3.1`.
`doctor` reported writes-outside-blocked `True`, 5 records on disk, 0 outside
the folder.

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

1. Real three-hour expiration. Proven only on a simulated clock.
2. The CLI. Exercised by hand, not by the automated suite.
3. The `ASSISTANT_MEMORY_ROOT` environment override.
4. Behavior with a large store. Largest test set is a few dozen records.
5. Recovery from a corrupt or partially written JSON file.
6. Non-default `retention_hours`. Only the three-hour default is tested.

## NOT IMPLEMENTED

1. A background scheduler. Records expire only when a sweep runs.
2. Natural-language command recognition.
3. Routing, filing, promotion, or archiving into any other system.
4. Artifact or report production.
5. Printing.
6. Any user interface. Command line only.
7. Any library, research, email, calendar, contact, or voice capability.
8. Any network capability.
9. Concurrency control, locking, or multi-user access.
10. Encryption, access control, or redaction beyond content purging.
11. Backup, synchronization, or replication.
12. Search beyond listing by state.
13. Undo.

## KNOWN LIMITATIONS

1. **No timer.** If the engine is never run, nothing expires. `list` sweeps
   first, so opening the list is enough - but a record past its time in an
   unopened folder is stale, not yet marked. A real gap, not a test gap.
2. Purged content is unrecoverable.
3. One operator at a time is assumed; concurrent writes are unguarded.
4. Plain readable JSON with no access control beyond the file system.
5. `Data\` accumulates tombstones indefinitely. No pruning policy.
6. Verified on Windows 11, Python 3.14.5 only.
7. The component cannot judge whether a record should be preserved. That stays
   with Mike Zachary.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. Sandbox doctrine is restated in full
in `Context\CONTEXT_v1.md` and `Constitution\CONSTITUTION_v1.md`, so a reviewer
needs no other folder and no other project to check this component against its
rules.

**On "may be referenced but not modified".** The existing Sandbox Engine was
treated as doctrine to follow, not code to import. This workstream is a fresh,
self-contained implementation. Nothing outside `ASST\2` was read at runtime or
written at any time. A test fails the build if `sandbox_engine` ever appears in
an import.

**The decision worth your attention: no parser.** Recognizing ordinary driver
language was deliberately left out. Operations are explicit - `level-2`,
`print-ready`. A retention store that also guesses what you meant has two jobs
and can fail at either while looking like it succeeded. Declared under NOT
IMPLEMENTED rather than half-built.

**Print is a state, not a level.** `PRINT_READY` stops expiration and leaves
`interaction_level` alone, so a printed Level 1 record reads `LEVEL_1` /
`PRINT_READY`. That is the one state that does not expire while still carrying
Level 1. Intended, and locked by two tests.

**The honest gap.** There is no background scheduler. Expiration happens when a
sweep runs. Listing sweeps first, so normal use is fine, but a record can sit
past its time in an unopened folder. This is stated in the context, the
architecture, the operator guide, the test report, and here - because it is the
one thing about this component that could mislead someone who assumed a timer.

**Containment is enforced, not promised.** `assert_within_folder()` resolves
every write path and raises before writing. `memory.cmd doctor` demonstrates it
on demand, and two tests assert it.
