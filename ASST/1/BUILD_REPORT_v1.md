# Workstream 1 - Assistant UI - Build Report

**Component:** Assistant UI
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\1`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build a visible desktop interface: driver-facing Assistant window, chat area,
conversation history, and Save / Level 3 / Print / Delete buttons.

UI only. No Outlook. No Voice. No Research. No Library. No Memory connection
required.

## FILES CREATED

```
ASST\1\
  README.md                                  reviewer entry point
  BUILD_REPORT_v1.md                         this file
  TEST_REPORT_v1.md                          full test results
  Context\CONTEXT_v1.md                      what this is and who operates it
  Constitution\CONSTITUTION_v1.md            binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md            module design and contracts
  Operator_Guide\OPERATOR_GUIDE_v1.md        how Mike runs it
  Source\run_ui.cmd                          launcher - opens the window
  Source\assistant_ui\__init__.py            package exports
  Source\assistant_ui\__main__.py            py -m assistant_ui entry
  Source\assistant_ui\conversation.py        Turn, Conversation, selection
  Source\assistant_ui\actions.py             ActionKind, ActionRequest, ActionLog
  Source\assistant_ui\view_model.py          every decision the window makes
  Source\assistant_ui\window.py              tkinter window
  Tests\run_tests.cmd                        test launcher
  Tests\test_assistant_ui.py                 39 tests
  Tests\_last_test_run.txt                   raw output of the last run
  Tests\_window_screenshot.png               the window, captured on screen
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\1\Tests\run_tests.cmd
D:\SANDBOX\Assistan_Building\ASST\1\Source\run_ui.cmd
py -m assistant_ui
```

Plus a scripted launch-and-capture that opened the window on this desktop,
populated it, brought it to the foreground, and saved the cropped screenshot.

## TEST RESULTS

**39 tests. 39 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestConversation` | 12 |
| `TestActionLog` | 5 |
| `TestViewModel` | 16 |
| `TestBoundaries` | 6 |

Detail in `TEST_REPORT_v1.md`. Raw output in `Tests\_last_test_run.txt`.

## PROVEN CAPABILITIES

1. A visible desktop window opens, titled Level 1 Assistant. Captured on screen
   in `Tests\_window_screenshot.png`.
2. Chat area accepts typed messages.
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

1. Mouse click-to-select in the running window. Logic tested; the click path is
   not automated.
2. The Enter-key binding. Its handler is tested; the binding is not.
3. Button clicks in the running window. Each is wired to a tested method; the
   click path is not automated.
4. Window resizing and minimum-size behavior.
5. Scrolling past the visible area with a long conversation.
6. Rendering at a different DPI, screen scale, or theme.
7. Behavior over a long session. The longest test is 50 turns.

## NOT IMPLEMENTED

1. Any connection to a memory or retention store.
2. Any connection to Company Library.
3. Any connection to Outlook, email, calendar, or contacts.
4. Any research capability.
5. Any voice input or output.
6. Any reasoning. The assistant reply is a fixed placeholder that says so.
7. Persistence. Nothing survives closing the window.
8. Producing a report, saving a record, or printing.
9. Message editing, search, export, or copy-to-clipboard.
10. Multiple conversations, tabs, or sessions.
11. Keyboard shortcuts other than Enter to send.
12. Accessibility beyond large high-contrast controls.
13. Any installer or packaged executable.

## KNOWN LIMITATIONS

1. Closing the window discards everything. By design.
2. The assistant reply is a placeholder. This window cannot answer anything.
3. Ids restart at 001 every launch, since nothing persists.
4. All four buttons share one enablement rule.
5. Delete cannot be undone. Nothing outside the window is affected.
6. tkinter is required. A stripped Python install would break the window while
   leaving the tested logic intact.
7. Verified on Windows 11, Python 3.14.5, tkinter 8.6, one display, one DPI.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. Folder 1 imports nothing from
folders 2-6 and nothing from any earlier project. No knowledge of any other
workstream is needed to review it.

**The one design decision worth your attention.** Every decision the window
makes lives in `view_model.py`; `window.py` only draws and forwards clicks. A
window that can only be checked by looking at it cannot be proven, so the logic
was moved somewhere a test can reach it. That is why this report can list
fourteen proven capabilities instead of one screenshot.

**How honesty is enforced, not just intended.** Each `ActionRequest` is built
with `performed=False` and no code path can change it. The four button notices
are fixed strings at the top of `actions.py` — one place to read, one place to
audit. The disconnection banner is permanent and cannot be dismissed.

**Deliberately writes nothing to disk.** No persistence was added even though a
window like this usually has some. A driver pressing Save must not be able to
believe a record now exists somewhere. A test fails the build if any file-write
call appears in the package.

**No integration, per the build matrix.** The buttons record requests that
nothing consumes. That gap is intended and is where a future mission would
connect this window to a retention store — a separate decision, yours to make.

**Boundary note for the reviewer.** `Tests\test_assistant_ui.py` reads the
package source to check imports. It reads only files inside folder 1.
