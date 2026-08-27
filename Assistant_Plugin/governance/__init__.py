"""Governance: constitutional boundaries, enforced in code.

Every response leaving the application core passes through `review()`. A
response that would breach the Constitution is refused or corrected here, not
downstream and not by convention.

Governing doctrine:
  JOE_CONSTITUTION_v1/02_CONSTITUTION_v1.md
  JOE_CONSTITUTION_v1/03_ARCHITECTURE_v1.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from contracts import AssistantResponse, Provenance, SourceMode
from contracts import MODE_PERMITTED_CLASSES, SourceClass

# Constitution 3.1 - claims of approval, decision, or completed action.
# Anchored so ordinary narration ("Print request recorded") does not trip.
FORBIDDEN_CLAIMS = (
    "i approve", "we approve", "is approved", "has been approved",
    "i authorize", "is authorized", "hereby authorize",
    "i have decided", "we have decided", "the decision is", "decision made",
    "load accepted", "i accepted the load", "i booked", "booked the load",
    "i dispatched", "has been dispatched",
    "payment sent", "funds committed", "i have paid",
    "email sent", "i sent the email", "i replied", "message sent",
    "this is now policy", "doctrine is updated", "policy is changed",
    "i have signed", "signed on behalf",
    "printed successfully", "the document was printed", "sent to the printer",
    "i updated dispatch", "written to dispatch", "dispatch has been updated",
)

# Constitution 3.1 - approval-by-omission phrasing.
SILENCE_CONSENT_PATTERNS = (
    r"unless you (?:say|reply|respond|object|stop)",
    r"if i (?:do ?n[o']?t|don't) hear",
    r"will (?:proceed|go ahead|execute|apply) automatically",
    r"takes effect unless",
    r"auto-?(?:approve|accept|apply|execute)",
    r"assume(?:d)? (?:approval|consent|agreement)",
)

# Words that assert an operational fact. Such statements need provenance.
OPERATIONAL_TERMS = (
    "load", "loads", "rate", "rates", "appointment", "appointments",
    "delivery", "pickup", "mission", "broker", "customer", "dispatch",
    "schedule", "calendar", "capacity", "status", "settlement", "invoice",
)


class GovernanceError(RuntimeError):
    """Raised when a response would breach the Constitution."""


@dataclass
class GovernanceFinding:
    rule: str
    detail: str
    severity: str = "SERIOUS"   # CRITICAL | SERIOUS | DRIFT

    def to_dict(self) -> dict:
        return {"rule": self.rule, "detail": self.detail, "severity": self.severity}


@dataclass
class GovernanceReport:
    findings: list[GovernanceFinding] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.findings

    @property
    def critical(self) -> list[GovernanceFinding]:
        return [f for f in self.findings if f.severity == "CRITICAL"]

    def to_dict(self) -> dict:
        return {
            "clean": self.clean,
            "findings": [f.to_dict() for f in self.findings],
            "corrections": list(self.corrections),
        }


# ---- individual checks --------------------------------------------------


def find_authority_claims(text: str) -> list[str]:
    lowered = " ".join((text or "").lower().split())
    return [phrase for phrase in FORBIDDEN_CLAIMS if phrase in lowered]


def find_silence_consent(text: str) -> list[str]:
    lowered = " ".join((text or "").lower().split())
    found = []
    for pattern in SILENCE_CONSENT_PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            found.append(match.group(0))
    return found


def mentions_operational_fact(text: str) -> bool:
    lowered = " ".join((text or "").lower().split())
    return any(re.search(r"\b" + term + r"\b", lowered) for term in OPERATIONAL_TERMS)


def is_stale(provenance: Provenance, max_age_minutes: int) -> bool:
    """A live reading older than the configured window is stale."""
    if provenance.mode != SourceMode.LIVE:
        return False
    from contracts import stamp, utc_now
    from datetime import datetime, timezone, timedelta

    try:
        text = provenance.as_of
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        read_at = datetime.fromisoformat(text)
        if read_at.tzinfo is None:
            read_at = read_at.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return True
    return utc_now() - read_at > timedelta(minutes=max_age_minutes)


# ---- the gate -----------------------------------------------------------


def _refusal_summary(critical) -> str:
    """Say what was actually wrong.

    Every refusal used to read "It claimed authority I do not have", which was
    accurate for authority breaches and misleading for every other kind - a
    grounding-mode breach is not an authority claim, and describing it as one
    sends the reader looking for the wrong defect."""
    rules = [f.rule for f in critical]
    if any("authority" in r or "approve" in r for r in rules):
        return "It claimed authority I do not have."
    if any("Reasoning mode" in r for r in rules):
        return "It was reasoned in a way that mode does not permit."
    if any("Provenance" in r for r in rules):
        return "Its sources were labelled in a way I cannot stand behind."
    if any("silence" in r for r in rules):
        return "It treated silence as consent."
    return "It broke a rule I am not allowed to break."


class Governor:
    """Reviews every response before it reaches Mike."""

    def __init__(self, stale_after_minutes: int = 15) -> None:
        self.stale_after_minutes = stale_after_minutes
        self.history: list[GovernanceReport] = []

    def review(self, response: AssistantResponse) -> GovernanceReport:
        report = GovernanceReport()
        body = " ".join(
            [response.answer, response.written, response.recommendation]
        )

        # 3.1 - no approval, no claimed action
        claims = find_authority_claims(body)
        if claims:
            report.findings.append(
                GovernanceFinding(
                    rule="Constitution 3.1 - may not approve or claim action",
                    detail="refused phrasing: " + ", ".join(claims),
                    severity="CRITICAL",
                )
            )

        # 3.1 - silence is never consent
        silence = find_silence_consent(body)
        if silence:
            report.findings.append(
                GovernanceFinding(
                    rule="Constitution 3.1 - silence is never consent",
                    detail="refused phrasing: " + ", ".join(silence),
                    severity="CRITICAL",
                )
            )

        # 3.3 / Architecture 4.3 - operational facts need provenance.
        # HELP text lists what JOE can do; naming a capability is not
        # asserting an operational fact, so it is exempt.
        if (
            response.capability != "HELP"
            and mentions_operational_fact(body)
            and not response.provenance
        ):
            response.add_notice(
                "No source is attached to this. Treat it as general wording, "
                "not an operational fact."
            )
            report.corrections.append("added missing-provenance notice")

        # 3.3 - stale is not current
        for provenance in response.provenance:
            if is_stale(provenance, self.stale_after_minutes):
                response.add_notice(
                    "This reading of " + provenance.source + " is older than "
                    + str(self.stale_after_minutes) + " minutes. It may not be current."
                )
                report.corrections.append("added stale-data notice for " + provenance.source)

        # SAMPLE data must be visibly labelled
        if SourceMode.SAMPLE in response.modes:
            response.add_notice(
                "SAMPLE DATA - this did not come from a live source."
            )
            report.corrections.append("added sample-data notice")

        # A declared reasoning mode may only produce the classes it is allowed
        # to produce. COMPANY_PROCEDURE answering from general knowledge is
        # inventing company policy; WEB_GROUNDED_RESEARCH answering without web
        # grounding is general reasoning wearing research's clothes. Both are
        # refusals, not stylistic slips.
        mode = getattr(response, "reasoning_mode", "") or ""
        if mode:
            permitted = MODE_PERMITTED_CLASSES.get(mode)
            if permitted is None:
                report.findings.append(
                    GovernanceFinding(
                        rule="Reasoning mode - unknown mode declared",
                        detail=mode + " is not a defined ReasoningMode",
                        severity="CRITICAL",
                    )
                )
            else:
                for provenance in response.provenance:
                    source_class = getattr(provenance, "source_class", "") or ""
                    if source_class and source_class not in permitted:
                        report.findings.append(
                            GovernanceFinding(
                                rule="Reasoning mode - source class not permitted",
                                detail=(
                                    mode + " may not produce " + source_class
                                    + " (from " + str(provenance.source) + ")"
                                ),
                                severity="CRITICAL",
                            )
                        )

        # A Copilot source may never wear a class Copilot can never hold.
        for provenance in response.provenance:
            source_class = getattr(provenance, "source_class", "") or ""
            source = str(getattr(provenance, "source", "") or "")
            if source_class in SourceClass.NEVER_FROM_COPILOT and "copilot" in source.lower():
                report.findings.append(
                    GovernanceFinding(
                        rule="Provenance - Copilot claiming a class it may never hold",
                        detail=source + " claimed " + source_class,
                        severity="CRITICAL",
                    )
                )

        # Authority flags must be false. They are literals in to_dict(), but a
        # true attribute is itself a defect worth catching.
        for name in ("approved", "decided", "acted_on", "operational_write"):
            if getattr(response, name, False):
                report.findings.append(
                    GovernanceFinding(
                        rule="Constitution Article III - authority flag set",
                        detail=name + " was True on a response",
                        severity="CRITICAL",
                    )
                )
                setattr(response, name, False)
                report.corrections.append("forced " + name + " to False")

        self.history.append(report)
        return report

    def enforce(self, response: AssistantResponse) -> AssistantResponse:
        """Review and refuse anything critical.

        A critical breach does not get softened or reworded into something
        acceptable. It is replaced with a refusal, because a reworded claim
        still reached the page once.
        """
        report = self.review(response)
        if report.critical:
            return AssistantResponse(
                capability=response.capability,
                answer=(
                    "I stopped that response. " + _refusal_summary(report.critical)
                ),
                written=(
                    "The response JOE was about to give was refused by "
                    "its own governance layer.\n\n"
                    + "\n".join(
                        "- " + f.rule + ": " + f.detail for f in report.critical
                    )
                    + "\n\nJOE may recommend. It may not approve, "
                    "decide, or claim a completed action. Mike Zachary remains "
                    "final authority."
                ),
                ok=False,
                failure="refused by governance",
                notices=["Refused by governance. Nothing was done."],
            )
        return response


AUTHORITY_STATEMENT = (
    "JOE may monitor, explain, research, retrieve, summarize, draft, "
    "recommend, remember, train, assist with procedure, surface uncertainty, "
    "and submit requests. It may not approve, decide, own Dispatch records, "
    "alter operational truth, or act on silence. Mike Zachary remains final "
    "authority."
)
