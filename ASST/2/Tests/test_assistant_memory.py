"""Tests for Workstream 2 - Assistant Memory.

Every test writes only inside Tests\\_workspace, which is inside folder 2 and
is removed afterward.

Run:  py -m unittest discover -s Tests -v      (from folder 2)
"""

from __future__ import annotations

import re
import shutil
import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_memory.clock import FixedClock, from_iso  # noqa: E402
from assistant_memory.record import (  # noqa: E402
    RECORD_FIELDS,
    InteractionLevel,
    RetentionState,
)
from assistant_memory.retention import (  # noqa: E402
    Operation,
    RetentionEngine,
    RetentionError,
)
from assistant_memory.store import MemoryStore, StoreError  # noqa: E402

WORKSPACE = FOLDER / "Tests" / "_workspace"


class MemoryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = WORKSPACE / uuid.uuid4().hex[:8]
        self.root.mkdir(parents=True, exist_ok=True)
        self.clock = FixedClock()
        self.engine = RetentionEngine(store=MemoryStore(self.root), clock=self.clock)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def make(self, request="What matters about tomorrow?"):
        return self.engine.create(driver_request=request, assistant_response="Answer.")


class TestCreation(MemoryTestCase):
    def test_new_record_is_temporary_level_1(self):
        record = self.make()
        self.assertEqual(record.state, RetentionState.TEMPORARY)
        self.assertEqual(record.interaction_level, InteractionLevel.LEVEL_1)

    def test_default_retention_is_three_hours(self):
        record = self.make()
        delta = from_iso(record.expires_at) - from_iso(record.created_at)
        self.assertEqual(delta, timedelta(hours=3))

    def test_all_required_fields_present(self):
        data = self.make().to_dict()
        for name in RECORD_FIELDS:
            self.assertIn(name, data)
        self.assertEqual(len(data), len(RECORD_FIELDS))

    def test_serialization_round_trip(self):
        record = self.make()
        self.assertEqual(self.engine.get(record.record_id).to_dict(), record.to_dict())

    def test_record_lands_inside_the_folder(self):
        record = self.make()
        path = self.engine.store.path_for(record.record_id, record.state)
        self.assertTrue(path.exists())
        self.assertTrue(str(path.resolve()).startswith(str(self.root.resolve())))

    def test_ids_are_unique(self):
        ids = {self.make().record_id for _ in range(20)}
        self.assertEqual(len(ids), 20)


class TestLevel1(MemoryTestCase):
    def test_level_1_resets_the_window(self):
        record = self.make()
        self.clock.advance(hours=2)
        self.engine.level_1(record.record_id)
        touched = self.engine.get(record.record_id)
        self.assertEqual(from_iso(touched.expires_at), self.clock.now() + timedelta(hours=3))

    def test_level_1_keeps_the_record_temporary(self):
        record = self.make()
        result = self.engine.level_1(record.record_id)
        self.assertEqual(result.new_state, RetentionState.TEMPORARY)

    def test_level_1_will_not_downgrade_a_preserved_record(self):
        record = self.make()
        self.engine.level_2(record.record_id)
        with self.assertRaises(RetentionError):
            self.engine.level_1(record.record_id)


class TestLevel2(MemoryTestCase):
    def test_level_2_saves_and_raises_the_level(self):
        record = self.make()
        result = self.engine.level_2(record.record_id)
        self.assertEqual(result.new_state, RetentionState.SAVED)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_2)

    def test_level_2_stops_expiration(self):
        record = self.make()
        self.engine.level_2(record.record_id)
        self.assertIsNone(self.engine.get(record.record_id).expires_at)

    def test_saved_record_survives_a_ten_hour_sweep(self):
        record = self.make()
        self.engine.level_2(record.record_id)
        self.clock.advance(hours=10)
        self.engine.sweep()
        self.assertEqual(self.engine.get(record.record_id).state, RetentionState.SAVED)

    def test_references_are_preserved(self):
        record = self.make()
        self.engine.level_2(
            record.record_id, related_load="Load 123", destination="Load 123"
        )
        saved = self.engine.get(record.record_id)
        self.assertEqual(saved.related_load, "Load 123")
        self.assertEqual(saved.destination, "Load 123")


class TestLevel3(MemoryTestCase):
    def test_level_3_marks_formal(self):
        record = self.make()
        result = self.engine.level_3(record.record_id, destination="Ideas")
        self.assertEqual(result.new_state, RetentionState.FORMAL)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_3)

    def test_level_3_preserves_the_destination_and_stops_expiration(self):
        record = self.make()
        self.engine.level_3(record.record_id, destination="Ideas")
        formal = self.engine.get(record.record_id)
        self.assertEqual(formal.destination, "Ideas")
        self.assertIsNone(formal.expires_at)

    def test_level_3_produces_nothing(self):
        record = self.make()
        result = self.engine.level_3(record.record_id)
        self.assertIn("No work product was produced", result.notice)

    def test_level_3_from_saved_is_an_upgrade(self):
        record = self.make()
        self.engine.level_2(record.record_id)
        result = self.engine.level_3(record.record_id)
        self.assertEqual(result.previous_state, RetentionState.SAVED)
        self.assertEqual(result.new_state, RetentionState.FORMAL)


class TestPrintReady(MemoryTestCase):
    def test_print_ready_sets_the_state(self):
        record = self.make()
        result = self.engine.print_ready(record.record_id)
        self.assertEqual(result.new_state, RetentionState.PRINT_READY)

    def test_print_ready_does_not_change_the_level(self):
        # Doctrine: Print is a state, not a level.
        record = self.make()
        result = self.engine.print_ready(record.record_id)
        self.assertEqual(result.previous_level, InteractionLevel.LEVEL_1)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_1)

    def test_print_ready_from_level_2_keeps_level_2(self):
        record = self.make()
        self.engine.level_2(record.record_id)
        result = self.engine.print_ready(record.record_id)
        self.assertEqual(result.new_level, InteractionLevel.LEVEL_2)

    def test_print_ready_stops_expiration(self):
        record = self.make()
        self.engine.print_ready(record.record_id)
        self.clock.advance(hours=10)
        self.engine.sweep()
        self.assertEqual(
            self.engine.get(record.record_id).state, RetentionState.PRINT_READY
        )

    def test_print_ready_never_claims_printing(self):
        record = self.make()
        result = self.engine.print_ready(record.record_id)
        self.assertIn("No printer was contacted", result.notice)
        self.assertIn("nothing", result.notice.lower())

    def test_print_ready_does_not_downgrade_a_formal_record(self):
        record = self.make()
        self.engine.level_3(record.record_id)
        result = self.engine.print_ready(record.record_id)
        self.assertEqual(result.new_state, RetentionState.FORMAL)


class TestDelete(MemoryTestCase):
    def test_delete_sets_the_state(self):
        record = self.make()
        result = self.engine.delete(record.record_id)
        self.assertEqual(result.new_state, RetentionState.DELETED)

    def test_delete_purges_content_and_records_the_reason(self):
        record = self.make(request="Sensitive broker rate discussion")
        self.engine.delete(record.record_id, reason="driver asked to forget it")
        tomb = self.engine.get(record.record_id)
        self.assertIsNone(tomb.driver_request)
        self.assertIsNone(tomb.assistant_response)
        self.assertEqual(tomb.citations, [])
        self.assertIn("forget", tomb.deletion_reason)

    def test_deleted_record_leaves_the_active_set(self):
        record = self.make()
        self.engine.delete(record.record_id)
        active = [r.record_id for r in self.engine.store.list_active()]
        self.assertNotIn(record.record_id, active)

    def test_no_operation_is_accepted_after_deletion(self):
        record = self.make()
        self.engine.delete(record.record_id)
        for operation in Operation.ALL:
            with self.subTest(operation=operation):
                with self.assertRaises(RetentionError):
                    self.engine.apply(record.record_id, operation)


class TestExpiration(MemoryTestCase):
    def test_does_not_expire_before_three_hours(self):
        record = self.make()
        self.clock.advance(hours=2, minutes=59)
        self.assertEqual(self.engine.sweep(), [])
        self.assertEqual(self.engine.get(record.record_id).state, RetentionState.TEMPORARY)

    def test_expires_past_three_hours(self):
        record = self.make()
        self.clock.advance(hours=3, seconds=1)
        expired = self.engine.sweep()
        self.assertEqual([r.record_id for r in expired], [record.record_id])
        self.assertEqual(self.engine.get(record.record_id).state, RetentionState.EXPIRED)

    def test_expired_is_absent_from_the_active_set(self):
        record = self.make()
        self.clock.advance(hours=4)
        self.engine.sweep()
        active = [r.record_id for r in self.engine.store.list_active()]
        expired = [r.record_id for r in self.engine.list_expired()]
        self.assertNotIn(record.record_id, active)
        self.assertIn(record.record_id, expired)

    def test_expired_content_is_purged_and_not_promoted(self):
        record = self.make(request="Temporary rate question")
        self.clock.advance(hours=4)
        self.engine.sweep()
        tomb = self.engine.get(record.record_id)
        self.assertIsNone(tomb.driver_request)
        self.assertIn("expired", tomb.deletion_reason)

    def test_operations_are_refused_on_an_expired_record(self):
        record = self.make()
        self.clock.advance(hours=4)
        with self.assertRaises(RetentionError):
            self.engine.level_2(record.record_id)
        self.assertEqual(self.engine.get(record.record_id).state, RetentionState.EXPIRED)

    def test_list_active_sweeps_first(self):
        record = self.make()
        self.clock.advance(hours=4)
        active = self.engine.list_active()
        self.assertNotIn(record.record_id, [r.record_id for r in active])

    def test_sweep_is_idempotent(self):
        self.make()
        self.clock.advance(hours=4)
        self.assertEqual(len(self.engine.sweep()), 1)
        self.assertEqual(len(self.engine.sweep()), 0)


class TestStore(MemoryTestCase):
    def test_refuses_to_write_outside_the_folder(self):
        for outside in ["C:/Windows/Temp/x.json", "C:/Users/Public/x.json"]:
            with self.subTest(path=outside):
                with self.assertRaises(StoreError):
                    self.engine.store.assert_within_folder(outside)

    def test_unknown_state_has_no_bucket(self):
        with self.assertRaises(StoreError):
            self.engine.store.bucket_for("ARCHIVED")

    def test_missing_record_raises(self):
        with self.assertRaises(StoreError):
            self.engine.get("MEM-not-real")

    def test_all_records_stay_inside_the_folder(self):
        for operation in (Operation.LEVEL_2, Operation.LEVEL_3,
                          Operation.PRINT_READY, Operation.DELETE):
            record = self.make()
            self.engine.apply(record.record_id, operation)
        self.make()
        root = str(self.root.resolve())
        for record in self.engine.store.list_all():
            path = self.engine.store.path_for(record.record_id, record.state).resolve()
            with self.subTest(record=record.record_id):
                self.assertTrue(str(path).startswith(root))

    def test_moving_buckets_leaves_no_duplicate(self):
        record = self.make()
        self.engine.delete(record.record_id)
        active_path = self.engine.store.data_root / "active" / (record.record_id + ".json")
        self.assertFalse(active_path.exists())


class TestBoundaries(MemoryTestCase):
    PACKAGE = FOLDER / "Source" / "assistant_memory"

    def _imports(self) -> set[str]:
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
            "assistant_ui", "assistant_library", "assistant_outlook",
            "assistant_research", "assistant_voice", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_network_email_printing_or_vendor_module(self):
        forbidden = {
            "socket", "urllib", "http", "requests", "smtplib", "imaplib",
            "poplib", "ssl", "win32com", "win32print", "msal", "office365",
            "openai", "anthropic", "boto3", "azure", "subprocess", "webbrowser",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "argparse", "dataclasses", "datetime", "json",
            "os", "pathlib", "re", "sys", "uuid",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_engine_exposes_no_routing_or_sending_operation(self):
        for name in ("send", "send_email", "route", "publish", "print_document",
                     "promote", "archive", "dispatch", "upload"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(self.engine, name))

    def test_expired_records_are_never_promoted(self):
        record = self.make()
        self.clock.advance(hours=4)
        self.engine.sweep()
        tomb = self.engine.get(record.record_id)
        self.assertEqual(tomb.state, RetentionState.EXPIRED)
        self.assertNotIn(tomb.state, RetentionState.NON_EXPIRING)
        buckets = [p.name for p in self.engine.store.data_root.iterdir() if p.is_dir()]
        self.assertEqual(sorted(buckets), ["active", "deleted", "expired"])

    def test_unknown_operation_is_refused(self):
        record = self.make()
        with self.assertRaises(RetentionError):
            self.engine.apply(record.record_id, "ARCHIVE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
