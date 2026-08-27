"""View model: everything the window does, with no widgets involved.

The tkinter layer is a thin renderer over this class. Keeping the logic here
means the whole behavior of the window is testable without a display, which
is why folder 1 can report proven behavior rather than a screenshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ACTION_LABEL, ActionKind, ActionLog, ActionRequest
from .conversation import Conversation, ConversationError, Speaker, Turn

WINDOW_TITLE = "Level 1 Assistant"

EMPTY_STATUS = "Ready. Type a message and press Send."
NOTHING_SELECTED = "Select a message first."

# The window is not connected to anything. Say so where the driver can see it.
CONNECTION_BANNER = (
    "UI only. Not connected to memory, library, email, research, or voice. "
    "Buttons record a request; they do not save, print, or file anything."
)


@dataclass
class ButtonState:
    kind: str
    label: str
    enabled: bool

    def to_dict(self) -> dict:
        return {"kind": self.kind, "label": self.label, "enabled": self.enabled}


@dataclass
class ViewState:
    """A complete snapshot of what the window should show."""

    title: str
    banner: str
    history: list[str] = field(default_factory=list)
    selected_id: str | None = None
    selected_text: str = ""
    status: str = EMPTY_STATUS
    buttons: list[ButtonState] = field(default_factory=list)
    action_history: list[str] = field(default_factory=list)
    turn_count: int = 0
    request_count: int = 0

    def button(self, kind: str) -> ButtonState:
        for state in self.buttons:
            if state.kind == kind:
                return state
        raise KeyError(kind)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "banner": self.banner,
            "history": list(self.history),
            "selected_id": self.selected_id,
            "selected_text": self.selected_text,
            "status": self.status,
            "buttons": [b.to_dict() for b in self.buttons],
            "action_history": list(self.action_history),
            "turn_count": self.turn_count,
            "request_count": self.request_count,
        }


class AssistantUIViewModel:
    """Drives JOE window.

    Deliberately knows nothing about retention, printing, filing, or any
    other workstream. Its whole job is: hold the conversation, track the
    selection, enable the right buttons, and record what was pressed.
    """

    def __init__(self, echo_assistant_reply: bool = True) -> None:
        self.conversation = Conversation()
        self.action_log = ActionLog()
        self._status = EMPTY_STATUS
        self._echo = echo_assistant_reply

    # ---- sending ------------------------------------------------------

    def send(self, text: str) -> Turn | None:
        """Add a driver message.

        This window has no reasoning of its own. When echo is on it adds a
        placeholder assistant line so the history and selection can be
        exercised; the placeholder says plainly that it is not an answer.
        """
        cleaned = (text or "").strip()
        if not cleaned:
            self._status = "Nothing to send."
            return None
        turn = self.conversation.add_driver_turn(cleaned)
        if self._echo:
            self.conversation.add_assistant_turn(
                "No assistant is connected to this window. "
                "Your message was recorded so the interface can be used."
            )
        self._status = "Sent."
        return turn

    # ---- selection ----------------------------------------------------

    def select(self, turn_id: str) -> bool:
        try:
            self.conversation.select(turn_id)
        except ConversationError:
            self._status = "No such message: " + str(turn_id)
            return False
        self._status = "Selected " + turn_id + "."
        return True

    # ---- buttons ------------------------------------------------------

    def _press(self, kind: str) -> ActionRequest | None:
        selected = self.conversation.selected
        if selected is None:
            self._status = NOTHING_SELECTED
            return None
        request = self.action_log.record(kind, selected.turn_id, selected.text)
        if kind == ActionKind.DELETE:
            self.conversation.remove(selected.turn_id)
        self._status = request.notice
        return request

    def press_save(self) -> ActionRequest | None:
        return self._press(ActionKind.SAVE)

    def press_level_3(self) -> ActionRequest | None:
        return self._press(ActionKind.LEVEL_3)

    def press_print(self) -> ActionRequest | None:
        return self._press(ActionKind.PRINT)

    def press_delete(self) -> ActionRequest | None:
        return self._press(ActionKind.DELETE)

    def press(self, kind: str) -> ActionRequest | None:
        return self._press(kind)

    # ---- rendering ----------------------------------------------------

    def button_states(self) -> list[ButtonState]:
        enabled = self.conversation.selected is not None
        return [
            ButtonState(kind=kind, label=ACTION_LABEL[kind], enabled=enabled)
            for kind in ActionKind.ALL
        ]

    @property
    def status(self) -> str:
        return self._status

    def view_state(self) -> ViewState:
        selected = self.conversation.selected
        return ViewState(
            title=WINDOW_TITLE,
            banner=CONNECTION_BANNER,
            history=self.conversation.history_lines(),
            selected_id=selected.turn_id if selected else None,
            selected_text=selected.text if selected else "",
            status=self._status,
            buttons=self.button_states(),
            action_history=self.action_log.display_lines(),
            turn_count=len(self.conversation),
            request_count=len(self.action_log),
        )
