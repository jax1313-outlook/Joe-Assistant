"""Automated tests for the assembled JOE, the Level 1 Assistant.

Every test writes only inside tests/_workspace, which is inside the plugin and
is removed afterward. No test contacts Dispatch. Tests that would contact
Outlook are marked and skipped unless ASSISTANT_TEST_OUTLOOK=1, so the suite
never starts Outlook by surprise.

Run:  py -m unittest discover -s tests -v      (from the plugin root)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import unittest
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from app import bootstrap  # noqa: E402,F401
from app.config import Config, ContainmentError, assert_within_plugin  # noqa: E402
from app.router import route, wants_driver_mode  # noqa: E402
from app.service import AssistantService  # noqa: E402
from contracts import (  # noqa: E402
    ActionRequest,
    AssistantResponse,
    Capability,
    Provenance,
    SourceMode,
)
from governance import (  # noqa: E402
    Governor,
    find_authority_claims,
    find_silence_consent,
)
from adapters import (  # noqa: E402
    DispatchPort,
    DispatchPortError,
    LibraryFsAdapter,
    OutlookComAdapter,
    ResearchProviderAdapter,
    SapiVoiceAdapter,
)
from adapters.outlook_com import (  # noqa: E402
    FORBIDDEN_COM_CALLS,
    DateRange,
    range_for,
    range_for_date,
)
from contracts import SourceClass  # noqa: E402
from adapters.reasoning_provider import (  # noqa: E402
    Answer,
    ReasoningProviderAdapter,
    ReasoningStatus,
)
from app.when import parse_when, wants_next_item  # noqa: E402
from app.router import asking_about_a_command  # noqa: E402

WORKSPACE = PLUGIN_ROOT / "tests" / "_workspace"
RUN_OUTLOOK = os.environ.get("ASSISTANT_TEST_OUTLOOK") == "1"

# Code written for this assembly, as opposed to the six vendored component
# packages (which carry their own suites) and this test file (whose own
# patterns would otherwise match themselves).
FIRST_PARTY = ("app", "adapters", "contracts", "governance", "ui/window.py")


def _first_party_sources(exclude_adapters: bool = False) -> list[Path]:
    root = str(PLUGIN_ROOT).replace("\\", "/")
    out: list[Path] = []
    for path in PLUGIN_ROOT.rglob("*.py"):
        text = str(path).replace("\\", "/")
        if any(skip in text for skip in ("_workspace", "__pycache__", "/tests/", "/proof/")):
            continue
        rel = text[len(root) + 1:]
        if not any(rel == m or rel.startswith(m + "/") for m in FIRST_PARTY):
            continue
        if exclude_adapters and rel.startswith("adapters/"):
            continue
        out.append(path)
    return out


def make_config(root: Path) -> Config:
    """A config whose runtime data lives in an isolated workspace."""
    base = json.loads(
        (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
            encoding="utf-8"
        )
    )
    base["paths"] = {
        "runtime_data": str(root / "runtime_data"),
        "logs": str(root / "logs"),
    }
    base["outlook"]["enabled"] = RUN_OUTLOOK
    path = root / "config.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    return Config.load(path)


class PluginTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = WORKSPACE / uuid.uuid4().hex[:8]
        self.root.mkdir(parents=True, exist_ok=True)
        self.service = AssistantService(make_config(self.root))

    def tearDown(self) -> None:
        try:
            self.service.shutdown()
        except Exception:
            pass
        shutil.rmtree(self.root, ignore_errors=True)


# ======================================================================
# Launch and shutdown
# ======================================================================


class TestLaunch(PluginTestCase):
    def test_service_starts(self):
        self.assertTrue(self.service.started_at)

    def test_all_six_components_are_packaged(self):
        report = bootstrap.component_report()
        self.assertEqual(len(report), 6)
        for entry in report:
            with self.subTest(component=entry["component"]):
                self.assertTrue(entry["present"], entry["component"] + " missing")
                self.assertTrue(entry["modules"])

    def test_entry_point_exists(self):
        self.assertTrue((PLUGIN_ROOT / "joe_main.py").is_file())

    def test_double_clickable_launcher_exists(self):
        launcher = PLUGIN_ROOT / "START_JOE.cmd"
        self.assertTrue(launcher.is_file())
        self.assertIn("joe_main.py", launcher.read_text(encoding="utf-8"))

    def test_every_required_launcher_exists(self):
        required = (
            "STOP_JOE.cmd", "RESTART_JOE.cmd", "JOE_STATUS.cmd",
            "RUN_TESTS.cmd", "RUN_PROOF.cmd", "OPEN_LOGS.cmd", "OPEN_DATA.cmd",
        )
        for name in required:
            with self.subTest(launcher=name):
                self.assertTrue((PLUGIN_ROOT / "launchers" / name).is_file())

    def test_shutdown_is_clean(self):
        self.service.shutdown()
        self.assertTrue(self.service.log.path.exists())

    def test_status_reports_every_capability(self):
        names = {s.name for s in self.service.status()}
        self.assertEqual(
            names,
            # Voice is TWO capabilities. Output is proven; input has never
        # heard a person. One chip across both was a false indicator.
        {"Reasoning", "Library", "Outlook", "Research",
         "Voice out", "Voice in", "Dispatch"},
        )

    def test_operating_mode_is_stated(self):
        self.assertTrue(self.service.operating_mode())


# ======================================================================
# Routing - ordinary language
# ======================================================================


class TestRouting(unittest.TestCase):
    def assert_route(self, text, capability):
        self.assertEqual(route(text).capability, capability, text)

    def test_retention_language(self):
        for text, intent in (
            ("Save this", "LEVEL_2"),
            ("Keep this", "LEVEL_2"),
            ("Level 2 this", "LEVEL_2"),
            ("Level 3 this", "LEVEL_3"),
            ("Level 3 this under Ideas", "LEVEL_3"),
            ("Make this printable", "PRINT"),
            ("Print this", "PRINT"),
            ("Delete this", "DELETE"),
            ("Forget this", "DELETE"),
        ):
            with self.subTest(text=text):
                chosen = route(text)
                self.assertEqual(chosen.capability, Capability.RETENTION)
                self.assertEqual(chosen.retention_intent, intent)

    def test_retention_beats_other_language(self):
        chosen = route("Save this and find the packet")
        self.assertEqual(chosen.capability, Capability.RETENTION)

    def test_level_3_destination_is_preserved(self):
        chosen = route("Level 3 this under Ideas")
        self.assertEqual(chosen.references.get("destination"), "Ideas")

    def test_library_language(self):
        for text in (
            "Find the broker packet",
            "Search for the rate floor",
            "Look up the appointment policy",
            "Where is the template",
        ):
            self.assert_route(text, Capability.LIBRARY)

    def test_operations_language(self):
        for text in (
            "What is on my calendar",
            "What matters about tomorrow",
            "Show me unread mail",
            "Who is J. Reed",
        ):
            self.assert_route(text, Capability.OPERATIONS)

    def test_research_language(self):
        for text in ("Research the road restriction", "Look into the northbound lane"):
            self.assert_route(text, Capability.RESEARCH)

    def test_explain_language(self):
        for text in (
            "Explain that in plain language",
            "What does the rate floor mean",
            "Walk me through the appointment policy",
        ):
            self.assert_route(text, Capability.EXPLAIN)

    def test_how_do_i_is_procedure_not_explain(self):
        """"How do I ..." asks for the procedure, not for a definition."""
        self.assert_route("How do I record detention", Capability.PROCEDURE)

    def test_help_language(self):
        for text in ("help", "what can you do"):
            self.assert_route(text, Capability.HELP)

    def test_unmatched_language_falls_back_to_answer(self):
        self.assert_route("zzzz qqqq", Capability.ANSWER)

    def test_capitalisation_and_punctuation_do_not_matter(self):
        for text in ("SAVE THIS.", "  save this!!  ", "Save This"):
            with self.subTest(text=text):
                self.assertEqual(route(text).capability, Capability.RETENTION)

    def test_driver_mode_detection(self):
        self.assertTrue(wants_driver_mode("What matters about tomorrow's run?"))
        self.assertTrue(wants_driver_mode("Just tell me the short answer"))
        self.assertFalse(wants_driver_mode("Find the broker packet"))

    def test_subject_extraction_strips_command_words(self):
        self.assertEqual(route("Find the broker packet").subject, "the broker packet")


# ======================================================================
# Retention lifecycle
# ======================================================================


class TestRetention(PluginTestCase):
    def ask_and_record(self, text="Find the rate floor policy"):
        interaction = self.service.ask(text)
        return interaction.record_id

    def test_level_1_is_the_default(self):
        record = self.service.memory.get(self.ask_and_record())
        self.assertEqual(record.state, "TEMPORARY")
        self.assertEqual(record.interaction_level, "LEVEL_1")

    def test_default_expiration_is_three_hours(self):
        from assistant_memory.clock import from_iso

        record = self.service.memory.get(self.ask_and_record())
        delta = from_iso(record.expires_at) - from_iso(record.created_at)
        self.assertEqual(delta, timedelta(hours=3))

    def test_save_promotes_to_level_2(self):
        record_id = self.ask_and_record()
        self.service.ask("Save this")
        record = self.service.memory.get(record_id)
        self.assertEqual(record.state, "SAVED")
        self.assertEqual(record.interaction_level, "LEVEL_2")
        self.assertIsNone(record.expires_at)

    def test_level_3_promotes_to_formal_with_destination(self):
        record_id = self.ask_and_record()
        response = self.service.ask("Level 3 this under Ideas").response
        record = self.service.memory.get(record_id)
        self.assertEqual(record.state, "FORMAL")
        self.assertEqual(record.interaction_level, "LEVEL_3")
        self.assertEqual(record.destination, "Ideas")
        self.assertIn("artifact", response.written.lower())

    def test_level_3_artifact_request_is_not_produced(self):
        self.ask_and_record()
        response = self.service.ask("Level 3 this").response
        self.assertIn("produced=False", response.written)

    def test_print_does_not_change_interaction_level(self):
        record_id = self.ask_and_record()
        before = self.service.memory.get(record_id).interaction_level
        self.service.ask("Print this")
        record = self.service.memory.get(record_id)
        self.assertEqual(record.state, "PRINT_READY")
        self.assertEqual(record.interaction_level, before)
        self.assertEqual(record.interaction_level, "LEVEL_1")

    def test_print_clears_expiration(self):
        record_id = self.ask_and_record()
        self.service.ask("Print this")
        self.assertIsNone(self.service.memory.get(record_id).expires_at)

    def test_print_never_claims_physical_printing(self):
        self.ask_and_record()
        response = self.service.ask("Print this").response
        joined = " ".join(response.notices) + response.written
        self.assertIn("Nothing was physically printed", joined)

    def test_print_from_level_2_keeps_level_2(self):
        record_id = self.ask_and_record()
        self.service.ask("Save this")
        self.service.ask("Print this")
        record = self.service.memory.get(record_id)
        self.assertEqual(record.state, "PRINT_READY")
        self.assertEqual(record.interaction_level, "LEVEL_2")

    def test_delete_removes_from_active_view(self):
        record_id = self.ask_and_record()
        self.service.ask("Delete this")
        self.assertEqual(self.service.memory.get(record_id).state, "DELETED")
        self.assertNotIn(
            record_id, [row["record_id"] for row in self.service.history()]
        )

    def test_delete_purges_content(self):
        record_id = self.ask_and_record("Find the sensitive broker rate")
        self.service.ask("Delete this")
        record = self.service.memory.get(record_id)
        self.assertIsNone(record.driver_request)
        self.assertIsNone(record.assistant_response)

    def test_deleted_record_refuses_later_commands(self):
        record_id = self.ask_and_record()
        self.service.ask("Delete this")
        response = self.service.apply_retention(record_id, "LEVEL_2")
        self.assertFalse(response.ok)

    def test_retention_command_creates_no_extra_record(self):
        self.ask_and_record()
        before = len(self.service.history())
        self.service.ask("Save this")
        self.assertEqual(len(self.service.history()), before)

    def test_retention_command_does_not_move_the_selection(self):
        record_id = self.ask_and_record()
        self.service.ask("Save this")
        self.assertEqual(self.service.selected_id, record_id)

    def test_two_commands_target_the_same_record(self):
        record_id = self.ask_and_record()
        self.service.ask("Save this")
        self.service.ask("Print this")
        record = self.service.memory.get(record_id)
        self.assertEqual(record.state, "PRINT_READY")
        self.assertEqual(record.interaction_level, "LEVEL_2")

    def test_expiration_sweeps_on_access(self):
        from assistant_memory.clock import FixedClock

        record_id = self.ask_and_record()
        self.service.memory.clock = FixedClock()
        self.service.memory.clock.advance(hours=4)
        self.service.memory.sweep()
        self.assertEqual(self.service.memory.get(record_id).state, "EXPIRED")
        self.assertNotIn(
            record_id, [row["record_id"] for row in self.service.history()]
        )

    def test_saved_records_survive_a_sweep(self):
        from assistant_memory.clock import FixedClock

        record_id = self.ask_and_record()
        self.service.ask("Save this")
        self.service.memory.clock = FixedClock()
        self.service.memory.clock.advance(hours=10)
        self.service.memory.sweep()
        self.assertEqual(self.service.memory.get(record_id).state, "SAVED")

    def test_records_survive_a_restart(self):
        record_id = self.ask_and_record()
        self.service.ask("Save this")
        self.service.shutdown()
        second = AssistantService(make_config(self.root))
        restored = second.reload_history()
        self.assertGreaterEqual(restored, 1)
        self.assertIn(record_id, [row["record_id"] for row in second.history()])
        second.shutdown()


# ======================================================================
# UI behaviour (headless - view model only)
# ======================================================================


class TestSelection(PluginTestCase):
    def test_new_interaction_becomes_selected(self):
        interaction = self.service.ask("Find the rate floor")
        self.assertEqual(self.service.selected_id, interaction.record_id)

    def test_history_marks_the_selected_row(self):
        self.service.ask("Find the rate floor")
        rows = self.service.history()
        self.assertEqual(sum(1 for row in rows if row["selected"]), 1)

    def test_select_by_id(self):
        first = self.service.ask("Find the rate floor").record_id
        self.service.ask("Find the appointment policy")
        self.assertTrue(self.service.select(first))
        self.assertEqual(self.service.selected_id, first)

    def test_select_unknown_id_is_refused(self):
        self.assertFalse(self.service.select("MEM-not-real"))

    def test_retention_with_nothing_selected_is_refused(self):
        response = self.service.ask("Save this").response
        self.assertFalse(response.ok)
        self.assertIn("no interaction selected", response.answer.lower())

    def test_empty_request_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.ask("   ")

    def test_ui_module_imports_without_opening_a_window(self):
        from ui import window

        self.assertTrue(hasattr(window, "AssistantWindow"))

    def test_ui_holds_no_business_logic(self):
        source = (PLUGIN_ROOT / "ui" / "window.py").read_text(encoding="utf-8")
        for forbidden in (
            "RetentionEngine(", "Library(", "OutlookComAdapter(",
            "ResearchProviderAdapter(", "Governor(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


# ======================================================================
# Truthful capability labelling
# ======================================================================


class TestLabelling(PluginTestCase):
    def test_library_results_are_labelled_by_source(self):
        response = self.service.ask("Find the rate floor policy").response
        if response.findings:
            self.assertTrue(response.provenance)
            for provenance in response.provenance:
                with self.subTest(source=provenance.source):
                    self.assertIn(provenance.mode, SourceMode.ALL)

    def test_sample_data_is_announced(self):
        response = self.service.ask("Research the northbound lane").response
        self.assertIn(SourceMode.SAMPLE, response.modes)
        self.assertTrue(
            any("SAMPLE DATA" in notice for notice in response.notices)
        )

    def test_research_fixture_is_never_called_live(self):
        probe = self.service.research.probe()
        self.assertFalse(probe["live_connection"])
        self.assertIn("no live research provider", probe["blocker"])

    def test_research_status_is_truthful(self):
        status = {s.name: s for s in self.service.status()}["Research"]
        self.assertFalse(status.live_connection)
        self.assertEqual(status.mode, SourceMode.SAMPLE)

    def test_voice_status_is_truthful(self):
        status = {s.name: s for s in self.service.status()}["Voice out"]
        probe = self.service.voice.probe()
        self.assertEqual(status.live_connection, bool(probe.get("tts_available")))

    def test_dispatch_is_never_reported_as_connected(self):
        status = {s.name: s for s in self.service.status()}["Dispatch"]
        self.assertFalse(status.live_connection)
        self.assertFalse(self.service.dispatch.connected)

    def test_outlook_status_reflects_configuration(self):
        status = {s.name: s for s in self.service.status()}["Outlook"]
        if not RUN_OUTLOOK:
            self.assertFalse(status.live_connection)

    def test_status_dict_declares_no_dispatch_contact(self):
        data = self.service.status_dict()
        self.assertFalse(data["dispatch_contacted"])
        self.assertEqual(data["operational_writes"], 0)


# ======================================================================
# Governance - constitutional boundaries
# ======================================================================


class TestGovernance(unittest.TestCase):
    def setUp(self):
        self.governor = Governor()

    def test_approval_claims_are_refused(self):
        for text in (
            "I approve the rate.", "The decision is to run it.",
            "I authorize the counter.", "This is now policy.",
        ):
            with self.subTest(text=text):
                response = AssistantResponse(capability="ANSWER", answer=text)
                out = self.governor.enforce(response)
                self.assertFalse(out.ok)
                self.assertIn("stopped that response", out.answer)

    def test_completed_action_claims_are_refused(self):
        for text in (
            "Email sent to the broker.", "Booked the load at 2.40.",
            "Payment sent this morning.", "Dispatch has been updated.",
            "The document was printed.",
        ):
            with self.subTest(text=text):
                out = self.governor.enforce(
                    AssistantResponse(capability="ANSWER", answer=text)
                )
                self.assertFalse(out.ok)

    def test_silence_is_never_consent(self):
        for text in (
            "I will proceed unless you say otherwise.",
            "This takes effect unless rejected.",
            "If I don't hear back I will apply it.",
            "I will auto-approve anything under 500.",
        ):
            with self.subTest(text=text):
                out = self.governor.enforce(
                    AssistantResponse(capability="ANSWER", answer=text)
                )
                self.assertFalse(out.ok)

    def test_ordinary_recommendation_passes(self):
        out = self.governor.enforce(
            AssistantResponse(
                capability="RESEARCH",
                answer="Recommend a four week trial, then review.",
            )
        )
        self.assertTrue(out.ok)

    def test_print_request_wording_is_allowed(self):
        out = self.governor.enforce(
            AssistantResponse(
                capability="RETENTION",
                answer="Print request recorded. Nothing was physically printed.",
            )
        )
        self.assertTrue(out.ok)

    def test_operational_claim_without_provenance_is_flagged(self):
        response = AssistantResponse(
            capability="ANSWER", answer="The load rate is 2.40 per mile."
        )
        self.governor.review(response)
        self.assertTrue(
            any("No source is attached" in n for n in response.notices)
        )

    def test_help_text_is_exempt_from_the_provenance_check(self):
        response = AssistantResponse(
            capability="HELP", answer="I can read your calendar and find a load."
        )
        self.governor.review(response)
        self.assertFalse(
            any("No source is attached" in n for n in response.notices)
        )

    def test_stale_live_data_is_flagged(self):
        response = AssistantResponse(
            capability="OPERATIONS",
            answer="Two appointments tomorrow.",
            provenance=[
                Provenance(
                    source="Outlook",
                    mode=SourceMode.LIVE,
                    as_of="2020-01-01T00:00:00Z",
                )
            ],
        )
        self.governor.review(response)
        self.assertTrue(any("may not be current" in n for n in response.notices))

    def test_fresh_live_data_is_not_flagged(self):
        response = AssistantResponse(
            capability="OPERATIONS",
            answer="Two appointments tomorrow.",
            provenance=[Provenance(source="Outlook", mode=SourceMode.LIVE)],
        )
        self.governor.review(response)
        self.assertFalse(any("may not be current" in n for n in response.notices))

    def test_authority_flags_are_forced_false(self):
        response = AssistantResponse(capability="ANSWER", answer="Fine.")
        response.approved = True
        response.decided = True
        response.acted_on = True
        response.operational_write = True
        self.governor.review(response)
        for name in ("approved", "decided", "acted_on", "operational_write"):
            with self.subTest(flag=name):
                self.assertFalse(getattr(response, name))

    def test_response_dict_always_reports_no_authority(self):
        response = AssistantResponse(capability="ANSWER", answer="Fine.")
        response.approved = True
        data = response.to_dict()
        for name in ("approved", "decided", "acted_on", "operational_write"):
            with self.subTest(flag=name):
                self.assertFalse(data[name])

    def test_claim_detection_helpers(self):
        self.assertIn("i approve", find_authority_claims("I approve this"))
        self.assertTrue(find_silence_consent("takes effect unless rejected"))
        self.assertEqual(find_authority_claims("Recommend a review"), [])


# ======================================================================
# Adapter isolation and failure
# ======================================================================


class TestAdapters(PluginTestCase):
    def test_a_failing_capability_does_not_stop_the_application(self):
        def explode(*_a, **_k):
            raise RuntimeError("simulated adapter failure")

        self.service.library.search = explode
        response = self.service.ask("Find the rate floor").response
        self.assertFalse(response.ok)
        self.assertIn("still working", response.answer)
        # the rest of the app still answers
        self.assertTrue(self.service.ask("help").response.ok)

    def test_outlook_adapter_refuses_a_non_read_script(self):
        from adapters.outlook_com import OutlookAdapterError

        adapter = OutlookComAdapter(enabled=True)
        with self.assertRaises(OutlookAdapterError):
            adapter._assert_read_only("$i.Send()")

    def test_outlook_generated_scripts_contain_no_write_call(self):
        adapter = OutlookComAdapter(enabled=True)
        for folder in ("calendar", "inbox", "contacts"):
            script = adapter._build_script(folder)
            for call in FORBIDDEN_COM_CALLS:
                with self.subTest(folder=folder, call=call):
                    self.assertNotIn(call, script)

    def test_calendar_script_sorts_by_start_date(self):
        """Regression: the calendar used to return folder order, which is not
        chronological, so "what is on tomorrow" could not be answered."""
        script = OutlookComAdapter(enabled=True)._build_script("calendar")
        self.assertIn('$source.Sort("[Start]")', script)
        self.assertIn("IncludeRecurrences", script)
        self.assertIn("$source.Restrict($filter)", script)
        self.assertIn("[Start] >=", script)

    def test_calendar_window_is_configurable(self):
        from adapters.outlook_com import range_for

        adapter = OutlookComAdapter(enabled=True, calendar_window_days=30)
        window = range_for("", days=adapter.calendar_window_days)
        self.assertEqual((window.end - window.start).days, 30)
        script = adapter._build_script("calendar")
        for placeholder in ("__WINDOW__", "__START__", "__END__", "__ACCOUNT__"):
            with self.subTest(placeholder=placeholder):
                self.assertNotIn(placeholder, script)

    def test_calendar_window_is_never_zero_or_negative(self):
        for value in (0, -5):
            with self.subTest(value=value):
                adapter = OutlookComAdapter(enabled=True, calendar_window_days=value)
                self.assertGreaterEqual(adapter.calendar_window_days, 1)

    def test_mail_and_contacts_are_not_date_windowed(self):
        """The window exists because recurring calendar series can iterate
        forever. Mail and contacts need no such preparation."""
        adapter = OutlookComAdapter(enabled=True)
        for folder in ("inbox", "contacts"):
            script = adapter._build_script(folder)
            with self.subTest(folder=folder):
                self.assertNotIn("IncludeRecurrences", script)
                self.assertNotIn("Restrict", script)

    def test_ordering_is_reported_honestly(self):
        from adapters.outlook_com import OutlookResult

        for ordering, date_ordered in (
            ("date_with_recurrences", True),
            ("date_no_recurrences", True),
            ("received_desc", False),
            ("display_name_asc", False),
            ("folder", False),
        ):
            with self.subTest(ordering=ordering):
                result = OutlookResult(ok=True, ordering=ordering)
                self.assertEqual(result.is_date_ordered, date_ordered)
                self.assertTrue(result.ordering_label)
        unsorted = OutlookResult(ok=True, ordering="folder")
        self.assertFalse(unsorted.is_sorted)
        self.assertIn("NOT sorted", unsorted.ordering_label)

    def test_provenance_states_the_ordering_and_window(self):
        from adapters.outlook_com import OutlookResult

        result = OutlookResult(
            ok=True, folder="Calendar", total=601, returned=9,
            account="ops@example.invalid",
            ordering="date_with_recurrences",
            window_start="2026-08-25T00:00:00",
            window_end="2026-09-08T00:00:00",
            window_label="tomorrow",
        )
        line = result.provenance().line()
        self.assertIn("9 of 601", line)
        self.assertIn("tomorrow", line)
        self.assertIn("date order", line)
        self.assertIn("ops@example.invalid", line)

    def test_calendar_script_still_passes_the_read_only_guard(self):
        """Sort and IncludeRecurrences change an in-memory view, not the
        mailbox. The read-only guard must still find nothing forbidden."""
        script = OutlookComAdapter(enabled=True)._build_script("calendar")
        for call in FORBIDDEN_COM_CALLS:
            with self.subTest(call=call):
                self.assertNotIn(call, script)

    @unittest.skipUnless(RUN_OUTLOOK, "set ASSISTANT_TEST_OUTLOOK=1 to read live Outlook")
    def test_live_calendar_is_returned_in_date_order(self):
        result = OutlookComAdapter(enabled=True).calendar()
        self.assertTrue(result.ok, result.error)
        self.assertTrue(result.is_date_ordered, result.ordering_note)
        starts = [str(i.get("start", "")) for i in result.items]
        parsed = []
        for text in starts:
            for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
                try:
                    parsed.append(__import__("datetime").datetime.strptime(text, fmt))
                    break
                except ValueError:
                    continue
        self.assertEqual(parsed, sorted(parsed), "calendar items are not in date order")

    def test_outlook_disabled_returns_unavailable_not_sample(self):
        adapter = OutlookComAdapter(enabled=False)
        result = adapter.calendar()
        self.assertFalse(result.ok)
        self.assertIn("disabled", result.error)
        self.assertEqual(result.items, [])

    def test_research_adapter_never_invents_findings(self):
        adapter = ResearchProviderAdapter(provider="none", fixtures_path=None)
        result = adapter.research("anything at all")
        self.assertFalse(result.ok)
        self.assertEqual(result.brief, {})

    def test_named_but_unimplemented_provider_fails_loudly(self):
        adapter = ResearchProviderAdapter(provider="some-vendor")
        result = adapter.research("anything")
        self.assertFalse(result.ok)
        self.assertIn("no adapter for it is implemented", result.error)

    def test_library_adapter_reports_missing_sources(self):
        adapter = LibraryFsAdapter(
            sources=[{"name": "Nowhere", "path": "Z:/not/real", "kind": "company"}]
        )
        statuses = adapter.load()
        self.assertFalse(statuses[0].exists)
        self.assertFalse(adapter.has_any_source)

    def test_library_company_material_outranks_sample_at_equal_score(self):
        hits = [
            {"score": 5, "is_company": False, "doc_id": "B"},
            {"score": 5, "is_company": True, "doc_id": "A"},
        ]
        hits.sort(key=lambda h: (-h["score"], not h["is_company"], h["doc_id"]))
        self.assertTrue(hits[0]["is_company"])

    def test_voice_adapter_disabled_reports_blocker(self):
        adapter = SapiVoiceAdapter(enabled=False)
        probe = adapter.probe()
        self.assertFalse(probe["tts_available"])
        self.assertIn("disabled", probe["blocker"])


# ======================================================================
# Dispatch boundary
# ======================================================================


class TestDispatchBoundary(PluginTestCase):
    def test_port_is_not_connected(self):
        self.assertFalse(self.service.dispatch.connected)

    def test_read_returns_unavailable_not_a_guess(self):
        result = self.service.dispatch.read("loads")
        self.assertFalse(result.ok)
        self.assertIn("not connected", result.error)
        self.assertEqual(result.data, {})

    def test_unpermitted_read_is_refused(self):
        for fact in ("bank_account", "everything", "internals"):
            with self.subTest(fact=fact):
                with self.assertRaises(DispatchPortError):
                    self.service.dispatch.read(fact)

    def test_no_operational_write_method_exists(self):
        for name in (
            "write", "update", "create", "delete", "accept_load", "book",
            "dispatch", "commit", "pay", "approve", "post",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(self.service.dispatch, name))

    def test_submission_is_a_proposal_not_an_action(self):
        request = self.service.dispatch.submit(
            "recommendation", "consider a four week trial"
        )
        data = request.to_dict()
        self.assertFalse(data["accepted"])
        self.assertFalse(data["performed"])
        self.assertFalse(data["auto_execute"])
        self.assertEqual(data["decision_required_from"], "Mike Zachary")

    def test_unpermitted_submission_kind_is_refused(self):
        with self.assertRaises(DispatchPortError):
            self.service.dispatch.submit("operational_write", "do it")

    def test_nothing_drains_the_submission_queue(self):
        self.service.dispatch.submit("draft", "a draft")
        for request in self.service.dispatch.pending():
            with self.subTest(kind=request.kind):
                self.assertFalse(request.accepted)
                self.assertFalse(request.performed)

    def test_no_dispatch_path_appears_in_configuration(self):
        text = (
            PLUGIN_ROOT / "configuration" / "joe.config.json"
        ).read_text(encoding="utf-8").lower()
        self.assertIn('"interface": "none"', text)
        self.assertIn('"enabled": false', text)


# ======================================================================
# Containment and independence
# ======================================================================


class TestContainment(PluginTestCase):
    def test_writes_outside_the_plugin_are_refused(self):
        for outside in (
            "C:/Windows/Temp/escape.json",
            "C:/Users/Public/escape.json",
            str(PLUGIN_ROOT.parent / "escape.json"),
        ):
            with self.subTest(path=outside):
                with self.assertRaises(ContainmentError):
                    assert_within_plugin(outside)

    def test_runtime_data_is_inside_the_plugin(self):
        self.assertTrue(
            str(self.service.config.runtime_data).startswith(str(PLUGIN_ROOT))
        )

    def test_logs_are_inside_the_plugin(self):
        self.assertTrue(str(self.service.config.logs).startswith(str(PLUGIN_ROOT)))

    def test_every_record_file_is_inside_the_plugin(self):
        self.service.ask("Find the rate floor")
        for record in self.service.memory.store.list_all():
            path = self.service.memory.store.path_for(record.record_id, record.state)
            with self.subTest(record=record.record_id):
                self.assertTrue(str(path.resolve()).startswith(str(PLUGIN_ROOT)))

    def test_no_assistant_code_references_dispatch_internals(self):
        suspicious = re.compile(
            r"dispatch[\\/](?:core|db|data|internal)|\.mdb|dispatch\.sqlite",
            re.IGNORECASE,
        )
        for path in _first_party_sources():
            with self.subTest(file=path.name):
                self.assertIsNone(suspicious.search(path.read_text(encoding="utf-8")))

    def test_no_manager_component_exists(self):
        for path in PLUGIN_ROOT.rglob("*.py"):
            if "_workspace" in str(path) or "__pycache__" in str(path):
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertIsNone(
                    re.search(r"\bclass\s+\w*Manager\b", text),
                    "a Manager component appeared in " + path.name,
                )

    def test_provider_code_stays_inside_adapters(self):
        """PowerShell and COM belong in adapters and nowhere else."""
        markers = ("powershell", "Outlook.Application", "subprocess", "win32com")
        for path in _first_party_sources(exclude_adapters=True):
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                with self.subTest(file=path.name, marker=marker):
                    self.assertNotIn(marker, text)


# ======================================================================
# Driver mode
# ======================================================================


class TestDriverMode(PluginTestCase):
    def test_spoken_summary_exists_for_every_response(self):
        for text in ("help", "Find the rate floor"):
            with self.subTest(text=text):
                response = self.service.ask(text).response
                self.assertTrue(response.spoken_summary)

    def test_spoken_summary_respects_the_word_limit(self):
        from assistant_voice.driver_mode import MAX_SPOKEN_WORDS

        response = self.service.ask("Find the rate floor policy").response
        self.assertLessEqual(
            len(response.spoken_summary.split()), MAX_SPOKEN_WORDS + 5
        )

    def test_written_response_is_always_preserved(self):
        response = self.service.ask("Find the rate floor policy").response
        self.assertTrue(response.written)
        self.assertGreaterEqual(len(response.written), len(response.answer))

    def test_no_voice_only_record(self):
        interaction = self.service.ask("help", channel="voice")
        record = self.service.memory.get(interaction.record_id)
        self.assertTrue(record.assistant_response)
        self.assertEqual(record.source_channel, "voice")


# ======================================================================
# Cognitive load
# ======================================================================


class TestCognitiveLoad(PluginTestCase):
    def test_no_record_id_is_required_to_operate(self):
        self.service.ask("Find the rate floor")
        response = self.service.ask("Save this").response
        self.assertTrue(response.ok)

    def test_ordinary_language_needs_no_syntax(self):
        for text in ("Save this", "Print this", "Level 3 this under Ideas"):
            with self.subTest(text=text):
                self.service.ask("Find the rate floor")
                self.assertTrue(self.service.ask(text).response.ok)

    def test_no_confirmation_queue_is_created(self):
        self.service.ask("Find the rate floor")
        self.service.ask("Level 3 this")
        self.assertEqual(len(self.service.dispatch.pending()), 0)

    def test_answer_comes_before_documents(self):
        response = self.service.ask("Find the rate floor policy").response
        self.assertTrue(response.answer)
        self.assertLess(len(response.answer), len(response.written) + 1)


# ======================================================================
# v2 - reasoning provider
# ======================================================================


class TestReasoningAdapter(unittest.TestCase):
    def test_none_reports_not_configured(self):
        state = ReasoningProviderAdapter(provider="none").status()
        self.assertEqual(state["status"], ReasoningStatus.NOT_CONFIGURED)
        self.assertFalse(state["live"])
        self.assertIn("no reasoning provider is configured", state["blocker"])

    def test_unsupported_provider_reports_error(self):
        state = ReasoningProviderAdapter(provider="some-vendor").status()
        self.assertEqual(state["status"], ReasoningStatus.ERROR)
        self.assertIn("no adapter", state["blocker"])

    def test_missing_credential_reports_not_configured(self):
        adapter = ReasoningProviderAdapter(
            provider="openai_compatible", endpoint="http://127.0.0.1:9/v1"
        )
        os.environ.pop("ASSISTANT_REASONING_KEY", None)
        state = adapter.status()
        self.assertEqual(state["status"], ReasoningStatus.NOT_CONFIGURED)
        self.assertTrue(state["credential_required"])
        self.assertFalse(state["credential_present"])

    def test_unreachable_provider_reports_unavailable(self):
        # port 9 is discard; nothing answers there
        adapter = ReasoningProviderAdapter(
            provider="ollama", endpoint="http://127.0.0.1:9"
        )
        state = adapter.status()
        self.assertEqual(state["status"], ReasoningStatus.UNAVAILABLE)
        self.assertFalse(state["live"])

    def test_every_required_status_state_exists(self):
        for state in (
            "REASONING LIVE", "REASONING NOT CONFIGURED",
            "REASONING UNAVAILABLE", "REASONING ERROR",
        ):
            with self.subTest(state=state):
                self.assertIn(state, ReasoningStatus.ALL)

    def test_contract_methods_exist(self):
        adapter = ReasoningProviderAdapter()
        for name in ("status", "answer", "summarize", "draft", "recommend"):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(adapter, name, None)))

    def test_calls_fail_safely_when_not_configured(self):
        adapter = ReasoningProviderAdapter(provider="none")
        for call in (
            lambda: adapter.answer("anything"),
            lambda: adapter.summarize("anything"),
            lambda: adapter.draft("anything"),
            lambda: adapter.recommend("anything"),
        ):
            answer = call()
            with self.subTest(task=answer.task):
                self.assertFalse(answer.ok)
                self.assertEqual(answer.text, "")
                self.assertEqual(answer.status, ReasoningStatus.NOT_CONFIGURED)

    def test_answers_never_carry_authority(self):
        answer = Answer(text="a recommendation")
        data = answer.to_dict()
        for flag in ("approved", "decided", "acted_on"):
            with self.subTest(flag=flag):
                self.assertFalse(data[flag])

    def test_credential_is_never_in_the_status_output(self):
        os.environ["ASSISTANT_REASONING_KEY"] = "sk-test-SHOULD-NOT-APPEAR-12345"
        try:
            adapter = ReasoningProviderAdapter(
                provider="openai_compatible", endpoint="http://127.0.0.1:9/v1"
            )
            text = json.dumps(adapter.status())
            self.assertNotIn("SHOULD-NOT-APPEAR", text)
            self.assertTrue(adapter.credential_present)
        finally:
            os.environ.pop("ASSISTANT_REASONING_KEY", None)

    def test_credential_is_redacted_from_error_text(self):
        os.environ["ASSISTANT_REASONING_KEY"] = "sk-test-SHOULD-NOT-APPEAR-12345"
        try:
            adapter = ReasoningProviderAdapter(provider="openai_compatible")
            message = adapter._safe_error(
                RuntimeError("failed with key sk-test-SHOULD-NOT-APPEAR-12345")
            )
            self.assertNotIn("SHOULD-NOT-APPEAR", message)
            self.assertIn("[redacted]", message)
        finally:
            os.environ.pop("ASSISTANT_REASONING_KEY", None)

    def test_no_credential_appears_in_configuration_files(self):
        """Check configuration VALUES, not prose.

        An earlier version scanned raw text and tripped on a comment saying
        "tenant_id and client_id are not secrets" - a false positive on the
        very sentence that exists to make this point. What matters is that no
        field name or value holds credential material.
        """
        credential_names = re.compile(
            r"secret|password|api[_-]?key|access[_-]?token|refresh[_-]?token|bearer",
            re.IGNORECASE,
        )
        key_shaped = re.compile(r"^(?:sk-|pat_|ghp_|ey[A-Za-z0-9_-]{20,})")

        def walk(node, path=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    if str(key).startswith("_"):
                        continue  # comments are prose, not values
                    here = path + "/" + str(key)
                    self.assertIsNone(
                        credential_names.search(str(key)),
                        "credential-shaped field name at " + here,
                    )
                    walk(value, here)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, path + "[" + str(index) + "]")
            elif isinstance(node, str):
                self.assertIsNone(
                    key_shaped.match(node.strip()),
                    "credential-shaped value at " + path,
                )

        for name in ("joe.config.json", "joe.config.template.json"):
            data = json.loads(
                (PLUGIN_ROOT / "configuration" / name).read_text(encoding="utf-8")
            )
            with self.subTest(file=name):
                walk(data)

    def test_copilot_configuration_holds_no_credential_fields(self):
        allowed = {
            "_comment", "tenant_id", "client_id", "time_zone",
            "web_enabled_default", "timeout_seconds",
        }
        for name in ("joe.config.json", "joe.config.template.json"):
            data = json.loads(
                (PLUGIN_ROOT / "configuration" / name).read_text(encoding="utf-8")
            )
            copilot = (data.get("reasoning") or {}).get("copilot") or {}
            with self.subTest(file=name):
                self.assertEqual(set(copilot) - allowed, set())
                self.assertNotIn("client_secret", copilot)

    def test_credentials_are_read_from_environment_only(self):
        source = (PLUGIN_ROOT / "adapters" / "reasoning_provider.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.environ.get", source)
        # a credential must never be read out of the config file
        self.assertNotIn('config.get("reasoning", "api_key"', source)


class TestReasoningInService(PluginTestCase):
    def test_status_includes_reasoning(self):
        names = {s.name for s in self.service.status()}
        self.assertIn("Reasoning", names)

    def test_reasoning_reported_not_live(self):
        status = {s.name: s for s in self.service.status()}["Reasoning"]
        self.assertFalse(status.live_connection)

    def test_summarize_without_provider_does_not_invent(self):
        response = self.service.ask("Summarize the rate floor policy").response
        joined = response.written + " ".join(response.notices)
        self.assertTrue(
            "no reasoning provider" in joined.lower()
            or "rather than a summary" in joined.lower()
        )

    def test_draft_without_provider_refuses(self):
        response = self.service.ask("Draft an email to the broker").response
        self.assertFalse(response.ok)
        self.assertIn("no reasoning provider", response.answer.lower())

    def test_procedure_without_a_governing_document_says_so(self):
        response = self.service.ask(
            "How do I zzzqqqxyz zzzqqqwvu"
        ).response
        self.assertFalse(response.ok)
        # The mission fixes this wording exactly: JOE must say no APPROVED
        # LEVEL 1 TRANSPORT procedure was found, not merely "no document".
        # Which company's procedure is missing is the operative fact.
        self.assertIn(
            "no approved level 1 transport procedure was found",
            response.answer.lower(),
        )
        self.assertEqual(response.failure, "no governing document")

    def test_application_works_with_provider_removed(self):
        self.service.reasoning = ReasoningProviderAdapter(provider="none")
        self.assertTrue(self.service.ask("help").response.ok)
        self.assertTrue(self.service.ask("Find the rate floor").response.ok)

    def test_ungrounded_answers_are_labelled(self):
        from app.reasoning_capabilities import UNGROUNDED_NOTICE

        response = AssistantResponse(capability="ANSWER", answer="x")
        wrapped = self.service._reasoned(
            "ANSWER",
            Answer(text="general thoughts", ok=True, provider="test"),
            [], [],
        )
        self.assertIn(UNGROUNDED_NOTICE, wrapped.notices)

    def test_grounded_answers_carry_their_sources(self):
        wrapped = self.service._reasoned(
            "SUMMARIZE",
            Answer(text="a summary", ok=True, provider="test", grounded=True),
            ["Rate Floor Policy (Operations/RATE_FLOOR_POLICY.md)"],
            [],
        )
        self.assertIn("GROUNDED IN", wrapped.written)
        self.assertEqual(len(wrapped.citations), 1)

    def test_general_reasoning_is_distinct_from_live_research(self):
        research = self.service.research.probe()
        reasoning = self.service.reasoning.status()
        self.assertFalse(research["live_connection"])
        self.assertFalse(reasoning["live"])
        response = self.service.ask("Research the northbound lane").response
        self.assertTrue(any("SAMPLE DATA" in n for n in response.notices))

    def test_no_message_is_ever_sent(self):
        data = self.service.status_dict()
        self.assertEqual(data["messages_sent"], 0)
        for name in ("send", "send_email", "reply", "forward", "transmit"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(self.service, name))


# ======================================================================
# v2 - calendar date filtering, mail and contact ordering, accounts
# ======================================================================


class TestCalendarDates(unittest.TestCase):
    NOW = datetime(2026, 8, 25, 10, 0)

    def test_date_words_are_recognised(self):
        cases = {
            "What is on my calendar tomorrow?": "tomorrow",
            "what's on today": "today",
            "next week": "next week",
            "this week": "this week",
            "what is next": "next",
            "show me the calendar": "default",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_when(text, self.NOW)[0], expected)

    def test_named_days_and_dates(self):
        for text, expected in (
            ("on Friday", datetime(2026, 8, 28).date()),
            ("September 2", datetime(2026, 9, 2).date()),
            ("on the 30th", datetime(2026, 8, 30).date()),
        ):
            with self.subTest(text=text):
                kind, anchor = parse_when(text, self.NOW)
                self.assertEqual(kind, "date")
                self.assertEqual(anchor.date(), expected)

    def test_next_item_language(self):
        for text in ("what is next", "my next appointment", "what's next"):
            with self.subTest(text=text):
                self.assertTrue(wants_next_item(text))

    def test_today_range_is_one_day(self):
        window = range_for("today", now=self.NOW)
        self.assertEqual(window.label, "today")
        self.assertEqual((window.end - window.start).days, 1)
        self.assertEqual(window.start.hour, 0)

    def test_tomorrow_range_starts_tomorrow(self):
        window = range_for("tomorrow", now=self.NOW)
        self.assertEqual(window.start.date(), datetime(2026, 8, 26).date())
        self.assertEqual((window.end - window.start).days, 1)

    def test_specific_date_range(self):
        window = range_for_date(datetime(2026, 9, 2))
        self.assertEqual(window.start.date(), datetime(2026, 9, 2).date())
        self.assertEqual((window.end - window.start).days, 1)

    def test_default_range_uses_the_window(self):
        window = range_for("", days=14, now=self.NOW)
        self.assertEqual((window.end - window.start).days, 14)

    def test_filter_dates_are_real_dates_not_format_specifiers(self):
        """Regression: .NET format specifiers were passed to Python strftime.

        `strftime("MM/dd/yyyy hh:mm tt")` returns those characters literally.
        Outlook does not reject a malformed filter - it matches nothing, so an
        empty calendar looked like a genuinely empty day.
        """
        for window in (
            range_for("today", now=self.NOW),
            range_for("tomorrow", now=self.NOW),
            range_for("", days=14, now=self.NOW),
            range_for_date(datetime(2026, 9, 2)),
        ):
            with self.subTest(label=window.label):
                for text in (window.ps_start(), window.ps_end()):
                    self.assertRegex(
                        text, r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2} (?:AM|PM)$"
                    )
                    for token in ("MM", "dd", "yyyy", "hh", "tt"):
                        self.assertNotIn(token, text)

    def test_malformed_filter_date_raises_rather_than_matching_nothing(self):
        from adapters.outlook_com import OutlookAdapterError
        import adapters.outlook_com as module

        original = module._PS_DATE
        module._PS_DATE = "MM/dd/yyyy hh:mm tt"  # the defect, restored
        try:
            with self.assertRaises(OutlookAdapterError):
                range_for("today", now=self.NOW).ps_start()
        finally:
            module._PS_DATE = original

    def test_calendar_script_carries_a_real_date_in_the_filter(self):
        script = OutlookComAdapter(enabled=True)._build_script(
            "calendar", date_range=range_for("tomorrow", now=self.NOW)
        )
        self.assertRegex(script, r"\[Start\] >= '\d{2}/\d{2}/\d{4}")
        self.assertNotIn("MM/dd/yyyy", script)

    def test_calendar_script_uses_the_requested_range(self):
        adapter = OutlookComAdapter(enabled=True)
        window = range_for("tomorrow", now=self.NOW)
        script = adapter._build_script("calendar", date_range=window)
        self.assertIn(window.ps_start(), script)
        self.assertIn(window.ps_end(), script)
        self.assertIn('$source.Sort("[Start]")', script)
        self.assertIn("IncludeRecurrences", script)


class TestMailAndContactOrdering(unittest.TestCase):
    def test_mail_is_sorted_newest_first(self):
        script = OutlookComAdapter(enabled=True)._build_script("inbox")
        self.assertIn('$source.Sort("[ReceivedTime]", $true)', script)

    def test_contacts_are_sorted_alphabetically(self):
        script = OutlookComAdapter(enabled=True)._build_script("contacts")
        self.assertIn('$source.Sort("[FileAs]")', script)

    def test_every_folder_declares_an_ordering(self):
        from adapters.outlook_com import ORDERING_LABEL, OutlookResult

        for ordering in ("date_with_recurrences", "received_desc", "display_name_asc"):
            with self.subTest(ordering=ordering):
                result = OutlookResult(ok=True, ordering=ordering)
                self.assertTrue(result.is_sorted)
                self.assertIn(ordering, ORDERING_LABEL)

    def test_folder_order_is_reported_as_unsorted(self):
        from adapters.outlook_com import OutlookResult

        result = OutlookResult(ok=True, ordering="folder")
        self.assertFalse(result.is_sorted)
        self.assertIn("NOT sorted", result.ordering_label)

    def test_all_scripts_still_pass_the_read_only_guard(self):
        adapter = OutlookComAdapter(enabled=True)
        for folder in ("calendar", "inbox", "contacts"):
            script = adapter._build_script(folder)
            for call in FORBIDDEN_COM_CALLS:
                with self.subTest(folder=folder, call=call):
                    self.assertNotIn(call, script)


class TestOutlookAccounts(unittest.TestCase):
    def test_account_can_be_designated(self):
        adapter = OutlookComAdapter(enabled=True, account="ops@example.invalid")
        script = adapter._build_script("inbox")
        self.assertIn("ops@example.invalid", script)
        self.assertIn("DeliveryStore.GetDefaultFolder", script)

    def test_empty_account_uses_the_default_store(self):
        script = OutlookComAdapter(enabled=True, account="")._build_script("inbox")
        self.assertIn("$ns.GetDefaultFolder", script)

    def test_account_name_with_a_quote_is_refused(self):
        from adapters.outlook_com import OutlookAdapterError

        adapter = OutlookComAdapter(enabled=True, account="bad'name")
        with self.assertRaises(OutlookAdapterError):
            adapter._build_script("inbox")

    def test_accounts_listing_script_is_read_only(self):
        from adapters.outlook_com import _ACCOUNTS_SCRIPT

        for call in FORBIDDEN_COM_CALLS:
            with self.subTest(call=call):
                self.assertNotIn(call, _ACCOUNTS_SCRIPT)

    def test_disabled_adapter_lists_no_accounts(self):
        self.assertEqual(OutlookComAdapter(enabled=False).accounts(), [])

    def test_result_carries_the_account_that_was_read(self):
        from adapters.outlook_com import OutlookResult

        result = OutlookResult(
            ok=True, folder="Inbox", account="ops@example.invalid",
            returned=5, total=100, ordering="received_desc",
        )
        self.assertIn("ops@example.invalid", result.provenance().line())


# ======================================================================
# v2 - asking about a command is not issuing it
# ======================================================================


class TestCommandQuestions(unittest.TestCase):
    def test_asking_how_does_not_execute(self):
        for text in (
            "How do I delete this",
            "How do I save something",
            "How do I create a Level 3 record",
            "What is the process for printing this",
            "Explain what delete this does",
        ):
            with self.subTest(text=text):
                self.assertNotEqual(route(text).capability, Capability.RETENTION)

    def test_issuing_the_command_still_works(self):
        for text in ("Save this", "Delete this", "Print this", "Level 3 this"):
            with self.subTest(text=text):
                self.assertEqual(route(text).capability, Capability.RETENTION)

    def test_guard_recognises_questions(self):
        self.assertTrue(asking_about_a_command("how do i delete this"))
        self.assertFalse(asking_about_a_command("delete this"))


class TestNewCapabilityRouting(unittest.TestCase):
    def test_new_capabilities_route(self):
        for text, expected in (
            ("Summarize this", Capability.SUMMARIZE),
            ("Give me the short version", Capability.SUMMARIZE),
            ("Draft an email to the broker", Capability.DRAFT),
            ("Compose a pickup notice", Capability.DRAFT),
            ("How do I create a Level 3 record", Capability.PROCEDURE),
            ("What is the procedure for proof of pickup", Capability.PROCEDURE),
        ):
            with self.subTest(text=text):
                self.assertEqual(route(text).capability, expected)

    def test_draft_beats_mail_reading(self):
        self.assertEqual(
            route("Draft an email to the broker").capability, Capability.DRAFT
        )
        self.assertEqual(
            route("Show me unread mail").capability, Capability.OPERATIONS
        )


# ======================================================================
# v2 - voice input path
# ======================================================================


class TestVoiceInputPath(PluginTestCase):
    def test_voice_channel_uses_the_same_path_as_typed_input(self):
        typed = self.service.ask("help", channel="text")
        spoken = self.service.ask("help", channel="voice")
        self.assertEqual(typed.response.capability, spoken.response.capability)

    def test_voice_interaction_is_retained_in_writing(self):
        interaction = self.service.ask("help", channel="voice")
        record = self.service.memory.get(interaction.record_id)
        self.assertEqual(record.source_channel, "voice")
        self.assertTrue(record.assistant_response)

    def test_failed_recognition_returns_a_reason_not_text(self):
        adapter = SapiVoiceAdapter(enabled=False)
        result = adapter.listen(1)
        self.assertFalse(result["recognized"])
        self.assertEqual(result["text"], "")
        self.assertTrue(result["error"])

    def test_ui_displays_recognised_text_before_processing(self):
        source = (PLUGIN_ROOT / "ui" / "window.py").read_text(encoding="utf-8")
        self.assertIn("HEARD:", source)
        self.assertIn("_handle_listen_result", source)
        self.assertIn('channel="voice"', source)

    def test_ui_never_substitutes_assumed_text(self):
        source = (PLUGIN_ROOT / "ui" / "window.py").read_text(encoding="utf-8")
        self.assertIn("Nothing was assumed and nothing was invented", source)

    def test_text_mode_survives_voice_failure(self):
        self.service.voice = SapiVoiceAdapter(enabled=False)
        self.assertTrue(self.service.ask("help").response.ok)

    def test_voice_test_mode_exists(self):
        source = (PLUGIN_ROOT / "ui" / "window.py").read_text(encoding="utf-8")
        self.assertIn("VOICE INPUT TEST", source)

    def test_short_spoken_answer_plus_full_written_answer(self):
        response = self.service.ask("Find the rate floor policy").response
        self.assertTrue(response.spoken_summary)
        self.assertTrue(response.written)
        self.assertLessEqual(
            len(response.spoken_summary.split()), len(response.written.split())
        )


# ======================================================================
# v2 - drafting is never sending
# ======================================================================


class TestDraftingBoundary(PluginTestCase):
    def test_no_send_capability_anywhere(self):
        for holder in (self.service, self.service.outlook, self.service.dispatch):
            for name in ("send", "send_email", "reply", "forward", "transmit", "post"):
                with self.subTest(holder=type(holder).__name__, name=name):
                    self.assertFalse(hasattr(holder, name))

    def test_no_mail_transport_module_is_imported(self):
        forbidden = {"smtplib", "imaplib", "poplib", "email"}
        for path in _first_party_sources():
            text = path.read_text(encoding="utf-8")
            for module in forbidden:
                with self.subTest(file=path.name, module=module):
                    self.assertNotIn("import " + module, text)

    def test_draft_labelling_exists_in_the_capability(self):
        source = (PLUGIN_ROOT / "app" / "reasoning_capabilities.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("DRAFT ONLY", source)
        self.assertIn("NOT SENT", source)


# ======================================================================
# Microsoft 365 Copilot provider - mocked HTTP, no tenant required
# ======================================================================


class FakeGraph:
    """Stands in for Microsoft Graph. Records every request it is given."""

    def __init__(self, reply_text="Two stops tomorrow. Nothing needs a decision tonight.",
                 citations=None, annotations=None, sensitivity=None,
                 fail_on=None, http_error=None):
        self.reply_text = reply_text
        self.citations = citations or []
        self.annotations = annotations or []
        self.sensitivity = sensitivity or {}
        self.fail_on = fail_on or set()
        self.http_error = http_error
        self.calls = []
        self.turn = 0

    def __call__(self, url, body, auth):
        from adapters.m365_copilot import CopilotApiError

        self.calls.append({"url": url, "body": body})
        for marker in self.fail_on:
            if marker in url:
                raise CopilotApiError(self.http_error or "simulated failure")
        if url.endswith("/conversations"):
            return {"id": "conv-1234", "createdDateTime": "2026-08-25T10:00:00Z",
                    "displayName": "", "status": "active", "turnCount": 0}
        self.turn += 1
        attributions = (
            [dict(a, attributionType="citation") for a in self.citations]
            + [dict(a, attributionType="annotation") for a in self.annotations]
        )
        return {
            "id": "conv-1234",
            "turnCount": self.turn,
            "messages": [
                {"id": "m-echo", "text": body["message"]["text"],
                 "attributions": [], "sensitivityLabel": {}},
                {"id": "m-reply", "text": self.reply_text,
                 "attributions": attributions,
                 "sensitivityLabel": self.sensitivity},
            ],
        }

    @property
    def last_body(self):
        return self.calls[-1]["body"] if self.calls else {}


CITATION = {
    "providerDisplayName": "Rate Floor Policy",
    "seeMoreWebUrl": "https://contoso.sharepoint.com/Docs/Rate-Floor.docx",
    "attributionSource": "grounding",
}


def copilot(**kwargs):
    from adapters.m365_copilot import M365CopilotProvider

    return M365CopilotProvider(transport=FakeGraph(**kwargs))


class TestCopilotProvider(unittest.TestCase):
    def test_conversation_is_created_with_an_empty_body(self):
        provider = copilot()
        conversation_id = provider.start_conversation()
        self.assertEqual(conversation_id, "conv-1234")
        first = provider._transport.calls[0]
        self.assertTrue(first["url"].endswith("/copilot/conversations"))
        self.assertEqual(first["body"], {})

    def test_chat_posts_to_the_conversation(self):
        provider = copilot()
        provider.chat("what is on tomorrow")
        self.assertTrue(provider._transport.calls[-1]["url"].endswith("/conv-1234/chat"))

    def test_reply_is_the_last_message_not_the_echo(self):
        provider = copilot(reply_text="The answer.")
        reply = provider.chat("the question")
        self.assertEqual(reply.text, "The answer.")

    def test_location_hint_is_always_sent(self):
        provider = copilot()
        provider.chat("anything")
        self.assertEqual(
            provider._transport.last_body["locationHint"]["timeZone"],
            "America/New_York",
        )

    def test_multi_turn_reuses_one_conversation(self):
        provider = copilot()
        provider.chat("first")
        provider.chat("second")
        provider.chat("third")
        creates = [c for c in provider._transport.calls if c["url"].endswith("/conversations")]
        self.assertEqual(len(creates), 1)
        self.assertEqual(provider.turns, 3)

    def test_reset_starts_a_new_conversation(self):
        provider = copilot()
        provider.chat("first")
        provider.reset_conversation()
        provider.chat("second")
        creates = [c for c in provider._transport.calls if c["url"].endswith("/conversations")]
        self.assertEqual(len(creates), 2)

    def test_additional_context_is_sent(self):
        provider = copilot()
        provider.chat("question", additional_context=["a grounding fact"])
        self.assertEqual(
            provider._transport.last_body["additionalContext"],
            [{"text": "a grounding fact"}],
        )

    def test_empty_additional_context_is_omitted(self):
        provider = copilot()
        provider.chat("question", additional_context=["", "   "])
        self.assertNotIn("additionalContext", provider._transport.last_body)

    def test_files_are_sent_as_contextual_resources(self):
        provider = copilot()
        provider.chat("summarize", files=["https://contoso.sharepoint.com/a.docx"])
        files = provider._transport.last_body["contextualResources"]["files"]
        self.assertEqual(files, [{"uri": "https://contoso.sharepoint.com/a.docx"}])

    def test_web_context_is_always_explicit(self):
        provider = copilot()
        provider.chat("question")
        self.assertIn("webContext", provider._transport.last_body["contextualResources"])
        self.assertFalse(
            provider._transport.last_body["contextualResources"]["webContext"]["isWebEnabled"]
        )

    def test_web_search_can_be_enabled_per_turn(self):
        provider = copilot()
        provider.chat("question", web_enabled=True)
        self.assertTrue(
            provider._transport.last_body["contextualResources"]["webContext"]["isWebEnabled"]
        )

    def test_research_is_the_only_path_that_enables_web(self):
        provider = copilot()
        provider.research("what changed on I-95")
        self.assertTrue(
            provider._transport.last_body["contextualResources"]["webContext"]["isWebEnabled"]
        )

    def test_context_is_truncated_to_the_limit(self):
        from adapters.m365_copilot import M365CopilotProvider

        provider = M365CopilotProvider(transport=FakeGraph(), max_context_chars=500)
        provider.chat("q", additional_context=["x" * 5000])
        sent = provider._transport.last_body["additionalContext"][0]["text"]
        self.assertEqual(len(sent), 500)


class TestCopilotAttribution(unittest.TestCase):
    def test_citations_are_parsed_and_preserved(self):
        provider = copilot(citations=[CITATION])
        reply = provider.chat("question")
        self.assertEqual(len(reply.citations), 1)
        self.assertIn("Rate Floor Policy", reply.sources()[0])
        self.assertIn("sharepoint.com", reply.sources()[0])

    def test_annotations_are_kept_separate_from_citations(self):
        provider = copilot(
            citations=[CITATION],
            annotations=[{"seeMoreWebUrl": "https://example.invalid/x"}],
        )
        reply = provider.chat("question")
        self.assertEqual(len(reply.citations), 1)
        self.assertEqual(len(reply.annotations), 1)

    def test_sensitivity_label_is_preserved(self):
        provider = copilot(
            sensitivity={"displayName": "Confidential", "isEncrypted": True}
        )
        reply = provider.chat("question")
        self.assertEqual(reply.sensitivity_label, "Confidential")
        self.assertTrue(reply.is_encrypted)
        answer = provider._answer_from(reply, "answer")
        self.assertEqual(answer.sensitivity_label, "Confidential")

    def test_null_sensitivity_fields_are_dropped(self):
        provider = copilot(sensitivity={"displayName": None, "isEncrypted": None})
        reply = provider.chat("question")
        self.assertEqual(reply.sensitivity_label, "")
        self.assertFalse(reply.is_encrypted)


class TestCopilotProvenanceClasses(unittest.TestCase):
    def test_citations_without_web_are_work_grounded(self):
        provider = copilot(citations=[CITATION])
        reply = provider.chat("question", web_enabled=False)
        self.assertEqual(reply.source_class(), SourceClass.COPILOT_WORK_GROUNDED)

    def test_citations_with_web_are_web_grounded(self):
        provider = copilot(citations=[CITATION])
        reply = provider.chat("question", web_enabled=True)
        self.assertEqual(reply.source_class(), SourceClass.COPILOT_WEB_GROUNDED)

    def test_no_citations_is_general_reasoning(self):
        provider = copilot(citations=[])
        reply = provider.chat("question", web_enabled=True)
        self.assertEqual(reply.source_class(), SourceClass.COPILOT_GENERAL_REASONING)

    def test_supplied_files_keep_it_work_grounded_even_with_web_on(self):
        provider = copilot(citations=[CITATION])
        reply = provider.chat(
            "question", files=["https://contoso.sharepoint.com/a.docx"], web_enabled=True
        )
        self.assertEqual(reply.source_class(), SourceClass.COPILOT_WORK_GROUNDED)

    def test_copilot_never_claims_a_local_source_class(self):
        provider = copilot(citations=[CITATION])
        for web in (True, False):
            reply = provider.chat("question", web_enabled=web)
            with self.subTest(web=web):
                self.assertNotIn(reply.source_class(), SourceClass.LOCAL)
                self.assertNotIn(reply.source_class(), SourceClass.NOT_IMPLEMENTED)

    def test_provenance_carries_the_class(self):
        provider = copilot(citations=[CITATION])
        answer = provider.answer("question")
        provenance = provider.provenance_for(answer)
        self.assertTrue(provenance.is_copilot)
        self.assertFalse(provenance.is_local_read)
        self.assertIn("Copilot", provenance.line())

    def test_local_reads_declare_their_own_class(self):
        from adapters.library_fs import LibraryFsAdapter
        from adapters.outlook_com import OutlookResult

        library = LibraryFsAdapter(sources=[])
        hit = {"source_name": "Company Library", "mode": SourceMode.LIVE,
               "relative_path": "a/b.md"}
        self.assertEqual(
            library.provenance_for(hit).source_class, SourceClass.LOCAL_LIBRARY
        )
        result = OutlookResult(ok=True, folder="Calendar", ordering="date_with_recurrences")
        self.assertEqual(
            result.provenance().source_class, SourceClass.LOCAL_OUTLOOK
        )

    def test_the_seven_source_classes_exist(self):
        for name in (
            "LOCAL_LIBRARY", "LOCAL_OUTLOOK", "COPILOT_WORK_GROUNDED",
            "COPILOT_WEB_GROUNDED", "COPILOT_GENERAL_REASONING",
            "ROUTE_RISK_EVENT", "DISPATCH_FACT",
        ):
            with self.subTest(name=name):
                self.assertIn(getattr(SourceClass, name), SourceClass.ALL)


class TestCopilotContract(unittest.TestCase):
    def test_the_reasoning_contract_is_satisfied(self):
        provider = copilot()
        for name in ("status", "answer", "summarize", "draft", "recommend"):
            with self.subTest(name=name):
                self.assertTrue(callable(getattr(provider, name, None)))

    def test_answers_never_carry_authority(self):
        provider = copilot()
        for call in (
            provider.answer, provider.summarize, provider.draft, provider.recommend,
        ):
            answer = call("anything")
            data = answer.to_dict()
            with self.subTest(task=answer.task):
                for flag in ("approved", "decided", "acted_on"):
                    self.assertFalse(data[flag])

    def test_no_action_method_exists(self):
        provider = copilot()
        for name in (
            "send", "send_email", "reply", "approve", "decide", "schedule",
            "create_event", "update", "delete", "book", "dispatch", "commit",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(provider, name))

    def test_status_declares_every_boundary_false(self):
        state = copilot().status()
        for flag in (
            "can_approve", "can_decide", "can_send", "can_schedule",
            "can_modify_outlook", "can_modify_dispatch",
        ):
            with self.subTest(flag=flag):
                self.assertFalse(state[flag])

    def test_status_declares_preview(self):
        state = copilot().status()
        self.assertTrue(state["preview"])
        self.assertIn("PILOT / PREVIEW", state["label"])
        self.assertIn("not supported", state["preview_notice"])

    def test_no_client_secret_is_used(self):
        self.assertFalse(copilot().status()["client_secret_used"])


class TestCopilotFailure(unittest.TestCase):
    def test_streamed_turn_falls_back_to_synchronous(self):
        provider = copilot(fail_on={"chatOverStream"})
        reply = provider.chat_over_stream("question")
        self.assertTrue(reply.text)
        self.assertIn("used synchronous", provider.last_error)

    def test_api_failure_returns_an_error_answer_not_an_exception(self):
        provider = copilot(fail_on={"/chat"}, http_error="HTTP 403: access denied")
        answer = provider.answer("question")
        self.assertFalse(answer.ok)
        self.assertEqual(answer.text, "")
        self.assertIn("403", answer.error)

    def test_empty_reply_is_reported_not_invented(self):
        provider = copilot(reply_text="")
        answer = provider.answer("question")
        self.assertFalse(answer.ok)
        self.assertIn("empty", answer.error)

    def test_http_error_text_carries_no_header_material(self):
        provider = copilot(fail_on={"/chat"}, http_error="HTTP 401: sign-in expired")
        answer = provider.answer("question")
        self.assertNotIn("Bearer", answer.error)
        self.assertNotIn("Authorization", answer.error)

    def test_unsigned_in_provider_reports_not_configured(self):
        from adapters.m365_copilot import M365CopilotProvider

        provider = M365CopilotProvider()  # no transport, no auth configured
        state = provider.status()
        self.assertIn(state["status"], ReasoningStatus.ALL)
        self.assertFalse(state["live"])
        answer = provider.answer("question")
        self.assertFalse(answer.ok)
        self.assertEqual(answer.text, "")


class TestCopilotAuthentication(unittest.TestCase):
    def setUp(self):
        from adapters.m365_copilot_auth import CopilotAuth

        self.root = WORKSPACE / uuid.uuid4().hex[:8]
        self.root.mkdir(parents=True, exist_ok=True)
        self.auth = CopilotAuth(cache_dir=self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_unconfigured_state(self):
        from adapters.m365_copilot_auth import AuthState

        self.assertIn(
            self.auth.state(), (AuthState.NOT_CONFIGURED, AuthState.LIBRARY_MISSING)
        )
        self.assertFalse(self.auth.configured)

    def test_no_client_secret_is_used(self):
        """A public desktop client has nowhere safe to keep a secret.

        Checks what matters: MSAL is built as a PUBLIC client, no credential
        is handed to it, and no confidential-client path exists. The string
        "client_secret" appearing inside a status flag named
        `client_secret_used` is not a finding.
        """
        source = (PLUGIN_ROOT / "adapters" / "m365_copilot_auth.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("PublicClientApplication", source)
        self.assertNotIn("ConfidentialClientApplication", source)
        self.assertNotIn("client_credential", source)
        self.assertNotIn("client_secret=", source)
        self.assertFalse(self.auth.status()["client_secret_used"])

    def test_status_exposes_no_token_material(self):
        text = json.dumps(self.auth.status())
        for marker in ("access_token", "refresh_token", "id_token", "Bearer "):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, text)

    def test_authorization_header_is_none_when_signed_out(self):
        self.assertIsNone(self.auth.authorization_header())

    def test_msal_is_used_not_hand_rolled_oauth(self):
        source = (PLUGIN_ROOT / "adapters" / "m365_copilot_auth.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("msal", source)
        self.assertIn("PublicClientApplication", source)
        # no hand-built token endpoint calls
        for marker in ("oauth2/v2.0/token", "grant_type", "urn:ietf:params:oauth"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_cache_is_encrypted_or_memory_only_never_plain_text(self):
        source = (PLUGIN_ROOT / "adapters" / "m365_copilot_auth.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("FilePersistenceWithDataProtection", source)
        # the plain FilePersistence class must not be used as a fallback
        self.assertNotIn("FilePersistence(", source)

    def test_all_seven_graph_scopes_are_requested(self):
        from adapters.m365_copilot_auth import GRAPH_SCOPES

        self.assertEqual(
            set(GRAPH_SCOPES),
            {
                "Sites.Read.All", "Mail.Read", "People.Read.All",
                "OnlineMeetingTranscript.Read.All", "Chat.Read",
                "ChannelMessage.Read.All", "ExternalItem.Read.All",
            },
        )

    def test_sign_out_reports_what_it_cleared(self):
        message = self.auth.sign_out()
        self.assertIn("Signed out", message)

    def test_no_token_is_written_in_plain_text(self):
        self.auth.sign_out()
        for path in self.root.rglob("*"):
            if path.is_file():
                with self.subTest(file=path.name):
                    self.assertNotIn(
                        "access_token", path.read_bytes().decode("utf-8", "ignore")
                    )


class TestAccountDiscoveryHonesty(unittest.TestCase):
    """A mailbox that could not be asked about is not a mailbox that is absent.

    Outlook went unresponsive during a real investigation and `knows_account`
    returned False for the APPROVED Ops@ mailbox - the same answer it gives for
    a mailbox that genuinely is not in the profile. A timeout was being reported
    as a missing mailbox."""

    def _adapter(self, powershell):
        from adapters.outlook_com import OutlookComAdapter
        a = OutlookComAdapter.__new__(OutlookComAdapter)
        a.enabled = True
        a._accounts = None
        a.accounts_known = False
        a.last_error = ""
        a._assert_read_only = lambda script: None
        a._powershell = powershell
        return a

    @staticmethod
    def _ok(smtps):
        payload = json.dumps(
            {"ok": True, "accounts": [{"smtp": s, "display_name": s} for s in smtps]}
        )
        return lambda script: (True, payload, "")

    @staticmethod
    def _dead(reason="Outlook did not respond within 90 seconds"):
        return lambda script: (False, "", reason)

    def test_unreachable_outlook_reports_unknown_not_absent(self):
        a = self._adapter(self._dead())
        self.assertIsNone(a.knows_account("Ops@l1truck.com"))
        self.assertEqual(a.account_status("Ops@l1truck.com"), "unknown")
        self.assertFalse(a.accounts_known)

    def test_a_genuinely_missing_mailbox_is_absent_not_unknown(self):
        a = self._adapter(self._ok(["Ops@l1truck.com"]))
        self.assertIs(a.knows_account("Admin@l1truck.com"), False)
        self.assertEqual(a.account_status("Admin@l1truck.com"), "absent")
        self.assertTrue(a.accounts_known)

    def test_a_present_mailbox_is_present(self):
        a = self._adapter(self._ok(["Ops@l1truck.com", "Admin@l1truck.com"]))
        self.assertIs(a.knows_account("Admin@l1truck.com"), True)
        self.assertEqual(a.account_status("Admin@l1truck.com"), "present")

    def test_a_failed_enumeration_is_never_cached(self):
        """Outlook is busy for a minute and fine the next. Caching the failure
        turned a transient timeout into a permanent 'there are no mailboxes'."""
        a = self._adapter(self._dead())
        a.accounts()
        self.assertIsNone(a._accounts, "ignorance was cached")
        a._powershell = self._ok(["Ops@l1truck.com"])
        # no refresh flag - it must retry on its own
        self.assertIs(a.knows_account("Ops@l1truck.com"), True)

    def test_unknown_is_still_falsy_so_existing_callers_are_unharmed(self):
        a = self._adapter(self._dead())
        self.assertFalse(bool(a.knows_account("Ops@l1truck.com")))

    def test_malformed_output_is_unknown_not_empty(self):
        a = self._adapter(lambda script: (True, "not json", ""))
        self.assertEqual(a.account_status("Ops@l1truck.com"), "unknown")

    def test_outlook_disabled_is_a_real_answer_not_ignorance(self):
        a = self._adapter(self._ok([]))
        a.enabled = False
        self.assertEqual(a.account_status("Ops@l1truck.com"), "absent")
        self.assertTrue(a.accounts_known)


class TestCopilotProofRunner(unittest.TestCase):
    """The verdict PROVE_COPILOT.cmd reaches, exercised without a tenant.

    The check is PER PROVENANCE ENTRY. A correct live answer routinely carries
    a COPILOT_* entry alongside LOCAL_LIBRARY entries - Copilot reasoned, and
    the Library was genuinely read. An earlier version flattened the classes
    and failed on any local class appearing, which rejected a real, correct,
    live Copilot answer and reported live reasoning as a failure."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "prove_copilot", PLUGIN_ROOT / "proof" / "prove_copilot.py"
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    class _R:
        def __init__(self, ok=True):
            self.ok = ok

    @staticmethod
    def _prov(source_class, is_copilot, source="src"):
        from contracts import Provenance, SourceMode
        return Provenance(source=source, mode=SourceMode.LIVE,
                          source_class=source_class)

    def _copilot(self, cls="COPILOT_GENERAL_REASONING"):
        return self._prov(cls, True, "Microsoft 365 Copilot")

    def _library(self):
        return self._prov("LOCAL_LIBRARY", False, "Library / Company Library")

    def test_a_good_copilot_answer_passes(self):
        passed, _, reasons = self.mod.judge(
            self._R(), "Detention is waiting time beyond the free period.",
            [self._copilot()])
        self.assertTrue(passed, reasons)

    def test_copilot_reasoning_alongside_a_genuine_library_read_passes(self):
        """The exact shape of the first real live answer."""
        passed, breaches, reasons = self.mod.judge(
            self._R(), "Detention is waiting time beyond the free period.",
            [self._copilot(), self._library(), self._library()])
        self.assertTrue(passed, reasons)
        self.assertEqual(breaches, [])

    def test_work_and_web_grounded_answers_pass(self):
        for cls in ("COPILOT_WORK_GROUNDED", "COPILOT_WEB_GROUNDED"):
            with self.subTest(source_class=cls):
                passed, _, reasons = self.mod.judge(
                    self._R(), "An answer.", [self._copilot(cls)])
                self.assertTrue(passed, reasons)

    def test_an_empty_reply_fails(self):
        passed, _, reasons = self.mod.judge(self._R(), "   ", [self._copilot()])
        self.assertFalse(passed)
        self.assertTrue(any("empty" in r for r in reasons))

    def test_a_provider_failure_fails(self):
        passed, _, reasons = self.mod.judge(
            self._R(ok=False), "An answer.", [self._copilot()])
        self.assertFalse(passed)
        self.assertTrue(any("failure" in r for r in reasons))

    def test_a_genuine_local_read_is_not_mistaken_for_a_masquerade(self):
        """LOCAL_LIBRARY sourced from the Library is correct, not a breach."""
        passed, breaches, reasons = self.mod.judge(
            self._R(), "An answer.", [self._copilot(), self._library()])
        self.assertTrue(passed, reasons)
        self.assertEqual(breaches, [])

    def test_copilot_content_wearing_a_local_class_fails(self):
        """The masquerade: SOURCE says Copilot, CLASS claims a local read.

        Checked on the source string, not on `is_copilot` - that property is
        derived from source_class, so the two can never disagree and a check
        written against it is dead code that always passes."""
        for cls in ("LOCAL_LIBRARY", "LOCAL_OUTLOOK",
                    "ROUTE_RISK_EVENT", "DISPATCH_FACT"):
            with self.subTest(source_class=cls):
                bad = self._prov(cls, True, "Microsoft 365 Copilot")
                passed, breaches, reasons = self.mod.judge(
                    self._R(), "A thoroughly persuasive answer.",
                    [self._copilot(), bad])
                self.assertFalse(passed, cls + " was accepted")
                self.assertEqual(len(breaches), 1)
                self.assertTrue(any("may never claim" in r for r in reasons))

    def test_a_library_only_answer_fails_because_copilot_was_never_asked(self):
        """This is what the first live run actually produced."""
        passed, _, reasons = self.mod.judge(
            self._R(), "SOME_DOCUMENT - Company Library/...", [self._library()])
        self.assertFalse(passed)
        self.assertTrue(any("never asked" in r for r in reasons))

    def test_no_provenance_at_all_fails(self):
        passed, _, reasons = self.mod.judge(self._R(), "An answer.", [])
        self.assertFalse(passed)
        self.assertTrue(any("never asked" in r for r in reasons))

    def test_the_forbidden_list_matches_the_contract(self):
        from contracts import SourceClass
        self.assertEqual(
            set(self.mod.FORBIDDEN_CLASSES),
            {SourceClass.LOCAL_LIBRARY, SourceClass.LOCAL_OUTLOOK,
             SourceClass.ROUTE_RISK_EVENT, SourceClass.DISPATCH_FACT})

    def test_a_refusal_is_not_a_substantive_follow_up(self):
        """A refusal can name the subject while answering nothing."""
        text = "The supplied context does not discuss detention time."
        self.assertTrue(any(w in text.lower() for w in self.mod.FOLLOW_UP_TOPIC))
        self.assertTrue(any(m in text.lower() for m in self.mod.REFUSAL_MARKERS))

    def test_a_real_follow_up_answer_is_not_flagged_as_a_refusal(self):
        text = ("Detention is normally paid by the shipper or broker, and the "
                "free time and hourly rate are set in the rate confirmation.")
        self.assertTrue(any(w in text.lower() for w in self.mod.FOLLOW_UP_TOPIC))
        self.assertFalse(any(m in text.lower() for m in self.mod.REFUSAL_MARKERS))

    def test_the_follow_up_prompt_has_no_standalone_referent(self):
        """If it named its subject, it would prove nothing about multi-turn."""
        self.assertNotIn("detention", self.mod.FOLLOW_UP.lower())
        self.assertIn("it", self.mod.FOLLOW_UP.lower())

    def test_the_runner_writes_a_blocked_report_that_claims_nothing(self):
        self.mod.write_report("no tenant id", "", "", [], False, [])
        text = (PLUGIN_ROOT / "proof" / "COPILOT_LIVE_PROOF.md").read_text(encoding="utf-8")
        self.assertIn("BLOCKED", text)
        self.assertIn("NOT CONNECTED", text)
        self.assertNotIn("PASS - reasoning is LIVE", text)


class TestTokenCacheOnDisk(unittest.TestCase):
    """If a token cache exists on this machine, it must be encrypted.

    Everything claimed about credential handling rests on this one file. It is
    checked against the bytes actually written, not against configuration
    saying encryption was requested."""

    # The well-known Windows DPAPI blob header: version 01000000 followed by
    # the provider GUID d08c9ddf-0115-d111-8c7a-00c04fc297eb.
    DPAPI_HEADER = bytes.fromhex("01000000d08c9ddf0115d1118c7a00c04fc297eb")

    def setUp(self):
        self.cache = PLUGIN_ROOT / "runtime_data" / "auth" / "copilot_token_cache.bin"
        if not self.cache.exists():
            self.skipTest("no token cache on this machine - nobody has signed in")
        self.blob = self.cache.read_bytes()

    def test_the_cache_is_a_dpapi_blob(self):
        self.assertTrue(
            self.blob.startswith(self.DPAPI_HEADER),
            "token cache is not DPAPI-encrypted: " + self.blob[:20].hex(),
        )

    def test_no_token_material_appears_in_clear(self):
        for marker in (b"access_token", b"refresh_token", b"id_token",
                       b"Bearer", b"eyJ", b'{"'):
            with self.subTest(marker=marker.decode("latin1")):
                self.assertNotIn(marker, self.blob)

    def test_the_cache_does_not_leak_the_account(self):
        self.assertNotIn(b"l1truck", self.blob.lower())

    def test_the_bytes_look_encrypted_not_merely_obfuscated(self):
        """Base64 or a simple encoding would show far lower entropy."""
        import collections, math
        counts = collections.Counter(self.blob)
        entropy = -sum(
            (c / len(self.blob)) * math.log2(c / len(self.blob))
            for c in counts.values()
        )
        self.assertGreater(entropy, 7.5, "entropy %.2f - not encrypted" % entropy)

    def test_the_cache_lives_inside_the_plugin(self):
        self.assertTrue(str(self.cache.resolve()).startswith(str(PLUGIN_ROOT.resolve())))


class TestVoiceProofRunner(unittest.TestCase):
    """The scoring PROVE_VOICE_INPUT.cmd will apply, exercised without a voice.

    Mike gets one sitting at the microphone. The scoring should not be
    discovered to be wrong during it."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "prove_voice_input", PLUGIN_ROOT / "proof" / "prove_voice_input.py"
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_an_exact_match_scores_one(self):
        self.assertEqual(
            self.mod.word_overlap("What is my next appointment",
                                  "What is my next appointment"), 1.0)

    def test_casing_and_punctuation_do_not_penalise_the_speaker(self):
        self.assertEqual(
            self.mod.word_overlap("What is my next appointment",
                                  "what is my next appointment?"), 1.0)

    def test_nothing_recognized_scores_zero(self):
        self.assertEqual(self.mod.word_overlap("Save this", ""), 0.0)

    def test_a_wrong_phrase_scores_zero(self):
        self.assertEqual(self.mod.word_overlap("Save this", "delete everything"), 0.0)

    def test_a_partial_hearing_scores_partially(self):
        score = self.mod.word_overlap("Read me the detention policy",
                                      "read me the detention")
        self.assertAlmostEqual(score, 4 / 5)

    def test_extra_words_do_not_defeat_a_correct_phrase(self):
        """Recognizers pad. The phrase being present is what matters."""
        self.assertEqual(
            self.mod.word_overlap("Save this", "um save this please"), 1.0)

    def test_a_repeated_word_is_not_double_counted(self):
        """Two 'this' heard must not satisfy two different expected words."""
        self.assertAlmostEqual(
            self.mod.word_overlap("save this now", "this this this"), 1 / 3)

    def test_the_pass_threshold_is_a_real_bar(self):
        """0.6 must reject a phrase that was mostly missed."""
        score = self.mod.word_overlap("What is my next appointment", "what is")
        self.assertLess(score, 0.6)

    def test_the_phrases_are_fixed_so_the_result_is_comparable(self):
        self.assertEqual(len(self.mod.PHRASES), 3)
        for phrase in self.mod.PHRASES:
            self.assertTrue(phrase.strip())

    def test_a_blocked_run_claims_nothing(self):
        self.mod.write_report([], blocked="nobody was present to speak")
        text = (PLUGIN_ROOT / "proof" / "VOICE_INPUT_PROOF.md").read_text(encoding="utf-8")
        self.assertIn("BLOCKED", text)
        self.assertIn("must not be reported as working", text)
        self.assertNotIn("proven for these phrases", text)

    def test_a_partial_run_is_reported_as_not_proven(self):
        self.mod.write_report(
            [{"phrase": "Save this", "recognized": "save this", "overlap": 1.0,
              "ok": True, "error": ""},
             {"phrase": "Read me the detention policy", "recognized": "",
              "overlap": 0.0, "ok": False, "error": ""}],
            blocked="",
        )
        text = (PLUGIN_ROOT / "proof" / "VOICE_INPUT_PROOF.md").read_text(encoding="utf-8")
        self.assertIn("1 of 2 phrases recognized", text)
        self.assertIn("**Voice input is NOT proven.**", text)


class TestLiveResearch(unittest.TestCase):
    """Research is live only when actual attributions come back.

    Web grounding switched on with nothing returned is general reasoning with
    search enabled. Reporting that as research would be the exact mislabelling
    the provenance contract exists to prevent."""

    class _Answer:
        def __init__(self, ok=True, text="Findings.", sources=None,
                     source_class="COPILOT_WEB_GROUNDED", error=""):
            self.ok = ok
            self.text = text
            self.sources = sources if sources is not None else [
                "FDOT advisory  https://d4fdot.com/x"]
            self.source_class = source_class
            self.error = error
            self.sensitivity_label = ""

    class _Copilot:
        def __init__(self, answer, live=True):
            self._answer = answer
            self._live = live
            self.asked = []

        def status(self):
            return {"live": self._live}

        def research(self, question, context="", sources=None):
            self.asked.append(question)
            return self._answer

    def _adapter(self, answer, live=True):
        from adapters.research_provider import ResearchProviderAdapter
        copilot = self._Copilot(answer, live)
        adapter = ResearchProviderAdapter(provider="m365_copilot", copilot=copilot)
        return adapter, copilot

    def test_web_grounding_enabled_reports_live(self):
        adapter, _ = self._adapter(self._Answer())
        self.assertTrue(adapter.has_live_provider)
        self.assertEqual(adapter.probe()["mode"], "LIVE")

    def test_attributions_are_carried_through(self):
        adapter, _ = self._adapter(self._Answer(
            sources=["FDOT  https://d4fdot.com/a", "511  https://fl511.com/b"]))
        result = adapter.research("I-95")
        self.assertEqual(len(result.brief["citations"]), 2)

    def test_a_retrieval_timestamp_is_always_recorded(self):
        adapter, _ = self._adapter(self._Answer())
        result = adapter.research("I-95")
        self.assertTrue(result.brief["retrieved_at"])
        self.assertTrue(result.read_at)

    def test_no_attributions_is_not_reported_as_web_grounded(self):
        """The mislabelling this whole capability has to avoid."""
        adapter, _ = self._adapter(self._Answer(
            sources=[], source_class="COPILOT_GENERAL_REASONING"))
        result = adapter.research("I-95")
        self.assertFalse(result.brief["web_grounded"])
        self.assertEqual(result.brief["citations"], [])

    def test_an_unsigned_in_provider_is_not_live(self):
        """Naming a provider in configuration is not having one."""
        adapter, _ = self._adapter(self._Answer(), live=False)
        self.assertFalse(adapter.has_live_provider)
        self.assertNotEqual(adapter.probe()["mode"], "LIVE")

    def test_a_provider_error_is_reported_not_swallowed(self):
        adapter, _ = self._adapter(self._Answer(ok=False, error="graph 503"))
        result = adapter.research("I-95")
        self.assertFalse(result.ok)
        self.assertIn("503", result.error)

    def test_an_exception_does_not_become_an_empty_finding(self):
        class Boom:
            def status(self):
                return {"live": True}

            def research(self, *a, **k):
                raise RuntimeError("network down")

        from adapters.research_provider import ResearchProviderAdapter
        adapter = ResearchProviderAdapter(provider="m365_copilot", copilot=Boom())
        result = adapter.research("I-95")
        self.assertFalse(result.ok)
        self.assertIn("network down", result.error)
        self.assertEqual(result.brief, {})

    def test_sample_mode_survives_and_is_never_called_live(self):
        """Sample mode stays for deterministic testing. It is not live."""
        from adapters.research_provider import ResearchProviderAdapter
        adapter = ResearchProviderAdapter(provider="fixture", copilot=None)
        self.assertFalse(adapter.has_live_provider)
        self.assertNotEqual(adapter.probe()["mode"], "LIVE")

    def test_the_report_names_every_required_section(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "prove_research", PLUGIN_ROOT / "proof" / "prove_research.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(len(mod.REQUIRED_SECTIONS), 12)
        for section in ("QUESTION", "RETRIEVAL TIME", "ATTRIBUTIONS",
                        "SOURCE CONFLICTS", "UNCERTAINTY", "SHORT SPOKEN ANSWER"):
            self.assertIn(section, mod.REQUIRED_SECTIONS)

    def test_the_official_source_notice_is_not_optional(self):
        from app.service import AssistantService
        self.assertIn("does not replace official DOT or 511",
                      AssistantService.OFFICIAL_SOURCE_NOTICE)


class TestDriverVoiceLoop(unittest.TestCase):
    """Continuous voice, tested without a microphone, speaker, or display.

    The loop is separated from the window precisely so this is possible. A
    voice feature that can only be tested by speaking is a voice feature that
    is never regression-tested."""

    def setUp(self):
        from app.driver_voice import DriverVoiceLoop, VoiceState
        self.VoiceState = VoiceState
        self.heard = []
        self.said = []
        self.asked = []

        def listen(seconds):
            return self.heard.pop(0) if self.heard else ""

        def speak(text):
            self.said.append(text)
            return True

        def ask(text, short=False, save=False):
            self.asked.append({"text": text, "short": short, "save": save})
            return ("Short answer.", "MEM-TEST-1")

        self.loop = DriverVoiceLoop(listen=listen, speak=speak, ask=ask,
                                    listen_seconds=0, pause_seconds=0)

    # ---- command recognition ------------------------------------------

    def test_ordinary_commands_are_recognised(self):
        from app.driver_voice import recognise_command
        for phrase, expected in (
            ("Joe, stop.", "STOP"),
            ("stop", "STOP"),
            ("Joe, repeat that.", "REPEAT"),
            ("short version", "SHORTER"),
            ("Joe, save that.", "SAVE"),
            ("turn voice off", "VOICE_OFF"),
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(recognise_command(phrase), expected)

    def test_an_ordinary_question_is_not_a_command(self):
        from app.driver_voice import recognise_command
        for phrase in ("what is on my calendar tomorrow",
                       "explain what matters about today",
                       "who do I call about the load"):
            with self.subTest(phrase=phrase):
                self.assertEqual(recognise_command(phrase), "")

    def test_asking_about_a_command_does_not_execute_it(self):
        """The same defect the typed router had: a question is not an order."""
        from app.driver_voice import recognise_command
        for phrase in ("what does save that mean",
                       "how do I turn voice off",
                       "should I save that"):
            with self.subTest(phrase=phrase):
                self.assertEqual(recognise_command(phrase), "")

    def test_the_wake_word_is_stripped_from_the_request(self):
        from app.driver_voice import strip_wake_word
        self.assertEqual(strip_wake_word("Joe, what is my next stop?"),
                         "what is my next stop")

    def test_noise_is_not_sent_anywhere(self):
        """An open microphone with nobody speaking returns fragments."""
        from app.driver_voice import is_usable_utterance
        for noise in ("", "  ", "uh", "the"):
            with self.subTest(noise=repr(noise)):
                self.assertFalse(is_usable_utterance(noise))
        self.assertTrue(is_usable_utterance("what is my delivery address"))

    # ---- the loop ------------------------------------------------------

    def test_a_spoken_question_is_answered_and_spoken_back(self):
        self.heard = ["what is my delivery address"]
        self.loop._handle("what is my delivery address")
        self.assertEqual(len(self.asked), 1)
        self.assertIn("Short answer.", self.said)
        self.assertTrue(self.loop.turns[-1].answered)
        self.assertTrue(self.loop.turns[-1].spoken)

    def test_every_voice_turn_produces_a_written_record(self):
        """Voice is transport. It is never the only record."""
        self.loop._handle("what is my delivery address")
        self.assertTrue(self.loop.turns[-1].record_id)

    def test_the_microphone_is_suppressed_while_speaking(self):
        """Without this JOE hears its own answer and talks to itself."""
        observed = []

        def speak(text):
            observed.append(self.loop.microphone_suppressed)
            return True

        self.loop._speak = speak
        self.loop.say("An answer.")
        self.assertEqual(observed, [True], "microphone was open while speaking")
        self.assertFalse(self.loop.microphone_suppressed, "suppression stuck on")

    def test_repeat_says_the_last_answer_again_without_re_asking(self):
        self.loop._handle("what is my delivery address")
        asked_before = len(self.asked)
        self.said.clear()
        self.loop._handle("Joe, repeat that")
        self.assertEqual(len(self.asked), asked_before, "repeat re-ran the request")
        self.assertEqual(self.said, ["Short answer."])

    def test_repeat_with_nothing_said_yet_says_so(self):
        self.loop._handle("Joe, repeat that")
        self.assertIn("not said anything yet", self.said[-1])

    def test_short_version_is_passed_through_to_the_request(self):
        self.loop._handle("short version")
        self.assertTrue(self.asked[-1]["short"])

    def test_save_that_is_passed_through_as_a_retention_request(self):
        self.loop._handle("Joe, save that")
        self.assertTrue(self.asked[-1]["save"])

    def test_voice_off_by_voice_stops_the_loop(self):
        self.loop.start()
        self.assertTrue(self.loop.is_on)
        self.loop._handle("turn voice off")
        self.assertFalse(self.loop.is_on)
        self.assertEqual(self.loop.state, self.VoiceState.OFF)

    def test_stop_is_not_answered_as_a_question(self):
        self.loop._handle("Joe, stop")
        self.assertEqual(self.asked, [], "stop was sent through as a request")

    def test_a_microphone_failure_does_not_end_the_conversation(self):
        def boom(seconds):
            raise RuntimeError("microphone gone")

        self.loop._listen = boom
        self.loop.start()
        time.sleep(0.15)
        still_on = self.loop.is_on
        self.loop.stop()
        self.loop.join()
        self.assertTrue(still_on, "a microphone error killed voice mode")
        self.assertTrue(any(t.error for t in self.loop.turns))

    def test_a_request_failure_is_reported_not_swallowed(self):
        def boom(text, short=False, save=False):
            raise RuntimeError("copilot down")

        self.loop._ask = boom
        self.loop._handle("what is my delivery address")
        turn = self.loop.turns[-1]
        self.assertIn("copilot down", turn.error)
        self.assertFalse(turn.answered)
        self.assertTrue(self.said, "the failure was silent")

    def test_toggle_turns_it_on_and_off(self):
        self.assertFalse(self.loop.is_on)
        self.assertTrue(self.loop.toggle())
        self.assertFalse(self.loop.toggle())
        self.loop.join()

    def test_state_changes_are_reported_for_the_button(self):
        seen = []
        self.loop._on_state = seen.append
        self.loop.say("An answer.")
        self.assertIn(self.VoiceState.SPEAKING, seen)


class TestVoiceButtonAppearance(unittest.TestCase):
    """The button's appearance IS the status indicator.

    The mission is explicit: lowercase and subdued when off, uppercase and
    white when listening. Mike should be able to tell whether JOE is listening
    without reading a word of it, so these are asserted rather than left to
    drift with a future style change."""

    def test_off_is_lowercase_and_subdued(self):
        import ui.window as w
        self.assertEqual(w.VOICE_OFF_TEXT, "voice")
        self.assertTrue(w.VOICE_OFF_TEXT.islower())
        self.assertNotEqual(w.VOICE_OFF_COLOURS["fg"].lower(), "#ffffff")

    def test_on_is_uppercase_and_white(self):
        import ui.window as w
        self.assertEqual(w.VOICE_ON_TEXT, "VOICE")
        self.assertTrue(w.VOICE_ON_TEXT.isupper())
        self.assertEqual(w.VOICE_ON_COLOURS["fg"].lower(), "#ffffff")

    def test_the_two_states_are_visually_unmistakable(self):
        import ui.window as w
        self.assertNotEqual(w.VOICE_ON_COLOURS["bg"], w.VOICE_OFF_COLOURS["bg"])
        self.assertNotEqual(w.VOICE_ON_FONT, w.VOICE_OFF_FONT)

    def test_the_old_push_to_talk_button_is_gone(self):
        """The prohibited workflow was press, speak, stop, review, upload."""
        source = (PLUGIN_ROOT / "ui" / "window.py").read_text(encoding="utf-8")
        self.assertNotIn('("Listen", self._on_listen)', source)


class TestMicrophones(unittest.TestCase):
    """Microphone enumeration, selection truth, and fallback.

    The constraint that shapes all of this: System.Speech can only bind to the
    Windows DEFAULT input device. A preference is therefore remembered and
    reported, never silently enforced - otherwise Mike speaks into a headset
    while JOE listens to the laptop lid."""

    def _report(self, rows, preferred=""):
        from adapters.microphones import Microphone, MicrophoneReport
        return MicrophoneReport(
            ok=True, preferred=preferred,
            devices=[Microphone(name=n, state=s) for n, s in rows])

    def test_only_connected_non_loopback_devices_are_usable(self):
        from adapters.microphones import STATE_ACTIVE, STATE_NOT_PRESENT
        report = self._report([
            ("Stereo Mix", STATE_ACTIVE),
            ("Internal Microphone", STATE_ACTIVE),
            ("Headset", STATE_NOT_PRESENT),
        ])
        self.assertEqual([d.name for d in report.available],
                         ["Internal Microphone"])

    def test_a_loopback_device_is_never_selected(self):
        """Stereo Mix records what the machine PLAYS - JOE would hear itself."""
        from adapters.microphones import STATE_ACTIVE
        report = self._report([("Stereo Mix", STATE_ACTIVE)])
        self.assertIsNone(report.in_use)

    def test_no_connected_device_is_reported_plainly(self):
        from adapters.microphones import STATE_NOT_PRESENT
        report = self._report([("Headset", STATE_NOT_PRESENT)])
        self.assertIsNone(report.in_use)
        self.assertIn("no recording device is connected", report.blocker())

    def test_falling_back_to_the_windows_default_needs_no_configuration(self):
        """First run must work with nothing set."""
        from adapters.microphones import STATE_ACTIVE
        report = self._report([("Internal Microphone", STATE_ACTIVE)],
                              preferred="")
        self.assertTrue(report.preference_honoured)
        self.assertEqual(report.blocker(), "")
        self.assertEqual(report.in_use.name, "Internal Microphone")

    def test_a_preference_windows_is_honouring_is_reported_as_honoured(self):
        from adapters.microphones import STATE_ACTIVE
        report = self._report(
            [("Headset (LEVN LE-HS015 Hands-Free)", STATE_ACTIVE)],
            preferred="LEVN LE-HS015")
        self.assertTrue(report.preference_honoured)

    def test_a_preference_windows_ignores_is_reported_not_hidden(self):
        """The failure this exists to prevent: silently hearing the wrong mic."""
        from adapters.microphones import STATE_ACTIVE, STATE_NOT_PRESENT
        report = self._report([
            ("Internal Microphone", STATE_ACTIVE),
            ("Headset", STATE_NOT_PRESENT),
        ], preferred="Headset")
        self.assertFalse(report.preference_honoured)
        blocker = report.blocker()
        self.assertIn("Headset", blocker)
        self.assertIn("Internal Microphone", blocker)
        self.assertIn("Windows default", blocker)

    def test_a_disappeared_device_falls_back_to_the_windows_default(self):
        from adapters.microphones import STATE_ACTIVE, STATE_NOT_PRESENT
        report = self._report([
            ("Internal Microphone", STATE_ACTIVE),
            ("Headset", STATE_NOT_PRESENT),
        ], preferred="Headset")
        self.assertEqual(report.in_use.name, "Internal Microphone")

    def test_bluetooth_endpoints_are_identified(self):
        from adapters.microphones import Microphone, STATE_ACTIVE
        for name in ("Headset", "Headset (LEVN LE-HS015 Hands-Free)",
                     "Bluetooth Audio", "AirPods"):
            with self.subTest(name=name):
                self.assertTrue(
                    Microphone(name=name, state=STATE_ACTIVE).looks_like_bluetooth)
        self.assertFalse(
            Microphone(name="Internal Microphone",
                       state=STATE_ACTIVE).looks_like_bluetooth)

    def test_device_states_are_translated_into_plain_language(self):
        from adapters.microphones import (Microphone, STATE_ACTIVE,
                                          STATE_DISABLED, STATE_NOT_PRESENT)
        self.assertEqual(Microphone("m", STATE_ACTIVE).status,
                         "connected and available")
        self.assertEqual(Microphone("m", STATE_DISABLED).status,
                         "disabled in Windows")
        self.assertEqual(Microphone("m", STATE_NOT_PRESENT).status,
                         "not connected")

    def test_an_unreadable_device_list_is_unknown_not_empty(self):
        from adapters.microphones import MicrophoneReport
        report = MicrophoneReport(ok=False, error="powershell timed out")
        self.assertIn("powershell timed out", report.blocker())

    def test_the_selection_limit_is_documented_not_hidden(self):
        source = (PLUGIN_ROOT / "adapters" / "microphones.py").read_text(
            encoding="utf-8")
        self.assertIn("SetInputToDefaultAudioDevice", source)
        self.assertIn("remembered and reported, not enforced", source)

    def test_the_service_exposes_microphone_diagnostics(self):
        from app.service import AssistantService
        self.assertTrue(hasattr(AssistantService, "__init__"))
        source = (PLUGIN_ROOT / "app" / "service.py").read_text(encoding="utf-8")
        self.assertIn("MicrophoneAdapter", source)
        self.assertIn("self.microphones", source)


class TestMailboxRegistry(unittest.TestCase):
    """Email Connection Layer v1.

    The single-account model assumed one mailbox held mail, calendar, AND
    contacts. On this profile it does not, and pointing the one setting at
    Ops@ answered every calendar question with an empty day - true of the
    mailbox, false of Mike's day."""

    def _registry(self, rows, defaults=None, ok=True, error=""):
        from adapters.mailbox_registry import (MailboxConnection,
                                               MailboxRegistry, Discovery)
        connections = [
            MailboxConnection(connection_id=r["id"],
                              friendly_name=r["name"],
                              address=r["address"],
                              enabled=r.get("enabled", True))
            for r in rows
        ]
        registry = MailboxRegistry(connections=connections,
                                   defaults=defaults or {})
        return registry

    def _discovery(self, accounts=(), stores=(), folders=(), ok=True, error=""):
        from adapters.mailbox_registry import Discovery
        return Discovery(ok=ok, error=error, accounts=list(accounts),
                         stores=list(stores), folders=list(folders))

    # ---- three-view reconciliation --------------------------------------

    def test_a_full_account_is_found_in_all_three_views(self):
        from adapters.mailbox_registry import FULL_ACCOUNT, PRESENT
        discovery = self._discovery(
            accounts=[{"smtp": "Ops@l1truck.com"}],
            stores=[{"display_name": "Ops@l1truck.com", "exchange_type": 4}],
            folders=["Ops@l1truck.com"])
        status, kind, views = discovery.classify("Ops@l1truck.com")
        self.assertEqual(status, PRESENT)
        self.assertEqual(kind, FULL_ACCOUNT)
        self.assertEqual(views, ["Accounts", "Stores", "Folders"])

    def test_a_shared_mailbox_is_found_even_though_accounts_omits_it(self):
        """The case reading Accounts alone would silently hide."""
        from adapters.mailbox_registry import PRESENT, SHARED_MAILBOX
        discovery = self._discovery(
            accounts=[{"smtp": "Ops@l1truck.com"}],
            stores=[{"display_name": "Shared@l1truck.com", "exchange_type": 4}],
            folders=["Shared@l1truck.com"])
        status, kind, views = discovery.classify("Shared@l1truck.com")
        self.assertEqual(status, PRESENT)
        self.assertEqual(kind, SHARED_MAILBOX)
        self.assertNotIn("Accounts", views)

    def test_a_pst_is_identified_as_a_data_file(self):
        from adapters.mailbox_registry import DATA_FILE
        discovery = self._discovery(
            stores=[{"display_name": "Archive", "exchange_type": -1,
                     "file_path": "C:/x/archive.pst"}],
            folders=["Archive"])
        _, kind, _ = discovery.classify("Archive")
        self.assertEqual(kind, DATA_FILE)

    def test_a_mailbox_outlook_does_not_expose_is_absent(self):
        from adapters.mailbox_registry import ABSENT
        discovery = self._discovery(accounts=[{"smtp": "Ops@l1truck.com"}],
                                    stores=[{"display_name": "Ops@l1truck.com"}],
                                    folders=["Ops@l1truck.com"])
        status, _, _ = discovery.classify("Missing@l1truck.com")
        self.assertEqual(status, ABSENT)

    # ---- unknown is not absent ------------------------------------------

    def test_a_failed_discovery_is_unknown_not_absent(self):
        from adapters.mailbox_registry import UNKNOWN
        discovery = self._discovery(ok=False, error="Outlook did not respond")
        status, _, _ = discovery.classify("Ops@l1truck.com")
        self.assertEqual(status, UNKNOWN)

    def test_a_failure_is_never_cached_as_absence(self):
        """A mailbox unreachable for a minute must not be declared gone."""
        from adapters.mailbox_registry import UNKNOWN
        registry = self._registry([{"id": "ops", "name": "Operations",
                                    "address": "Ops@l1truck.com"}])
        registry._failed("Outlook did not respond within 90 seconds")
        self.assertIsNone(registry.last_discovery)
        self.assertEqual(registry.connections[0].status, UNKNOWN)
        self.assertIn("did not respond", registry.connections[0].failure_message)

    # ---- per-capability sources -----------------------------------------

    def test_a_mailbox_with_no_calendar_is_not_the_calendar_source(self):
        """The defect this layer exists to fix."""
        from adapters.mailbox_registry import CALENDAR, MAIL, PRESENT
        registry = self._registry([{"id": "ops", "name": "Operations",
                                    "address": "Ops@l1truck.com"}])
        ops = registry.connections[0]
        ops.status = PRESENT
        ops.holdings = {MAIL: 127, CALENDAR: 0, "contacts": 0}
        self.assertEqual(registry.source_for(MAIL), ops)
        self.assertIsNone(registry.source_for(CALENDAR))

    def test_zero_is_empty_and_minus_one_is_unknown(self):
        """`0 or -1` once turned an empty calendar into an unknown one."""
        from adapters.mailbox_registry import MailboxConnection, CALENDAR
        empty = MailboxConnection("a", "A", "a@x.com")
        empty.holdings = {CALENDAR: 0}
        self.assertFalse(empty.holds(CALENDAR))

        unreadable = MailboxConnection("b", "B", "b@x.com")
        unreadable.holdings = {CALENDAR: -1}
        self.assertTrue(unreadable.holds(CALENDAR),
                        "an unreadable folder was treated as empty")

    def test_no_mailbox_holding_a_calendar_is_said_plainly(self):
        from adapters.mailbox_registry import CALENDAR, MAIL, PRESENT
        registry = self._registry([{"id": "ops", "name": "Operations",
                                    "address": "Ops@l1truck.com"}])
        ops = registry.connections[0]
        ops.status = PRESENT
        ops.holdings = {MAIL: 127, CALENDAR: 0}
        note = registry.fallback_note(CALENDAR)
        self.assertIn("no approved mailbox holds any calendar", note)
        self.assertIn("not reading an empty one", note)

    def test_a_configured_default_is_used_when_it_qualifies(self):
        from adapters.mailbox_registry import MAIL, PRESENT
        registry = self._registry(
            [{"id": "ops", "name": "Operations", "address": "Ops@l1truck.com"},
             {"id": "admin", "name": "Administration",
              "address": "Admin@l1truck.com"}],
            defaults={MAIL: "admin"})
        for c in registry.connections:
            c.status = PRESENT
            c.holdings = {MAIL: 5}
        self.assertEqual(registry.source_for(MAIL).connection_id, "admin")

    def test_falling_back_from_an_unavailable_default_says_so(self):
        from adapters.mailbox_registry import ABSENT, MAIL, PRESENT
        registry = self._registry(
            [{"id": "ops", "name": "Operations", "address": "Ops@l1truck.com"},
             {"id": "admin", "name": "Administration",
              "address": "Admin@l1truck.com"}],
            defaults={MAIL: "admin"})
        ops, admin = registry.connections
        ops.status, ops.holdings = PRESENT, {MAIL: 127}
        admin.status = ABSENT
        self.assertEqual(registry.source_for(MAIL).connection_id, "ops")
        note = registry.fallback_note(MAIL)
        self.assertIn("Administration", note)
        self.assertIn("Operations", note)

    # ---- failure isolation ----------------------------------------------

    def test_one_mailbox_failing_does_not_disable_the_other(self):
        from adapters.mailbox_registry import MAIL, PRESENT, UNKNOWN
        registry = self._registry(
            [{"id": "ops", "name": "Operations", "address": "Ops@l1truck.com"},
             {"id": "admin", "name": "Administration",
              "address": "Admin@l1truck.com"}])
        ops, admin = registry.connections
        ops.status, ops.holdings = PRESENT, {MAIL: 127}
        admin.status = UNKNOWN
        admin.failure_message = "timed out"
        self.assertEqual([c.connection_id for c in registry.usable_connections],
                         ["ops"])
        self.assertEqual(registry.source_for(MAIL).connection_id, "ops")

    def test_a_disabled_mailbox_is_never_used(self):
        from adapters.mailbox_registry import MAIL, PRESENT
        registry = self._registry([{"id": "ops", "name": "Operations",
                                    "address": "Ops@l1truck.com",
                                    "enabled": False}])
        registry.connections[0].status = PRESENT
        registry.connections[0].holdings = {MAIL: 127}
        self.assertIsNone(registry.source_for(MAIL))
        self.assertEqual(registry.connections[0].display, "OFF")

    # ---- zero / one / many ----------------------------------------------

    def test_zero_configured_accounts_is_handled(self):
        from adapters.mailbox_registry import MAIL
        registry = self._registry([])
        self.assertEqual(registry.connections, [])
        self.assertIsNone(registry.source_for(MAIL))
        self.assertIn("no approved mailbox", registry.fallback_note(MAIL))

    def test_lookup_works_by_id_friendly_name_and_address(self):
        registry = self._registry([{"id": "ops", "name": "Operations",
                                    "address": "Ops@l1truck.com"}])
        for wanted in ("ops", "Operations", "Ops@l1truck.com"):
            with self.subTest(wanted=wanted):
                self.assertIsNotNone(registry.get(wanted))

    # ---- operator display ------------------------------------------------

    def test_the_display_label_has_no_developer_terms(self):
        from adapters.mailbox_registry import (ABSENT, MailboxConnection,
                                               PRESENT, UNKNOWN)
        for status, expected in ((PRESENT, "LIVE"), (ABSENT, "NOT MOUNTED"),
                                 (UNKNOWN, "UNKNOWN")):
            with self.subTest(status=status):
                c = MailboxConnection("a", "A", "a@x.com")
                c.status = status
                self.assertEqual(c.display, expected)

    # ---- read-only --------------------------------------------------------

    def test_write_authority_is_none_and_there_is_no_send_path(self):
        from adapters.mailbox_registry import MailboxConnection, WRITE_AUTHORITY
        self.assertEqual(WRITE_AUTHORITY, "none")
        self.assertEqual(MailboxConnection("a", "A", "a@x.com").write_authority,
                         "none")
        source = (PLUGIN_ROOT / "adapters" / "mailbox_registry.py").read_text(
            encoding="utf-8")
        for forbidden in ("def send", "def delete", "def move", "def flag",
                          ".Send(", ".Delete(", ".Move("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_every_connection_carries_outlook_provenance(self):
        from adapters.mailbox_registry import MailboxConnection
        from contracts import SourceClass
        self.assertEqual(MailboxConnection("a", "A", "a@x.com").provenance_class,
                         SourceClass.LOCAL_OUTLOOK)

    # ---- the retired mailbox ---------------------------------------------

    def test_the_retired_mailbox_is_not_referenced_in_the_layer(self):
        source = (PLUGIN_ROOT / "adapters" / "mailbox_registry.py").read_text(
            encoding="utf-8")
        self.assertNotIn("System@l1truck", source)

    def test_the_shipped_configuration_names_no_retired_mailbox(self):
        import json
        config = json.loads(
            (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
                encoding="utf-8"))
        self.assertNotIn("system@", json.dumps(config).lower())

    def test_the_deployment_template_ships_with_no_mailboxes(self):
        import json
        template = json.loads(
            (PLUGIN_ROOT / "configuration" / "joe.config.template.json").read_text(
                encoding="utf-8"))
        self.assertEqual(template["outlook"]["accounts"], [])
        self.assertEqual(template["outlook"]["account"], "")


class TestVoiceStatusTruthfulness(unittest.TestCase):
    """Voice input and output are reported separately.

    Output is proven and audible. Input binds an engine and has never heard a
    person. A single "Voice LIVE" chip across both is the false status
    indicator the governing mission names: a green label is not proof."""

    def setUp(self):
        self.root = WORKSPACE / uuid.uuid4().hex[:8]
        self.root.mkdir(parents=True, exist_ok=True)
        self.service = AssistantService(make_config(self.root))

    def tearDown(self):
        try:
            self.service.shutdown()
        except Exception:
            pass
        shutil.rmtree(self.root, ignore_errors=True)

    def _status(self, name):
        return {s.name: s for s in self.service.status()}[name]

    def test_voice_input_and_output_are_separate_capabilities(self):
        names = {s.name for s in self.service.status()}
        self.assertIn("Voice out", names)
        self.assertIn("Voice in", names)
        self.assertNotIn("Voice", names, "the conflated chip is still present")

    def test_voice_input_never_claims_live(self):
        """Binding a recognizer is not hearing a person."""
        status = self._status("Voice in")
        self.assertFalse(status.live_connection)
        self.assertNotIn("LIVE", status.chip())

    def test_voice_input_names_what_is_blocking_it(self):
        status = self._status("Voice in")
        self.assertTrue(status.blocker, "no reason given for an unproven capability")

    def test_voice_output_may_claim_live_when_an_engine_is_bound(self):
        status = self._status("Voice out")
        self.assertEqual(status.live_connection, status.available)

    def test_the_detail_says_it_was_never_proven(self):
        status = self._status("Voice in")
        detail = (status.detail or "").lower()
        if status.available:
            self.assertIn("never proven", detail)


class TestContactOrdering(unittest.TestCase):
    """Outlook reported this folder as alphabetical over a field it leaves empty.

    These tests hold the ordering to what a person actually sees on screen."""

    def setUp(self):
        from adapters.outlook_com import OutlookComAdapter
        self.sort = OutlookComAdapter._sort_contacts

    def test_alphabetical_by_the_name_that_is_shown(self):
        items = [{"display_name": n} for n in ("Zeta Co", "adam Szabo", "Mid Freight")]
        ordered, ordering, note = self.sort(items, 10)
        self.assertEqual([i["display_name"] for i in ordered],
                         ["adam Szabo", "Mid Freight", "Zeta Co"])
        self.assertEqual(ordering, "display_name_asc")
        self.assertEqual(note, "")

    def test_unnamed_contacts_go_last_and_are_counted(self):
        items = [{"display_name": ""}, {"display_name": "Bravo"},
                 {"display_name": "   "}, {"display_name": "Alpha"}]
        ordered, _, note = self.sort(items, 10)
        self.assertEqual([i["display_name"] for i in ordered[:2]], ["Alpha", "Bravo"])
        self.assertIn("2 contact(s) have no name", note)

    def test_the_limit_truncates_but_only_after_sorting(self):
        """Sorting a slice of the folder would alphabetise an arbitrary subset."""
        items = [{"display_name": n} for n in ("Zeta", "Yankee", "Alpha", "Bravo")]
        ordered, _, _ = self.sort(items, 2)
        self.assertEqual([i["display_name"] for i in ordered], ["Alpha", "Bravo"])

    def test_ordering_value_has_an_honest_label(self):
        from adapters.outlook_com import ORDERING_LABEL
        self.assertEqual(ORDERING_LABEL["display_name_asc"],
                         "alphabetical by the name shown")

    def test_the_whole_folder_is_fetched_before_sorting(self):
        from adapters import outlook_com
        self.assertGreaterEqual(outlook_com._CONTACTS_FETCH_MAX, 1000)


class TestCopilotInService(PluginTestCase):
    def test_copilot_is_selected_but_not_signed_in_by_default(self):
        """The shipped configuration now SELECTS Copilot. That is not the same
        as being connected to it, and this test exists to keep the two apart.

        An earlier version of this test asserted the provider was not selected.
        That was true when the shipped provider was "none" and became false the
        moment Copilot was selected - so it failed for the right reason, and
        the assertion, not the program, was what needed correcting."""
        status = self.service.copilot_status()
        self.assertTrue(status["provider_selected"])
        self.assertFalse(status["signed_in"])
        self.assertFalse(status["live"])
        self.assertTrue(status["preview"])
        self.assertTrue(status["blocker"])

    def test_selected_but_unsigned_copilot_composes_nothing(self):
        """Selection must never be reported to Mike as a connection."""
        reasoning = {s.name: s for s in self.service.status()}["Reasoning"]
        self.assertFalse(reasoning.live_connection)
        self.assertIn("NOT", reasoning.chip())
        # and JOE still answers from what it genuinely has
        self.assertTrue(self.service.ask("help").response.ok)

    def test_selecting_copilot_builds_the_backend(self):
        base = json.loads(
            (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
                encoding="utf-8"
            )
        )
        base["paths"] = {
            "runtime_data": str(self.root / "rd2"),
            "logs": str(self.root / "logs2"),
        }
        base["outlook"]["enabled"] = False
        base["reasoning"]["provider"] = "m365_copilot"
        path = self.root / "copilot.json"
        path.write_text(json.dumps(base), encoding="utf-8")
        service = AssistantService(Config.load(path))
        try:
            status = service.copilot_status()
            self.assertTrue(status["provider_selected"])
            self.assertFalse(status["live"])   # nobody signed in
            self.assertTrue(status["preview"])
            # the app still works without a signed-in provider
            self.assertTrue(service.ask("help").response.ok)
        finally:
            service.shutdown()

    def test_dispatch_stays_not_connected_with_copilot_selected(self):
        self.assertFalse(self.service.dispatch.connected)
        status = {s.name: s for s in self.service.status()}["Dispatch"]
        self.assertFalse(status.live_connection)


if __name__ == "__main__":
    unittest.main(verbosity=2)