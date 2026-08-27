"""Button actions as requests.

Every button in this window records a REQUEST. Nothing here saves, prints,
formalizes, or deletes anything outside this window. There is no retention
store, no printer, no library, and no other workstream to call.

A request is a statement of what the driver asked for, not a claim that it
happened.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import datetime, timezone


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ActionKind:
    SAVE = "SAVE"
    LEVEL_3 = "LEVEL_3"
    PRINT = "PRINT"
    DELETE = "DELETE"

    ALL = (SAVE, LEVEL_3, PRINT, DELETE)


# What the status line says after each button. Worded so it never claims a
# completed action.
ACTION_NOTICE = {
    ActionKind.SAVE: "Save requested. Recorded in this window only.",
    ActionKind.LEVEL_3: "Level 3 requested. No report was produced.",
    ActionKind.PRINT: "Print requested. No printer was contacted.",
    ActionKind.DELETE: "Removed from this window. Nothing else was changed.",
}

ACTION_LABEL = {
    ActionKind.SAVE: "Save",
    ActionKind.LEVEL_3: "Level 3",
    ActionKind.PRINT: "Print",
    ActionKind.DELETE: "Delete",
}


@dataclass
class ActionRequest:
    """One recorded button press."""

    request_id: str
    kind: str
    turn_id: str
    turn_text: str
    requested_at: str
    performed: bool = False
    notice: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "kind": self.kind,
            "turn_id": self.turn_id,
            "turn_text": self.turn_text,
            "requested_at": self.requested_at,
            "performed": self.performed,
            "notice": self.notice,
        }

    def display_line(self) -> str:
        return (
            self.request_id
            + "  "
            + ACTION_LABEL.get(self.kind, self.kind)
            + " on "
            + self.turn_id
            + "  (performed=" + str(self.performed) + ")"
        )


class ActionLogError(ValueError):
    pass


class ActionLog:
    """In-memory record of what the driver pressed.

    Kept in memory on purpose. This workstream writes no files, so a review
    of folder 1 does not have to ask where anything went.
    """

    def __init__(self) -> None:
        self._requests: list[ActionRequest] = []
        self._counter = itertools.count(1)

    def record(self, kind: str, turn_id: str, turn_text: str) -> ActionRequest:
        if kind not in ActionKind.ALL:
            raise ActionLogError("unknown action: " + str(kind))
        request = ActionRequest(
            request_id="REQ-{0:03d}".format(next(self._counter)),
            kind=kind,
            turn_id=turn_id,
            turn_text=turn_text,
            requested_at=_stamp(),
            performed=False,
            notice=ACTION_NOTICE[kind],
        )
        self._requests.append(request)
        return request

    @property
    def requests(self) -> list[ActionRequest]:
        return list(self._requests)

    def __len__(self) -> int:
        return len(self._requests)

    def of_kind(self, kind: str) -> list[ActionRequest]:
        return [r for r in self._requests if r.kind == kind]

    def for_turn(self, turn_id: str) -> list[ActionRequest]:
        return [r for r in self._requests if r.turn_id == turn_id]

    def display_lines(self) -> list[str]:
        return [request.display_line() for request in self._requests]
