"""The mediator. Every exchange goes through it, which is the point.

Without a mediator, "bounded contracts between the workers" is a naming
convention: Publisher imports Intelligence, Intelligence reads Library's files,
and within a few weeks there is one program with three folder names. The bus
makes that structurally impossible rather than discouraged.

Four rules it enforces, and each of them is already written down somewhere:

**Dispatch calls workers. Workers do not call each other.** A request whose
`requested_by` is a registered worker is refused. Where a worker genuinely needs
something another worker holds -- the Publisher needs Library assets -- it
declares that as a *dependency* and the bus fetches it, so the traffic is
visible in one audit trail instead of buried in an import.

**A capability that requires human authorisation gets a recorded one or
nothing.** `Dispatch/CLAUDE.md` section 4: no record may claim Mike approved
something unless he performed an authenticated action that produced it. So the
bus requires both a named authoriser and a reference to the decision, refuses
the reserved system identities outright, and refuses an authoriser who merely
asserts they are Mike without a reference.

**No worker writes to Dispatch.** Section 5.4: "No direct Dispatch write
authority may be granted to Assistant." A response is data returned to the
caller; there is no channel by which a worker can request a write.

**Every exchange is recorded before the answer is used.** The audit is written
whatever the outcome, including refusals -- a refusal nobody can see is
indistinguishable from a question nobody asked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from worker_bus.audit import AuditLog
from worker_bus.contracts import (
    RESERVED_SYSTEM_IDENTITIES,
    Capability,
    WorkerRequest,
    WorkerResponse,
    refuse,
)

DISPATCH = "DISPATCH"


class Worker(Protocol):
    """What a worker has to be. Deliberately four members."""

    worker_id: str

    def capabilities(self) -> tuple[Capability, ...]:
        """Everything this worker will do, declared up front."""

    def status(self) -> str:
        """One truth word for the worker as a whole, without doing any work."""

    def handle(self, request: WorkerRequest, deps: "Dependencies") -> WorkerResponse:
        """Answer one request. Returns a refusal rather than raising."""


@dataclass
class Dependencies:
    """What a worker may reach, handed to it rather than imported by it.

    This is the seam that keeps Publisher from importing Library. A worker that
    needs another worker asks through here, the bus records the hop, and the
    dependency is visible in one place instead of in an import statement
    somebody has to go looking for.
    """

    ask: Callable[[str, WorkerRequest], WorkerResponse]
    #: Read-only views onto Dispatch, injected by the host. Never a write path.
    dispatch_reader: object | None = None


@dataclass
class WorkerBus:
    audit: AuditLog = field(default_factory=AuditLog)
    _workers: dict = field(default_factory=dict)
    #: Guards against a cycle: Publisher -> Library -> Publisher would otherwise
    #: recurse until the stack ends, and the failure would look like a crash
    #: rather than the design error it is.
    _in_flight: list = field(default_factory=list)
    max_depth: int = 4

    # ----------------------------------------------------------- registration

    def register(self, worker: Worker) -> None:
        if worker.worker_id in self._workers:
            raise ValueError(f"{worker.worker_id} is already registered")
        self._workers[worker.worker_id] = worker

    def registered(self) -> tuple[str, ...]:
        return tuple(sorted(self._workers))

    def get(self, worker_id: str) -> Worker | None:
        return self._workers.get(worker_id)

    def roster(self) -> list[dict]:
        """Who is here, what they will do, and whether they can do it today."""
        return [
            {
                "worker": worker_id,
                "status": worker.status(),
                "capabilities": [c.to_dict() for c in worker.capabilities()],
            }
            for worker_id, worker in sorted(self._workers.items())
        ]

    # ------------------------------------------------------------- dispatching

    def ask(self, worker_id: str, request: WorkerRequest) -> WorkerResponse:
        """Put one request to one worker. Always returns; never raises for a
        refusal."""
        worker = self._workers.get(worker_id)
        if worker is None:
            response = refuse(
                request, worker_id, "worker_not_registered",
                f"No worker {worker_id!r} is registered on this bus.",
                f"Registered: {', '.join(self.registered()) or 'none'}.",
            )
            self.audit.record(worker_id, request, response)
            return response

        guard = self._guard(worker_id, request)
        if guard is not None:
            self.audit.record(worker_id, request, guard)
            return guard

        self._in_flight.append(worker_id)
        try:
            deps = Dependencies(ask=self._nested_ask(worker_id))
            try:
                response = worker.handle(request, deps)
            except Exception as exc:  # noqa: BLE001 - a worker fault is not a Dispatch fault
                # Degradation is permitted; incapacity is not (CLAUDE.md 5.4). A
                # worker that throws must not take the caller down with it.
                response = WorkerResponse(
                    worker=worker_id, capability=request.capability, status="UNAVAILABLE",
                    correlation_id=request.correlation_id,
                    detail=f"{type(exc).__name__}: {exc}",
                )
        finally:
            self._in_flight.pop()

        self.audit.record(worker_id, request, response)
        return response

    def _nested_ask(self, caller: str) -> Callable[[str, WorkerRequest], WorkerResponse]:
        def ask(worker_id: str, request: WorkerRequest) -> WorkerResponse:
            # Rewritten so the audit shows who really asked. A dependency hop
            # attributed to DISPATCH would hide the one thing this trail exists
            # to show.
            hop = WorkerRequest(
                capability=request.capability,
                payload=request.payload,
                requested_by=caller,
                authorization_ref=request.authorization_ref,
                authorized_by=request.authorized_by,
                correlation_id=request.correlation_id,
            )
            return self._ask_dependency(worker_id, hop)

        return ask

    def _ask_dependency(self, worker_id: str, request: WorkerRequest) -> WorkerResponse:
        if len(self._in_flight) >= self.max_depth:
            response = refuse(
                request, worker_id, "dependency_depth_exceeded",
                f"Dependency chain is {len(self._in_flight)} deep "
                f"({' -> '.join(self._in_flight)} -> {worker_id}).",
                "A chain this long means a worker is orchestrating, which is Dispatch's job.",
            )
            self.audit.record(worker_id, request, response)
            return response
        if worker_id in self._in_flight:
            response = refuse(
                request, worker_id, "dependency_cycle",
                f"{worker_id} is already in flight ({' -> '.join(self._in_flight)}).",
                "Two workers that need each other are one worker with a seam drawn in "
                "the wrong place.",
            )
            self.audit.record(worker_id, request, response)
            return response

        worker = self._workers.get(worker_id)
        if worker is None:
            response = refuse(
                request, worker_id, "worker_not_registered",
                f"No worker {worker_id!r} is registered on this bus.",
            )
            self.audit.record(worker_id, request, response)
            return response

        self._in_flight.append(worker_id)
        try:
            deps = Dependencies(ask=self._nested_ask(worker_id))
            try:
                response = worker.handle(request, deps)
            except Exception as exc:  # noqa: BLE001
                response = WorkerResponse(
                    worker=worker_id, capability=request.capability, status="UNAVAILABLE",
                    correlation_id=request.correlation_id,
                    detail=f"{type(exc).__name__}: {exc}",
                )
        finally:
            self._in_flight.pop()
        self.audit.record(worker_id, request, response)
        return response

    # ----------------------------------------------------------------- guards

    def _guard(self, worker_id: str, request: WorkerRequest) -> WorkerResponse | None:
        """Everything the bus refuses before a worker sees the request."""
        worker = self._workers[worker_id]

        declared = {c.name: c for c in worker.capabilities()}
        capability = declared.get(request.capability)
        if capability is None:
            return refuse(
                request, worker_id, "undeclared_capability",
                f"{worker_id} does not declare {request.capability!r}.",
                f"Declared: {', '.join(sorted(declared)) or 'none'}.",
            )

        # Worker-to-worker traffic, attempted directly rather than as a declared
        # dependency. This is the rule that keeps three workers from becoming one.
        if request.requested_by in self._workers and request.requested_by != worker_id:
            if not self._in_flight:
                return refuse(
                    request, worker_id, "worker_to_worker_call",
                    f"{request.requested_by} may not call {worker_id} directly.",
                    "Dispatch coordinates. A worker that needs another declares a "
                    "dependency, and the bus makes the hop so it is in one audit trail.",
                )

        if capability.requires_human_authorization:
            problem = self._authorization_problem(request)
            if problem is not None:
                return refuse(request, worker_id, *problem)

        return None

    @staticmethod
    def _authorization_problem(request: WorkerRequest) -> tuple[str, str, str] | None:
        who = (request.authorized_by or "").strip()
        if not who:
            return (
                "human_authorization_required",
                f"{request.capability} requires a named human authorisation and none was given.",
                "Record the decision first, then pass authorized_by and authorization_ref.",
            )
        if who.upper() in RESERVED_SYSTEM_IDENTITIES:
            return (
                "reserved_identity_cannot_authorize",
                f"{who!r} is the program, not a person.",
                "Only a real, external identity can authorise this.",
            )
        if not request.authorization_ref:
            return (
                "authorization_reference_required",
                f"{who} is named as the authoriser but nothing is referenced.",
                "Pass authorization_ref pointing at the recorded decision. An assertion "
                "that somebody approved is not a record that they did "
                "(CLAUDE.md section 4).",
            )
        return None
