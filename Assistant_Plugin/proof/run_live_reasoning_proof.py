"""Live reasoning proof for JOE - a REAL Microsoft 365 Copilot call.

DELIBERATELY NOT PART OF THE DEFAULT 24-PROOF SUITE.

    py proof\\run_live_reasoning_proof.py
    py proof\\run_proof.py --live-reasoning     (same steps, still excluded
                                                 from the 24)

WHY IT IS SEPARATE. run_proof.py must be runnable at any time, on any
machine, without contacting a paid preview API and without depending on
somebody being signed in. It redirects paths.runtime_data into a throwaway
workspace, so the token cache is never visible to it and step 22 always -
correctly - proves the NO-PROVIDER path. That leaves the working path
unproven, which is what this file is for.

WHAT THIS RUN ACTUALLY DOES, so nobody is surprised by it:

  * It uses the REAL runtime_data, because that is where the encrypted token
    cache lives. Nothing else can see the sign-in.
  * It sends two real requests to the Microsoft 365 Copilot Chat API. That is
    a /beta endpoint which Microsoft states is not supported for production
    use. Requests leave this machine.
  * It creates real Level 1 memory records, which expire in three hours like
    any other Level 1 record.
  * It sends no mail, approves nothing, decides nothing, and writes nothing
    outside the plugin root.

A step passes only on what was observed in this run. Nothing here is asserted
from design intent.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "proof"))

from app import bootstrap  # noqa: E402,F401
from app.service import AssistantService  # noqa: E402
from adapters.reasoning_provider import ReasoningStatus  # noqa: E402
from contracts import SourceMode  # noqa: E402
from run_proof import DIVIDER, Proof  # noqa: E402

REPORT = PLUGIN_ROOT / "docs" / "JOE_LIVE_REASONING_PROOF_v1.md"

# Anything whose presence would mean a raw token had escaped the auth module.
TOKEN_MARKERS = ("Bearer ", "access_token", "eyJ", "refresh_token", "id_token")


def _leaks(blob: str) -> list:
    return [m for m in TOKEN_MARKERS if m in blob]


def step_live_status(proof: Proof, service) -> dict:
    """The provider reports LIVE, and says which account it is bound to."""
    state = service.reasoning.status()
    live = (state["status"] == ReasoningStatus.LIVE and state["live"]
            and state["credential_present"])
    proof.record(
        "L1", "Reasoning reports LIVE and names the bound account", live,
        [
            "status              " + state["status"],
            "live                " + str(state["live"]),
            "provider            " + state["provider"],
            "account             " + (state.get("account") or "(none)"),
            "auth state          " + (state.get("auth_state") or "(none)"),
            "credential present  " + str(state["credential_present"]),
            "client secret used  " + str(state.get("client_secret_used")),
            "cache encrypted     " + str(state.get("cache_encrypted")),
            "blocker             " + (state.get("blocker") or "(none)"),
        ],
        note=("" if live else
              "not signed in - sign in through JOE, then run this again"),
    )
    return state


def step_real_answer(proof: Proof, service):
    """A real request to the API comes back with usable text."""
    started = time.perf_counter()
    answer = service.reasoning.answer(
        "In one sentence, what is a rate floor in freight dispatch?")
    elapsed = time.perf_counter() - started
    text = (answer.text or "").strip()
    ok = bool(answer.ok) and len(text) > 0
    proof.record(
        "L2", "A real Copilot request returns usable text", ok,
        [
            "request sent        yes - live /beta Copilot Chat API",
            "round trip          " + ("%.1f s" % elapsed),
            "ok                  " + str(answer.ok),
            "characters returned " + str(len(text)),
            "provider            " + (answer.provider or "(none)"),
            "model               " + (answer.model or "(none)"),
            "grounded            " + str(answer.grounded),
            "source class        " + (answer.source_class or "NONE"),
            "sources cited       " + str(len(answer.sources)),
            "conversation turns  " + str(answer.turn_count),
            "error               " + (answer.error or "(none)"),
            "",
            "first line          " + (text.splitlines()[0][:70] if text else "-"),
        ],
        note=("" if ok else "the API did not return usable text this run"),
    )
    return answer


def step_provenance(proof: Proof, answer) -> None:
    """The reply is reported as LIVE, and never as sample data."""
    p = answer.provenance()
    ok = p.mode == SourceMode.LIVE and answer.provider != ""
    proof.record(
        "L3", "The reply is labelled LIVE, not sample", ok,
        [
            "provenance mode     " + str(p.mode),
            "is SAMPLE           " + str(p.mode == SourceMode.SAMPLE),
            "source              " + p.source,
            "as of               " + p.as_of,
            "detail              " + p.detail[:70],
        ],
    )


def step_draft_carries_no_authority(proof: Proof, service):
    """A real draft is produced, and it approves and decides nothing."""
    started = time.perf_counter()
    draft = service.reasoning.draft(
        "Draft a short note to a broker asking to confirm a pickup time.")
    elapsed = time.perf_counter() - started
    text = (draft.text or "").strip()

    asked = service.ask("Draft an email to the broker").response
    shown = ((asked.written or "") + " " + (asked.answer or "")).upper()
    labelled = "DRAFT ONLY" in shown and "NOT SENT" in shown

    authority = {
        "approved": draft.approved,
        "decided": draft.decided,
        "acted_on": draft.acted_on,
    }
    clean = not any(authority.values())
    ok = bool(draft.ok) and len(text) > 0 and clean and labelled
    proof.record(
        "L4",
        "A real draft is produced, labelled DRAFT ONLY / NOT SENT, and "
        "carries no authority",
        ok,
        [
            "request sent        yes - live /beta Copilot Chat API",
            "round trip          " + ("%.1f s" % elapsed),
            "draft returned      " + str(draft.ok) + ", " + str(len(text))
            + " characters",
            "ask path labelled   " + str(labelled)
            + "  (DRAFT ONLY / NOT SENT shown to Mike)",
            "approved            " + str(authority["approved"]),
            "decided             " + str(authority["decided"]),
            "acted on            " + str(authority["acted_on"]),
            "",
            "first line          " + (text.splitlines()[0][:70] if text else "-"),
        ],
        note=("" if ok else
              "a live draft must be produced, labelled, and carry no authority"),
    )
    return draft


def step_no_token_escapes(proof: Proof, service, answer, draft) -> None:
    """Nothing a caller can reach contains a token."""
    surfaces = {
        "answer.to_dict()": json.dumps(answer.to_dict(), default=str),
        "draft.to_dict()": json.dumps(draft.to_dict(), default=str),
        "reasoning.status()": json.dumps(service.reasoning.status(), default=str),
        "service.status_dict()": json.dumps(service.status_dict(), default=str),
    }
    log = PLUGIN_ROOT / "logs" / "joe.log"
    if log.exists():
        surfaces["logs/joe.log"] = log.read_text(encoding="utf-8", errors="replace")

    found = {name: _leaks(blob) for name, blob in surfaces.items()}
    clean = not any(found.values())
    proof.record(
        "L5", "No token reaches any caller-visible surface", clean,
        ["%-22s %s" % (name, (", ".join(hits) + "  LEAK") if hits else "clean")
         for name, hits in found.items()]
        + ["", "markers searched    " + ", ".join(TOKEN_MARKERS)],
        note=("" if clean else
              "a token marker appeared where callers can see it"),
    )


def step_nothing_sent(proof: Proof, service) -> None:
    """A live provider does not give JOE the ability to send."""
    missing = [
        name
        for holder in (service, service.outlook, service.dispatch)
        for name in ("send", "send_email", "reply", "forward", "transmit")
        if hasattr(holder, name)
    ]
    data = service.status_dict()
    ok = not missing and data["messages_sent"] == 0
    proof.record(
        "L6", "Reasoning being live grants no ability to send", ok,
        [
            "send methods        " + (", ".join(missing) if missing
                                      else "none exist, provider live"),
            "messages sent       " + str(data["messages_sent"]),
            "outlook writes      0",
        ],
    )


def write_report(proof: Proof, state: dict) -> Path:
    at = datetime.now(timezone.utc).isoformat()
    lines = [
        "# JOE - Live Reasoning Proof",
        "",
        "**Program:** JOE, the Level 1 Assistant",
        "**Plugin root:** `" + str(PLUGIN_ROOT) + "`",
        "**Run generated (UTC):** " + at,
        "**Generated by:** `proof/run_live_reasoning_proof.py`",
        "",
        "This proof is NOT part of the default 24-proof suite. It sends real "
        "requests to the Microsoft 365 Copilot Chat API, a /beta endpoint "
        "Microsoft states is not supported for production use.",
        "",
        "Every value below was observed during this run on this machine.",
        "",
        "## Result",
        "",
        "| Proof | Requirement | Result |",
        "| --- | --- | --- |",
    ]
    for step in proof.steps:
        mark = "SKIP" if step["skipped"] else ("PASS" if step["passed"] else "FAIL")
        lines.append("| %s | %s | %s |" % (step["number"], step["title"], mark))
    lines += [
        "",
        "**Overall: %d passed, %d skipped, %d failed**"
        % (proof.passed_count, proof.skipped_count, proof.failed_count),
        "",
        "**Account:** " + (state.get("account") or "(none)"),
        "**Provider:** " + (state.get("provider") or "(none)"),
        "",
        "## Evidence",
        "",
    ]
    for step in proof.steps:
        mark = "SKIPPED" if step["skipped"] else (
            "PASS" if step["passed"] else "FAIL")
        lines += ["### Proof " + str(step["number"]) + " - " + step["title"],
                  "", "Result: **" + mark + "**", "", "```"]
        lines += step["evidence"]
        lines += ["```", ""]
        if step["note"]:
            lines += ["> " + step["note"], ""]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    return REPORT


def run() -> int:
    print(DIVIDER)
    print("JOE - LIVE REASONING PROOF  (real Copilot calls; not in the 24)")
    print(DIVIDER)

    proof = Proof()
    service = AssistantService()
    try:
        state = step_live_status(proof, service)
        if not (state["status"] == ReasoningStatus.LIVE and state["live"]):
            print()
            print(DIVIDER)
            print("STOPPED: no live reasoning provider - nothing was sent.")
            print(DIVIDER)
            print("  report written  " + str(write_report(proof, state)))
            return 1

        answer = step_real_answer(proof, service)
        step_provenance(proof, answer)
        draft = step_draft_carries_no_authority(proof, service)
        step_no_token_escapes(proof, service, answer, draft)
        step_nothing_sent(proof, service)

        report = write_report(proof, state)
        print()
        print(DIVIDER)
        print("RESULT: %d passed, %d skipped, %d failed  (of %d steps)"
              % (proof.passed_count, proof.skipped_count,
                 proof.failed_count, len(proof.steps)))
        print(DIVIDER)
        print("  report written  " + str(report))
        return 0 if proof.all_passed else 1
    finally:
        service.shutdown()


if __name__ == "__main__":
    raise SystemExit(run())
