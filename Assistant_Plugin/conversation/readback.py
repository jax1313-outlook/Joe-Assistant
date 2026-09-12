"""The read-back contract: what Joe says out loud, and in what order.

`DRIVER_FIRST_DOCTRINE_v2` D2, the 70 MPH Test:

    "Can the driver obtain the needed information within seconds during
    real-world operations? If the answer is no, redesign the feature."

The driver is moving, is tired, and has one hand. Three consequences shape every
sentence this module produces:

**The most important fact comes first**, because a sentence heard at speed is
often only half heard. "Delivery is tomorrow at 14:00 in Dallas" survives being
cut off. "For load LD-4471, which is currently in transit, the delivery is..."
does not.

**There is no list.** A list is a thing you scan, and scanning is a thing you do
with your eyes on a screen. Where several facts are needed they are joined into
one spoken sentence with the count stated first, so the driver knows how long it
will be before it starts.

**A missing fact is said, not skipped.** Silence about the delivery time is
indistinguishable from there being no appointment, and a driver who assumes the
wrong one of those loses a load. Every unknown is named in the sentence and
returned separately so a screen can show it too.

Times are spoken in the operator's own zone with the day named, never as an ISO
string and never as a bare hour -- "tomorrow at 14:00" is safe; "14:00" is not,
because the driver does not know whether it is today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

#: What a driver asks for, and the one fact that answers it.
ASPECTS = ("next", "delivery", "pickup", "where", "when", "customer", "status", "everything")


@dataclass
class SpokenAnswer:
    text: str
    aspect: str
    unknown: tuple[str, ...] = ()
    facts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"text": self.text, "aspect": self.aspect,
                "unknown": list(self.unknown), "facts": dict(self.facts)}



def _time_helpers():
    """Dispatch's normaliser when it is installed; a local one when it is not.

    Joe is a plug-in and must run standalone (THE MIKE RULE, and CLAUDE.md 5.4:
    Dispatch runs without the plug-ins, and the plug-ins are not to be welded
    in). Falling back to printing the raw ISO string would have been the easy
    option and it fails the 70 MPH Test outright -- "2026-09-13T14:00:00-04:00"
    spoken aloud is not an answer a driver can use. So the fallback parses,
    rather than giving up and reading out the storage format.
    """
    try:
        from dispatch.timestamps import normalize, operating_timezone  # type: ignore

        return normalize, operating_timezone
    except ImportError:
        return _local_normalize, _local_zone


_LOCAL_FORMATS = (
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M %p", "%m/%d/%Y",
)


def _local_zone():
    import os

    name = os.environ.get("DISPATCH_OPERATING_TIMEZONE", "America/New_York")
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - a missing tzdata is a deployment fact
        return timezone.utc


def _local_normalize(value):
    text = str(value or "").strip()
    if not text:
        return {"instant": None}
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is not None:
            return {"instant": parsed}
    except ValueError:
        parsed = None
    for fmt in _LOCAL_FORMATS:
        try:
            naive = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return {"instant": naive.replace(tzinfo=_local_zone())}
    return {"instant": None}


def _spoken_time(raw: str | None, *, now: datetime | None = None) -> tuple[str, bool]:
    """A time a person can act on, and whether it was known at all.

    Relative where relative is unambiguous ("today", "tomorrow"), absolute
    beyond that. A bare "14:00" is the dangerous case: it sounds precise and
    does not say which day.
    """
    if not raw:
        return "", False
    normalize, operating_timezone = _time_helpers()
    result = normalize(raw)
    instant = result["instant"]
    if instant is None:
        # Kept, not dropped. Somebody wrote it for a reason, and a driver can
        # make sense of "whenever they call" where this module cannot.
        return str(raw), True

    zone = operating_timezone()
    local = instant.astimezone(zone)
    reference = (now or datetime.now(timezone.utc)).astimezone(zone)
    days = (local.date() - reference.date()).days
    clock = local.strftime("%H:%M")
    if days == 0:
        return f"today at {clock}", True
    if days == 1:
        return f"tomorrow at {clock}", True
    if days == -1:
        return f"yesterday at {clock}", True
    if 1 < days <= 6:
        return f"{local.strftime('%A')} at {clock}", True
    return f"{local.strftime('%-d %B')} at {clock}" if hasattr(local, "strftime") else clock, True


def _place(value: str | None) -> str:
    return (value or "").strip()


def read_back_load(load: dict, *, aspect: str = "", now: datetime | None = None) -> SpokenAnswer:
    """One sentence, shortest useful answer first."""
    aspect = (aspect or "next").strip().lower()
    if aspect not in ASPECTS:
        aspect = "next"

    delivery_text, delivery_known = _spoken_time(load.get("delivery_datetime"), now=now)
    pickup_text, pickup_known = _spoken_time(load.get("pickup_datetime"), now=now)
    pickup_place = _place(load.get("pickup_location"))
    delivery_place = _place(load.get("delivery_location"))
    status = (load.get("status") or "").replace("_", " ")
    customer = _place(load.get("customer"))

    unknown: list[str] = []
    if not delivery_known:
        unknown.append("delivery time")
    if not pickup_known:
        unknown.append("pickup time")
    if not delivery_place:
        unknown.append("delivery location")
    if not pickup_place:
        unknown.append("pickup location")

    facts = {
        "status": status, "customer": customer,
        "pickup_place": pickup_place, "delivery_place": delivery_place,
        "pickup_time": pickup_text, "delivery_time": delivery_text,
    }

    def missing(label: str) -> str:
        return f"The {label} is not on file."

    if aspect in ("delivery", "when"):
        if not delivery_known:
            return SpokenAnswer(missing("delivery time"), aspect, tuple(unknown), facts)
        where = f" in {delivery_place}" if delivery_place else ""
        return SpokenAnswer(f"Delivery is {delivery_text}{where}.", aspect, tuple(unknown), facts)

    if aspect == "pickup":
        if not pickup_known:
            return SpokenAnswer(missing("pickup time"), aspect, tuple(unknown), facts)
        where = f" in {pickup_place}" if pickup_place else ""
        return SpokenAnswer(f"Pickup is {pickup_text}{where}.", aspect, tuple(unknown), facts)

    if aspect == "where":
        if not delivery_place:
            return SpokenAnswer(missing("delivery location"), aspect, tuple(unknown), facts)
        return SpokenAnswer(f"You're going to {delivery_place}.", aspect, tuple(unknown), facts)

    if aspect == "customer":
        if not customer:
            return SpokenAnswer(missing("customer"), aspect, tuple(unknown), facts)
        return SpokenAnswer(f"The customer is {customer}.", aspect, tuple(unknown), facts)

    if aspect == "status":
        if not status:
            return SpokenAnswer(missing("status"), aspect, tuple(unknown), facts)
        return SpokenAnswer(f"The load is {status}.", aspect, tuple(unknown), facts)

    if aspect == "everything":
        # The count comes first so the driver knows how long this is before it
        # starts. Still one sentence -- a list is a thing you scan.
        parts = []
        if customer:
            parts.append(f"customer {customer}")
        if pickup_place and pickup_known:
            parts.append(f"pickup {pickup_text} in {pickup_place}")
        if delivery_place and delivery_known:
            parts.append(f"delivery {delivery_text} in {delivery_place}")
        if status:
            parts.append(f"status {status}")
        if not parts:
            return SpokenAnswer("Nothing is on file for this load.", aspect, tuple(unknown), facts)
        body = "; ".join(parts)
        tail = f" Not on file: {', '.join(unknown)}." if unknown else ""
        return SpokenAnswer(f"{len(parts)} things. {body}.{tail}", aspect, tuple(unknown), facts)

    # "next" -- the default, and the one a driver actually asks.
    if delivery_known and delivery_place:
        sentence = f"Next is delivery {delivery_text} in {delivery_place}."
    elif pickup_known and pickup_place:
        sentence = f"Next is pickup {pickup_text} in {pickup_place}."
    elif delivery_place:
        sentence = f"Next is delivery in {delivery_place}. The time is not on file."
    elif pickup_place:
        sentence = f"Next is pickup in {pickup_place}. The time is not on file."
    else:
        sentence = "Nothing about the next stop is on file for this load."
    return SpokenAnswer(sentence, aspect, tuple(unknown), facts)
