"""Assistant Voice - Workstream 6.

Speech-to-text, text-to-speech, driver interaction layer. Voice transport only.

No reasoning. No memory. No Outlook. No library.

This package imports nothing outside itself and nothing outside folder 6.
No real speech engine is bound; see engines.py.
"""

__version__ = "1.0.0"

from .utterance import (
    LOW_CONFIDENCE_BELOW,
    Direction,
    SpeechResult,
    Transcript,
    Utterance,
    UtteranceError,
)
from .engines import (
    AVAILABLE_ENGINES,
    NOT_IMPLEMENTED_ENGINES,
    EngineError,
    SilentTextToSpeech,
    SpeechToTextEngine,
    TextSpeechToText,
    TextTextToSpeech,
    TextToSpeechEngine,
)
from .driver_mode import (
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
)
from .session import SessionError, SessionEvent, SessionState, VoiceSession

__all__ = [
    "__version__",
    "LOW_CONFIDENCE_BELOW", "Direction", "SpeechResult", "Transcript",
    "Utterance", "UtteranceError",
    "AVAILABLE_ENGINES", "NOT_IMPLEMENTED_ENGINES", "EngineError",
    "SilentTextToSpeech", "SpeechToTextEngine", "TextSpeechToText",
    "TextTextToSpeech", "TextToSpeechEngine",
    "MAX_SPOKEN_WORDS", "TOO_LONG_TO_READ_WORDS", "DriverBrief",
    "DriverModeError", "build_brief", "check_length", "defer_long_text",
    "is_too_long_to_read", "prepare_for_speech", "strip_unspeakable",
    "SessionError", "SessionEvent", "SessionState", "VoiceSession",
]
