"""Conversation model for the Assistant UI.

Pure data and logic. No widgets, no files, no network, no other workstream.
This module is what the tests exercise; the tkinter layer only renders it.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class Speaker:
    DRIVER = "DRIVER"
    ASSISTANT = "ASSISTANT"

    ALL = (DRIVER, ASSISTANT)


@dataclass
class Turn:
    """One line of conversation. Immutable in practice."""

    turn_id: str
    speaker: str
    text: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "turn_id": self.turn_id,
            "speaker": self.speaker,
            "text": self.text,
            "created_at": self.created_at,
        }

    def display_line(self) -> str:
        label = "You" if self.speaker == Speaker.DRIVER else "Assistant"
        return "[" + self.turn_id + "] " + label + ": " + self.text


class ConversationError(ValueError):
    pass


class Conversation:
    """Ordered turns with a single selected turn.

    The UI acts on the selected turn. Selection defaults to the newest turn
    so the driver can press a button without aiming at anything.
    """

    def __init__(self) -> None:
        self._turns: list[Turn] = []
        self._counter = itertools.count(1)
        self._selected_id: str | None = None

    # ---- adding -------------------------------------------------------

    def _next_id(self) -> str:
        return "T{0:03d}".format(next(self._counter))

    def add_turn(self, speaker: str, text: str) -> Turn:
        if speaker not in Speaker.ALL:
            raise ConversationError("unknown speaker: " + str(speaker))
        cleaned = (text or "").strip()
        if not cleaned:
            raise ConversationError("a turn needs text")
        turn = Turn(
            turn_id=self._next_id(),
            speaker=speaker,
            text=cleaned,
            created_at=_stamp(_utc_now()),
        )
        self._turns.append(turn)
        self._selected_id = turn.turn_id
        return turn

    def add_driver_turn(self, text: str) -> Turn:
        return self.add_turn(Speaker.DRIVER, text)

    def add_assistant_turn(self, text: str) -> Turn:
        return self.add_turn(Speaker.ASSISTANT, text)

    # ---- reading ------------------------------------------------------

    @property
    def turns(self) -> list[Turn]:
        return list(self._turns)

    def __len__(self) -> int:
        return len(self._turns)

    @property
    def is_empty(self) -> bool:
        return not self._turns

    def get(self, turn_id: str) -> Turn:
        for turn in self._turns:
            if turn.turn_id == turn_id:
                return turn
        raise ConversationError("no such turn: " + str(turn_id))

    def has(self, turn_id: str) -> bool:
        return any(turn.turn_id == turn_id for turn in self._turns)

    def history_lines(self) -> list[str]:
        return [turn.display_line() for turn in self._turns]

    # ---- selection ----------------------------------------------------

    @property
    def selected_id(self) -> str | None:
        return self._selected_id

    @property
    def selected(self) -> Turn | None:
        if self._selected_id is None:
            return None
        return self.get(self._selected_id)

    def select(self, turn_id: str) -> Turn:
        turn = self.get(turn_id)
        self._selected_id = turn.turn_id
        return turn

    def clear_selection(self) -> None:
        self._selected_id = None

    # ---- removal ------------------------------------------------------

    def remove(self, turn_id: str) -> Turn:
        """Remove one turn from the visible conversation.

        This affects the window only. Nothing outside this folder is
        touched, because nothing outside this folder is reachable.
        """
        turn = self.get(turn_id)
        index = self._turns.index(turn)
        self._turns.remove(turn)
        if self._selected_id == turn_id:
            if self._turns:
                self._selected_id = self._turns[min(index, len(self._turns) - 1)].turn_id
            else:
                self._selected_id = None
        return turn

    def clear(self) -> None:
        self._turns.clear()
        self._selected_id = None
