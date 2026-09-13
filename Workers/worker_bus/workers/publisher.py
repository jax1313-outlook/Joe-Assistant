"""Publisher: assembles a package from facts that already exist. Invents nothing.

Two rules define this worker, and both are already written down.

**It never invents a fact.** Everything in a package comes from a Dispatch record
or a Library asset. A required part that is missing produces a *notice* naming
what is missing -- not a plausible sentence in its place.

**It never approves its own work.** `dispatch_publisher.service.approve_review_package`
requires an approver id, and the reserved system identities are refused. The bus
enforces the same rule one layer up, so `assemble_completion_package` is declared
`requires_human_authorization` and a request without a recorded human decision
never reaches this code at all.

The Library dependency goes through the bus. Publisher does not import Library:
the hop appears in the audit trail as PUBLISHER -> LIBRARY under the caller's own
correlation id, which is what makes "which worker read what" answerable.
"""

from __future__ import annotations

from dataclasses import dataclass

from worker_bus.contracts import (
    RESERVED_SYSTEM_IDENTITIES,
    Capability,
    Finding,
    WorkerRequest,
    WorkerResponse,
    refuse,
)


@dataclass
class PublisherWorker:
    worker_id: str = "PUBLISHER"
    reader: object | None = None

    def capabilities(self) -> tuple[Capability, ...]:
        return (
            Capability(
                "check_readiness",
                "Is everything a completion package needs actually on file?",
                produces="findings naming what is missing",
                reads=("load", "evidence", "POD", "rate confirmation", "library templates"),
            ),
            Capability(
                "assemble_completion_package",
                "Build the package a person will review before it is sent.",
                produces="a draft package for human review",
                requires_human_authorization=True,
                reads=("load", "evidence", "library templates"),
            ),
        )

    def status(self) -> str:
        return "LIVE" if self.reader is not None else "UNCONFIGURED"

    def handle(self, request: WorkerRequest, deps) -> WorkerResponse:
        if self.reader is None:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail="Publisher has no read access to Dispatch on this machine.",
            )
        if request.capability == "check_readiness":
            return self._check_readiness(request, deps)
        return self._assemble(request, deps)

    # ----------------------------------------------------------------- work

    def _required_parts(self, load_id: str) -> tuple[list[Finding], dict]:
        load = self.reader.get_load(load_id)
        findings: list[Finding] = []
        parts: dict = {}
        if not load:
            findings.append(Finding(
                "LOAD_NOT_FOUND", f"No load {load_id!r}.", confidence="ABSENT",
            ))
            return findings, parts

        parts["load"] = load

        rate = self.reader.get_rate_confirmation(load_id)
        if rate:
            parts["rate"] = rate
        else:
            findings.append(Finding(
                "RATE_MISSING", "No rate confirmation on file.",
                "The package cannot state a figure that was never recorded.",
                confidence="ABSENT", source_ref=f"load:{load_id}",
            ))

        pods = self.reader.list_pods(load_id)
        if pods:
            parts["pod"] = pods[0]
        else:
            findings.append(Finding(
                "POD_MISSING", "No proof of delivery.",
                "A completion package without a POD is a claim the load was delivered, "
                "with nothing behind it.",
                confidence="ABSENT", source_ref=f"load:{load_id}",
                requires_human_review=True,
            ))

        evidence = self.reader.list_evidence(load_id)
        parts["evidence_count"] = len(evidence)
        if not evidence:
            findings.append(Finding(
                "NO_EVIDENCE", "Nothing is attached to this load.",
                confidence="ABSENT", source_ref=f"load:{load_id}",
            ))
        return findings, parts

    def _check_readiness(self, request: WorkerRequest, deps) -> WorkerResponse:
        load_id = request.payload.get("load_id", "")
        findings, parts = self._required_parts(load_id)

        # The Library hop. Through the bus, never an import.
        template_id = request.payload.get("template_id", "")
        if template_id:
            answer = deps.ask("LIBRARY", WorkerRequest(
                capability="fetch_asset",
                payload={"asset_id": template_id},
                requested_by=self.worker_id,
                correlation_id=request.correlation_id,
            ))
            asset = answer.artifacts.get("asset") if answer.artifacts else None
            if answer.status == "ABSENT":
                findings.append(Finding(
                    "TEMPLATE_NOT_IN_LIBRARY",
                    f"Library has no approved template {template_id!r}.",
                    "Publisher uses approved assets. It does not write a replacement.",
                    confidence="ABSENT", source_ref=f"library:{template_id}",
                ))
            elif answer.status not in ("LIVE", "SIMULATED") or not asset:
                # Only an answer that carries the asset is an asset. A present-but-blocked
                # template (review due) used to fall into the else branch below and count as
                # present; any answer without an asset now says why instead.
                reason = next((f.summary for f in answer.findings), f"Library answered {answer.status}.")
                findings.append(Finding(
                    "TEMPLATE_NOT_USABLE",
                    f"Template {template_id!r} cannot be used: {reason}",
                    "Publisher uses approved, usable assets. It does not substitute one.",
                    confidence=answer.status, source_ref=f"library:{template_id}",
                    requires_human_review=True,
                ))
            else:
                parts["template"] = asset

        blocking = [f for f in findings if f.requires_human_review]
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status="LIVE", correlation_id=request.correlation_id,
            findings=tuple(findings),
            recommendations=tuple(f"Supply: {f.summary}" for f in findings),
            artifacts={"parts_present": sorted(parts)},
            detail=(
                "Ready to assemble." if not findings else
                f"{len(findings)} part(s) missing"
                + (f", {len(blocking)} of which need a person." if blocking else ".")
            ),
        )

    def _assemble(self, request: WorkerRequest, deps) -> WorkerResponse:
        load_id = request.payload.get("load_id", "")
        findings, parts = self._required_parts(load_id)
        if any(f.confidence == "ABSENT" and f.code == "LOAD_NOT_FOUND" for f in findings):
            return refuse(request, self.worker_id, "subject_not_found",
                          f"No load {load_id!r} to assemble a package for.")

        missing = [f for f in findings if f.requires_human_review]
        if missing:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNVERIFIED", correlation_id=request.correlation_id,
                findings=tuple(findings),
                detail=(
                    "Not assembled. A package is built from facts that exist; the missing "
                    "ones are named above rather than written in."
                ),
            )

        load = parts["load"]
        summary = [
            f"Load {load['load_id']}",
            f"Customer: {load.get('customer', '')}",
            f"{load.get('pickup_location', '')} -> {load.get('delivery_location', '')}",
            f"Evidence items attached: {parts.get('evidence_count', 0)}",
        ]
        if "rate" in parts:
            summary.append(f"Rate: {parts['rate'].get('rate_amount', 0):.2f}")

        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status="LIVE", correlation_id=request.correlation_id,
            findings=tuple(findings),
            artifacts={
                "package": {
                    "load_id": load["load_id"],
                    "summary_lines": summary,
                    "parts": sorted(parts),
                    # Named so the record shows who authorised the assembly. It is
                    # not an approval of the package -- a person still reviews it,
                    # and the contract refuses a response carrying an approval.
                    "assembled_under_authorization": request.authorization_ref,
                    "requested_by": request.authorized_by,
                },
                "review_required": True,
            },
            detail="Draft assembled. It is a draft until a person reviews and submits it.",
        )
