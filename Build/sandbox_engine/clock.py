"""Injectable clock.

Expiration must be provable without waiting three real hours, so every
time reading in the engine goes through a Clock. Production uses
SystemClock; tests and the proof script use FixedClock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(moment: datetime | None) -> str | None:
    """UTC ISO-8601 with a trailing Z. None passes through."""
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def from_iso(text: str | None) -> datetime | None:
    if text is None:
        return None
    cleaned = text.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class Clock:
    """Base clock interface."""

    def now(self) -> datetime:  # pragma: no cover - interface only
        raise NotImplementedError


class SystemClock(Clock):
    """Real wall-clock time, always UTC."""

    def now(self) -> datetime:
        return utc_now()


class FixedClock(Clock):
    """Controllable clock for simulating the passage of time.

    Nothing outside tests and the proof script should construct this.
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or utc_now()
        if self._now.tzinfo is None:
            self._now = self._now.replace(tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, hours: float = 0.0, minutes: float = 0.0, seconds: float = 0.0) -> datetime:
        self._now = self._now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return self._now

    def set(self, moment: datetime) -> datetime:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        self._now = moment.astimezone(timezone.utc)
        return self._now
