"""Dispatch port - the boundary, defined and deliberately unconnected.

**No Dispatch connection exists in this build, and none is attempted.**

This module states the shape of the boundary so a connection can be made later
under an interface Dispatch publishes. It contains no endpoint, no credential,
no database handle, and no path into Dispatch.

Doctrine, from JOE_CONSTITUTION_v1:

  - Architecture 3.6: JOE never writes to Dispatch. It submits a
    request that Dispatch or Mike accepts or rejects.
  - Architecture 3.8: the interface belongs to Dispatch. JOE consumes
    it and may not expand its own access.
  - Constitution 3.1: silence is never consent. Nothing executes by default.

The write path here is a request queue that nothing drains. That is not an
oversight - there is no authorized consumer, so a submitted request stays
submitted and says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import ActionRequest, Provenance, SourceMode, stamp


class DispatchPortError(RuntimeError):
    pass


# What JOE is permitted to ask Dispatch for. A closed list: what is
# not here is not requestable, and the port cannot be widened from this side.
READABLE_FACTS = (
    "loads",
    "schedule",
    "capacity",
    "route",
    "mission",
    "status",
    "reference_documents",
)

# What JOE is permitted to send toward Dispatch. All are proposals.
SUBMITTABLE = (
    "finding",
    "recommendation",
    "draft",
    "explanation",
    "question",
    "action_request",
    "proposed_change",
)


@dataclass
class DispatchReadResult:
    """The answer to a read request. Unconnected in this build."""

    fact: str
    ok: bool = False
    data: dict = field(default_factory=dict)
    error: str = "no Dispatch interface is connected"
    read_at: str = field(default_factory=stamp)

    def provenance(self) -> Provenance:
        return Provenance(
            source="Dispatch (system of record)",
            mode=SourceMode.LIVE if self.ok else SourceMode.UNAVAILABLE,
            as_of=self.read_at,
            detail=self.error if not self.ok else self.fact,
        )


class DispatchPort:
    """JOE's side of the Dispatch boundary.

    Every method either reads through a published interface or submits a
    proposal. There is no method that performs an operational write, because
    performing one is prohibited - not disabled, absent.
    """

    name = "dispatch-port"

    def __init__(self, interface: str = "none", endpoint: str = "", enabled: bool = False) -> None:
        self.interface = (interface or "none").strip().lower()
        self.endpoint = endpoint or ""
        self.enabled = bool(enabled)
        self.submitted: list[ActionRequest] = []

    # ---- connection ---------------------------------------------------

    @property
    def connected(self) -> bool:
        """True only when Dispatch has published an interface and it is bound.

        No interface exists on this machine, so this is False and every read
        returns unavailable rather than a guess.
        """
        return self.enabled and self.interface not in ("none", "")

    def probe(self) -> dict:
        return {
            "available": self.connected,
            "live_connection": self.connected,
            "interface": self.interface,
            "blocker": (
                ""
                if self.connected
                else "no approved Dispatch interface is published or configured"
            ),
            "readable_facts": list(READABLE_FACTS),
            "submittable": list(SUBMITTABLE),
            "can_write_operational_truth": False,
        }

    # ---- reads --------------------------------------------------------

    def read(self, fact: str) -> DispatchReadResult:
        """Request a read-only operational fact."""
        wanted = (fact or "").strip().lower()
        if wanted not in READABLE_FACTS:
            raise DispatchPortError(
                "'" + str(fact) + "' is not on the permitted read list; the "
                "Assistant may not widen its own access"
            )
        if not self.connected:
            return DispatchReadResult(
                fact=wanted,
                ok=False,
                error=(
                    "Dispatch is not connected. I cannot read authoritative "
                    "operational information."
                ),
            )
        # Unreachable in this build: connected is False by construction.
        raise DispatchPortError(
            "interface '" + self.interface + "' is configured but no adapter "
            "for it is implemented in this build"
        )

    # ---- submissions --------------------------------------------------

    def submit(self, kind: str, detail: str) -> ActionRequest:
        """Submit a proposal toward Dispatch.

        Submitting is not doing. The returned request reports
        `accepted=False`, `performed=False`, `auto_execute=False`, and names
        Mike Zachary as the decision holder. Nothing drains this queue.
        """
        wanted = (kind or "").strip().lower()
        if wanted not in SUBMITTABLE:
            raise DispatchPortError(
                "'" + str(kind) + "' is not a permitted submission kind"
            )
        request = ActionRequest(kind=wanted, detail=str(detail or ""))
        request.submitted = self.connected
        self.submitted.append(request)
        return request

    def pending(self) -> list[ActionRequest]:
        return list(self.submitted)

    # ---- what does not exist ------------------------------------------
    #
    # There is deliberately no write(), update(), create(), delete(),
    # accept_load(), book(), dispatch(), or commit() method on this class.
    # Their absence is asserted by the test suite.
