# Workstream 1 - Assistant UI - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\1`

---

## Open the window

```bash
D:\SANDBOX\Assistan_Building\ASST\1\Source\run_ui.cmd
```

A window titled **Level 1 Assistant** opens. Close it with the X. Nothing is
left behind.

## What you see

- **Banner**, top of the window. States what this window is not connected to.
  It stays there. It is the truth about this build.
- **Conversation.** Every message, newest at the bottom, each with an id like
  `T001`.
- **Message box and Send.** Type and press Enter, or click Send.
- **Four buttons.** Save, Level 3, Print, Delete. Grey until you select a
  message.
- **Requests recorded in this window.** Every button press you made.
- **Status line**, bottom. What just happened.

## Using it

1. Type a message and press Enter. It appears as `You:`.
2. A line comes back saying no assistant is connected. That is honest, not a
   failure — this window has no reasoning in it.
3. The newest message is selected for you. Click any message to select a
   different one.
4. Press a button.

## What the buttons actually do

Every button records a **request**. None of them carries the request out,
because there is nothing here to carry it out with.

| Button | What happens | What does NOT happen |
| --- | --- | --- |
| **Save** | A save request is recorded | Nothing is saved anywhere |
| **Level 3** | A Level 3 request is recorded | No report is produced |
| **Print** | A print request is recorded | No printer is contacted. Nothing prints. |
| **Delete** | The message is removed from this window and a delete request is recorded | Nothing outside this window is touched |

Every recorded request shows `performed=False`. That is not a bug. It is the
component telling you the truth.

## Nothing is saved when you close it

The conversation and the request list live in memory only. Close the window and
they are gone. This component writes no files at all.

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\1\Tests\run_tests.cmd
```

39 tests, headless — no window opens. Output also lands in
`Tests\_last_test_run.txt`.

## If something goes wrong

**`py was not found`** — Python is not installed, or the `py` launcher is
missing. Install Python 3.10 or newer from python.org. Note that `python` on
this machine is the Microsoft Store stub, not an interpreter, which is why
everything here uses `py`.

**`No module named tkinter`** — Python was installed without tcl/tk. Re-run the
installer and include it. On this machine tkinter 8.6 is present.

**Buttons stay grey** — nothing is selected. Send a message, or click one.

**Window opens behind another window** — check the taskbar for **Level 1
Assistant**.

## What this component will not do

It will not save, file, print, email, look anything up, listen, or speak. It is
the window and nothing else. Connecting it to anything is a separate mission and
a separate decision — yours.
