"""Tests for Workstream 1 - Assistant UI.

Runs headless. The view model holds every decision the window makes, so the
whole behavior is testable without opening a display. The tkinter layer is
checked only for importability and for the fact that it renders the view
model rather than deciding anything itself.

Run:  py -m unittest discover -s Tests -v      (from folder 1)
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_ui.actions import ACTION_LABEL, ActionKind, ActionLog, ActionLogError  # noqa: E402
from assistant_ui.conversation import (  # noqa: E402
    Conversation,
    ConversationError,
    Speaker,
)
from assistant_ui.view_model import (  # noqa: E402
    NOTHING_SELECTED,
    AssistantUIViewModel,
)


class TestConversation(unittest.TestCase):
    def setUp(self):
        self.conversation = Conversation()

    def test_starts_empty(self):
        self.assertTrue(self.conversation.is_empty)
        self.assertEqual(len(self.conversation), 0)
        self.assertIsNone(self.conversation.selected)

    def test_adding_turns_assigns_sequential_ids(self):
        first = self.conversation.add_driver_turn("one")
        second = self.conversation.add_assistant_turn("two")
        self.assertEqual(first.turn_id, "T001")
        self.assertEqual(second.turn_id, "T002")

    def test_new_turn_becomes_selected(self):
        self.conversation.add_driver_turn("one")
        turn = self.conversation.add_assistant_turn("two")
        self.assertEqual(self.conversation.selected_id, turn.turn_id)

    def test_blank_text_is_refused(self):
        for text in ["", "   ", "\n\t "]:
            with self.subTest(text=repr(text)):
                with self.assertRaises(ConversationError):
                    self.conversation.add_driver_turn(text)

    def test_unknown_speaker_is_refused(self):
        with self.assertRaises(ConversationError):
            self.conversation.add_turn("DISPATCHER", "hello")

    def test_text_is_stripped(self):
        turn = self.conversation.add_driver_turn("   spaced out   ")
        self.assertEqual(turn.text, "spaced out")

    def test_history_lines_label_the_speaker(self):
        self.conversation.add_driver_turn("my question")
        self.conversation.add_assistant_turn("the reply")
        lines = self.conversation.history_lines()
        self.assertIn("You: my question", lines[0])
        self.assertIn("Assistant: the reply", lines[1])

    def test_select_unknown_turn_raises(self):
        with self.assertRaises(ConversationError):
            self.conversation.select("T999")

    def test_remove_drops_the_turn(self):
        self.conversation.add_driver_turn("keep")
        target = self.conversation.add_driver_turn("drop")
        self.conversation.remove(target.turn_id)
        self.assertEqual(len(self.conversation), 1)
        self.assertFalse(self.conversation.has(target.turn_id))

    def test_removing_the_selected_turn_moves_the_selection(self):
        self.conversation.add_driver_turn("one")
        middle = self.conversation.add_driver_turn("two")
        self.conversation.add_driver_turn("three")
        self.conversation.select(middle.turn_id)
        self.conversation.remove(middle.turn_id)
        self.assertIsNotNone(self.conversation.selected)
        self.assertNotEqual(self.conversation.selected_id, middle.turn_id)

    def test_removing_the_last_turn_clears_the_selection(self):
        only = self.conversation.add_driver_turn("only")
        self.conversation.remove(only.turn_id)
        self.assertIsNone(self.conversation.selected)
        self.assertTrue(self.conversation.is_empty)

    def test_created_at_is_utc_iso_with_z(self):
        turn = self.conversation.add_driver_turn("stamped")
        self.assertRegex(turn.created_at, r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z$")


class TestActionLog(unittest.TestCase):
    def setUp(self):
        self.log = ActionLog()

    def test_records_a_request_per_press(self):
        self.log.record(ActionKind.SAVE, "T001", "text")
        self.log.record(ActionKind.PRINT, "T001", "text")
        self.assertEqual(len(self.log), 2)

    def test_request_ids_are_sequential(self):
        first = self.log.record(ActionKind.SAVE, "T001", "a")
        second = self.log.record(ActionKind.SAVE, "T002", "b")
        self.assertEqual(first.request_id, "REQ-001")
        self.assertEqual(second.request_id, "REQ-002")

    def test_every_request_is_marked_not_performed(self):
        for kind in ActionKind.ALL:
            with self.subTest(kind=kind):
                request = self.log.record(kind, "T001", "text")
                self.assertFalse(request.performed)

    def test_unknown_action_is_refused(self):
        with self.assertRaises(ActionLogError):
            self.log.record("EMAIL", "T001", "text")

    def test_filters_by_kind_and_turn(self):
        self.log.record(ActionKind.SAVE, "T001", "a")
        self.log.record(ActionKind.PRINT, "T002", "b")
        self.assertEqual(len(self.log.of_kind(ActionKind.SAVE)), 1)
        self.assertEqual(len(self.log.for_turn("T002")), 1)


class TestViewModel(unittest.TestCase):
    def setUp(self):
        self.vm = AssistantUIViewModel()

    def send(self, text="what matters about tomorrow?"):
        return self.vm.send(text)

    def test_opens_with_no_conversation_and_disabled_buttons(self):
        state = self.vm.view_state()
        self.assertEqual(state.turn_count, 0)
        self.assertIsNone(state.selected_id)
        for button in state.buttons:
            with self.subTest(button=button.kind):
                self.assertFalse(button.enabled)

    def test_all_four_buttons_are_present(self):
        state = self.vm.view_state()
        kinds = [button.kind for button in state.buttons]
        self.assertEqual(kinds, list(ActionKind.ALL))
        self.assertEqual(
            [button.label for button in state.buttons],
            [ACTION_LABEL[kind] for kind in ActionKind.ALL],
        )

    def test_send_adds_the_driver_turn(self):
        turn = self.send("check the Charlotte run")
        self.assertIsNotNone(turn)
        self.assertEqual(turn.speaker, Speaker.DRIVER)
        self.assertIn("check the Charlotte run", self.vm.view_state().history[0])

    def test_send_blank_does_nothing(self):
        self.assertIsNone(self.vm.send("   "))
        self.assertEqual(self.vm.view_state().turn_count, 0)
        self.assertEqual(self.vm.status, "Nothing to send.")

    def test_buttons_enable_once_something_is_selected(self):
        self.send()
        for button in self.vm.view_state().buttons:
            with self.subTest(button=button.kind):
                self.assertTrue(button.enabled)

    def test_pressing_with_nothing_selected_is_refused(self):
        for kind in ActionKind.ALL:
            with self.subTest(kind=kind):
                vm = AssistantUIViewModel()
                self.assertIsNone(vm.press(kind))
                self.assertEqual(vm.status, NOTHING_SELECTED)

    def test_save_records_a_request_and_changes_nothing_else(self):
        self.send()
        before = self.vm.view_state().turn_count
        request = self.vm.press_save()
        self.assertEqual(request.kind, ActionKind.SAVE)
        self.assertFalse(request.performed)
        self.assertEqual(self.vm.view_state().turn_count, before)

    def test_level_3_records_a_request(self):
        self.send()
        request = self.vm.press_level_3()
        self.assertEqual(request.kind, ActionKind.LEVEL_3)
        self.assertIn("No report was produced", request.notice)

    def test_print_never_claims_printing(self):
        self.send()
        request = self.vm.press_print()
        self.assertEqual(request.kind, ActionKind.PRINT)
        self.assertIn("No printer was contacted", request.notice)
        self.assertFalse(request.performed)

    def test_delete_removes_the_turn_from_the_window(self):
        self.send()
        selected = self.vm.conversation.selected_id
        before = self.vm.view_state().turn_count
        request = self.vm.press_delete()
        self.assertEqual(request.kind, ActionKind.DELETE)
        self.assertEqual(self.vm.view_state().turn_count, before - 1)
        self.assertFalse(self.vm.conversation.has(selected))

    def test_delete_is_recorded_like_every_other_press(self):
        self.send()
        self.vm.press_delete()
        self.assertEqual(len(self.vm.action_log.of_kind(ActionKind.DELETE)), 1)

    def test_selecting_an_unknown_turn_reports_and_changes_nothing(self):
        self.send()
        before = self.vm.conversation.selected_id
        self.assertFalse(self.vm.select("T999"))
        self.assertEqual(self.vm.conversation.selected_id, before)

    def test_action_history_is_visible_in_the_view_state(self):
        self.send()
        self.vm.press_save()
        self.vm.press_print()
        state = self.vm.view_state()
        self.assertEqual(state.request_count, 2)
        self.assertEqual(len(state.action_history), 2)

    def test_status_line_reports_the_last_action(self):
        self.send()
        self.vm.press_save()
        self.assertIn("Save requested", self.vm.status)

    def test_view_state_serializes(self):
        self.send()
        self.vm.press_save()
        data = self.vm.view_state().to_dict()
        for key in ("title", "banner", "history", "buttons", "status"):
            self.assertIn(key, data)

    def test_conversation_history_survives_many_turns(self):
        for index in range(25):
            self.vm.send("message " + str(index))
        self.assertEqual(self.vm.view_state().turn_count, 50)  # driver + placeholder


class TestBoundaries(unittest.TestCase):
    """Workstream 1 is UI only and must stay that way."""

    PACKAGE = FOLDER / "Source" / "assistant_ui"

    def _imports(self) -> set[str]:
        """Top-level modules this package imports.

        Relative imports (`from .actions import ...`) are internal to the
        package and resolve to an empty root, so they are dropped.
        """
        pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_.][\w.]*)", re.MULTILINE)
        found: set[str] = set()
        for source in sorted(self.PACKAGE.glob("*.py")):
            for module in pattern.findall(source.read_text(encoding="utf-8")):
                root = module.split(".")[0]
                if root:
                    found.add(root)
        return found

    def test_imports_nothing_from_another_workstream(self):
        forbidden = {
            "assistant_memory", "assistant_library", "assistant_outlook",
            "assistant_research", "assistant_voice", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_network_email_or_vendor_module(self):
        forbidden = {
            "socket", "urllib", "http", "requests", "smtplib", "imaplib",
            "poplib", "ssl", "win32com", "msal", "office365", "openai",
            "anthropic", "boto3", "azure", "subprocess", "webbrowser",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "dataclasses", "datetime", "itertools", "tkinter",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_the_package_writes_no_files(self):
        writers = re.compile(r"\bopen\s*\(|write_text|Path\s*\(|os\.|shutil\.|json\.dump")
        for source in sorted(self.PACKAGE.glob("*.py")):
            with self.subTest(source=source.name):
                self.assertIsNone(writers.search(source.read_text(encoding="utf-8")))

    def test_no_action_is_ever_marked_performed(self):
        vm = AssistantUIViewModel()
        vm.send("anything")
        for kind in ActionKind.ALL:
            vm.conversation.add_driver_turn("row for " + kind)
            request = vm.press(kind)
            with self.subTest(kind=kind):
                self.assertFalse(request.performed)

    def test_tkinter_layer_imports_and_holds_no_logic(self):
        # Importing must not open a window.
        from assistant_ui import window

        self.assertTrue(hasattr(window, "AssistantWindow"))
        source = (self.PACKAGE / "window.py").read_text(encoding="utf-8")
        # The window renders the view model; it must not build its own log.
        self.assertNotIn("ActionLog(", source)
        self.assertNotIn("Conversation(", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
