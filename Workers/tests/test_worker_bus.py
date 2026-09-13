"""Three workers stay three workers, and none of them decides anything.

The mission was explicit: implement bounded contracts and working connections
among Intelligence, Publisher and Joe -- and **do not create a monolithic
agent**. That is not a style preference. `Dispatch/CLAUDE.md` section 5.4
requires Dispatch to start and run without any plug-in, and section 5.1 gives
lifecycle authority to the Spine alone. A single agent that could do all of it
would break both on its first useful day, because the cheapest way to satisfy a
request is always to reach into the next component's data.

So the tests below are mostly about what the bus **refuses**.
"""

from __future__ import annotations

import pytest

from worker_bus.audit import AuditLog
from worker_bus.bus import WorkerBus
from worker_bus.contracts import (
    RESERVED_SYSTEM_IDENTITIES,
    Capability,
    ContractError,
    Finding,
    WorkerRequest,
    WorkerResponse,
)
from worker_bus.workers import IntelligenceWorker, JoeWorker, LibraryWorker, PublisherWorker


class FakeReader:
    """A read-only view of Dispatch, with no write methods at all."""

    def __init__(self, loads=None, rates=None, pods=None, evidence=None,
                 lane=None, brokers=None, milestones=None, exceptions=None, drivers=None):
        self._loads = loads or {}
        self._rates = rates or {}
        self._pods = pods or {}
        self._evidence = evidence or {}
        self._lane = lane or []
        self._brokers = brokers or {}
        self._milestones = milestones or {}
        self._exceptions = exceptions or {}
        self._drivers = drivers or {}

    def get_load(self, load_id): return self._loads.get(load_id)
    def get_rate_confirmation(self, load_id): return self._rates.get(load_id)
    def list_pods(self, load_id): return self._pods.get(load_id, [])
    def list_evidence(self, load_id): return self._evidence.get(load_id, [])
    def list_milestones(self, load_id): return self._milestones.get(load_id, [])
    def list_exceptions(self, load_id): return self._exceptions.get(load_id, [])
    def get_driver(self, driver_id): return self._drivers.get(driver_id)
    def lane_history(self, origin, destination, *, exclude_load_id=""):
        # Mirrors store.get_lane_history exactly: prior LOAD ROWS, list[dict],
        # no aggregate, and the subject excluded. The old double returned a dict
        # carrying "average_revenue" -- a key the real function has never had --
        # so the one test covering this branch proved the shape of the bug.
        return [r for r in self._lane if r.get("load_id") != exclude_load_id]
    def broker_record(self, name): return self._brokers.get(name)


LOAD = {
    "load_id": "LD-1", "customer": "Acme Foods", "status": "in_transit",
    "pickup_location": "Columbus OH", "delivery_location": "Dallas TX",
    "pickup_datetime": "2026-09-14T08:00:00-04:00",
    "delivery_datetime": "2026-09-15T14:00:00-05:00",
    "driver_id": "DRV-1", "broker_shipper": "TQL",
}


@pytest.fixture
def reader():
    return FakeReader(
        loads={"LD-1": dict(LOAD)},
        rates={"LD-1": {"revenue": 1800.0, "rate_amount": 1800.0}},
        evidence={"LD-1": [{"evidence_id": "EV-1"}]},
        pods={"LD-1": [{"pod_id": "POD-1"}]},
        drivers={"DRV-1": {"name": "Ray"}},
        milestones={"LD-1": [{"event_type": "loaded"}]},
    )


@pytest.fixture
def bus(reader):
    bus = WorkerBus(audit=AuditLog())
    bus.register(IntelligenceWorker(reader=reader))
    bus.register(PublisherWorker(reader=reader))
    bus.register(JoeWorker(reader=reader))
    bus.register(LibraryWorker(assets={
        "TPL-COMPLETION": {"kind": "template", "name": "Completion package"},
    }))
    return bus


class TestTheBoundaryHolds:
    def test_a_worker_may_not_call_another_worker_directly(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="check_readiness", payload={"load_id": "LD-1"},
            requested_by="INTELLIGENCE",
        ))
        assert response.refused
        assert response.refusal.rule == "worker_to_worker_call"
        # The rule that keeps three workers from becoming one.
        assert "Dispatch coordinates" in response.refusal.remedy

    def test_a_declared_dependency_is_allowed_and_recorded(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="check_readiness",
            payload={"load_id": "LD-1", "template_id": "TPL-COMPLETION"},
        ))
        assert not response.refused
        hops = bus.audit.for_correlation(response.correlation_id)
        assert [(h.requested_by, h.worker) for h in hops] == [
            ("PUBLISHER", "LIBRARY"), ("DISPATCH", "PUBLISHER"),
        ], "the Library hop must appear under the caller's own correlation id"

    def test_an_undeclared_capability_is_refused_before_the_worker_sees_it(self, bus):
        response = bus.ask("INTELLIGENCE", WorkerRequest(capability="approve_load"))
        assert response.refusal.rule == "undeclared_capability"

    def test_an_unregistered_worker_is_a_refusal_not_a_crash(self, bus):
        response = bus.ask("MANAGER", WorkerRequest(capability="anything"))
        assert response.refusal.rule == "worker_not_registered"

    def test_a_cycle_is_refused_rather_than_recursing(self, reader):
        """Two workers that need each other are one worker with the seam in the
        wrong place."""

        class Looper:
            worker_id = "A"

            def capabilities(self):
                return (Capability("go", "calls B", produces="nothing"),)

            def status(self):
                return "LIVE"

            def handle(self, request, deps):
                inner = deps.ask("B", WorkerRequest(capability="go", requested_by="A"))
                return WorkerResponse(worker="A", capability="go", status="LIVE",
                                      correlation_id=request.correlation_id,
                                      detail=inner.refusal.rule if inner.refused else "ok")

        class Other(Looper):
            worker_id = "B"

            def handle(self, request, deps):
                inner = deps.ask("A", WorkerRequest(capability="go", requested_by="B"))
                return WorkerResponse(worker="B", capability="go", status="LIVE",
                                      correlation_id=request.correlation_id,
                                      detail=inner.refusal.rule if inner.refused else "ok")

        bus = WorkerBus()
        bus.register(Looper())
        bus.register(Other())
        bus.ask("A", WorkerRequest(capability="go"))

        # The refusal happens at the hop that would have closed the loop, and it
        # is the audit that shows it -- A only sees that B answered, which is
        # correct: a worker should not have to understand the topology it sits in.
        assert [e.refusal_rule for e in bus.audit.refusals()] == ["dependency_cycle"]
        assert [(e.requested_by, e.worker) for e in bus.audit.entries] == [
            ("B", "A"), ("A", "B"), ("DISPATCH", "A"),
        ]

    def test_a_worker_that_throws_does_not_take_dispatch_down(self, bus):
        class Exploding:
            worker_id = "BROKEN"

            def capabilities(self):
                return (Capability("go", "throws", produces="nothing"),)

            def status(self):
                return "LIVE"

            def handle(self, request, deps):
                raise RuntimeError("the wheel came off")

        bus.register(Exploding())
        response = bus.ask("BROKEN", WorkerRequest(capability="go"))
        assert response.status == "UNAVAILABLE"
        assert "the wheel came off" in response.detail


class TestAuthority:
    def test_assembling_a_package_needs_a_named_human(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
        ))
        assert response.refusal.rule == "human_authorization_required"

    @pytest.mark.parametrize("identity", sorted(RESERVED_SYSTEM_IDENTITIES))
    def test_the_program_cannot_authorise_itself(self, bus, identity):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
            authorized_by=identity, authorization_ref="DEC-1",
        ))
        assert response.refusal.rule == "reserved_identity_cannot_authorize"

    def test_a_name_without_a_reference_is_not_an_authorisation(self, bus):
        """An assertion that somebody approved is not a record that they did."""
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
            authorized_by="Mike",
        ))
        assert response.refusal.rule == "authorization_reference_required"
        assert "CLAUDE.md section 4" in response.refusal.remedy

    def test_a_recorded_decision_is_accepted(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
            authorized_by="Mike", authorization_ref="DECISION-2026-09-12-004",
        ))
        assert not response.refused
        assert response.status == "LIVE"

    def test_no_response_may_carry_an_approval(self):
        with pytest.raises(ContractError, match="workers advise"):
            WorkerResponse(worker="W", capability="c", status="LIVE", correlation_id="X",
                           artifacts={"approved_by": "Mike"})

    def test_a_status_must_be_one_of_the_eight(self):
        with pytest.raises(ContractError, match="truth words"):
            WorkerResponse(worker="W", capability="c", status="PROBABLY", correlation_id="X")

    def test_a_finding_confidence_must_be_one_of_the_eight(self):
        with pytest.raises(ContractError, match="truth words"):
            Finding("C", "s", confidence="quite sure")


class TestIntelligence:
    def test_it_notices_a_missing_rate_without_refusing_the_load(self, bus):
        reader = FakeReader(loads={"LD-1": dict(LOAD)})
        bus = WorkerBus()
        bus.register(IntelligenceWorker(reader=reader))
        response = bus.ask("INTELLIGENCE", WorkerRequest(
            capability="assess_load", payload={"load_id": "LD-1"}))
        codes = {f.code for f in response.findings}
        assert "NO_RATE_ON_FILE" in codes
        assert response.status == "LIVE"
        assert not response.refused, "Intelligence reports; it does not refuse freight"

    def test_a_low_rate_is_a_finding_not_a_verdict(self, reader):
        # Two priced priors on the same lane. The average is theirs, not LD-1's.
        reader._lane = [{"load_id": "LD-8"}, {"load_id": "LD-9"}]
        reader._rates["LD-8"] = {"revenue": 2600.0, "rate_amount": 2600.0}
        reader._rates["LD-9"] = {"revenue": 2600.0, "rate_amount": 2600.0}
        bus = WorkerBus()
        bus.register(IntelligenceWorker(reader=reader))
        response = bus.ask("INTELLIGENCE", WorkerRequest(
            capability="assess_load", payload={"load_id": "LD-1"}))
        low = [f for f in response.findings if f.code == "RATE_BELOW_LANE_HISTORY"]
        assert low and low[0].requires_human_review
        assert "not a refusal" in low[0].detail

    def test_with_no_reader_it_says_so_rather_than_reasoning_from_nothing(self):
        bus = WorkerBus()
        bus.register(IntelligenceWorker(reader=None))
        response = bus.ask("INTELLIGENCE", WorkerRequest(
            capability="assess_load", payload={"load_id": "LD-1"}))
        assert response.status == "UNCONFIGURED"
        assert response.findings == ()

    def test_a_broker_with_no_record_is_absent_not_risky(self, reader):
        bus = WorkerBus()
        bus.register(IntelligenceWorker(reader=reader))
        response = bus.ask("INTELLIGENCE", WorkerRequest(
            capability="assess_broker", payload={"broker": "Unknown Logistics"}))
        assert {f.code for f in response.findings} == {"BROKER_NOT_ON_FILE"}
        assert all(f.confidence == "ABSENT" for f in response.findings)


class TestPublisher:
    def test_a_missing_pod_blocks_assembly_and_is_named(self, reader):
        reader._pods = {}
        bus = WorkerBus()
        bus.register(PublisherWorker(reader=reader))
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
            authorized_by="Mike", authorization_ref="DEC-1"))
        assert response.status == "UNVERIFIED"
        assert "POD_MISSING" in {f.code for f in response.findings}
        assert "rather than written in" in response.detail

    def test_a_template_not_in_the_library_is_not_invented(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="check_readiness",
            payload={"load_id": "LD-1", "template_id": "TPL-NOT-THERE"}))
        finding = [f for f in response.findings if f.code == "TEMPLATE_NOT_IN_LIBRARY"]
        assert finding
        assert "does not write a replacement" in finding[0].detail

    def test_an_assembled_package_is_a_draft(self, bus):
        response = bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"},
            authorized_by="Mike", authorization_ref="DEC-1"))
        assert response.artifacts["review_required"] is True
        assert "draft until a person reviews" in response.detail


class TestJoe:
    def test_he_reads_back_in_one_sentence(self, bus):
        response = bus.ask("JOE", WorkerRequest(
            capability="read_back_load", payload={"load_id": "LD-1", "aspect": "where"}))
        assert response.artifacts["spoken"] == "You're going to Dallas TX."

    def test_he_says_what_is_not_on_file_rather_than_skipping_it(self, reader):
        reader._loads["LD-2"] = {"load_id": "LD-2", "delivery_location": "Dallas TX"}
        bus = WorkerBus()
        bus.register(JoeWorker(reader=reader))
        response = bus.ask("JOE", WorkerRequest(
            capability="read_back_load", payload={"load_id": "LD-2", "aspect": "delivery"}))
        assert "not on file" in response.artifacts["spoken"]

    def test_a_proposal_never_applies_itself(self, bus):
        response = bus.ask("JOE", WorkerRequest(
            capability="propose_capture",
            payload={"load_id": "LD-1", "heard": "we're loaded", "confidence": 0.9}))
        assert response.artifacts["applies_itself"] is False
        assert response.artifacts["proposal"]["applied"] is False
        assert "yes or no" in response.artifacts["spoken"]

    def test_a_half_heard_sentence_produces_nothing(self, bus):
        response = bus.ask("JOE", WorkerRequest(
            capability="propose_capture",
            payload={"load_id": "LD-1", "heard": "mmf rolling", "confidence": 0.2}))
        assert "proposal" not in response.artifacts
        assert "Saying nothing is the correct answer" in response.detail

    def test_without_a_reasoner_he_still_reads_back_and_says_what_he_cannot_do(self, bus):
        assert bus.ask("JOE", WorkerRequest(
            capability="read_back_load", payload={"load_id": "LD-1"})).status == "LIVE"
        assert bus.ask("JOE", WorkerRequest(
            capability="answer_question", payload={"question": "should I take it"}
        )).status == "UNCONFIGURED"


class TestTheAudit:
    def test_every_exchange_is_recorded_including_refusals(self, bus):
        bus.ask("PUBLISHER", WorkerRequest(
            capability="assemble_completion_package", payload={"load_id": "LD-1"}))
        assert len(bus.audit.refusals()) == 1

    def test_it_records_the_shape_of_a_payload_not_its_contents(self, bus):
        bus.ask("JOE", WorkerRequest(
            capability="read_back_load",
            payload={"load_id": "LD-1", "driver_phone": "555-0100"}))
        entry = bus.audit.entries[-1]
        assert entry.payload_shape == "{driver_phone, load_id}"
        assert "555-0100" not in entry.payload_shape, (
            "an audit that copies the data is a second place the data has to be protected"
        )

    def test_it_can_be_written_to_a_file(self, bus, tmp_path):
        import json

        bus.audit.path = tmp_path / "worker-audit.jsonl"
        bus.ask("JOE", WorkerRequest(capability="read_back_load", payload={"load_id": "LD-1"}))
        lines = (tmp_path / "worker-audit.jsonl").read_text(encoding="utf-8").splitlines()
        assert json.loads(lines[0])["worker"] == "JOE"


class TestTheRoster:
    def test_it_says_who_is_here_and_whether_they_can_work(self, bus):
        roster = {row["worker"]: row for row in bus.roster()}
        assert set(roster) == {"INTELLIGENCE", "PUBLISHER", "JOE", "LIBRARY"}
        assert roster["JOE"]["status"] in ("LIVE", "CONFIGURED")

    def test_no_worker_declares_a_capability_that_decides_anything(self, bus):
        for row in bus.roster():
            for capability in row["capabilities"]:
                assert not any(
                    word in capability["name"]
                    for word in ("approve", "authorize", "decide", "commit")
                ), f"{row['worker']} declares {capability['name']}"

    def test_registering_the_same_worker_twice_is_refused(self, bus):
        with pytest.raises(ValueError, match="already registered"):
            bus.register(JoeWorker())
