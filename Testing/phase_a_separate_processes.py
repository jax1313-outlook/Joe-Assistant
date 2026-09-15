"""PHASE A, across separate processes: Library -> Publisher -> COMI -> Email Helper.

The first Phase A had to run as one script because the Library forgot everything when the
process exited (KNOWN_LIMITATIONS.md section 14). This runs every step as its own Python process
against the persistent Library catalog. A step can only succeed if what an earlier process wrote
was remembered by the store that wrote it -- there is no shared memory to lean on.

    python Testing/phase_a_separate_processes.py [--library-src PATH] [--dispatch PATH]

Everything runs in a fresh certification workspace: its own Library catalog, its own Dispatch
database, its own Archive and its own memory root. D:\\Memory and the operator's real data are
never named. No Microsoft call is made and nothing is delivered; the transport writes an .eml.
The approvals in it are by "Phase A Certification Operator", a test identity, not by Mike.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS_FILE = Path(__file__).resolve().parent / "phase_a_steps.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library-src", default=os.environ.get("DISPATCH_LIBRARY_SRC", str(ROOT.parent / "Library" / "src")))
    parser.add_argument("--dispatch", default=str(ROOT.parent / "Dispatch"))
    parser.add_argument("--workspace", default="")
    args = parser.parse_args()

    ws = Path(args.workspace) if args.workspace else Path(tempfile.mkdtemp(prefix="phase-a-separate-"))
    ws.mkdir(parents=True, exist_ok=True)
    # Every inherited DISPATCH_* and PORTAL_* variable is dropped, then only workspace paths are set.
    # Overriding a chosen few is not enough: on the operator's machine DISPATCH_ARCHIVE_PATH pointed
    # the CIN outbox at the real D:\Archive\CIN, and the first run of this script wrote one .eml
    # there (2026-09-13, moved into that run's workspace). Dispatch reads over a hundred such names,
    # SMTP and Microsoft credentials among them; none may leak into a certification run.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("DISPATCH_", "PORTAL_"))}
    env.update({
        "PORTAL_DATA_DIR": str(ws / "portal"),
        "PORTAL_UPLOAD_DIR": str(ws / "portal" / "uploads"),
        "DISPATCH_ARCHIVE_ROOT": str(ws / "Archive"),
        "DISPATCH_ARCHIVE_PATH": str(ws / "Archive" / "CIN"),
        "DISPATCH_MEMORY_ROOT": str(ws / "Memory"),
        "DISPATCH_OPERATIONS_ROOT": str(ws / "Operations"),
        "DISPATCH_BACKUP_DIR": str(ws / "Backups"),
        "DISPATCH_LOG_DIR": str(ws / "Logs"),
        "DISPATCH_LAUNCHER_LOG_DIR": str(ws / "Logs"),
        "DISPATCH_LIBRARY_CATALOG": str(ws / "Library" / "catalog.db"),
        "DISPATCH_LIBRARY_SRC": args.library_src,
        "PYTHONPATH": os.pathsep.join([str(ROOT / "Workers"), str(ROOT / "Assistant_Plugin"), args.dispatch,
                                       args.library_src]),
    })
    for key in ("PORTAL_DATA_DIR", "PORTAL_UPLOAD_DIR", "DISPATCH_ARCHIVE_ROOT", "DISPATCH_ARCHIVE_PATH",
                "DISPATCH_MEMORY_ROOT", "DISPATCH_OPERATIONS_ROOT", "DISPATCH_LOG_DIR"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    leaked = sorted(k for k, v in env.items() if k.upper().startswith(("DISPATCH_", "PORTAL_"))
                    and ":" in v and not v.startswith(str(ws)) and k != "DISPATCH_LIBRARY_SRC")
    assert not leaked, f"certification environment names paths outside the workspace: {leaked}"

    results: dict = {"workspace": str(ws)}
    pids = set()

    def run(title, argv):
        print(f"\n{'=' * 72}\n  {title}\n  $ {' '.join(argv[1:])}\n{'=' * 72}")
        done = subprocess.run(argv, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                              cwd=str(ROOT / "Workers"), timeout=300)
        print(done.stdout.rstrip())
        if done.returncode not in (0, 1) or (done.stderr.strip() and done.returncode):
            print(done.stderr.rstrip())
        return done

    def step(name):
        done = run(f"STEP {name}  (new process)", [sys.executable, str(STEPS_FILE), name, str(ws)])
        assert done.returncode == 0, done.stderr
        payload = json.loads(done.stdout.strip().splitlines()[-1])
        pids.add(payload.get("pid"))
        results[name] = payload
        return payload

    placed = step("place_templates")
    assert [p["state"] for p in placed["placed"]] == ["CURRENT", "CURRENT"]
    assert "system identity" in placed["refusals"]["PUBLISHER as approver"]
    assert placed["refusals"]["no object_type"].startswith("refused")

    listing = run("LIBRARY list, new process", [sys.executable, "-m", "dispatch_library.catalog", "list",
                                               "--collection", "Templates"])
    assert listing.returncode == 0 and "TPL-BROKER-CLOSEOUT" in listing.stdout

    seeded = step("seed_load")

    readiness = run("PUBLISHER check_readiness via the worker bus CLI, new process",
                    [sys.executable, "-m", "worker_bus", "--json", "ask", "PUBLISHER", "check_readiness",
                     f"load_id={seeded['load_id']}", "template_id=TPL-BROKER-CLOSEOUT"])
    ready = json.loads(readiness.stdout)
    results["check_readiness"] = {"status": ready.get("status"), "detail": ready.get("detail"),
                                  "findings": [f.get("code") for f in ready.get("findings", [])]}
    assert ready["status"] == "LIVE" and ready["detail"] == "Ready to assemble.", ready

    assembled = step("assemble")
    assert assembled["without_authorisation"]["status"] == "ABSENT"
    assert assembled["with_authorisation"]["status"] == "LIVE"
    assert assembled["with_authorisation"]["review_required"] is True

    blocked = step("review_due_block")
    assert "TEMPLATE_NOT_USABLE" in blocked["findings"] and blocked["external_after_renewal"] is True

    composed = step("compose")
    assert composed["template"].startswith("TPL-BROKER-CLOSEOUT v1.0 CURRENT")
    assert composed["system_submit"].startswith("refused")
    assert "profit" in composed["withheld_from_broker"]

    for result in composed["send_results"]:
        assert str(ws) in result.get("result", ""), f"the transport wrote outside the workspace: {result}"
    outbox = step("read_outbox")
    assert outbox["eml_files"] and outbox["eml_files"][0]["to"] == "ops@l1truck.com"
    assert outbox["eml_files"][0]["body_has_template"]
    # Nothing delivered: the transport says so where it can report, and every send result says so.
    assert outbox["transport"].get("delivering") is not True
    assert all(str(r.get("result", "")).startswith("not sent") for r in composed["send_results"]), composed["send_results"]
    assert all(str(ws) in box for box in outbox["outboxes"] if Path(box).exists()), outbox["outboxes"]

    record = step("library_record")
    assert ("PUBLISHER", "RETURNED") in [tuple(r) for r in record["retrievals_by_role"]]

    results["distinct_step_processes"] = len(pids)
    assert len(pids) == 7, "every step must have been its own process"
    (ws / "phase_a_separate_processes_result.json").write_text(json.dumps(results, indent=2, default=str),
                                                                 encoding="utf-8")
    print(f"\n{'=' * 72}\n  PHASE A PASSED ACROSS {len(pids)} STEP PROCESSES (+2 CLI processes)\n"
          f"  Nothing was delivered. Transport: {json.dumps(outbox['transport'])}\n  Workspace: {ws}\n{'=' * 72}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
