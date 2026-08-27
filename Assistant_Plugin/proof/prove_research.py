"""LIVE WEB-GROUNDED RESEARCH PROOF.

Research is only live when actual source attributions come back. Web grounding
switched on with nothing returned is general reasoning wearing research's
clothes, and this proof fails it rather than reporting it as research.

Sample mode is NOT removed - it stays available for deterministic testing - but
it must always be labelled SAMPLE DATA and can never be reported as live.

Run:   py proof\\prove_research.py
Writes evidence to proof\\RESEARCH_PROOF.md.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74

QUESTION = ("Research what current public information could affect commercial "
            "travel on I-95 in Florida")

# Every section the mission requires. A missing section reads as "nothing to
# report"; an empty one reads as "asked, and nothing came back". The report
# must carry all of them so those two never blur.
REQUIRED_SECTIONS = (
    "QUESTION", "RESEARCH SCOPE", "RETRIEVAL TIME", "SOURCES CONSULTED",
    "ATTRIBUTIONS", "CONFIRMED FINDINGS", "UNCONFIRMED INFORMATION",
    "SOURCE CONFLICTS", "OPERATIONAL CONSEQUENCES", "UNCERTAINTY",
    "RECOMMENDATION", "SHORT SPOKEN ANSWER",
)


def main() -> int:
    from app.config import Config
    from app.service import AssistantService

    print(DIVIDER)
    print("JOE - LIVE WEB-GROUNDED RESEARCH PROOF")
    print(DIVIDER)
    print()

    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json")
    )
    try:
        probe = service.research.probe()
        print("  research provider   " + str(probe.get("provider")))
        print("  mode                " + str(probe.get("mode")))
        print("  live connection     " + str(probe.get("live_connection")))
        print()
        if not probe.get("live_connection"):
            print("BLOCKED: research is not live. " + str(probe.get("blocker") or ""))
            write_report(None, blocked=str(probe.get("blocker") or "not live"))
            return 2

        print("  question            " + QUESTION)
        print("  asking...")
        response = service.ask(QUESTION).response
        classes = sorted({p.source_class for p in response.provenance if p.source_class})
        written = response.written or ""

        spoke = False
        if response.spoken_summary:
            try:
                attempt = service.voice.speak(response.spoken_summary[:400])
                spoke = bool(getattr(attempt, "spoken", False))
            except Exception:  # noqa: BLE001
                spoke = False

        checks = {
            "answered": bool(response.ok),
            "web grounding enabled": "COPILOT_WEB_GROUNDED" in classes,
            "actual attributions returned": len(response.citations) > 0,
            "attributions carry a source": any(
                "http" in str(c).lower() for c in response.citations),
            "labelled COPILOT_WEB_GROUNDED": classes == ["COPILOT_WEB_GROUNDED"],
            "retrieval time included": "RETRIEVAL TIME" in written,
            "states it does not replace DOT or 511": (
                "does not replace official DOT or 511" in written),
            "short spoken answer present": bool(response.spoken_summary),
            "short answer was spoken aloud": spoke,
            "full report retained": len(written) > 400,
            "reasoning mode declared": (
                getattr(response, "reasoning_mode", "") == "WEB_GROUNDED_RESEARCH"),
        }
        for section in REQUIRED_SECTIONS:
            checks["section: " + section] = section in written

        print()
        print("  classes             " + (", ".join(classes) or "(none)"))
        print("  attributions        " + str(len(response.citations)))
        for citation in response.citations[:5]:
            print("     - " + str(citation)[:86])
        print()
        for label, value in checks.items():
            print("  %-42s %s" % (label, value))
        print()

        passed = all(checks.values())
        print(DIVIDER)
        print("RESULT: " + ("PASS - research is LIVE and attributed"
                            if passed else "FAIL - research is NOT proven"))
        print(DIVIDER)
        write_report({
            "response": response, "classes": classes, "checks": checks,
            "spoke": spoke,
        }, blocked="")
        print()
        print("Evidence written to  proof\\RESEARCH_PROOF.md")
        return 0 if passed else 1
    finally:
        service.shutdown()


def write_report(data, blocked: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# JOE - Live Web-Grounded Research Proof",
        "",
        "**Run:** " + stamp,
        "**Provider:** Microsoft 365 Copilot - PILOT / PREVIEW (`/beta` endpoint)",
        "",
        "Research is live only when actual attributions come back. Web grounding "
        "switched on with nothing returned is general reasoning, and this proof "
        "fails it rather than reporting it as research.",
        "",
    ]
    if blocked or data is None:
        lines += ["## Result", "", "**BLOCKED.** " + (blocked or "not run"), "",
                  "Research is NOT live and must not be reported as live.", ""]
    else:
        response = data["response"]
        passed = all(data["checks"].values())
        lines += [
            "## Result",
            "",
            "**" + ("PASS - research is LIVE and attributed."
                    if passed else "FAIL - research is NOT proven.") + "**",
            "",
            "| | |",
            "| --- | --- |",
            "| Question | " + QUESTION + " |",
            "| Source classes | " + (", ".join(data["classes"]) or "-") + " |",
            "| Attributions returned | " + str(len(response.citations)) + " |",
            "| Short answer spoken aloud | " + str(data["spoke"]) + " |",
            "",
            "### Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
        for label, value in data["checks"].items():
            lines.append("| " + label + " | "
                         + ("**True**" if value else "**False**") + " |")
        lines += ["", "### Attributions returned", ""]
        lines += ["- " + str(c) for c in response.citations] or ["(none)"]
        lines += ["", "### Full report as JOE rendered it", "", "```",
                  (response.written or "")[:6000], "```", ""]
    (PLUGIN_ROOT / "proof" / "RESEARCH_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
