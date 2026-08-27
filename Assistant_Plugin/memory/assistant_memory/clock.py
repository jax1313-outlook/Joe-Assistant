"""Injectable clock.

Retention has to be provable without waiting three real hours, so every time
reading in this component goes through a Clock. Production uses SystemClock;
tests and the operator's simulation use FixedClock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(moment: datetime | None) -> str | None:
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
    def now(self) -> datetime:  # pragma: no cover - interface
        raise NotImplementedError


class SystemClock(Clock):
    """Real wall-clock time, always UTC."""

    def now(self) -> datetime:
        return utc_now()


class FixedClock(Clock):
    """Controllable clock for simulating elapsed time."""

    def __init__(self, start: datetime | None = None) -> None:
        moment = start or utc_now()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        self._now = moment.astimezone(timezone.utc)

    def now(self) -> datetime:
        return self._now

    def advance(self, hours: float = 0.0, minutes: float = 0.0, seconds: float = 0.0) -> datetime:
        self._now = self._now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return self._now
