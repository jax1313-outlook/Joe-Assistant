"""Continuous Driver Voice Mode - the conversation loop, without the UI.

The workflow this replaces was a voice keyboard: press microphone, speak, press
stop, review the transcription, press upload, wait, press play. That is six
deliberate hand movements to ask one question, and it is unusable at 65 mph.

What this does instead:

    Mike speaks  ->  JOE understands  ->  JOE answers  ->  JOE listens again

The loop lives here rather than in the window so it can be tested without a
microphone, a speaker, or a display. The window owns the button and the colours;
this owns when to listen, when to stop listening, and what a spoken command
means.

Two rules that are not negotiable:

  * The microphone is suppressed while JOE is speaking. Without that, JOE hears
    its own answer, treats it as the next question, and talks to itself.
  * Every voice interaction produces a WRITTEN record. Voice is transport. It
    is never the only record of what was said or answered.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


class VoiceState:
    """What JOE is doing right now. The button colour follows this."""

    OFF = "OFF"                # not listening; typed input only
    LISTENING = "LISTENING"    # microphone open, waiting for Mike
    THINKING = "THINKING"      # heard something, working on it
    SPEAKING = "SPEAKING"      # talking; microphone suppressed
    ALL = (OFF, LISTENING, THINKING, SPEAKING)


# Ordinary things a person says, not technical phrases. Matching is on the
# recognized text, which is why each entry is a plain word or two rather than
# an exact utterance - "Joe, stop" and "stop" must both work.
COMMANDS = {
    "STOP": ("stop", "quiet", "be quiet", "shut up", "nevermind", "never mind"),
    "REPEAT": ("repeat", "say that again", "again please", "what did you say"),
    "SHORTER": ("short version", "shorter", "keep it short", "briefly"),
    "SAVE": ("save that", "save this", "keep that", "remember that"),
    "VOICE_OFF": ("voice off", "turn voice off", "stop listening",
                  "voice mode off", "turn off voice"),
}

# A recognizer with an open microphone and no speech returns noise. Anything
# this short is not a request and must not be sent anywhere.
MIN_UTTERANCE_WORDS = 2


def normalise(text: str) -> str:
    keep = [c.lower() if (c.isalnum() or c.isspace()) else " " for c in text or ""]
    return " ".join("".join(keep).split())


def strip_wake_word(text: str) -> str:
    """Drop a leading "Joe," so the rest is the actual request."""
    cleaned = normalise(text)
    for prefix in ("joe ", "hey joe ", "ok joe ", "okay joe "):
        if cleaned.startswith(prefix):
            return cleaned[len(prefix):].strip()
    return cleaned


def recognise_command(text: str) -> str:
    """Which spoken command this is, or "" for an ordinary request.

    Checked against the whole utterance, not a substring of it: "save that" is
    a command, but "what does save that mean" is a question about one, and
    answering a question by executing it is the same defect the typed router
    already had to fix."""
    cleaned = strip_wake_word(text)
    if not cleaned:
        return ""
    for name, phrases in COMMANDS.items():
        for phrase in phrases:
            if cleaned == phrase or cleaned.startswith(phrase + " ") or \
                    cleaned.endswith(" " + phrase):
                # A question ABOUT a command is not the command.
                if cleaned.startswith(("what ", "how ", "when ", "why ",
                                       "does ", "do i ", "should i ")):
                    return ""
                return name
    return ""


def is_usable_utterance(text: str) -> bool:
    cleaned = strip_wake_word(text)
    return len(cleaned.split()) >= MIN_UTTERANCE_WORDS


@dataclass
class VoiceTurn:
    """One pass round the loop, kept for the written record."""

    heard: str = ""
    command: str = ""
    answered: bool = False
    spoken: bool = False
    record_id: str = ""
    error: str = ""
    at: float = field(default_factory=time.time)


class DriverVoiceLoop:
    """Listen, answer, speak, listen again - until told to stop.

    Everything that touches hardware is injected, so the whole loop is
    testable: `listen` returns recognized text, `speak` says something, `ask`
    runs the normal request path. None of them are called on the UI thread.
    """

    def __init__(self, listen, speak, ask, on_state=None, on_turn=None,
                 listen_seconds=6, pause_seconds=0.25):
        self._listen = listen
        self._speak = speak
        self._ask = ask
        self._on_state = on_state or (lambda state: None)
        self._on_turn = on_turn or (lambda turn: None)
        self.listen_seconds = listen_seconds
        self.pause_seconds = pause_seconds

        self.state = VoiceState.OFF
        self.turns: list[VoiceTurn] = []
        self.last_answer = ""
        self._thread = None
        self._running = threading.Event()
        # Set while JOE speaks. The loop will not open the microphone while it
        # is set, which is what stops JOE answering itself.
        self._muted = threading.Event()

    # ---- state ---------------------------------------------------------

    @property
    def is_on(self) -> bool:
        return self.state != VoiceState.OFF

    @property
    def is_listening(self) -> bool:
        return self.state == VoiceState.LISTENING

    @property
    def is_speaking(self) -> bool:
        return self.state == VoiceState.SPEAKING

    @property
    def microphone_suppressed(self) -> bool:
        return self._muted.is_set()

    def _set_state(self, state: str) -> None:
        self.state = state
        self._on_state(state)

    # ---- lifecycle -----------------------------------------------------

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._set_state(VoiceState.LISTENING)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Turn voice off. Safe to call from any thread, including the UI."""
        self._running.clear()
        self._muted.clear()
        self._set_state(VoiceState.OFF)

    def toggle(self) -> bool:
        if self.is_on:
            self.stop()
        else:
            self.start()
        return self.is_on

    def join(self, timeout=5.0) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    # ---- the loop ------------------------------------------------------

    def _loop(self) -> None:
        while self._running.is_set():
            if self._muted.is_set():
                time.sleep(0.05)
                continue
            self._set_state(VoiceState.LISTENING)
            try:
                heard = self._listen(self.listen_seconds)
            except Exception as error:  # noqa: BLE001
                # A microphone failure must not end the conversation or the
                # program. It is reported and the loop keeps going.
                self._emit(VoiceTurn(error=str(error)))
                time.sleep(0.5)
                continue

            if not self._running.is_set():
                break
            text = (heard or "").strip()
            if not is_usable_utterance(text):
                time.sleep(self.pause_seconds)
                continue

            self._handle(text)
            time.sleep(self.pause_seconds)
        self._set_state(VoiceState.OFF)

    def _handle(self, text: str) -> None:
        command = recognise_command(text)
        turn = VoiceTurn(heard=text, command=command)

        if command == "VOICE_OFF":
            self.say("Voice off.", turn)
            self._emit(turn)
            self.stop()
            return
        if command == "STOP":
            # Already not speaking by the time this is heard; the point is to
            # not answer it as a question.
            self._emit(turn)
            return
        if command == "REPEAT":
            if self.last_answer:
                self.say(self.last_answer, turn)
            else:
                self.say("I have not said anything yet.", turn)
            self._emit(turn)
            return

        self._set_state(VoiceState.THINKING)
        try:
            spoken, record_id = self._ask(text, short=(command == "SHORTER"),
                                          save=(command == "SAVE"))
        except Exception as error:  # noqa: BLE001
            turn.error = str(error)
            self.say("That request failed. The written detail is on screen.", turn)
            self._emit(turn)
            return

        turn.answered = True
        turn.record_id = record_id or ""
        self.last_answer = spoken or ""
        if spoken:
            self.say(spoken, turn)
        self._emit(turn)

    # ---- speaking ------------------------------------------------------

    def say(self, text: str, turn: VoiceTurn | None = None) -> bool:
        """Speak with the microphone suppressed for the whole utterance."""
        if not text:
            return False
        self._muted.set()
        self._set_state(VoiceState.SPEAKING)
        try:
            spoken = bool(self._speak(text))
        except Exception as error:  # noqa: BLE001
            spoken = False
            if turn is not None:
                turn.error = str(error)
        finally:
            self._muted.clear()
            if self._running.is_set():
                self._set_state(VoiceState.LISTENING)
            else:
                self._set_state(VoiceState.OFF)
        if turn is not None:
            turn.spoken = spoken
        return spoken

    def _emit(self, turn: VoiceTurn) -> None:
        self.turns.append(turn)
        self._on_turn(turn)
