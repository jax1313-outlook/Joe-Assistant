"""Speech recognition that can be pointed at a microphone.

WHY THIS EXISTS. JOE recognised speech through Windows System.Speech, which
offers exactly one way to attach a microphone - SetInputToDefaultAudioDevice()
- and no way to name one. On this machine, with Mike's Bluetooth headset set as
the Windows default, that engine returned:

    said     "Joe can you hear me through the headset"
    heard    "But we're right on it shut"
    match    0%

Not one word in common. A Bluetooth headset drops to a narrowband link when it
records, and that engine cannot work with it. It is not a tuning problem.

This adapter fixes both halves. Capture is done by sounddevice, which binds to
a named device, so "which microphone" stops being a Windows setting JOE can
only observe. Transcription is done by faster-whisper, which handles narrowband
audio and is far more accurate than the engine it replaces.

WHAT IT WILL NOT DO. It returns what was heard, or it returns nothing and says
why. It does not fill a silence with a plausible sentence, and it does not
report a transcription when the model or the microphone was unavailable - a
recogniser that guesses is worse than one that fails, because a guess reaches
Mike wearing the same clothes as an answer.

THE MODEL IS A DOWNLOAD. The first run fetches it, which needs a network. That
is reported as a blocker rather than attempted silently at the wheel.
"""

from __future__ import annotations

import queue
import threading

# Whisper is trained on 16 kHz mono. It is also what a Bluetooth headset
# natively provides when recording, so nothing is resampled twice.
SAMPLE_RATE = 16000
CHANNELS = 1

# base is the largest model that keeps a short phrase quick on a 2018 laptop
# CPU. small and medium are materially more accurate and belong on a machine
# with a GPU; the model name is configuration, not a constant.
DEFAULT_MODEL = "base"

# int8 keeps a CPU run fast. A GPU machine should use float16.
DEFAULT_COMPUTE = "int8"


def available() -> tuple[bool, str]:
    """Are both halves installed? Says which is missing, not just 'no'."""
    missing = []
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        missing.append("faster-whisper")
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        missing.append("sounddevice")
    if missing:
        return False, ("not installed: " + ", ".join(missing)
                       + " - run: py -m pip install --user "
                       + " ".join(missing))
    return True, ""


def input_devices() -> list:
    """Every capture device, with the index needed to bind to one."""
    try:
        import sounddevice as sd
    except ImportError:
        return []
    devices = []
    try:
        default_index = sd.default.device[0]
    except Exception:  # noqa: BLE001
        default_index = None
    for index, device in enumerate(sd.query_devices()):
        if device.get("max_input_channels", 0) < 1:
            continue
        devices.append({
            "index": index,
            "name": str(device.get("name", "")),
            "channels": int(device.get("max_input_channels", 0)),
            "sample_rate": int(device.get("default_samplerate", 0)),
            "is_windows_default": index == default_index,
        })
    return devices


def resolve_device(preferred: str):
    """The device index for a name, or None for the Windows default.

    Matching is loose because Windows spells the same headset several ways -
    "Headset (LE-HS015)" and "Headset (@System32\\drivers\\bthhfenum.sys...)"
    are the same piece of plastic. The exact name JOE settled on is reported
    back, so there is no doubt afterwards which one it used.
    """
    wanted = (preferred or "").strip().lower()
    if not wanted:
        return None, ""
    devices = input_devices()
    for device in devices:                       # exact first
        if device["name"].strip().lower() == wanted:
            return device["index"], device["name"]
    for device in devices:                       # then contained
        if wanted in device["name"].strip().lower():
            return device["index"], device["name"]
    return None, ""


class WhisperListener:
    """Records from a chosen microphone and transcribes what was said."""

    name = "whisper"

    def __init__(self, model: str = "", device: str = "",
                 compute_type: str = "", enabled: bool = True) -> None:
        self.model_name = (model or DEFAULT_MODEL).strip()
        self.preferred_device = (device or "").strip()
        self.compute_type = (compute_type or DEFAULT_COMPUTE).strip()
        self.enabled = bool(enabled)
        self.last_error = ""
        self._model = None

    # ---- status --------------------------------------------------------

    def probe(self) -> dict:
        installed, missing = available()
        index, resolved = resolve_device(self.preferred_device)
        devices = input_devices()

        blocker = ""
        if not self.enabled:
            blocker = "disabled in configuration"
        elif not installed:
            blocker = missing
        elif not devices:
            blocker = "no recording device is connected"
        elif self.preferred_device and not resolved:
            blocker = ("the preferred microphone \"" + self.preferred_device
                       + "\" is not connected")

        return {
            "provider": self.name,
            "available": not blocker,
            "live_connection": not blocker,
            "model": self.model_name,
            "model_loaded": self._model is not None,
            "compute_type": self.compute_type,
            "preferred_device": self.preferred_device,
            # The whole point: JOE names the microphone it will use, and can
            # choose it, rather than reporting whatever Windows decided.
            "device_in_use": resolved or self._windows_default_name(devices),
            "device_chosen_by_joe": bool(resolved),
            "devices": devices,
            "blocker": blocker,
            "last_error": self.last_error,
        }

    @staticmethod
    def _windows_default_name(devices) -> str:
        for device in devices:
            if device["is_windows_default"]:
                return device["name"]
        return ""

    # ---- the model -----------------------------------------------------

    def load(self) -> tuple[bool, str]:
        """Load the model, downloading it on first use. Slow, once."""
        if self._model is not None:
            return True, ""
        installed, missing = available()
        if not installed:
            return False, missing
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self.model_name, device="cpu",
                                       compute_type=self.compute_type)
            return True, ""
        except Exception as error:  # noqa: BLE001
            self.last_error = _brief(error)
            return False, self.last_error

    # ---- listening -----------------------------------------------------

    def listen(self, seconds: int = 6) -> dict:
        """Record for a few seconds and return what was said.

        Same shape as the SAPI listener returns, so this drops into the slot
        that one occupies rather than becoming a second way to do it."""
        blocked = self.probe()["blocker"]
        if blocked:
            return self._nothing(blocked, real_audio=False)

        ok, why = self.load()
        if not ok:
            return self._nothing(why, real_audio=False)

        audio, error, used = self._record(seconds)
        if error:
            return self._nothing(error, real_audio=False, device=used)

        try:
            segments, info = self._model.transcribe(
                audio, language="en", beam_size=5,
                # Whisper will happily invent fluent text from silence. This
                # suppresses that: no speech detected means no speech
                # returned, which is the honest answer.
                vad_filter=True,
                condition_on_previous_text=False,
            )
            spoken = " ".join(segment.text.strip() for segment in segments).strip()
            confidence = float(getattr(info, "language_probability", 0.0) or 0.0)
        except Exception as error:  # noqa: BLE001
            self.last_error = _brief(error)
            return self._nothing(self.last_error, real_audio=True, device=used)

        self.last_error = ""
        return {
            "recognized": bool(spoken),
            "text": spoken,
            "confidence": confidence,
            "error": "" if spoken else "no speech was detected",
            "real_audio_input": True,
            "device": used,
            "engine": self.name + ":" + self.model_name,
        }

    def _record(self, seconds: int):
        """Capture mono 16 kHz from the chosen device."""
        try:
            import numpy
            import sounddevice as sd
        except ImportError as error:
            return None, _brief(error), ""

        index, resolved = resolve_device(self.preferred_device)
        used = resolved or self._windows_default_name(input_devices())
        frames: queue.Queue = queue.Queue()

        def collect(indata, _frames, _time, status):
            if status:
                self.last_error = str(status)
            frames.put(indata.copy())

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype="float32", device=index,
                                callback=collect):
                threading.Event().wait(max(1, int(seconds)))
        except Exception as error:  # noqa: BLE001
            return None, _brief(error), used

        chunks = []
        while not frames.empty():
            chunks.append(frames.get())
        if not chunks:
            return None, "no audio was captured", used
        return numpy.concatenate(chunks).flatten(), "", used

    def _nothing(self, why: str, real_audio: bool, device: str = "") -> dict:
        return {
            "recognized": False,
            "text": "",
            "confidence": 0.0,
            "error": why,
            "real_audio_input": real_audio,
            "device": device,
            "engine": self.name + ":" + self.model_name,
        }


def _brief(error) -> str:
    text = str(error).strip().replace("\n", " ")
    return (text[:160] + "...") if len(text) > 160 else (text or
                                                         type(error).__name__)
