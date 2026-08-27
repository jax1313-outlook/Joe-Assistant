# Workstream 4 - Assistant Outlook - Build Report

**Component:** Assistant Outlook
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\4`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build calendar awareness, email awareness, and contact awareness.

Read only. No sending. No modification. No scheduling. No approval authority.

## FILES CREATED

```
ASST\4\
  README.md                                     reviewer entry point
  BUILD_REPORT_v1.md                            this file
  TEST_REPORT_v1.md                             full test results
  Context\CONTEXT_v1.md                         what this is, and the live-connection gap
  Constitution\CONSTITUTION_v1.md               binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md               the port, models, calendar arithmetic, flagging
  Operator_Guide\OPERATOR_GUIDE_v1.md           how Mike runs it
  Source\outlook.cmd                            launcher
  Source\assistant_outlook\__init__.py          package exports
  Source\assistant_outlook\__main__.py          py -m assistant_outlook entry
  Source\assistant_outlook\models.py            frozen event, message, contact models
  Source\assistant_outlook\provider.py          read-only port + JSON fixture provider
  Source\assistant_outlook\awareness.py         briefs, conflicts, flags, lookup
  Source\assistant_outlook\cli.py               operator interface
  Data\README_DATA.md                           what the sample data is and is not
  Data\calendar.json                            4 sample events
  Data\emails.json                              4 sample messages
  Data\contacts.json                            3 sample contacts
  Tests\run_tests.cmd                           test launcher
  Tests\test_assistant_outlook.py               63 tests
  Tests\_last_test_run.txt                      raw output of the last run
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\4\Tests\run_tests.cmd
py -m assistant_outlook --now 2026-08-26T08:00:00Z brief
py -m assistant_outlook --now 2026-08-25T12:00:00Z next
py -m assistant_outlook status
```

## TEST RESULTS

**63 tests. 63 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestModels` | 13 |
| `TestProvider` | 7 |
| `TestProviderEdges` | 5 |
| `TestCalendarAwareness` | 12 |
| `TestEmailAwareness` | 11 |
| `TestContactAwareness` | 6 |
| `TestBoundaries` | 9 |

Live operator run:

```
brief   -> 2 events on 2026-08-26, 1 conflict (30 min overlap),
           1 invitation with no response recorded
next    -> nothing happening now; next is Pickup - Charlotte NC at 12:00 UTC
status  -> live_connection False, source "local sample fixture files,
           not a live mailbox", 4 events / 4 messages / 3 contacts,
           can_send / can_reply / can_schedule / can_modify /
           can_accept_or_decline / has_approval_authority all False
```

Detail in `TEST_REPORT_v1.md`.

## PROVEN CAPABILITIES

1. Reads calendar, email, and contact data through a read-only provider port.
2. Parses UTC, naive, and offset timestamps; rejects unreadable ones.
3. Rejects events ending before they start; records missing required fields.
4. Sorts events by start time and messages newest first.
5. Reports the next event and the current event at any given moment.
6. Detects overlapping appointments and measures the overlap in minutes.
7. Treats back-to-back appointments as **not** in conflict.
8. Lists invitations with no response, without being able to answer them.
9. Produces a day brief with events, conflicts, unanswered invitations, bounds.
10. Filters unread mail.
11. Flags mail by decision marker, importance, unread state, and age.
12. Reports the reason for every flag.
13. Reports `decided: False` and `acted_on: False` on every flag.
14. Leaves routine read mail unflagged.
15. Searches mail by text and by sender.
16. Finds contacts by name, company, or role; resolves a sender address.
17. Reports missing data files by name and treats them as empty.
18. Raises on malformed JSON rather than reporting an empty calendar.
19. Skips, counts, and names a bad entry without losing the good ones.
20. Exposes no send, reply, accept, decline, schedule, or modify method.
21. Declares every capability flag as `False`.
22. Changes nothing on disk, proven by filesystem observation.
23. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. The CLI. Exercised by hand, not by the automated suite.
2. The `ASSISTANT_OUTLOOK_DATA` environment override.
3. Behavior with a large mailbox or calendar. Sample set is 4/4/3.
4. Conflict detection at scale. The comparison grows quadratically.
5. `has_attachments` and `to` are modelled and carried but no rule uses them.
6. All-day events. `is_all_day` is modelled; no data or test exercises one.

## NOT IMPLEMENTED

1. **Any live Outlook, Exchange, Microsoft Graph, MAPI, or COM connection.**
2. Sending, replying, forwarding, or drafting email.
3. Accepting, declining, creating, moving, or cancelling calendar entries.
4. Marking read, flagging, filing, or deleting messages.
5. Any approval authority.
6. Recurring event expansion.
7. Full message bodies or attachment contents.
8. Time-zone display. Everything is UTC.
9. Free/busy lookup or meeting-time suggestion.
10. Any retention or memory between runs.
11. Any library, research, or voice capability.
12. Any network capability.
13. Any user interface. Command line only.

## KNOWN LIMITATIONS

1. **The data is sample data.** Every result describes the fixtures in
   `ASST\4\Data`, not a real mailbox.
2. Flagging over-flags: a subscription confirmation containing "confirm" gets
   flagged. Stated cost of an auditable rule.
3. Flagging under-flags: a message needing a decision that uses none of the
   marker words, is read, normal importance, and recent will be missed.
4. Conflict detection compares every pair; unmeasured beyond a handful.
5. All times are UTC. A driver reading "12:00" is reading UTC, not local time.
6. `STALE_AFTER_DAYS` is fixed at 14 and not configurable.
7. Verified on Windows 11, Python 3.14.5 only.
8. Noticing is not deciding. Every decision stays with Mike Zachary.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. The component ships with its own
sample fixtures, so every command and every test runs with no credentials, no
network, and no access grants.

**The biggest thing to know, stated plainly: there is no live mailbox.** No
Graph, no Exchange, no MAPI, no COM, no credentials. The awareness logic is real
and tested; the data is sample data. This is not buried - it is the second
heading of the context document, and `outlook.cmd status` prints
`live_connection: False` and `source: local sample fixture files, not a live
mailbox` on every single run. Building a live provider needs authentication,
network access, and a decision from you about what an Assistant may read from a
real mailbox. That is a separate mission.

**The design decision that carries the whole boundary: the port.**
`AwarenessProvider` defines three methods and all three are reads. There is no
`send`, no `accept`, no `update` - not stubbed, not raising, **absent**. A future
live provider could implement only those three, because those are the only three
the component ever calls. A test asserts the port's public surface exactly. That
makes read-only structural rather than something a reviewer has to police.

**Models are frozen dataclasses.** An awareness component that could mutate what
it reports is one refactor from being a component that changes things.

**Flagging is noticing, not deciding - and it says so in the data.** Every
flagged message carries the reasons it surfaced plus `decided: False` and
`acted_on: False`. The marker list is ~22 visible words at the top of
`awareness.py`. It will over-flag. That is the deliberate price of a rule you can
read and check in ten seconds, and it is declared under KNOWN LIMITATIONS rather
than replaced with something cleverer and unauditable.

**One asymmetry worth understanding.** A missing data file is reported by name
and treated as empty - awareness of nothing is still awareness. A **malformed**
file raises. Quietly reporting an empty calendar from a file that failed to parse
would be a lie, and an empty calendar is exactly the kind of lie that gets
someone to the dock on the wrong day.

**The touching-is-not-overlap case has its own test.** A 12:00-14:00 and a
14:00-15:00 are back to back, not in conflict. Getting that wrong would flag
every consecutive appointment and make conflict detection worthless.

**No mail library is imported at all** - not `smtplib`, not `imaplib`, not even
`email`. A component that cannot send mail should not be able to construct a
message either.
