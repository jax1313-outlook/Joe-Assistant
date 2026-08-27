"""Deterministic command recognition.

No language model is involved. Ordinary driver language is matched by
explicit, reviewable patterns against the phrases named in the governing
configuration. Capitalization and trailing punctuation do not matter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class CommandIntent:
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    PRINT = "PRINT"
    DELETE = "DELETE"
    NONE = "NONE"

    ALL = (LEVEL_1, LEVEL_2, LEVEL_3, PRINT, DELETE, NONE)


# Ordered highest precedence first. Rationale for the order is recorded in
# Constitution/SANDBOX_ENGINE_BOUNDARIES_v1.md.
#
# LEVEL_1 leads because its decline phrases contain the words other
# intents match on ("no need to save this" contains "save this").
_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        CommandIntent.LEVEL_1,
        (
            r"\blevel\s*(?:1|one)\b",
            r"\bjust answer (?:it|this)\b",
            r"\bjust tell me what matters\b",
            r"\bno need to (?:save|keep) (?:this|it)\b",
            r"\b(?:do ?n[o']?t|do not) (?:save|keep) (?:this|it)\b",
            r"\blet (?:it|this) expire\b",
        ),
    ),
    (
        CommandIntent.DELETE,
        (
            r"\bdelete (?:this|it)\b",
            r"\bremove (?:this|it)\b",
            r"\bforget (?:this|it)\b",
            r"\bdiscard (?:this|it)\b",
            r"\bthrow (?:this|it) (?:out|away)\b",
        ),
    ),
    (
        CommandIntent.LEVEL_3,
        (
            r"\blevel\s*(?:3|three)\b",
            r"\bbuild (?:me )?(?:a|the) report\b",
            r"\bformal (?:presentation|report|write[\s\-]?up|document)\b",
            r"\bwrite (?:this|it) up\b",
            r"\bresearch (?:this|it) (?:completely|fully|in full)\b",
        ),
    ),
    (
        CommandIntent.LEVEL_2,
        (
            r"\blevel\s*(?:2|two)\b",
            r"\bsave (?:this|it)\b",
            r"\bkeep (?:this|it)\b",
            r"\bput (?:this|it) under\b",
            r"\battach (?:this|it) to\b",
            r"\bparked review\b",
        ),
    ),
    (
        CommandIntent.PRINT,
        (
            r"\bprint (?:this|it)\b",
            r"\bmake (?:this|it) printable\b",
            r"\bprintable\b",
            r"\bso (?:i|I) can print\b",
            r"\bprint (?:this |it )?later\b",
        ),
    ),
)

_PRINT_PATTERNS = dict(_INTENT_PATTERNS)[CommandIntent.PRINT]

# Words that are never an organization name in "<org> load 123".
_ORG_STOPWORDS = {
    "under", "the", "a", "an", "this", "that", "to", "for", "on", "at",
    "in", "and", "with", "my", "our", "of", "into", "onto", "attach",
    "put", "save", "keep", "level", "print", "delete", "remove",
}

_DESTINATION_RE = re.compile(
    r"\bunder\s+(?P<dest>.+?)(?=\s+with\b|\s+and\b|[.,;:!?]|$)",
    re.IGNORECASE,
)
_LOAD_RE = re.compile(r"\bload\s*#?\s*(?P<load>[A-Za-z0-9][A-Za-z0-9\-]*)\b", re.IGNORECASE)
_ORG_LOAD_RE = re.compile(
    r"\b(?P<org>[A-Za-z][A-Za-z0-9&.\-]*)\s+load\s*#?\s*[A-Za-z0-9][A-Za-z0-9\-]*\b",
    re.IGNORECASE,
)
# A connector word is never part of a party or mission name, so
# "broker XPO for customer Acme" yields "XPO", not "XPO for".
_CONNECTOR = (
    r"(?!for\b|and\b|with\b|under\b|to\b|on\b|at\b|in\b|is\b|the\b|a\b|an\b"
    r"|my\b|our\b|of\b|load\b|mission\b|customer\b|broker\b)"
)
_NAME = r"[A-Za-z0-9][\w&.\-]*"


def _party_re(keyword: str, group: str) -> re.Pattern:
    return re.compile(
        r"\b" + keyword + r"\s+(?P<" + group + r">"
        + _CONNECTOR + _NAME
        + r"(?:\s+" + _CONNECTOR + _NAME + r")?)",
        re.IGNORECASE,
    )


_MISSION_NAMED_RE = _party_re("mission", "mission")
_MISSION_BARE_RE = re.compile(r"\b(?:the|this|that|my)\s+mission\b", re.IGNORECASE)
_CUSTOMER_RE = _party_re("customer", "customer")
_BROKER_RE = _party_re("broker", "broker")

MISSION_UNSPECIFIED = "(unspecified)"


@dataclass
class RecognizedCommand:
    """Result of parsing one line of driver language."""

    intent: str
    raw_text: str
    matched_phrase: str | None = None
    print_requested: bool = False
    references: dict = field(default_factory=dict)

    @property
    def recognized(self) -> bool:
        return self.intent != CommandIntent.NONE

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "raw_text": self.raw_text,
            "matched_phrase": self.matched_phrase,
            "print_requested": self.print_requested,
            "references": dict(self.references),
        }


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, drop surrounding punctuation."""
    lowered = (text or "").lower().replace("\u2019", "'")
    collapsed = re.sub(r"\s+", " ", lowered).strip()
    return collapsed.strip(" .,;:!?\"'")


def _clean_reference(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().strip("\"'").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(".,;:!?")
    return cleaned or None


def extract_references(text: str) -> dict:
    """Pull load / mission / customer / broker / destination from raw text.

    Runs against the original string so the driver's own capitalization is
    preserved in the stored record.
    """
    refs: dict = {}
    source = text or ""

    destination_match = _DESTINATION_RE.search(source)
    if destination_match:
        dest = _clean_reference(destination_match.group("dest"))
        if dest:
            refs["destination"] = dest

    load_match = _LOAD_RE.search(source)
    if load_match:
        refs["related_load"] = "Load " + _clean_reference(load_match.group("load"))
        org_match = _ORG_LOAD_RE.search(source)
        if org_match:
            org = _clean_reference(org_match.group("org"))
            if org and org.lower() not in _ORG_STOPWORDS:
                refs["load_organization"] = org

    customer_match = _CUSTOMER_RE.search(source)
    if customer_match:
        refs["related_customer"] = _clean_reference(customer_match.group("customer"))

    broker_match = _BROKER_RE.search(source)
    if broker_match:
        refs["related_broker"] = _clean_reference(broker_match.group("broker"))

    mission_named = _MISSION_NAMED_RE.search(source)
    if mission_named:
        refs["related_mission"] = _clean_reference(mission_named.group("mission"))
    elif _MISSION_BARE_RE.search(source):
        refs["related_mission"] = MISSION_UNSPECIFIED

    if "destination" not in refs:
        if "related_load" in refs:
            refs["destination"] = refs["related_load"]
        elif "related_mission" in refs and refs["related_mission"] != MISSION_UNSPECIFIED:
            refs["destination"] = "Mission " + refs["related_mission"]

    return refs


def recognize(text: str) -> RecognizedCommand:
    """Classify one line of driver language into exactly one intent."""
    normalized = normalize(text)
    raw = (text or "").strip()

    print_requested = any(
        re.search(pattern, normalized) for pattern in _PRINT_PATTERNS
    )

    for intent, patterns in _INTENT_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return RecognizedCommand(
                    intent=intent,
                    raw_text=raw,
                    matched_phrase=match.group(0),
                    print_requested=print_requested,
                    references=extract_references(raw),
                )

    return RecognizedCommand(
        intent=CommandIntent.NONE,
        raw_text=raw,
        matched_phrase=None,
        print_requested=print_requested,
        references=extract_references(raw),
    )
