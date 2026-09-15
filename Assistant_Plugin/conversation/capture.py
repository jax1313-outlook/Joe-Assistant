"""Turning something a driver said into a proposal Dispatch may apply.

`Dispatch/CLAUDE.md` section 5.4: **"No direct Dispatch write authority may be
granted to Assistant."** This module is the shape of that rule.

Joe hears a sentence. He does not write a milestone. He produces a *proposal*:
what he thinks was meant, how sure he is, and the exact words a person would say
to confirm it. Dispatch applies the proposal, or does not.

The reason is not governance theatre. A cab at 70 MPH is the worst listening
environment this software will ever run in, and the failure mode of a
speech-to-write path is silent and expensive: the driver says "picked up", the
recogniser hears "pick up", and a load advances a state nobody chose. The
repository has already shipped one of these -- `driver_step_milestone` once
swallowed a refused transition inside `except Exception: pass`, so a driver
tapped "Picked Up" at a dock, nothing was recorded, and the screen said it
worked.

**Below the confidence floor, Joe says nothing rather than guessing.** A wrong
proposal costs a confirmation exchange the driver has to listen to and refuse
while driving, which is worse than not offering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Below this, no proposal is made at all. Chosen to sit above the range where a
#: recogniser is essentially reporting that it heard *something*.
CONFIDENCE_FLOOR = 0.55

#: Above this, the confirmation can be a single word. Below it, Joe repeats the
#: whole thing back, because a driver confirming something he half heard is how
#: a misheard sentence becomes a record.
HIGH_CONFIDENCE = 0.85

#: What a driver actually says, and the milestone it means. Ordered: the first
#: match wins, so the more specific phrases come first ("picked up" before "up").
PHRASES: tuple[tuple[str, str, str], ...] = (
    (r"\b(loaded|picked up|pick ?up done|got the load)\b", "loaded", "loaded"),
    (r"\b(delivered|dropped|unloaded|delivery done)\b", "delivered", "delivered"),
    (r"\b(at the (dock|shipper|pickup))\b", "arrived_pickup", "arrived at pickup"),
    (r"\b(at the (receiver|consignee|delivery))\b", "arrived_delivery", "arrived at delivery"),
    (r"\b(rolling|on my way|en ?route|heading (out|there))\b", "in_transit", "in transit"),
    (r"\b(left the (shipper|dock)|departed)\b", "departed_pickup", "departed pickup"),
)

#: Phrases that are a problem report, not a milestone. They become an exception
#: proposal, and the distinction matters: a delay is not a state change.
#
# Weather needs a problem word beside it. The first version matched a bare
# mention, so "nice weather out here" opened a weather exception -- which is
# worse than missing one: the driver now has to listen to a confirmation
# question and refuse it, at speed, because he made conversation.
TROUBLE = (
    (r"\b(breakdown|broke down|broken down|blew a tire|blown tire)\b", "mechanical"),
    (r"\b(accident|wreck|collision|rear.?ended)\b", "accident"),
    (r"\b(been (waiting|sitting|here)|still waiting|detained|sitting here|"
     r"they.re not ready|no dock)\b", "detention"),
    (r"\b(running (late|behind)|gonna be late|going to be late|i.m late|"
     r"delayed|held up|behind schedule)\b", "delay"),
    (r"\b(shut down|closed|stuck|can.t get through|road.s? closed|whiteout|"
     r"black ice)\b.*\b(snow|ice|storm|fog|weather|wind)\b", "weather"),
    (r"\b(snow|ice|storm|fog|weather|wind)\b.*\b(shut down|closed|stuck|"
     r"can.t get through|slowing me|crawling)\b", "weather"),
)


@dataclass
class Proposal:
    kind: str
    load_id: str
    summary: str
    confirmation_prompt: str
    heard: str
    confidence: float
    fields: dict = field(default_factory=dict)
    #: Always false. Present so that anything consuming a proposal has to look
    #: at it, rather than there being no statement either way.
    applied: bool = False

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "load_id": self.load_id, "summary": self.summary,
            "confirmation_prompt": self.confirmation_prompt, "heard": self.heard,
            "confidence": round(self.confidence, 3), "fields": dict(self.fields),
            "applied": self.applied,
        }


def propose_change(heard: str, load_id: str = "", confidence: float = 0.0) -> Proposal | None:
    """What Joe thinks was meant, or None when he is not sure enough to say.

    None is a real answer. Saying nothing to a sentence that was probably
    misheard is better than making the driver refuse a wrong guess at speed.
    """
    text = (heard or "").strip().lower()
    if not text or confidence < CONFIDENCE_FLOOR:
        return None

    for pattern, event_type, spoken in PHRASES:
        if re.search(pattern, text):
            return Proposal(
                kind="milestone",
                load_id=load_id,
                summary=f"Record milestone '{event_type}'.",
                confirmation_prompt=_prompt(f"Record {spoken}?", heard, confidence),
                heard=heard,
                confidence=confidence,
                fields={"event_type": event_type},
            )

    for pattern, exception_type in TROUBLE:
        if re.search(pattern, text):
            return Proposal(
                kind="exception",
                load_id=load_id,
                summary=f"Open a {exception_type} exception.",
                confirmation_prompt=_prompt(
                    f"Open a {exception_type} exception and tell the office?", heard, confidence
                ),
                heard=heard,
                confidence=confidence,
                # The driver's own words, unedited. A paraphrase of a problem
                # report loses the detail that made it worth reporting.
                fields={"exception_type": exception_type, "description": heard.strip()},
            )

    return None


def _prompt(question: str, heard: str, confidence: float) -> str:
    if confidence >= HIGH_CONFIDENCE:
        return f"{question} Say yes or no."
    # Repeat it back. A driver confirming something he only half heard is how a
    # misheard sentence becomes a record.
    return f'I heard "{heard.strip()}". {question} Say yes or no.'
