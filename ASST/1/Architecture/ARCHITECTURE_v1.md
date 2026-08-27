# Workstream 1 - Assistant UI - Architecture

**Component:** Assistant UI
**Version:** 1.0.0

---

## 1. Shape

```
                 +-----------------------------+
                 |        window.py            |   tkinter widgets only.
                 |  draws, forwards clicks     |   No decisions. Not unit-tested.
                 +--------------+--------------+
                                |  calls
                                v
                 +-----------------------------+
                 |      view_model.py          |   EVERY decision lives here.
                 |  send / select / press      |   Fully tested, headless.
                 |  button enablement, status  |
                 +------+---------------+------+
                        |               |
                        v               v
            +----------------+   +----------------+
            | conversation.py|   |   actions.py   |
            | turns,         |   | ActionRequest, |
            | selection      |   | ActionLog      |
            +----------------+   +----------------+
```

The split exists for one reason: a window that can only be checked by looking
at it cannot be proven. Putting every decision in `view_model.py` makes the
whole behavior of this component testable without a display, which is why the
build report can list proven capabilities instead of a screenshot alone.

## 2. Modules

| Module | Responsibility | Tested |
| --- | --- | --- |
| `conversation.py` | `Turn`, `Conversation`. Ordered turns, id assignment, selection, removal. | Yes, 12 tests |
| `actions.py` | `ActionKind`, `ActionRequest`, `ActionLog`. Records button presses as requests. | Yes, 5 tests |
| `view_model.py` | `AssistantUIViewModel`, `ViewState`, `ButtonState`. Send, select, press, button enablement, status line, full render snapshot. | Yes, 15 tests |
| `window.py` | tkinter window. Layout, event wiring, rendering a `ViewState`. | Import and structure only |
| `__main__.py` | `py -m assistant_ui` entry point. | No |

Dependency direction is one way: `window` → `view_model` → {`conversation`,
`actions`}. Nothing points back up.

## 3. The ViewState contract

`view_model.view_state()` returns one complete snapshot of what the window
should show:

```
  title            window title
  banner           the permanent "not connected" line
  history          one display string per turn
  selected_id      the turn the buttons act on, or None
  selected_text    text of that turn
  status           one line describing the last thing that happened
  buttons          four ButtonState entries: kind, label, enabled
  action_history   one display string per recorded request
  turn_count       number of turns
  request_count    number of requests
```

`window.py` reads this and draws it. It never asks the conversation or the
action log anything directly.

## 4. Selection and button enablement

All four buttons share one rule: **enabled if and only if a turn is selected.**

Selection moves automatically so the driver rarely has to aim:

- adding a turn selects it
- deleting the selected turn selects its neighbour
- deleting the last turn clears the selection and disables the buttons

A press with nothing selected is refused with `Select a message first.` and
records nothing.

## 5. Actions are requests

```
  press(kind)
      |
      +-- nothing selected?  ->  status = "Select a message first."   (no record)
      |
      +-- record ActionRequest{ kind, turn_id, turn_text, performed=False }
              |
              +-- kind == DELETE  ->  also remove the turn from the conversation
              |
              +-- status = the notice for that kind
```

`performed` is set to `False` at construction and there is no code path that
changes it. That single flag is how this component stays honest: the log shows
what was asked for, and shows that it was not carried out.

Notices are fixed strings, so the honesty rules are reviewable in one place at
the top of `actions.py`:

| Kind | Notice |
| --- | --- |
| SAVE | Save requested. Recorded in this window only. |
| LEVEL_3 | Level 3 requested. No report was produced. |
| PRINT | Print requested. No printer was contacted. |
| DELETE | Removed from this window. Nothing else was changed. |

## 6. Send behavior

This window has no reasoning. `send()` adds the driver's turn, then adds a
placeholder assistant turn whose text states plainly that no assistant is
connected. The placeholder exists so history, selection, and buttons can be
exercised. It is never presented as an answer.

Blank or whitespace-only input is refused with `Nothing to send.` and adds
nothing.

## 7. State that exists, and where it lives

| State | Lives in | Survives closing the window? |
| --- | --- | --- |
| Conversation turns | memory | No |
| Selection | memory | No |
| Action log | memory | No |

Nothing is written to disk. See the constitution, section 4.

## 8. What was deliberately left out

- No persistence, so no file format to design and no migration to maintain.
- No scrollback limit, message search, or editing. Not asked for.
- No theming system. Colors are five constants at the top of `window.py`.
- No accessibility work beyond large controls and high contrast. Screen-reader
  behavior is untested and is declared as such.
- No integration point of any kind, by rule.
