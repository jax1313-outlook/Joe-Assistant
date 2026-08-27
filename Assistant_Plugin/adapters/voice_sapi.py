"""Voice adapter - Windows System.Speech, via PowerShell.

Provider-specific speech code lives here and nowhere else. The Voice
capability module knows nothing about SAPI, .NET, or Windows.

Two engines:
  - synthesis (text to speech)   - genuinely bindable on this machine
  - recognition (speech to text) - engine bindable; recognition needs a person
                                   at the microphone, so it is never claimed
                                   as proven from an automated run

Nothing speaks unless asked. `speak()` is called only when Mike presses Speak
or enables spoken replies. Opening JOE makes no sound.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from contracts import Provenance, SourceMode, stamp


class VoiceAdapterError(RuntimeError):
    pass


def _ps(script: str, timeout: int = 60) -> tuple[bool, str, str]:
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True,
            # Spoken text carries characters PowerShell does not emit as
            # clean UTF-8. Strict decoding would raise inside the reader
            # thread and surface as the speech engine being unavailable,
            # when the only problem was one odd byte.
            encoding="utf-8", errors="replace", timeout=timeout,
            # Every route through this function - probe, speak, listen,
            # synthesize - would otherwise flash a black console window.
            # This one is the worst offender: speak() runs on every sentence
            # JOE says, so without this the screen blinks each time it
            # opens its mouth.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return False, "", "PowerShell was not found on this machine"
    except subprocess.TimeoutExpired:
        return False, "", "the speech engine did not respond in time"
    out = (completed.stdout or "").strip()
    err = (completed.stderr or "").strip()
    return completed.returncode == 0, out, err


def _escape(text: str) -> str:
    """Single-quoted PowerShell string: double the single quotes."""
    return (text or "").replace("'", "''")


@dataclass
class SpeechAttempt:
    requested_text: str
    spoken: bool = False
    engine: str = "system.speech"
    voice: str = ""
    error: str = ""
    audio_produced: bool = False
    at: str = field(default_factory=stamp)

    def to_dict(self) -> dict:
        return {
            "requested_text": self.requested_text,
            "spoken": self.spoken,
            "engine": self.engine,
            "voice": self.voice,
            "error": self.error,
            "audio_produced": self.audio_produced,
            "at": self.at,
        }


class SapiVoiceAdapter:
    """Live text-to-speech; recognition engine binding only."""

    name = "system-speech"

    def __init__(
        self,
        enabled: bool = True,
        voice_name: str = "",
        rate: int = 0,
        timeout_seconds: int = 60,
        recognizer=None,
    ) -> None:
        self.enabled = enabled
        self.voice_name = voice_name or ""
        self.rate = max(-10, min(10, int(rate)))
        self.timeout_seconds = timeout_seconds
        # An optional replacement for the hearing half only. Speaking stays
        # with System.Speech, which does it well; hearing does not, and cannot
        # be pointed at a microphone.
        self.recognizer = recognizer
        self._probe: dict | None = None
        self.last_error = ""
        self.spoken_count = 0

    # ---- probing ------------------------------------------------------

    def probe(self, refresh: bool = False) -> dict:
        """What speech hardware and engines exist. Makes no sound."""
        if self._probe is not None and not refresh:
            return self._probe
        if not self.enabled:
            self._probe = {
                "tts_available": False,
                "stt_engine_available": False,
                "voices": [],
                "recognizers": [],
                "blocker": "disabled in configuration",
            }
            return self._probe

        script = (
            "$o=[ordered]@{tts=$false;stt=$false;voices=@();recog=@();err=''};"
            "try{Add-Type -AssemblyName System.Speech -ErrorAction Stop;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$o.voices=@($s.GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name});"
            "$o.tts=($o.voices.Count -gt 0);$s.Dispose()}catch{$o.err=$_.Exception.Message};"
            "try{$o.recog=@([System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()"
            "|ForEach-Object{$_.Name});$o.stt=($o.recog.Count -gt 0)}catch{};"
            "$o|ConvertTo-Json -Compress"
        )
        ok, out, err = _ps(script, self.timeout_seconds)
        if not ok or not out:
            self._probe = {
                "tts_available": False,
                "stt_engine_available": False,
                "voices": [],
                "recognizers": [],
                "blocker": err or "speech probe failed",
            }
            return self._probe
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            self._probe = {
                "tts_available": False,
                "stt_engine_available": False,
                "voices": [],
                "recognizers": [],
                "blocker": "speech probe returned unreadable output",
            }
            return self._probe

        voices = payload.get("voices") or []
        recog = payload.get("recog") or []
        if isinstance(voices, str):
            voices = [voices]
        if isinstance(recog, str):
            recog = [recog]
        self._probe = {
            "tts_available": bool(payload.get("tts")),
            "stt_engine_available": bool(payload.get("stt")),
            "voices": list(voices),
            "recognizers": list(recog),
            "blocker": str(payload.get("err", "")),
        }
        return self._probe

    # ---- speaking -----------------------------------------------------

    def speak(self, text: str) -> SpeechAttempt:
        """Speak out loud. Called only on an explicit request."""
        attempt = SpeechAttempt(requested_text=text or "")
        cleaned = (text or "").strip()
        if not cleaned:
            attempt.error = "nothing to speak"
            return attempt
        probe = self.probe()
        if not probe.get("tts_available"):
            attempt.error = probe.get("blocker") or "no speech engine is available"
            return attempt

        chosen = self.voice_name or (probe["voices"][0] if probe["voices"] else "")
        select = (
            "$s.SelectVoice('" + _escape(chosen) + "');" if chosen else ""
        )
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            + select
            + "$s.Rate=" + str(self.rate) + ";"
            "$s.Speak('" + _escape(cleaned) + "');$s.Dispose();'SPOKEN'"
        )
        ok, out, err = _ps(script, self.timeout_seconds)
        if ok and "SPOKEN" in out:
            attempt.spoken = True
            attempt.audio_produced = True
            attempt.voice = chosen
            self.spoken_count += 1
        else:
            attempt.error = err or "the speech engine did not confirm"
            self.last_error = attempt.error
        return attempt

    def synthesize_to_file(self, text: str, wav_path) -> SpeechAttempt:
        """Render speech to a WAV file. Proves the engine binds without sound."""
        attempt = SpeechAttempt(requested_text=text or "")
        cleaned = (text or "").strip()
        if not cleaned:
            attempt.error = "nothing to synthesize"
            return attempt
        probe = self.probe()
        if not probe.get("tts_available"):
            attempt.error = probe.get("blocker") or "no speech engine is available"
            return attempt
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.SetOutputToWaveFile('" + _escape(str(wav_path)) + "');"
            "$s.Speak('" + _escape(cleaned) + "');$s.Dispose();'RENDERED'"
        )
        ok, out, err = _ps(script, self.timeout_seconds)
        if ok and "RENDERED" in out:
            attempt.spoken = True
            attempt.audio_produced = True
            attempt.voice = self.voice_name or "(default)"
        else:
            attempt.error = err or "the speech engine did not confirm"
        return attempt

    # ---- listening ----------------------------------------------------

    def listen(self, seconds: int = 6) -> dict:
        """Listen at the microphone and return what was recognized.

        Requires a person to speak. An automated run cannot prove this, so the
        result always records whether real audio input was involved.

        When a recognizer has been attached, it is used instead of Windows
        System.Speech. That is not a preference: System.Speech cannot bind to a
        named microphone, and on Mike's Bluetooth headset it returned no
        correct words at all. Speaking still goes through System.Speech, which
        does that part perfectly well.
        """
        if self.recognizer is not None:
            return self.recognizer.listen(seconds)

        probe = self.probe()
        if not probe.get("stt_engine_available"):
            return {
                "recognized": False,
                "text": "",
                "confidence": 0.0,
                "error": probe.get("blocker") or "no recognition engine is available",
                "real_audio_input": False,
            }
        script = (
            "$ErrorActionPreference='Stop';"
            "Add-Type -AssemblyName System.Speech;"
            "$r=New-Object System.Speech.Recognition.SpeechRecognitionEngine;"
            "$r.SetInputToDefaultAudioDevice();"
            "$r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));"
            "$res=$r.Recognize([TimeSpan]::FromSeconds(" + str(int(seconds)) + "));"
            "$o=[ordered]@{recognized=$false;text='';confidence=0.0};"
            "if($res){$o.recognized=$true;$o.text=$res.Text;$o.confidence=$res.Confidence};"
            "$r.Dispose();$o|ConvertTo-Json -Compress"
        )
        ok, out, err = _ps(script, max(self.timeout_seconds, seconds + 30))
        if not ok or not out:
            return {
                "recognized": False,
                "text": "",
                "confidence": 0.0,
                "error": err or "the recognition engine did not respond",
                "real_audio_input": True,
            }
        try:
            payload = json.loads(out)
        except json.JSONDecodeError:
            return {
                "recognized": False, "text": "", "confidence": 0.0,
                "error": "recognizer returned unreadable output",
                "real_audio_input": True,
            }
        return {
            "recognized": bool(payload.get("recognized")),
            "text": str(payload.get("text", "")),
            "confidence": float(payload.get("confidence", 0.0) or 0.0),
            "error": "" if payload.get("recognized") else "nothing was recognized",
            "real_audio_input": True,
        }

    # ---- reporting ----------------------------------------------------

    def provenance(self) -> Provenance:
        probe = self.probe()
        return Provenance(
            source="Windows System.Speech",
            mode=SourceMode.LIVE if probe.get("tts_available") else SourceMode.UNAVAILABLE,
            detail=", ".join(probe.get("voices", [])) or probe.get("blocker", ""),
        )
