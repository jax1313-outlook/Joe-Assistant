"""The research record: question, scope, sources, findings, recommendation.

Assembles everything into one reportable object and renders it. Nothing here
fetches anything - sources are supplied.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .analysis import CONFIDENCE_MEANING, Confidence, Finding, analyze, topics_in
from .authority import AUTHORITY_STATEMENT, Recommendation
from .sources import Source, SourceError, SourceKind

ENV_ROOT = "ASSISTANT_RESEARCH_DATA"


class RecordError(RuntimeError):
    pass


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_data_root() -> Path:
    # ...\5\Source\assistant_research\record.py -> ...\5\Data
    return Path(__file__).resolve().parent.parent.parent / "Data"


def resolve_data_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).resolve()
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    return default_data_root()


@dataclass
class ResearchRecord:
    """One piece of research, start to finish."""

    question: str
    scope: str = ""
    sources: list[Source] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    recommendation: Recommendation | None = None
    prepared_at: str = field(default_factory=_stamp)

    # ---- assembly -----------------------------------------------------

    @classmethod
    def build(
        cls,
        question: str,
        sources: list[Source],
        scope: str = "",
        topics: list[str] | None = None,
        recommendation: Recommendation | None = None,
    ) -> "ResearchRecord":
        cleaned = (question or "").strip()
        if not cleaned:
            raise RecordError("a research record needs a question")
        return cls(
            question=cleaned,
            scope=scope,
            sources=list(sources),
            findings=analyze(sources, topics),
            recommendation=recommendation,
        )

    # ---- reading ------------------------------------------------------

    @property
    def topics(self) -> list[str]:
        return [finding.topic for finding in self.findings]

    def findings_by_confidence(self, confidence: str) -> list[Finding]:
        return [f for f in self.findings if f.confidence == confidence]

    @property
    def contested(self) -> list[Finding]:
        return self.findings_by_confidence(Confidence.CONTESTED)

    @property
    def settled(self) -> list[Finding]:
        return [f for f in self.findings if f.is_settled]

    @property
    def uncertainties(self) -> list[dict]:
        """Every uncertainty, one per finding. Never empty when findings exist."""
        return [
            {"topic": f.topic, "confidence": f.confidence, "uncertainty": f.uncertainty}
            for f in self.findings
        ]

    def citations(self) -> list[str]:
        seen: list[str] = []
        for source in self.sources:
            citation = source.citation()
            if citation not in seen:
                seen.append(citation)
        return seen

    @property
    def rests_on_approved_company_material(self) -> bool:
        return any(source.is_approved_company_truth for source in self.sources)

    def source_kind_counts(self) -> dict:
        counts = {kind: 0 for kind in SourceKind.ALL}
        for source in self.sources:
            counts[source.kind] += 1
        return counts

    # ---- reporting ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "scope": self.scope,
            "prepared_at": self.prepared_at,
            "authority": AUTHORITY_STATEMENT,
            "source_count": len(self.sources),
            "source_kind_counts": self.source_kind_counts(),
            "rests_on_approved_company_material": self.rests_on_approved_company_material,
            "sources": [s.to_dict() for s in self.sources],
            "findings": [f.to_dict() for f in self.findings],
            "uncertainties": self.uncertainties,
            "citations": self.citations(),
            "recommendation": (
                self.recommendation.to_dict() if self.recommendation else None
            ),
            "is_approved_doctrine": False,
            "is_a_decision": False,
            "decision_required_from": "Mike Zachary",
        }

    def render(self) -> str:
        """A readable report. States what is known, what is not, and who decides."""
        line = "-" * 72
        out = [
            line,
            "RESEARCH RECORD",
            line,
            "Question:    " + self.question,
            "Scope:       " + (self.scope or "(not stated)"),
            "Prepared:    " + self.prepared_at,
            "Sources:     " + str(len(self.sources)),
            "",
            AUTHORITY_STATEMENT,
            "",
            line,
            "FINDINGS",
            line,
        ]
        if not self.findings:
            out.append("  No findings. No source spoke to any topic.")
        for finding in self.findings:
            out.append("")
            out.append("  " + finding.topic)
            out.append(
                "    confidence:  "
                + finding.confidence
                + "  ("
                + CONFIDENCE_MEANING[finding.confidence]
                + ")"
            )
            for entry in finding.supporting:
                out.append("    supports:    " + entry["statement"])
                out.append("                 - " + entry["citation"] + "  [" + entry["standing"] + "]")
            for entry in finding.contradicting:
                out.append("    CONTRADICTS: " + entry["statement"])
                out.append("                 - " + entry["citation"] + "  [" + entry["standing"] + "]")
            out.append("    uncertainty: " + finding.uncertainty)
            if finding.rests_only_on_public_or_personal:
                out.append(
                    "    NOTE:        no approved company material supports this."
                )

        out += ["", line, "UNCERTAINTIES", line]
        for item in self.uncertainties:
            out.append("  " + item["topic"] + "  [" + item["confidence"] + "]")
            out.append("    " + item["uncertainty"])
        if not self.uncertainties:
            out.append("  (none recorded)")

        out += ["", line, "RECOMMENDATION", line]
        if self.recommendation is None:
            out.append("  None offered.")
        else:
            out.append("  " + self.recommendation.statement)
            if self.recommendation.rationale:
                out.append("  Because: " + self.recommendation.rationale)
            for question in self.recommendation.open_questions:
                out.append("  Open question: " + question)
            out.append("")
            out.append("  This is a recommendation only.")
            out.append("  approved=False  decided=False  acted_on=False  doctrine_changed=False")
            out.append(
                "  Decision required from: " + self.recommendation.decision_required_from
            )

        out += ["", line, "SOURCES", line]
        for source in self.sources:
            out.append("  " + source.source_id + "  " + source.citation())
            out.append("      " + source.standing)
        if not self.sources:
            out.append("  (none supplied)")
        out.append("")
        return "\n".join(out)


# ---- loading supplied research input -----------------------------------


def load_sources(path: str | Path) -> list[Source]:
    """Read a supplied JSON list of sources. Reading only - nothing is fetched."""
    target = Path(path)
    if not target.exists():
        raise RecordError("source file not found: " + str(target))
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RecordError("malformed JSON in " + target.name + ": " + str(error)) from None
    if not isinstance(payload, list):
        raise RecordError(target.name + " must contain a JSON list of sources")
    try:
        return [Source.from_dict(entry) for entry in payload]
    except SourceError as error:
        raise RecordError("bad source in " + target.name + ": " + str(error)) from None


def load_brief(path: str | Path) -> dict:
    """Read a supplied research brief: question, scope, sources, recommendation."""
    target = Path(path)
    if not target.exists():
        raise RecordError("brief not found: " + str(target))
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RecordError("malformed JSON in " + target.name + ": " + str(error)) from None
    if not isinstance(payload, dict):
        raise RecordError(target.name + " must contain a JSON object")
    return payload


def record_from_brief(brief: dict) -> ResearchRecord:
    """Build a record from a supplied brief."""
    try:
        sources = [Source.from_dict(entry) for entry in brief.get("sources", [])]
    except SourceError as error:
        raise RecordError("bad source in brief: " + str(error)) from None

    recommendation = None
    raw = brief.get("recommendation")
    if raw:
        recommendation = Recommendation(
            statement=str(raw.get("statement", "")),
            rationale=str(raw.get("rationale", "")),
            rests_on=[str(r) for r in raw.get("rests_on", [])],
            open_questions=[str(q) for q in raw.get("open_questions", [])],
        )

    return ResearchRecord.build(
        question=str(brief.get("question", "")),
        scope=str(brief.get("scope", "")),
        sources=sources,
        topics=brief.get("topics"),
        recommendation=recommendation,
    )
