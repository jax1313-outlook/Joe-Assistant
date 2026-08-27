"""Driver mode: shaping text for a person who is driving.

Three rules from the doctrine, applied mechanically:

1. Say what changed.
2. Say why it matters.
3. Say whether a decision or action is required.

Plus two more this layer enforces:

4. Never read long citations or full reports aloud. Say where the written
   result is held.
5. Keep it short enough to hear at speed.

**This module does not summarize.** Summarizing is reasoning, and reasoning is
not this workstream. It formats parts it is given, and where it is handed
something too long it defers to the written copy rather than inventing a
shorter version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# A spoken turn longer than this is too long to hear at speed. This is the
# ONE limit. An earlier draft had a separate, higher "too long to read"
# threshold, which left a gap: text between the two passed the defer check and
# then produced a turn that exceeded the spoken limit anyway. One limit, checked
# against the assembled turn, closes it.
MAX_SPOKEN_WORDS = 60

# Kept as a name because the defer path reads better with it, but it is the
# same number by definition, not a second threshold.
TOO_LONG_TO_READ_WORDS = MAX_SPOKEN_WORDS

_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_BRACKETED_CITATION = re.compile(r"\[[^\]]*\]|\([^)]*(?:retrieved|source|ibid|p\.\s*\d+)[^)]*\)", re.IGNORECASE)
_FOOTNOTE = re.compile(r"\[\^?\d+\]|\(\d+\)")
# A file path read aloud is "slash Operations slash RATE underscore FLOOR
# underscore POLICY dot M D". It is never the answer to anything asked at the
# wheel, and it belongs on the screen that gets read parked. Both branches
# require an extension, so ordinary prose like "and/or" is left alone.
_FILE_PATH = re.compile(
    r"(?:[\w.\-]+[/\\])+[\w.\-]*\.[A-Za-z0-9]{1,5}\b"
    r"|\b[\w\-]+\.(?:md|txt|docx?|pdf|xlsx?|csv|json|html?|pptx?|ya?ml)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")


class DriverModeError(ValueError):
    pass


def strip_unspeakable(text: str) -> str:
    """Remove what should never be read aloud: URLs, file paths, citations,
    footnotes."""
    cleaned = _URL.sub("", text or "")
    cleaned = _FILE_PATH.sub("", cleaned)
    cleaned = _BRACKETED_CITATION.sub("", cleaned)
    cleaned = _FOOTNOTE.sub("", cleaned)
    cleaned = cleaned.replace("*", "").replace("#", "").replace("`", "")
    return _WHITESPACE.sub(" ", cleaned).strip(" .,;:")


def word_count(text: str) -> int:
    return len((text or "").split())


def is_too_long_to_read(text: str) -> bool:
    return word_count(text) > TOO_LONG_TO_READ_WORDS


@dataclass
class DriverBrief:
    """A spoken turn built from parts the caller supplied."""

    what_changed: str
    why_it_matters: str = ""
    decision_required: str = ""
    written_result_location: str = ""
    deferred: bool = False
    defer_reason: str = ""
    truncated: bool = False
    removed_unspeakable: bool = False

    def spoken_text(self) -> str:
        parts = [self.what_changed]
        if self.why_it_matters:
            parts.append(self.why_it_matters)
        if self.decision_required:
            parts.append(self.decision_required)
        else:
            parts.append("No decision needed right now.")
        if self.written_result_location:
            parts.append("Full written result is in " + self.written_result_location + ".")
        return " ".join(part.rstrip(".") + "." for part in parts if part)

    @property
    def spoken_word_count(self) -> int:
        return word_count(self.spoken_text())

    def to_dict(self) -> dict:
        return {
            "what_changed": self.what_changed,
            "why_it_matters": self.why_it_matters,
            "decision_required": self.decision_required,
            "written_result_location": self.written_result_location,
            "spoken_text": self.spoken_text(),
            "spoken_word_count": self.spoken_word_count,
            "deferred": self.deferred,
            "defer_reason": self.defer_reason,
            "truncated": self.truncated,
            "removed_unspeakable": self.removed_unspeakable,
            "summarized": False,
            "interpreted": False,
        }


def build_brief(
    what_changed: str,
    why_it_matters: str = "",
    decision_required: str = "",
    written_result_location: str = "",
) -> DriverBrief:
    """Build a spoken turn from supplied parts.

    Parts are cleaned of URLs, citations, and footnote markers. Nothing is
    summarized or reworded beyond that.
    """
    cleaned_change = strip_unspeakable(what_changed)
    if not cleaned_change:
        raise DriverModeError("a driver brief needs something that changed")

    removed = any(
        strip_unspeakable(part) != (part or "").strip()
        for part in (what_changed, why_it_matters, decision_required)
    )

    return DriverBrief(
        what_changed=cleaned_change,
        why_it_matters=strip_unspeakable(why_it_matters),
        decision_required=strip_unspeakable(decision_required),
        written_result_location=(written_result_location or "").strip(),
        removed_unspeakable=removed,
    )


def defer_long_text(text: str, written_result_location: str = "") -> DriverBrief:
    """Refuse to read a long written product aloud, and say where it is.

    This is the honest response to being handed a report: not a summary this
    layer is not entitled to produce, but a pointer to the written copy.
    """
    where = (written_result_location or "").strip()
    return DriverBrief(
        what_changed="There is a written result ready.",
        why_it_matters=(
            "It runs to about " + str(word_count(text)) + " words, too long to read at speed."
        ),
        decision_required="Read it when you are stopped.",
        written_result_location=where,
        deferred=True,
        defer_reason=(
            "longer than " + str(TOO_LONG_TO_READ_WORDS) + " words; not read aloud"
        ),
    )


def prepare_for_speech(
    text: str, written_result_location: str = ""
) -> DriverBrief:
    """Take arbitrary text and produce something safe to speak.

    Short text is cleaned and spoken. Long text is deferred to its written
    copy. It is never summarized - this layer does not have that job.

    The length test is applied to the **assembled** turn, not to the raw text,
    because the scaffolding ("No decision needed right now", "Full written
    result is in ...") adds words. Testing the raw text would let a turn slip
    past the limit once assembled.
    """
    cleaned = strip_unspeakable(text)
    if not cleaned:
        raise DriverModeError("nothing speakable in the supplied text")
    if is_too_long_to_read(cleaned):
        return defer_long_text(cleaned, written_result_location)
    brief = DriverBrief(
        what_changed=cleaned,
        written_result_location=(written_result_location or "").strip(),
        removed_unspeakable=cleaned != (text or "").strip(),
    )
    fits, _ = check_length(brief)
    if not fits:
        return defer_long_text(cleaned, written_result_location)
    return brief


def check_length(brief: DriverBrief) -> tuple[bool, str]:
    """Is this short enough to hear at speed?"""
    count = brief.spoken_word_count
    if count > MAX_SPOKEN_WORDS:
        return False, (
            "spoken turn is "
            + str(count)
            + " words; over the "
            + str(MAX_SPOKEN_WORDS)
            + " word driver-mode limit"
        )
    return True, "within the driver-mode length limit"
