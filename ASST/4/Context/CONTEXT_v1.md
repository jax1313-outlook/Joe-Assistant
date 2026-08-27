# Workstream 4 - Assistant Outlook - Context

**Component:** Assistant Outlook
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\4`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

Read-only awareness of three things:

- **Calendar** - what is scheduled, what is next, what overlaps, what has no
  response recorded
- **Email** - what arrived, what is unread, what looks like it is waiting on a
  person
- **Contacts** - who a sender is, and how to reach them

## Awareness, not action

The word in the mission is *awareness*, and it is the whole boundary. This
component notices and reports. It does not act.

It cannot send, reply, forward, accept, decline, schedule, reschedule, mark
read, flag, move, delete, or approve. Those are not disabled - there is no such
method anywhere in the component, and the provider port that supplies the data
defines exactly three methods, all reads.

Outlook remains scheduling authority and email transport. This component reads
what Outlook knows and says what it sees.

## The most important limitation, stated first

**There is no live Outlook connection.** No Microsoft Graph, no Exchange, no
MAPI, no COM, no credentials, no network access of any kind.

What exists is a **provider port** with three read methods, and one provider
that reads sample JSON fixture files from `ASST\4\Data`. A live provider is
**NOT IMPLEMENTED** and would be a separate mission requiring authentication and
network access that this build deliberately does not have.

So: the awareness logic is real and tested. The data it reads is sample data.
Both facts are reported by `outlook.cmd status`, which prints
`live_connection: False` and `source: local sample fixture files, not a live
mailbox` every time it runs.

## What "flagged" means, exactly

The component flags mail that looks like it is waiting on someone. It does this
by matching a visible list of words - `confirm`, `approve`, `please advise`,
`rate change`, and about twenty more - against the subject and preview, plus
unread state, importance, and age.

That is **pattern matching, not judgement**. A flagged message carries the
reason it was flagged, so the driver can see why. Every flag reports
`decided: False` and `acted_on: False`, because nothing has been answered,
accepted, or decided.

A message about "confirming your subscription" will be flagged. That is the
cost of a rule simple enough to audit, and it is stated rather than hidden
behind a cleverer rule nobody can check.

## What the driver gets from it

| Question | Command |
| --- | --- |
| What does tomorrow look like? | `brief` |
| What is happening now, and next? | `next` |
| Does anything overlap? | `events` - conflicts are computed and shown |
| What mail is waiting on me? | `attention` |
| Who is this sender? | `contacts` |

Conflict detection is the piece worth having: two appointments that overlap is
exactly the sort of thing that costs a day, and it is arithmetic rather than
opinion.

## What it deliberately is not

- no sending, replying, or drafting
- no scheduling or calendar modification
- no accepting or declining invitations
- no approval authority of any kind
- no retention or memory - nothing is stored between runs
- no library, research, or voice
- no network access

## Runtime

Python 3.10 or newer through the `py` launcher. Verified on this machine:
Python 3.14.5. Standard library only. Nothing is installed, and notably no
`exchangelib`, `O365`, `msal`, or `pywin32`.

## Relationship to other workstreams

None. This folder does not know any other workstream exists. It imports nothing
from folders 1, 2, 3, 5, or 6.
