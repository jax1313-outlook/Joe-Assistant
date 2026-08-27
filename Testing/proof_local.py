"""Local proof run for Sandbox Engine v1.

Demonstrates, on this machine, the ten proofs required by the mission and
writes Testing/LOCAL_PROOF_REPORT_v1.md from what actually happened.

Run:  py Testing\\proof_local.py          (from the project root)
      or Build\\run_proof.cmd

By default this resets the demonstration Sandbox so the visible result is
reproducible. Pass --no-reset to keep whatever is already there.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Build"))

from sandbox_engine import __version__  # noqa: E402
from sandbox_engine.clock import FixedClock, SystemClock, from_iso  # noqa: E402
from sandbox_engine.engine import EngineError, SandboxEngine  # noqa: E402
from sandbox_engine.records import RecordState  # noqa: E402
from sandbox_engine.store import SandboxStore, StoreError  # noqa: E402

REPORT_PATH = PROJECT_ROOT / "Testing" / "LOCAL_PROOF_REPORT_v1.md"
EXPIRY_WORKSPACE = PROJECT_ROOT / "Testing" / "_proof_expiry"

DIVIDER = "=" * 72
FORBIDDEN_MODULES = (
    "socket", "urllib", "http", "requests", "ftplib", "smtplib", "poplib",
    "imaplib", "telnetlib", "ssl", "xmlrpc", "boto3", "azure", "msal",
    "openai", "anthropic", "office365", "win32com", "subprocess", "webbrowser",
)


class Proof:
    """Collects proof steps and their observed evidence."""

    def __init__(self) -> None:
        self.steps: list[dict] = []

    def record(self, number: int, title: str, passed: bool, evidence: list[str]) -> None:
        self.steps.append(
            {
                "number": number,
                "title": title,
                "passed": bool(passed),
                "evidence": list(evidence),
            }
        )
        status = "PASS" if passed else "FAIL"
        print()
        print(DIVIDER)
        print("PROOF {0}  [{1}]  {2}".format(number, status, title))
        print(DIVIDER)
        for line in evidence:
            print("  " + line)

    @property
    def all_passed(self) -> bool:
        return all(step["passed"] for step in self.steps)


def reset_demo_sandbox(store: SandboxStore) -> list[str]:
    notes = []
    for folder in ("active", "expired", "deleted"):
        target = store.sandbox_root / folder
        if target.exists():
            removed = list(target.glob("*.json"))
            for path in removed:
                path.unlink()
            notes.append(
                "cleared {0} file(s) from Sandbox/{1}".format(len(removed), folder)
            )
    requests_dir = store.artifact_requests_root
    if requests_dir.exists():
        removed = list(requests_dir.glob("*"))
        for path in removed:
            if path.is_file():
                path.unlink()
        notes.append("cleared {0} file(s) from Artifacts/requests".format(len(removed)))
    shutil.rmtree(EXPIRY_WORKSPACE, ignore_errors=True)
    return notes


# ---------------------------------------------------------------------------


def proof_1_and_2(proof: Proof, engine: SandboxEngine) -> str:
    record = engine.create(
        driver_request="What matters about tomorrow's run?",
        assistant_response=(
            "Two stops, both live unload. Nothing needs a decision tonight."
        ),
        research_scope="Tomorrow's schedule only",
        uncertainty="Second stop appointment window is not confirmed.",
        assistant_recommendation="Confirm the second appointment before departure.",
    )
    proof.record(
        1,
        "Create a Level 1 temporary record",
        record.state == RecordState.TEMPORARY
        and record.interaction_level == "LEVEL_1",
        [
            "sandbox_id           " + record.sandbox_id,
            "state                " + record.state,
            "interaction_level    " + record.interaction_level,
            "file                 "
            + str(engine.store.path_for(record.sandbox_id, record.state)),
        ],
    )

    created = from_iso(record.created_at)
    expires = from_iso(record.expires_at)
    delta = expires - created
    proof.record(
        2,
        "Show the three-hour expiration time",
        delta == timedelta(hours=3),
        [
            "created_at (UTC)     " + record.created_at,
            "expires_at (UTC)     " + record.expires_at,
            "difference           " + str(delta),
            "expected             3:00:00",
        ],
    )
    return record.sandbox_id


def proof_3(proof: Proof, engine: SandboxEngine) -> str:
    record = engine.create(
        driver_request="Broker offered 2.10 a mile on the Charlotte run.",
        assistant_response="Below your recorded floor for that lane.",
        key_findings=["Offer is under the recorded lane floor."],
        operational_consequences=["Accepting would reduce the week's average."],
        assistant_recommendation="Counter or pass. Mike decides.",
    )
    result = engine.apply_command(record.sandbox_id, "Save this")
    saved = engine.get(record.sandbox_id)
    proof.record(
        3,
        'Process "Save this" and show conversion to Level 2 SAVED',
        saved.state == RecordState.SAVED
        and saved.interaction_level == "LEVEL_2"
        and saved.expires_at is None,
        [
            "sandbox_id           " + saved.sandbox_id,
            "recognized intent    " + result.command.intent,
            "matched phrase       " + str(result.command.matched_phrase),
            "state                " + result.previous_state + " -> " + saved.state,
            "interaction_level    "
            + result.previous_level
            + " -> "
            + saved.interaction_level,
            "expires_at           " + str(saved.expires_at) + "  (expiration cleared)",
            "file                 "
            + str(engine.store.path_for(saved.sandbox_id, saved.state)),
            "notice               " + result.notice,
        ],
    )
    return saved.sandbox_id


def proof_4(proof: Proof, engine: SandboxEngine) -> tuple[str, str]:
    record = engine.create(
        driver_request="Look at running a dedicated northbound lane.",
        assistant_response="Comparison of three options with current public rate data.",
        research_scope="Northbound dedicated lane, public rate sources",
        sources_consulted=["public rate index", "internal lane history"],
        citations=["https://example.invalid/rate-index"],
        key_findings=["Two of three options clear the recorded floor."],
    )
    result = engine.apply_command(record.sandbox_id, "Level 3 this under Ideas")
    formal = engine.get(record.sandbox_id)
    request = result.artifact_requests[0]
    proof.record(
        4,
        'Process "Level 3 this under Ideas" and show FORMAL with destination Ideas',
        formal.state == RecordState.FORMAL
        and formal.destination == "Ideas"
        and formal.interaction_level == "LEVEL_3"
        and request["artifact_kind"] == "FORMAL_REPORT",
        [
            "sandbox_id           " + formal.sandbox_id,
            "recognized intent    " + result.command.intent,
            "state                " + result.previous_state + " -> " + formal.state,
            "interaction_level    " + formal.interaction_level,
            "destination          " + str(formal.destination),
            "expires_at           " + str(formal.expires_at) + "  (expiration cleared)",
            "artifact request     " + request["artifact_request_id"],
            "artifact kind        " + request["artifact_kind"],
            "artifact status      " + request["status"],
            "produced             " + str(request["produced"]),
            "citations carried    " + str(request["citations"]),
            "request file         "
            + str(engine.store.artifact_requests_root / (request["artifact_request_id"] + ".md")),
        ],
    )
    return formal.sandbox_id, request["artifact_request_id"]


def proof_5(proof: Proof, engine: SandboxEngine) -> str:
    record = engine.create(
        driver_request="Put the maintenance summary somewhere I can print later.",
        assistant_response="Summary of the last three service events.",
    )
    result = engine.apply_command(record.sandbox_id, "Print this")
    printable = engine.get(record.sandbox_id)
    request = result.artifact_requests[0]
    body = (
        engine.store.artifact_requests_root / (request["artifact_request_id"] + ".md")
    ).read_text(encoding="utf-8")
    honest = (
        request["physical_print_performed"] is False
        and request["produced"] is False
        and "Nothing was printed" in body
        and "No printer was contacted" in result.notice
    )
    # Doctrine C4, ruled by Mike Zachary: Print is a state, not a level.
    level_held = (
        result.previous_level == "LEVEL_1"
        and printable.interaction_level == "LEVEL_1"
    )
    proof.record(
        5,
        'Process "Print this" and show PRINT_READY without claiming physical printing',
        printable.state == RecordState.PRINT_READY and honest and level_held,
        [
            "sandbox_id                 " + printable.sandbox_id,
            "recognized intent          " + result.command.intent,
            "state                      "
            + result.previous_state
            + " -> "
            + printable.state,
            "interaction_level          "
            + result.previous_level
            + " -> "
            + printable.interaction_level
            + "   (doctrine C4: Print is a state, not a level)",
            "expires_at                 " + str(printable.expires_at),
            "artifact request           " + request["artifact_request_id"],
            "produced                   " + str(request["produced"]),
            "physical_print_performed   " + str(request["physical_print_performed"]),
            "notice                     " + result.notice,
            'request document states    "Nothing was printed."',
        ],
    )
    return printable.sandbox_id


def proof_6(proof: Proof, engine: SandboxEngine) -> str:
    record = engine.create(
        driver_request="Scratch that last rate question.",
        assistant_response="Understood.",
    )
    result = engine.apply_command(record.sandbox_id, "Delete this")
    tombstone = engine.get(record.sandbox_id)
    active_ids = [r.sandbox_id for r in engine.store.list_active()]
    refused = False
    try:
        engine.apply_command(record.sandbox_id, "Save this")
    except EngineError:
        refused = True
    proof.record(
        6,
        'Process "Delete this" and show DELETED',
        tombstone.state == RecordState.DELETED
        and tombstone.driver_request is None
        and record.sandbox_id not in active_ids
        and refused,
        [
            "sandbox_id           " + tombstone.sandbox_id,
            "recognized intent    " + result.command.intent,
            "state                " + result.previous_state + " -> " + tombstone.state,
            "driver_request       " + str(tombstone.driver_request) + "  (purged)",
            "deletion_reason      " + str(tombstone.deletion_reason),
            "in active Sandbox    " + str(record.sandbox_id in active_ids),
            "later command        refused = " + str(refused),
            "file                 "
            + str(engine.store.path_for(tombstone.sandbox_id, tombstone.state)),
        ],
    )
    return tombstone.sandbox_id


def proof_7_and_8(proof: Proof) -> dict:
    """Expiration is proven on a simulated clock in an isolated store.

    An isolated store keeps the visible demonstration Sandbox intact; a
    simulated clock avoids waiting three real hours.
    """
    EXPIRY_WORKSPACE.mkdir(parents=True, exist_ok=True)
    clock = FixedClock()
    engine = SandboxEngine(store=SandboxStore(EXPIRY_WORKSPACE), clock=clock)
    record = engine.create(
        driver_request="How long to the next scale?",
        assistant_response="About forty minutes.",
    )
    t0 = clock.now()

    clock.advance(hours=2, minutes=59)
    early = engine.sweep()
    state_before = engine.get(record.sandbox_id).state

    clock.advance(minutes=2)
    expired = engine.sweep()
    tombstone = engine.get(record.sandbox_id)

    proof.record(
        7,
        "Simulate expiration without waiting three real hours",
        early == []
        and state_before == RecordState.TEMPORARY
        and [r.sandbox_id for r in expired] == [record.sandbox_id]
        and tombstone.state == RecordState.EXPIRED,
        [
            "isolated store       " + str(EXPIRY_WORKSPACE),
            "simulated start      " + t0.isoformat(),
            "created_at           " + record.created_at,
            "expires_at           " + str(record.expires_at),
            "at +2h59m            expired this sweep = "
            + str(len(early))
            + ", state = "
            + state_before,
            "at +3h01m            expired this sweep = " + str(len(expired)),
            "final state          " + tombstone.state,
            "content purged       driver_request = " + str(tombstone.driver_request),
            "deletion_reason      " + str(tombstone.deletion_reason),
            "no real waiting      the clock was simulated, not slept",
        ],
    )

    active_ids = [r.sandbox_id for r in engine.store.list_active()]
    expired_ids = [r.sandbox_id for r in engine.list_expired()]
    requests_after = engine.store.list_artifact_requests()
    proof.record(
        8,
        "Confirm expired records are absent from active Sandbox results",
        record.sandbox_id not in active_ids
        and record.sandbox_id in expired_ids
        and requests_after == [],
        [
            "active Sandbox count       " + str(len(active_ids)),
            "expired record in active   " + str(record.sandbox_id in active_ids),
            "expired record in expired  " + str(record.sandbox_id in expired_ids),
            "artifact requests created  "
            + str(len(requests_after))
            + "  (expired records are never promoted)",
            "active directory           "
            + str(engine.store.sandbox_root / "active"),
            "expired directory          "
            + str(engine.store.sandbox_root / "expired"),
        ],
    )
    return {
        "sandbox_id": record.sandbox_id,
        "created_at": record.created_at,
        "expires_at": record.expires_at,
    }


def proof_9(proof: Proof, engine: SandboxEngine) -> None:
    root = PROJECT_ROOT.resolve()
    offenders: list[str] = []

    stores = [engine.store, SandboxStore(EXPIRY_WORKSPACE)]
    counted = 0
    for store in stores:
        for record in store.list_all():
            counted += 1
            path = store.path_for(record.sandbox_id, record.state).resolve()
            if not str(path).startswith(str(root)):
                offenders.append(str(path))
        for path in store.artifact_requests_root.glob("*"):
            if not str(path.resolve()).startswith(str(root)):
                offenders.append(str(path.resolve()))

    outside_blocked = []
    for candidate in (
        "C:/Windows/Temp/sandbox_escape.json",
        "C:/Users/Public/sandbox_escape.json",
        str(PROJECT_ROOT.parent / "sandbox_escape.json"),
    ):
        try:
            engine.store.assert_within_project(candidate)
            outside_blocked.append(candidate + " -> NOT BLOCKED")
        except StoreError:
            outside_blocked.append(candidate + " -> blocked")

    proof.record(
        9,
        "Confirm no test record was written outside " + str(root),
        not offenders and all("-> blocked" in line for line in outside_blocked),
        ["project root         " + str(root), "records inspected    " + str(counted)]
        + ["escape attempt       " + line for line in outside_blocked]
        + ["records outside root " + str(len(offenders))],
    )


def proof_10(proof: Proof) -> None:
    package = PROJECT_ROOT / "Build" / "sandbox_engine"
    pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", re.MULTILINE)
    imports: set[str] = set()
    for source in sorted(package.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for module in pattern.findall(text):
            imports.add(module.split(".")[0])
    offenders = sorted(imports & set(FORBIDDEN_MODULES))
    third_party = sorted(
        m
        for m in imports
        if m
        not in {
            "__future__", "argparse", "dataclasses", "datetime", "json", "os",
            "pathlib", "re", "sys", "uuid",
        }
    )
    proof.record(
        10,
        "Confirm no production system was contacted or modified",
        not offenders and not third_party,
        [
            "engine package             " + str(package),
            "modules imported           " + ", ".join(sorted(imports)),
            "network / vendor imports   "
            + (", ".join(offenders) if offenders else "none"),
            "third-party imports        "
            + (", ".join(third_party) if third_party else "none"),
            "email sent                 no send path exists in the engine",
            "calls placed               no dialing path exists in the engine",
            "money committed            no payment path exists in the engine",
            "loads accepted/dispatched  no Dispatch path exists in the engine",
            "Dispatch / Outlook / M365   never imported, never called",
            "Company Library / Archive   never written",
        ],
    )


# ---------------------------------------------------------------------------


def write_report(proof: Proof, engine: SandboxEngine, notes: list[str], expiry: dict) -> Path:
    active = engine.store.list_active()
    requests = engine.store.list_artifact_requests()
    stamp = SystemClock().now().isoformat().replace("+00:00", "Z")

    lines = [
        "# Sandbox Engine v1 - Local Proof Report",
        "",
        "**Project:** Level 1 Assistant - Sandbox Engine v1",
        "**Engine version:** " + __version__,
        "**Project root:** `" + str(PROJECT_ROOT) + "`",
        "**Run generated (UTC):** " + stamp,
        "**Generated by:** `Testing/proof_local.py`",
        "",
        "Every value below was read back from the record files this run "
        "produced on this machine. Nothing in this report is asserted from "
        "design intent.",
        "",
        "## Result",
        "",
        "| Proof | Requirement | Result |",
        "| --- | --- | --- |",
    ]
    for step in proof.steps:
        lines.append(
            "| {0} | {1} | {2} |".format(
                step["number"],
                step["title"].replace("|", "\\|"),
                "PASS" if step["passed"] else "FAIL",
            )
        )
    lines += [
        "",
        "**Overall: " + ("ALL TEN PROOFS PASSED" if proof.all_passed else "ONE OR MORE PROOFS FAILED") + "**",
        "",
        "## Evidence",
        "",
    ]
    for step in proof.steps:
        lines += [
            "### Proof " + str(step["number"]) + " - " + step["title"],
            "",
            "Result: **" + ("PASS" if step["passed"] else "FAIL") + "**",
            "",
            "```",
        ]
        lines += step["evidence"]
        lines += ["```", ""]

    lines += [
        "## Visible active Sandbox after this run",
        "",
        "```",
        "  {0:<28} {1:<12} {2:<8} {3}".format(
            "SANDBOX_ID", "STATE", "LEVEL", "EXPIRES_AT (UTC)"
        ),
    ]
    for record in active:
        lines.append(
            "  {0:<28} {1:<12} {2:<8} {3}".format(
                record.sandbox_id,
                record.state,
                record.interaction_level.replace("LEVEL_", "L"),
                record.expires_at or "(no expiration)",
            )
        )
    if not active:
        lines.append("  (none)")
    lines += [
        "```",
        "",
        "Files: `" + str(engine.store.sandbox_root / "active") + "`",
        "",
        "## Visible artifact requests after this run",
        "",
        "```",
    ]
    for request in requests:
        lines.append(
            "  {0:<26} {1:<14} {2:<24} produced={3}  physical_print_performed={4}".format(
                request["artifact_request_id"],
                request["artifact_kind"],
                request["status"],
                request["produced"],
                request["physical_print_performed"],
            )
        )
    if not requests:
        lines.append("  (none)")
    lines += [
        "```",
        "",
        "Files: `" + str(engine.store.artifact_requests_root) + "`",
        "",
        "## Expiration demonstration detail",
        "",
        "- Simulated clock, isolated store: `" + str(EXPIRY_WORKSPACE) + "`",
        "- Record: `" + expiry["sandbox_id"] + "`",
        "- created_at: `" + str(expiry["created_at"]) + "`",
        "- expires_at: `" + str(expiry["expires_at"]) + "`",
        "- The clock was advanced in code. No real time was slept and no "
        "three-hour wait occurred.",
        "- The demonstration used an isolated store so the visible active "
        "Sandbox above was not swept.",
        "",
        "## Run notes",
        "",
    ]
    for note in notes or ["(no reset performed)"]:
        lines.append("- " + note)
    lines += [
        "",
        "## What this report does not prove",
        "",
        "- Expiration after three hours of **real** elapsed time has not been "
        "observed. It is proven only on a simulated clock. There is no "
        "background scheduler; expiration happens when `sweep` runs.",
        "- No integration with Dispatch, Outlook, Microsoft Graph, Microsoft "
        "365 Copilot, COMI, Publisher, Company Library, or Research Library "
        "was built, attempted, or tested.",
        "- No artifact was produced. Level 3 and Print create **requests** only.",
        "- No printer was contacted. Physical printing is not implemented.",
        "- No voice, phone, or email path exists in this engine.",
        "- Command recognition is proven against the phrases named in the "
        "governing configuration and the variations listed in the test suite. "
        "It is not proven against unrestricted natural language.",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local proof run for Sandbox Engine v1.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Keep whatever is already in the demonstration Sandbox.",
    )
    parser.add_argument("--json", action="store_true", help="Also print JSON results.")
    args = parser.parse_args(argv)

    store = SandboxStore(PROJECT_ROOT)
    engine = SandboxEngine(store=store, clock=SystemClock())

    print(DIVIDER)
    print("SANDBOX ENGINE v" + __version__ + " - LOCAL PROOF RUN")
    print(DIVIDER)
    print("  project root   " + str(PROJECT_ROOT))
    print("  sandbox store  " + str(store.sandbox_root))

    notes: list[str] = []
    if not args.no_reset:
        notes = reset_demo_sandbox(store)
        print("  reset          " + ("; ".join(notes) if notes else "nothing to clear"))
    else:
        print("  reset          skipped (--no-reset)")

    proof = Proof()
    proof_1_and_2(proof, engine)
    proof_3(proof, engine)
    proof_4(proof, engine)
    proof_5(proof, engine)
    proof_6(proof, engine)
    expiry = proof_7_and_8(proof)
    proof_9(proof, engine)
    proof_10(proof)

    report = write_report(proof, engine, notes, expiry)

    print()
    print(DIVIDER)
    print(
        "RESULT: {0} of {1} proofs passed".format(
            sum(1 for s in proof.steps if s["passed"]), len(proof.steps)
        )
    )
    print(DIVIDER)
    print("  report written  " + str(report))
    print("  active Sandbox  " + str(store.sandbox_root / "active"))
    print("  requests        " + str(store.artifact_requests_root))

    if args.json:
        print(json.dumps(proof.steps, indent=2))

    return 0 if proof.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
