# Workstream 4 - Assistant Outlook - Constitution

**Component:** Assistant Outlook
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\4`.

---

## 1. Authority

Mike Zachary remains final authority.

**This component has no approval authority of any kind.** It reports what a
calendar, a mailbox, and a contact list contain. Every decision that follows -
answering a message, accepting a meeting, agreeing a rate - is Mike's.

Where the component flags a message as looking like it needs a decision, that is
a pattern match on words in a subject line. It is noticing, not deciding, and
the flag says so: `decided: False`, `acted_on: False`.

## 2. Read only - structurally

1. **No sending.** No `send`, `reply`, `reply_all`, `forward`, or `draft` method
   exists anywhere in this component.
2. **No modification.** No `update`, `delete`, `move`, `flag`, `mark_read`, or
   `save` method exists.
3. **No scheduling.** No `schedule`, `create_event`, `accept`, or `decline`
   method exists.
4. **The provider port defines exactly three methods, and all three are reads:**
   `calendar_events()`, `email_messages()`, `contacts()`. There is no write
   method for a provider to implement, so no provider - present or future - can
   be given one without changing `provider.py` itself.
5. **No file is written.** The component reads JSON fixtures and holds
   everything in memory.

Enforced by five tests:

- `test_the_provider_port_defines_only_reads` asserts the port's public surface
  is exactly `name`, `calendar_events`, `email_messages`, `contacts`.
- `test_no_send_reply_or_schedule_method_exists` checks seventeen forbidden
  method names against both the awareness object and the provider.
- `test_status_declares_every_capability_as_absent` asserts every capability
  flag is `False`.
- `test_no_write_call_exists_anywhere_in_the_package` scans every source file.
- `test_reading_awareness_changes_nothing_on_disk` snapshots every file
  modification time in `Data\`, runs a brief, a flag pass, and a contact
  search, then asserts nothing changed.

## 3. Isolation - absolute

1. This folder writes no file outside `ASST\4`. It writes no file at all.
2. This folder imports nothing from workstreams 1, 2, 3, 5, or 6.
3. This folder assumes no other workstream exists.
4. There is no integration code here, and none may be added.

Enforced by `test_imports_nothing_from_another_workstream` and
`test_uses_only_the_standard_library`, which fail on any import outside
`__future__`, `argparse`, `dataclasses`, `datetime`, `json`, `os`, `pathlib`,
`sys`.

Note what that list does **not** contain: `smtplib`, `imaplib`, `poplib`, or
even `email`. A component that cannot send mail should not be able to construct
a message either.

## 4. Hard prohibitions

There is no code path in this component that could do any of the following:

1. Send, reply to, forward, or draft an email.
2. Accept, decline, create, move, or cancel a calendar entry.
3. Mark a message read, flag it, file it, or delete it.
4. Reach the network. No networking module is imported at all.
5. Connect to Outlook, Exchange, Microsoft Graph, MAPI, or COM.
6. Approve a rate, a contract, a load, or anything else.
7. Commit money.
8. Write any file, inside `ASST\4` or out.
9. Retain anything between runs.

`test_no_live_outlook_or_graph_provider_is_shipped` fails if
`graph.microsoft.com`, `outlook.office`, `MAPI`, or `Outlook.Application` ever
appears in the source.

## 5. Honesty rules

- **Never imply a live connection.** `status` prints `live_connection: False`
  and `source: local sample fixture files, not a live mailbox` on every run.
- **Never present a flag as a decision.** Every flagged message carries
  `decided: False` and `acted_on: False` and the reason it was noticed.
- **Never hide a gap in the data.** A missing fixture file is reported by name.
  An unreadable entry is skipped, counted, and named.
- **Never report empty when the truth is broken.** A missing file yields an
  empty list, because awareness of nothing is still awareness. **Malformed JSON
  raises**, because silently reporting an empty calendar from a broken file
  would be a lie.
- **Never claim to have answered an invitation.** Events with no response are
  listed under a heading that says this component cannot answer them.
- **The sample data says it is sample data.** `Data\README_DATA.md` states that
  the fixtures are not a live mailbox, calendar, or contact list.

## 6. What must not happen without a new decision

- Do not add a send, reply, accept, decline, or schedule capability.
- Do not add a write method to the provider port. Adding one changes what every
  future provider is allowed to do.
- Do not build a live Outlook or Graph provider inside this mission. That needs
  authentication, network access, and a decision from Mike about what an
  Assistant is permitted to read from a real mailbox.
- Do not let flagging become deciding. If the rule ever stops being a visible
  word list, the honesty claim in section 5 stops being checkable.
- Do not remove the sample-data notice.
