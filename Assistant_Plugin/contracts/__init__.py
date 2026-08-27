"""Contracts: the only shapes that cross a capability boundary.

Every exchange between the application core and a bounded capability uses one
of these objects. A capability never hands back a raw internal object, and the
core never reaches into a capability's internals.

Governing doctrine: JOE_CONSTITUTION_v1, Document 3, section 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stamp(moment: datetime | None = None) -> str:
    return (moment or utc_now()).astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


class SourceMode:
    """How real the data behind a result is. Never guessed, never omitted."""

    LIVE = "LIVE"            # a real, connected source was read
    SAMPLE = "SAMPLE"        # fixture / sample data, clearly not live
    READY = "READY"          # a real source is present but not yet contacted
    UNAVAILABLE = "UNAVAILABLE"  # the source could not be reached
    NONE = "NONE"            # no external source was involved

    ALL = (LIVE, SAMPLE, READY, UNAVAILABLE, NONE)


LABEL = {
    SourceMode.LIVE: "LIVE",
    SourceMode.SAMPLE: "SAMPLE DATA",
    SourceMode.READY: "READY",
    SourceMode.UNAVAILABLE: "UNAVAILABLE",
    SourceMode.NONE: "-",
}



class SourceClass:
    """Where a statement came from. Kept distinct so one can never pass as
    another.

    Copilot grounding is NOT a Company Library result, NOT an Outlook read,
    NOT a route-risk event, and NOT a Dispatch fact - however confidently it
    is worded. These classes are the mechanism that keeps that true.
    """

    LOCAL_LIBRARY = "LOCAL_LIBRARY"
    LOCAL_OUTLOOK = "LOCAL_OUTLOOK"
    COPILOT_WORK_GROUNDED = "COPILOT_WORK_GROUNDED"
    COPILOT_WEB_GROUNDED = "COPILOT_WEB_GROUNDED"
    COPILOT_GENERAL_REASONING = "COPILOT_GENERAL_REASONING"
    ROUTE_RISK_EVENT = "ROUTE_RISK_EVENT"
    DISPATCH_FACT = "DISPATCH_FACT"
    # Something Mike told JOE. True that he said it; NOT independently
    # verified, and it must never be presented as though it were.
    USER_SUPPLIED_INFORMATION = "USER_SUPPLIED_INFORMATION"
    NONE = "NONE"

    ALL = (
        LOCAL_LIBRARY,
        LOCAL_OUTLOOK,
        COPILOT_WORK_GROUNDED,
        COPILOT_WEB_GROUNDED,
        COPILOT_GENERAL_REASONING,
        ROUTE_RISK_EVENT,
        DISPATCH_FACT,
        USER_SUPPLIED_INFORMATION,
        NONE,
    )

    # Classes JOE reads directly and can stand behind itself.
    LOCAL = (LOCAL_LIBRARY, LOCAL_OUTLOOK)

    # Classes that came from Copilot. Never a local read.
    COPILOT = (
        COPILOT_WORK_GROUNDED,
        COPILOT_WEB_GROUNDED,
        COPILOT_GENERAL_REASONING,
    )

    # Defined, produced by nothing in this build.
    NOT_IMPLEMENTED = (ROUTE_RISK_EVENT, DISPATCH_FACT)

    # Classes no Copilot answer may ever wear. Copilot grounding must never
    # masquerade as a direct read, an operational event, or Mike's own words.
    NEVER_FROM_COPILOT = (
        LOCAL_LIBRARY,
        LOCAL_OUTLOOK,
        ROUTE_RISK_EVENT,
        DISPATCH_FACT,
        USER_SUPPLIED_INFORMATION,
    )


class ReasoningMode:
    """How JOE is allowed to reason for a given question.

    One universal grounding rule does not fit every question. Asking what a
    drop-and-hook is deserves general industry knowledge; asking what Level 1
    Transport's procedure is deserves the Company Library and nothing else.
    Applying the strict rule everywhere makes JOE useless; applying the loose
    rule everywhere makes JOE dangerous.
    """

    # Approved Company Library material only. Never invent company policy.
    COMPANY_PROCEDURE = "COMPANY_PROCEDURE"
    # Reason over one selected document, separating fact from explanation.
    SELECTED_DOCUMENT = "SELECTED_DOCUMENT"
    # General industry knowledge. Never Level 1 Transport doctrine.
    GENERAL_REASONING = "GENERAL_REASONING"
    # Microsoft 365 enterprise grounding, attributions preserved.
    WORK_GROUNDED = "WORK_GROUNDED"
    # Live web grounding, citations and retrieval time preserved.
    WEB_GROUNDED_RESEARCH = "WEB_GROUNDED_RESEARCH"
    # Prepared, and cannot receive live events until Dispatch publishes the
    # approved interface. Not connected in this build.
    ROUTE_EVENT_ANALYSIS = "ROUTE_EVENT_ANALYSIS"

    ALL = (
        COMPANY_PROCEDURE,
        SELECTED_DOCUMENT,
        GENERAL_REASONING,
        WORK_GROUNDED,
        WEB_GROUNDED_RESEARCH,
        ROUTE_EVENT_ANALYSIS,
    )

    # Modes that must refuse rather than answer from general knowledge.
    LIBRARY_ONLY = (COMPANY_PROCEDURE,)

    # Modes with no live source behind them in this build.
    NOT_CONNECTED = (ROUTE_EVENT_ANALYSIS,)


REASONING_MODE_LABEL = {
    ReasoningMode.COMPANY_PROCEDURE: "Company procedure - approved Library material only",
    ReasoningMode.SELECTED_DOCUMENT: "Selected document",
    ReasoningMode.GENERAL_REASONING: "General industry knowledge - not company doctrine",
    ReasoningMode.WORK_GROUNDED: "Microsoft 365 work grounding",
    ReasoningMode.WEB_GROUNDED_RESEARCH: "Live web research",
    ReasoningMode.ROUTE_EVENT_ANALYSIS: "Route event analysis - NOT CONNECTED",
}

# The source classes each mode is permitted to produce. Anything else is a
# contract breach, not a stylistic preference.
MODE_PERMITTED_CLASSES = {
    # Copilot may EXPLAIN an approved governing document. It may not supply
    # the procedure itself, so web grounding and tenant grounding are barred -
    # company policy comes from the Company Library or JOE refuses.
    ReasoningMode.COMPANY_PROCEDURE: (
        SourceClass.LOCAL_LIBRARY,
        SourceClass.COPILOT_GENERAL_REASONING,
        SourceClass.NONE),
    ReasoningMode.SELECTED_DOCUMENT: (
        SourceClass.LOCAL_LIBRARY, SourceClass.COPILOT_GENERAL_REASONING,
        SourceClass.NONE),
    ReasoningMode.GENERAL_REASONING: (
        SourceClass.COPILOT_GENERAL_REASONING, SourceClass.LOCAL_LIBRARY,
        SourceClass.NONE),
    ReasoningMode.WORK_GROUNDED: (
        SourceClass.COPILOT_WORK_GROUNDED, SourceClass.COPILOT_GENERAL_REASONING,
        SourceClass.LOCAL_LIBRARY, SourceClass.NONE),
    ReasoningMode.WEB_GROUNDED_RESEARCH: (
        SourceClass.COPILOT_WEB_GROUNDED, SourceClass.COPILOT_GENERAL_REASONING,
        SourceClass.NONE),
    ReasoningMode.ROUTE_EVENT_ANALYSIS: (
        SourceClass.ROUTE_RISK_EVENT, SourceClass.NONE),
}


SOURCE_CLASS_LABEL = {
    SourceClass.LOCAL_LIBRARY: "Company Library (read directly)",
    SourceClass.LOCAL_OUTLOOK: "Outlook (read directly, read-only)",
    SourceClass.COPILOT_WORK_GROUNDED: "Copilot, grounded in work data",
    SourceClass.COPILOT_WEB_GROUNDED: "Copilot, grounded in web search",
    SourceClass.COPILOT_GENERAL_REASONING: "Copilot, general reasoning - no source",
    SourceClass.ROUTE_RISK_EVENT: "Route risk event",
    SourceClass.DISPATCH_FACT: "Dispatch (system of record)",
    SourceClass.USER_SUPPLIED_INFORMATION: (
        "you told JOE this - recorded, not independently verified"),
    SourceClass.NONE: "-",
}


class Capability:
    ANSWER = "ANSWER"
    LIBRARY = "LIBRARY"
    RESEARCH = "RESEARCH"
    OPERATIONS = "OPERATIONS"   # read-only awareness (calendar / mail / contacts)
    RETENTION = "RETENTION"     # save / level 3 / print / delete
    EXPLAIN = "EXPLAIN"
    HELP = "HELP"
    SUMMARIZE = "SUMMARIZE"
    DRAFT = "DRAFT"
    PROCEDURE = "PROCEDURE"

    ALL = (
        ANSWER, LIBRARY, RESEARCH, OPERATIONS, RETENTION, EXPLAIN, HELP,
        SUMMARIZE, DRAFT, PROCEDURE,
    )


@dataclass
class Provenance:
    """Where a fact came from and as of when.

    Constitution 3.3 and Architecture 4.3: an operational statement without
    provenance and an as-of time is prohibited output.
    """

    source: str
    mode: str = SourceMode.NONE
    as_of: str = field(default_factory=stamp)
    detail: str = ""
    source_class: str = SourceClass.NONE

    @property
    def is_live(self) -> bool:
        return self.mode == SourceMode.LIVE

    def label(self) -> str:
        return LABEL.get(self.mode, self.mode)

    @property
    def is_copilot(self) -> bool:
        return self.source_class in SourceClass.COPILOT

    @property
    def is_local_read(self) -> bool:
        return self.source_class in SourceClass.LOCAL

    def class_label(self) -> str:
        return SOURCE_CLASS_LABEL.get(self.source_class, self.source_class)

    def line(self) -> str:
        parts = [self.source, self.label()]
        if self.source_class != SourceClass.NONE:
            parts.append(self.class_label())
        if self.mode in (SourceMode.LIVE, SourceMode.SAMPLE):
            parts.append("as of " + self.as_of[:19].replace("T", " ") + "Z")
        if self.detail:
            parts.append(self.detail)
        return "  |  ".join(parts)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "mode": self.mode,
            "label": self.label(),
            "as_of": self.as_of,
            "detail": self.detail,
            "is_live": self.is_live,
            "source_class": self.source_class,
            "source_class_label": self.class_label(),
            "is_copilot": self.is_copilot,
            "is_local_read": self.is_local_read,
        }


@dataclass
class AssistantRequest:
    """What Mike asked, before any capability has seen it."""

    text: str
    channel: str = "text"     # text | voice
    driver_mode: bool = False
    requested_at: str = field(default_factory=stamp)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "channel": self.channel,
            "driver_mode": self.driver_mode,
            "requested_at": self.requested_at,
        }


@dataclass
class AssistantResponse:
    """What a capability hands back. The only shape the UI ever renders.

    `spoken_summary` is the short driver-mode form. `written` is the full
    parked-review text. Both always exist; the short one never replaces the
    written one.
    """

    capability: str
    answer: str                     # the direct answer, first
    written: str = ""               # full written response for parked review
    spoken_summary: str = ""        # short form for driver mode
    provenance: list[Provenance] = field(default_factory=list)
    uncertainty: str = ""
    recommendation: str = ""
    notices: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    ok: bool = True
    failure: str = ""
    # How JOE was allowed to reason for this answer. One universal grounding
    # rule does not fit every question; see ReasoningMode.
    reasoning_mode: str = ""

    # Authority flags. Emitted as literals; nothing can set them true.
    approved: bool = False
    decided: bool = False
    acted_on: bool = False
    operational_write: bool = False

    def __post_init__(self) -> None:
        if not self.written:
            self.written = self.answer
        if not self.spoken_summary:
            self.spoken_summary = self.answer

    @property
    def is_live(self) -> bool:
        return any(p.is_live for p in self.provenance)

    @property
    def modes(self) -> set[str]:
        return {p.mode for p in self.provenance}

    @property
    def source_classes(self) -> set[str]:
        return {p.source_class for p in self.provenance}

    @property
    def has_copilot_source(self) -> bool:
        return any(p.is_copilot for p in self.provenance)

    @property
    def has_local_source(self) -> bool:
        return any(p.is_local_read for p in self.provenance)

    def add_notice(self, text: str) -> None:
        if text and text not in self.notices:
            self.notices.append(text)

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "answer": self.answer,
            "written": self.written,
            "spoken_summary": self.spoken_summary,
            "provenance": [p.to_dict() for p in self.provenance],
            "uncertainty": self.uncertainty,
            "recommendation": self.recommendation,
            "notices": list(self.notices),
            "findings": list(self.findings),
            "citations": list(self.citations),
            "source_classes": sorted(self.source_classes),
            "has_copilot_source": self.has_copilot_source,
            "has_local_source": self.has_local_source,
            "ok": self.ok,
            "failure": self.failure,
            # Constitution Article III - emitted as literals, never from state.
            "approved": False,
            "decided": False,
            "acted_on": False,
            "operational_write": False,
        }


@dataclass
class CapabilityStatus:
    """What the UI shows about one capability. Truthful or it does not ship."""

    name: str
    available: bool
    mode: str
    detail: str = ""
    live_connection: bool = False
    blocker: str = ""

    def display(self) -> str:
        if self.live_connection:
            return self.name + ": LIVE" + (" - " + self.detail if self.detail else "")
        if self.mode == SourceMode.SAMPLE:
            return self.name + ": SAMPLE DATA" + (" - " + self.detail if self.detail else "")
        if self.mode == SourceMode.READY:
            return self.name + ": READY" + (" - " + self.detail if self.detail else "")
        if not self.available:
            return self.name + ": NOT CONNECTED" + (" - " + self.blocker if self.blocker else "")
        return self.name + ": " + self.mode + (" - " + self.detail if self.detail else "")

    def chip(self) -> str:
        """Short form for the status strip. Full form is display()."""
        if self.live_connection:
            return self.name + " LIVE"
        if self.mode == SourceMode.SAMPLE:
            return self.name + " SAMPLE"
        if self.mode == SourceMode.READY:
            return self.name + " READY"
        return self.name + " NOT CONNECTED"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "available": self.available,
            "mode": self.mode,
            "detail": self.detail,
            "live_connection": self.live_connection,
            "blocker": self.blocker,
            "chip": self.chip(),
            "display": self.display(),
        }


@dataclass
class ActionRequest:
    """A request for an authorized action. Never an action.

    Constitution 3.1 and Architecture 3.6: JOE proposes; Dispatch or
    Mike decides. `auto_execute` exists only so a test can assert it is always
    False - silence is never consent.
    """

    kind: str
    detail: str
    requested_at: str = field(default_factory=stamp)
    submitted: bool = False
    accepted: bool = False
    performed: bool = False
    auto_execute: bool = False
    decision_required_from: str = "Mike Zachary"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "requested_at": self.requested_at,
            "submitted": self.submitted,
            "accepted": False,
            "performed": False,
            "auto_execute": False,
            "decision_required_from": "Mike Zachary",
        }
