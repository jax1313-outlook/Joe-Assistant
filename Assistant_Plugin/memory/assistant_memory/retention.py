"""Retention engine.

Deterministic lifecycle for temporary interaction records: Level 1, Level 2,
Level 3, Print Ready, Delete, Expiration.

This component holds records. It does not route them anywhere, produce
artifacts, print, send anything, or contact any system. It has no network code
and no knowledge of any other workstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .clock import Clock, SystemClock, to_iso
from .record import (
    DEFAULT_RETENTION_HOURS,
    InteractionLevel,
    LEVEL_RANK,
    MemoryRecord,
    RetentionState,
    STATE_RANK,
)
from .store import MemoryStore


class RetentionError(RuntimeError):
    pass


class Operation:
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    PRINT_READY = "PRINT_READY"
    DELETE = "DELETE"

    ALL = (LEVEL_1, LEVEL_2, LEVEL_3, PRINT_READY, DELETE)


@dataclass
class OperationResult:
    record_id: str
    operation: str
    previous_state: str
    new_state: str
    previous_level: str
    new_level: str
    expires_at: str | None
    notice: str = ""
    changes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "operation": self.operation,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "previous_level": self.previous_level,
            "new_level": self.new_level,
            "expires_at": self.expires_at,
            "notice": self.notice,
            "changes": list(self.changes),
        }


class RetentionEngine:
    def __init__(
        self,
        store: MemoryStore | None = None,
        clock: Clock | None = None,
        retention_hours: float = DEFAULT_RETENTION_HOURS,
        folder_root: str | Path | None = None,
    ) -> None:
        self.store = store or MemoryStore(folder_root)
        self.clock = clock or SystemClock()
        self.retention_hours = retention_hours

    # ---- creation -----------------------------------------------------

    def create(
        self,
        driver_request: str,
        assistant_response: str | None = None,
        source_channel: str = "local",
        **extra: object,
    ) -> MemoryRecord:
        """Every interaction begins TEMPORARY at Level 1."""
        now = self.clock.now()
        record = MemoryRecord.create(
            now=now,
            driver_request=driver_request,
            assistant_response=assistant_response,
            source_channel=source_channel,
            retention_hours=self.retention_hours,
            **extra,
        )
        self.store.save(record)
        return record

    # ---- reading ------------------------------------------------------

    def get(self, record_id: str) -> MemoryRecord:
        return self.store.load(record_id)

    def list_active(self, state: str | None = None, sweep_first: bool = True):
        if sweep_first:
            self.sweep()
        return self.store.list_active(state=state)

    def list_expired(self):
        return self.store.list_expired()

    def list_deleted(self):
        return self.store.list_deleted()

    # ---- expiration ---------------------------------------------------

    def sweep(self, now: datetime | None = None) -> list[MemoryRecord]:
        """Expire every untouched TEMPORARY record whose time has come.

        Expired records are marked EXPIRED, their content is purged, and they
        leave the active set. They are never promoted anywhere.
        """
        moment = now or self.clock.now()
        expired: list[MemoryRecord] = []
        for record in self.store.list_active():
            if record.is_expired_at(moment):
                record.state = RetentionState.EXPIRED
                record.purge_content()
                record.deletion_reason = (
                    "expired: untouched past three-hour retention"
                )
                record.touch(moment)
                self.store.save(record)
                expired.append(record)
        return expired

    # ---- operations ---------------------------------------------------

    def apply(self, record_id: str, operation: str, **options) -> OperationResult:
        if operation not in Operation.ALL:
            raise RetentionError("unknown operation: " + str(operation))

        now = self.clock.now()
        record = self.store.load(record_id)

        if record.is_terminal:
            raise RetentionError(
                record_id + " is " + record.state + "; no further operations are accepted"
            )
        if record.is_expired_at(now):
            self.sweep(now)
            raise RetentionError(
                record_id
                + " expired at "
                + str(record.expires_at)
                + "; it left the active set and was not promoted"
            )

        previous_state = record.state
        previous_level = record.interaction_level
        changes: list[str] = []

        if operation == Operation.LEVEL_1:
            notice = self._level_1(record, now, changes)
        elif operation == Operation.LEVEL_2:
            notice = self._level_2(record, changes, options)
        elif operation == Operation.LEVEL_3:
            notice = self._level_3(record, changes, options)
        elif operation == Operation.PRINT_READY:
            notice = self._print_ready(record, changes, options)
        else:
            notice = self._delete(record, changes, options)

        record.touch(now)
        self.store.save(record)

        return OperationResult(
            record_id=record.record_id,
            operation=operation,
            previous_state=previous_state,
            new_state=record.state,
            previous_level=previous_level,
            new_level=record.interaction_level,
            expires_at=record.expires_at,
            notice=notice,
            changes=changes,
        )

    # convenience wrappers
    def level_1(self, record_id: str) -> OperationResult:
        return self.apply(record_id, Operation.LEVEL_1)

    def level_2(self, record_id: str, **options) -> OperationResult:
        return self.apply(record_id, Operation.LEVEL_2, **options)

    def level_3(self, record_id: str, **options) -> OperationResult:
        return self.apply(record_id, Operation.LEVEL_3, **options)

    def print_ready(self, record_id: str, **options) -> OperationResult:
        return self.apply(record_id, Operation.PRINT_READY, **options)

    def delete(self, record_id: str, reason: str | None = None) -> OperationResult:
        return self.apply(record_id, Operation.DELETE, reason=reason)

    # ---- per-operation ------------------------------------------------

    def _level_1(self, record: MemoryRecord, now: datetime, changes: list[str]) -> str:
        if record.state != RetentionState.TEMPORARY:
            raise RetentionError(
                record.record_id
                + " is "
                + record.state
                + "; Level 1 will not downgrade a record that is already preserved"
            )
        record.expires_at = to_iso(now + timedelta(hours=self.retention_hours))
        record.interaction_level = InteractionLevel.LEVEL_1
        changes.append("three-hour expiration set to " + str(record.expires_at))
        return "Held temporarily. This will expire unless preserved."

    def _level_2(self, record: MemoryRecord, changes: list[str], options: dict) -> str:
        self._apply_references(record, changes, options)
        self._raise_level(record, InteractionLevel.LEVEL_2, changes)
        self._raise_state(record, RetentionState.SAVED, changes)
        self._stop_expiration(record, changes)
        where = record.destination or record.related_load or record.related_mission
        if where:
            return "Kept for parked review under " + where + "."
        return "Kept for parked review."

    def _level_3(self, record: MemoryRecord, changes: list[str], options: dict) -> str:
        self._apply_references(record, changes, options)
        self._raise_level(record, InteractionLevel.LEVEL_3, changes)
        self._raise_state(record, RetentionState.FORMAL, changes)
        self._stop_expiration(record, changes)
        if record.destination:
            return (
                "Marked formal under "
                + record.destination
                + ". No work product was produced."
            )
        return "Marked formal. No work product was produced."

    def _print_ready(self, record: MemoryRecord, changes: list[str], options: dict) -> str:
        # Doctrine: Print is a state, not a level. It does NOT raise
        # interaction_level. Do not add a _raise_level call here.
        self._apply_references(record, changes, options)
        self._raise_state(record, RetentionState.PRINT_READY, changes)
        self._stop_expiration(record, changes)
        changes.append("interaction_level unchanged at " + record.interaction_level)
        return (
            "Marked print ready and held. No printer was contacted and nothing "
            "was physically printed."
        )

    def _delete(self, record: MemoryRecord, changes: list[str], options: dict) -> str:
        reason = options.get("reason") or "deleted by operator"
        record.state = RetentionState.DELETED
        record.purge_content()
        record.expires_at = None
        record.deletion_reason = str(reason)
        changes.append("record content purged; tombstone retained for audit")
        changes.append("record removed from the active set; not promoted anywhere")
        return "Deleted. It was not promoted anywhere."

    # ---- shared -------------------------------------------------------

    def _apply_references(
        self, record: MemoryRecord, changes: list[str], options: dict
    ) -> None:
        for name in ("related_load", "related_mission", "destination"):
            value = options.get(name)
            if value and getattr(record, name) != value:
                setattr(record, name, value)
                changes.append(name + " = " + str(value))

    def _raise_state(self, record: MemoryRecord, target: str, changes: list[str]) -> None:
        if STATE_RANK[target] > STATE_RANK.get(record.state, 0):
            record.state = target
            changes.append("state = " + target)
        else:
            changes.append("state unchanged at " + record.state + " (no downgrade)")

    def _raise_level(self, record: MemoryRecord, target: str, changes: list[str]) -> None:
        if LEVEL_RANK[target] > LEVEL_RANK.get(record.interaction_level, 0):
            record.interaction_level = target
            changes.append("interaction_level = " + target)

    def _stop_expiration(self, record: MemoryRecord, changes: list[str]) -> None:
        if record.expires_at is not None:
            record.expires_at = None
            changes.append("expiration cleared; this record no longer expires")
