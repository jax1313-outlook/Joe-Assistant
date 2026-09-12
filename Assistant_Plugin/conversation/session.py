"""A conversation with a driver: turns, interruption, and an audit of both.

`Assistant_Plugin/voice/assistant_voice/session.py` already handles the
mechanics of speech -- turn taking, queueing, barge-in -- and this module does
not duplicate it. This is the layer above: what a conversation *is*, how it ends,
what it remembers within itself, and what it writes down.

**Interruption is normal, not an error.** A driver who cuts Joe off mid-sentence
has decided the answer is not what he needed, and the correct response is to stop
speaking immediately and listen. The half-spoken answer is recorded as
interrupted rather than as delivered, because a record saying Joe told the driver
something he did not hear is worse than no record.

**A session forgets when it ends.** There is no cross-session memory here.
Dispatch is the system of record; a second memory in the assistant is a second
truth, and D4 (Single Source Of Truth) forbids it. What persists is the audit --
what was asked, what was answered, and what was proposed -- not a model of the
driver.

**Every turn is recorded before it is spoken**, so a turn that is interrupted,
times out, or crashes still leaves a trace. A conversation that failed silently
is indistinguishable from one that never happened.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

OPEN = "OPEN"
CLOSED = "CLOSED"

#: Why a turn ended. The distinctions matter to the person reading the audit.
SPOKEN = "SPOKEN"
INTERRUPTED = "INTERRUPTED"
REFUSED = "REFUSED"
FAILED = "FAILED"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Turn:
    index: int
    heard: str
    spoken: str
    outcome: str
    status: str
    source: str
    at: str = field(default_factory=_now)
    proposal: dict | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ConversationSession:
    """One conversation. Bounded, auditable, and forgetful by design."""

    orchestrator: object
    load_id: str = ""
    driver_id: str = ""
    session_id: str = field(default_factory=lambda: f"CONV-{uuid.uuid4().hex[:10].upper()}")
    state: str = OPEN
    turns: list = field(default_factory=list)
    started_at: str = field(default_factory=_now)
    ended_at: str = ""
    #: Set true by the voice layer when the driver speaks over Joe. Checked
    #: before a turn is recorded as delivered.
    _interrupted: bool = False

    # ------------------------------------------------------------- interruption

    def interrupt(self) -> None:
        """The driver spoke over Joe. Stop, and do not claim he heard it."""
        self._interrupted = True

    def _take_interrupt(self) -> bool:
        was, self._interrupted = self._interrupted, False
        return was

    # -------------------------------------------------------------------- turns

    def ask(self, heard: str) -> Turn:
        if self.state != OPEN:
            return self._record(heard, "This conversation is over.", REFUSED, "ABSENT", "refusal")

        try:
            result = self.orchestrator.take_turn(heard, load_id=self.load_id)
        except Exception as exc:  # noqa: BLE001 - a crash here must not end the drive
            return self._record(
                heard, "Something went wrong on my end.", FAILED, "UNAVAILABLE", "failure",
                detail=f"{type(exc).__name__}: {exc}",
            )

        outcome = INTERRUPTED if self._take_interrupt() else (
            REFUSED if result.source == "refusal" else SPOKEN
        )
        spoken = result.spoken
        if outcome == INTERRUPTED:
            # What was actually delivered is unknown, so the record says so
            # rather than quoting the whole sentence as though it landed.
            spoken = f"(interrupted) {result.spoken}"
        return self._record(
            heard, spoken, outcome, result.status, result.source, detail=result.detail
        )

    def propose(self, heard: str, confidence: float) -> Turn:
        """Offer a change. Never applies one -- see conversation/capture.py."""
        from conversation.capture import propose_change

        proposal = propose_change(heard, load_id=self.load_id, confidence=confidence)
        if proposal is None:
            return self._record(
                heard,
                "I didn't catch that well enough to act on it.",
                REFUSED, "UNVERIFIED", "capture",
                detail=f"below the confidence floor, or not a phrase Joe knows ({confidence:.2f})",
            )
        turn = self._record(
            heard, proposal.confirmation_prompt, SPOKEN, "LIVE", "capture",
            detail=proposal.summary,
        )
        turn.proposal = proposal.to_dict()
        return turn

    def confirm(self, answer: str) -> dict | None:
        """The driver's yes or no to the last proposal.

        Returns the proposal to apply, or None. Applying it is Dispatch's, and
        this method returning a dict rather than performing a write is the whole
        boundary in one line.
        """
        said = (answer or "").strip().lower()
        last = self._last_proposal_turn()
        if last is None:
            self._record(answer, "There's nothing to confirm.", REFUSED, "ABSENT", "capture")
            return None
        if said in ("yes", "yeah", "yep", "correct", "right", "confirm", "do it"):
            self._record(answer, "Sent to the office.", SPOKEN, "LIVE", "capture",
                         detail="confirmed")
            return dict(last.proposal)
        if said in ("no", "nope", "cancel", "wrong", "never mind", "nevermind"):
            self._record(answer, "Dropped it.", SPOKEN, "LIVE", "capture", detail="declined")
            return None
        # Anything else is not a yes. A proposal advances only on an
        # unambiguous confirmation, because "uh" is not consent.
        self._record(answer, "I need a yes or a no.", REFUSED, "UNVERIFIED", "capture")
        return None

    def _last_proposal_turn(self) -> Turn | None:
        for turn in reversed(self.turns):
            if turn.proposal:
                return turn
            if turn.source == "capture" and turn.detail in ("confirmed", "declined"):
                return None
        return None

    def close(self) -> None:
        """End it. Nothing is carried into the next conversation."""
        self.state = CLOSED
        self.ended_at = _now()

    # ------------------------------------------------------------------- audit

    def _record(self, heard, spoken, outcome, status, source, detail="") -> Turn:
        turn = Turn(
            index=len(self.turns), heard=heard, spoken=spoken, outcome=outcome,
            status=status, source=source, detail=detail,
        )
        self.turns.append(turn)
        return turn

    def audit(self) -> dict:
        """What was asked, what was answered, what was proposed. Not a model of
        the driver."""
        return {
            "session_id": self.session_id,
            "load_id": self.load_id,
            "driver_id": self.driver_id,
            "state": self.state,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "turn_count": len(self.turns),
            "interrupted_turns": sum(1 for t in self.turns if t.outcome == INTERRUPTED),
            "proposals": [t.proposal for t in self.turns if t.proposal],
            "turns": [t.to_dict() for t in self.turns],
        }
