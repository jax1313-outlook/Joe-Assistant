"""Whether JOE has ever actually heard Mike, on THIS machine.

The status panel used to end its voice-input line with the fixed words "never
proven with a live voice". That was true when it was written and false the
moment Mike proved it - a claim nobody checked, printed as though it were a
finding. This replaces the sentence with a reading.

IT LIVES IN runtime_data, DELIBERATELY. runtime_data is excluded from the
deployment package, so a fresh install starts with no record and correctly says
hearing has never been proven here. Putting it in proof/ would ship Mike's
result to another machine and claim, on hardware it had never met, that the
microphone works. That is the same failure this file exists to remove, moved
somewhere harder to notice.

A failed attempt is recorded too. "Tried and failed" and "never tried" are
different states, and a driver deciding whether to trust a voice command should
be able to tell them apart.
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

FILENAME = "hearing_proof.json"


def _path(runtime_data) -> Path:
    return Path(runtime_data) / "voice" / FILENAME


def record(runtime_data, *, passed: bool, phrase: str, heard: str,
           overlap: float, device: str, engine: str = "",
           self_heard: bool | None = None) -> Path:
    """Write what happened the last time a person spoke to JOE here."""
    target = _path(runtime_data)
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="\n").write(json.dumps({
        "at": datetime.now(timezone.utc).isoformat(),
        "passed": bool(passed),
        "phrase": str(phrase or ""),
        "heard": str(heard or ""),
        "overlap": round(float(overlap or 0.0), 4),
        "device": str(device or ""),
        "engine": str(engine or ""),
        "self_heard": self_heard,
    }, indent=2) + "\n")
    return target


def last(runtime_data) -> dict | None:
    """The last recorded attempt, or None if nobody has ever spoken here."""
    target = _path(runtime_data)
    if not target.is_file():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def summary(runtime_data) -> str:
    """One clause for the status line. Says what is known, and when."""
    record_ = last(runtime_data)
    if not record_:
        return "never proven with a live voice"
    when = str(record_.get("at", ""))[:10]
    percent = int(round(float(record_.get("overlap") or 0.0) * 100))
    if record_.get("passed"):
        return "heard a live voice " + when + " at " + str(percent) + "%"
    return ("last live test FAILED " + when + " at " + str(percent)
            + "% - hearing is not proven here")
