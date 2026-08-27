"""Assistant Memory - Workstream 2.

Sandbox retention: Level 1, Level 2, Level 3, Print Ready, Delete, Expiration.

This package imports nothing outside itself and nothing outside folder 2.
It holds records. It routes nothing, produces nothing, and contacts nothing.
"""

__version__ = "1.0.0"

from .clock import Clock, SystemClock, FixedClock
from .record import (
    DEFAULT_RETENTION_HOURS,
    RECORD_FIELDS,
    InteractionLevel,
    MemoryRecord,
    RetentionState,
)
from .store import MemoryStore, StoreError
from .retention import Operation, OperationResult, RetentionEngine, RetentionError

__all__ = [
    "__version__",
    "Clock", "SystemClock", "FixedClock",
    "DEFAULT_RETENTION_HOURS", "RECORD_FIELDS",
    "InteractionLevel", "MemoryRecord", "RetentionState",
    "MemoryStore", "StoreError",
    "Operation", "OperationResult", "RetentionEngine", "RetentionError",
]
