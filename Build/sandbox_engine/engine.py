"""Sandbox Engine v1.

Deterministic lifecycle for temporary Assistant interaction records.

The engine does not send email, place calls, commit money, accept or
dispatch loads, contact Dispatch, or write into Company Library, Research
Library, or Archive. It has no network code of any kind.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .clock import Clock, SystemClock, to_iso
from .intents import CommandIntent, RecognizedCommand, recognize
from .records import (
    DEFAULT_RETENTION_HOURS,
    InteractionLevel,
    LEVEL_RANK,
    RecordState,
    STATE_RANK,
    SandboxRecord,
)
from .store import SandboxStore

REFERENCE_FIELDS = (
    "related_load",
    "related_mission",
    "related_customer",
    "related_broker",
    "destination",
)


class EngineError(RuntimeError):
    pass


@dataclass
class CommandResult:
    sandbox_id: str
    command: RecognizedCommand
    accepted: bool
    previous_state: str
    new_state: str
    previous_level: str
    new_level: str
    expires_at: str | None
    notice: str = ""
    changes: list[str] = field(default_factory=list)
    artifact_requests: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sandbox_id": self.sandbox_id,
            "command": self.command.to_dict(),
            "accepted": self.accepted,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "previous_level": self.previous_level,
            "new_level": self.new_level,
            "expires_at": self.expires_at,
            "notice": self.notice,
            "changes": list(self.changes),
            "artifact_requests": list(self.artifact_requests),
        }


class SandboxEngine:
    def __init__(
        self,
        store: SandboxStore | None = None,
        clock: Clock | None = None,
        retention_hours: float = DEFAULT_RETENTION_HOURS,
        project_root: str | Path | None = None,
    ) -> None:
        self.store = store or SandboxStore(project_root)
        self.clock = clock or SystemClock()
        self.retention_hours = retention_hours

    # ---- creation --------------------------------------------------------

    def create(
        self,
        driver_request: str,
        assistant_response: str | None = None,
        source_channel: str = "local_cli",
        **extra: object,
    ) -> SandboxRecord:
        """Every interaction begins TEMPORARY at Level 1."""
        now = self.clock.now()
        record = SandboxRecord.create(
            now=now,
            driver_request=driver_request,
            assistant_response=assistant_response,
            source_channel=source_channel,
            retention_hours=self.retention_hours,
            **extra,
        )
        self.store.save(record)
        return record

    # ---- reading ---------------------------------------------------------

    def get(self, sandbox_id: str) -> SandboxRecord:
        return self.store.load(sandbox_id)

    def list_active(
        self, state: str | None = None, sweep_first: bool = True
    ) -> list[SandboxRecord]:
        if sweep_first:
            self.sweep()
        return self.store.list_active(state=state)

    def list_expired(self) -> list[SandboxRecord]:
        return self.store.list_expired()

    def list_deleted(self) -> list[SandboxRecord]:
        return self.store.list_deleted()

    # ---- expiration ------------------------------------------------------

    def sweep(self, now: datetime | None = None) -> list[SandboxRecord]:
        """Expire every untouched TEMPORARY record whose time has come.

        Expired records are marked EXPIRED, their content is purged, and
        they leave the active Sandbox. They are never promoted anywhere.
        """
        moment = now or self.clock.now()
        expired: list[SandboxRecord] = []
        for record in self.store.list_active():
            if record.is_expired_at(moment):
                record.state = RecordState.EXPIRED
                record.purge_content()
                record.deletion_reason = (
                    "expired: untouched past three-hour Sandbox retention"
                )
                record.touch(moment)
                self.store.save(record)
                expired.append(record)
        return expired

    # ---- commands --------------------------------------------------------

    def apply_command(self, sandbox_id: str, text: str) -> CommandResult:
        now = self.clock.now()
        record = self.store.load(sandbox_id)

        if record.is_terminal:
            raise EngineError(
                sandbox_id
                + " is "
                + record.state
                + "; no further commands are accepted"
            )

        if record.is_expired_at(now):
            self.sweep(now)
            raise EngineError(
                sandbox_id
                + " expired at "
                + str(record.expires_at)
                + "; it left the active Sandbox and was not promoted"
            )

        command = recognize(text)
        previous_state = record.state
        previous_level = record.interaction_level
        changes: list[str] = []
        artifact_requests: list[dict] = []

        if command.intent == CommandIntent.NONE:
            return CommandResult(
                sandbox_id=record.sandbox_id,
                command=command,
                accepted=False,
                previous_state=previous_state,
                new_state=record.state,
                previous_level=previous_level,
                new_level=record.interaction_level,
                expires_at=record.expires_at,
                notice="No Sandbox command recognized. The record is unchanged.",
            )

        if command.intent == CommandIntent.LEVEL_1:
            notice = self._apply_level_1(record, now, changes)
        elif command.intent == CommandIntent.DELETE:
            notice = self._apply_delete(record, command, changes)
        elif command.intent == CommandIntent.LEVEL_2:
            notice = self._apply_level_2(record, command, changes)
        elif command.intent == CommandIntent.LEVEL_3:
            notice = self._apply_level_3(record, command, now, changes, artifact_requests)
        elif command.intent == CommandIntent.PRINT:
            notice = self._apply_print(record, command, now, changes, artifact_requests)
        else:  # pragma: no cover - CommandIntent is a closed set
            raise EngineError("unhandled intent: " + command.intent)

        # A print request rides along with Level 2 / Level 3 when both
        # appear in the same sentence.
        if command.print_requested and command.intent in (
            CommandIntent.LEVEL_2,
            CommandIntent.LEVEL_3,
        ):
            artifact_requests.append(
                self._create_artifact_request(record, "PRINT_READY", now)
            )
            changes.append("print-ready artifact request created alongside the command")

        record.touch(now)
        self.store.save(record)

        return CommandResult(
            sandbox_id=record.sandbox_id,
            command=command,
            accepted=True,
            previous_state=previous_state,
            new_state=record.state,
            previous_level=previous_level,
            new_level=record.interaction_level,
            expires_at=record.expires_at,
            notice=notice,
            changes=changes,
            artifact_requests=artifact_requests,
        )

    # ---- per-intent handlers --------------------------------------------

    def _apply_level_1(
        self, record: SandboxRecord, now: datetime, changes: list[str]
    ) -> str:
        if record.state != RecordState.TEMPORARY:
            raise EngineError(
                record.sandbox_id
                + " is "
                + record.state
                + "; Level 1 will not downgrade a record that is already preserved"
            )
        expires = now + timedelta(hours=self.retention_hours)
        record.expires_at = to_iso(expires)
        record.interaction_level = InteractionLevel.LEVEL_1
        changes.append("three-hour expiration set to " + str(record.expires_at))
        return "Held in the Sandbox. This will expire unless saved."

    def _apply_level_2(
        self, record: SandboxRecord, command: RecognizedCommand, changes: list[str]
    ) -> str:
        self._apply_references(record, command, changes)
        self._raise_level(record, InteractionLevel.LEVEL_2, changes)
        self._raise_state(record, RecordState.SAVED, changes)
        self._stop_expiration(record, changes)
        where = record.destination or record.related_load or record.related_mission
        if where:
            return "Kept for parked review under " + where + "."
        return "Kept for parked review."

    def _apply_level_3(
        self,
        record: SandboxRecord,
        command: RecognizedCommand,
        now: datetime,
        changes: list[str],
        artifact_requests: list[dict],
    ) -> str:
        self._apply_references(record, command, changes)
        self._raise_level(record, InteractionLevel.LEVEL_3, changes)
        self._raise_state(record, RecordState.FORMAL, changes)
        self._stop_expiration(record, changes)
        artifact_requests.append(
            self._create_artifact_request(record, "FORMAL_REPORT", now)
        )
        changes.append("formal-artifact request created")
        if record.destination:
            return (
                "Formal work-product requested under "
                + record.destination
                + ". Not yet produced."
            )
        return "Formal work-product requested. Not yet produced."

    def _apply_print(
        self,
        record: SandboxRecord,
        command: RecognizedCommand,
        now: datetime,
        changes: list[str],
        artifact_requests: list[dict],
    ) -> str:
        # Doctrine C4, ruled by Mike Zachary: Print does NOT raise the
        # interaction level. Print is a state, not a level. A Level 1 record
        # that is printed reads LEVEL_1 / PRINT_READY.
        # Do not add a _raise_level call here without a new ruling.
        # Locked by test_print_does_not_raise_the_interaction_level.
        self._apply_references(record, command, changes)
        self._raise_state(record, RecordState.PRINT_READY, changes)
        self._stop_expiration(record, changes)
        changes.append("interaction_level unchanged at " + record.interaction_level)
        artifact_requests.append(
            self._create_artifact_request(record, "PRINT_READY", now)
        )
        changes.append("print-ready artifact request created")
        return (
            "Print-ready artifact requested and held for review. "
            "No printer was contacted and nothing was physically printed."
        )

    def _apply_delete(
        self, record: SandboxRecord, command: RecognizedCommand, changes: list[str]
    ) -> str:
        record.state = RecordState.DELETED
        record.purge_content()
        record.expires_at = None
        record.deletion_reason = "driver command: " + command.raw_text
        changes.append("record content purged; tombstone retained for audit")
        changes.append("record removed from the active Sandbox; not promoted anywhere")
        return "Deleted from the Sandbox. It was not promoted anywhere."

    # ---- shared mutations ------------------------------------------------

    def _apply_references(
        self, record: SandboxRecord, command: RecognizedCommand, changes: list[str]
    ) -> None:
        refs = command.references
        for name in REFERENCE_FIELDS:
            value = refs.get(name)
            if value and getattr(record, name) != value:
                setattr(record, name, value)
                changes.append(name + " = " + str(value))
        org = refs.get("load_organization")
        if org and record.destination and org.lower() not in record.destination.lower():
            record.destination = org + " " + record.destination
            changes.append("destination = " + record.destination)

    def _raise_state(self, record: SandboxRecord, target: str, changes: list[str]) -> None:
        current_rank = STATE_RANK.get(record.state, 0)
        if STATE_RANK[target] > current_rank:
            record.state = target
            changes.append("state = " + target)
        else:
            changes.append("state unchanged at " + record.state + " (no downgrade)")

    def _raise_level(self, record: SandboxRecord, target: str, changes: list[str]) -> None:
        if LEVEL_RANK[target] > LEVEL_RANK.get(record.interaction_level, 0):
            record.interaction_level = target
            changes.append("interaction_level = " + target)

    def _stop_expiration(self, record: SandboxRecord, changes: list[str]) -> None:
        if record.expires_at is not None:
            record.expires_at = None
            changes.append("expiration cleared; this record no longer expires")

    # ---- artifact requests -----------------------------------------------

    def _create_artifact_request(
        self, record: SandboxRecord, kind: str, now: datetime
    ) -> dict:
        request_id = "AR-" + now.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()
        request = {
            "artifact_request_id": request_id,
            "requested_at": to_iso(now),
            "sandbox_id": record.sandbox_id,
            "artifact_kind": kind,
            "status": "REQUESTED_NOT_PRODUCED",
            "produced": False,
            "physical_print_performed": False,
            "destination": record.destination,
            "related_load": record.related_load,
            "related_mission": record.related_mission,
            "related_customer": record.related_customer,
            "related_broker": record.related_broker,
            "interaction_level": record.interaction_level,
            "driver_request": record.driver_request,
            "research_scope": record.research_scope,
            "sources_consulted": list(record.sources_consulted),
            "citations": list(record.citations),
            "key_findings": list(record.key_findings),
            "uncertainty": record.uncertainty,
            "assistant_recommendation": record.assistant_recommendation,
            "notes": (
                "This is a request only. Sandbox Engine v1 does not produce the "
                "finished artifact, does not route it into Dispatch, Company Library, "
                "Research Library, or Archive, and does not operate a printer."
            ),
        }
        self.store.write_artifact_request(request, artifact_request_markdown(request))
        return request


def artifact_request_markdown(request: dict) -> str:
    def line(label, value):
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value) if value else "(none recorded)"
        if value in (None, ""):
            value = "(none recorded)"
        return "- **" + label + ":** " + str(value)

    if request["artifact_kind"] == "FORMAL_REPORT":
        kind_title = "Formal Artifact Request"
    else:
        kind_title = "Print-Ready Artifact Request"

    return "\n".join(
        [
            "# " + kind_title,
            "",
            "**Request ID:** " + request["artifact_request_id"],
            "**Requested at:** " + str(request["requested_at"]),
            "**Status:** " + request["status"],
            "",
            "## Status statement",
            "",
            "This artifact has **not** been produced. Nothing was printed. Nothing was "
            "routed into Dispatch, Company Library, Research Library, or Archive. "
            "Mike Zachary remains final authority.",
            "",
            "## Source record",
            "",
            line("Sandbox ID", request["sandbox_id"]),
            line("Interaction level", request["interaction_level"]),
            line("Driver request", request["driver_request"]),
            "",
            "## Requested destination and references",
            "",
            line("Destination", request["destination"]),
            line("Related load", request["related_load"]),
            line("Related mission", request["related_mission"]),
            line("Related customer", request["related_customer"]),
            line("Related broker", request["related_broker"]),
            "",
            "## Research material carried forward",
            "",
            line("Research scope", request["research_scope"]),
            line("Sources consulted", request["sources_consulted"]),
            line("Citations", request["citations"]),
            line("Key findings", request["key_findings"]),
            line("Uncertainty", request["uncertainty"]),
            line("Assistant recommendation", request["assistant_recommendation"]),
            "",
            "## Note",
            "",
            request["notes"],
            "",
        ]
    )
