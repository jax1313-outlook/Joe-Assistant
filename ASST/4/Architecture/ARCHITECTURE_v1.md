# Workstream 4 - Assistant Outlook - Architecture

**Component:** Assistant Outlook
**Version:** 1.0.0

---

## 1. Shape

```
                    +---------------------------+
                    |          cli.py           |  operator surface
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |       awareness.py        |  all the noticing
                    |  briefs, next, conflicts, |  no acting, ever
                    |  flags, contact lookup    |
                    +-------------+-------------+
                                  |  three read calls, nothing else
                                  v
                    +---------------------------+
                    |    AwarenessProvider      |  THE PORT
                    |  calendar_events()        |  three methods
                    |  email_messages()         |  all reads
                    |  contacts()               |  no write method exists
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |     JsonFileProvider      |  the only provider built
                    |  reads ASST\4\Data\*.json |  no live connection
                    +---------------------------+
                                  |
                                  v
                    +---------------------------+
                    |         models.py         |  frozen dataclasses
                    +---------------------------+
```

## 2. The port is the boundary

`AwarenessProvider` is the design decision that carries the whole read-only
guarantee. It defines three methods and all three are reads.

There is no `send`, no `accept`, no `update`. Not stubbed out, not raising
`NotImplementedError` - **absent**. A future live Outlook provider would
subclass this port and could implement only the three reads, because those are
the only three the component ever calls.

That makes the boundary structural rather than procedural. It does not depend on
a reviewer noticing that someone added a method.

A test asserts the port's public surface is exactly
`{name, calendar_events, email_messages, contacts}`.

## 3. Modules

| Module | Responsibility | Tests |
| --- | --- | --- |
| `models.py` | `CalendarEvent`, `EmailMessage`, `Contact` as **frozen** dataclasses. Timestamp parsing, overlap arithmetic, validation. | 13 |
| `provider.py` | The read-only port, plus `JsonFileProvider`. Missing-file and malformed-file handling, status reporting. | 12 |
| `awareness.py` | Briefs, next/current event, conflicts, unanswered invitations, mail flagging, search, contact lookup. | 29 |
| `cli.py` | `brief`, `next`, `events`, `mail`, `attention`, `contacts`, `status`. | exercised manually |

**Third-party dependencies: zero.** Imports across the package: `__future__`,
`argparse`, `dataclasses`, `datetime`, `json`, `os`, `pathlib`, `sys`.

Note the absences: no `exchangelib`, no `O365`, no `msal`, no `pywin32` - and no
`smtplib`, `imaplib`, `poplib`, or even `email`. A component that cannot send
mail should not be able to construct a message either.

## 4. Models are frozen

All three models are `@dataclass(frozen=True)`. An awareness component that
could mutate the objects it reports would be one refactor away from being a
component that changes things. Freezing them removes the possibility.

Time handling: every timestamp is parsed to UTC. Naive values are treated as
UTC; offsets are converted. `Z` suffixes are handled. Unparseable values raise
rather than defaulting to now.

## 5. Calendar arithmetic

**Overlap.** `self.start < other.end and other.start < self.end`.

Touching events do **not** overlap - a 12:00-14:00 and a 14:00-15:00 are back to
back, not in conflict. There is a test for exactly this, because getting it
wrong would flag every consecutive appointment.

**Conflicts** are every overlapping pair, with the overlap measured in minutes.

**Unanswered invitations** are events whose `response_status` is `none` or
`tentative`. Reported only - the component cannot answer them, and the output
says so.

**Next / current.** `current_event` is the one containing the moment;
`next_event` is the first one starting after it. Both take an explicit `now`, so
every calendar behavior is testable at a fixed point in time rather than
depending on when the suite runs.

## 6. Mail flagging

A message is flagged if any of these hold:

| Reason | Rule |
| --- | --- |
| contains a decision marker | one of ~22 visible words appears in subject or preview |
| marked high importance | `importance == "high"` |
| unread | `is_read` is false |
| older than 14 days | `received` is more than `STALE_AFTER_DAYS` before now |

The marker list lives at the top of `awareness.py` and includes `approve`,
`confirm`, `authorize`, `sign`, `decision`, `please advise`, `rate change`,
`counter`, and similar.

Every flag carries **the reasons it was flagged**, plus `decided: False` and
`acted_on: False`. The driver can see why something surfaced and can see that
nothing was done about it.

This will produce false positives - a subscription confirmation will be flagged.
That is the price of a rule that can be read and audited in ten seconds, and it
is stated openly rather than replaced with something cleverer and unauditable.

## 7. Data handling, and one deliberate asymmetry

| Situation | Behavior | Why |
| --- | --- | --- |
| Fixture file missing | empty list, filename reported in `status` | awareness of nothing is still awareness |
| Malformed JSON | **raises `ProviderError`** | reporting an empty calendar from a broken file would be a lie |
| JSON is not a list | raises `ProviderError` | same reason |
| One bad entry among good ones | skipped, counted, and named | one broken record should not hide the rest |

The asymmetry between "missing" and "malformed" is the point: absent data is a
fact worth reporting; corrupted data is a failure worth raising.

## 8. Configuration

Data root resolution order:

1. explicit `--data-root` / constructor argument
2. `ASSISTANT_OUTLOOK_DATA` environment variable
3. `ASST\4\Data` - the sample fixtures in this folder

Global CLI options - `--data-root`, `--json`, `--now` - come **before** the
subcommand. `--now` lets any command be evaluated at a fixed moment, which is
how the calendar behavior is demonstrated repeatably.

## 9. What was deliberately left out

- **A live Outlook / Graph / Exchange provider.** Needs authentication, network
  access, and a decision from Mike about what an Assistant may read from a real
  mailbox. Declared NOT IMPLEMENTED rather than stubbed.
- **Any write path.** See section 2.
- **Full message bodies.** Only `body_preview` is modelled. Awareness needs the
  gist; the full body is a retrieval problem, and retrieving a whole mailbox
  into a local component is a decision nobody has made.
- **Attachment contents.** Presence is modelled, contents are not.
- **Recurring event expansion.** A recurrence rule would need a whole calendar
  engine. Single occurrences only.
- **Time-zone display.** Everything is reported in UTC, stated as UTC.
- **Any storage.** Nothing is retained between runs.
