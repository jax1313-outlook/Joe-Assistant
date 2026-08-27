"""OPERATOR CONTROL AUDIT.

Mike operated JOE and reported that some controls work and some do not. That
finding governs: a passing test suite does not overrule it, and neither does a
passing proof script. This audit drives every visible control the way a person
would and records what actually happens.

The rules it holds every control to:

    no control may do nothing silently
    no control may claim success without completing the action
    no control may act on the wrong selected record
    no control may create an interaction that steals selection
    no control may display stale capability status
    no control may hide its failure only in the log

Run:   py proof\\audit_controls.py
Writes evidence to proof\\CONTROL_AUDIT.md.

Needs a display. It builds the real window, invokes the real handlers, and
never simulates a click it did not make.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74
PASS, FAIL, PARTIAL, UNCLEAR = "PASS", "FAIL", "PARTIAL", "UNCLEAR"


class Audit:
    def __init__(self):
        self.rows = []

    def record(self, control, expected, actual, result, files="", note=""):
        self.rows.append({
            "control": control, "expected": expected, "actual": actual,
            "result": result, "files": files, "note": note,
        })
        print("  %-18s %-8s %s" % (control, result, actual[:74]))

    @property
    def failures(self):
        return [r for r in self.rows if r["result"] in (FAIL, PARTIAL)]


def pump(window, seconds=0.4):
    """Let tkinter process queued work, as a real click would."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            window.root.update()
        except Exception:  # noqa: BLE001 - window closed
            return
        time.sleep(0.02)


def settle(window, seconds=25.0):
    """Wait for a background worker to finish, without freezing the audit."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            window.root.update()
        except Exception:  # noqa: BLE001
            return
        if not window.busy:
            return
        time.sleep(0.05)


def main() -> int:
    import tkinter
    from tkinter import messagebox

    from app.config import Config
    from app.service import AssistantService
    from ui.window import AssistantWindow

    print(DIVIDER)
    print("JOE - OPERATOR CONTROL AUDIT")
    print(DIVIDER)
    print()

    audit = Audit()
    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json")
    )
    # Delete asks for confirmation. The audit answers yes, deliberately and
    # visibly, rather than bypassing the prompt.
    original_ask = messagebox.askyesno
    messagebox.askyesno = lambda *a, **k: True

    window = None
    try:
        window = AssistantWindow(service)
        window.root.withdraw()          # built for real; kept off-screen
        pump(window)

        audit_ask(audit, window)
        audit_history_and_actions(audit, window, service)
        audit_quick_buttons(audit, window)
        audit_settings(audit, window)
        audit_status_freshness(audit, window, service)

        print()
        print(DIVIDER)
        failures = audit.failures
        print("RESULT: %d controls audited, %d need work"
              % (len(audit.rows), len(failures)))
        print(DIVIDER)
        write_report(audit)
        print()
        print("Evidence written to  proof\\CONTROL_AUDIT.md")
        return 0 if not failures else 1
    finally:
        messagebox.askyesno = original_ask
        try:
            if window is not None:
                window.root.destroy()
        except Exception:  # noqa: BLE001
            pass
        service.shutdown()


def audit_ask(audit, window):
    """Ask / Send, and the Return key that shares its path."""
    window.entry.delete(0, "end")
    window.entry.insert(0, "help")
    window._on_send()
    settle(window)
    pump(window)
    text = window.response.get("1.0", "end").strip()
    audit.record(
        "Ask", "typed question produces a written answer",
        ("answer rendered, %d chars" % len(text)) if text else "NOTHING RENDERED",
        PASS if text else FAIL, "ui/window.py::_on_send")

    audit.record(
        "Entry cleared", "the box empties so the next question can be typed",
        "entry = " + repr(window.entry.get()),
        PASS if not window.entry.get() else FAIL, "ui/window.py::_on_send")

    audit.record(
        "Busy released", "controls usable again once the answer arrives",
        "busy = " + str(window.busy),
        PASS if not window.busy else FAIL, "ui/window.py::_set_busy")


def audit_history_and_actions(audit, window, service):
    """History selection, then Save / Level 3 / Print / Delete on it."""
    if not window._rows:
        audit.record("History", "asked questions appear in history",
                     "HISTORY EMPTY after asking", FAIL, "ui/window.py::_refresh_history")
        return

    window.history.selection_clear(0, "end")
    window.history.selection_set(0)
    window._on_select()
    pump(window)
    selected = service.selected()
    audit.record(
        "History select", "clicking a row selects that interaction",
        ("selected " + selected.record_id) if selected else "NOTHING SELECTED",
        PASS if selected else FAIL, "ui/window.py::_on_select")

    if selected is None:
        return

    # Each action is checked against the record it was supposed to act on -
    # acting on the wrong record is a specific prohibited failure.
    # A FRESH interaction per action. The first pass of this audit selected
    # whatever sat at the top of history - an old record already at
    # LEVEL_3/FORMAL - and then reported Save and Print as broken because they
    # could not demote it. The controls were fine; the audit was testing
    # against an unknown starting state, which is not a test.
    for label, intent, expect in (
        ("Save", "LEVEL_2", ("LEVEL_2", "SAVED")),
        ("Print", "PRINT", ("LEVEL_1", "PRINT_READY")),
        ("Level 3", "LEVEL_3", ("LEVEL_3", "FORMAL")),
    ):
        window.entry.delete(0, "end")
        window.entry.insert(0, "help")
        window._on_send()
        settle(window)
        pump(window)
        target = service.selected()
        if target is None:
            audit.record(label, "acts on the selected interaction",
                         "nothing selected", FAIL, "ui/window.py::_on_action")
            continue
        target_id = target.record_id
        window._on_action(intent)
        pump(window)
        try:
            record = service.memory.store.load(target_id)
            actual = record.interaction_level + " / " + record.state
            ok = record.state == expect[1]
            # Print must NOT raise the interaction level - Doctrine C4.
            if intent == "PRINT" and record.interaction_level != "LEVEL_1":
                ok = False
                actual += "  (Print changed the level - Doctrine C4 breach)"
        except Exception as error:  # noqa: BLE001
            actual, ok = "record unreadable: " + str(error), False
        audit.record(label, "%s -> %s on the SELECTED record" % (label, expect[1]),
                     actual, PASS if ok else FAIL, "ui/window.py::_on_action")

        still = service.selected()
        audit.record(
            label + " selection", "the same record stays selected",
            (still.record_id if still else "(none)") + (" == " + target_id
                                                        if still and still.record_id == target_id
                                                        else " != " + target_id),
            PASS if still and still.record_id == target_id else FAIL,
            "app/service.py::apply_retention")

    # Delete last, on a fresh interaction so nothing else is disturbed.
    window.entry.delete(0, "end")
    window.entry.insert(0, "help")
    window._on_send()
    settle(window)
    pump(window)
    victim = service.selected()
    if victim is None:
        audit.record("Delete", "removes the selected interaction",
                     "no interaction to delete", UNCLEAR, "ui/window.py::_on_action")
        return
    victim_id = victim.record_id
    window._on_action("DELETE")
    pump(window)
    try:
        record = service.memory.store.load(victim_id)
        state = record.state
    except Exception:  # noqa: BLE001
        state = "purged"
    audit.record("Delete", "the selected interaction becomes DELETED",
                 "state = " + state,
                 PASS if state in ("DELETED", "purged") else FAIL,
                 "ui/window.py::_on_action")


def audit_quick_buttons(audit, window):
    """The quick-access row. Each must do something visible, or say why not."""
    checks = (
        ("Library search", window._on_library, "searches the Library", True),
        ("Research", window._on_research, "researches the typed subject", True),
        ("Calendar", lambda: window._ask_text("What is on my calendar?"),
         "reads the calendar", True),
        ("Unread mail", lambda: window._ask_text("Show me unread mail"),
         "reads mail", True),
        ("Help", lambda: window._ask_text("help"), "shows what JOE can do", True),
        ("Speak answer", window._on_speak, "speaks the selected answer", False),
    )
    for label, handler, expected, needs_text in checks:
        window.entry.delete(0, "end")
        if needs_text and label in ("Library search", "Research"):
            window.entry.insert(0, "detention")
        before_status = window.status_line.cget("text")
        before_body = window.response.get("1.0", "end")
        try:
            handler()
        except Exception as error:  # noqa: BLE001
            audit.record(label, expected, "RAISED " + type(error).__name__ + ": "
                         + str(error)[:60], FAIL, "ui/window.py")
            continue
        settle(window)
        pump(window)
        after_status = window.status_line.cget("text")
        after_body = window.response.get("1.0", "end")
        changed = (after_body != before_body) or (after_status != before_status)
        audit.record(
            label, expected,
            ("something changed on screen" if changed
             else "NOTHING CHANGED - silent no-op"),
            PASS if changed else FAIL, "ui/window.py")


def audit_settings(audit, window):
    """Settings must open without raising and without exposing secrets."""
    try:
        import ui.settings_panel as panel_module
        opened = {}

        class Spy(panel_module.SettingsPanel):
            def __init__(self, parent, service):
                super().__init__(parent, service)
                opened["panel"] = self

        original = panel_module.SettingsPanel
        panel_module.SettingsPanel = Spy
        try:
            window._on_settings()
            pump(window)
        finally:
            panel_module.SettingsPanel = original

        spy = opened.get("panel")
        if spy is None:
            audit.record("Settings", "opens the connection panel",
                         "panel did not open", FAIL, "ui/settings_panel.py")
            return
        text = spy.status_text.get("1.0", "end")
        leaked = [m for m in ("access_token", "refresh_token", "Bearer ", "eyJ")
                  if m in text]
        audit.record("Settings", "opens and shows connection state",
                     "opened, %d chars rendered" % len(text.strip()),
                     PASS if text.strip() else FAIL, "ui/settings_panel.py")
        audit.record("Settings secrets", "no token material on screen",
                     "leaked: " + (", ".join(leaked) if leaked else "none"),
                     PASS if not leaked else FAIL, "ui/settings_panel.py")
        try:
            spy.window.destroy()
        except Exception:  # noqa: BLE001
            pass
    except Exception as error:  # noqa: BLE001
        audit.record("Settings", "opens the connection panel",
                     "RAISED " + type(error).__name__ + ": " + str(error)[:60],
                     FAIL, "ui/settings_panel.py")


def audit_status_freshness(audit, window, service):
    """The status line must match what the service actually reports."""
    try:
        window._refresh_status()
        pump(window)
    except Exception as error:  # noqa: BLE001
        audit.record("Status line", "shows current capability state",
                     "RAISED " + type(error).__name__, FAIL, "ui/window.py")
        return
    # The chips live in status_strip. status_line is the last-action message -
    # reading that reported "Spoken aloud." as if it were a capability state.
    truth = {s.name: s.chip() for s in service.status()}
    shown = " ".join(
        child.cget("text") for child in window.status_strip.winfo_children()
        if hasattr(child, "cget")
    ).strip()
    missing = [name for name, chip in truth.items() if chip not in shown]
    audit.record(
        "Status freshness", "the chips match what the service reports",
        "shown: " + shown[:70],
        PASS if not missing else PARTIAL,
        "ui/window.py::_refresh_status",
        note="not shown: " + ", ".join(missing) if missing else "")


def write_report(audit) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    failures = audit.failures
    lines = [
        "# JOE - Operator Control Audit",
        "",
        "**Run:** " + stamp,
        "",
        "Mike operated JOE and reported that some controls work and some do "
        "not. That finding governs. A passing test suite does not overrule it.",
        "",
        "**" + str(len(audit.rows)) + " controls audited. "
        + str(len(failures)) + " need work.**",
        "",
        "| Control | Expected | Actual | Result | Files |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in audit.rows:
        lines.append("| " + " | ".join((
            row["control"],
            row["expected"],
            row["actual"].replace("|", "\\|"),
            "**" + row["result"] + "**",
            "`" + row["files"] + "`" if row["files"] else "-",
        )) + " |")
    lines.append("")
    if failures:
        lines += ["## Controls needing work", ""]
        for row in failures:
            lines += ["### " + row["control"] + " - " + row["result"], "",
                      "- Expected: " + row["expected"],
                      "- Actual: " + row["actual"],
                      "- Files: `" + (row["files"] or "-") + "`", ""]
            if row["note"]:
                lines += ["- Note: " + row["note"], ""]
    else:
        lines += ["Every audited control behaved as expected in this pass.",
                  "",
                  "That is not the same as Mike accepting them. Hands-on "
                  "operation is the gate.", ""]
    (PLUGIN_ROOT / "proof" / "CONTROL_AUDIT.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
