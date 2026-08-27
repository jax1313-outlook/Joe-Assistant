# Workstream 2 - Assistant Memory - Constitution

**Component:** Assistant Memory
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\2`.

---

## 1. Authority

Mike Zachary remains final authority. This component holds and expires records.
It decides nothing operational and has no authority of any kind.

## 2. Isolation - absolute

1. This folder writes no file outside `ASST\2`. Runtime data lives in
   `ASST\2\Data`; test data lives in `ASST\2\Tests\_workspace`.
2. This folder imports nothing from workstreams 1, 3, 4, 5, or 6.
3. This folder imports nothing from any earlier project. The existing Sandbox
   Engine is **doctrine to follow, not code to import**, and it is not modified.
4. This folder assumes no other workstream exists.
5. There is no integration code here, and none may be added.

Enforced by `test_imports_nothing_from_another_workstream` and
`test_uses_only_the_standard_library`, which fail on any import outside
`__future__`, `argparse`, `dataclasses`, `datetime`, `json`, `os`, `pathlib`,
`re`, `sys`, `uuid`.

## 3. Hard prohibitions

There is no code path in this component that could do any of the following, and
tests assert the absence of every import that would be required:

1. Route, file, promote, or archive a record into any other system.
2. Produce an artifact, report, or document.
3. Contact a printer or cause physical printing.
4. Send or read email.
5. Reach the network. No networking module is imported at all.
6. Read a calendar, contact list, library, or research source.
7. Record or play audio.
8. Commit money, accept a load, or approve anything.
9. Write any file outside `ASST\2`.

`test_engine_exposes_no_routing_or_sending_operation` fails if the engine ever
grows a `send`, `route`, `publish`, `promote`, `archive`, `dispatch`,
`print_document`, or `upload` method.

## 4. Retention doctrine - binding

1. **Temporary is the default.** Every record is created `TEMPORARY` at
   `LEVEL_1` with a three-hour expiry. There is no way to create a record in any
   other state.
2. **Three hours** is the default retention. The value lives in one place
   (`DEFAULT_RETENTION_HOURS`) and is a constructor argument, so changing it is a
   doctrine decision, not a code hunt.
3. **Expiration purges content.** An expired record keeps its id, timestamps,
   state, and reason. The material itself is removed. Sandbox content is
   temporary by doctrine; keeping the text of an expired record would contradict
   that.
4. **Expired records are never promoted.** There is no path from `EXPIRED` to
   anywhere. `test_expired_records_are_never_promoted` asserts the store has
   exactly three buckets - active, expired, deleted - and nothing else.
5. **Delete purges content too**, and records why.
6. **Terminal is terminal.** No operation is accepted against a `DELETED` or
   `EXPIRED` record.
7. **Print is a state, not a level.** `PRINT_READY` stops expiration and leaves
   `interaction_level` alone. Do not add a level change to `_print_ready`
   without a new ruling. Locked by `test_print_ready_does_not_change_the_level`
   and `test_print_ready_from_level_2_keeps_level_2`.
8. **State never downgrades.** Rank is `TEMPORARY(0) < SAVED(1) <
   PRINT_READY(2) < FORMAL(3)`. An operation that would lower the rank leaves
   the state alone and says so. `Level 1` against an already-preserved record is
   refused outright rather than silently un-preserving it. Rank prevents
   accidental loss; it is not a claim about which level matters more.

## 5. Honesty rules

- **Never claim a completed action.** Level 3 says "No work product was
  produced." Print Ready says "No printer was contacted and nothing was
  physically printed."
- **Never describe a record as permanently saved.** A preserved record is
  described as held locally in this workstream's store, explicitly not routed
  anywhere.
- **Never promote an expired record.**
- **Say what is not proven.** The test and build reports carry explicit
  `IMPLEMENTED BUT NOT PROVEN` and `NOT IMPLEMENTED` sections.

## 6. Containment

`MemoryStore.assert_within_folder()` resolves every write path and raises
`StoreError` if it falls outside `ASST\2`. It runs on directory creation and on
every record write. `memory.cmd doctor` reports it on demand.

## 7. What must not happen without a new decision

- Do not connect this store to a UI, library, mailbox, research source, or
  voice engine. That is integration, forbidden by the build matrix.
- Do not add routing, promotion, or artifact production.
- Do not let a record be created in any state other than `TEMPORARY`.
- Do not let `PRINT_READY` change the interaction level.
- Do not let anything import this package from outside folder 2.
