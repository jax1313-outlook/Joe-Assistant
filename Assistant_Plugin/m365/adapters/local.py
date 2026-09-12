"""Substitutes, so every port has an answer on a machine with no Microsoft account.

Each of these answers `SIMULATED` and says what it did. That word is the whole
purpose of the module: a local file written to a scratch folder and a document
that reached OneDrive are different facts, and the only thing standing between
them in a report is the status word.

They are not mocks. They do real, useful work locally -- the calendar reads a
JSON file an operator can edit, the mail writes a `.eml` a person can open, the
file port writes to disk -- so Joe and the workers are exercisable end to end
without a tenant. What they never do is claim the work reached anybody.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from m365.ports import CalendarEvent, Result, StoredFile

PROVIDER = "local"


@dataclass
class LocalCalendar:
    """Reads events from a JSON file. An operator can edit it; nobody is invited."""

    source: Path | None = None
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "SIMULATED" if self.source and Path(self.source).is_file() else "UNCONFIGURED"

    def read_events(self, *, start: str, end: str, limit: int = 100) -> Result:
        if self.status() == "UNCONFIGURED":
            return Result("UNCONFIGURED", "No local calendar file is configured.", PROVIDER)
        try:
            rows = json.loads(Path(self.source).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return Result("UNAVAILABLE", f"could not read the calendar file: {exc}", PROVIDER)
        events = [
            CalendarEvent(
                event_id=row.get("id", ""), subject=row.get("subject", ""),
                starts_at=row.get("start", ""), ends_at=row.get("end", ""),
                location=row.get("location", ""), source="local file",
            ).to_dict()
            for row in rows[:limit]
            if start <= row.get("start", "") <= end
        ]
        return Result("SIMULATED", f"{len(events)} event(s) from a local file. "
                      "Nothing was read from Outlook.", PROVIDER, {"events": events})

    def propose_event(self, *, subject, starts_at, ends_at, location="",
                      authorized_by="", authorization_ref="") -> Result:
        return Result("MANUAL",
                      "There is no calendar to write to. This is the event somebody "
                      "would create.", PROVIDER,
                      {"proposed": {"subject": subject, "starts_at": starts_at,
                                    "ends_at": ends_at, "location": location}})


@dataclass
class LocalMail:
    """Writes a .eml. A person can open it; nobody received it."""

    outbox: Path = field(default_factory=lambda: Path("Outbox"))
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "SIMULATED"

    def send(self, *, to: tuple, subject: str, body_text: str,
             body_html: str = "", cc: tuple = ()) -> Result:
        from email.message import EmailMessage

        message = EmailMessage()
        message["To"] = ", ".join(to)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        message.set_content(body_text)
        if body_html:
            message.add_alternative(body_html, subtype="html")

        Path(self.outbox).mkdir(parents=True, exist_ok=True)
        import hashlib
        from datetime import datetime, timezone

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        digest = hashlib.sha256(message.as_bytes()).hexdigest()[:8]
        path = Path(self.outbox) / f"{stamp}-{digest}.eml"
        path.write_bytes(message.as_bytes())
        return Result("SIMULATED", f"not sent; written to {path}", PROVIDER,
                      {"path": str(path)})


@dataclass
class LocalFiles:
    root: Path = field(default_factory=lambda: Path("LocalDrive"))
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "SIMULATED"

    def put(self, *, path: str, content: bytes, content_type: str = "") -> Result:
        import hashlib

        target = Path(self.root) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return Result("SIMULATED", f"written to {target}; nothing reached OneDrive.",
                      PROVIDER, {"file": StoredFile(
                          file_id=str(target), name=target.name, size=len(content),
                          checksum=hashlib.sha256(content).hexdigest(),
                      ).to_dict()})

    def get(self, *, path: str) -> Result:
        target = Path(self.root) / path
        if not target.is_file():
            return Result("ABSENT", f"{target} is not there.", PROVIDER)
        return Result("SIMULATED", f"{target.stat().st_size:,} bytes from disk.",
                      PROVIDER, {"content": target.read_bytes()})

    def list(self, *, folder: str = "") -> Result:
        base = Path(self.root) / folder if folder else Path(self.root)
        if not base.is_dir():
            return Result("ABSENT", f"{base} is not there.", PROVIDER, {"files": []})
        files = [
            StoredFile(file_id=str(p), name=p.name, size=p.stat().st_size).to_dict()
            for p in sorted(base.iterdir()) if p.is_file()
        ]
        return Result("SIMULATED", f"{len(files)} local file(s).", PROVIDER, {"files": files})


@dataclass
class LocalDocuments:
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "SIMULATED"

    def render(self, *, title: str, sections: tuple, fmt: str = "txt") -> Result:
        if fmt not in ("txt", "html"):
            return Result("ABSENT",
                          f"{fmt!r} needs a provider that can produce it. Locally there "
                          "is plain text and HTML.", PROVIDER)
        from m365.adapters.graph import _render_body

        body = _render_body(title, sections, fmt)
        return Result("SIMULATED", f"{len(body):,} bytes rendered locally.", PROVIDER,
                      {"content": body, "format": fmt})


@dataclass
class UnavailableSite:
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "ABSENT"

    def list_documents(self, *, library: str = "Documents", limit: int = 50) -> Result:
        return Result("ABSENT", "There is no local stand-in for a SharePoint site. "
                      "A shared site is shared with somebody, and a folder on this "
                      "laptop is not.", PROVIDER)

    def read_document(self, *, item_id: str) -> Result:
        return self.list_documents()


@dataclass
class UnavailableChat:
    provider_id: str = PROVIDER

    def status(self) -> str:
        return "ABSENT"

    def post_notice(self, *, channel: str, text: str, authorized_by: str = "") -> Result:
        return Result("ABSENT", "There is no local stand-in for a Teams channel. "
                      "Writing the notice to a file would not tell anybody.", PROVIDER,
                      {"proposed": {"channel": channel, "text": text}})
