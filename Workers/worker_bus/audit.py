"""Every exchange, recorded before the answer is used.

Append-only and in memory by default, with an optional JSONL file. A refusal
nobody can see is indistinguishable from a question nobody asked, which is why
refusals are recorded exactly like successes rather than being treated as
non-events.

Payload contents are recorded by *shape*, not by value. A request can carry a
broker's rate or a driver's phone number, and an audit trail that copies those
into a second file is a second place they have to be protected. The trail
answers "who asked whom for what, and what came back" -- which is what an audit
is for -- without becoming a duplicate of the data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shape(value) -> str:
    """A description of a value, never the value."""
    if isinstance(value, dict):
        return "{" + ", ".join(sorted(value)) + "}"
    if isinstance(value, (list, tuple)):
        return f"[{len(value)}]"
    return type(value).__name__


@dataclass
class AuditEntry:
    at: str
    worker: str
    capability: str
    requested_by: str
    correlation_id: str
    status: str
    refused: bool
    refusal_rule: str = ""
    payload_shape: str = ""
    finding_count: int = 0
    detail: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class AuditLog:
    path: Path | None = None
    entries: list = field(default_factory=list)

    def record(self, worker_id: str, request, response) -> AuditEntry:
        entry = AuditEntry(
            at=_now(),
            worker=worker_id,
            capability=request.capability,
            requested_by=request.requested_by,
            correlation_id=request.correlation_id,
            status=response.status,
            refused=response.refused,
            refusal_rule=response.refusal.rule if response.refusal else "",
            payload_shape=_shape(request.payload),
            finding_count=len(response.findings),
            detail=response.detail[:300],
        )
        self.entries.append(entry)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
        return entry

    def for_correlation(self, correlation_id: str) -> list[AuditEntry]:
        """One conversation, in order -- including every dependency hop."""
        return [e for e in self.entries if e.correlation_id == correlation_id]

    def refusals(self) -> list[AuditEntry]:
        return [e for e in self.entries if e.refused]

    def render(self) -> str:
        if not self.entries:
            return "  No exchanges recorded.\n"
        lines = []
        for entry in self.entries:
            mark = "REFUSED" if entry.refused else entry.status
            lines.append(
                f"  {entry.at}  {entry.requested_by:>12} -> {entry.worker:<14} "
                f"{entry.capability:<28} {mark}"
            )
            if entry.refused:
                lines.append(f"                 rule: {entry.refusal_rule} -- {entry.detail}")
        return "\n".join(lines) + "\n"
