"""Tests for Workstream 6 - Assistant Voice.

Runs with no microphone, no speaker, and no audio device. Nothing is written
to disk.

Run:  py -m unittest discover -s Tests -v      (from folder 6)
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_voice.driver_mode import (  # noqa: E402
    MAX_SPOKEN_WORDS,
    TOO_LONG_TO_READ_WORDS,
    DriverBrief,
    DriverModeError,
    build_brief,
    check_length,
    defer_long_text,
    is_too_long_to_read,
    prepare_for_speech,
    strip_unspeakable,
    word_count,
)
from assistant_voice.engines import (  # noqa: E402
    NOT_IMPLEMENTED_ENGINES,
    EngineError,
    SilentTextToSpeech,
    SpeechToTextEngine,
    TextSpeechToText,
    TextTextToSpeech,
    TextToSpeechEngine,
)
from assistant_voice.session import (  # noqa: E402
    SessionError,
    SessionState,
    VoiceSession,
)
from assistant_voice.utterance import (  # noqa: E402
    LOW_CONFIDENCE_BELOW,
    Direction,
    Utterance,
    UtteranceError,
)

LONG_TEXT = "The northbound lane cleared the recorded floor in eleven weeks. " * 8


class TestUtterance(unittest.TestCase):
    def test_outbound_and_inbound(self):
        self.assertEqual(Utterance.outbound("hello").direction, Direction.OUTBOUND)
        self.assertEqual(Utterance.inbound("hello").direction, Direction.INBOUND)

    def test_blank_text_is_refused(self):
        for text in ["", "   ", "\n\t"]:
            with self.subTest(text=repr(text)):
                with self.assertRaises(UtteranceError):
                    Utterance.outbound(text)

    def test_unknown_direction_is_refused(self):
        with self.assertRaises(UtteranceError):
            Utterance._make("SIDEWAYS", "hello")

    def test_text_is_stripped(self):
        self.assertEqual(Utterance.outbound("  spaced  ").text, "spaced")

    def test_ids_are_unique(self):
        ids = {Utterance.outbound("x" + str(n)).utterance_id for n in range(20)}
        self.assertEqual(len(ids), 20)

    def test_word_count(self):
        self.assertEqual(Utterance.outbound("one two three").word_count, 3)


class TestEngines(unittest.TestCase):
    def test_text_stt_returns_what_it_was_given(self):
        transcript = TextSpeechToText().transcribe("pickup moved to noon")
        self.assertEqual(transcript.text, "pickup moved to noon")
        self.assertTrue(transcript.is_final)

    def test_text_stt_tags_the_engine(self):
        self.assertEqual(TextSpeechToText().transcribe("x").engine, "text-stt")

    def test_empty_input_yields_an_empty_transcript(self):
        for value in ["", "   ", None]:
            with self.subTest(value=repr(value)):
                self.assertTrue(TextSpeechToText().transcribe(value).is_empty)

    def test_confidence_is_carried_not_judged(self):
        transcript = TextSpeechToText(confidence=0.42).transcribe("mumbled")
        self.assertEqual(transcript.confidence, 0.42)
        self.assertTrue(transcript.is_low_confidence)

    def test_high_confidence_is_not_flagged(self):
        self.assertFalse(TextSpeechToText(confidence=0.95).transcribe("clear").is_low_confidence)

    def test_confidence_threshold_is_visible(self):
        self.assertTrue(0.0 < LOW_CONFIDENCE_BELOW < 1.0)

    def test_out_of_range_confidence_is_refused(self):
        for value in [-0.1, 1.5]:
            with self.subTest(value=value):
                with self.assertRaises(EngineError):
                    TextSpeechToText(confidence=value)

    def test_text_tts_records_what_would_be_said(self):
        engine = TextTextToSpeech()
        result = engine.speak(Utterance.outbound("two stops tomorrow"))
        self.assertTrue(result.spoken)
        self.assertEqual(engine.spoken[0].text, "two stops tomorrow")

    def test_text_tts_never_claims_audio(self):
        result = TextTextToSpeech().speak(Utterance.outbound("anything"))
        self.assertFalse(result.to_dict()["audio_produced"])
        self.assertIn("no audio was produced", result.reason)

    def test_silent_engine_speaks_nothing_and_says_so(self):
        result = SilentTextToSpeech().speak(Utterance.outbound("anything"))
        self.assertFalse(result.spoken)
        self.assertIn("nothing was spoken", result.reason)

    def test_stop_is_counted(self):
        engine = TextTextToSpeech()
        engine.stop()
        engine.stop()
        self.assertEqual(engine.stop_count, 2)

    def test_ports_declare_no_real_audio(self):
        self.assertFalse(SpeechToTextEngine().status()["real_audio_input"])
        self.assertFalse(TextToSpeechEngine().status()["real_audio_output"])

    def test_the_not_implemented_list_is_explicit(self):
        self.assertIn("microphone capture", NOT_IMPLEMENTED_ENGINES)
        self.assertIn("audio playback", NOT_IMPLEMENTED_ENGINES)


class TestDriverMode(unittest.TestCase):
    def test_builds_the_three_part_brief(self):
        brief = build_brief(
            what_changed="Pickup moved to noon",
            why_it_matters="It overlaps the Richmond delivery",
            decision_required="Pick one before you roll",
        )
        spoken = brief.spoken_text()
        self.assertIn("Pickup moved to noon", spoken)
        self.assertIn("overlaps", spoken)
        self.assertIn("Pick one", spoken)

    def test_missing_decision_says_none_is_needed(self):
        brief = build_brief(what_changed="Pickup moved to noon")
        self.assertIn("No decision needed right now", brief.spoken_text())

    def test_written_location_is_stated_when_supplied(self):
        brief = build_brief(what_changed="Something changed", written_result_location="the Sandbox")
        self.assertIn("Full written result is in the Sandbox", brief.spoken_text())

    def test_an_empty_change_is_refused(self):
        for text in ["", "   ", "https://example.invalid/only-a-url"]:
            with self.subTest(text=text):
                with self.assertRaises(DriverModeError):
                    build_brief(what_changed=text)

    def test_urls_are_never_spoken(self):
        cleaned = strip_unspeakable("See https://example.invalid/rate-index for detail")
        self.assertNotIn("http", cleaned)
        self.assertIn("See", cleaned)

    def test_bracketed_citations_are_removed(self):
        cleaned = strip_unspeakable("Rates cleared the floor [Rate Floor Policy, p. 3]")
        self.assertNotIn("[", cleaned)
        self.assertIn("Rates cleared the floor", cleaned)

    def test_footnote_markers_are_removed(self):
        self.assertNotIn("[1]", strip_unspeakable("Confirmed by the facility [1]"))

    def test_markdown_marks_are_removed(self):
        self.assertNotIn("*", strip_unspeakable("**Confirmed** by the facility"))

    def test_removal_is_reported(self):
        brief = build_brief(what_changed="Confirmed, see https://example.invalid/x")
        self.assertTrue(brief.removed_unspeakable)

    def test_no_removal_is_reported_as_none(self):
        self.assertFalse(build_brief(what_changed="Confirmed by the facility").removed_unspeakable)

    def test_short_text_is_spoken(self):
        brief = prepare_for_speech("Two stops tomorrow, both live unload.")
        self.assertFalse(brief.deferred)
        self.assertIn("Two stops tomorrow", brief.spoken_text())

    def test_long_text_is_deferred_not_summarized(self):
        brief = prepare_for_speech(LONG_TEXT, "the Sandbox")
        self.assertTrue(brief.deferred)
        self.assertIn("written result ready", brief.spoken_text())
        self.assertFalse(brief.to_dict()["summarized"])

    def test_a_deferred_turn_is_itself_short_enough(self):
        brief = prepare_for_speech(LONG_TEXT, "the Sandbox")
        fits, _ = check_length(brief)
        self.assertTrue(fits)

    def test_prepare_never_returns_an_over_length_turn(self):
        # The bug this closes: an earlier draft tested the RAW text against a
        # higher threshold, so text between the two limits passed the defer
        # check and then exceeded the spoken limit once assembled.
        for words in (10, 40, 55, 58, 60, 65, 90, 200):
            text = " ".join("word" + str(n) for n in range(words))
            with self.subTest(words=words):
                brief = prepare_for_speech(text, "the Sandbox")
                fits, note = check_length(brief)
                self.assertTrue(fits, note)

    def test_the_defer_threshold_equals_the_spoken_limit(self):
        self.assertEqual(TOO_LONG_TO_READ_WORDS, MAX_SPOKEN_WORDS)

    def test_deferred_text_says_where_the_written_copy_is(self):
        self.assertIn("the Sandbox", prepare_for_speech(LONG_TEXT, "the Sandbox").spoken_text())

    def test_defer_reports_the_reason(self):
        self.assertIn("not read aloud", prepare_for_speech(LONG_TEXT).defer_reason)

    def test_defer_long_text_directly(self):
        brief = defer_long_text(LONG_TEXT, "the Sandbox")
        self.assertTrue(brief.deferred)
        self.assertIn("too long to read at speed", brief.spoken_text())

    def test_nothing_speakable_is_refused(self):
        with self.assertRaises(DriverModeError):
            prepare_for_speech("https://example.invalid/x [1]")

    def test_check_length_rejects_an_over_long_brief(self):
        brief = DriverBrief(what_changed=" ".join(["word"] * 200))
        fits, note = check_length(brief)
        self.assertFalse(fits)
        self.assertIn("over the", note)

    def test_is_too_long_to_read(self):
        self.assertFalse(is_too_long_to_read("short enough"))
        self.assertTrue(is_too_long_to_read(" ".join(["word"] * 200)))

    def test_word_count(self):
        self.assertEqual(word_count("one two three"), 3)
        self.assertEqual(word_count(""), 0)

    def test_a_brief_never_claims_to_have_summarized_or_interpreted(self):
        data = build_brief(what_changed="Something changed").to_dict()
        self.assertFalse(data["summarized"])
        self.assertFalse(data["interpreted"])


class TestSession(unittest.TestCase):
    def setUp(self):
        self.session = VoiceSession()

    def test_opens_idle(self):
        self.assertEqual(self.session.state, SessionState.IDLE)

    def test_opening_is_recorded(self):
        self.assertEqual(self.session.events[0].kind, "session_opened")

    def test_enqueue_does_not_speak(self):
        self.session.enqueue("first")
        self.assertEqual(self.session.queued_count, 1)
        self.assertEqual(self.session.spoken_texts(), [])

    def test_flush_speaks_in_order(self):
        self.session.enqueue("first")
        self.session.enqueue("second")
        self.session.flush()
        self.assertEqual(self.session.spoken_texts(), ["first", "second"])

    def test_say_queues_and_speaks(self):
        result = self.session.say("just this")
        self.assertTrue(result.spoken)
        self.assertEqual(self.session.queued_count, 0)

    def test_returns_to_idle_after_speaking(self):
        self.session.say("something")
        self.assertEqual(self.session.state, SessionState.IDLE)

    def test_listen_records_what_was_heard(self):
        self.session.listen("what changed")
        self.assertEqual(self.session.heard_texts(), ["what changed"])

    def test_empty_input_is_recorded_as_heard_nothing(self):
        self.session.listen("")
        self.assertIn("heard_nothing", [e.kind for e in self.session.events])
        self.assertEqual(self.session.heard_texts(), [])

    def test_low_confidence_is_recorded_not_corrected(self):
        session = VoiceSession(stt=TextSpeechToText(confidence=0.3))
        transcript = session.listen("mumbled something")
        self.assertIn("low_confidence", [e.kind for e in session.events])
        self.assertEqual(transcript.text, "mumbled something")

    def test_barge_in_drops_the_queue(self):
        self.session.enqueue("one")
        self.session.enqueue("two")
        self.session.barge_in()
        self.assertEqual(self.session.queued_count, 0)
        self.assertEqual(self.session.spoken_texts(), [])

    def test_barge_in_marks_dropped_utterances_interrupted(self):
        self.session.enqueue("one")
        self.session.barge_in()
        self.assertTrue(self.session.results[0].interrupted)
        self.assertIn("the driver spoke", self.session.results[0].reason)

    def test_barge_in_stops_the_engine(self):
        self.session.enqueue("one")
        self.session.barge_in()
        self.assertEqual(self.session.tts.stop_count, 1)

    def test_listening_while_speaking_triggers_barge_in(self):
        self.session.enqueue("a long answer")
        self.session.state = SessionState.SPEAKING
        self.session.listen("actually, stop")
        self.assertIn("barge_in", [e.kind for e in self.session.events])
        self.assertEqual(self.session.queued_count, 0)

    def test_barge_in_can_be_disabled(self):
        session = VoiceSession(allow_barge_in=False)
        session.enqueue("keep talking")
        session.state = SessionState.SPEAKING
        session.listen("stop")
        self.assertNotIn("barge_in", [e.kind for e in session.events])

    def test_silent_engine_reports_nothing_spoken(self):
        session = VoiceSession(tts=SilentTextToSpeech())
        result = session.say("anything")
        self.assertFalse(result.spoken)
        self.assertEqual(session.spoken_texts(), [])

    def test_closing_clears_the_queue(self):
        self.session.enqueue("pending")
        self.session.close()
        self.assertEqual(self.session.state, SessionState.CLOSED)
        self.assertEqual(self.session.queued_count, 0)

    def test_no_operation_after_closing(self):
        self.session.close()
        for action in (
            lambda: self.session.enqueue("x"),
            lambda: self.session.say("x"),
            lambda: self.session.listen("x"),
            lambda: self.session.barge_in(),
        ):
            with self.subTest(action=action):
                with self.assertRaises(SessionError):
                    action()

    def test_closing_twice_is_harmless(self):
        self.session.close()
        self.session.close()
        self.assertEqual(self.session.state, SessionState.CLOSED)

    def test_every_event_is_recorded_in_order(self):
        self.session.enqueue("one")
        self.session.flush()
        self.session.listen("reply")
        kinds = [e.kind for e in self.session.events]
        self.assertEqual(kinds[:4], ["session_opened", "queued", "spoken", "heard"])

    def test_status_declares_no_audio_no_reasoning_no_memory(self):
        status = self.session.status()
        for key in (
            "real_audio_input", "real_audio_output", "interprets_speech",
            "remembers_between_sessions", "has_reasoning",
        ):
            with self.subTest(key=key):
                self.assertFalse(status[key])

    def test_transcript_log_serializes(self):
        self.session.say("something")
        for entry in self.session.transcript_log():
            with self.subTest(entry=entry):
                self.assertIn("kind", entry)


class TestBoundaries(unittest.TestCase):
    PACKAGE = FOLDER / "Source" / "assistant_voice"

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
            "assistant_outlook", "assistant_research", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_audio_network_or_vendor_module(self):
        forbidden = {
            "wave", "audioop", "sounddevice", "pyaudio", "speech_recognition",
            "pyttsx3", "win32com", "comtypes", "socket", "urllib", "http",
            "requests", "ssl", "smtplib", "imaplib", "msal", "office365",
            "openai", "anthropic", "boto3", "azure", "subprocess", "webbrowser",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "argparse", "dataclasses", "datetime", "itertools",
            "json", "re", "sys",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_no_reasoning_memory_or_retrieval_method_exists(self):
        session = VoiceSession()
        for name in (
            "answer", "understand", "interpret", "reason", "think", "decide",
            "remember", "recall", "store", "save", "search", "retrieve",
            "summarize", "translate",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(session, name))

    def test_no_write_call_exists_anywhere_in_the_package(self):
        writers = re.compile(
            r"write_text|write_bytes|\.write\(|\bmkdir\b|\bunlink\b|\brmdir\b"
            r"|\.rename\(|os\.replace|shutil\.|os\.remove|os\.makedirs"
            r"|open\s*\([^)]*['\"][wax]"
        )
        for source in self._sources():
            with self.subTest(source=source.name):
                self.assertIsNone(writers.search(source.read_text(encoding="utf-8")))

    def test_nothing_persists_between_sessions(self):
        first = VoiceSession()
        first.say("remember this")
        first.close()
        second = VoiceSession()
        self.assertEqual(second.spoken_texts(), [])
        self.assertEqual(second.heard_texts(), [])

    def test_transcripts_never_claim_understanding(self):
        transcript = TextSpeechToText().transcribe("anything at all")
        data = transcript.to_dict()
        self.assertFalse(data["interpreted"])
        self.assertFalse(data["understood"])

    def test_no_speech_result_ever_claims_audio(self):
        for engine in (TextTextToSpeech(), SilentTextToSpeech()):
            result = engine.speak(Utterance.outbound("anything"))
            with self.subTest(engine=engine.name):
                self.assertFalse(result.to_dict()["audio_produced"])

    def test_the_package_never_answers_a_question(self):
        # Voice transport carries text. It must not contain a reply table or
        # canned answers, which would be reasoning smuggled into transport.
        joined = " ".join(s.read_text(encoding="utf-8") for s in self._sources())
        for word in ("ANSWERS", "RESPONSES = {", "def answer", "def reply"):
            with self.subTest(word=word):
                self.assertNotIn(word, joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
