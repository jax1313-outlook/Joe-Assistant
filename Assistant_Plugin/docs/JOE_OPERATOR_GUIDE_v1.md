# JOE - Operator Guide

**For:** Mike Zachary
**Program:** JOE, the Level 1 Assistant
**Folder:** `D:\SANDBOX\Assistan_Building\Assistant_Plugin`

---

## Open it

Double-click:

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\START_JOE.cmd
```

A window opens. No console, no typing commands. Takes about five seconds the
first time.

Close it with the X. Nothing else is affected - **Dispatch does not know this
program exists.**

## What you see

- **Title and the plugin statement.** A permanent line saying Dispatch remains
  the System of Record and that JOE may recommend but may not
  approve, decide, or change operational truth.
- **Operating mode.** What is live right now.
- **Status chips.** Library / Outlook / Research / Voice / Dispatch, each
  coloured. Hover any chip for the full detail.
- **Interaction history**, left. Every interaction with its state and level.
  The selected one is marked `>`.
- **Response**, right. The direct answer first, then the full written response,
  then uncertainty, then sources, then the authority line.
- **Buttons**: Save, Level 3, Print, Delete.
- **Quick access**: Library search, Research, Calendar, Unread mail, Speak
  answer, Listen, Help.
- **Type box and Ask.**
- **Status line**, bottom.

## Just type

Ordinary sentences. No syntax, no record numbers, no menus.

```
What is on my calendar?
Find the rate floor policy
Explain that in plain language
Show me unread mail
Who is J. Reed
Research the northbound lane
help
```

Press Enter or click Ask.

## Keeping things

Everything you ask starts **temporary** and disappears in three hours. To keep
it, say so - or press the button. Both do the same thing.

```
Save this                     keeps it (Level 2)
Level 3 this                  makes it formal (Level 3)
Level 3 this under Ideas      formal, filed under Ideas
Print this                    marks it print ready
Delete this                   removes it now
```

| | State becomes | Level becomes | Expires? |
| --- | --- | --- | --- |
| **Save** | SAVED | LEVEL_2 | no |
| **Level 3** | FORMAL | LEVEL_3 | no |
| **Print** | PRINT_READY | **unchanged** | no |
| **Delete** | DELETED | — | content erased |

Print leaving the level alone is deliberate. Print is a state, not a level.

Commands act on **the selected interaction**. Click a different one in the
history first if you want to act on that instead.

## What each capability actually does

**Library** — searches the real Company Library plus a small labelled sample
corpus. Results say which source they came from. It never invents a document,
and it never dresses a sample up as Company Library material.

**Outlook** — reads your real calendar, mail, and contacts, **read-only**. It
does not open on startup; it connects the first time you ask for calendar,
mail, or a contact, which takes a few seconds. It cannot send, reply, accept,
decline, schedule, move, delete, or mark anything read. There is no such code
in it.

The **calendar comes back in date order, soonest first**, covering the next
14 days from midnight today, with recurring events expanded. Every calendar
answer states its window and its ordering, so you can see what you are looking
at:

```
Window: 2026-08-25 to 2026-09-08  (14 days)
Order:  date order, recurring events included
```

To look further ahead, raise `outlook.calendar_window_days` in
`configurationssistant.config.json`. If Outlook ever fails to sort or filter,
the answer says so in plain words rather than quietly handing you a jumbled
list.

**Research** — **no research provider is connected.** What you get is a sample
brief, labelled SAMPLE DATA everywhere it appears. It is not internet research
and is never presented as such.

**Voice** — Windows speech, working. Press **Speak answer** to hear the short
form of the selected answer. Press **Listen**, speak, and what it heard goes
into the type box for you to check before sending. It never speaks unless you
ask it to.

**Reasoning** — **Microsoft 365 Copilot, PILOT / PREVIEW.** Selected but not
signed in. Press **Settings** in the window to see the connection, sign in, or
disconnect. Until you sign in, JOE will not compose answers and says
so rather than guessing.

Signing in needs things only you can do: an Entra app registration, its tenant
and client id in the configuration, admin consent on seven delegated Graph
permissions, and a work or school account with a Copilot licence. Your personal
`outlook.com` account will not work — Microsoft's API does not support personal
accounts.

Your Microsoft sign-in is held by MSAL in a **Windows-encrypted** token cache.
No token, secret, or password is written in plain text, logged, or shown
anywhere — including in the Settings panel. **Disconnect and clear
authentication** removes it entirely.

**Dispatch** — **not connected.** No interface has been published to connect
to. JOE can never write to Dispatch regardless.

## When something is not available

The program says so, plainly, and keeps working:

```
Outlook is not connected. I cannot read the live calendar.
Voice is unavailable. Text mode remains available.
No approved Library location is configured.
Research provider is unavailable. No live research was performed.
Print request recorded. Nothing was physically printed.
```

It will not substitute sample data for something real, and it will not guess.

## The honest limitation

**There is no reasoning provider connected.** This program cannot compose an
original answer to an open question.

Ask it something it has no source for and it will tell you there is no source,
rather than producing something that reads like an answer. That is deliberate.

What it is genuinely good at: finding what already exists, reading what
arrived, keeping what matters, and letting the rest expire.

## The other buttons

```
D:\...\Assistant_Plugin\launchers\
    JOE_STATUS.cmd     what is connected, is the window running
    STOP_JOE.cmd       close it
    RESTART_JOE.cmd    close and reopen
    RUN_TESTS.cmd            259 automated tests
    RUN_PROOF.cmd            24 operational proof steps
    PROVE_COPILOT.cmd        sends ONE real prompt to Microsoft 365 Copilot.
                             Asks you to sign in. Blocked until an Entra app
                             registration exists - see COPILOT_ACTIVATION_STEPS.md
    PROVE_VOICE_INPUT.cmd    asks you to speak three phrases and records what
                             the recognizer heard. Cannot pass without your voice, writes a report
    OPEN_LOGS.cmd            open the log folder
    OPEN_DATA.cmd            open your saved records
```

## Where your records are

```
Assistant_Plugin\runtime_data\memory\active\     what is kept
Assistant_Plugin\runtime_data\memory\expired\    what ran out of time
Assistant_Plugin\runtime_data\memory\deleted\    what you deleted
```

Plain JSON files. Open any in Notepad. Expired and deleted ones have their
content erased - only the timestamps and the reason remain.

## Two things worth knowing

**Nothing expires on a timer.** Records expire when the program checks, and it
checks every time it shows you the history. If you never open it, nothing
expires. That is a real limitation, not a feature.

**Closing the window keeps your saved records.** Anything Saved, Level 3, or
Print Ready is still there next time. Temporary ones may have expired.

## Adding a Library location

Edit `configuration\joe.config.json`, under `library.sources`. Add a
name, a path, and `"kind": "company"` for approved company material or
`"sample"` for anything else. Restart JOE.

It only ever reads. It has no write capability to enable.

## If something goes wrong

**Nothing happens when you double-click** — Python may not be installed. Get
3.10 or newer from python.org. Then run `launchers\JOE_STATUS.cmd` from a
terminal to see the error.

**"Outlook is not connected"** — Outlook may be mid-start, or a dialog may be
waiting. Try once more; it allows 90 seconds.

**The window sits on "Working..."** — an Outlook read is in progress. It cannot
freeze the window; it will come back or report a timeout.

**A capability failed** — the message names it and the rest keeps working.
Detail is in `logs\joe.log`.

**You want it gone** — delete the whole `Assistant_Plugin` folder. Dispatch is
unaffected. That is what "plugin" means here.

## Authority

JOE may monitor, explain, research, retrieve, summarize, draft,
recommend, remember, surface uncertainty, and submit requests.

It may not approve, decide, own Dispatch records, alter operational truth, or
act because you did not answer.

**Silence is never consent. Mike Zachary remains final authority.**
