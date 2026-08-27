"""What moves through the voice layer: utterances, transcripts, speech results.

Transport objects only. Nothing here understands what is being said.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone


class UtteranceError(ValueError):
    pass


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Direction:
    INBOUND = "INBOUND"    # driver speaking to the Assistant
    OUTBOUND = "OUTBOUND"  # Assistant speaking to the driver

    ALL = (INBOUND, OUTBOUND)


_counter = itertools.count(1)


def next_utterance_id() -> str:
    return "UTT-{0:04d}".format(next(_counter))


@dataclass
class Transcript:
    """What a speech-to-text engine returned.

    `confidence` is whatever the engine reported. This layer does not judge it,
    improve it, or correct it - it carries it so whoever consumes the transcript
    can see how much to trust it.
    """

    utterance_id: str
    text: str
    confidence: float = 0.0
    is_final: bool = True
    engine: str = "none"
    created_at: str = field(default_factory=_stamp)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < LOW_CONFIDENCE_BELOW

    def to_dict(self) -> dict:
        return {
            "utterance_id": self.utterance_id,
            "text": self.text,
            "confidence": self.confidence,
            "is_final": self.is_final,
            "is_low_confidence": self.is_low_confidence,
            "engine": self.engine,
            "created_at": self.created_at,
            "interpreted": False,
            "understood": False,
        }


LOW_CONFIDENCE_BELOW = 0.6


@dataclass
class Utterance:
    """One thing to be spoken, or one thing that was heard."""

    utterance_id: str
    direction: str
    text: str
    created_at: str = field(default_factory=_stamp)

    @classmethod
    def outbound(cls, text: str) -> "Utterance":
        return cls._make(Direction.OUTBOUND, text)

    @classmethod
    def inbound(cls, text: str) -> "Utterance":
        return cls._make(Direction.INBOUND, text)

    @classmethod
    def _make(cls, direction: str, text: str) -> "Utterance":
        cleaned = (text or "").strip()
        if not cleaned:
            raise UtteranceError("an utterance needs text")
        if direction not in Direction.ALL:
            raise UtteranceError("unknown direction: " + str(direction))
        return cls(
            utterance_id=next_utterance_id(), direction=direction, text=cleaned
        )

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> dict:
        return {
            "utterance_id": self.utterance_id,
            "direction": self.direction,
            "text": self.text,
            "word_count": self.word_count,
            "created_at": self.created_at,
        }


@dataclass
class SpeechResult:
    """What happened when an utterance was handed to a text-to-speech engine."""

    utterance_id: str
    text: str
    engine: str
    spoken: bool = False
    interrupted: bool = False
    reason: str = ""
    created_at: str = field(default_factory=_stamp)

    def to_dict(self) -> dict:
        return {
            "utterance_id": self.utterance_id,
            "text": self.text,
            "engine": self.engine,
            "spoken": self.spoken,
            "interrupted": self.interrupted,
            "reason": self.reason,
            "created_at": self.created_at,
            "audio_produced": False,
        }
