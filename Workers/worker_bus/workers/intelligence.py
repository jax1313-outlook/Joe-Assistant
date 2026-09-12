"""Intelligence: looks at what is true and says what it notices. Decides nothing.

The boundary that matters for this worker is not technical, it is
epistemological, and the constitutions say it in their own words: research is
not truth, and a recommendation is not an approval. So every finding carries a
confidence drawn from the eight truth words, and the highest an unverified
observation can reach is UNVERIFIED -- which is a real answer, not a failure.

What it will do:

  assess_load       is anything about this load worth a person's attention
  assess_broker     what the record says about who is offering the freight
  summarise_risk    the findings, ordered, with nothing invented

What it will never do: decide whether to take the load. That is Mike's, and
after him the Spine's.
"""

from __future__ import annotations

from dataclasses import dataclass

from worker_bus.contracts import Capability, Finding, WorkerRequest, WorkerResponse, refuse

#: A rate this far below the lane's own history is worth a second look. Not a
#: refusal -- Intelligence does not refuse freight, it notices things.
LOW_RATE_FRACTION = 0.85


@dataclass
class IntelligenceWorker:
    worker_id: str = "INTELLIGENCE"
    #: Injected read-only view of Dispatch. None means this worker can observe
    #: nothing and must say so rather than reasoning from an empty set.
    reader: object | None = None

    def capabilities(self) -> tuple[Capability, ...]:
        return (
            Capability(
                "assess_load",
                "Notice anything about a load that is worth a person's attention.",
                produces="findings, ordered by severity",
                reads=("load", "rate confirmation", "lane history"),
            ),
            Capability(
                "assess_broker",
                "Report what the record says about a broker. Never a score, never a verdict.",
                produces="findings",
                reads=("broker contacts", "settlement history"),
            ),
            Capability(
                "summarise_risk",
                "Order existing findings for a person to read.",
                produces="an ordered summary",
            ),
        )

    def status(self) -> str:
        return "LIVE" if self.reader is not None else "UNCONFIGURED"

    def handle(self, request: WorkerRequest, deps) -> WorkerResponse:
        if self.reader is None:
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status="UNCONFIGURED", correlation_id=request.correlation_id,
                detail=(
                    "Intelligence has no read access to Dispatch on this machine, so it "
                    "has observed nothing. It will not reason from an empty set."
                ),
            )
        handler = {
            "assess_load": self._assess_load,
            "assess_broker": self._assess_broker,
            "summarise_risk": self._summarise_risk,
        }[request.capability]
        return handler(request)

    # ----------------------------------------------------------------- work

    def _assess_load(self, request: WorkerRequest) -> WorkerResponse:
        load_id = request.payload.get("load_id", "")
        load = self.reader.get_load(load_id) if load_id else None
        if not load:
            return refuse(
                request, self.worker_id, "subject_not_found",
                f"No load {load_id!r} to look at.",
                "Intelligence reports on what exists; it does not speculate about what does not.",
            )

        findings: list[Finding] = []

        rate = self.reader.get_rate_confirmation(load_id)
        if not rate:
            findings.append(Finding(
                "NO_RATE_ON_FILE",
                "No rate confirmation is recorded for this load.",
                "Revenue, margin and the settlement are all unknown until there is one.",
                confidence="ABSENT", source_ref=f"load:{load_id}",
            ))
        else:
            history = self.reader.lane_history(
                load.get("pickup_location", ""), load.get("delivery_location", "")
            )
            if history and history.get("average_revenue"):
                average = history["average_revenue"]
                if rate["revenue"] < average * LOW_RATE_FRACTION:
                    findings.append(Finding(
                        "RATE_BELOW_LANE_HISTORY",
                        f"{rate['revenue']:.2f} is below this lane's average of {average:.2f}.",
                        f"Based on {history.get('load_count', 0)} previous load(s). "
                        "History is not a rate floor and this is not a refusal.",
                        confidence="LIVE", source_ref=f"lane:{load.get('pickup_location')}",
                        requires_human_review=True,
                    ))

        for name in ("pickup_datetime", "delivery_datetime"):
            if not load.get(name):
                findings.append(Finding(
                    "APPOINTMENT_MISSING",
                    f"{name.replace('_', ' ')} is empty.",
                    "Nothing can judge whether the truck can make it.",
                    confidence="ABSENT", source_ref=f"load:{load_id}",
                ))

        if not load.get("driver_id"):
            findings.append(Finding(
                "NO_DRIVER_ASSIGNED", "No driver is assigned.", "",
                confidence="ABSENT", source_ref=f"load:{load_id}",
            ))

        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status="LIVE", correlation_id=request.correlation_id,
            findings=tuple(findings),
            recommendations=tuple(
                f"Look at: {f.summary}" for f in findings if f.requires_human_review
            ),
            detail=f"{len(findings)} finding(s). Advisory only -- nothing here decides anything.",
        )

    def _assess_broker(self, request: WorkerRequest) -> WorkerResponse:
        name = request.payload.get("broker", "")
        if not name:
            return refuse(request, self.worker_id, "subject_not_named",
                          "No broker was named.")
        record = self.reader.broker_record(name)
        findings = []
        if not record:
            findings.append(Finding(
                "BROKER_NOT_ON_FILE", f"Nothing is recorded about {name}.",
                "First time doing business with them, as far as this record goes.",
                confidence="ABSENT",
            ))
        else:
            overdue = record.get("overdue_settlements", 0)
            if overdue:
                findings.append(Finding(
                    "BROKER_HAS_OVERDUE_SETTLEMENTS",
                    f"{overdue} settlement(s) with {name} are past due.",
                    "A fact from the settlement record. It is not a trust score and "
                    "this worker does not compute one.",
                    confidence="LIVE", requires_human_review=True,
                ))
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability, status="LIVE",
            correlation_id=request.correlation_id, findings=tuple(findings),
        )

    def _summarise_risk(self, request: WorkerRequest) -> WorkerResponse:
        raw = request.payload.get("findings", [])
        order = {"LIVE": 0, "CONFIGURED": 1, "SIMULATED": 2, "UNVERIFIED": 3,
                 "UNAVAILABLE": 4, "MANUAL": 5, "UNCONFIGURED": 6, "ABSENT": 7}
        findings = tuple(
            Finding(**f) if isinstance(f, dict) else f
            for f in raw
        )
        ordered = tuple(sorted(
            findings,
            key=lambda f: (not f.requires_human_review, order.get(f.confidence, 9)),
        ))
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability, status="LIVE",
            correlation_id=request.correlation_id, findings=ordered,
            detail="Ordered. Nothing added, nothing removed, nothing inferred.",
        )
