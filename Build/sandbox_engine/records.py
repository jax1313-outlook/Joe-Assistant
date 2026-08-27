"""Sandbox record model, states, and levels.

The field list is fixed by the mission. Nothing here talks to a network,
a vendor SDK, or a production system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

from .clock import to_iso, from_iso

DEFAULT_RETENTION_HOURS = 3


class RecordState:
    TEMPORARY = "TEMPORARY"
    SAVED = "SAVED"
    FORMAL = "FORMAL"
    PRINT_READY = "PRINT_READY"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"

    ALL = (TEMPORARY, SAVED, FORMAL, PRINT_READY, DELETED, EXPIRED)
    TERMINAL = (DELETED, EXPIRED)
    NON_EXPIRING = (SAVED, FORMAL, PRINT_READY)


# Rank exists only to prevent silent downgrades. It is not a doctrine
# statement about which level matters more.
STATE_RANK = {
    RecordState.TEMPORARY: 0,
    RecordState.SAVED: 1,
    RecordState.PRINT_READY: 2,
    RecordState.FORMAL: 3,
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
    "sandbox_id",
    "created_at",
    "expires_at",
    "updated_at",
    "state",
    "interaction_level",
    "source_channel",
    "driver_request",
    "assistant_response",
    "research_scope",
    "sources_consulted",
    "key_findings",
    "operational_consequences",
    "uncertainty",
    "assistant_recommendation",
    "driver_decision",
    "drafts_created",
    "actions_completed",
    "actions_awaiting_approval",
    "related_load",
    "related_mission",
    "related_customer",
    "related_broker",
    "destination",
    "citations",
    "deletion_reason",
)

# Fields purged when a record is deleted or expires. Sandbox content is
# temporary by doctrine; a tombstone keeps the lifecycle auditable
# without keeping the material itself.
CONTENT_FIELDS = (
    "driver_request",
    "assistant_response",
    "research_scope",
    "sources_consulted",
    "key_findings",
    "operational_consequences",
    "uncertainty",
    "assistant_recommendation",
    "driver_decision",
    "drafts_created",
    "actions_completed",
    "actions_awaiting_approval",
    "citations",
)

LIST_FIELDS = (
    "sources_consulted",
    "key_findings",
    "operational_consequences",
    "drafts_created",
    "actions_completed",
    "actions_awaiting_approval",
    "citations",
)


def new_sandbox_id(created: datetime) -> str:
    return "SBX-{stamp}-{suffix}".format(
        stamp=created.strftime("%Y%m%d-%H%M%S"),
        suffix=uuid.uuid4().hex[:6].upper(),
    )


@dataclass
class SandboxRecord:
    sandbox_id: str
    created_at: str
    expires_at: str | None
    updated_at: str
    state: str = RecordState.TEMPORARY
    interaction_level: str = InteractionLevel.LEVEL_1
    source_channel: str = "local_cli"
    driver_request: str | None = None
    assistant_response: str | None = None
    research_scope: str | None = None
    sources_consulted: list[str] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    operational_consequences: list[str] = field(default_factory=list)
    uncertainty: str | None = None
    assistant_recommendation: str | None = None
    driver_decision: str | None = None
    drafts_created: list[str] = field(default_factory=list)
    actions_completed: list[str] = field(default_factory=list)
    actions_awaiting_approval: list[str] = field(default_factory=list)
    related_load: str | None = None
    related_mission: str | None = None
    related_customer: str | None = None
    related_broker: str | None = None
    destination: str | None = None
    citations: list[str] = field(default_factory=list)
    deletion_reason: str | None = None

    # ---- construction -------------------------------------------------

    @classmethod
    def create(
        cls,
        now: datetime,
        driver_request: str,
        assistant_response: str | None = None,
        source_channel: str = "local_cli",
        retention_hours: float = DEFAULT_RETENTION_HOURS,
        **extra: object,
    ) -> "SandboxRecord":
        expires = now + timedelta(hours=retention_hours)
        record = cls(
            sandbox_id=new_sandbox_id(now),
            created_at=to_iso(now),
            expires_at=to_iso(expires),
            updated_at=to_iso(now),
            state=RecordState.TEMPORARY,
            interaction_level=InteractionLevel.LEVEL_1,
            source_channel=source_channel,
            driver_request=driver_request,
            assistant_response=assistant_response,
        )
        for key, value in extra.items():
            if key not in RECORD_FIELDS:
                raise ValueError(f"unknown record field: {key}")
            setattr(record, key, value)
        return record

    # ---- serialization ------------------------------------------------

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in RECORD_FIELDS}

    @classmethod
    def from_dict(cls, data: dict) -> "SandboxRecord":
        clean: dict = {}
        for name in RECORD_FIELDS:
            value = data.get(name)
            if name in LIST_FIELDS:
                value = list(value or [])
            clean[name] = value
        return cls(**clean)

    # ---- lifecycle helpers --------------------------------------------

    @property
    def is_terminal(self) -> bool:
        return self.state in RecordState.TERMINAL

    def expires_moment(self) -> datetime | None:
        return from_iso(self.expires_at)

    def is_expired_at(self, now: datetime) -> bool:
        """Only TEMPORARY records ever expire."""
        if self.state != RecordState.TEMPORARY:
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

    def as_json_dict(self) -> dict:
        return asdict(self)
