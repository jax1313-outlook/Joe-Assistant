"""The steps of Phase A, each one a whole process. Run by phase_a_separate_processes.py.

    python Testing/phase_a_steps.py STEP WORKSPACE

Every step opens what it needs, does one thing, prints one JSON line, and exits. Nothing is
carried from one step to the next except what the real stores remember: the Library catalog,
the Dispatch database, the Archive outbox, and a small state file naming the load.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

OPERATOR = "Phase A Certification Operator"
OPS = "ops@l1truck.com"
STATE = "phase_a_state.json"

BROKER_TEMPLATE = """CLOSEOUT — Load {load_id}
{pickup} -> {delivery}
Delivered {delivered_on}.  POD on file: {pod_id}
Evidence items attached: {evidence_count}
Rate: {rate}
Level 1 Transport Inc."""

CUSTOMER_TEMPLATE = """Your shipment has been delivered.
Load {load_id}, {pickup} to {delivery}.
Proof of delivery is on file."""


def _state(ws: Path) -> dict:
    path = ws / STATE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save(ws: Path, **values) -> None:
    state = _state(ws)
    state.update(values)
    (ws / STATE).write_text(json.dumps(state, indent=2), encoding="utf-8")


def library():
    from worker_bus.host import library_persistent, library_service

    service = library_service()
    assert service is not None and library_persistent(), "the persistent Library is not configured"
    return service


def place_templates(ws: Path) -> dict:
    from dispatch_library.catalog import CatalogRefusal, MissingObjectType

    lib = library()
    placed = []
    for code, title, body in (("TPL-BROKER-CLOSEOUT", "Broker closeout notice", BROKER_TEMPLATE),
                              ("TPL-CUSTOMER-DELIVERED", "Customer delivery notice", CUSTOMER_TEMPLATE)):
        obj = lib.ingest_human_document(code, "Templates", title, body, OPERATOR, ["closeout"],
                                        object_type="FORM_TEMPLATE")
        placed.append({"code": obj.object_code, "version": obj.version_label, "state": obj.lifecycle_state,
                       "accepted_by": obj.accepted_by})
    refusals = {}
    try:
        lib.ingest_human_document("TPL-BAD", "Templates", "x", "x", "PUBLISHER", object_type="FORM_TEMPLATE")
        refusals["PUBLISHER as approver"] = "NOT REFUSED"
    except CatalogRefusal as exc:
        refusals["PUBLISHER as approver"] = str(exc)
    try:
        lib.ingest_human_document("TPL-UNTYPED", "Templates", "x", "x", OPERATOR)
        refusals["no object_type"] = "NOT REFUSED"
    except MissingObjectType as exc:
        refusals["no object_type"] = f"refused; notice {exc.notice_id}"
    return {"placed": placed, "refusals": refusals, "pid": os.getpid()}


def seed_load(ws: Path) -> dict:
    from dispatch import db, services, store
    from dispatch.models import EvidenceItem, PODPackage, RateConfirmation

    db.set_db_path(Path(os.environ["PORTAL_DATA_DIR"]) / "dispatch.db")
    driver = services.create_driver(name="Ray Vasquez", phone="904-555-0142")
    load = services.create_load(
        customer="Acme Foods", broker_shipper="TQL", driver_id=driver["driver_id"],
        pickup_location="Jacksonville FL", delivery_location="Savannah GA",
        pickup_datetime="2026-09-11 06:00 - 10:00", delivery_datetime="2026-09-12 13:00 - 17:00")
    load_id = load["load_id"]
    store.create_rate_confirmation(RateConfirmation(
        confirmation_id="", load_id=load_id, rate_amount=2850.00, rate_type="flat",
        distance_miles=142.0, confirmed_by="TQL", notes="Test load — Phase A separate processes"))
    pod_file = ws / "pod.txt"
    pod_file.write_text("SIGNED PROOF OF DELIVERY — Acme Foods — 2026-09-12", encoding="utf-8")
    ev = store.create_evidence(EvidenceItem(
        evidence_id="", load_id=load_id, related_milestone_id="", evidence_type="pod",
        file_path=str(pod_file), original_filename="pod.txt", file_size=pod_file.stat().st_size,
        mime_type="text/plain", capture_time="", description="Signed POD", uploaded_by="Ray Vasquez",
        checksum=hashlib.sha256(pod_file.read_bytes()).hexdigest()))
    pod = store.create_pod(PODPackage(
        pod_id="", load_id=load_id, evidence_ids=[ev["evidence_id"]], generated_at="", status="delivered",
        recipient="TQL", file_path=str(pod_file), notes=""))
    for event in ("dispatched", "loaded", "in_transit", "delivered"):
        services.add_milestone(load_id, event_type=event)
    _save(ws, load_id=load_id, pod_id=pod["pod_id"])
    return {"load_id": load_id, "pod_id": pod["pod_id"], "pid": os.getpid()}


def _bus():
    from worker_bus.host import build_bus

    return build_bus()


def _ask(capability, worker="PUBLISHER", **kw):
    from worker_bus.contracts import WorkerRequest

    return _bus().ask(worker, WorkerRequest(capability=capability, requested_by="OPERATOR", **kw))


def assemble(ws: Path) -> dict:
    from dispatch import db, services

    db.set_db_path(Path(os.environ["PORTAL_DATA_DIR"]) / "dispatch.db")
    load_id = _state(ws)["load_id"]
    refused = _ask("assemble_completion_package", payload={"load_id": load_id})
    decision = services.add_milestone(
        load_id, event_type="checkpoint",
        note=f"{OPERATOR} approved release of the completion package (Phase A certification test).")
    ref = f"milestone:{decision['milestone_id']}"
    assembled = _ask("assemble_completion_package", payload={"load_id": load_id, "template_id": "TPL-BROKER-CLOSEOUT"},
                     authorized_by=OPERATOR, authorization_ref=ref)
    return {"without_authorisation": {"status": refused.status,
                                      "rule": refused.refusal.rule if refused.refusal else None},
            "with_authorisation": {"status": assembled.status, "detail": assembled.detail,
                                   "review_required": assembled.artifacts.get("review_required"),
                                   "summary": assembled.artifacts.get("package", {}).get("summary_lines")},
            "decision_ref": ref, "pid": os.getpid()}


def review_due_block(ws: Path) -> dict:
    from dispatch import db

    db.set_db_path(Path(os.environ["PORTAL_DATA_DIR"]) / "dispatch.db")
    load_id = _state(ws)["load_id"]
    lib = library()
    lib.set_lifecycle("TPL-CUSTOMER-DELIVERED", "REVIEW_DUE")
    blocked = _ask("check_readiness", payload={"load_id": load_id, "template_id": "TPL-CUSTOMER-DELIVERED"})
    lib.set_lifecycle("TPL-CUSTOMER-DELIVERED", "CURRENT", by=OPERATOR)
    return {"readiness_status": blocked.status, "detail": blocked.detail,
            "findings": [f.code for f in blocked.findings],
            "external_after_renewal": lib.current_for_external_use("TPL-CUSTOMER-DELIVERED") is not None,
            "pid": os.getpid()}


def compose(ws: Path) -> dict:
    from dispatch import comi_routing, db, store
    from portal.models import email_helper

    db.set_db_path(Path(os.environ["PORTAL_DATA_DIR"]) / "dispatch.db")
    state = _state(ws)
    load_id = state["load_id"]
    load = store.get_load(load_id)
    template = library().current_for_external_use("TPL-BROKER-CLOSEOUT", purpose="Phase A closeout",
                                                  consumer_role="PUBLISHER")
    rate = store.get_rate_confirmation(load_id)
    rendered = template.body_or_uri.format(
        load_id=load_id, pickup=load["pickup_location"], delivery=load["delivery_location"],
        delivered_on="2026-09-12", pod_id=state["pod_id"], evidence_count=len(store.list_evidence(load_id)),
        rate=f"{rate['revenue']:.2f}")
    internal = {"load_id": load_id, "pickup_location": load["pickup_location"],
                "delivery_location": load["delivery_location"], "revenue": 2850.00, "profit": 910.00,
                "margin_pct": 31.9, "total_expenses": 1940.00, "internal_note": "Broker was slow to pay."}
    broker_view = comi_routing.sanitize_payload_for_role(internal, "broker")
    draft = email_helper.create_draft(load_id=load_id, load=load,
                                      broker_contact={"email": OPS, "name": "Level 1 Operations"},
                                      pod_id=state["pod_id"], invoice_number="INV-PHASE-A-SEP-001")
    email_helper.update_draft(load_id, broker_email=OPS, broker_body=rendered,
                              broker_subject=f"Closeout — {load_id} — Jacksonville FL to Savannah GA",
                              customer_email="")
    try:
        email_helper.submit_package(load_id, submitted_by="PUBLISHER")
        system_submit = "NOT REFUSED"
    except Exception as exc:  # noqa: BLE001
        system_submit = f"refused: {exc}"
    submitted = email_helper.submit_package(load_id, submitted_by=OPERATOR)
    return {"template": f"{template.object_code} v{template.version_label} {template.lifecycle_state}",
            "rendered_first_line": rendered.splitlines()[0], "withheld_from_broker": sorted(set(internal) - set(broker_view)),
            "draft_status": draft["status"], "system_submit": system_submit, "submitted_status": submitted["status"],
            "send_results": submitted.get("send_results", []), "pid": os.getpid()}


def read_outbox(ws: Path) -> dict:
    """Read back what the transport wrote, on either Dispatch line.

    `sandbox/phase2-corrections` has `dispatch.transport` and reports the transport's status;
    `joe/capture-to-card` has `dispatch.mail` with its own outbox and no status module. Both
    outboxes are searched, and a missing status is reported as missing rather than invented.
    """
    from cin_lite import email_delivery

    outboxes = {Path(email_delivery.outbox_dir() if hasattr(email_delivery, "outbox_dir")
                     else email_delivery._OUTBOX)}
    try:
        from dispatch import mail

        outboxes.add(Path(getattr(mail, "_OUTBOX")))
    except (ImportError, AttributeError):
        pass
    try:
        from dispatch.transport import selection

        transport = selection.outbound_status()
    except ImportError:
        transport = {"status": "not reported: this Dispatch has no dispatch.transport", "delivering": None}
    outbox = sorted({p for box in outboxes if box.exists() for p in box.rglob("*.eml")})
    messages = []
    for path in outbox:
        text = path.read_text(encoding="utf-8", errors="replace")
        headers = {k: v for k, v in (line.split(": ", 1) for line in text.splitlines()[:20] if ": " in line)}
        messages.append({"file": path.name, "to": headers.get("To"), "subject": headers.get("Subject"),
                         "body_has_template": "CLOSEOUT — Load" in text})
    return {"eml_files": messages, "outboxes": sorted(str(b) for b in outboxes), "transport": transport,
            "pid": os.getpid()}


def library_record(ws: Path) -> dict:
    lib = library()
    events = lib.catalog.retrieval_events()
    return {"counts": lib.catalog.counts(),
            "templates": [{"code": o.object_code, "version": o.version_label, "state": o.lifecycle_state,
                           "accepted_by": o.accepted_by} for o in lib.list_current("Templates")],
            "retrievals_by_role": sorted({(e["consumer_role"], e["outcome"]) for e in events}),
            "open_notices": [(n["notice_type"], n["missing_field"]) for n in lib.notices()],
            "pid": os.getpid()}


STEPS = {"place_templates": place_templates, "seed_load": seed_load, "assemble": assemble,
         "review_due_block": review_due_block, "compose": compose, "read_outbox": read_outbox,
         "library_record": library_record}

if __name__ == "__main__":
    step, workspace = sys.argv[1], Path(sys.argv[2])
    print(json.dumps(STEPS[step](workspace), default=str))
