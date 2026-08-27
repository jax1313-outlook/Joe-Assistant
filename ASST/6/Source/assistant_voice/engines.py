"""Speech engine ports, and the text-only engines built here.

Two ports: one for speech to text, one for text to speech. Each defines the
smallest surface a transport layer needs.

**No real speech engine is bound in this workstream.** The engines below are
text-only stand-ins that move text through the same path real engines would
use. They do not record audio, do not play audio, and say so: every result
reports `audio_produced: False`.

Binding a real engine is a separate mission. It would need a microphone, an
audio device, and a decision about which vendor - none of which this build has
or makes.
"""

from __future__ import annotations

from .utterance import SpeechResult, Transcript, Utterance, next_utterance_id


class EngineError(RuntimeError):
    pass


# ---- ports --------------------------------------------------------------


class SpeechToTextEngine:
    """Port: audio in, text out.

    `transcribe` takes a reference to whatever the caller has - in this build,
    a string. A real engine would take audio. The port stays the same either
    way, which is the point of having it.
    """

    name = "abstract-stt"
    produces_audio = False
    consumes_audio = True

    def transcribe(self, audio_reference) -> Transcript:  # pragma: no cover
        raise NotImplementedError

    def status(self) -> dict:
        return {
            "engine": self.name,
            "kind": "speech-to-text",
            "real_audio_input": False,
            "note": "no real speech engine is bound in this workstream",
        }


class TextToSpeechEngine:
    """Port: text in, spoken output out."""

    name = "abstract-tts"
    produces_audio = True
    consumes_audio = False

    def speak(self, utterance: Utterance) -> SpeechResult:  # pragma: no cover
        raise NotImplementedError

    def stop(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def status(self) -> dict:
        return {
            "engine": self.name,
            "kind": "text-to-speech",
            "real_audio_output": False,
            "note": "no real speech engine is bound in this workstream",
        }


# ---- text-only engines --------------------------------------------------


class TextSpeechToText(SpeechToTextEngine):
    """Takes typed text where audio would go, and returns it as a transcript.

    Honest about what it is: `real_audio_input` is False and every transcript
    is tagged with this engine's name, so nothing downstream can mistake typed
    text for something that was actually heard.
    """

    name = "text-stt"

    def __init__(self, confidence: float = 1.0) -> None:
        if not 0.0 <= confidence <= 1.0:
            raise EngineError("confidence must be between 0.0 and 1.0")
        self.confidence = confidence
        self.transcribed: list[Transcript] = []

    def transcribe(self, audio_reference) -> Transcript:
        text = "" if audio_reference is None else str(audio_reference)
        transcript = Transcript(
            utterance_id=next_utterance_id(),
            text=text.strip(),
            confidence=self.confidence,
            is_final=True,
            engine=self.name,
        )
        self.transcribed.append(transcript)
        return transcript


class TextTextToSpeech(TextToSpeechEngine):
    """Collects what would have been spoken. Produces no audio.

    Every `SpeechResult` reports `audio_produced: False`. A driver reading a
    transcript of this engine is reading what the Assistant *would* have said,
    not a record of sound that reached the cab.
    """

    name = "text-tts"

    def __init__(self) -> None:
        self.spoken: list[SpeechResult] = []
        self.is_speaking = False
        self.stop_count = 0

    def speak(self, utterance: Utterance) -> SpeechResult:
        self.is_speaking = True
        result = SpeechResult(
            utterance_id=utterance.utterance_id,
            text=utterance.text,
            engine=self.name,
            spoken=True,
            interrupted=False,
            reason="delivered to the text engine; no audio was produced",
        )
        self.spoken.append(result)
        self.is_speaking = False
        return result

    def stop(self) -> None:
        self.stop_count += 1
        self.is_speaking = False


class SilentTextToSpeech(TextToSpeechEngine):
    """Accepts utterances and speaks none of them.

    Used when voice output is off. Reports `spoken: False` with a reason, so
    the caller can tell "nothing was said" apart from "something was said".
    """

    name = "silent-tts"

    def __init__(self) -> None:
        self.suppressed: list[SpeechResult] = []
        self.stop_count = 0

    def speak(self, utterance: Utterance) -> SpeechResult:
        result = SpeechResult(
            utterance_id=utterance.utterance_id,
            text=utterance.text,
            engine=self.name,
            spoken=False,
            interrupted=False,
            reason="voice output is off; nothing was spoken",
        )
        self.suppressed.append(result)
        return result

    def stop(self) -> None:
        self.stop_count += 1


AVAILABLE_ENGINES = {
    "text-stt": TextSpeechToText,
    "text-tts": TextTextToSpeech,
    "silent-tts": SilentTextToSpeech,
}

# Engines that would need hardware, a vendor, and a separate decision.
NOT_IMPLEMENTED_ENGINES = (
    "microphone capture",
    "audio playback",
    "Windows SAPI / System.Speech",
    "any cloud speech service",
    "wake-word detection",
    "speaker identification",
)
