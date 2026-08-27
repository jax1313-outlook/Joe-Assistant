"""When JOE is allowed to start talking.

    Dispatch may initiate workflow. JOE may initiate conversation.
    Those are not the same thing.

Dispatch sweeps, scores, analyses, builds cards and tracks workflow, and it
does all of it without saying a word. A card is workflow state. So is a score,
a risk calculation, an archived card, and the Email Sent banner. None of it is
a reason to interrupt a man driving a truck.

JOE speaks on exactly two occasions: when Mike asks, and when an alert exists.
An alert is not an event - it is something requiring Mike's attention.

WHY THIS IS AN ALLOWLIST. A blocklist would mean every new Dispatch workflow
event becomes an interruption by default, and the person who adds it will not
be thinking about a cab at seventy miles an hour. Silence is the default here.
An alert kind JOE does not recognise is not spoken, and the operator is told it
was withheld rather than it vanishing quietly - a channel that silently drops
things is its own kind of lie.

That is a boundary JOE keeps on its own side. Dispatch is not expected to send
workflow noise down this channel; JOE simply does not depend on that.
"""

from __future__ import annotations

# What earns an interruption. Each is something Mike would want to know while
# driving, and each names a consequence rather than a state change.
SPEAKABLE = {
    "route_closure": "a route closure affecting an active mission",
    "appointment_changed": "a pickup or delivery appointment that moved",
    "broker_replied": "a broker replying on a load Mike is working",
    "decision_required": "a decision waiting on Mike",
    "compliance_risk": "a compliance or hard-stop risk",
    "detention_started": "detention running on an active load",
}

# Named so the boundary is visible and testable, not to be checked at runtime -
# the allowlist above already decides. These are the ones most likely to be
# proposed as alerts, and none of them is one.
WORKFLOW_ONLY = {
    "card_found": "the sweeper found a card",
    "scoring_complete": "scoring finished",
    "risk_calculated": "risk was computed",
    "card_updated": "a card changed",
    "card_archived": "a card was archived",
    "email_sent": "the auto-interest email went out",
    "sweep_started": "a sweep began",
    "sweep_finished": "a sweep ended",
}

# Ordered by what should reach Mike first when several arrive together. A
# compliance risk on a load being run now outranks a broker's reply.
URGENCY = (
    "compliance_risk",
    "route_closure",
    "detention_started",
    "decision_required",
    "appointment_changed",
    "broker_replied",
)


def kind_of(alert) -> str:
    return str((alert or {}).get("kind") or "").strip().lower()


def is_speakable(alert) -> bool:
    """May JOE open its mouth about this, unasked?"""
    return kind_of(alert) in SPEAKABLE


def withheld_reason(alert) -> str:
    """Why an alert was not spoken. Never silence without a reason."""
    kind = kind_of(alert)
    if not kind:
        return "no alert kind given"
    if kind in WORKFLOW_ONLY:
        return ("workflow state, not an alert - " + WORKFLOW_ONLY[kind]
                + ". Dispatch owns it.")
    if kind not in SPEAKABLE:
        return ("unrecognised alert kind \"" + kind + "\" - not spoken. Add it "
                "to SPEAKABLE deliberately if it should interrupt Mike.")
    return ""


def rank(alert) -> int:
    """Lower comes first. Unknown kinds sort last."""
    kind = kind_of(alert)
    return URGENCY.index(kind) if kind in URGENCY else len(URGENCY)


def speakable(alerts) -> list:
    """Only what earns an interruption, most urgent first."""
    return sorted([a for a in (alerts or []) if is_speakable(a)], key=rank)


def spoken(alert) -> str:
    """One sentence: what happened, and what it touches.

    An alert that does not say what it affects is not actionable at the wheel -
    "appointment changed" leaves Mike asking which load, which is a second
    question he has to ask instead of an answer he was given."""
    if not is_speakable(alert):
        return ""

    kind = kind_of(alert)
    subject = str(alert.get("subject") or "").strip()
    detail = str(alert.get("detail") or "").strip()
    load = str(alert.get("load_id") or "").strip()

    lead = {
        "compliance_risk": "Compliance risk",
        "route_closure": "Route closure",
        "detention_started": "Detention started",
        "decision_required": "Decision needed",
        "appointment_changed": "Appointment changed",
        "broker_replied": "Broker replied",
    }[kind]

    parts = [lead]
    if subject:
        parts.append(subject)
    elif load:
        parts.append("load " + load)
    sentence = " on ".join(parts) if len(parts) > 1 else parts[0]
    if detail:
        sentence += ": " + detail
    return sentence.rstrip(".") + "."
