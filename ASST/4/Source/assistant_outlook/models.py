"""Read-only awareness models: calendar events, email messages, contacts.

These objects describe what exists. None of them can change anything. There is
no send, no accept, no decline, no schedule, no reply, and no save - not
disabled, absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


class ModelError(ValueError):
    pass


def parse_moment(text: str) -> datetime:
    """Parse an ISO-8601 timestamp. Naive values are treated as UTC."""
    if not text:
        raise ModelError("a timestamp is required")
    cleaned = str(text).strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as error:
        raise ModelError("unreadable timestamp: " + str(text)) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_iso(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class CalendarEvent:
    """One calendar entry. Read only."""

    event_id: str
    subject: str
    start: datetime
    end: datetime
    location: str = ""
    organizer: str = ""
    attendees: tuple[str, ...] = ()
    is_all_day: bool = False
    response_status: str = "none"  # none | accepted | tentative | declined
    body_preview: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CalendarEvent":
        try:
            event_id = str(data["event_id"])
            subject = str(data.get("subject", "(no subject)"))
            start = parse_moment(data["start"])
            end = parse_moment(data["end"])
        except KeyError as error:
            raise ModelError("calendar event missing field: " + str(error)) from None
        if end < start:
            raise ModelError("event ends before it starts: " + event_id)
        return cls(
            event_id=event_id,
            subject=subject,
            start=start,
            end=end,
            location=str(data.get("location", "")),
            organizer=str(data.get("organizer", "")),
            attendees=tuple(str(a) for a in data.get("attendees", ())),
            is_all_day=bool(data.get("is_all_day", False)),
            response_status=str(data.get("response_status", "none")).lower(),
            body_preview=str(data.get("body_preview", "")),
        )

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def overlaps(self, other: "CalendarEvent") -> bool:
        """True when two events occupy the same time. Touching is not overlap."""
        return self.start < other.end and other.start < self.end

    def is_on(self, day: datetime) -> bool:
        target = day.astimezone(timezone.utc).date()
        return self.start.astimezone(timezone.utc).date() == target

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "subject": self.subject,
            "start": to_iso(self.start),
            "end": to_iso(self.end),
            "location": self.location,
            "organizer": self.organizer,
            "attendees": list(self.attendees),
            "is_all_day": self.is_all_day,
            "response_status": self.response_status,
            "duration_minutes": int(self.duration.total_seconds() // 60),
        }


@dataclass(frozen=True)
class EmailMessage:
    """One mail message. Read only. This component cannot send or reply."""

    message_id: str
    subject: str
    sender: str
    received: datetime
    is_read: bool = False
    has_attachments: bool = False
    importance: str = "normal"  # low | normal | high
    body_preview: str = ""
    to: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "EmailMessage":
        try:
            message_id = str(data["message_id"])
            received = parse_moment(data["received"])
        except KeyError as error:
            raise ModelError("email missing field: " + str(error)) from None
        return cls(
            message_id=message_id,
            subject=str(data.get("subject", "(no subject)")),
            sender=str(data.get("sender", "")),
            received=received,
            is_read=bool(data.get("is_read", False)),
            has_attachments=bool(data.get("has_attachments", False)),
            importance=str(data.get("importance", "normal")).lower(),
            body_preview=str(data.get("body_preview", "")),
            to=tuple(str(t) for t in data.get("to", ())),
        )

    @property
    def searchable_text(self) -> str:
        return (self.subject + " " + self.body_preview).lower()

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "received": to_iso(self.received),
            "is_read": self.is_read,
            "has_attachments": self.has_attachments,
            "importance": self.importance,
            "body_preview": self.body_preview,
            "to": list(self.to),
        }


@dataclass(frozen=True)
class Contact:
    """One contact. Read only."""

    contact_id: str
    display_name: str
    email: str = ""
    company: str = ""
    phone: str = ""
    role: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Contact":
        try:
            contact_id = str(data["contact_id"])
        except KeyError as error:
            raise ModelError("contact missing field: " + str(error)) from None
        return cls(
            contact_id=contact_id,
            display_name=str(data.get("display_name", "")),
            email=str(data.get("email", "")),
            company=str(data.get("company", "")),
            phone=str(data.get("phone", "")),
            role=str(data.get("role", "")),
        )

    @property
    def searchable_text(self) -> str:
        return " ".join(
            [self.display_name, self.email, self.company, self.role]
        ).lower()

    def to_dict(self) -> dict:
        return {
            "contact_id": self.contact_id,
            "display_name": self.display_name,
            "email": self.email,
            "company": self.company,
            "phone": self.phone,
            "role": self.role,
        }
