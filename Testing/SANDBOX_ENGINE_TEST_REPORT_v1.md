# Sandbox Engine v1 - Test Report

**Project:** Level 1 Assistant - local governed workflow layer
**Engine version:** 1.0.0
**Project root:** `D:\Sandbox\Assistan_Building`
**Runtime:** Python 3.14.5 via the `py` launcher, standard library only
**Final authority:** Mike Zachary

---

## Result

**50 tests. 50 passed. 0 failed. 0 errors. 0 skipped.**

Command run:

```bash
D:\Sandbox\Assistan_Building\Build\run_tests.cmd
```

Which executes:

```bash
py -m unittest discover -s Testing -v
```

Raw console output from the last run is kept at
`Testing\_last_test_run.txt`, regenerated on every run.

Test source: `Testing\test_sandbox_engine.py`.

## Coverage by area

| Area | Tests | What it establishes |
| --- | --- | --- |
| `TestCreation` | 5 | Records begin `TEMPORARY` at Level 1, carry all 26 required fields, expire exactly three hours after creation, survive a serialization round trip, and land inside the project. |
| `TestIntentRecognition` | 12 | Every command phrase named in the governing configuration is recognized. Capitalization and punctuation are irrelevant. The three documented conflicts resolve as decided. Unrelated language is not a command. |
| `TestLevel2` | 5 | `Save this` converts to `SAVED` / `LEVEL_2`, expiration is cleared, the record survives a ten-hour sweep, load references are preserved, and Level 1 will not downgrade it. |
| `TestLevel3` | 5 | `Level 3 this under Ideas` yields `FORMAL` with destination `Ideas`, raises a formal-artifact request, carries citations and sources forward, and combines correctly with print language. |
| `TestPrint` | 7 | `Print this` yields `PRINT_READY`, stops expiration, never claims physical printing in any output, and — per Mike Zachary's ruling on doctrine C4 — leaves `interaction_level` unchanged. |
| `TestDelete` | 4 | `Delete this` yields `DELETED`, purges content, records the reason, leaves the active Sandbox, and accepts no further commands. |
| `TestExpiration` | 7 | Records survive to 2h59m and expire past 3h, leave the active Sandbox, have content purged, are never promoted, refuse later commands, and an explicit Level 1 resets the window. |
| `TestBoundaries` | 5 | The store refuses to write outside the project, all records stay inside it, the engine imports no network or vendor module, no send/dispatch/payment operation exists, and unrecognized language changes nothing. |

## Every test, by name

### TestCreation (5)

- `test_new_record_is_temporary_level_1`
- `test_expiration_is_exactly_three_hours_after_creation`
- `test_every_required_field_is_present`
- `test_record_survives_a_serialization_round_trip`
- `test_record_file_lands_inside_the_project`

### TestIntentRecognition (12)

- `test_level_1_phrases`
- `test_level_2_phrases`
- `test_level_3_phrases`
- `test_print_phrases`
- `test_delete_phrases`
- `test_capitalization_and_punctuation_do_not_matter`
- `test_decline_phrases_are_not_mistaken_for_save`
- `test_let_it_expire_is_level_1_not_delete`
- `test_bare_print_language_is_print_not_level_3`
- `test_level_3_wins_when_combined_with_print_language`
- `test_unrelated_language_is_not_a_command`
- `test_reference_extraction`

### TestLevel2 (5)

- `test_save_this_converts_to_saved_level_2`
- `test_saved_record_no_longer_expires`
- `test_saved_record_survives_a_ten_hour_sweep`
- `test_load_reference_is_preserved`
- `test_level_1_will_not_downgrade_a_saved_record`

### TestLevel3 (5)

- `test_level_3_under_ideas_is_formal_with_destination`
- `test_level_3_creates_a_formal_artifact_request`
- `test_citations_and_sources_are_carried_into_the_request`
- `test_level_3_plus_print_creates_both_requests`
- `test_xpo_load_reference_is_preserved`

### TestPrint (7)

- `test_print_this_yields_print_ready`
- `test_print_ready_record_does_not_expire`
- `test_print_does_not_raise_the_interaction_level` *(locks doctrine C4)*
- `test_every_print_phrase_leaves_the_level_at_level_1` *(locks doctrine C4)*
- `test_print_from_level_2_does_not_change_the_level` *(locks doctrine C4)*
- `test_engine_never_claims_physical_printing`
- `test_print_request_markdown_states_nothing_was_printed`

### TestDelete (4)

- `test_delete_this_yields_deleted`
- `test_deleted_record_leaves_the_active_sandbox`
- `test_deleted_record_content_is_purged_and_reason_recorded`
- `test_no_command_is_accepted_after_deletion`

### TestExpiration (7)

- `test_record_does_not_expire_before_three_hours`
- `test_record_expires_at_three_hours`
- `test_expired_record_is_absent_from_the_active_sandbox`
- `test_expired_record_content_is_purged_and_not_promoted`
- `test_commands_are_refused_on_an_expired_record`
- `test_explicit_level_1_resets_the_three_hour_window`
- `test_nothing_expired_is_ever_written_to_an_artifact_request`

### TestBoundaries (5)

- `test_store_refuses_to_write_outside_the_project`
- `test_all_records_live_under_the_project_root`
- `test_engine_source_imports_no_network_or_vendor_modules`
- `test_engine_exposes_no_send_dispatch_or_payment_operations`
- `test_unrecognized_language_changes_nothing`

## Command phrases covered

Every phrase below is asserted by the suite, in the exact wording of the
governing configuration and this mission.

| Intent | Phrases tested |
| --- | --- |
| LEVEL 1 | `Level 1`, `Just answer it`, `Just tell me what matters`, `No need to save this`, `Let it expire`, `Don't save this`, `Do not keep this` |
| LEVEL 2 | `Save this`, `Keep this`, `Level 2 this`, `Put this under Load 123`, `Attach this to the mission`, `Keep this for parked review` |
| LEVEL 3 | `Level 3 this`, `Build a report`, `Formal presentation`, `Write this up`, `Research this completely`, `Level 3 this under XPO Load 123`, `Level 3 this under Ideas with formal presentation` |
| PRINT | `Print this`, `Make this printable`, `Write this so I can print later` |
| DELETE | `Delete this`, `Remove this`, `Forget this` |
| NONE | `What loads do I have tomorrow`, `How far is Atlanta`, empty string |
| Case / punctuation | `level 3 this under ideas`, `LEVEL 3 THIS UNDER IDEAS.`, `  Level 3 this under Ideas!!  `, `level  3  this under Ideas,` |

## Test data containment

Every test writes only into `Testing\_test_workspace\<random>\`, which is removed
in `tearDown`. No test writes to `Sandbox\`, to any other project folder, or to
anywhere outside `D:\Sandbox\Assistan_Building`. Two tests assert this directly:
`test_record_file_lands_inside_the_project` and
`test_all_records_live_under_the_project_root`.

No test contacts a network, a printer, Dispatch, Outlook, Microsoft Graph, or
any production system. `test_engine_source_imports_no_network_or_vendor_modules`
scans the engine source and fails if any networking or vendor module appears in
an import statement.

---

## Honest limitations - what these tests do NOT prove

The suite passing does not mean the workflow is operationally proven. It means
the code does what it was written to do. Specifically:

1. **Real three-hour expiration has never been observed.** Every expiration test
   uses a simulated clock. Expiration after three hours of real elapsed time on
   this machine is untested.

2. **There is no background scheduler.** Expiration happens when a sweep runs —
   `sandbox.cmd list`, `sandbox.cmd sweep`, or a programmatic call. A record past
   its time sitting in an unopened folder is stale but not yet marked `EXPIRED`.
   If the engine is never run again, records never expire. This is a real gap,
   not a test gap.

3. **Recognition is proven against a fixed phrase list, not open language.** The
   phrases in the governing documents and the listed variations are covered.
   Unrestricted natural language is not. A phrase nobody anticipated resolves to
   `NONE` and changes nothing, which is the safe failure, but it is still a miss.

4. **Reference extraction is pattern matching, not understanding.** `Load 123`,
   `customer X`, `broker X`, `mission X`, and `under X` are recognized. An
   organization named before a load number (`XPO Load 123`) is kept in
   `destination` and deliberately **not** written to `related_broker`, because
   deterministic code cannot tell a broker from a customer from a lane name.

5. **No integration is tested, because none exists.** Dispatch, Outlook,
   Microsoft Graph, Microsoft 365 Copilot, COMI, Publisher, Company Library,
   Research Library, and Archive are untouched. There are no integration tests
   because there is nothing to integrate with yet.

6. **No artifact is produced or verified.** Level 3 and Print write requests. The
   tests confirm those requests carry `produced: false` and
   `physical_print_performed: false`. Nothing verifies a downstream producer,
   because there is no downstream producer.

7. **Nothing is tested under concurrency.** The store assumes one operator at a
   time. Two processes writing the same record simultaneously is untested and
   unguarded.

8. **No multi-user, permission, or encryption behavior is tested.** Records are
   plain readable JSON on a local disk with no access control beyond the file
   system.

9. **Only this machine is tested.** Windows 11, Python 3.14.5. Other Python
   versions and other machines are untested.

10. **Voice, phone, and email paths are untested because they do not exist.**
