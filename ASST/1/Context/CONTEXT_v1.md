# Workstream 1 - Assistant UI - Context

**Component:** Assistant UI
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\1`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

The driver-facing Assistant window. A visible desktop interface with a chat
area, conversation history, and four buttons: Save, Level 3, Print, Delete.

## What it is for

Level 1 Transport's Assistant needs a surface the driver can actually look at
and touch. This is that surface, and only that surface. It shows the
conversation, lets a message be selected, and records which button was pressed
against which message.

## Who operates it

Mike Zachary, owner/operator, frequently driving. Consequences for the design:

- Large, plainly labelled buttons. No icons that need learning.
- Buttons are disabled until a message is selected, so a press cannot land on
  nothing.
- The newest message is selected automatically, so the common case needs no
  aiming.
- Every press produces one short status line stating what is now true.
- A banner at the top of the window states, permanently, that nothing is
  connected. The driver never has to guess whether a press did something real.

## What it is deliberately not

This window is not connected to anything and cannot become connected without a
new mission. It has:

- no retention or memory store
- no Company Library access
- no Outlook, email, calendar, or contacts
- no research
- no voice
- no reasoning of its own

When the driver sends a message, the window records it and adds a placeholder
line that says in plain words that no assistant is connected. It never invents
an answer.

## What the buttons mean here

Each button records a **request**. A request is a statement of what the driver
asked for. It is never a claim that the thing happened.

| Button | What it records | What it does NOT do |
| --- | --- | --- |
| Save | A save request against the selected message | Does not save anything anywhere |
| Level 3 | A Level 3 request against the selected message | Does not produce a report |
| Print | A print request against the selected message | Does not contact a printer |
| Delete | A delete request, and removes the message from this window | Does not delete anything outside this window |

Delete is the only button that changes what is on screen, and its effect stops
at the window.

## Runtime

Python 3.10 or newer through the `py` launcher, plus tkinter, which ships with
Python on Windows. Verified on this machine: Python 3.14.5, tkinter 8.6.
Nothing is installed. No third-party package is used.

## Relationship to other workstreams

None. By rule, this folder does not know any other workstream exists. It
imports nothing from folders 2 through 6 and nothing from any earlier project.
A reviewer can read folder 1 alone and understand the whole component.
