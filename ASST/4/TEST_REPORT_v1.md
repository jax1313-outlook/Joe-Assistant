# Workstream 4 - Assistant Outlook - Test Report

**Component:** Assistant Outlook
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, standard library only

---

## Result

**63 tests. 63 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\4\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_outlook.py`.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestModels` | 13 | UTC parsing of `Z`, naive, and offset timestamps; unreadable timestamps raise; missing fields raise; an event ending before it starts raises; overlap arithmetic including the touching-is-not-overlap case; duration; same-day comparison; models are frozen. |
| `TestProvider` | 7 | Sample calendar, mail, and contacts load; events sorted by start; messages newest first; status reports no live connection; the default data root is this folder. |
| `TestProviderEdges` | 5 | Missing files yield empty lists and are named; malformed JSON raises; non-list JSON raises; a bad entry is skipped, counted, and named without killing the good ones; empty lists are handled throughout. |
| `TestCalendarAwareness` | 12 | Next and current event at fixed moments; none before and after everything; events on a day; conflicts detected and measured in minutes; unanswered invitations include `none` and `tentative` but not `accepted`; day brief reports events, conflicts, and day bounds; empty days; serialization. |
| `TestEmailAwareness` | 11 | Unread filtering; flags for decision markers, high importance, unread, and staleness; a routine read message is **not** flagged; every flag carries reasons; **every flag reports `decided: False` and `acted_on: False`**; the marker list is visible; search by text and by sender; empty search returns nothing. |
| `TestContactAwareness` | 6 | Find by name, company, and role; resolve a sender address to a contact; unknown sender returns `None`; empty query returns nothing. |
| `TestBoundaries` | 9 | No workstream import; no mail-transport or vendor import; standard library only; **the provider port defines only reads**; seventeen forbidden method names absent from both awareness and provider; every capability flag `False`; no write call anywhere; **reading changes nothing on disk**; no live Outlook/Graph provider shipped. |

## The read-only proofs

Four tests carry the central claim:

1. `test_the_provider_port_defines_only_reads` - the port's public surface is
   exactly `{name, calendar_events, email_messages, contacts}`. Nothing else can
   be called, so no provider can be asked to write.
2. `test_no_send_reply_or_schedule_method_exists` - seventeen names checked
   against both the awareness object and the provider: `send`, `send_email`,
   `reply`, `reply_all`, `forward`, `accept`, `decline`, `schedule`,
   `create_event`, `update`, `delete`, `move`, `flag`, `mark_read`, `save`,
   `draft`.
3. `test_status_declares_every_capability_as_absent` - `can_send`, `can_reply`,
   `can_schedule`, `can_modify`, `can_accept_or_decline`,
   `has_approval_authority`, `live_connection` all `False`.
4. `test_reading_awareness_changes_nothing_on_disk` - snapshots every file
   modification time in `Data\`, runs a day brief, a flag pass, and a contact
   search, then asserts nothing changed.

## Operator verification

```
outlook.cmd --now 2026-08-26T08:00:00Z brief
  -> 2 events, 1 conflict (30 min overlap), 1 invitation with no response
outlook.cmd --now 2026-08-25T12:00:00Z next
  -> nothing happening now; next is Pickup - Charlotte NC at 12:00 UTC
outlook.cmd status
  -> provider json-file, live_connection False,
     source "local sample fixture files, not a live mailbox",
     4 events / 4 messages / 3 contacts,
     can_send / can_reply / can_schedule / can_modify /
     can_accept_or_decline / has_approval_authority all False
```

## Boundary verification

Imports across the whole package: `__future__`, `argparse`, `dataclasses`,
`datetime`, `json`, `os`, `pathlib`, `sys`. Nothing else.

Absent by test: `smtplib`, `imaplib`, `poplib`, `email`, `socket`, `urllib`,
`http`, `requests`, `ssl`, `win32com`, `pythoncom`, `msal`, `office365`,
`exchangelib`, `O365`, and every other vendor module. A component that cannot
send mail does not import a mail library either.

---

## PROVEN CAPABILITIES

1. Reads calendar, email, and contact data through a read-only provider port.
2. Parses UTC, naive, and offset timestamps correctly; rejects unreadable ones.
3. Rejects events that end before they start and records missing required fields.
4. Sorts events by start time and messages newest first.
5. Reports the next event and the current event at any given moment.
6. Detects overlapping appointments and measures the overlap in minutes.
7. Correctly treats back-to-back appointments as **not** in conflict.
8. Lists invitations with no response recorded, without being able to answer them.
9. Produces a day brief with events, conflicts, unanswered invitations, and day
   bounds.
10. Filters unread mail.
11. Flags mail by decision marker, importance, unread state, and age.
12. Reports the reason for every flag.
13. Reports `decided: False` and `acted_on: False` on every flag.
14. Leaves routine read mail unflagged.
15. Searches mail by text and by sender.
16. Finds contacts by name, company, or role, and resolves a sender address.
17. Reports missing data files by name and treats them as empty.
18. Raises on malformed JSON rather than reporting an empty calendar.
19. Skips, counts, and names a bad entry without losing the good ones.
20. Exposes no send, reply, accept, decline, schedule, or modify method.
21. Declares every capability flag as `False`.
22. Changes nothing on disk, proven by filesystem observation.
23. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. **The CLI.** Exercised by hand as recorded above; no automated test drives
   `cli.py`.
2. **The `ASSISTANT_OUTLOOK_DATA` environment override.** Implemented in
   `resolve_data_root()`; tests pass an explicit root.
3. **Behavior with a large mailbox or calendar.** The sample set is 4 events,
   4 messages, 3 contacts. Nothing is measured at scale.
4. **Conflict detection at scale.** The comparison is every pair against every
   other pair, which grows quadratically. Fine for a day; unmeasured for a year.
5. **`has_attachments`, `to`, and `body_preview`** are modelled and carried
   through, but no awareness rule uses `has_attachments` or `to`.
6. **All-day events.** `is_all_day` is modelled; no sample data or test exercises
   one, and overlap arithmetic for all-day events is unverified.

## NOT IMPLEMENTED

1. **Any live Outlook, Exchange, Microsoft Graph, MAPI, or COM connection.**
   This is the largest gap and is deliberate: it needs authentication, network
   access, and a decision about what an Assistant may read from a real mailbox.
2. **Sending, replying, forwarding, or drafting email.**
3. **Accepting, declining, creating, moving, or cancelling calendar entries.**
4. **Marking read, flagging, filing, or deleting messages.**
5. **Any approval authority.**
6. **Recurring event expansion.** Single occurrences only.
7. **Full message bodies or attachment contents.**
8. **Time-zone display.** Everything is reported in UTC.
9. **Free/busy lookup or meeting-time suggestion.**
10. **Any retention or memory between runs.**
11. **Any library, research, or voice capability.**
12. **Any network capability.**
13. **Any user interface.** Command line only.

## KNOWN LIMITATIONS

1. **The data is sample data.** Every result in this report describes the
   fixtures in `ASST\4\Data`, not a real mailbox.
2. **Flagging over-flags.** The marker list is deliberate pattern matching, so a
   subscription confirmation containing the word "confirm" will be flagged. This
   is the stated cost of a rule that can be audited in ten seconds.
3. **Flagging under-flags.** A message that genuinely needs a decision but uses
   none of the marker words, is read, is normal importance, and is recent will
   not be flagged.
4. Conflict detection compares every pair; unmeasured beyond a handful of events.
5. All times are UTC, including in the day brief. A driver reading "12:00" is
   reading UTC, not local time.
6. `STALE_AFTER_DAYS` is fixed at 14 and is not configurable.
7. Verified on Windows 11 with Python 3.14.5 only.
8. Noticing is not deciding. Every decision this component surfaces stays with
   Mike Zachary.
