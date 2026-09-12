"""Joe at 70 MPH: what he says, what he refuses, and what he never writes.

Three doctrines meet in this layer and each of them fails in a specific way if
it is only written down.

`DRIVER_FIRST_DOCTRINE_v2` **D2, the 70 MPH Test** -- the driver is moving,
tired, and has one hand. An answer that is a list, or that buries the fact in a
clause, or that renders a time as `2026-09-15T14:00:00-05:00`, has failed
whatever else is true about it.

**D9, Retrieval Is Not Modification** -- reading must not change anything. The
retrieval port has no write method to call by mistake.

`Dispatch/CLAUDE.md` **5.4** -- "No direct Dispatch write authority may be
granted to Assistant." Speech never becomes a database write. It becomes a
proposal with the words that would confirm it, and this repository has already
shipped the failure that rule exists to prevent: `driver_step_milestone` once
swallowed a refused transition, so a driver tapped Picked Up at a dock, nothing
was recorded, and the screen said it worked.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from conversation.capture import CONFIDENCE_FLOOR, HIGH_CONFIDENCE, propose_change
from conversation.mission_record import MissionRecordRetrieval
from conversation.orchestrator import ReasoningOrchestrator, classify
from conversation.readback import read_back_load
from conversation.session import (
    FAILED,
    INTERRUPTED,
    REFUSED,
    SPOKEN,
    ConversationSession,
)

NOW = datetime(2026, 9, 12, 18, 0, tzinfo=timezone.utc)

LOAD = {
    "load_id": "LD-1", "customer": "Acme Foods", "status": "in_transit",
    "pickup_location": "Columbus OH", "delivery_location": "Dallas TX",
    "pickup_datetime": "2026-09-12 08:00",
    "delivery_datetime": "2026-09-13T14:00:00-04:00",
    "driver_id": "DRV-1",
}


class Reader:
    def __init__(self, loads=None):
        self._loads = loads if loads is not None else {"LD-1": dict(LOAD)}

    def get_load(self, load_id): return self._loads.get(load_id)
    def list_milestones(self, load_id): return [{"event_type": "loaded"}]
    def list_exceptions(self, load_id): return []
    def get_driver(self, driver_id): return {"name": "Ray"}


@pytest.fixture(autouse=True)
def _eastern(monkeypatch):
    monkeypatch.setenv("DISPATCH_OPERATING_TIMEZONE", "America/New_York")


class TestTheReadBackIsOneSentence:
    @pytest.mark.parametrize(
        "aspect,expected",
        [
            ("next", "Next is delivery tomorrow at 14:00 in Dallas TX."),
            ("delivery", "Delivery is tomorrow at 14:00 in Dallas TX."),
            ("pickup", "Pickup is today at 08:00 in Columbus OH."),
            ("where", "You're going to Dallas TX."),
            ("customer", "The customer is Acme Foods."),
            ("status", "The load is in transit."),
        ],
    )
    def test_it_answers_in_one_sentence(self, aspect, expected):
        assert read_back_load(LOAD, aspect=aspect, now=NOW).text == expected

    def test_a_time_is_never_an_iso_string(self):
        for aspect in ("next", "delivery", "pickup", "everything"):
            text = read_back_load(LOAD, aspect=aspect, now=NOW).text
            assert "T14:00" not in text and "-04:00" not in text and "Z" not in text.split()

    def test_a_bare_hour_is_never_spoken_without_a_day(self):
        """"14:00" sounds precise and does not say which day. A driver who hears
        it and assumes today loses the load."""
        text = read_back_load(LOAD, aspect="delivery", now=NOW).text
        assert any(word in text for word in ("today", "tomorrow", "yesterday")) or \
            any(day in text for day in ("Monday", "Tuesday", "Wednesday", "Thursday",
                                        "Friday", "Saturday", "Sunday"))

    def test_the_most_important_fact_comes_first(self):
        """A sentence heard at speed is often only half heard."""
        text = read_back_load(LOAD, aspect="next", now=NOW).text
        assert text.startswith("Next is delivery")

    def test_everything_states_the_count_before_it_starts(self):
        text = read_back_load(LOAD, aspect="everything", now=NOW).text
        assert text.startswith("4 things.")

    def test_a_missing_fact_is_said_not_skipped(self):
        """Silence about the delivery time is indistinguishable from there being
        no appointment."""
        partial = {"load_id": "LD-2", "delivery_location": "Dallas TX"}
        answer = read_back_load(partial, aspect="delivery", now=NOW)
        assert answer.text == "The delivery time is not on file."
        assert "delivery time" in answer.unknown

    def test_an_unreadable_time_is_spoken_as_written_not_dropped(self):
        load = dict(LOAD, delivery_datetime="whenever they call")
        answer = read_back_load(load, aspect="delivery", now=NOW)
        assert "whenever they call" in answer.text

    def test_an_empty_load_says_so(self):
        assert read_back_load({"load_id": "X"}, now=NOW).text == (
            "Nothing about the next stop is on file for this load."
        )


class TestRetrievalDoesNotModify:
    def test_the_port_has_no_write_method(self):
        retrieval = MissionRecordRetrieval(Reader())
        public = [n for n in dir(retrieval) if not n.startswith("_")]
        assert not any(
            n.startswith(("set_", "update_", "create_", "delete_", "save", "write"))
            for n in public
        ), f"a write path exists on the retrieval port: {public}"

    def test_it_names_what_is_not_known(self):
        reader = Reader({"LD-3": {"load_id": "LD-3", "customer": "Acme"}})
        record = MissionRecordRetrieval(reader).retrieve("LD-3")
        assert "delivery datetime" in record.unknown
        assert "pickup location" in record.unknown

    def test_the_reasoning_context_is_narrow(self):
        """A provider handed the whole record answers from anything in it, and
        one of the fields is a driver's phone number."""
        reader = Reader({"LD-1": dict(LOAD, driver_phone="555-0100", notes="internal")})
        context = MissionRecordRetrieval(reader).retrieve("LD-1").context_for_reasoning()
        assert "555-0100" not in context
        assert "internal" not in context
        assert "Dallas TX" in context

    def test_the_context_states_the_gaps(self):
        reader = Reader({"LD-4": {"load_id": "LD-4", "customer": "Acme", "status": "created"}})
        context = MissionRecordRetrieval(reader).retrieve("LD-4").context_for_reasoning()
        assert "NOT ON FILE" in context

    def test_with_no_reader_it_retrieves_nothing_rather_than_guessing(self):
        retrieval = MissionRecordRetrieval(None)
        assert retrieval.status() == "UNCONFIGURED"
        assert retrieval.retrieve("LD-1") is None


class FakeAnswer:
    def __init__(self, text="a considered answer", status="LIVE"):
        self.text, self.status, self.provenance = text, status, "reasoning provider"


class SlowReasoner:
    def __init__(self, answer=None):
        self.calls = 0
        self._answer = answer or FakeAnswer()

    def answer(self, question, context=""):
        self.calls += 1
        return self._answer


class TestBoundedReasoning:
    def _orchestrator(self, reasoner=None, reader=None, clock=None):
        return ReasoningOrchestrator(
            retrieval=MissionRecordRetrieval(reader or Reader()),
            reasoner=reasoner, clock=clock or (lambda: 0.0),
        )

    @pytest.mark.parametrize("question,aspect", [
        ("where am I going", "where"),
        ("when's delivery", "delivery"),
        ("what time is pickup", "pickup"),
        ("who's the customer", "customer"),
        ("what's next", "next"),
        ("read me the whole load", "everything"),
    ])
    def test_a_question_about_a_fact_never_reaches_a_provider(self, question, aspect):
        reasoner = SlowReasoner()
        result = self._orchestrator(reasoner).take_turn(question, load_id="LD-1")
        assert result.source == "record"
        assert result.provider_called is False
        assert reasoner.calls == 0, (
            "calling a model to read back a stored fact is slower, costs money, and "
            "can be wrong about something the database knows exactly"
        )

    def test_an_open_question_goes_to_the_provider_once(self):
        reasoner = SlowReasoner()
        result = self._orchestrator(reasoner).take_turn(
            "is this broker worth working with", load_id="LD-1")
        assert result.provider_called is True
        assert reasoner.calls == 1, "one call per driver utterance, no chains"

    def test_with_no_provider_he_says_what_he_can_still_do(self):
        result = self._orchestrator(None).take_turn("what do you reckon", load_id="LD-1")
        assert result.status == "UNCONFIGURED"
        assert "what's on the load" in result.spoken

    def test_a_provider_that_throws_does_not_end_the_drive(self):
        class Broken:
            def answer(self, question, context=""):
                raise RuntimeError("no network")

        result = self._orchestrator(Broken()).take_turn("anything", load_id="LD-1")
        assert result.status == "UNAVAILABLE"
        assert "couldn't work that out" in result.spoken

    def test_an_answer_that_arrives_too_late_is_not_spoken_as_if_it_were_timely(self):
        ticks = iter([0.0, 0.0, 99.0, 99.0])
        orchestrator = self._orchestrator(SlowReasoner(), clock=lambda: next(ticks))
        result = orchestrator.take_turn("something open ended", load_id="LD-1")
        assert result.source == "timeout"
        assert "took too long" in result.spoken

    def test_a_fact_question_with_no_load_refuses_rather_than_inventing(self):
        result = self._orchestrator(SlowReasoner()).take_turn("where am I going")
        assert result.status == "ABSENT"
        assert "don't have a load" in result.spoken

    def test_silence_is_answered_honestly(self):
        assert "didn't catch" in self._orchestrator(None).take_turn("  ").spoken

    def test_classification_does_not_over_reach(self):
        assert classify("should I take this load") == ""
        assert classify("what do you think of the rate") == ""


class TestCapture:
    @pytest.mark.parametrize("heard,event", [
        ("we're loaded", "loaded"),
        ("picked up", "loaded"),
        ("delivered", "delivered"),
        ("at the receiver", "arrived_delivery"),
        ("rolling", "in_transit"),
    ])
    def test_it_recognises_what_a_driver_actually_says(self, heard, event):
        proposal = propose_change(heard, "LD-1", confidence=0.9)
        assert proposal.fields["event_type"] == event
        assert proposal.kind == "milestone"

    def test_trouble_is_an_exception_not_a_state_change(self):
        proposal = propose_change("been sitting here two hours", "LD-1", confidence=0.9)
        assert proposal.kind == "exception"
        assert proposal.fields["exception_type"] == "detention"
        # The driver's own words, unedited: a paraphrase loses the detail that
        # made it worth reporting.
        assert proposal.fields["description"] == "been sitting here two hours"

    def test_below_the_floor_joe_says_nothing(self):
        assert propose_change("we're loaded", "LD-1", confidence=CONFIDENCE_FLOOR - 0.01) is None

    def test_a_low_confidence_proposal_repeats_it_back(self):
        proposal = propose_change("delivered", "LD-1", confidence=HIGH_CONFIDENCE - 0.1)
        assert 'I heard "delivered"' in proposal.confirmation_prompt

    def test_a_high_confidence_proposal_is_a_single_question(self):
        proposal = propose_change("delivered", "LD-1", confidence=0.95)
        assert proposal.confirmation_prompt.startswith("Record delivered?")

    def test_a_proposal_is_never_applied(self):
        assert propose_change("delivered", "LD-1", 0.95).to_dict()["applied"] is False

    @pytest.mark.parametrize("heard", [
        "nice weather out here",
        "the coffee at this stop is terrible",
        "traffic's moving fine",
    ])
    def test_conversation_is_not_a_report(self, heard):
        """A bare mention of weather is not a weather exception. Opening one is
        worse than missing it: the driver then has to listen to a confirmation
        question and refuse it, at speed, because he made conversation."""
        assert propose_change(heard, "LD-1", 0.99) is None

    @pytest.mark.parametrize("heard,kind", [
        ("I-70's shut down with snow", "weather"),
        ("stuck in ice on the grade", "weather"),
        ("been waiting two hours", "detention"),
        ("running late into Dallas", "delay"),
        ("blew a tire", "mechanical"),
    ])
    def test_an_actual_problem_is_reported(self, heard, kind):
        proposal = propose_change(heard, "LD-1", 0.9)
        assert proposal is not None and proposal.fields["exception_type"] == kind


class TestTheConversation:
    def _session(self, reasoner=None, reader=None):
        return ConversationSession(
            orchestrator=ReasoningOrchestrator(
                retrieval=MissionRecordRetrieval(reader or Reader()),
                reasoner=reasoner, clock=lambda: 0.0,
            ),
            load_id="LD-1", driver_id="DRV-1",
        )

    def test_a_turn_is_recorded_before_it_matters(self):
        session = self._session()
        session.ask("where am I going")
        assert session.turns[0].outcome == SPOKEN
        assert session.turns[0].spoken == "You're going to Dallas TX."

    def test_an_interruption_is_not_recorded_as_delivered(self):
        """A record saying Joe told the driver something he did not hear is
        worse than no record."""
        session = self._session()
        session.interrupt()
        turn = session.ask("read me the whole load")
        assert turn.outcome == INTERRUPTED
        assert turn.spoken.startswith("(interrupted)")

    def test_an_interruption_applies_to_one_turn_only(self):
        session = self._session()
        session.interrupt()
        session.ask("where am I going")
        assert session.ask("where am I going").outcome == SPOKEN

    def test_an_orchestrator_that_crashes_is_recorded_as_failed(self):
        class Exploding:
            def take_turn(self, *a, **k):
                raise RuntimeError("boom")

        session = ConversationSession(orchestrator=Exploding(), load_id="LD-1")
        turn = session.ask("anything")
        assert turn.outcome == FAILED
        assert "boom" in turn.detail

    def test_a_proposal_advances_only_on_an_unambiguous_yes(self):
        session = self._session()
        session.propose("we're loaded", confidence=0.95)
        assert session.confirm("uh") is None
        assert session.turns[-1].outcome == REFUSED
        applied = session.confirm("yes")
        assert applied["fields"]["event_type"] == "loaded"

    def test_a_no_drops_it(self):
        session = self._session()
        session.propose("delivered", confidence=0.95)
        assert session.confirm("no") is None
        assert session.turns[-1].detail == "declined"

    def test_confirming_nothing_is_refused(self):
        assert self._session().confirm("yes") is None

    def test_a_confirmed_proposal_is_not_confirmable_twice(self):
        session = self._session()
        session.propose("delivered", confidence=0.95)
        assert session.confirm("yes") is not None
        assert session.confirm("yes") is None

    def test_a_closed_session_answers_nothing(self):
        session = self._session()
        session.close()
        assert session.ask("where am I going").outcome == REFUSED

    def test_the_audit_records_what_happened_not_a_model_of_the_driver(self):
        session = self._session()
        session.ask("where am I going")
        session.propose("delivered", confidence=0.95)
        session.confirm("yes")
        audit = session.audit()
        assert audit["turn_count"] == 3
        assert len(audit["proposals"]) == 1
        assert set(audit) == {
            "session_id", "load_id", "driver_id", "state", "started_at", "ended_at",
            "turn_count", "interrupted_turns", "proposals", "turns",
        }

    def test_nothing_is_carried_between_sessions(self):
        """Dispatch is the system of record. A second memory is a second truth."""
        first = self._session()
        first.ask("where am I going")
        first.close()
        second = self._session()
        assert second.turns == []
        assert second.session_id != first.session_id


class TestVoiceProviders:
    def test_there_is_always_a_working_pair(self, monkeypatch):
        import sys

        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
        from voice.providers import build_engines, selected

        for var in ("JOE_AZURE_SPEECH_KEY", "JOE_AZURE_SPEECH_REGION", "JOE_WHISPER_MODEL"):
            monkeypatch.delenv(var, raising=False)
        stt, tts, report = build_engines()
        assert stt is not None and tts is not None
        assert selected("speech_to_text").status == "SIMULATED"

    def test_a_key_makes_a_provider_configured_never_live(self, monkeypatch):
        from voice.providers import azure_status

        monkeypatch.setenv("JOE_AZURE_SPEECH_KEY", "x" * 32)
        monkeypatch.setenv("JOE_AZURE_SPEECH_REGION", "eastus")
        status = azure_status("text_to_speech")
        assert status.status in ("CONFIGURED", "UNAVAILABLE")
        assert status.status != "LIVE", (
            "a key that parses is not a round trip that happened"
        )

    def test_missing_settings_are_named(self, monkeypatch):
        from voice.providers import azure_status

        monkeypatch.delenv("JOE_AZURE_SPEECH_KEY", raising=False)
        monkeypatch.setenv("JOE_AZURE_SPEECH_REGION", "eastus")
        status = azure_status("text_to_speech")
        assert status.status == "UNCONFIGURED"
        assert "JOE_AZURE_SPEECH_KEY" in status.detail

    def test_every_reported_status_is_one_of_the_eight(self):
        from voice.providers import TRUTH_WORDS, survey

        for rows in survey().values():
            assert all(row.status in TRUTH_WORDS for row in rows)

    def test_exactly_one_provider_is_selected_per_role(self):
        from voice.providers import survey

        for rows in survey().values():
            assert sum(1 for row in rows if row.selected) == 1
