# Workstream 1 - Assistant UI - Constitution

**Component:** Assistant UI
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\1`.

---

## 1. Authority

Mike Zachary remains final authority. This window presents and records. It
decides nothing operational and has no authority of any kind.

## 2. Isolation - absolute

1. This folder writes no file outside `ASST\1`.
2. This folder imports nothing from workstreams 2, 3, 4, 5, or 6.
3. This folder imports nothing from any earlier project, including the existing
   Sandbox Engine.
4. This folder assumes no other workstream exists.
5. There is no integration code here, and none may be added.

Enforced by `test_imports_nothing_from_another_workstream` and
`test_uses_only_the_standard_library`, which fail on any import outside
`__future__`, `dataclasses`, `datetime`, `itertools`, and `tkinter`.

## 3. Hard prohibitions

There is no code path in this component that could do any of the following, and
tests assert the absence of every import that would be required:

1. Send email, or read email.
2. Reach the network. No networking module is imported at all.
3. Read or write a calendar, contact list, or mailbox.
4. Contact a printer or cause physical printing.
5. Save, file, archive, or retain anything outside this window.
6. Commit money, accept a load, or approve anything.
7. Alter doctrine or policy.
8. Read the Company Library or any research source.
9. Record or play audio.

## 4. It writes nothing to disk

This component has no persistence. The conversation and the action log live in
memory and end when the window closes.

This is deliberate. A reviewer opening folder 1 does not have to ask where
anything went, and a driver pressing Save cannot be misled into thinking a
record now exists somewhere. Enforced by `test_the_package_writes_no_files`,
which fails if `open(`, `Path(`, `os.`, `shutil.`, or `json.dump` appears
anywhere in the package.

## 5. Honesty rules

- **A button records a request, never a completed action.** Every
  `ActionRequest` is created with `performed=False`, and nothing in this
  component can set it to `True`. Enforced by
  `test_no_action_is_ever_marked_performed`.
- **Print never claims printing.** The Print notice reads "No printer was
  contacted."
- **Level 3 never claims a report.** Its notice reads "No report was produced."
- **Save never claims retention.** Its notice reads "Recorded in this window
  only."
- **The window never invents an answer.** With no assistant connected, the
  placeholder reply says exactly that.
- **The disconnection is always visible.** The banner stating what this window
  is not connected to is permanent and cannot be dismissed.

## 6. Structural rules

- All behavior lives in `view_model.py` and the modules it uses. The tkinter
  layer renders and forwards clicks; it holds no logic and constructs neither a
  `Conversation` nor an `ActionLog` of its own. Enforced by
  `test_tkinter_layer_imports_and_holds_no_logic`.
- This is why the component is testable headlessly and why folder 1 can report
  proven behavior rather than only a screenshot.

## 7. What must not happen without a new decision

- Do not connect this window to a retention store, library, mailbox, research
  source, or voice engine. That is integration, and integration is forbidden by
  the build matrix.
- Do not add persistence.
- Do not let `performed` become settable.
- Do not move logic into the tkinter layer.
- Do not remove or soften the disconnection banner.
