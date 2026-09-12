"""The shape of every exchange between Dispatch and a worker.

Three workers -- Intelligence, Publisher and Joe -- plus Library, which the
Publisher pulls from. They are separate programs with separate repositories, and
the reason to keep them separate is not tidiness: `Dispatch/CLAUDE.md` section
5.4 requires that Dispatch "must start and run its core operation without any of
them", and section 5.1 gives lifecycle authority to the Spine alone.

A single agent that could do all of it would violate both rules on its first
useful day, because the cheapest way to satisfy a request is always to reach
into the next component's data. So the boundary is a message, not a method call,
and this module is the message.

Four properties the shape enforces, each because of a rule that already exists:

**A worker advises; it never decides.** Every response carries findings and
recommendations. None carries an approval. `Dispatch/CLAUDE.md` section 4: "AI
decides nothing", and "a recommendation that reads like a decision is a decision
made without authority".

**A worker never writes to Dispatch.** A response is data returned to the
caller. There is no field by which a worker can ask for a write, so there is
nothing for Dispatch to accidentally honour.

**Every response says how true it is**, in the eight fixed words. A worker with
no provider configured answers UNCONFIGURED and returns nothing else; it does
not answer with a plausible guess.

**A refusal is a first-class answer.** A worker that will not do something
returns a Refusal naming the rule, not an exception, not an empty result.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

#: The eight. Dispatch/CLAUDE.md section 6; no synonyms, no variants.
TRUTH_WORDS = (
    "LIVE", "CONFIGURED", "UNCONFIGURED", "SIMULATED",
    "UNAVAILABLE", "MANUAL", "ABSENT", "UNVERIFIED",
)

#: Identities that are the program itself. None of them may approve anything,
#: anywhere. Mirrors the set dispatch/connectors and dispatch_publisher both
#: enforce -- duplicated rather than imported across a repository boundary,
#: which is THE MIKE RULE, and pinned by a test so the copies cannot drift.
RESERVED_SYSTEM_IDENTITIES = frozenset({
    "PUBLISHER", "SYSTEM", "AUTOMATION", "INTELLIGENCE", "LIBRARY", "JOE",
    "CRON", "BACKGROUND_JOB", "DISPATCH_DAEMON",
})


class ContractError(ValueError):
    """A message that does not satisfy the contract. Never sent, never answered."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


@dataclass(frozen=True)
class Capability:
    """One thing a worker will do, declared before it is asked.

    `requires_human_authorization` is the flag that makes an authority rule
    checkable by the bus instead of remembered by each worker.
    """

    name: str
    summary: str
    produces: str
    requires_human_authorization: bool = False
    reads: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class WorkerRequest:
    """Dispatch asking one worker for one thing."""

    capability: str
    payload: dict = field(default_factory=dict)
    #: Who is asking. Always Dispatch or a named person -- never a worker; the
    #: bus refuses worker-to-worker traffic, and this is the field it reads.
    requested_by: str = "DISPATCH"
    #: A recorded human decision this request relies on, where the capability
    #: requires one. An assertion is not enough: it has to point at something.
    authorization_ref: str = ""
    authorized_by: str = ""
    correlation_id: str = field(default_factory=lambda: _new_id("REQ"))
    requested_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.capability:
            raise ContractError("a request must name a capability")
        if not self.requested_by:
            raise ContractError("a request must say who is asking")

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Finding:
    """One thing a worker noticed. Advisory by construction."""

    code: str
    summary: str
    detail: str = ""
    confidence: str = "UNVERIFIED"
    source_ref: str = ""
    requires_human_review: bool = False

    def __post_init__(self) -> None:
        if self.confidence not in TRUTH_WORDS:
            raise ContractError(
                f"confidence must be one of the eight truth words, not {self.confidence!r}"
            )

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Refusal:
    """A worker declining, and naming the rule it is declining under.

    Returned, not raised. An exception loses the reason by the time it reaches a
    screen, and "the worker errored" and "the worker refused because nobody
    authorised it" need different things from a person.
    """

    rule: str
    reason: str
    remedy: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class WorkerResponse:
    """What comes back. Advice, a status word, and never a decision."""

    worker: str
    capability: str
    status: str
    correlation_id: str
    findings: tuple[Finding, ...] = ()
    recommendations: tuple[str, ...] = ()
    artifacts: dict = field(default_factory=dict)
    refusal: Refusal | None = None
    detail: str = ""
    responded_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.status not in TRUTH_WORDS:
            raise ContractError(
                f"status must be one of the eight truth words, not {self.status!r}"
            )
        for banned in ("approved", "approved_by", "decision", "authorized_by"):
            if banned in self.artifacts:
                raise ContractError(
                    f"a worker response may not carry {banned!r}: workers advise, "
                    "they do not decide (CLAUDE.md section 4)"
                )

    @property
    def refused(self) -> bool:
        return self.refusal is not None

    @property
    def actionable(self) -> bool:
        """Whether a person can act on this, as opposed to being told to go and
        configure something."""
        return self.status in ("LIVE", "SIMULATED", "MANUAL") and not self.refused

    def to_dict(self) -> dict:
        return {
            "worker": self.worker,
            "capability": self.capability,
            "status": self.status,
            "correlation_id": self.correlation_id,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": list(self.recommendations),
            "artifacts": dict(self.artifacts),
            "refusal": self.refusal.to_dict() if self.refusal else None,
            "detail": self.detail,
            "responded_at": self.responded_at,
        }


def refuse(request: WorkerRequest, worker: str, rule: str, reason: str, remedy: str = "") -> WorkerResponse:
    """The one way a refusal is built, so every refusal has the same shape."""
    return WorkerResponse(
        worker=worker,
        capability=request.capability,
        status="ABSENT",
        correlation_id=request.correlation_id,
        refusal=Refusal(rule=rule, reason=reason, remedy=remedy),
        detail=reason,
    )
