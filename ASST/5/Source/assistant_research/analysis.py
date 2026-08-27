"""Analysis: turn claims into findings, with confidence and uncertainty stated.

The rules here are arithmetic and visible. A reviewer can read them and predict
every result. Nothing is inferred beyond what the sources say.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sources import Source, SourceKind


class Confidence:
    """How well supported a finding is. A count, not an opinion."""

    CONFIRMED = "CONFIRMED"      # 2+ sources support, none contradict
    SUPPORTED = "SUPPORTED"      # 1 source supports, none contradict
    CONTESTED = "CONTESTED"      # sources disagree
    CONTRADICTED = "CONTRADICTED"  # only contradicting sources
    UNSUPPORTED = "UNSUPPORTED"  # no source speaks to it

    ALL = (CONFIRMED, SUPPORTED, CONTESTED, CONTRADICTED, UNSUPPORTED)


CONFIDENCE_MEANING = {
    Confidence.CONFIRMED: "two or more sources agree and none contradict",
    Confidence.SUPPORTED: "one source supports this and none contradict",
    Confidence.CONTESTED: "sources disagree; both sides are recorded below",
    Confidence.CONTRADICTED: "every source that speaks to this contradicts it",
    Confidence.UNSUPPORTED: "no supplied source speaks to this",
}


@dataclass
class Finding:
    """One topic, everything the sources said about it, and how solid it is."""

    topic: str
    confidence: str
    supporting: list[dict] = field(default_factory=list)
    contradicting: list[dict] = field(default_factory=list)
    uncertainty: str = ""
    rests_on_approved_company_material: bool = False
    rests_only_on_public_or_personal: bool = False

    @property
    def support_count(self) -> int:
        return len(self.supporting)

    @property
    def contradiction_count(self) -> int:
        return len(self.contradicting)

    @property
    def is_settled(self) -> bool:
        return self.confidence in (Confidence.CONFIRMED, Confidence.SUPPORTED)

    def citations(self) -> list[str]:
        seen: list[str] = []
        for entry in self.supporting + self.contradicting:
            if entry["citation"] not in seen:
                seen.append(entry["citation"])
        return seen

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "confidence": self.confidence,
            "confidence_meaning": CONFIDENCE_MEANING[self.confidence],
            "support_count": self.support_count,
            "contradiction_count": self.contradiction_count,
            "supporting": list(self.supporting),
            "contradicting": list(self.contradicting),
            "uncertainty": self.uncertainty,
            "citations": self.citations(),
            "rests_on_approved_company_material": self.rests_on_approved_company_material,
            "rests_only_on_public_or_personal": self.rests_only_on_public_or_personal,
            "is_approved_doctrine": False,
            "is_a_decision": False,
        }


def _entry(source: Source, claim) -> dict:
    return {
        "source_id": source.source_id,
        "kind": source.kind,
        "standing": source.standing,
        "statement": claim.statement,
        "citation": source.citation(),
    }


def _uncertainty_for(
    confidence: str,
    supporting: list[dict],
    contradicting: list[dict],
) -> str:
    """State plainly what is not known. Never leave this blank."""
    if confidence == Confidence.CONTESTED:
        return (
            "Sources disagree. "
            + str(len(supporting))
            + " support, "
            + str(len(contradicting))
            + " contradict. This is not settled and should not be treated as settled."
        )
    if confidence == Confidence.CONTRADICTED:
        return (
            "Every source that speaks to this contradicts it. "
            "Nothing supplied supports it."
        )
    if confidence == Confidence.UNSUPPORTED:
        return "No supplied source speaks to this. Nothing is known either way."
    if confidence == Confidence.SUPPORTED:
        return (
            "Rests on a single source. A second source has not been supplied, "
            "so agreement has not been established."
        )
    kinds = {entry["kind"] for entry in supporting}
    if kinds and kinds <= {SourceKind.PUBLIC, SourceKind.PERSONAL, SourceKind.UNKNOWN}:
        return (
            "Sources agree, but none is approved company material. "
            "Research is not doctrine."
        )
    return "Sources agree and none contradict. No unresolved conflict recorded."


def analyze_topic(topic: str, sources: list[Source]) -> Finding:
    """Build one finding for one topic.

    The rule, in full:

        2+ supporting, 0 contradicting  ->  CONFIRMED
        1  supporting, 0 contradicting  ->  SUPPORTED
        1+ supporting, 1+ contradicting ->  CONTESTED
        0  supporting, 1+ contradicting ->  CONTRADICTED
        0  supporting, 0 contradicting  ->  UNSUPPORTED
    """
    supporting: list[dict] = []
    contradicting: list[dict] = []

    for source in sources:
        for claim in source.claims:
            if claim.topic != topic:
                continue
            if claim.supports:
                supporting.append(_entry(source, claim))
            else:
                contradicting.append(_entry(source, claim))

    if supporting and contradicting:
        confidence = Confidence.CONTESTED
    elif len(supporting) >= 2:
        confidence = Confidence.CONFIRMED
    elif len(supporting) == 1:
        confidence = Confidence.SUPPORTED
    elif contradicting:
        confidence = Confidence.CONTRADICTED
    else:
        confidence = Confidence.UNSUPPORTED

    involved = supporting + contradicting
    kinds = {entry["kind"] for entry in involved}

    return Finding(
        topic=topic,
        confidence=confidence,
        supporting=supporting,
        contradicting=contradicting,
        uncertainty=_uncertainty_for(confidence, supporting, contradicting),
        rests_on_approved_company_material=SourceKind.COMPANY in kinds,
        rests_only_on_public_or_personal=bool(kinds)
        and kinds <= {SourceKind.PUBLIC, SourceKind.PERSONAL, SourceKind.UNKNOWN},
    )


def topics_in(sources: list[Source]) -> list[str]:
    """Every topic any source speaks to, in first-seen order."""
    seen: list[str] = []
    for source in sources:
        for topic in source.topics():
            if topic not in seen:
                seen.append(topic)
    return seen


def analyze(sources: list[Source], topics: list[str] | None = None) -> list[Finding]:
    """Build a finding for every topic. Ordering is stable."""
    wanted = topics if topics is not None else topics_in(sources)
    return [analyze_topic(topic, sources) for topic in wanted]
