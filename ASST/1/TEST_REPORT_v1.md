# Workstream 1 - Assistant UI - Test Report

**Component:** Assistant UI
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, tkinter 8.6, standard library only

---

## Result

**39 tests. 39 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\1\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_ui.py`.

The suite is headless. No window opens while it runs.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestConversation` | 12 | Turn ids are sequential, new turns become selected, blank text and unknown speakers are refused, text is stripped, history lines label the speaker, removal moves the selection correctly, timestamps are UTC ISO with `Z`. |
| `TestActionLog` | 5 | One request per press, sequential request ids, every request marked `performed=False`, unknown actions refused, filtering by kind and by turn. |
| `TestViewModel` | 16 | Opens empty with all buttons disabled, all four buttons present and labelled, send adds a turn, blank send refused, buttons enable on selection, presses with nothing selected refused, each of the four actions behaves and reports correctly, delete removes only from the window, unknown selection changes nothing, status and action history render, view state serializes, 25 sends produce 50 turns. |
| `TestBoundaries` | 6 | No import from another workstream, no network/email/vendor import, standard library only, package writes no files, no action is ever marked performed, tkinter layer holds no logic. |

## Visible window - proven on screen

The window was launched on this desktop, populated, brought to the foreground,
and captured. Evidence: `Tests\_window_screenshot.png` (916 x 719, cropped to
the window).

The capture shows, in the running application:

- title bar reading **Level 1 Assistant**
- the permanent disconnection banner
- four conversation turns `T001`-`T004` with speaker labels
- `T004` selected and highlighted
- all four buttons — Save, Level 3, Print, Delete — rendered and enabled

A separate scripted probe constructed the window, sent a message, refreshed,
and read back the live widget state: title `Level 1 Assistant`, four buttons
present and enabled, 2 history rows rendered, status `Sent.`

## Boundary verification

Imports across the whole package, measured by the suite:
`__future__`, `dataclasses`, `datetime`, `itertools`, `tkinter`. Nothing else.
No third party. No networking module. No workstream 2-6 import. No import of
the existing Sandbox Engine.

`test_the_package_writes_no_files` fails if `open(`, `Path(`, `os.`, `shutil.`,
or `json.dump` appears anywhere in the package. It passes: this component
writes nothing to disk.

---

## PROVEN CAPABILITIES

1. A visible desktop window opens, titled Level 1 Assistant. Captured on screen.
2. Chat area accepts typed messages via Enter or the Send button.
3. Conversation history displays every turn with id and speaker label.
4. Message selection, including automatic selection of the newest turn.
5. All four required buttons exist, are labelled, and enable only on selection.
6. Save records a request and changes nothing else.
7. Level 3 records a request and produces no report.
8. Print records a request and contacts no printer.
9. Delete removes the message from the window and records a request.
10. Presses with nothing selected are refused and record nothing.
11. No request is ever marked performed.
12. Blank input is refused.
13. The component writes no files.
14. The component imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. **Mouse click-to-select in the running window.** Selection logic is fully
   tested through the view model, and the handler is wired, but no automated
   test drives a real mouse click on the listbox.
2. **The Enter-key binding in the running window.** Wired to the same handler as
   the Send button; the handler is tested, the key binding itself is not.
3. **Button clicks in the running window.** Each command is wired to a tested
   view-model method; the click path itself is not automated.
4. **Window resizing and minimum-size behavior.** Set to 900x680 with a 720x520
   minimum. Not exercised.
5. **Scrolling with a long conversation.** The scrollbar is wired; behavior past
   the visible area is untested.
6. **Rendering on a different DPI, screen scale, or theme.** Verified on this
   display only.
7. **Behavior over a long session.** Longest test is 50 turns.

## NOT IMPLEMENTED

1. Any connection to a memory or retention store.
2. Any connection to Company Library.
3. Any connection to Outlook, email, calendar, or contacts.
4. Any research capability.
5. Any voice input or output.
6. Any reasoning. The assistant reply is a fixed placeholder that says so.
7. Persistence of any kind. Nothing survives closing the window.
8. Producing a report, saving a record, or printing.
9. Message editing, search, export, or copy-to-clipboard.
10. Multiple conversations, tabs, or sessions.
11. Keyboard shortcuts other than Enter to send.
12. Accessibility support beyond large high-contrast controls.
13. Any installer or packaged executable.

## KNOWN LIMITATIONS

1. Closing the window discards the conversation and the request list. By design;
   see the constitution, section 4.
2. The assistant reply is a placeholder. This window cannot answer anything.
3. Request ids and turn ids restart at 001 every launch, since nothing persists.
4. The four buttons share one enablement rule. There is no per-button
   eligibility, because this component has no state that would justify one.
5. Deleting is immediate and cannot be undone. Nothing outside the window is
   affected.
6. tkinter is required. It ships with Python on Windows but a stripped install
   would break the window while leaving the tested logic intact.
7. Verified on Windows 11, Python 3.14.5, tkinter 8.6, one display, one DPI.
