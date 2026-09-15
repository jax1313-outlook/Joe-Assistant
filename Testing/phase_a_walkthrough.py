"""PHASE A -- Library -> Publisher -> COMI -> Email Helper -> a composed message.

Everything except delivery. No Microsoft, no tenant, no credentials, and the
recipient address is the one Mike named: ops@l1truck.com. The last step opens
the .eml the transport actually wrote and reads it back, because a step that
reports success without looking at what it produced is how the whole class of
defect this walkthrough exists to catch stays hidden.

It is not a test. It is the thing a test double stands in for -- the real
Library, the real Dispatch store, the real worker bus, the real COMI
sanitiser, the real Email Helper. Run it, read it, and disbelieve anything it
does not print.

    PYTHONPATH=/path/to/Dispatch python Testing/phase_a_walkthrough.py

Every run works in a fresh temporary directory and leaves the repo alone.

What it found the first two times it was run is recorded in TEST_EVIDENCE.md
section 9. Nothing below was written to make those defects appear; they were
already there, under passing tests.
"""
import hashlib, json, os, sys, tempfile
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)
tmp = Path(tempfile.mkdtemp(prefix="phase-a-"))
os.environ["PORTAL_DATA_DIR"] = str(tmp / "portal")
os.environ["DISPATCH_ARCHIVE_ROOT"] = str(tmp / "Archive")
_WORK = Path(ROOT).parent
sys.path[:0] = [f"{ROOT}/Workers", f"{ROOT}/Assistant_Plugin",
                str(_WORK / "Dispatch"), str(_WORK / "Library" / "src")]

STEP = 0
def step(title):
    global STEP
    STEP += 1
    print(f"\n{'='*72}\n  STEP {STEP}.  {title}\n{'='*72}")

OPS = "ops@l1truck.com"

# ─────────────────────────────────────────────────────── 1. the Library
step("Place two approved templates in the real Library")
from worker_bus.host import library_service
library = library_service()   # the same shelf the bus hands PUBLISHER
assert library is not None, "Library not importable — Phase A cannot run"

BROKER_TEMPLATE = """CLOSEOUT — Load {load_id}
{pickup} -> {delivery}
Delivered {delivered_on}.  POD on file: {pod_id}
Evidence items attached: {evidence_count}
Rate: {rate}
Level 1 Transport Inc."""

CUSTOMER_TEMPLATE = """Your shipment has been delivered.
Load {load_id}, {pickup} to {delivery}.
Proof of delivery is on file."""

for code, title, body in (
    ("TPL-BROKER-CLOSEOUT", "Broker closeout notice", BROKER_TEMPLATE),
    ("TPL-CUSTOMER-DELIVERED", "Customer delivery notice", CUSTOMER_TEMPLATE),
):
    obj = library.ingest_human_document(
        object_code=code, collection="Templates", title=title,
        body_or_uri=body, accepted_by="Mike Zachary", tags=["closeout"],
    )
    print(f"  {obj.object_code:<26} v{obj.version}  {obj.status.value:<9} "
          f"accepted_by={obj.accepted_by}")

print("\n  refusal check — a system identity may not accept a Library object:")
try:
    library.ingest_human_document(
        object_code="TPL-BAD", collection="Templates", title="x",
        body_or_uri="x", accepted_by="PUBLISHER")
    print("    NOT REFUSED  <-- defect")
except ValueError as exc:
    print(f"    refused: {exc}")

# ─────────────────────────────────────────────────── 2. a complete load
step("Seed one complete test load in Dispatch")
from dispatch import db, services, store
from dispatch.models import RateConfirmation, EvidenceItem, PODPackage
db.set_db_path(tmp / "portal" / "dispatch.db")

driver = services.create_driver(name="Ray Vasquez", phone="904-555-0142")
load = services.create_load(
    customer="Acme Foods", broker_shipper="TQL", driver_id=driver["driver_id"],
    pickup_location="Jacksonville FL", delivery_location="Savannah GA",
    pickup_datetime="2026-09-11 06:00 - 10:00",
    delivery_datetime="2026-09-12 13:00 - 17:00",
)
LOAD_ID = load["load_id"]
store.create_rate_confirmation(RateConfirmation(
    confirmation_id="", load_id=LOAD_ID, rate_amount=2850.00, rate_type="flat",
    distance_miles=142.0, confirmed_by="TQL", notes="Test load — Phase A"))

pod_file = tmp / "pod.txt"
pod_file.write_text("SIGNED PROOF OF DELIVERY — Acme Foods — 2026-09-12", encoding="utf-8")
ev = store.create_evidence(EvidenceItem(
    evidence_id="", load_id=LOAD_ID, related_milestone_id="", evidence_type="pod",
    file_path=str(pod_file), original_filename="pod.txt",
    file_size=pod_file.stat().st_size, mime_type="text/plain", capture_time="",
    description="Signed POD", uploaded_by="Ray Vasquez",
    checksum=hashlib.sha256(pod_file.read_bytes()).hexdigest()))
pod = store.create_pod(PODPackage(
    pod_id="", load_id=LOAD_ID, evidence_ids=[ev["evidence_id"]], generated_at="",
    status="delivered", recipient="TQL", file_path=str(pod_file), notes=""))
for event in ("dispatched", "loaded", "in_transit", "delivered"):
    services.add_milestone(LOAD_ID, event_type=event)

print(f"  load {LOAD_ID}  {load['pickup_location']} -> {load['delivery_location']}")
print(f"  rate 2850.00 · pod {pod['pod_id']} · evidence 1 · milestones 4")

# ─────────────────────────────────────────────── 3. Publisher readiness
step("PUBLISHER check_readiness, asking the real Library for the template")
from worker_bus.__main__ import main as cli
rc = cli(["ask", "PUBLISHER", "check_readiness",
          f"load_id={LOAD_ID}", "template_id=TPL-BROKER-CLOSEOUT"])
print(f"  exit {rc}")

# ─────────────────────────────────────────── 4. the human authorisation
step("Assemble — refused without a recorded human decision, then with one")
from worker_bus.contracts import WorkerRequest
from worker_bus.host import build_bus
bus = build_bus()

def ask(worker, capability, **kw):
    return bus.ask(worker, WorkerRequest(capability=capability, requested_by="OPERATOR", **kw))

refused = ask("PUBLISHER", "assemble_completion_package", payload={"load_id": LOAD_ID})
print(f"  without authorisation: {refused.status}")
print(f"    refused under {refused.refusal.rule}: {refused.refusal.reason}")
print(f"    {refused.refusal.remedy}")

DECISION = services.add_milestone(
    LOAD_ID, event_type="checkpoint",
    note="Mike Zachary approved release of the completion package (Phase A test).")
DECISION_REF = f"milestone:{DECISION['milestone_id']}"
print(f"\n  decision recorded in Dispatch: {DECISION_REF}")

assembled = ask("PUBLISHER", "assemble_completion_package",
                payload={"load_id": LOAD_ID, "template_id": "TPL-BROKER-CLOSEOUT"},
                authorized_by="Mike Zachary", authorization_ref=DECISION_REF)
print(f"  with authorisation:    {assembled.status}")
print(f"    {assembled.detail}")
package = assembled.artifacts["package"]
for line in package["summary_lines"]:
    print(f"      {line}")
print(f"    review_required = {assembled.artifacts['review_required']}")

# ───────────────────────────────────────────────────────── 5. COMI
step("COMI — the broker must not see what the broker must not see")
from dispatch import comi_routing
internal = {
    "load_id": LOAD_ID, "pickup_location": load["pickup_location"],
    "delivery_location": load["delivery_location"],
    "revenue": 2850.00, "profit": 910.00, "margin_pct": 31.9,
    "total_expenses": 1940.00,
    "internal_note": "Broker was slow to pay on the last two.",
}
broker_view = comi_routing.sanitize_payload_for_role(internal, "broker")
print("  internal keys:", ", ".join(sorted(internal)))
print("  broker sees:  ", ", ".join(sorted(broker_view)))
withheld = sorted(set(internal) - set(broker_view))
print(f"  withheld:      {', '.join(withheld) if withheld else 'NOTHING — defect'}")

# ───────────────────────────────── 6. template rendered with real data
step("Render the Library template with the load's own facts")
template = library.current("TPL-BROKER-CLOSEOUT")
rate = store.get_rate_confirmation(LOAD_ID)
rendered = template.body_or_uri.format(
    load_id=LOAD_ID, pickup=load["pickup_location"], delivery=load["delivery_location"],
    delivered_on="2026-09-12", pod_id=pod["pod_id"],
    evidence_count=len(store.list_evidence(LOAD_ID)),
    rate=f"{rate['revenue']:.2f}",
)
print(f"  from {template.object_code} v{template.version} ({template.status.value})\n")
for line in rendered.splitlines():
    print(f"    | {line}")

# ──────────────────────────────────────────────── 7. Email Helper
step(f"Email Helper — draft and submit to {OPS}")
from portal.models import email_helper
draft = email_helper.create_draft(
    load_id=LOAD_ID, load=load, broker_contact={"email": OPS, "name": "Level 1 Operations"},
    pod_id=pod["pod_id"], invoice_number="INV-PHASE-A-001")
email_helper.update_draft(LOAD_ID, broker_email=OPS, broker_body=rendered,
                          broker_subject=f"Closeout — {LOAD_ID} — Jacksonville FL to Savannah GA",
                          customer_email="")
print(f"  draft {draft['id']}  status={draft['status']}")

print("\n  refusal check — no system identity may submit:")
try:
    email_helper.submit_package(LOAD_ID, submitted_by="PUBLISHER")
    print("    NOT REFUSED  <-- defect")
except Exception as exc:
    print(f"    refused: {exc}")

submitted = email_helper.submit_package(LOAD_ID, submitted_by="Mike Zachary")
print(f"\n  submitted by Mike Zachary -> status={submitted['status']}")
for result in submitted.get("send_results", []):
    print(f"    {json.dumps(result)}")

# ───────────────────────────────────────── 8. read back what was written
step("Open what the transport actually wrote")
outbox = list((tmp / "Archive").rglob("*.eml"))
print(f"  .eml files written: {len(outbox)}")
for path in outbox:
    print(f"\n  {path.relative_to(tmp)}")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:18]:
        print(f"    | {line}")

from dispatch.transport import selection
print(f"\n  transport: {json.dumps(selection.outbound_status())}")
db.set_db_path(None)
print(f"\n{'='*72}\n  Workspace: {tmp}\n{'='*72}")
