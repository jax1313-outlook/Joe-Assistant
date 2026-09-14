"""Joe performs the Library PIN Service's work: portal entry for Operations, Driver, Customer."""

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
def bus(tmp_path):
    if not ensure_library_importable():
        pytest.skip("Library repo is not on this machine")
    from dispatch_library.catalog import open_library

    library = open_library(tmp_path / "catalog.db")
    audit = AuditLog(path=tmp_path / "audit.jsonl")
    b = WorkerBus(audit=audit)
    b.register(JoeWorker(pins=library.pins))
    yield b
    library.close()


def ask(bus, capability, **payload):
    return bus.ask("JOE", WorkerRequest(capability=capability, payload=payload, requested_by="OPERATOR"))


def test_joe_creates_and_validates_for_all_three_portals(bus):
    assert ask(bus, "pin_create", role="operations", name=MIKE, pin="7301", for_person=MIKE).status == "LIVE"
    assert ask(bus, "pin_create", role="driver", name="Ray Vasquez", pin="4418", for_person=MIKE,
               subject_ref="DRV-0007").status == "LIVE"
    assert ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE).status == "LIVE"

    answers = {
        role: ask(bus, "pin_validate", role=role, pin=pin, client_key="tablet").artifacts["answer"]
        for role, pin in (("operations", "7301"), ("driver", "4418"), ("customer", "8842193"))
    }
    assert [answers[r]["role"] for r in ("operations", "driver", "customer")] == ["Operations", "Driver", "Customer"]
    assert answers["customer"]["display_name"] == "XPO Logistics"
    denied = ask(bus, "pin_validate", role="customer", pin="1111111", client_key="tablet")
    assert (denied.detail, denied.artifacts["answer"]) == ("Denied", {"result": "Denied"})


def test_joe_resets_enables_and_disables(bus):
    ask(bus, "pin_create", role="driver", name="Ray Vasquez", pin="4418", for_person=MIKE)
    ask(bus, "pin_reset", role="driver", name="Ray Vasquez", pin="9926", for_person=MIKE)
    assert ask(bus, "pin_validate", role="driver", pin="4418").detail == "Denied"
    ask(bus, "pin_disable", role="driver", name="Ray Vasquez", for_person=MIKE)
    assert ask(bus, "pin_validate", role="driver", pin="9926").detail == "Denied"
    ask(bus, "pin_enable", role="driver", name="Ray Vasquez", for_person=MIKE)
    assert ask(bus, "pin_validate", role="driver", pin="9926").detail == "Authenticated"


def test_joe_acts_for_a_person_not_for_himself(bus):
    for who in ("", "Joe", "JOE", "system"):
        response = ask(bus, "pin_create", role="driver", name="Ray Vasquez", pin="4418", for_person=who)
        assert response.refused, who


def test_joe_says_why_a_second_customer_cannot_take_a_load_number(bus):
    ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE)
    response = ask(bus, "pin_add_customer_load", customer="Werner", load_number="8842193", for_person=MIKE)
    assert response.refused
    assert "XPO Logistics" in response.refusal.reason


def test_no_pin_reaches_the_audit_log_or_a_response(bus, tmp_path):
    responses = [
        ask(bus, "pin_create", role="driver", name="Ray Vasquez", pin="44187", for_person=MIKE),
        ask(bus, "pin_add_customer_load", customer="XPO Logistics", load_number="8842193", for_person=MIKE),
        ask(bus, "pin_validate", role="driver", pin="44187", client_key="tablet"),
        ask(bus, "pin_validate", role="customer", pin="8842193", client_key="tablet"),
    ]
    trail = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    everything = trail + json.dumps([r.to_dict() for r in responses], default=str)
    assert "44187" not in everything
    assert "8842193" not in everything


def test_without_the_persistent_library_joe_says_so():
    bus = WorkerBus()
    bus.register(JoeWorker())
    answer = bus.ask("JOE", WorkerRequest(capability="pin_validate", payload={"role": "driver", "pin": "4418"},
                                          requested_by="OPERATOR"))
    assert answer.status == "UNCONFIGURED"
