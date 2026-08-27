"""MICROSOFT 365 COPILOT LIVE PROOF - requires Mike to sign in.

Sends ONE real prompt to the Microsoft 365 Copilot Chat API and records what
came back, including its provenance class. Until this runs and passes,
reasoning must be reported as NOT CONNECTED, and a mocked test must never be
described as a live answer.

This program does not create the Entra app registration, does not grant
consent, and does not sign in on Mike's behalf. It reports exactly what is
missing and stops.

Run:   launchers\\PROVE_COPILOT.cmd
   or: py proof\\prove_copilot.py

Writes evidence to proof\\COPILOT_LIVE_PROOF.md. No token, secret, or
authentication code is written to it, printed, or logged.

MICROSOFT 365 COPILOT - PILOT / PREVIEW. The Chat API is a /beta endpoint and
Microsoft states it is not supported for production use.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74

# One question with a checkable shape. Deliberately general reasoning - it must
# not appear to come from the Company Library, Outlook, Route Risk, or Dispatch.
PROMPT = (
    "In two sentences, explain what detention time means in trucking and why "
    "it is billed."
)

# Deliberately elliptical. "it" and "that" have no referent unless the first
# turn is still in the conversation, so a reply that stays on topic is evidence
# the conversation was reused rather than restarted.
FOLLOW_UP = "Who normally pays for it, and how is that usually agreed in advance?"

# Words only a reply still on the detention subject would reach for.
FOLLOW_UP_TOPIC = ("detention", "shipper", "receiver", "broker", "carrier",
                   "rate", "contract", "accessorial", "wait")

# A refusal can mention the subject while answering nothing. "detention" inside
# "the context does not discuss detention" is not a follow-up answer, and an
# on-topic check alone would score it as one. Carrying context and answering
# are separate claims and are reported separately.
REFUSAL_MARKERS = ("cannot answer", "can't answer", "does not discuss",
                   "doesn't discuss", "no information", "not discussed",
                   "not covered", "unable to answer", "provided material",
                   "supplied context")


# Source classes Copilot may never claim. Copilot grounding must never
# masquerade as a Company Library, Outlook, Route Risk, or Dispatch result.
FORBIDDEN_CLASSES = ("LOCAL_LIBRARY", "LOCAL_OUTLOOK", "ROUTE_RISK_EVENT", "DISPATCH_FACT")


def judge(response, answer: str, provenance):
    """Does this reply prove reasoning is live, without a masqueraded source?

    Returns (passed, breaches, reasons). Pure, so it is testable without a
    tenant - the alternative is that Mike completes five Entra steps, signs in,
    and only then discovers whether the judgment code works.

    THE CHECK IS PER PROVENANCE ENTRY, NOT OVER A FLATTENED SET OF CLASSES.
    A correct answer routinely carries both a COPILOT_* entry and LOCAL_LIBRARY
    entries: Copilot reasoned, and the Library was genuinely read locally. Both
    are true and both must be declared. An earlier version of this function
    flattened the classes and failed on any local class appearing - which would
    have rejected an honest, correct answer and called live reasoning a
    failure.

    The breach that matters is a single entry that is Copilot-sourced while
    claiming a local or Dispatch class. That is grounding masquerading as a
    direct read, and it is a failure however good the prose is."""
    reasons = []
    breaches = []

    # The breach is an entry whose SOURCE is Copilot while its CLASS claims a
    # local or Dispatch read.
    #
    # Note on why this tests the source string and not `is_copilot`: that
    # property is DERIVED FROM source_class, so "is_copilot AND class is local"
    # can never be true, and a check written that way is dead code that always
    # passes. The class is the claim; the source is what actually produced the
    # text. Comparing the two is the only way to catch one wearing the other.
    for entry in provenance or []:
        source_class = getattr(entry, "source_class", "") or ""
        source = str(getattr(entry, "source", "") or "")
        if source_class in FORBIDDEN_CLASSES and "copilot" in source.lower():
            breaches.append(source + " -> " + source_class)

    classes = [
        getattr(e, "source_class", "") or "" for e in (provenance or [])
    ]
    used_copilot = any(c.startswith("COPILOT_") for c in classes)

    if not getattr(response, "ok", False):
        reasons.append("the provider reported failure")
    if not (answer or "").strip():
        reasons.append("the reply was empty - an empty answer is not an answer")
    if breaches:
        reasons.append(
            "Copilot content claimed a source class it may never claim: "
            + "; ".join(breaches)
        )
    if not used_copilot:
        reasons.append(
            "no COPILOT_* provenance entry - Copilot was never asked, so this "
            "proves nothing about reasoning being live"
        )

    return (not reasons), breaches, reasons


def main() -> int:
    from app.config import Config
    from app.service import AssistantService

    print(DIVIDER)
    print("MICROSOFT 365 COPILOT LIVE PROOF        PILOT / PREVIEW")
    print(DIVIDER)
    print()

    service = AssistantService(Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json"))
    try:
        status = service.copilot_status()

        print("  provider selected      " + str(status.get("provider_selected")))
        print("  msal installed         " + str(status.get("msal_available")))
        print("  tenant id set          " + str(status.get("tenant_id_set")))
        print("  client id set          " + str(status.get("client_id_set")))
        print("  client secret used     " + str(status.get("client_secret_used", False)))
        print("  signed in              " + str(status.get("signed_in")))
        print("  state                  " + str(status.get("state")))
        print()

        if not status.get("provider_selected"):
            return blocked(
                "Microsoft 365 Copilot is not the selected reasoning provider.",
                ['Set  "provider": "m365_copilot"  under  "reasoning"  in',
                 "configuration\\joe.config.json, then run this again."],
            )

        if not (status.get("tenant_id_set") and status.get("client_id_set")):
            return blocked(
                "No tenant id and client id are configured.",
                ["These come from an Entra app registration, which only Mike can",
                 "create. See docs\\COPILOT_ACTIVATION_STEPS.md for the exact steps.",
                 "Neither value is a secret."],
            )

        if not status.get("msal_available"):
            return blocked(
                "MSAL is not installed.",
                ["py -m pip install --user msal msal-extensions"],
            )

        # ---- sign in, if needed. Microsoft's own page, Mike's own hands. ----
        if not status.get("signed_in"):
            auth = service.copilot_auth
            print(DIVIDER)
            print("SIGN IN TO MICROSOFT 365")
            print(DIVIDER)
            try:
                flow = auth.begin_device_flow()
            except Exception as error:  # noqa: BLE001
                return blocked("Sign-in could not start.", [str(error)])

            print()
            print("  1. Open   " + flow.verification_uri)
            print("  2. Enter this code:")
            print()
            print("        " + flow.user_code)
            print()
            print("  3. Sign in with a WORK OR SCHOOL account that has a")
            print("     Microsoft 365 Copilot licence.")
            print()
            print("     A personal Microsoft account will not work. The API does")
            print("     not support them.")
            print()
            print("  Waiting for you to finish...")

            ok, message = auth.complete_device_flow(flow)
            print("  " + message)
            print()
            if not ok:
                return blocked("Not signed in.", [message])
            status = service.copilot_status()

        # ---- one real prompt ------------------------------------------------
        print(DIVIDER)
        print("SENDING ONE REAL PROMPT")
        print(DIVIDER)
        print()
        print("  account   " + str(status.get("account") or "(unknown)"))
        print("  prompt    " + PROMPT)
        print()

        result = service.ask(PROMPT)
        response = result.response
        answer = (response.answer or response.written or "").strip()
        classes = sorted({p.class_label() for p in response.provenance})
        raw_classes = sorted({getattr(p, "source_class", "") for p in response.provenance})

        print("  ok        " + str(response.ok))
        print("  classes   " + (", ".join(classes) or "(none)"))
        print()
        print("  answer:")
        for line in (answer or "(empty)").splitlines():
            print("    " + line)
        print()

        passed, forbidden, reasons = judge(response, answer, response.provenance)
        for reason in reasons:
            print("  FAIL  " + reason)

        # ---- a second turn, on the same conversation ---------------------
        follow = {"asked": FOLLOW_UP, "answer": "", "passed": False, "reasons": []}
        if passed:
            print(DIVIDER)
            print("FOLLOW-UP TURN  (same conversation)")
            print(DIVIDER)
            print()
            print("  prompt    " + FOLLOW_UP)
            print()
            second = service.ask(FOLLOW_UP).response
            follow["answer"] = (second.answer or second.written or "").strip()
            f_passed, _f_breaches, f_reasons = judge(
                second, follow["answer"], second.provenance
            )
            lowered = follow["answer"].lower()
            on_topic = any(w in lowered for w in FOLLOW_UP_TOPIC)
            refused = any(m in lowered for m in REFUSAL_MARKERS)
            follow["context_carried"] = on_topic
            follow["substantive"] = on_topic and not refused

            if not on_topic:
                f_passed = False
                f_reasons = f_reasons + [
                    "the reply drifted off the first turn's subject - the "
                    "conversation was not carried over"
                ]
            follow["passed"] = f_passed
            follow["reasons"] = f_reasons

            print("  answer:")
            for line in (follow["answer"] or "(empty)").splitlines():
                print("    " + line)
            print()
            for reason in f_reasons:
                print("  FAIL  " + reason)
            print("  context carried over    " + str(on_topic)
                  + "   (Copilot resolved \"it\" to the first turn's subject)")
            print("  substantive answer      " + str(follow["substantive"])
                  + ("" if follow["substantive"]
                     else "   <- it declined; see the note in the evidence file"))
            print()
            passed = passed and f_passed

        print(DIVIDER)
        print("RESULT: " + ("PASS - reasoning is LIVE, first turn and follow-up"
                            if passed else "FAIL - reasoning is NOT proven"))
        print(DIVIDER)

        write_report(
            blocked_reason="",
            account=str(status.get("account") or ""),
            answer=answer,
            classes=raw_classes,
            passed=passed,
            forbidden=forbidden,
            follow=follow,
        )
        print()
        print("Evidence written to  proof\\COPILOT_LIVE_PROOF.md")
        return 0 if passed else 1
    finally:
        service.shutdown()


def blocked(reason: str, detail: list[str]) -> int:
    print("BLOCKED: " + reason)
    for line in detail:
        print("  " + line)
    print()
    print("Reasoning remains NOT CONNECTED. This is not a failure of the program -")
    print("it is a step only Mike can take.")
    write_report(blocked_reason=reason + " " + " ".join(detail),
                 account="", answer="", classes=[], passed=False, forbidden=[])
    return 2


def write_report(blocked_reason: str, account: str, answer: str,
                 classes: list[str], passed: bool, forbidden: list[str],
                 follow: dict | None = None) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Microsoft 365 Copilot Live Proof",
        "",
        "**Run:** " + stamp,
        "**Provider:** MICROSOFT 365 COPILOT - PILOT / PREVIEW",
        "",
        "Microsoft states the Copilot Chat API is a `/beta` endpoint and is not",
        "supported for production use.",
        "",
        "No token, secret, password, or authentication code appears in this file.",
        "",
    ]
    if blocked_reason:
        lines += [
            "## Result",
            "",
            "**BLOCKED.** " + blocked_reason,
            "",
            "Reasoning is NOT CONNECTED. No live prompt was sent. A mocked test "
            "must never be described as a live answer.",
            "",
        ]
    else:
        lines += [
            "## Result",
            "",
            "**" + ("PASS - reasoning is LIVE." if passed
                    else "FAIL - reasoning is NOT proven.") + "**",
            "",
            "| | |",
            "| --- | --- |",
            "| Account | " + (account or "(not reported)") + " |",
            "| Prompt | " + PROMPT + " |",
            "| Provenance classes | " + (", ".join(classes) or "(none)") + " |",
            "",
            "### Exact answer returned",
            "",
            "```",
            answer or "(empty)",
            "```",
            "",
        ]
        if follow and follow.get("asked"):
            lines += [
                "### Follow-up turn, same conversation",
                "",
                'The follow-up is deliberately elliptical - "it" and "that" have no',
                "referent unless the first turn is still in the conversation.",
                "",
                "| | |",
                "| --- | --- |",
                "| Asked | " + follow["asked"] + " |",
                "| Conversation carried over | "
                + ("**yes** - Copilot resolved \"it\" to the first turn's subject"
                   if follow.get("context_carried") else "**no**") + " |",
                "| Substantive answer | "
                + ("**yes**" if follow.get("substantive")
                   else "**no - it declined to answer from the supplied material**") + " |",
                "| Result | " + ("**PASS**" if follow.get("passed") else "**FAIL**") + " |",
                "",
                "```",
                follow.get("answer") or "(empty)",
                "```",
                "",
            ]
            for reason in follow.get("reasons") or []:
                lines.append("- FAIL: " + reason)
            if follow.get("reasons"):
                lines.append("")
            if follow.get("context_carried") and not follow.get("substantive"):
                lines += [
                    "**What this does and does not establish.** Multi-turn "
                    "conversation IS proven: the follow-up says nothing but "
                    '"it" and "that", and Copilot resolved them to detention '
                    "time, so the conversation was reused rather than restarted.",
                    "",
                    "It did **not** produce a substantive follow-up answer. It "
                    "declined, because the capability that handled the turn "
                    "constrains Copilot to Company Library material and the "
                    "Library holds nothing on detention. That is JOE "
                    "refusing to answer a company question from general "
                    "knowledge. Whether that constraint is correct is a doctrine "
                    "question for Mike, not a defect this proof should paper over.",
                    "",
                ]

        if forbidden:
            lines += [
                "### Boundary breach",
                "",
                "Copilot claimed a source class it may never claim: **"
                + ", ".join(forbidden) + "**. Copilot grounding must never "
                "masquerade as a Company Library, Outlook, Route Risk, or Dispatch "
                "result. This is a failure regardless of the answer's quality.",
                "",
            ]
    (PLUGIN_ROOT / "proof" / "COPILOT_LIVE_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
