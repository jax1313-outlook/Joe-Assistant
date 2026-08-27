"""Sandbox Engine v1 - Level 1 Assistant local governed workflow layer.

Vendor-agnostic. Standard library only. No network access.
"""

__version__ = "1.0.0"

from .records import (
    SandboxRecord,
    RecordState,
    InteractionLevel,
    RECORD_FIELDS,
)
from .intents import CommandIntent, RecognizedCommand, recognize
from .clock import Clock, SystemClock, FixedClock
from .store import SandboxStore
from .engine import SandboxEngine, EngineError

__all__ = [
    "__version__",
    "SandboxRecord",
    "RecordState",
    "InteractionLevel",
    "RECORD_FIELDS",
    "CommandIntent",
    "RecognizedCommand",
    "recognize",
    "Clock",
    "SystemClock",
    "FixedClock",
    "SandboxStore",
    "SandboxEngine",
    "EngineError",
]
