"""What Dispatch needs from an office suite — stated without naming one.

**Microsoft is a replaceable wheel.** `Dispatch/CLAUDE.md` records the General
Contractor Doctrine in those terms: "Dispatch coordinates core operational work
and uses external wheels... Use the provider; own the interface." A port is how
you own the interface. If every module that wants a calendar imports
`msgraph`, the wheel is welded on, and the cost of that is not felt until the
day it has to come off.

Six ports, one per thing Dispatch actually needs:

| Port | What Dispatch needs | What it must never do |
|---|---|---|
| `CalendarPort` | read the schedule | write a second schedule |
| `MailPort` | send what a person approved | send what nobody approved |
| `FilePort` | keep evidence somewhere durable | become the system of record |
| `SitePort` | read shared documents | publish without review |
| `ChatPort` | post a notice a person wrote | hold a conversation |
| `DocumentPort` | produce a document from approved facts | invent a fact |

The asymmetry in the calendar port is doctrine, not taste. CLAUDE.md 5.5:
Outlook is the scheduling authority, and **"Dispatch must not create a separate
competing scheduling system."** So `CalendarPort` has `read_events` and
`propose_event` -- and `propose_event` returns a proposal for a person to
accept, because creating a calendar entry is an external side effect of a
human's approval, not a state Dispatch passes through.

Every port answers `status()` in the eight truth words before it is asked to do
anything, so a screen can say what this machine will actually do without a test
message going to a broker to find out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

TRUTH_WORDS = ("LIVE", "CONFIGURED", "UNCONFIGURED", "SIMULATED",
               "UNAVAILABLE", "MANUAL", "ABSENT", "UNVERIFIED")


class PortError(RuntimeError):
    """The provider tried and failed. Retryable unless it says otherwise."""

    retryable = True


class PortUnconfigured(PortError):
    """Asked to work without the settings it needs. Never retried -- retrying a
    missing client id every five minutes achieves nothing but a longer log."""

    retryable = False


class PortRefused(PortError):
    """The provider answered, and the answer was no. Not a fault; not retried."""

    retryable = False


@dataclass(frozen=True)
class Result:
    """What happened, in the words the rest of the program already uses."""

    status: str
    detail: str
    provider: str = ""
    data: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in TRUTH_WORDS:
            raise ValueError(f"status must be one of the eight, not {self.status!r}")

    @property
    def ok(self) -> bool:
        return self.status in ("LIVE", "SIMULATED")

    @property
    def real(self) -> bool:
        """True only for something that actually reached a provider.

        SIMULATED is a successful answer from a substitute. Treating it as real
        is how a local fixture becomes a claim about the world.
        """
        return self.status == "LIVE"

    def to_dict(self) -> dict:
        return {"status": self.status, "detail": self.detail,
                "provider": self.provider, "data": dict(self.data)}


@dataclass(frozen=True)
class CalendarEvent:
    """One appointment, as Dispatch reads it. Never as Dispatch owns it."""

    event_id: str
    subject: str
    starts_at: str
    ends_at: str
    location: str = ""
    organizer: str = ""
    is_all_day: bool = False
    #: Where this came from, so a surface can say so rather than presenting it
    #: as something Dispatch knows.
    source: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class StoredFile:
    file_id: str
    name: str
    size: int
    web_url: str = ""
    checksum: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class CalendarPort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def read_events(self, *, start: str, end: str, limit: int = 100) -> Result: ...
    def propose_event(self, *, subject: str, starts_at: str, ends_at: str,
                      location: str = "", authorized_by: str = "",
                      authorization_ref: str = "") -> Result: ...


class MailPort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def send(self, *, to: tuple, subject: str, body_text: str,
             body_html: str = "", cc: tuple = ()) -> Result: ...


class FilePort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def put(self, *, path: str, content: bytes, content_type: str = "") -> Result: ...
    def get(self, *, path: str) -> Result: ...
    def list(self, *, folder: str = "") -> Result: ...


class SitePort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def list_documents(self, *, library: str = "Documents", limit: int = 50) -> Result: ...
    def read_document(self, *, item_id: str) -> Result: ...


class ChatPort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def post_notice(self, *, channel: str, text: str, authorized_by: str = "") -> Result: ...


class DocumentPort(Protocol):
    provider_id: str

    def status(self) -> str: ...
    def render(self, *, title: str, sections: tuple, fmt: str = "docx") -> Result: ...
