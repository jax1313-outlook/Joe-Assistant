"""Assistant UI - Workstream 1.

Driver-facing Assistant window. UI only.

This package imports nothing outside itself and nothing outside folder 1.
It has no memory, no library, no email, no research, and no voice.
"""

__version__ = "1.0.0"

from .conversation import Conversation, ConversationError, Speaker, Turn
from .actions import ActionKind, ActionLog, ActionRequest
from .view_model import AssistantUIViewModel, ButtonState, ViewState

__all__ = [
    "__version__",
    "Conversation",
    "ConversationError",
    "Speaker",
    "Turn",
    "ActionKind",
    "ActionLog",
    "ActionRequest",
    "AssistantUIViewModel",
    "ButtonState",
    "ViewState",
]
