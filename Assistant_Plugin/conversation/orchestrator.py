"""Bounded reasoning: a turn that is allowed to end without an answer.

Joe's reasoning is bounded in four ways, and every bound exists because of a
specific way an unbounded assistant fails a driver.

**Bounded in scope.** A question is first matched against the Mission Record. If
the answer is a fact on file, it is read back and no provider is called at all --
which is faster, free, exact, and cannot hallucinate. The provider is for what
is genuinely open-ended, and even then it sees only
`MissionRecord.context_for_reasoning()`, never the raw record.

**Bounded in turns.** One provider call per driver utterance. No chains, no
self-directed follow-ups. A driver who asks a question and hears nothing for six
seconds has already looked at the screen, which is the thing this is supposed to
prevent.

**Bounded in time.** A deadline, after which the turn ends with what it has.
"Still thinking" is not an answer at 70 MPH.

**Bounded in authority.** Nothing a provider returns becomes a change. It can
be spoken, and a change can only be *proposed* (`conversation/capture.py`).

The fifth property is the one that is usually missing: **it may return nothing,
and nothing is a valid outcome.** `Answer.status` is one of the eight truth
words, and UNCONFIGURED -- "no provider is set up on this machine" -- is a real
answer a driver can act on, where a confident-sounding guess is not.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

#: Questions that are answered from the record, never from a provider. Ordered:
#: first match wins.
#
# No trailing \b on a stem. "when's delivery" against `...deliver\b` does not
# match, because the character after "deliver" is "y" -- a word boundary that is
# not there. The first version of this table had exactly that bug and it failed
# silently: the question fell through to the reasoning provider, which answered
# it correctly, slowly, and for money, from a fact the database already knew.
DIRECT_QUESTIONS: tuple[tuple[str, str], ...] = (
    (r"\bwhere (am i going|are we going|to)\b", "where"),
    (r"\bwhat.s the destination\b", "where"),
    (r"\bwhere.s it going\b", "where"),
    (r"\bwhen.{0,3}s? (the )?deliver", "delivery"),
    (r"\bwhen is (the )?deliver", "delivery"),
    (r"\bdelivery time\b", "delivery"),
    (r"\bwhat time.{0,12}deliver", "delivery"),
    (r"\bwhen.{0,3}s? (the )?pick ?up", "pickup"),
    (r"\bwhen is (the )?pick ?up", "pickup"),
    (r"\bpick ?up time\b", "pickup"),
    (r"\bwhat time.{0,12}pick", "pickup"),
    (r"\bwho.s the customer\b", "customer"),
    (r"\bwhat customer\b", "customer"),
    (r"\bwho.s it for\b", "customer"),
    (r"\bwhat.s (the )?status\b", "status"),
    (r"\bwhere are we\b", "status"),
    (r"\bhow.s this load\b", "status"),
    (r"\bwhat.s next\b", "next"),
    (r"\bwhat.s after\b", "next"),
    (r"\bnext stop\b", "next"),
    (r"\btell me everything\b", "everything"),
    (r"\bread (me )?the (whole )?load\b", "everything"),
    (r"\bfull details\b", "everything"),
)

#: The whole turn, including the read-back. Beyond this the driver has looked at
#: the screen and the point is lost.
DEFAULT_DEADLINE_SECONDS = 6.0


@dataclass
class TurnResult:
    spoken: str
    status: str
    source: str
    #: "record" | "provider" | "refusal" | "timeout"
    aspect: str = ""
    unknown: tuple = ()
    provider_called: bool = False
    elapsed_seconds: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "spoken": self.spoken, "status": self.status, "source": self.source,
            "aspect": self.aspect, "unknown": list(self.unknown),
            "provider_called": self.provider_called,
            "elapsed_seconds": round(self.elapsed_seconds, 3), "detail": self.detail,
        }


def classify(question: str) -> str:
    """Which fact answers this, or "" when it is genuinely open."""
    text = (question or "").strip().lower()
    for pattern, aspect in DIRECT_QUESTIONS:
        if re.search(pattern, text):
            return aspect
    return ""


@dataclass
class ReasoningOrchestrator:
    retrieval: object
    reasoner: object | None = None
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS
    clock: object = field(default=time.monotonic)

    def status(self) -> str:
        if not getattr(self.retrieval, "available", False):
            return "UNCONFIGURED"
        return "LIVE" if self.reasoner is not None else "CONFIGURED"

    def take_turn(self, question: str, load_id: str = "") -> TurnResult:
        started = self.clock()

        if not (question or "").strip():
            return TurnResult(
                "I didn't catch that.", "UNVERIFIED", "refusal",
                elapsed_seconds=self.clock() - started,
            )

        record = self.retrieval.retrieve(load_id) if load_id else None

        aspect = classify(question)
        if aspect and record is not None:
            from conversation.readback import read_back_load

            spoken = read_back_load(record.load, aspect=aspect)
            return TurnResult(
                spoken.text, "LIVE", "record", aspect=aspect, unknown=spoken.unknown,
                provider_called=False, elapsed_seconds=self.clock() - started,
                detail="Answered from the record. No provider was called.",
            )

        if aspect and record is None:
            return TurnResult(
                "I don't have a load on file to answer that from.", "ABSENT", "refusal",
                aspect=aspect, elapsed_seconds=self.clock() - started,
            )

        if self.reasoner is None:
            return TurnResult(
                "I can tell you what's on the load, but I'm not set up to answer that one.",
                "UNCONFIGURED", "refusal", elapsed_seconds=self.clock() - started,
                detail="No reasoning provider is configured on this machine.",
            )

        remaining = self.deadline_seconds - (self.clock() - started)
        if remaining <= 0:
            return TurnResult(
                "That took too long. Ask me again.", "UNAVAILABLE", "timeout",
                elapsed_seconds=self.clock() - started,
            )

        context = record.context_for_reasoning() if record is not None else ""
        try:
            answer = self.reasoner.answer(question, context=context)
        except Exception as exc:  # noqa: BLE001 - a provider fault must not end the drive
            return TurnResult(
                "I couldn't work that out just now.", "UNAVAILABLE", "provider",
                provider_called=True, elapsed_seconds=self.clock() - started,
                detail=f"{type(exc).__name__}: {exc}",
            )

        elapsed = self.clock() - started
        if elapsed > self.deadline_seconds:
            # The answer arrived, and it arrived too late to be spoken at speed.
            # Said plainly rather than delivered into a gap the driver has
            # already filled by looking at the screen.
            return TurnResult(
                "That took too long, so I'll leave it. Ask me again when you're stopped.",
                "UNAVAILABLE", "timeout", provider_called=True, elapsed_seconds=elapsed,
                detail="The provider answered after the deadline.",
            )

        text = getattr(answer, "text", "") or ""
        status = getattr(answer, "status", "UNVERIFIED")
        return TurnResult(
            text or "I don't have an answer for that.",
            status if status else "UNVERIFIED", "provider",
            provider_called=True, elapsed_seconds=elapsed,
            detail=str(getattr(answer, "provenance", "") or ""),
        )
