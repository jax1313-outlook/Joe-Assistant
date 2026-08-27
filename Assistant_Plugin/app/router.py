"""Router: ordinary language to a bounded capability.

Deterministic. No model, no guessing. Every routing decision can be predicted
by reading the patterns below, and every route names the capability it chose so
the decision is visible rather than mysterious.

Retention commands are recognized by the packaged retention-language module,
so retention doctrine has exactly one implementation.

Order matters. Rules that would be stolen by a more general rule are asked
first, and each such case is commented with the sentence that forced it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from contracts import Capability

# Ordered. First match wins.
_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        # An explicit retrieval verb means Mike wants a document, even when the
        # subject also contains a calendar word. "Look up the appointment
        # policy" is a Library request; "my appointments tomorrow" is not.
        Capability.LIBRARY,
        (
            r"\b(?:find|search for|look up|pull up)\b",
            r"\bwhere is\b",
            r"\blibrary\b",
        ),
    ),
    (
        Capability.RESEARCH,
        (
            r"\bresearch\b",
            r"\blook into\b",
            r"\bdig into\b",
            r"\bwhat does .* mean for (?:the|my) (?:run|load|route|trip)\b",
            r"\bcompare\b.*\boptions\b",
        ),
    ),
    (
        # Asked before OPERATIONS, because "draft an email to the broker"
        # contains the word "email" and would otherwise be treated as a request
        # to read the inbox. DRAFT needs an explicit draft/write/compose verb,
        # so "show me unread mail" is unaffected.
        Capability.DRAFT,
        (
            r"\bdrafts?\b",
            r"\bwrite (?:me )?(?:an?|the) "
            r"(?:email|e-?mail|note|message|notice|update|reply|letter)\b",
            r"\bcompose\b",
            r"\bput together (?:an?|the) (?:email|note|message|notice)\b",
        ),
    ),
    (
        Capability.OPERATIONS,
        (
            r"\b(?:my |the )?calendar\b",
            r"\b(?:my|the) schedule\b",
            r"\bmy (?:next )?appointments?\b",
            r"\bnext (?:scheduled )?(?:item|appointment|stop|meeting|event)\b",
            r"\bwhat(?:'s| is) next\b",
            r"\bcoming up (?:next|today|tomorrow)\b",
            r"\bappointments?\s+(?:today|tomorrow|this week|next week)\b",
            r"\bwhat(?:'s| is| does)?.{0,20}\b(?:tomorrow|today|this week|next week)\b",
            r"\bmeetings?\b",
            r"\b(?:e-?mail|inbox|mail)\b",
            r"\bunread\b",
            r"\bwho is\b",
            r"\bcontact (?:for|details|info)\b",
            r"\bphone number\b",
        ),
    ),
    (
        # Asked before the topical Library rule below, because "what is the
        # procedure for X" contains the word "procedure" and would otherwise
        # come back as a document list instead of the procedure itself.
        Capability.PROCEDURE,
        (
            r"\bhow do i\b",
            r"\bwhat(?:'s| is) the (?:process|procedure)\b",
            r"\boperating procedure\b",
            r"\bwhat should (?:the driver|i) do when\b",
            r"\bsteps? (?:to|for)\b",
        ),
    ),
    (
        Capability.DRAFT,
        (
            r"\bdrafts?\b",
            r"\bwrite (?:me )?(?:an?|the) "
            r"(?:email|e-?mail|note|message|notice|update|reply|letter)\b",
            r"\bcompose\b",
            r"\bput together (?:an?|the) (?:email|note|message|notice)\b",
        ),
    ),
    (
        Capability.SUMMARIZE,
        (
            r"\bsummar(?:ise|ize|y|ies)\b",
            r"\bshort version\b",
            r"\bwhat matters here\b",
            r"\bwhat action requires my attention\b",
            r"\bgive me the gist\b",
            r"\bboil (?:this|it) down\b",
        ),
    ),
    (
        Capability.EXPLAIN,
        (
            r"\bexplain\b",
            r"\bin plain (?:language|english|terms)\b",
            r"\bwhat does .* mean\b",
            r"\bwalk me through\b",
        ),
    ),
    (
        # Topical Library terms. "procedure" is deliberately NOT here - it is
        # owned by the PROCEDURE rule above.
        Capability.LIBRARY,
        (
            r"\bfind\b",
            r"\bsearch\b",
            r"\blook up\b",
            r"\bwhere is\b",
            r"\b(?:the )?(?:packet|document|doc|policy|template|doctrine)\b",
            r"\blibrary\b",
        ),
    ),
    (
        Capability.HELP,
        (
            r"\bwhat can you do\b",
            r"\bhelp\b",
            r"\bcommands?\b",
            r"\bhow do you work\b",
        ),
    ),
)

# Phrases that ask for a short spoken answer.
_DRIVER_MODE = (
    r"\bwhile (?:i'?m )?driving\b",
    r"\bshort (?:answer|version)\b",
    r"\bquick(?:ly)?\b",
    r"\bjust tell me\b",
    r"\bwhat matters\b",
    r"\b70 mph\b",
    r"\bseventy\b",
)


# Asking about a command is not issuing it. "How do I delete this?" must
# explain deletion, not delete it. These patterns suppress retention
# recognition so the question reaches PROCEDURE or EXPLAIN instead.
_ASKING_ABOUT = (
    r"\bhow do i\b",
    r"\bhow does\b",
    r"\bhow would i\b",
    r"\bwhat(?:'s| is) the (?:process|procedure)\b",
    r"\bwhat does .* (?:mean|do)\b",
    r"\bwhen should i\b",
    r"\bwhat happens (?:if|when)\b",
    r"\bexplain\b",
    r"\bwalk me through\b",
    r"\bwhat(?:'s| is) the difference\b",
)


def asking_about_a_command(text: str) -> bool:
    """True when Mike is asking how something works, not asking for it."""
    normalized = _normalize(text)
    return any(re.search(pattern, normalized) for pattern in _ASKING_ABOUT)


@dataclass
class Route:
    capability: str
    matched: str = ""
    driver_mode: bool = False
    subject: str = ""
    retention_intent: str = "NONE"
    references: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "capability": self.capability,
            "matched": self.matched,
            "driver_mode": self.driver_mode,
            "subject": self.subject,
            "retention_intent": self.retention_intent,
            "references": dict(self.references),
        }


def _normalize(text: str) -> str:
    lowered = (text or "").lower().replace("’", "'")
    return re.sub(r"\s+", " ", lowered).strip()


def wants_driver_mode(text: str) -> bool:
    normalized = _normalize(text)
    return any(re.search(pattern, normalized) for pattern in _DRIVER_MODE)


def extract_subject(text: str) -> str:
    """The thing being asked about, with the command words trimmed off."""
    cleaned = (text or "").strip()
    cleaned = re.sub(
        r"^(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?"
        r"(?:go\s+)?(?:and\s+)?"
        r"(?:how do i|how would i|what(?:'s| is) the process for|"
        r"what(?:'s| is) the procedure for|steps? (?:to|for)|"
        r"research|find|search for|search|look up|look into|dig into|"
        r"explain|summarize|summarise|draft|compose|tell me about|show me|"
        r"get me|pull up|where is)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:for me|please|and tell me what it means.*|in plain language|"
        r"in plain english|while driving|quickly)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" .,;:?!") or (text or "").strip()


def route(text: str) -> Route:
    """Choose one bounded capability for one request.

    Retention language is checked first and always wins: "save this" is a
    retention command even if the sentence also contains "find".
    """
    raw = (text or "").strip()
    normalized = _normalize(raw)
    driver = wants_driver_mode(raw)

    # 1. Retention, via the packaged retention-language recognizer.
    #    Reused verbatim from Sandbox Engine v1 so retention doctrine has one
    #    implementation, already covered by that component's own tests.
    from retention_language import recognize as recognize_retention

    retention = recognize_retention(raw)
    if retention.intent != "NONE" and not asking_about_a_command(raw):
        return Route(
            capability=Capability.RETENTION,
            matched=retention.matched_phrase or "",
            driver_mode=driver,
            subject=extract_subject(raw),
            retention_intent=retention.intent,
            references=dict(retention.references),
        )

    # 2. Everything else, in order.
    for capability, patterns in _ROUTES:
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return Route(
                    capability=capability,
                    matched=match.group(0),
                    driver_mode=driver,
                    subject=extract_subject(raw),
                )

    # 3. Nothing matched. Answer capability decides what it can honestly say.
    return Route(
        capability=Capability.ANSWER,
        matched="",
        driver_mode=driver,
        subject=extract_subject(raw),
    )
