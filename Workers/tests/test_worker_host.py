"""The workers have a host, and it cannot write.

Before `worker_bus/host.py` existed, `WorkerBus` was constructed in exactly one
place -- `Workers/tests/test_worker_bus.py` -- and every worker was instantiated
only there. Thirty-nine tests passed and nothing in Dispatch or the Assistant
Plugin ever built one. Intelligence, Publisher and Joe could not perform a
single constitutional duty against a real load, because nothing called them.

These tests cover the assembly point, and most of them are about the boundary
it has to hold: `CLAUDE.md` §5.4, "No direct Dispatch write authority may be
granted to Assistant."
"""

from __future__ import annotations

import sys

import pytest

from worker_bus.contracts import WorkerRequest
from worker_bus.host import (
    READ_METHODS,
    DispatchReader,
    build_bus,
    describe,
    dispatch_available,
    ensure_plugin_importable,
)


# ── the boundary ─────────────────────────────────────────────────────────


class TestTheReaderCannotWrite:
    """Structural, not promised. A worker that wanted to write would have to
    add a method to a reviewed file, in public, on purpose."""

    WRITE_PREFIXES = ("create", "update", "save", "delete", "set_", "add_",
                      "insert", "upsert", "remove", "apply", "mark", "record")

    def test_no_method_on_the_reader_looks_like_a_write(self):
        for name in dir(DispatchReader):
            if name.startswith("_"):
                continue
            assert not name.startswith(self.WRITE_PREFIXES), (
                f"DispatchReader.{name} looks like a write path"
            )

    def test_every_declared_read_is_a_real_dispatch_function(self):
        """READ_METHODS is the audit surface: one tuple answers 'what can the
        Assistant see'. A row naming a function that does not exist would make
        that answer a fiction."""
        store = pytest.importorskip("dispatch.store")
        for _reader_method, dotted in READ_METHODS:
            module, _, func = dotted.partition(".")
            assert module == "store", dotted
            assert hasattr(store, func), f"{dotted} does not exist"

    def test_none_of_the_declared_reads_is_a_write(self):
        for _reader_method, dotted in READ_METHODS:
            func = dotted.split(".")[-1]
            assert not func.startswith(self.WRITE_PREFIXES), dotted

    def test_the_reader_exposes_exactly_what_it_declares(self):
        declared = {name for name, _ in READ_METHODS}
        public = {
            name for name in dir(DispatchReader)
            if not name.startswith("_") and callable(getattr(DispatchReader, name))
        }
        assert public == declared, (
            f"reader surface and READ_METHODS disagree: "
            f"only on the reader {public - declared}, only declared {declared - public}"
        )


# ── assembly ─────────────────────────────────────────────────────────────


class TestBuildingTheBus:
    def test_all_four_workers_are_registered(self):
        assert set(build_bus().registered()) == {
            "INTELLIGENCE", "PUBLISHER", "JOE", "LIBRARY"
        }

    def test_it_does_not_raise_when_dispatch_cannot_be_imported(self, monkeypatch):
        """§5.4: degradation is permitted, incapacity is not. A plug-in that
        cannot start is worse than one that says it has nothing to read."""
        import worker_bus.host as host

        monkeypatch.setattr(host, "dispatch_available", lambda: False)
        bus = host.build_bus()
        statuses = {r["worker"]: r["status"] for r in bus.roster()}
        assert statuses["INTELLIGENCE"] == "UNCONFIGURED"
        assert statuses["PUBLISHER"] == "UNCONFIGURED"
        assert statuses["JOE"] == "UNCONFIGURED"

    def test_a_reader_can_be_injected(self):
        sentinel = object()
        bus = build_bus(reader=sentinel)
        assert bus.get("JOE").reader is sentinel

    def test_joe_has_no_reasoner_unless_one_is_given(self):
        """Defaulting one in would claim a capability nobody configured. He
        reads back facts without one and says CONFIGURED, not LIVE."""
        assert build_bus().get("JOE").reasoner is None
        marker = object()
        assert build_bus(reasoner=marker).get("JOE").reasoner is marker

    def test_describe_reports_status_without_running_anything(self):
        described = describe()
        assert set(described) >= {"dispatch_readable", "plugin_present", "workers"}
        assert isinstance(described["dispatch_readable"], bool)
        for row in described["workers"]:
            assert row["status"] in {
                "LIVE", "CONFIGURED", "UNCONFIGURED", "SIMULATED",
                "UNAVAILABLE", "MANUAL", "ABSENT", "UNVERIFIED",
            }


class TestThePluginPath:
    def test_it_puts_the_plugin_where_joe_can_import_it(self):
        """Joe imports `conversation.readback` as a top-level package. Under
        pytest the repo conftest arranges that; nothing arranged it anywhere
        else, so Joe raised ModuleNotFoundError the first time a real host asked
        him to read a load."""
        assert ensure_plugin_importable() is True
        assert any(p.endswith("Assistant_Plugin") for p in sys.path)

    def test_it_is_idempotent(self):
        ensure_plugin_importable()
        before = sys.path.count(next(p for p in sys.path if p.endswith("Assistant_Plugin")))
        ensure_plugin_importable()
        after = sys.path.count(next(p for p in sys.path if p.endswith("Assistant_Plugin")))
        assert before == after


class TestJoeDegradesRatherThanCrashing:
    def test_a_missing_conversation_layer_is_unconfigured_not_a_traceback(self, monkeypatch):
        """UNCONFIGURED means not set up. UNAVAILABLE means it should be
        reachable and is not. A raw ModuleNotFoundError in `detail` is neither
        -- it is a traceback, and a driver reading it learns nothing.

        The reader has to answer, or Joe fails earlier for a different reason
        and this proves nothing.
        """
        class Reader:
            def get_load(self, load_id):
                return {"load_id": load_id, "delivery_location": "Houston TX",
                        "delivery_datetime": "2026-07-30 16:00 - 20:00",
                        "status": "dispatched"}

            def list_milestones(self, load_id):
                return []

        import builtins

        real_import = builtins.__import__

        def refuse_conversation(name, *args, **kwargs):
            if name.startswith("conversation"):
                raise ImportError("No module named 'conversation'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", refuse_conversation)
        response = build_bus(reader=Reader()).ask("JOE", WorkerRequest(
            capability="read_back_load", payload={"load_id": "LOAD-X"},
            requested_by="test",
        ))
        assert response.status == "UNCONFIGURED", response.detail
        assert "not installed on this machine" in response.detail
        assert "Traceback" not in response.detail


# ── the duties, against a real Dispatch ──────────────────────────────────


@pytest.fixture()
def seeded(tmp_path, monkeypatch):
    pytest.importorskip("dispatch")
    monkeypatch.setenv("PORTAL_DATA_DIR", str(tmp_path / "portal"))
    from dispatch import db, services

    db.set_db_path(tmp_path / "portal" / "dispatch.db")
    try:
        driver = services.create_driver(name="Jane Trucker", phone="555-0000")
        load = services.create_load(
            customer="Host Co", broker_shipper="TQL", driver_id=driver["driver_id"],
            pickup_location="Dallas TX", delivery_location="Houston TX",
            pickup_datetime="2026-07-30 06:00 - 10:00",
            delivery_datetime="2026-07-30 16:00 - 20:00",
        )
        services.add_milestone(load["load_id"], event_type="dispatched")
        yield load["load_id"]
    finally:
        db.set_db_path(None)


def _ask(bus, worker, capability, load_id):
    return bus.ask(worker, WorkerRequest(
        capability=capability, payload={"load_id": load_id}, requested_by="test",
    ))


class TestTheDutiesAgainstARealLoad:
    def test_dispatch_is_readable_from_the_host(self, seeded):
        assert dispatch_available() is True

    def test_intelligence_analyses_a_real_load(self, seeded):
        """Constitution: Intelligence 'extracts, analyzes, classifies, and
        structures ... risks and operational considerations'."""
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", seeded)
        assert response.status == "LIVE", response.detail
        assert response.findings
        assert "NO_RATE_ON_FILE" in {f.code for f in response.findings}

    def test_publisher_detects_the_gaps_in_a_real_load(self, seeded):
        """Constitution §10: Publisher may 'detect gaps'."""
        response = _ask(build_bus(), "PUBLISHER", "check_readiness", seeded)
        assert response.status == "LIVE", response.detail
        codes = {f.code for f in response.findings}
        assert {"RATE_MISSING", "POD_MISSING"} <= codes, codes

    def test_joe_reads_the_load_back_in_one_sentence(self, seeded):
        """DRIVER_FIRST_DOCTRINE_v2 D2, the 70 MPH test."""
        response = _ask(build_bus(), "JOE", "read_back_load", seeded)
        assert response.status == "LIVE", response.detail
        assert response.detail
        assert response.detail.count(".") <= 2, response.detail

    def test_no_worker_writes_anything(self, seeded):
        """§5.4 again, measured rather than trusted: ask every worker and check
        that not one row anywhere moved."""
        import hashlib

        from dispatch import db

        def fingerprint():
            with db.get_connection() as conn:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                counts = [f"{t}={conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}"
                          for t in tables]
            return hashlib.sha256("|".join(counts).encode()).hexdigest()

        bus = build_bus()
        before = fingerprint()
        for worker, capability in (("INTELLIGENCE", "assess_load"),
                                   ("PUBLISHER", "check_readiness"),
                                   ("JOE", "read_back_load")):
            _ask(bus, worker, capability, seeded)
        assert fingerprint() == before, "a worker changed Dispatch"


# ── the lane-history comparison, against a real Dispatch ─────────────────
#
# This branch is only reachable once a load has a rate confirmation, and no
# fixture ever seeded one. `assess_load` read `average_revenue` off
# `store.get_lane_history()`, which is typed `list[dict]` and has no such key,
# so every rate-confirmed load raised AttributeError and the bus degraded it to
# UNAVAILABLE. Nothing failed; the capability simply never worked.
#
# These tests seed the rate confirmation the others omit.


@pytest.fixture()
def priced_lane(tmp_path, monkeypatch):
    """Three Dallas->Houston loads: two priced history, one under assessment."""
    pytest.importorskip("dispatch")
    monkeypatch.setenv("PORTAL_DATA_DIR", str(tmp_path / "portal"))
    from dispatch import db, services, store
    from dispatch.models import RateConfirmation

    db.set_db_path(tmp_path / "portal" / "dispatch.db")
    try:
        made = []
        for amount in (3000.0, 3000.0, 1000.0):
            load = services.create_load(
                customer="Lane Co", broker_shipper="TQL",
                pickup_location="Dallas TX", delivery_location="Houston TX",
                pickup_datetime="2026-07-30 06:00 - 10:00",
                delivery_datetime="2026-07-30 16:00 - 20:00",
            )
            store.create_rate_confirmation(RateConfirmation(
                confirmation_id="", load_id=load["load_id"], rate_amount=amount,
                rate_type="flat", distance_miles=240.0, confirmed_by="TQL", notes="",
            ))
            made.append(load["load_id"])
        yield made          # [prior, prior, the cheap one]
    finally:
        db.set_db_path(None)


class TestTheLaneComparison:
    def test_a_rate_confirmed_load_does_not_crash(self, priced_lane):
        """The whole defect in one assertion: this returned UNAVAILABLE."""
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", priced_lane[0])
        assert response.status == "LIVE", response.detail
        assert "AttributeError" not in response.detail

    def test_a_low_rate_is_noticed(self, priced_lane):
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", priced_lane[2])
        codes = {f.code for f in response.findings}
        assert "RATE_BELOW_LANE_HISTORY" in codes, codes
        finding = next(f for f in response.findings if f.code == "RATE_BELOW_LANE_HISTORY")
        assert "3000.00" in finding.summary          # the average of the two priors
        assert "2 previous priced load(s)" in finding.detail
        assert finding.requires_human_review

    def test_a_rate_at_the_going_rate_is_not_noticed(self, priced_lane):
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", priced_lane[0])
        assert "RATE_BELOW_LANE_HISTORY" not in {f.code for f in response.findings}

    def test_the_load_is_not_compared_against_itself(self, priced_lane):
        """A lane of one priced load has no history to compare to. Including the
        load under assessment would make it its own benchmark and never fire."""
        from dispatch import services, store
        from dispatch.models import RateConfirmation
        alone = services.create_load(
            customer="Solo Co", broker_shipper="TQL",
            pickup_location="Reno NV", delivery_location="Boise ID",
        )
        store.create_rate_confirmation(RateConfirmation(
            confirmation_id="", load_id=alone["load_id"], rate_amount=50.0,
            rate_type="flat", distance_miles=400.0, confirmed_by="TQL", notes="",
        ))
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", alone["load_id"])
        assert response.status == "LIVE"
        assert "RATE_BELOW_LANE_HISTORY" not in {f.code for f in response.findings}

    def test_an_unpriced_lane_yields_no_average(self, priced_lane):
        """Prior loads with no rate confirmation contribute nothing. Treating a
        missing rate as zero would drag the average down and suppress the very
        finding this exists to raise."""
        from dispatch import services, store
        from dispatch.models import RateConfirmation
        for _ in range(2):
            services.create_load(
                customer="Unpriced Co", broker_shipper="TQL",
                pickup_location="Ogden UT", delivery_location="Elko NV",
            )
        subject = services.create_load(
            customer="Unpriced Co", broker_shipper="TQL",
            pickup_location="Ogden UT", delivery_location="Elko NV",
        )
        store.create_rate_confirmation(RateConfirmation(
            confirmation_id="", load_id=subject["load_id"], rate_amount=10.0,
            rate_type="flat", distance_miles=300.0, confirmed_by="TQL", notes="",
        ))
        response = _ask(build_bus(), "INTELLIGENCE", "assess_load", subject["load_id"])
        assert response.status == "LIVE"
        assert "RATE_BELOW_LANE_HISTORY" not in {f.code for f in response.findings}
