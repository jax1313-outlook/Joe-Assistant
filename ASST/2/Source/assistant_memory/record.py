"""Retention record, states, and levels.

Sandbox doctrine, restated here so folder 2 stands alone:

- Every interaction begins TEMPORARY at Level 1.
- Default retention is three hours.
- If untouched at expiration the record is marked expired, its content is
  purged, and it leaves the active set. It is never promoted anywhere.
- Level 2, Level 3, and Print Ready stop expiration.
- Print is a state, not a level: it does not change interaction_level.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .clock import to_iso, from_iso

DEFAULT_RETENTION_HOURS = 3


class RetentionState:
    TEMPORARY = "TEMPORARY"
    SAVED = "SAVED"
    FORMAL = "FORMAL"
    PRINT_READY = "PRINT_READY"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"

    ALL = (TEMPORARY, SAVED, FORMAL, PRINT_READY, DELETED, EXPIRED)
    TERMINAL = (DELETED, EXPIRED)
    NON_EXPIRING = (SAVED, FORMAL, PRINT_READY)


# Rank prevents silent downgrades. It is not a claim about which level matters
# more to the operation.
STATE_RANK = {
    RetentionState.TEMPORARY: 0,
    RetentionState.SAVED: 1,
    RetentionState.PRINT_READY: 2,
    RetentionState.FORMAL: 3,
}


class InteractionLevel:
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"

    ALL = (LEVEL_1, LEVEL_2, LEVEL_3)


LEVEL_RANK = {
    InteractionLevel.LEVEL_1: 1,
    InteractionLevel.LEVEL_2: 2,
    InteractionLevel.LEVEL_3: 3,
}


RECORD_FIELDS = (
    "record_id",
    "created_at",
    "expires_at",
    "updated_at",
    "state",
    "interaction_level",
    "source_channel",
    "driver_request",
    "assistant_response",
    "related_load",
    "related_mission",
    "destination",
    "citations",
    "deletion_reason",
)

# Purged when a record is deleted or expires. Sandbox content is temporary by
# doctrine; keeping the text of an expired record would contradict that.
CONTENT_FIELDS = (
    "driver_request",
    "assistant_response",
    "citations",
)

LIST_FIELDS = ("citations",)


def new_record_id(created: datetime) -> str:
    return "MEM-{stamp}-{suffix}".format(
        stamp=created.strftime("%Y%m%d-%H%M%S"),
        suffix=uuid.uuid4().hex[:6].upper(),
    )


@dataclass
class MemoryRecord:
    record_id: str
    created_at: str
    expires_at: str | None
    updated_at: str
    state: str = RetentionState.TEMPORARY
    interaction_level: str = InteractionLevel.LEVEL_1
    source_channel: str = "local"
    driver_request: str | None = None
    assistant_response: str | None = None
    related_load: str | None = None
    related_mission: str | None = None
    destination: str | None = None
    citations: list[str] = field(default_factory=list)
    deletion_reason: str | None = None

    @classmethod
    def create(
        cls,
        now: datetime,
        driver_request: str,
        assistant_response: str | None = None,
        source_channel: str = "local",
        retention_hours: float = DEFAULT_RETENTION_HOURS,
        **extra: object,
    ) -> "MemoryRecord":
        record = cls(
            record_id=new_record_id(now),
            created_at=to_iso(now),
            expires_at=to_iso(now + timedelta(hours=retention_hours)),
            updated_at=to_iso(now),
            state=RetentionState.TEMPORARY,
            interaction_level=InteractionLevel.LEVEL_1,
            source_channel=source_channel,
            driver_request=driver_request,
            assistant_response=assistant_response,
        )
        for key, value in extra.items():
            if key not in RECORD_FIELDS:
                raise ValueError("unknown record field: " + str(key))
            setattr(record, key, value)
        return record

    # ---- serialization ------------------------------------------------

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in RECORD_FIELDS}

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryRecord":
        clean: dict = {}
        for name in RECORD_FIELDS:
            value = data.get(name)
            if name in LIST_FIELDS:
                value = list(value or [])
            clean[name] = value
        return cls(**clean)

    # ---- lifecycle ----------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        return self.state in RetentionState.TERMINAL

    def expires_moment(self) -> datetime | None:
        return from_iso(self.expires_at)

    def is_expired_at(self, now: datetime) -> bool:
        """Only TEMPORARY records ever expire."""
        if self.state != RetentionState.TEMPORARY:
            return False
        moment = self.expires_moment()
        if moment is None:
            return False
        return now >= moment

    def touch(self, now: datetime) -> None:
        self.updated_at = to_iso(now)

    def purge_content(self) -> None:
        for name in CONTENT_FIELDS:
            if name in LIST_FIELDS:
                setattr(self, name, [])
            else:
                setattr(self, name, None)
