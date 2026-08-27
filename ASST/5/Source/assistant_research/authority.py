"""The authority boundary.

Research may recommend. Research may not approve, decide, or alter doctrine.

This module makes that boundary mechanical. A recommendation carries flags that
cannot be set true, and its wording is checked against a list of decision and
approval phrases. Language that claims a decision is refused, not softened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Phrasing that claims a decision, an approval, or a doctrine change has
# happened. A recommendation containing any of these is refused.
FORBIDDEN_PHRASES = (
    "i approve", "we approve", "approved by", "is approved", "hereby approve",
    "i have decided", "we have decided", "the decision is", "decision made",
    "i authorize", "we authorize", "is authorized", "hereby authorize",
    "i accept the load", "load accepted", "i have accepted",
    "i have booked", "booked the load", "i dispatched", "has been dispatched",
    "payment sent", "funds committed", "i have paid",
    "this is now policy", "this becomes doctrine", "doctrine is updated",
    "policy is changed", "i have signed", "signed on behalf",
    "email sent", "i have sent", "i replied",
)

# Wording a recommendation is expected to use. Absence is reported as a
# weakness, not refused - phrasing is not always the author's choice.
RECOMMENDING_PHRASES = (
    "recommend", "suggest", "consider", "option", "would", "could",
    "worth", "advise", "propose", "appears", "indicates", "may",
)


class AuthorityError(ValueError):
    """Raised when text claims authority this component does not have."""


@dataclass
class Recommendation:
    """A recommendation. Never a decision.

    The four flags below are set at construction and there is no code path in
    this component that can change them.
    """

    statement: str
    rationale: str = ""
    rests_on: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    decision_required_from: str = "Mike Zachary"

    # Fixed. Not settable.
    is_recommendation_only: bool = True
    approved: bool = False
    decided: bool = False
    acted_on: bool = False
    doctrine_changed: bool = False

    def __post_init__(self) -> None:
        cleaned = (self.statement or "").strip()
        if not cleaned:
            raise AuthorityError("a recommendation needs a statement")
        assert_no_authority_claim(cleaned)
        assert_no_authority_claim(self.rationale or "")
        object.__setattr__(self, "statement", cleaned)

    @property
    def uses_recommending_language(self) -> bool:
        text = (self.statement + " " + self.rationale).lower()
        return any(word in text for word in RECOMMENDING_PHRASES)

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "rationale": self.rationale,
            "rests_on": list(self.rests_on),
            "open_questions": list(self.open_questions),
            "decision_required_from": self.decision_required_from,
            "is_recommendation_only": True,
            "approved": False,
            "decided": False,
            "acted_on": False,
            "doctrine_changed": False,
            "uses_recommending_language": self.uses_recommending_language,
        }


def find_authority_claims(text: str) -> list[str]:
    """Every forbidden phrase present in the text."""
    lowered = " ".join((text or "").lower().split())
    return [phrase for phrase in FORBIDDEN_PHRASES if phrase in lowered]


def assert_no_authority_claim(text: str) -> None:
    """Refuse text that claims a decision, approval, or doctrine change."""
    found = find_authority_claims(text)
    if found:
        raise AuthorityError(
            "research may recommend but may not approve, decide, or alter "
            "doctrine; refused phrasing: " + ", ".join(found)
        )


AUTHORITY_STATEMENT = (
    "Research may recommend. Research may not approve, may not decide, and may "
    "not alter doctrine. Mike Zachary remains final authority."
)
