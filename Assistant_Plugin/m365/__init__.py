"""Microsoft 365 behind provider-neutral ports. Microsoft is a replaceable wheel."""

from m365.ports import (
    CalendarEvent, CalendarPort, ChatPort, DocumentPort, FilePort, MailPort,
    PortError, PortRefused, PortUnconfigured, Result, SitePort, StoredFile,
)
from m365.registry import M365Suite, build_suite

__all__ = [
    "CalendarEvent", "CalendarPort", "ChatPort", "DocumentPort", "FilePort",
    "MailPort", "PortError", "PortRefused", "PortUnconfigured", "Result",
    "SitePort", "StoredFile", "M365Suite", "build_suite",
]
