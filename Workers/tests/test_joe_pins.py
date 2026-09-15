"""Joe performs the Library PIN Service's work: portal entry for Operations, Driver, Customer.

Mike Zachary, 2026-09-13: an Operations PIN is authorized by Mike Zachary by voice or in the
dialog box with Joe; drivers choose their own PIN; a customer's load number is their PIN.
"""

from __future__ import annotations

import json

import pytest

from worker_bus.audit import AuditLog
from worker_bus.bus import WorkerBus
from worker_bus.contracts import WorkerRequest
from worker_bus.host import ensure_library_importable
from worker_bus.workers.joe import JoeWorker

MIKE = "Mike Zachary"


@pytest.fixture
def library(tmp_path):
    if not ensure_library_importable():
        pytest.skip("Library repo is not on this machine")
    from dispatch_library.catalog import open_library

    lib = open_library(tmp_path / "catalog.db")
    yield lib
    lib.close()


@pytest.fixture
def bus(tmp_path, library):
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    b = WorkerBus(audit=audit)
    b.register(JoeWorker(pins=library.pins))
    return b


def ask(bus, capability, **payload):
    return bus.ask("JOE", WorkerRequest(capability=capability, payload=payload, requested_by="OPERATOR"))


def test_joe_serves_all_three_portals(bus, library):
    assert ask(bus, "pin_create", role="operations", name=MIKE, pin="7301", for_person=MIKE,
               channel="dialog").status == "LIVE"
    library.pins.add_driver_pin("4418")  # entered at the Driver portal's PIN window
    assert ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE).status == "LIVE"

    answers = {
        role: ask(bus, "pin_validate", role=role, pin=pin, client_key="tablet", **extra).artifacts["answer"]
        for role, pin, extra in (("operations", "7301", {}), ("driver", "4418", {}), ("customer", "8842193", {}))
    }
    assert [answers[r]["role"] for r in ("operations", "driver", "customer")] == ["Operations", "Driver", "Customer"]
    assert answers["customer"]["display_name"] == "XPO Logistics"
    denied = ask(bus, "pin_validate", role="customer", pin="1111111", client_key="tablet")
    assert (denied.detail, denied.artifacts["answer"]) == ("Denied", {"result": "Denied"})


@pytest.mark.parametrize("channel", ["voice", "DIALOG"])
def test_mike_authorizes_operations_by_voice_or_dialog(bus, channel):
    assert ask(bus, "pin_create", role="operations", name="Dana Cole", pin="7301", for_person=MIKE,
               channel=channel).status == "LIVE"


@pytest.mark.parametrize("who,channel", [(MIKE, ""), (MIKE, "email"), ("Dana Cole", "dialog")])
def test_operations_otherwise_is_refused(bus, who, channel):
    response = ask(bus, "pin_create", role="operations", name="Dana Cole", pin="7301", for_person=who, channel=channel)
    assert response.refused and "Mike Zachary" in response.refusal.reason


def test_joe_does_not_assign_a_driver_pin_he_retires_one(bus, library):
    assert ask(bus, "pin_create", role="driver", name="Ray Vasquez", pin="4418", for_person=MIKE).refused
    library.pins.add_driver_pin("4418")  # entered at the Driver portal's PIN window
    retired = ask(bus, "pin_retire", role="driver", pin="4418", for_person=MIKE)
    assert retired.status == "LIVE" and "4418" not in retired.detail
    assert ask(bus, "pin_validate", role="driver", pin="4418").detail == "Denied"


def test_joe_disables_and_enables(bus, library):
    library.pins.add_driver_pin("4418")
    ask(bus, "pin_disable", role="driver", name="Drivers", for_person=MIKE)
    assert ask(bus, "pin_validate", role="driver", pin="4418").detail == "Denied"
    ask(bus, "pin_enable", role="driver", name="Drivers", for_person=MIKE)
    assert ask(bus, "pin_validate", role="driver", pin="4418").detail == "Authenticated"


def test_joe_acts_for_a_person_not_for_himself(bus):
    for who in ("", "Joe", "JOE", "system"):
        response = ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=who)
        assert response.refused, who


def test_joe_says_why_a_second_customer_cannot_take_a_load_number(bus):
    ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE)
    response = ask(bus, "pin_add_customer_load", customer="Werner", load_number="8842193", for_person=MIKE)
    assert response.refused
    assert "XPO Logistics" in response.refusal.reason


def test_no_pin_reaches_the_audit_log_or_a_response(bus, tmp_path):
    responses = [
        ask(bus, "pin_create", role="operations", name=MIKE, pin="730155", for_person=MIKE, channel="voice"),
        ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE),
        ask(bus, "pin_validate", role="operations", pin="730155", client_key="tablet"),
        ask(bus, "pin_validate", role="customer", pin="8842193", client_key="tablet"),
    ]
    trail = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    everything = trail + json.dumps([r.to_dict() for r in responses], default=str)
    assert "730155" not in everything
    assert "8842193" not in everything


def test_without_the_persistent_library_joe_says_so():
    bus = WorkerBus()
    bus.register(JoeWorker())
    answer = bus.ask("JOE", WorkerRequest(capability="pin_validate", payload={"role": "driver", "pin": "4418"},
                                          requested_by="OPERATOR"))
    assert answer.status == "UNCONFIGURED"
