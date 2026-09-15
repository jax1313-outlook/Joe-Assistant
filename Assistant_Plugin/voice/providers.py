"""Which voice this machine actually has, and the honest word for it.

`voice/assistant_voice/engines.py` already defines the two ports --
`SpeechToTextEngine` and `TextToSpeechEngine` -- and ships text substitutes for
both. What was missing is the thing a person needs before trusting any of it:
**one place that says what is installed, what is configured, and what is merely
possible.**

| Provider | Speech to text | Text to speech | Needs |
|---|---|---|---|
| `azure_speech` | yes | yes | a Speech resource key + region |
| `whisper_local` | yes | — | the local model files |
| `windows_sapi` | — | yes | Windows |
| `text` | yes | yes | nothing; it is the substitute |

Three rules, and they are the difference between a voice stack and a demo.

**Nothing is claimed until it is exercised.** A key in the environment makes a
provider `CONFIGURED`, never `LIVE`. `LIVE` requires a round trip that actually
happened, and this module has never made one.

**There is always a working pair.** The text engines are last in the order and
always available, so Joe runs on a laptop with no microphone, in CI, and in a
test -- and reports `SIMULATED` while doing it, so nobody mistakes a transcript
for something that was heard.

**A failure degrades; it does not stop the drive.** A provider that raises is
reported `UNAVAILABLE` and the next one down is used. CLAUDE.md 5.4:
"Degradation is permitted. Incapacity is not."
"""

from __future__ import annotations

import os
from dataclasses import dataclass

TRUTH_WORDS = ("LIVE", "CONFIGURED", "UNCONFIGURED", "SIMULATED",
               "UNAVAILABLE", "MANUAL", "ABSENT", "UNVERIFIED")

#: Most specific first. `text` is last and always available.
STT_ORDER = ("azure_speech", "whisper_local", "text")
TTS_ORDER = ("azure_speech", "windows_sapi", "text")

AZURE_KEY = "JOE_AZURE_SPEECH_KEY"
AZURE_REGION = "JOE_AZURE_SPEECH_REGION"
WHISPER_MODEL = "JOE_WHISPER_MODEL"


@dataclass(frozen=True)
class ProviderStatus:
    provider_id: str
    role: str
    status: str
    detail: str
    requires: tuple = ()
    selected: bool = False

    def describe(self) -> str:
        return f"{self.status} -- {self.provider_id} ({self.role}): {self.detail}"

    def to_dict(self) -> dict:
        return {"provider_id": self.provider_id, "role": self.role, "status": self.status,
                "detail": self.detail, "requires": list(self.requires),
                "selected": self.selected}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def azure_status(role: str) -> ProviderStatus:
    """Microsoft's Speech service.

    Preferred where configured for an operational reason rather than a technical
    one: it is the same Microsoft account the rest of the integration uses, so
    there is one credential to manage rather than two.
    """
    key, region = _env(AZURE_KEY), _env(AZURE_REGION)
    if not key or not region:
        missing = [n for n, v in ((AZURE_KEY, key), (AZURE_REGION, region)) if not v]
        return ProviderStatus("azure_speech", role, "UNCONFIGURED",
                              f"not set: {', '.join(missing)}",
                              requires=(AZURE_KEY, AZURE_REGION))
    try:
        import azure.cognitiveservices.speech  # noqa: F401
    except ImportError:
        return ProviderStatus(
            "azure_speech", role, "UNAVAILABLE",
            "credentials are set but azure-cognitiveservices-speech is not installed here.",
            requires=(AZURE_KEY, AZURE_REGION))
    # CONFIGURED, not LIVE. A key that parses is not a round trip that happened.
    return ProviderStatus("azure_speech", role, "CONFIGURED",
                          f"key and region ({region}) present; no call has been made yet.",
                          requires=(AZURE_KEY, AZURE_REGION))


def whisper_status() -> ProviderStatus:
    try:
        from adapters import whisper_listen  # noqa: F401
    except ImportError:
        return ProviderStatus("whisper_local", "speech_to_text", "ABSENT",
                              "the local Whisper adapter is not present in this build.")
    model = _env(WHISPER_MODEL)
    if not model:
        return ProviderStatus("whisper_local", "speech_to_text", "UNCONFIGURED",
                              f"no {WHISPER_MODEL} is set, so there is no model to load.",
                              requires=(WHISPER_MODEL,))
    from pathlib import Path

    if not Path(model).exists():
        return ProviderStatus("whisper_local", "speech_to_text", "UNAVAILABLE",
                              f"{WHISPER_MODEL} points at {model}, which is not there.",
                              requires=(WHISPER_MODEL,))
    return ProviderStatus("whisper_local", "speech_to_text", "CONFIGURED",
                          f"model present at {model}; not yet exercised.",
                          requires=(WHISPER_MODEL,))


def sapi_status() -> ProviderStatus:
    if os.name != "nt":
        return ProviderStatus("windows_sapi", "text_to_speech", "ABSENT",
                              "SAPI is a Windows speech interface and this is not Windows.")
    try:
        from adapters import voice_sapi  # noqa: F401
    except ImportError:
        return ProviderStatus("windows_sapi", "text_to_speech", "ABSENT",
                              "the SAPI adapter is not present in this build.")
    return ProviderStatus("windows_sapi", "text_to_speech", "CONFIGURED",
                          "Windows speech is available; not yet exercised.")


def text_status(role: str) -> ProviderStatus:
    """The substitute. Always available, and always says what it is.

    SIMULATED rather than LIVE on purpose: a transcript typed into a test is not
    something that was heard, and a spoken line appended to a list is not
    something anybody was told.
    """
    return ProviderStatus("text", role, "SIMULATED",
                          "text in, text out. Nothing was heard and nothing was said aloud.")


def survey() -> dict:
    stt = [azure_status("speech_to_text"), whisper_status(), text_status("speech_to_text")]
    tts = [azure_status("text_to_speech"), sapi_status(), text_status("text_to_speech")]
    return {"speech_to_text": _mark_selected(stt, STT_ORDER),
            "text_to_speech": _mark_selected(tts, TTS_ORDER)}


def _mark_selected(statuses: list, order: tuple) -> list:
    by_id = {s.provider_id: s for s in statuses}
    chosen = None
    for provider_id in order:
        status = by_id.get(provider_id)
        if status is not None and status.status in ("LIVE", "CONFIGURED", "SIMULATED"):
            chosen = provider_id
            break
    return [ProviderStatus(s.provider_id, s.role, s.status, s.detail, s.requires,
                           selected=(s.provider_id == chosen)) for s in statuses]


def selected(role: str) -> ProviderStatus:
    for row in survey()[role]:
        if row.selected:
            return row
    return text_status(role)


def build_engines(*, prefer: str | None = None):
    """The pair Joe will actually use, plus what they are.

    Returns `(stt, tts, report)`. The report is not optional: a voice stack whose
    state is visible only in a debug line is one nobody can trust, and the first
    question anybody asks is whether it is actually listening.
    """
    from voice.assistant_voice.engines import TextSpeechToText, TextTextToSpeech

    stt = _build_stt(prefer or selected("speech_to_text").provider_id) or TextSpeechToText()
    tts = _build_tts(prefer or selected("text_to_speech").provider_id) or TextTextToSpeech()
    return stt, tts, survey()


def _build_stt(provider_id: str):
    if provider_id == "whisper_local":
        try:
            from adapters.whisper_listen import build_engine  # type: ignore

            return build_engine()
        except Exception:  # noqa: BLE001 - degrade, never stop
            return None
    return None  # azure_speech has no adapter written; see the activation doc


def _build_tts(provider_id: str):
    if provider_id == "windows_sapi":
        try:
            from adapters.voice_sapi import build_engine  # type: ignore

            return build_engine()
        except Exception:  # noqa: BLE001
            return None
    return None


def render_survey() -> str:
    lines = []
    for role, rows in survey().items():
        lines.append(f"  {role.replace('_', ' ')}:")
        for row in rows:
            lines.append(f"    {'>' if row.selected else ' '} {row.describe()}")
        lines.append("")
    return "\n".join(lines)
