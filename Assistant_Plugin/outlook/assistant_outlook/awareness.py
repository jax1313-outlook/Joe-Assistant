"""Awareness: what the calendar, mail, and contacts say - and nothing more.

This component reports. It does not act, schedule, reply, accept, decline, or
approve. Where it flags something as needing a decision, the decision is Mike
Zachary's; the component has only noticed a word in a subject line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .models import CalendarEvent, Contact, EmailMessage, to_iso
from .provider import AwarenessProvider, JsonFileProvider

# Words that suggest a message is waiting on a person. Deterministic and
# visible on purpose: this is pattern matching, not judgement.
DECISION_MARKERS = (
    "approve", "approval", "confirm", "confirmation", "authorize",
    "sign", "signature", "accept", "decline", "decision", "decide",
    "respond", "reply by", "need your", "let me know", "please advise",
    "asap", "urgent", "deadline", "expires", "rate change", "counter",
)

# A message this old is unlikely to still be actionable without review.
STALE_AFTER_DAYS = 14


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class FlaggedMessage:
    """A message the component noticed, with the reason it was noticed."""

    message_id: str
    subject: str
    sender: str
    received: str
    reasons: list[str] = field(default_factory=list)
    is_read: bool = False
    importance: str = "normal"

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "received": self.received,
            "reasons": list(self.reasons),
            "is_read": self.is_read,
            "importance": self.importance,
            "decided": False,
            "acted_on": False,
        }


@dataclass
class Conflict:
    """Two calendar events occupying the same time."""

    first_id: str
    second_id: str
    first_subject: str
    second_subject: str
    overlap_minutes: int

    def to_dict(self) -> dict:
        return {
            "first_id": self.first_id,
            "second_id": self.second_id,
            "first_subject": self.first_subject,
            "second_subject": self.second_subject,
            "overlap_minutes": self.overlap_minutes,
        }


@dataclass
class DayBrief:
    """What one day looks like. A report, not a plan."""

    date: str
    events: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    unanswered_invitations: list[dict] = field(default_factory=list)
    first_start: str | None = None
    last_end: str | None = None

    @property
    def event_count(self) -> int:
        return len(self.events)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "event_count": self.event_count,
            "events": list(self.events),
            "conflicts": list(self.conflicts),
            "unanswered_invitations": list(self.unanswered_invitations),
            "first_start": self.first_start,
            "last_end": self.last_end,
        }


class AwarenessError(RuntimeError):
    pass


class Awareness:
    """Read-only awareness of calendar, email, and contacts."""

    def __init__(self, provider: AwarenessProvider | None = None) -> None:
        self.provider = provider or JsonFileProvider()

    # ---- raw reads ----------------------------------------------------

    def events(self) -> list[CalendarEvent]:
        return self.provider.calendar_events()

    def messages(self) -> list[EmailMessage]:
        return self.provider.email_messages()

    def contacts(self) -> list[Contact]:
        return self.provider.contacts()

    # ---- calendar awareness -------------------------------------------

    def events_on(self, day: datetime) -> list[CalendarEvent]:
        return [event for event in self.events() if event.is_on(day)]

    def next_event(self, now: datetime | None = None) -> CalendarEvent | None:
        """The next event that has not started yet, or None."""
        moment = now or _utc_now()
        upcoming = [event for event in self.events() if event.start > moment]
        return upcoming[0] if upcoming else None

    def current_event(self, now: datetime | None = None) -> CalendarEvent | None:
        """The event happening right now, or None."""
        moment = now or _utc_now()
        for event in self.events():
            if event.start <= moment < event.end:
                return event
        return None

    def conflicts(self, events: list[CalendarEvent] | None = None) -> list[Conflict]:
        """Every pair of events that overlap in time."""
        candidates = events if events is not None else self.events()
        found: list[Conflict] = []
        for index, first in enumerate(candidates):
            for second in candidates[index + 1:]:
                if not first.overlaps(second):
                    continue
                overlap_end = min(first.end, second.end)
                overlap_start = max(first.start, second.start)
                found.append(
                    Conflict(
                        first_id=first.event_id,
                        second_id=second.event_id,
                        first_subject=first.subject,
                        second_subject=second.subject,
                        overlap_minutes=int(
                            (overlap_end - overlap_start).total_seconds() // 60
                        ),
                    )
                )
        return found

    def unanswered_invitations(
        self, events: list[CalendarEvent] | None = None
    ) -> list[CalendarEvent]:
        """Events with no response recorded.

        Reported only. This component cannot accept or decline anything.
        """
        candidates = events if events is not None else self.events()
        return [
            event
            for event in candidates
            if event.response_status in ("none", "tentative")
        ]

    def day_brief(self, day: datetime | None = None) -> DayBrief:
        target = day or _utc_now()
        events = self.events_on(target)
        return DayBrief(
            date=target.astimezone(timezone.utc).date().isoformat(),
            events=[event.to_dict() for event in events],
            conflicts=[conflict.to_dict() for conflict in self.conflicts(events)],
            unanswered_invitations=[
                event.to_dict() for event in self.unanswered_invitations(events)
            ],
            first_start=to_iso(events[0].start) if events else None,
            last_end=to_iso(max(e.end for e in events)) if events else None,
        )

    # ---- email awareness ----------------------------------------------

    def unread(self) -> list[EmailMessage]:
        return [message for message in self.messages() if not message.is_read]

    def flagged(self, now: datetime | None = None) -> list[FlaggedMessage]:
        """Messages worth a look, with the reason each was noticed.

        The reasons are pattern matches on the subject and preview, plus
        unread state, importance, and age. This is noticing, not deciding.
        """
        moment = now or _utc_now()
        flags: list[FlaggedMessage] = []
        for message in self.messages():
            reasons: list[str] = []
            text = message.searchable_text
            for marker in DECISION_MARKERS:
                if marker in text:
                    reasons.append('contains "' + marker + '"')
            if message.importance == "high":
                reasons.append("marked high importance")
            if not message.is_read:
                reasons.append("unread")
            age = moment - message.received
            if age > timedelta(days=STALE_AFTER_DAYS):
                reasons.append("older than " + str(STALE_AFTER_DAYS) + " days")
            if not reasons:
                continue
            flags.append(
                FlaggedMessage(
                    message_id=message.message_id,
                    subject=message.subject,
                    sender=message.sender,
                    received=to_iso(message.received),
                    reasons=reasons,
                    is_read=message.is_read,
                    importance=message.importance,
                )
            )
        return flags

    def search_messages(self, query: str) -> list[EmailMessage]:
        needle = (query or "").strip().lower()
        if not needle:
            return []
        return [
            message
            for message in self.messages()
            if needle in message.searchable_text or needle in message.sender.lower()
        ]

    # ---- contact awareness --------------------------------------------

    def find_contacts(self, query: str) -> list[Contact]:
        needle = (query or "").strip().lower()
        if not needle:
            return []
        return [
            contact for contact in self.contacts() if needle in contact.searchable_text
        ]

    def contact_for_sender(self, sender: str) -> Contact | None:
        address = (sender or "").strip().lower()
        if not address:
            return None
        for contact in self.contacts():
            if contact.email.lower() == address:
                return contact
        return None

    # ---- status -------------------------------------------------------

    def status(self) -> dict:
        status = dict(self.provider.status())
        status.update(
            {
                "events": len(self.events()),
                "messages": len(self.messages()),
                "contacts": len(self.contacts()),
                "can_send": False,
                "can_reply": False,
                "can_schedule": False,
                "can_modify": False,
                "can_accept_or_decline": False,
                "has_approval_authority": False,
            }
        )
        return status
