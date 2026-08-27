"""Tests for Workstream 4 - Assistant Outlook.

Reads the sample fixtures in this folder. Any test needing its own data writes
it inside Tests\\_workspace and removes it afterward.

Run:  py -m unittest discover -s Tests -v      (from folder 4)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_outlook.awareness import (  # noqa: E402
    DECISION_MARKERS,
    STALE_AFTER_DAYS,
    Awareness,
)
from assistant_outlook.models import (  # noqa: E402
    CalendarEvent,
    Contact,
    EmailMessage,
    ModelError,
    parse_moment,
)
from assistant_outlook.provider import (  # noqa: E402
    AwarenessProvider,
    JsonFileProvider,
    ProviderError,
    resolve_data_root,
)

DATA = FOLDER / "Data"
WORKSPACE = FOLDER / "Tests" / "_workspace"

# Fixed reference points inside the sample data.
BEFORE_ALL = parse_moment("2026-08-25T12:00:00Z")
DAY_ONE = parse_moment("2026-08-26T08:00:00Z")
DURING_PICKUP = parse_moment("2026-08-26T12:30:00Z")


def event(event_id, start, end, **extra):
    payload = {"event_id": event_id, "subject": event_id, "start": start, "end": end}
    payload.update(extra)
    return CalendarEvent.from_dict(payload)


class SampleDataTestCase(unittest.TestCase):
    def setUp(self):
        self.awareness = Awareness(JsonFileProvider(DATA))


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.workspace = WORKSPACE / uuid.uuid4().hex[:8]
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def write(self, name, payload):
        (self.workspace / name).write_text(
            json.dumps(payload), encoding="utf-8"
        )


class TestModels(unittest.TestCase):
    def test_parses_z_suffixed_timestamps(self):
        moment = parse_moment("2026-08-26T12:00:00Z")
        self.assertEqual(moment.tzinfo, timezone.utc)
        self.assertEqual(moment.hour, 12)

    def test_naive_timestamps_are_treated_as_utc(self):
        self.assertEqual(
            parse_moment("2026-08-26T12:00:00"), parse_moment("2026-08-26T12:00:00Z")
        )

    def test_offset_timestamps_convert_to_utc(self):
        self.assertEqual(
            parse_moment("2026-08-26T08:00:00-04:00"),
            parse_moment("2026-08-26T12:00:00Z"),
        )

    def test_unreadable_timestamp_raises(self):
        for bad in ["not a date", "", "2026-13-45T99:99:99Z"]:
            with self.subTest(value=bad):
                with self.assertRaises(ModelError):
                    parse_moment(bad)

    def test_event_missing_a_field_raises(self):
        with self.assertRaises(ModelError):
            CalendarEvent.from_dict({"subject": "no id or times"})

    def test_event_ending_before_it_starts_raises(self):
        with self.assertRaises(ModelError):
            event("EVT-X", "2026-08-26T14:00:00Z", "2026-08-26T12:00:00Z")

    def test_overlap_detection(self):
        first = event("A", "2026-08-26T12:00:00Z", "2026-08-26T14:00:00Z")
        overlapping = event("B", "2026-08-26T13:00:00Z", "2026-08-26T15:00:00Z")
        separate = event("C", "2026-08-26T16:00:00Z", "2026-08-26T17:00:00Z")
        self.assertTrue(first.overlaps(overlapping))
        self.assertFalse(first.overlaps(separate))

    def test_touching_events_do_not_overlap(self):
        first = event("A", "2026-08-26T12:00:00Z", "2026-08-26T14:00:00Z")
        second = event("B", "2026-08-26T14:00:00Z", "2026-08-26T15:00:00Z")
        self.assertFalse(first.overlaps(second))

    def test_duration_is_reported(self):
        one = event("A", "2026-08-26T12:00:00Z", "2026-08-26T14:00:00Z")
        self.assertEqual(one.duration, timedelta(hours=2))
        self.assertEqual(one.to_dict()["duration_minutes"], 120)

    def test_is_on_compares_the_utc_date(self):
        one = event("A", "2026-08-26T12:00:00Z", "2026-08-26T14:00:00Z")
        self.assertTrue(one.is_on(DAY_ONE))
        self.assertFalse(one.is_on(DAY_ONE + timedelta(days=1)))

    def test_email_missing_a_field_raises(self):
        with self.assertRaises(ModelError):
            EmailMessage.from_dict({"subject": "no id"})

    def test_contact_missing_a_field_raises(self):
        with self.assertRaises(ModelError):
            Contact.from_dict({"display_name": "no id"})

    def test_models_are_frozen(self):
        one = event("A", "2026-08-26T12:00:00Z", "2026-08-26T14:00:00Z")
        with self.assertRaises(Exception):
            one.subject = "changed"  # type: ignore[misc]


class TestProvider(SampleDataTestCase):
    def test_reads_the_sample_calendar(self):
        self.assertEqual(len(self.awareness.events()), 4)

    def test_reads_the_sample_mail(self):
        self.assertEqual(len(self.awareness.messages()), 4)

    def test_reads_the_sample_contacts(self):
        self.assertEqual(len(self.awareness.contacts()), 3)

    def test_events_are_sorted_by_start(self):
        starts = [e.start for e in self.awareness.events()]
        self.assertEqual(starts, sorted(starts))

    def test_messages_are_newest_first(self):
        received = [m.received for m in self.awareness.messages()]
        self.assertEqual(received, sorted(received, reverse=True))

    def test_status_reports_no_live_connection(self):
        status = self.awareness.status()
        self.assertFalse(status["live_connection"])
        self.assertIn("not a live mailbox", status["source"])

    def test_default_data_root_is_this_folder(self):
        self.assertEqual(resolve_data_root(None).name, "Data")
        self.assertTrue(str(resolve_data_root(None)).startswith(str(FOLDER)))


class TestProviderEdges(WorkspaceTestCase):
    def test_missing_files_yield_nothing_and_are_reported(self):
        provider = JsonFileProvider(self.workspace)
        self.assertEqual(provider.calendar_events(), [])
        self.assertEqual(provider.email_messages(), [])
        self.assertEqual(provider.contacts(), [])
        self.assertEqual(len(provider.status()["missing_files"]), 3)

    def test_malformed_json_raises_rather_than_reporting_empty(self):
        (self.workspace / "calendar.json").write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ProviderError):
            JsonFileProvider(self.workspace).calendar_events()

    def test_json_that_is_not_a_list_raises(self):
        self.write("calendar.json", {"event_id": "EVT-1"})
        with self.assertRaises(ProviderError):
            JsonFileProvider(self.workspace).calendar_events()

    def test_a_bad_entry_is_skipped_and_named_not_fatal(self):
        self.write("calendar.json", [
            {
                "event_id": "GOOD",
                "subject": "fine",
                "start": "2026-08-26T12:00:00Z",
                "end": "2026-08-26T13:00:00Z",
            },
            {"event_id": "BAD", "subject": "missing times"},
        ])
        provider = JsonFileProvider(self.workspace)
        events = provider.calendar_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(provider.skipped), 1)
        self.assertIn("calendar", provider.skipped[0])

    def test_empty_lists_are_handled(self):
        for name in ("calendar.json", "emails.json", "contacts.json"):
            self.write(name, [])
        awareness = Awareness(JsonFileProvider(self.workspace))
        self.assertEqual(awareness.events(), [])
        self.assertIsNone(awareness.next_event(BEFORE_ALL))
        self.assertEqual(awareness.day_brief(DAY_ONE).event_count, 0)


class TestCalendarAwareness(SampleDataTestCase):
    def test_next_event_from_before_everything(self):
        upcoming = self.awareness.next_event(BEFORE_ALL)
        self.assertIsNotNone(upcoming)
        self.assertEqual(upcoming.event_id, "EVT-001")

    def test_current_event_during_a_meeting(self):
        current = self.awareness.current_event(DURING_PICKUP)
        self.assertIsNotNone(current)
        self.assertEqual(current.event_id, "EVT-001")

    def test_no_current_event_when_nothing_is_running(self):
        self.assertIsNone(self.awareness.current_event(BEFORE_ALL))

    def test_next_event_is_none_after_everything(self):
        self.assertIsNone(
            self.awareness.next_event(parse_moment("2027-01-01T00:00:00Z"))
        )

    def test_events_on_a_day(self):
        self.assertEqual(len(self.awareness.events_on(DAY_ONE)), 2)

    def test_conflicts_are_detected(self):
        conflicts = self.awareness.conflicts()
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(
            {conflicts[0].first_id, conflicts[0].second_id}, {"EVT-001", "EVT-002"}
        )

    def test_conflict_overlap_is_measured(self):
        self.assertEqual(self.awareness.conflicts()[0].overlap_minutes, 30)

    def test_unanswered_invitations_include_none_and_tentative(self):
        unanswered = {e.event_id for e in self.awareness.unanswered_invitations()}
        self.assertEqual(unanswered, {"EVT-002", "EVT-003"})

    def test_accepted_events_are_not_flagged_as_unanswered(self):
        unanswered = {e.event_id for e in self.awareness.unanswered_invitations()}
        self.assertNotIn("EVT-001", unanswered)
        self.assertNotIn("EVT-004", unanswered)

    def test_day_brief_reports_events_conflicts_and_bounds(self):
        brief = self.awareness.day_brief(DAY_ONE)
        self.assertEqual(brief.event_count, 2)
        self.assertEqual(len(brief.conflicts), 1)
        self.assertEqual(brief.first_start[11:16], "12:00")
        self.assertEqual(brief.last_end[11:16], "15:30")

    def test_day_brief_for_an_empty_day(self):
        brief = self.awareness.day_brief(parse_moment("2026-09-15T08:00:00Z"))
        self.assertEqual(brief.event_count, 0)
        self.assertIsNone(brief.first_start)
        self.assertEqual(brief.conflicts, [])

    def test_day_brief_serializes(self):
        data = self.awareness.day_brief(DAY_ONE).to_dict()
        for key in ("date", "event_count", "events", "conflicts"):
            self.assertIn(key, data)


class TestEmailAwareness(SampleDataTestCase):
    def test_unread_is_filtered(self):
        unread = {m.message_id for m in self.awareness.unread()}
        self.assertEqual(unread, {"MSG-001", "MSG-003"})

    def test_flags_a_message_asking_for_confirmation(self):
        flags = {f.message_id: f for f in self.awareness.flagged(BEFORE_ALL)}
        self.assertIn("MSG-001", flags)
        self.assertTrue(
            any("confirm" in reason for reason in flags["MSG-001"].reasons)
        )

    def test_flags_high_importance(self):
        flags = {f.message_id: f for f in self.awareness.flagged(BEFORE_ALL)}
        self.assertIn("marked high importance", flags["MSG-001"].reasons)

    def test_flags_unread(self):
        flags = {f.message_id: f for f in self.awareness.flagged(BEFORE_ALL)}
        self.assertIn("unread", flags["MSG-003"].reasons)

    def test_flags_stale_messages(self):
        late = parse_moment("2026-08-24T00:00:00Z") + timedelta(
            days=STALE_AFTER_DAYS + 5
        )
        flags = {f.message_id: f for f in self.awareness.flagged(late)}
        self.assertIn("MSG-004", flags)
        self.assertTrue(
            any("older than" in reason for reason in flags["MSG-004"].reasons)
        )

    def test_a_routine_read_message_is_not_flagged(self):
        flags = {f.message_id for f in self.awareness.flagged(BEFORE_ALL)}
        self.assertNotIn("MSG-002", flags)

    def test_every_flag_carries_its_reasons(self):
        for flag in self.awareness.flagged(BEFORE_ALL):
            with self.subTest(message=flag.message_id):
                self.assertTrue(flag.reasons)

    def test_flags_never_claim_a_decision_or_action(self):
        for flag in self.awareness.flagged(BEFORE_ALL):
            data = flag.to_dict()
            with self.subTest(message=flag.message_id):
                self.assertFalse(data["decided"])
                self.assertFalse(data["acted_on"])

    def test_decision_markers_are_a_visible_list(self):
        self.assertGreater(len(DECISION_MARKERS), 10)
        self.assertIn("confirm", DECISION_MARKERS)

    def test_message_search(self):
        self.assertEqual(len(self.awareness.search_messages("settlement")), 1)
        self.assertEqual(len(self.awareness.search_messages("j.reed")), 1)

    def test_empty_search_returns_nothing(self):
        self.assertEqual(self.awareness.search_messages(""), [])
        self.assertEqual(self.awareness.search_messages("   "), [])


class TestContactAwareness(SampleDataTestCase):
    def test_find_by_name(self):
        self.assertEqual(len(self.awareness.find_contacts("reed")), 1)

    def test_find_by_company(self):
        self.assertEqual(len(self.awareness.find_contacts("sample")), 2)

    def test_find_by_role(self):
        self.assertEqual(len(self.awareness.find_contacts("broker")), 1)

    def test_contact_for_a_sender_address(self):
        contact = self.awareness.contact_for_sender("j.reed@example.invalid")
        self.assertIsNotNone(contact)
        self.assertEqual(contact.display_name, "J. Reed")

    def test_unknown_sender_returns_none(self):
        self.assertIsNone(self.awareness.contact_for_sender("nobody@example.invalid"))
        self.assertIsNone(self.awareness.contact_for_sender(""))

    def test_empty_query_returns_nothing(self):
        self.assertEqual(self.awareness.find_contacts(""), [])


class TestBoundaries(SampleDataTestCase):
    PACKAGE = FOLDER / "Source" / "assistant_outlook"

    def _sources(self):
        return sorted(self.PACKAGE.glob("*.py"))

    def _imports(self) -> set[str]:
        pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_.][\w.]*)", re.MULTILINE)
        found: set[str] = set()
        for source in self._sources():
            for module in pattern.findall(source.read_text(encoding="utf-8")):
                root = module.split(".")[0]
                if root:
                    found.add(root)
        return found

    def test_imports_nothing_from_another_workstream(self):
        forbidden = {
            "assistant_ui", "assistant_memory", "assistant_library",
            "assistant_research", "assistant_voice", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_mail_transport_or_vendor_module(self):
        forbidden = {
            "smtplib", "imaplib", "poplib", "email", "socket", "urllib", "http",
            "requests", "ssl", "win32com", "pythoncom", "msal", "office365",
            "exchangelib", "O365", "openai", "anthropic", "boto3", "azure",
            "subprocess", "webbrowser",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "argparse", "dataclasses", "datetime", "json",
            "os", "pathlib", "sys",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_the_provider_port_defines_only_reads(self):
        methods = {
            name for name in vars(AwarenessProvider) if not name.startswith("_")
        }
        self.assertEqual(methods, {"name", "calendar_events", "email_messages", "contacts"})

    def test_no_send_reply_or_schedule_method_exists(self):
        for target in (self.awareness, self.awareness.provider):
            for name in (
                "send", "send_email", "reply", "reply_all", "forward", "accept",
                "decline", "schedule", "create_event", "update", "delete",
                "move", "flag", "mark_read", "save", "draft",
            ):
                with self.subTest(target=type(target).__name__, name=name):
                    self.assertFalse(hasattr(target, name))

    def test_status_declares_every_capability_as_absent(self):
        status = self.awareness.status()
        for key in (
            "can_send", "can_reply", "can_schedule", "can_modify",
            "can_accept_or_decline", "has_approval_authority", "live_connection",
        ):
            with self.subTest(key=key):
                self.assertFalse(status[key])

    def test_no_write_call_exists_anywhere_in_the_package(self):
        writers = re.compile(
            r"write_text|write_bytes|\.write\(|\bmkdir\b|\bunlink\b|\brmdir\b"
            r"|\.rename\(|os\.replace|shutil\.|os\.remove|os\.makedirs"
            r"|open\s*\([^)]*['\"][wax]"
        )
        for source in self._sources():
            with self.subTest(source=source.name):
                self.assertIsNone(writers.search(source.read_text(encoding="utf-8")))

    def test_reading_awareness_changes_nothing_on_disk(self):
        before = {
            path: path.stat().st_mtime_ns
            for path in sorted(DATA.rglob("*")) if path.is_file()
        }
        self.awareness.day_brief(DAY_ONE)
        self.awareness.flagged(BEFORE_ALL)
        self.awareness.find_contacts("reed")
        after = {
            path: path.stat().st_mtime_ns
            for path in sorted(DATA.rglob("*")) if path.is_file()
        }
        self.assertEqual(before, after)

    def test_no_live_outlook_or_graph_provider_is_shipped(self):
        joined = " ".join(s.read_text(encoding="utf-8") for s in self._sources())
        for name in ("graph.microsoft.com", "outlook.office", "MAPI", "Outlook.Application"):
            with self.subTest(name=name):
                self.assertNotIn(name, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
