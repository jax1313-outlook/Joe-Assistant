"""The voice session: turn taking, queueing, and barge-in.

This is transport. The session moves utterances between the driver and whatever
is on the other side. It does not decide what to say, does not remember
anything between sessions, and does not understand a word of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engines import (
    SpeechToTextEngine,
    TextSpeechToText,
    TextTextToSpeech,
    TextToSpeechEngine,
)
from .utterance import (
    Direction,
    SpeechResult,
    Transcript,
    Utterance,
    UtteranceError,
)


class SessionError(RuntimeError):
    pass


class SessionState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    SPEAKING = "SPEAKING"
    CLOSED = "CLOSED"

    ALL = (IDLE, LISTENING, SPEAKING, CLOSED)


@dataclass
class SessionEvent:
    """One thing that happened, in order. The session's whole audit trail."""

    kind: str
    detail: str
    utterance_id: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "utterance_id": self.utterance_id,
        }


class VoiceSession:
    """One conversation's worth of voice transport.

    Barge-in is the behavior that matters here: a driver who starts talking
    while the Assistant is mid-sentence gets the Assistant to stop. In a moving
    truck, a system that talks over the driver is worse than one that says
    nothing.
    """

    def __init__(
        self,
        stt: SpeechToTextEngine | None = None,
        tts: TextToSpeechEngine | None = None,
        allow_barge_in: bool = True,
    ) -> None:
        self.stt = stt or TextSpeechToText()
        self.tts = tts or TextTextToSpeech()
        self.allow_barge_in = allow_barge_in
        self.state = SessionState.IDLE
        self.queue: list[Utterance] = []
        self.history: list[Utterance] = []
        self.transcripts: list[Transcript] = []
        self.results: list[SpeechResult] = []
        self.events: list[SessionEvent] = []
        self._record("session_opened", "voice transport session opened")

    # ---- bookkeeping --------------------------------------------------

    def _record(self, kind: str, detail: str, utterance_id: str = "") -> SessionEvent:
        event = SessionEvent(kind=kind, detail=detail, utterance_id=utterance_id)
        self.events.append(event)
        return event

    def _require_open(self) -> None:
        if self.state == SessionState.CLOSED:
            raise SessionError("the session is closed")

    # ---- listening ----------------------------------------------------

    def listen(self, audio_reference) -> Transcript:
        """Hand something to the speech-to-text engine and keep the transcript.

        If the Assistant is mid-sentence and barge-in is allowed, speaking is
        stopped first.
        """
        self._require_open()
        if self.state == SessionState.SPEAKING and self.allow_barge_in:
            self.barge_in()

        self.state = SessionState.LISTENING
        transcript = self.stt.transcribe(audio_reference)
        self.transcripts.append(transcript)

        if transcript.is_empty:
            self._record("heard_nothing", "transcript was empty", transcript.utterance_id)
            self.state = SessionState.IDLE
            return transcript

        if transcript.is_low_confidence:
            self._record(
                "low_confidence",
                "transcript confidence " + str(transcript.confidence)
                + "; carried through unchanged",
                transcript.utterance_id,
            )

        self.history.append(
            Utterance(
                utterance_id=transcript.utterance_id,
                direction=Direction.INBOUND,
                text=transcript.text,
            )
        )
        self._record("heard", transcript.text, transcript.utterance_id)
        self.state = SessionState.IDLE
        return transcript

    # ---- speaking -----------------------------------------------------

    def enqueue(self, text: str) -> Utterance:
        """Queue something to be spoken. Does not speak it."""
        self._require_open()
        utterance = Utterance.outbound(text)
        self.queue.append(utterance)
        self._record("queued", utterance.text, utterance.utterance_id)
        return utterance

    def say(self, text: str) -> SpeechResult:
        """Queue one utterance and speak it immediately."""
        self.enqueue(text)
        results = self.flush()
        return results[-1]

    def flush(self) -> list[SpeechResult]:
        """Speak everything queued, in order."""
        self._require_open()
        delivered: list[SpeechResult] = []
        while self.queue:
            utterance = self.queue.pop(0)
            self.state = SessionState.SPEAKING
            result = self.tts.speak(utterance)
            self.results.append(result)
            self.history.append(utterance)
            delivered.append(result)
            self._record(
                "spoken" if result.spoken else "not_spoken",
                result.reason or utterance.text,
                utterance.utterance_id,
            )
        self.state = SessionState.IDLE
        return delivered

    def barge_in(self) -> SessionEvent:
        """The driver started talking. Stop speaking and drop what was queued."""
        self._require_open()
        self.tts.stop()
        dropped = len(self.queue)
        for utterance in self.queue:
            self.results.append(
                SpeechResult(
                    utterance_id=utterance.utterance_id,
                    text=utterance.text,
                    engine=self.tts.name,
                    spoken=False,
                    interrupted=True,
                    reason="dropped by barge-in; the driver spoke",
                )
            )
        self.queue.clear()
        self.state = SessionState.IDLE
        return self._record(
            "barge_in",
            "driver interrupted; stopped speaking and dropped "
            + str(dropped)
            + " queued utterance(s)",
        )

    # ---- lifecycle ----------------------------------------------------

    def close(self) -> None:
        """End the session. Nothing is retained."""
        if self.state == SessionState.CLOSED:
            return
        self.tts.stop()
        self.queue.clear()
        self.state = SessionState.CLOSED
        self._record("session_closed", "voice transport session closed")

    # ---- reporting ----------------------------------------------------

    @property
    def is_speaking(self) -> bool:
        return self.state == SessionState.SPEAKING

    @property
    def queued_count(self) -> int:
        return len(self.queue)

    def spoken_texts(self) -> list[str]:
        return [r.text for r in self.results if r.spoken]

    def heard_texts(self) -> list[str]:
        return [u.text for u in self.history if u.direction == Direction.INBOUND]

    def status(self) -> dict:
        return {
            "state": self.state,
            "stt_engine": self.stt.name,
            "tts_engine": self.tts.name,
            "allow_barge_in": self.allow_barge_in,
            "queued": self.queued_count,
            "heard": len(self.heard_texts()),
            "spoken": len(self.spoken_texts()),
            "events": len(self.events),
            "real_audio_input": False,
            "real_audio_output": False,
            "interprets_speech": False,
            "remembers_between_sessions": False,
            "has_reasoning": False,
        }

    def transcript_log(self) -> list[dict]:
        return [event.to_dict() for event in self.events]
