# Workstream 4 - Assistant Outlook - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\4`

---

## Read this first

**This is not connected to your real mailbox.** There is no Outlook, Exchange,
or Microsoft Graph connection in this component. It reads sample data files in
`ASST\4\Data`.

The awareness logic is real and tested. The data is sample data. Run
`outlook.cmd status` any time and it will tell you so.

## What it does

Notices things and tells you. It cannot do anything about them.

| Question | Command |
| --- | --- |
| What does the day look like? | `brief` |
| What is now, and what is next? | `next` |
| Does anything overlap? | `events` |
| What mail is waiting on me? | `attention` |
| What came in? | `mail` or `mail --unread` |
| Who is this sender? | `contacts <name>` |
| Is this connected to anything? | `status` |

## The command

```bash
D:\SANDBOX\Assistan_Building\ASST\4\Source\outlook.cmd status
```

## The day

```bash
outlook.cmd brief
```

Shows the day's appointments, anything that overlaps, and anything with no
response recorded. To look at a different day, put `--now` **before** the
subcommand:

```bash
outlook.cmd --now 2026-08-26T08:00:00Z brief
```

That produces, from the sample data:

```
DAY BRIEF  2026-08-26
  12:00  Pickup - Charlotte NC            Charlotte NC
      120 min   response: accepted
  13:30  Delivery - Richmond VA           Richmond VA
      120 min   response: none

  CONFLICTS
    Pickup - Charlotte NC overlaps Delivery - Richmond VA by 30 min

  NO RESPONSE RECORDED  (this component cannot answer them)
    Delivery - Richmond VA  [none]
```

The conflict is the useful part. Two appointments overlapping by 30 minutes is
the kind of thing that costs a day.

## Now and next

```bash
outlook.cmd next
```

## Mail worth a look

```bash
outlook.cmd attention
```

Each flagged message tells you **why** it was flagged:

```
  Load 123 - please confirm the rate
    from j.reed@example.invalid   2026-08-24 15:10
    noticed because: contains "confirm"; contains "rate change"; marked high importance; unread
    decided: False    acted on: False
```

Those last two are the point. Nothing has been answered, accepted, or decided.

**It will over-flag.** The rule is a visible list of words - `confirm`,
`approve`, `please advise`, `urgent`, and about twenty more. A subscription
confirmation will get flagged. That is the price of a rule you can read and
check in ten seconds.

## Contacts

```bash
outlook.cmd contacts reed
```

```bash
outlook.cmd contacts
```

Searches name, email, company, and role.

## Check what it can and cannot do

```bash
outlook.cmd status
```

```
  live_connection          False
  source                   local sample fixture files, not a live mailbox
  can_send                 False
  can_reply                False
  can_schedule             False
  can_modify               False
  can_accept_or_decline    False
  has_approval_authority   False
```

Those are not settings. There is no code in this component that could do any of
them.

## Point it at different data

```bash
outlook.cmd --data-root "C:\path\to\fixtures" brief
```

The three files it looks for are `calendar.json`, `emails.json`, and
`contacts.json`. A missing file is reported by name and treated as empty. A
**broken** file raises an error rather than quietly reporting an empty calendar.

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\4\Tests\run_tests.cmd
```

63 tests.

## What this will NOT do - read this part

**It will not send anything.** No email, no reply, no forward, no draft. There
is no send method in this component and it does not even import a mail library.

**It will not touch your calendar.** No accepting, declining, scheduling,
rescheduling, or cancelling.

**It will not mark anything read, flag it, file it, or delete it.**

**It will not approve anything.** Not a rate, not a load, not a contract.
Flagging a message means a word matched. It does not mean a decision was made,
and every flag says `decided: False`.

**It will not remember anything.** Nothing is stored between runs.

**It will not reach the network.** There is no networking module in it.

## If something goes wrong

**`py was not found`** — install Python 3.10 or newer from python.org. `python`
on this machine is the Microsoft Store stub, which is why everything uses `py`.

**`unrecognized arguments: --now ...`** — global options go **before** the
subcommand: `outlook.cmd --now 2026-08-26T08:00:00Z brief`.

**`ERROR: malformed JSON in calendar.json`** — the data file is broken. This is
deliberate: it refuses to report an empty calendar from a file it could not
read.

**Everything reports zero** — check `outlook.cmd status` for `missing_files`.
The data root is probably pointing somewhere without the three JSON files.

**An appointment you expected is missing** — check `status` for
`skipped_entries`. An entry with a bad timestamp is skipped, counted, and named
rather than silently dropped.
