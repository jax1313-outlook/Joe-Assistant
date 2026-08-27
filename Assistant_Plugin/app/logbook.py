"""Logbook - plain-text event log inside the plugin.

Records what happened so a failure has technical detail somewhere, while the
UI keeps plain language. Writes only inside the plugin's logs directory, and
the containment check runs on every write path.

Never logs the body of a Library document, an email, or a calendar entry.
Subjects and counts only - the log is for diagnosing JOE, not for
accumulating a second copy of Mike's information.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import assert_within_plugin

MAX_DETAIL = 300


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Logbook:
    def __init__(self, directory: str | Path) -> None:
        self.directory = assert_within_plugin(Path(directory))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = assert_within_plugin(self.directory / "joe.log")
        self.entries = 0

    def _write(self, level: str, kind: str, detail: str, ref: str = "") -> str:
        line = "  ".join(
            [
                _stamp(),
                level.ljust(5),
                kind.ljust(20),
                (ref or "-").ljust(28),
                (detail or "")[:MAX_DETAIL].replace("\n", " "),
            ]
        )
        assert_within_plugin(self.path)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.entries += 1
        return line

    def event(self, kind: str, detail: str = "", ref: str = "") -> str:
        return self._write("INFO", kind, detail, ref)

    def warn(self, kind: str, detail: str = "", ref: str = "") -> str:
        return self._write("WARN", kind, detail, ref)

    def error(self, kind: str, detail: str = "", ref: str = "") -> str:
        return self._write("ERROR", kind, detail, ref)

    def tail(self, lines: int = 40) -> list[str]:
        if not self.path.exists():
            return []
        return self.path.read_text(encoding="utf-8").splitlines()[-lines:]
