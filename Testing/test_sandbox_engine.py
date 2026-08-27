"""Automated tests for Sandbox Engine v1.

Every test writes only inside Testing/_test_workspace, which is inside the
project. Nothing here touches a production system, a network, or Dispatch.

Run:  py -m unittest discover -s Testing -v      (from the project root)
"""

from __future__ import annotations

import re
import shutil
import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Build"))

from sandbox_engine.clock import FixedClock, from_iso  # noqa: E402
from sandbox_engine.engine import EngineError, SandboxEngine  # noqa: E402
from sandbox_engine.intents import CommandIntent, recognize  # noqa: E402
from sandbox_engine.records import (  # noqa: E402
    RECORD_FIELDS,
    InteractionLevel,
    RecordState,
)
from sandbox_engine.store import SandboxStore, StoreError  # noqa: E402

WORKSPACE = PROJECT_ROOT / "Testing" / "_test_workspace"


class EngineTestCase(unittest.TestCase):
    """Base case giving each test an isolated store inside Testing."""

    def setUp(self) -> None:
        self.root = WORKSPACE / uuid.uuid4().hex[:8]
        self.root.mkdir(parents=True, exist_ok=True)
        self.clock = FixedClock()
        self.engine = SandboxEngine(
            store=SandboxStore(self.root), clock=self.clock
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def make_record(self, request="What is my next stop?", response="Answer."):
        return self.engine.create(driver_request=request, assistant_response=response)


# ---------------------------------------------------------------------------
# Record creation and the three-hour default
# ---------------------------------------------------------------------------


class TestCreation(EngineTestCase):
    def test_new_record_is_temporary_level_1(self):
        record = self.make_record()
        self.assertEqual(record.state, RecordState.TEMPORARY)
        self.assertEqual(record.interaction_level, InteractionLevel.LEVEL_1)

    def test_expiration_is_exactly_three_hours_after_creation(self):
        record = self.make_record()
        created = from_iso(record.created_at)
        expires = from_iso(record.expires_at)
        self.assertEqual(expires - created, timedelta(hours=3))

    def test_every_required_field_is_present(self):
        record = self.make_record()
        data = record.to_dict()
        for name in RECORD_FIELDS:
            self.assertIn(name, data, "missing required field: " + name)
        self.assertEqual(len(data), len(RECORD_FIELDS))

    def test_record_survives_a_serialization_round_trip(self):
        record = self.make_record()
        reloaded = self.engine.get(record.sandbox_id)
        self.assertEqual(reloaded.to_dict(), record.to_dict())

    def test_record_file_lands_inside_the_project(self):
        record = self.make_record()
        path = self.engine.store.path_for(record.sandbox_id, record.state)
        self.assertTrue(path.exists())
        self.assertTrue(str(path.resolve()).startswith(str(self.root.resolve())))


# ---------------------------------------------------------------------------
# Deterministic command recognition
# ---------------------------------------------------------------------------


class TestIntentRecognition(unittest.TestCase):
    LEVEL_1_PHRASES = [
        "Level 1",
        "Just answer it",
        "Just tell me what matters",
        "No need to save this",
        "Let it expire",
    ]
    LEVEL_2_PHRASES = [
        "Save this",
        "Keep this",
        "Level 2 this",
        "Put this under Load 123",
        "Attach this to the mission",
        "Keep this for parked review",
    ]
    LEVEL_3_PHRASES = [
        "Level 3 this",
        "Build a report",
        "Formal presentation",
        "Write this up",
        "Research this completely",
        "Level 3 this under XPO Load 123",
        "Level 3 this under Ideas with formal presentation",
    ]
    PRINT_PHRASES = [
        "Print this",
        "Make this printable",
        "Write this so I can print later",
    ]
    DELETE_PHRASES = ["Delete this", "Remove this", "Forget this"]

    def assert_intent(self, phrases, expected):
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(recognize(phrase).intent, expected)

    def test_level_1_phrases(self):
        self.assert_intent(self.LEVEL_1_PHRASES, CommandIntent.LEVEL_1)

    def test_level_2_phrases(self):
        self.assert_intent(self.LEVEL_2_PHRASES, CommandIntent.LEVEL_2)

    def test_level_3_phrases(self):
        self.assert_intent(self.LEVEL_3_PHRASES, CommandIntent.LEVEL_3)

    def test_print_phrases(self):
        self.assert_intent(self.PRINT_PHRASES, CommandIntent.PRINT)

    def test_delete_phrases(self):
        self.assert_intent(self.DELETE_PHRASES, CommandIntent.DELETE)

    def test_capitalization_and_punctuation_do_not_matter(self):
        variants = [
            "level 3 this under ideas",
            "LEVEL 3 THIS UNDER IDEAS.",
            "  Level 3 this under Ideas!!  ",
            "level  3  this under Ideas,",
        ]
        for phrase in variants:
            with self.subTest(phrase=phrase):
                command = recognize(phrase)
                self.assertEqual(command.intent, CommandIntent.LEVEL_3)
                self.assertEqual(
                    (command.references.get("destination") or "").lower(), "ideas"
                )

    def test_decline_phrases_are_not_mistaken_for_save(self):
        # "no need to save this" contains "save this"; Level 1 must win.
        for phrase in ["No need to save this", "Don't save this", "Do not keep this"]:
            with self.subTest(phrase=phrase):
                self.assertEqual(recognize(phrase).intent, CommandIntent.LEVEL_1)

    def test_let_it_expire_is_level_1_not_delete(self):
        # Documented conflict resolution C3.
        self.assertEqual(recognize("Let it expire").intent, CommandIntent.LEVEL_1)

    def test_bare_print_language_is_print_not_level_3(self):
        # Documented conflict resolution C2.
        self.assertEqual(recognize("Make this printable").intent, CommandIntent.PRINT)

    def test_level_3_wins_when_combined_with_print_language(self):
        command = recognize("Level 3 this under Ideas with a formal printable report")
        self.assertEqual(command.intent, CommandIntent.LEVEL_3)
        self.assertTrue(command.print_requested)

    def test_unrelated_language_is_not_a_command(self):
        for phrase in ["What loads do I have tomorrow", "How far is Atlanta", ""]:
            with self.subTest(phrase=phrase):
                self.assertEqual(recognize(phrase).intent, CommandIntent.NONE)

    def test_reference_extraction(self):
        cases = [
            ("Put this under Load 123", "related_load", "Load 123"),
            ("Level 3 this under XPO Load 123", "related_load", "Load 123"),
            ("Level 3 this under Ideas", "destination", "Ideas"),
            ("Save this for customer Acme Freight", "related_customer", "Acme Freight"),
            ("Save this under broker XPO for now", "related_broker", "XPO"),
            ("Attach this to mission Northbound", "related_mission", "Northbound"),
        ]
        for phrase, field, expected in cases:
            with self.subTest(phrase=phrase):
                self.assertEqual(recognize(phrase).references.get(field), expected)


# ---------------------------------------------------------------------------
# Level 2 - save it
# ---------------------------------------------------------------------------


class TestLevel2(EngineTestCase):
    def test_save_this_converts_to_saved_level_2(self):
        record = self.make_record()
        result = self.engine.apply_command(record.sandbox_id, "Save this")
        self.assertTrue(result.accepted)
        self.assertEqual(result.new_state, RecordState.SAVED)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_2)

    def test_saved_record_no_longer_expires(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Save this")
        saved = self.engine.get(record.sandbox_id)
        self.assertIsNone(saved.expires_at)

    def test_saved_record_survives_a_ten_hour_sweep(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Save this")
        self.clock.advance(hours=10)
        self.engine.sweep()
        still_there = self.engine.get(record.sandbox_id)
        self.assertEqual(still_there.state, RecordState.SAVED)
        self.assertIn(
            record.sandbox_id, [r.sandbox_id for r in self.engine.store.list_active()]
        )

    def test_load_reference_is_preserved(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Put this under Load 123")
        saved = self.engine.get(record.sandbox_id)
        self.assertEqual(saved.related_load, "Load 123")
        self.assertEqual(saved.destination, "Load 123")
        self.assertEqual(saved.state, RecordState.SAVED)

    def test_level_1_will_not_downgrade_a_saved_record(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Save this")
        with self.assertRaises(EngineError):
            self.engine.apply_command(record.sandbox_id, "Level 1")


# ---------------------------------------------------------------------------
# Level 3 - build it
# ---------------------------------------------------------------------------


class TestLevel3(EngineTestCase):
    def test_level_3_under_ideas_is_formal_with_destination(self):
        record = self.make_record()
        result = self.engine.apply_command(
            record.sandbox_id, "Level 3 this under Ideas"
        )
        self.assertEqual(result.new_state, RecordState.FORMAL)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_3)
        formal = self.engine.get(record.sandbox_id)
        self.assertEqual(formal.destination, "Ideas")
        self.assertIsNone(formal.expires_at)

    def test_level_3_creates_a_formal_artifact_request(self):
        record = self.make_record()
        result = self.engine.apply_command(
            record.sandbox_id, "Level 3 this under Ideas"
        )
        self.assertEqual(len(result.artifact_requests), 1)
        request = result.artifact_requests[0]
        self.assertEqual(request["artifact_kind"], "FORMAL_REPORT")
        self.assertEqual(request["status"], "REQUESTED_NOT_PRODUCED")
        self.assertFalse(request["produced"])
        self.assertEqual(request["destination"], "Ideas")

    def test_citations_and_sources_are_carried_into_the_request(self):
        record = self.engine.create(
            driver_request="Research I-95 conditions",
            assistant_response="Summary.",
            citations=["https://example.invalid/a"],
            sources_consulted=["state DOT feed"],
            research_scope="I-95 corridor, next 24 hours",
        )
        result = self.engine.apply_command(record.sandbox_id, "Level 3 this")
        request = result.artifact_requests[0]
        self.assertEqual(request["citations"], ["https://example.invalid/a"])
        self.assertEqual(request["sources_consulted"], ["state DOT feed"])
        self.assertEqual(request["research_scope"], "I-95 corridor, next 24 hours")

    def test_level_3_plus_print_creates_both_requests(self):
        record = self.make_record()
        result = self.engine.apply_command(
            record.sandbox_id, "Level 3 this under Ideas with a formal printable report"
        )
        kinds = sorted(r["artifact_kind"] for r in result.artifact_requests)
        self.assertEqual(kinds, ["FORMAL_REPORT", "PRINT_READY"])
        self.assertEqual(result.new_state, RecordState.FORMAL)

    def test_xpo_load_reference_is_preserved(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Level 3 this under XPO Load 123")
        formal = self.engine.get(record.sandbox_id)
        self.assertEqual(formal.related_load, "Load 123")
        self.assertIn("XPO", formal.destination)


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------


class TestPrint(EngineTestCase):
    def test_print_this_yields_print_ready(self):
        record = self.make_record()
        result = self.engine.apply_command(record.sandbox_id, "Print this")
        self.assertEqual(result.new_state, RecordState.PRINT_READY)

    def test_print_ready_record_does_not_expire(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Print this")
        self.clock.advance(hours=10)
        self.engine.sweep()
        self.assertEqual(
            self.engine.get(record.sandbox_id).state, RecordState.PRINT_READY
        )

    def test_print_does_not_raise_the_interaction_level(self):
        # Doctrine C4, ruled by Mike Zachary: Print is a state, not a level.
        # A Level 1 record that is printed stays LEVEL_1.
        record = self.make_record()
        self.assertEqual(record.interaction_level, InteractionLevel.LEVEL_1)
        result = self.engine.apply_command(record.sandbox_id, "Print this")
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_1)
        printable = self.engine.get(record.sandbox_id)
        self.assertEqual(printable.interaction_level, InteractionLevel.LEVEL_1)
        self.assertEqual(printable.state, RecordState.PRINT_READY)
        self.assertIsNone(printable.expires_at)

    def test_every_print_phrase_leaves_the_level_at_level_1(self):
        # The ruling holds for all three print phrasings, not just one.
        for phrase in ["Print this", "Make this printable", "Write this so I can print later"]:
            with self.subTest(phrase=phrase):
                record = self.make_record()
                self.engine.apply_command(record.sandbox_id, phrase)
                printed = self.engine.get(record.sandbox_id)
                self.assertEqual(printed.interaction_level, InteractionLevel.LEVEL_1)
                self.assertEqual(printed.state, RecordState.PRINT_READY)

    def test_print_from_level_2_does_not_change_the_level(self):
        # Print does not raise, and it does not lower. It leaves the level alone.
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Save this")
        self.assertEqual(
            self.engine.get(record.sandbox_id).interaction_level,
            InteractionLevel.LEVEL_2,
        )
        self.engine.apply_command(record.sandbox_id, "Print this")
        printed = self.engine.get(record.sandbox_id)
        self.assertEqual(printed.interaction_level, InteractionLevel.LEVEL_2)
        self.assertEqual(printed.state, RecordState.PRINT_READY)

    def test_engine_never_claims_physical_printing(self):
        record = self.make_record()
        result = self.engine.apply_command(record.sandbox_id, "Print this")
        request = result.artifact_requests[0]
        self.assertFalse(request["physical_print_performed"])
        self.assertFalse(request["produced"])
        self.assertIn("No printer was contacted", result.notice)

    def test_print_request_markdown_states_nothing_was_printed(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Make this printable")
        requests = list(self.engine.store.artifact_requests_root.glob("*.md"))
        self.assertEqual(len(requests), 1)
        body = requests[0].read_text(encoding="utf-8")
        self.assertIn("has **not** been produced", body)
        self.assertIn("Nothing was printed", body)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete(EngineTestCase):
    def test_delete_this_yields_deleted(self):
        record = self.make_record()
        result = self.engine.apply_command(record.sandbox_id, "Delete this")
        self.assertEqual(result.new_state, RecordState.DELETED)

    def test_deleted_record_leaves_the_active_sandbox(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Delete this")
        active_ids = [r.sandbox_id for r in self.engine.store.list_active()]
        self.assertNotIn(record.sandbox_id, active_ids)

    def test_deleted_record_content_is_purged_and_reason_recorded(self):
        record = self.make_record(request="Sensitive broker rate discussion")
        self.engine.apply_command(record.sandbox_id, "Forget this")
        tombstone = self.engine.get(record.sandbox_id)
        self.assertIsNone(tombstone.driver_request)
        self.assertIsNone(tombstone.assistant_response)
        self.assertEqual(tombstone.citations, [])
        self.assertIn("Forget this", tombstone.deletion_reason)

    def test_no_command_is_accepted_after_deletion(self):
        record = self.make_record()
        self.engine.apply_command(record.sandbox_id, "Delete this")
        with self.assertRaises(EngineError):
            self.engine.apply_command(record.sandbox_id, "Save this")


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------


class TestExpiration(EngineTestCase):
    def test_record_does_not_expire_before_three_hours(self):
        record = self.make_record()
        self.clock.advance(hours=2, minutes=59)
        self.assertEqual(self.engine.sweep(), [])
        self.assertEqual(
            self.engine.get(record.sandbox_id).state, RecordState.TEMPORARY
        )

    def test_record_expires_at_three_hours(self):
        record = self.make_record()
        self.clock.advance(hours=3, seconds=1)
        expired = self.engine.sweep()
        self.assertEqual([r.sandbox_id for r in expired], [record.sandbox_id])
        self.assertEqual(self.engine.get(record.sandbox_id).state, RecordState.EXPIRED)

    def test_expired_record_is_absent_from_the_active_sandbox(self):
        record = self.make_record()
        self.clock.advance(hours=4)
        self.engine.sweep()
        active_ids = [r.sandbox_id for r in self.engine.store.list_active()]
        self.assertNotIn(record.sandbox_id, active_ids)
        expired_ids = [r.sandbox_id for r in self.engine.list_expired()]
        self.assertIn(record.sandbox_id, expired_ids)

    def test_expired_record_content_is_purged_and_not_promoted(self):
        record = self.make_record(request="Temporary rate question")
        self.clock.advance(hours=4)
        self.engine.sweep()
        tombstone = self.engine.get(record.sandbox_id)
        self.assertIsNone(tombstone.driver_request)
        self.assertEqual(tombstone.state, RecordState.EXPIRED)
        self.assertIn("expired", tombstone.deletion_reason)

    def test_commands_are_refused_on_an_expired_record(self):
        record = self.make_record()
        self.clock.advance(hours=4)
        with self.assertRaises(EngineError):
            self.engine.apply_command(record.sandbox_id, "Save this")
        self.assertEqual(self.engine.get(record.sandbox_id).state, RecordState.EXPIRED)

    def test_explicit_level_1_resets_the_three_hour_window(self):
        record = self.make_record()
        self.clock.advance(hours=2)
        self.engine.apply_command(record.sandbox_id, "Level 1")
        touched = self.engine.get(record.sandbox_id)
        expected = self.clock.now() + timedelta(hours=3)
        self.assertEqual(from_iso(touched.expires_at), expected)

    def test_nothing_expired_is_ever_written_to_an_artifact_request(self):
        record = self.make_record()
        self.clock.advance(hours=4)
        self.engine.sweep()
        self.assertEqual(self.engine.store.list_artifact_requests(), [])


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------


class TestBoundaries(EngineTestCase):
    def test_store_refuses_to_write_outside_the_project(self):
        for outside in ["C:/Windows/Temp/x.json", "C:/Users/Public/x.json"]:
            with self.subTest(path=outside):
                with self.assertRaises(StoreError):
                    self.engine.store.assert_within_project(outside)

    def test_all_records_live_under_the_project_root(self):
        ids = []
        for phrase in ["Save this", "Level 3 this under Ideas", "Print this", "Delete this"]:
            record = self.make_record()
            self.engine.apply_command(record.sandbox_id, phrase)
            ids.append(record.sandbox_id)
        self.make_record()
        root = str(self.root.resolve())
        for record in self.engine.store.list_all():
            path = self.engine.store.path_for(record.sandbox_id, record.state)
            self.assertTrue(
                str(path.resolve()).startswith(root),
                "record escaped the project root: " + str(path),
            )

    def test_engine_source_imports_no_network_or_vendor_modules(self):
        forbidden = (
            "socket", "urllib", "http", "https", "requests", "ftplib", "smtplib",
            "poplib", "imaplib", "telnetlib", "asyncio", "ssl", "xmlrpc",
            "boto3", "azure", "msal", "openai", "anthropic", "office365",
            "win32com", "subprocess", "webbrowser",
        )
        package = PROJECT_ROOT / "Build" / "sandbox_engine"
        pattern = re.compile(
            r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", re.MULTILINE
        )
        offenders = []
        for source in sorted(package.glob("*.py")):
            text = source.read_text(encoding="utf-8")
            for module in pattern.findall(text):
                if module.split(".")[0] in forbidden:
                    offenders.append(source.name + " -> " + module)
        self.assertEqual(offenders, [], "forbidden imports found: " + str(offenders))

    def test_engine_exposes_no_send_dispatch_or_payment_operations(self):
        forbidden_names = (
            "send_email", "send_mail", "place_call", "dial", "pay", "commit_funds",
            "accept_load", "dispatch_load", "book_load", "print_document",
        )
        for name in forbidden_names:
            with self.subTest(name=name):
                self.assertFalse(hasattr(self.engine, name))

    def test_unrecognized_language_changes_nothing(self):
        record = self.make_record()
        before = self.engine.get(record.sandbox_id).to_dict()
        result = self.engine.apply_command(record.sandbox_id, "How far is Atlanta")
        self.assertFalse(result.accepted)
        self.assertEqual(self.engine.get(record.sandbox_id).to_dict(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
