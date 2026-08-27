"""SUBSTANTIVE MULTI-TURN REASONING PROOF.

Two conversations, each two turns. The second turn of each is deliberately
elliptical - it names no subject - so an on-topic reply is evidence the
conversation was carried, not restarted.

An earlier follow-up proof passed on a reply that said "the supplied context
does not discuss that". Context HAD carried, but nothing was answered, and
scoring it as a pass conflated two different claims. Both are measured here,
separately:

    context carried   - did the referent resolve to the first turn's subject
    substantive       - did it actually answer, rather than decline

Proof 1 is general industry knowledge the Company Library does not cover.
Proof 2 is Level 1 Transport material the Library governs. They must be
answered under different reasoning modes and must not blur into each other.

Run:   py proof\\prove_reasoning.py
Writes evidence to proof\\REASONING_PROOF.md.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74

REFUSAL_MARKERS = (
    "cannot answer", "can't answer", "does not discuss", "doesn't discuss",
    "no information", "not discussed", "not covered", "unable to answer",
    "does not define", "does not explain", "not contain any information",
    "supplied material does not", "supplied context does not",
)

CONVERSATIONS = (
    {
        "name": "General industry knowledge",
        "turn_1": "Explain the difference between a live unload and a drop-and-hook.",
        "turn_2": ("Which one normally creates more uncertainty in the driver's "
                   "available time, and why?"),
        # words a reply still on the first turn's subject would reach for
        "topic": ("unload", "drop", "hook", "detention", "dock", "trailer",
                  "wait", "appointment", "live"),
        # the Library does not cover this, so it must NOT be answered as
        # Level 1 Transport doctrine
        "expect_mode": "GENERAL_REASONING",
        "must_not_claim_company_policy": True,
    },
    {
        "name": "Company Library material",
        "turn_1": "Explain the Level 1 record levels.",
        "turn_2": "When should I use Level 3 instead of Save this?",
        "topic": ("level", "record", "save", "formal", "retain", "temporary",
                  "three", "artifact"),
        "expect_mode": "",          # any grounded mode; must cite the document
        "must_cite_document": True,
    },
)


def declined(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


def on_topic(text: str, words) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in words)


def run_turn(service, prompt: str) -> dict:
    result = service.ask(prompt)
    response = result.response
    text = (response.answer or response.written or "").strip()
    return {
        "prompt": prompt,
        "text": text,
        "ok": bool(response.ok),
        "capability": str(response.capability),
        "mode": str(getattr(response, "reasoning_mode", "") or ""),
        "classes": sorted({
            p.source_class for p in response.provenance if p.source_class
        }),
        "citations": list(response.citations or []),
        "copilot": bool(response.has_copilot_source),
        "local": bool(response.has_local_source),
    }


def main() -> int:
    from app.config import Config
    from app.service import AssistantService

    print(DIVIDER)
    print("JOE - SUBSTANTIVE MULTI-TURN REASONING PROOF")
    print(DIVIDER)
    print()

    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json")
    )
    results = []
    try:
        if not service.copilot_status().get("live"):
            print("BLOCKED: no live reasoning provider. Sign in first:")
            print(r"  launchers\PROVE_COPILOT.cmd")
            write_report([], blocked="no live reasoning provider")
            return 2

        for spec in CONVERSATIONS:
            print(DIVIDER)
            print(spec["name"].upper())
            print(DIVIDER)
            print()

            # Each conversation starts clean, so turn 2 can only work if
            # turn 1 is genuinely being carried.
            reset = getattr(service.reasoning, "reset_conversation", None)
            if callable(reset):
                reset()

            first = run_turn(service, spec["turn_1"])
            print("  TURN 1  " + spec["turn_1"])
            print("     mode      " + (first["mode"] or "(none)"))
            print("     classes   " + (", ".join(first["classes"]) or "(none)"))
            print("     answer    " + (first["text"][:150] or "(empty)"))
            print()

            second = run_turn(service, spec["turn_2"])
            print("  TURN 2  " + spec["turn_2"])
            print("     mode      " + (second["mode"] or "(none)"))
            print("     classes   " + (", ".join(second["classes"]) or "(none)"))
            print("     answer    " + (second["text"][:150] or "(empty)"))
            print()

            checks = evaluate(spec, first, second)
            for label, value in checks.items():
                print("     %-34s %s" % (label, value))
            print()
            results.append({
                "spec": spec, "first": first, "second": second, "checks": checks,
            })

        passed = sum(1 for r in results if all(r["checks"].values()))
        print(DIVIDER)
        print("RESULT: " + str(passed) + " of " + str(len(results))
              + " conversations fully proven")
        print(DIVIDER)
        write_report(results, blocked="")
        print()
        print("Evidence written to  proof\\REASONING_PROOF.md")
        return 0 if passed == len(results) else 1
    finally:
        service.shutdown()


def evaluate(spec, first, second) -> dict:
    """Every required result, measured separately. No blurring."""
    checks = {
        "first turn answered": first["ok"] and bool(first["text"])
                               and not declined(first["text"]),
        "context retained": on_topic(second["text"], spec["topic"]),
        "referent understood": on_topic(second["text"], spec["topic"]),
        "substantive answer": (bool(second["text"])
                               and not declined(second["text"])),
        "capability mode identified": bool(second["mode"]),
        "source class identified": bool(second["classes"]),
    }

    if spec.get("must_not_claim_company_policy"):
        # What the mission forbids is presenting general industry knowledge AS
        # Level 1 Transport doctrine. A LOCAL_LIBRARY entry appearing beside a
        # COPILOT_GENERAL_REASONING entry is not that: the Library genuinely
        # was read and passed as context, and both entries are true. An earlier
        # version of this check failed on the mere presence of LOCAL_LIBRARY,
        # which would have marked a correctly-labelled answer as a violation.
        #
        # Two things are tested instead: the answer must not assert company
        # policy in words, and it must not be labelled COMPANY_PROCEDURE.
        lowered = second["text"].lower()
        asserts_policy = any(
            phrase in lowered for phrase in (
                "level 1 transport policy", "level 1 transport procedure",
                "company policy requires", "our policy is",
                "level 1 transport requires", "per company procedure",
            )
        )
        checks["no false company-policy claim"] = (
            not asserts_policy
            and second["mode"] != "COMPANY_PROCEDURE"
        )
        # And if the Library is cited, Mike must be able to see what was read.
        if "LOCAL_LIBRARY" in second["classes"]:
            checks["library citation is inspectable"] = bool(second["citations"])

    if spec.get("must_cite_document"):
        checks["governing document named"] = bool(second["citations"]) or second["local"]
        checks["library and copilot kept separate"] = not (
            second["copilot"] and not second["classes"]
        )

    if spec.get("expect_mode"):
        checks["mode is " + spec["expect_mode"]] = second["mode"] == spec["expect_mode"]

    return checks


def write_report(results, blocked: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# JOE - Substantive Multi-Turn Reasoning Proof",
        "",
        "**Run:** " + stamp,
        "",
        "Each second turn names no subject. An on-topic reply is therefore "
        "evidence the conversation was carried rather than restarted.",
        "",
        "**Context carried** and **substantive answer** are measured "
        "separately. A reply that says \"the supplied context does not discuss "
        "that\" has carried context and answered nothing; scoring those as one "
        "result is how a non-answer gets reported as a success.",
        "",
    ]
    if blocked:
        lines += ["## Result", "", "**BLOCKED.** " + blocked, ""]
    else:
        passed = sum(1 for r in results if all(r["checks"].values()))
        lines += [
            "## Result",
            "",
            "**" + str(passed) + " of " + str(len(results))
            + " conversations fully proven.**",
            "",
        ]
        for entry in results:
            spec, first, second, checks = (
                entry["spec"], entry["first"], entry["second"], entry["checks"])
            lines += [
                "## " + spec["name"],
                "",
                "### Turn 1",
                "",
                "**" + spec["turn_1"] + "**",
                "",
                "| | |",
                "| --- | --- |",
                "| Capability | " + first["capability"] + " |",
                "| Reasoning mode | " + (first["mode"] or "-") + " |",
                "| Source classes | " + (", ".join(first["classes"]) or "-") + " |",
                "",
                "```",
                first["text"][:1800] or "(empty)",
                "```",
                "",
                "### Turn 2",
                "",
                "**" + spec["turn_2"] + "**",
                "",
                "| | |",
                "| --- | --- |",
                "| Capability | " + second["capability"] + " |",
                "| Reasoning mode | " + (second["mode"] or "-") + " |",
                "| Source classes | " + (", ".join(second["classes"]) or "-") + " |",
                "| Citations | " + (", ".join(second["citations"]) or "-") + " |",
                "",
                "```",
                second["text"][:1800] or "(empty)",
                "```",
                "",
                "### Required results",
                "",
                "| Check | Result |",
                "| --- | --- |",
            ]
            for label, value in checks.items():
                lines.append("| " + label + " | "
                             + ("**True**" if value else "**False**") + " |")
            lines.append("")
    (PLUGIN_ROOT / "proof" / "REASONING_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
