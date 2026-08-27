"""Sources and the claims they make.

A source is something someone supplied. This component does not fetch, browse,
or discover sources - it has no network access. Sources come in, and what comes
in is reported with its origin attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


class SourceError(ValueError):
    pass


class SourceKind:
    """Where a source came from. Affects reporting, never truth."""

    COMPANY = "company"        # approved company material
    OPERATIONAL = "operational"  # load, mission, or system records
    PUBLIC = "public"          # public web or published material
    PERSONAL = "personal"      # someone said so
    UNKNOWN = "unknown"

    ALL = (COMPANY, OPERATIONAL, PUBLIC, PERSONAL, UNKNOWN)


# Company material is approved company fact. Everything else is evidence.
# This ordering affects how a finding is *reported*, never whether it is true.
KIND_STANDING = {
    SourceKind.COMPANY: "approved company material",
    SourceKind.OPERATIONAL: "operational record",
    SourceKind.PUBLIC: "public source, not approved company truth",
    SourceKind.PERSONAL: "stated by a person, unverified",
    SourceKind.UNKNOWN: "origin not recorded",
}


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_moment(text: str | None) -> datetime | None:
    if not text:
        return None
    cleaned = str(text).strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as error:
        raise SourceError("unreadable timestamp: " + str(text)) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class Claim:
    """One statement a source makes about one topic.

    `supports=False` means the source contradicts the topic statement rather
    than supporting it. Both are recorded; neither is discarded.
    """

    topic: str
    statement: str
    supports: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Claim":
        try:
            topic = str(data["topic"]).strip()
            statement = str(data["statement"]).strip()
        except KeyError as error:
            raise SourceError("claim missing field: " + str(error)) from None
        if not topic or not statement:
            raise SourceError("a claim needs both a topic and a statement")
        return cls(topic=topic, statement=statement, supports=bool(data.get("supports", True)))

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "statement": self.statement,
            "supports": self.supports,
        }


@dataclass(frozen=True)
class Source:
    """One source, with its origin and the claims it makes."""

    source_id: str
    title: str
    kind: str = SourceKind.UNKNOWN
    origin: str = ""
    retrieved_at: str | None = None
    claims: tuple[Claim, ...] = ()

    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        try:
            source_id = str(data["source_id"]).strip()
        except KeyError as error:
            raise SourceError("source missing field: " + str(error)) from None
        if not source_id:
            raise SourceError("a source needs an id")
        kind = str(data.get("kind", SourceKind.UNKNOWN)).lower()
        if kind not in SourceKind.ALL:
            raise SourceError("unknown source kind: " + kind)
        retrieved = data.get("retrieved_at")
        if retrieved is not None:
            retrieved = _stamp(parse_moment(retrieved))
        return cls(
            source_id=source_id,
            title=str(data.get("title", source_id)),
            kind=kind,
            origin=str(data.get("origin", "")),
            retrieved_at=retrieved,
            claims=tuple(Claim.from_dict(c) for c in data.get("claims", ())),
        )

    @property
    def standing(self) -> str:
        return KIND_STANDING[self.kind]

    @property
    def is_approved_company_truth(self) -> bool:
        """Only company material is approved company truth.

        Research is never doctrine, no matter how many public sources agree.
        """
        return self.kind == SourceKind.COMPANY

    def topics(self) -> list[str]:
        seen: list[str] = []
        for claim in self.claims:
            if claim.topic not in seen:
                seen.append(claim.topic)
        return seen

    def citation(self) -> str:
        parts = [self.title]
        if self.origin:
            parts.append(self.origin)
        if self.retrieved_at:
            parts.append("retrieved " + self.retrieved_at[:10])
        return " (".join([parts[0], ", ".join(parts[1:]) + ")"]) if len(parts) > 1 else parts[0]

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "kind": self.kind,
            "standing": self.standing,
            "origin": self.origin,
            "retrieved_at": self.retrieved_at,
            "claims": [c.to_dict() for c in self.claims],
            "citation": self.citation(),
            "is_approved_company_truth": self.is_approved_company_truth,
        }
