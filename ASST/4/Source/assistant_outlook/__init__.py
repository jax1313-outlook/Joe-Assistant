"""Assistant Outlook - Workstream 4.

Read-only calendar, email, and contact awareness.

No sending. No modification. No scheduling. No approval authority.
This package imports nothing outside itself and nothing outside folder 4.
"""

__version__ = "1.0.0"

from .models import CalendarEvent, Contact, EmailMessage, ModelError, parse_moment
from .provider import (
    AwarenessProvider,
    JsonFileProvider,
    ProviderError,
    resolve_data_root,
)
from .awareness import (
    DECISION_MARKERS,
    Awareness,
    AwarenessError,
    Conflict,
    DayBrief,
    FlaggedMessage,
)

__all__ = [
    "__version__",
    "CalendarEvent", "Contact", "EmailMessage", "ModelError", "parse_moment",
    "AwarenessProvider", "JsonFileProvider", "ProviderError", "resolve_data_root",
    "DECISION_MARKERS", "Awareness", "AwarenessError", "Conflict", "DayBrief",
    "FlaggedMessage",
]
