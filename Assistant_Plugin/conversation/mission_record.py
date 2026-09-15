"""Joe reading the Mission Record — a retrieval contract, and only retrieval.

`DRIVER_FIRST_DOCTRINE_v2` D9: **Retrieval Is Not Modification.** Reading
something must never change it. D5: the portal is a window; it does not hold a
second copy of state. Both apply to Joe with more force than to a screen,
because a voice assistant that "helpfully" updates a record while answering a
question about it produces a change nobody can point at afterwards.

So this module offers a read port and nothing else. There is no write method to
call by mistake, no cache that could answer with something stale, and the reader
it wraps is injected -- Joe holds no database handle of his own, which is what
makes "Joe cannot write to Dispatch" a property of the code rather than a
promise in a document.

`MissionRecord` is the shape Joe reasons over: one load, its current state, its
appointments, its open exceptions, and what is *not* known about it. That last
field is the one that matters. An assistant that answers only from what it has
will confidently describe a load with no delivery appointment as though the
appointment were simply not mentioned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class DispatchReader(Protocol):
    """The read surface Joe is given. Deliberately has no write methods."""

    def get_load(self, load_id: str) -> dict | None: ...
    def list_milestones(self, load_id: str) -> list: ...
    def list_exceptions(self, load_id: str) -> list: ...
    def get_driver(self, driver_id: str) -> dict | None: ...


@dataclass(frozen=True)
class MissionRecord:
    """Everything Joe may reason over about one load, including the gaps."""

    load_id: str
    load: dict
    status: str
    last_milestone: str = ""
    open_exceptions: tuple = ()
    driver_name: str = ""
    #: Field names that are empty. Carried explicitly so an answer can say "not
    #: on file" instead of describing an absence as though it were fine.
    unknown: tuple = ()
    retrieved_at: str = ""

    def to_dict(self) -> dict:
        return {
            "load_id": self.load_id, "status": self.status,
            "last_milestone": self.last_milestone,
            "open_exceptions": list(self.open_exceptions),
            "driver_name": self.driver_name, "unknown": list(self.unknown),
            "retrieved_at": self.retrieved_at,
        }

    def context_for_reasoning(self) -> str:
        """What a reasoning provider is allowed to see, as plain text.

        Narrow on purpose. A provider handed the whole record will answer from
        anything in it, including fields nobody asked about -- and one of them
        is a driver's phone number.
        """
        lines = [f"Load {self.load_id}", f"Status: {self.status or 'unknown'}"]
        for key in ("customer", "pickup_location", "delivery_location",
                    "pickup_datetime", "delivery_datetime", "equipment"):
            value = self.load.get(key)
            if value:
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        if self.last_milestone:
            lines.append(f"Last reported: {self.last_milestone}")
        if self.open_exceptions:
            lines.append(f"Open exceptions: {', '.join(self.open_exceptions)}")
        if self.unknown:
            lines.append(f"NOT ON FILE: {', '.join(self.unknown)}")
        return "\n".join(lines)


#: The fields a driver asks about. Absence of any of them is stated, never
#: glossed over.
EXPECTED_FIELDS = (
    "customer", "pickup_location", "delivery_location",
    "pickup_datetime", "delivery_datetime",
)


class MissionRecordRetrieval:
    """The only way Joe reaches Dispatch. Read, and nothing else.

    Every call is a fresh read. There is no cache, because a cached answer to
    "where am I going" is the one kind of stale that gets somebody sent to the
    wrong dock.
    """

    def __init__(self, reader: DispatchReader | None = None):
        self._reader = reader

    @property
    def available(self) -> bool:
        return self._reader is not None

    def status(self) -> str:
        return "LIVE" if self._reader is not None else "UNCONFIGURED"

    def retrieve(self, load_id: str) -> MissionRecord | None:
        if self._reader is None or not load_id:
            return None
        load = self._reader.get_load(load_id)
        if not load:
            return None

        milestones = self._reader.list_milestones(load_id) or []
        last = milestones[-1].get("event_type", "") if milestones else ""
        exceptions = tuple(
            e.get("exception_type", "") for e in (self._reader.list_exceptions(load_id) or [])
            if e.get("status") == "open"
        )
        driver_name = ""
        if load.get("driver_id"):
            driver = self._reader.get_driver(load["driver_id"])
            driver_name = (driver or {}).get("name", "")

        unknown = tuple(
            name.replace("_", " ") for name in EXPECTED_FIELDS if not load.get(name)
        )

        from datetime import datetime, timezone

        return MissionRecord(
            load_id=load_id,
            load=dict(load),
            status=load.get("status", ""),
            last_milestone=last,
            open_exceptions=exceptions,
            driver_name=driver_name,
            unknown=unknown,
            retrieved_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
