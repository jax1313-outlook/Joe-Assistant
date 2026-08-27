"""Microphone enumeration, selection, and diagnostics.

WHAT THIS CAN AND CANNOT DO, STATED UP FRONT
--------------------------------------------
JOE recognises speech through Windows `System.Speech`. That class offers
exactly one way to attach a live microphone:

    SetInputToDefaultAudioDevice()

There is no `SetInputToDevice(name)`. The other input methods take a wave file
or an audio stream, and filling a stream from a chosen capture endpoint needs a
WASAPI capture library this build does not have and will not silently acquire.

So:

  * JOE always records from the **Windows default input device**.
  * Mike may express a PREFERENCE for a device, and JOE will remember it,
    report it, and tell him plainly whether Windows agrees.
  * If the preferred device is not the Windows default, JOE says so and names
    the one actually in use. It does not pretend to have switched.

A selector that silently records a choice and then records from a different
microphone would be worse than no selector at all - Mike would speak into a
headset while JOE listened to the laptop lid.

Everything here is READ-ONLY with respect to Windows. JOE does not change the
system default device; that is a Windows sound setting and Mike's to make.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

# DeviceState values Windows records for each capture endpoint.
STATE_ACTIVE = 1
STATE_DISABLED = 0x10000001        # 268435457
STATE_NOT_PRESENT = 8              # unplugged, or a Bluetooth device not connected
STATE_UNPLUGGED = 4

STATE_LABEL = {
    STATE_ACTIVE: "connected and available",
    STATE_DISABLED: "disabled in Windows",
    STATE_NOT_PRESENT: "not connected",
    STATE_UNPLUGGED: "unplugged",
}

# Endpoints that are not a person speaking. Stereo Mix records what the
# machine is PLAYING - selecting it would make JOE hear its own voice through
# the loopback no matter how carefully the microphone is suppressed.
LOOPBACK_NAMES = ("stereo mix", "what u hear", "wave out mix", "loopback")

_CAPTURE_KEY = (
    r"HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
)
_NAME_PROPERTY = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"

_SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
$rows = @()
foreach ($key in Get-ChildItem '__CAPTURE__') {
  $name = $null; $state = $null
  try { $name = (Get-ItemProperty (Join-Path $key.PSPath 'Properties'))."__NAMEPROP__" } catch {}
  try { $state = (Get-ItemProperty $key.PSPath).DeviceState } catch {}
  if ($name) {
    $rows += [ordered]@{ name = [string]$name; state = [int]$state; id = $key.PSChildName }
  }
}
[ordered]@{ ok = $true; devices = $rows } | ConvertTo-Json -Depth 4 -Compress
"""


@dataclass
class Microphone:
    name: str
    state: int
    device_id: str = ""

    @property
    def available(self) -> bool:
        return self.state == STATE_ACTIVE

    @property
    def is_loopback(self) -> bool:
        lowered = self.name.lower()
        return any(marker in lowered for marker in LOOPBACK_NAMES)

    @property
    def status(self) -> str:
        return STATE_LABEL.get(self.state, "unknown state (" + str(self.state) + ")")

    @property
    def looks_like_bluetooth(self) -> bool:
        lowered = self.name.lower()
        return any(marker in lowered for marker in
                   ("headset", "hands-free", "bluetooth", "airpods", "buds"))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "status": self.status,
            "available": self.available,
            "is_loopback": self.is_loopback,
            "bluetooth": self.looks_like_bluetooth,
        }


@dataclass
class MicrophoneReport:
    ok: bool = False
    devices: list = field(default_factory=list)
    error: str = ""
    preferred: str = ""

    @property
    def available(self) -> list:
        return [d for d in self.devices if d.available and not d.is_loopback]

    @property
    def in_use(self):
        """What JOE will actually record from.

        Windows exposes one active capture endpoint at a time; that is the
        default device, and the only one System.Speech can bind to.
        """
        for device in self.available:
            return device
        return None

    @property
    def preference_honoured(self) -> bool:
        """True when Mike's preferred device is the one Windows will use."""
        if not self.preferred:
            return True
        current = self.in_use
        return current is not None and _matches(current.name, self.preferred)

    def blocker(self) -> str:
        if not self.ok:
            return self.error or "the microphone list could not be read"
        if not self.devices:
            return "Windows reports no recording devices at all"
        if not self.available:
            unplugged = [d.name for d in self.devices if not d.available]
            return ("no recording device is connected. Windows knows about "
                    + ", ".join(unplugged[:4]) + ", none of them connected")
        if not self.preference_honoured:
            current = self.in_use
            return ("your preferred microphone is \"" + self.preferred
                    + "\", but Windows is using \""
                    + (current.name if current else "nothing")
                    + "\". JOE records from the Windows default, so that is "
                      "what it will hear. Change it in Windows Sound settings "
                      "to make the preference take effect.")
        return ""


def _matches(name: str, wanted: str) -> bool:
    """Loose match. Windows renames endpoints more often than people expect."""
    a = (name or "").strip().lower()
    b = (wanted or "").strip().lower()
    return bool(a) and bool(b) and (a == b or a in b or b in a)


class MicrophoneAdapter:
    """Reads the Windows recording-device list. Never changes it."""

    name = "microphones"

    def __init__(self, preferred: str = "", timeout_seconds: int = 30,
                 logger=None) -> None:
        self.preferred = (preferred or "").strip()
        self.timeout_seconds = timeout_seconds
        self._logger = logger
        self.last_error = ""

    # ---- enumeration ---------------------------------------------------

    def enumerate(self) -> MicrophoneReport:
        script = (_SCRIPT.replace("__CAPTURE__", _CAPTURE_KEY)
                          .replace("__NAMEPROP__", _NAME_PROPERTY))
        try:
            finished = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True,
                # Real mail carries characters PowerShell does not
                # emit as clean UTF-8. Strict decoding raised
                # UnicodeDecodeError inside the reader THREAD, which
                # killed the read and surfaced as "Outlook returned
                # nothing" - a live mailbox reported as unreadable
                # because one subject line had an odd byte.
                encoding="utf-8", errors="replace", timeout=self.timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as error:  # noqa: BLE001
            self.last_error = str(error)
            self._log("microphone_enumeration_failed", self.last_error)
            return MicrophoneReport(ok=False, error=self.last_error,
                                    preferred=self.preferred)

        raw = (finished.stdout or "").strip()
        if not raw:
            self.last_error = (finished.stderr or "").strip() or "no output"
            self._log("microphone_enumeration_failed", self.last_error)
            return MicrophoneReport(ok=False, error=self.last_error,
                                    preferred=self.preferred)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.last_error = "the microphone list could not be read"
            self._log("microphone_enumeration_failed", self.last_error)
            return MicrophoneReport(ok=False, error=self.last_error,
                                    preferred=self.preferred)

        rows = payload.get("devices") or []
        if isinstance(rows, dict):
            rows = [rows]
        devices = [
            Microphone(name=str(r.get("name", "")), state=int(r.get("state", 0) or 0),
                       device_id=str(r.get("id", "")))
            for r in rows if r.get("name")
        ]
        report = MicrophoneReport(ok=True, devices=devices, preferred=self.preferred)
        self.last_error = ""
        current = report.in_use
        self._log("microphone_selected",
                  (current.name if current else "(none available)")
                  + ("  preferred=" + self.preferred if self.preferred else ""))
        if not report.preference_honoured:
            self._log("microphone_preference_not_honoured", report.blocker())
        return report

    # ---- diagnostics ---------------------------------------------------

    def diagnostics(self) -> dict:
        """Everything a person needs to work out why JOE cannot hear them."""
        report = self.enumerate()
        current = report.in_use
        return {
            "ok": report.ok,
            "in_use": current.name if current else "",
            "in_use_status": current.status if current else "no device connected",
            "preferred": self.preferred,
            "preference_honoured": report.preference_honoured,
            "bluetooth_present": any(d.looks_like_bluetooth for d in report.devices),
            "bluetooth_connected": any(
                d.looks_like_bluetooth and d.available for d in report.devices),
            "devices": [d.to_dict() for d in report.devices],
            "blocker": report.blocker(),
            # Stated plainly so nobody has to read this module to learn it.
            "selection_note": (
                "JOE records from the Windows default input device. Windows "
                "Speech Recognition offers no way to bind to a chosen device, "
                "so a preference here is remembered and reported, not enforced."
            ),
        }

    def _log(self, event: str, detail: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(event, detail)
        except Exception:  # noqa: BLE001 - logging must never break voice
            pass
