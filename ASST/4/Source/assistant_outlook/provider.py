r"""Awareness providers.

A provider supplies calendar, email, and contact data. The port defines three
methods and all three are reads. There is no write method to implement, so no
provider - present or future - can be given one without changing this file.

The only provider built here is JsonFileProvider, which reads sample fixture
files inside ASST\4\Data. No live Outlook, Microsoft Graph, Exchange, or COM
provider exists in this workstream.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import CalendarEvent, Contact, EmailMessage, ModelError

ENV_ROOT = "ASSISTANT_OUTLOOK_DATA"


class ProviderError(RuntimeError):
    pass


class AwarenessProvider:
    """Read-only port. Three methods, all reads.

    Deliberately has no send, reply, accept, decline, create, update, delete,
    move, or flag method. A provider cannot acquire one by subclassing, because
    nothing in this component ever calls anything but these three.
    """

    name = "abstract"

    def calendar_events(self) -> list[CalendarEvent]:  # pragma: no cover
        raise NotImplementedError

    def email_messages(self) -> list[EmailMessage]:  # pragma: no cover
        raise NotImplementedError

    def contacts(self) -> list[Contact]:  # pragma: no cover
        raise NotImplementedError


def default_data_root() -> Path:
    """Sample data inside folder 4, used when no root is configured."""
    # ...\4\Source\assistant_outlook\provider.py -> ...\4\Data
    return Path(__file__).resolve().parent.parent.parent / "Data"


def resolve_data_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).resolve()
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    return default_data_root()


class JsonFileProvider(AwarenessProvider):
    """Reads calendar, email, and contact fixtures from JSON files.

    Opens files for reading only. A missing file yields an empty list and is
    reported, rather than raising - awareness of nothing is still awareness.
    A malformed file raises, because silently reporting an empty calendar when
    the file is broken would be a lie.
    """

    name = "json-file"

    CALENDAR_FILE = "calendar.json"
    EMAIL_FILE = "emails.json"
    CONTACTS_FILE = "contacts.json"

    def __init__(self, data_root: str | Path | None = None) -> None:
        self.data_root = resolve_data_root(data_root)
        self.missing: list[str] = []
        self.skipped: list[str] = []

    # ---- loading ------------------------------------------------------

    def _read_json_list(self, filename: str) -> list[dict]:
        path = self.data_root / filename
        if not path.exists():
            if filename not in self.missing:
                self.missing.append(filename)
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ProviderError(
                "malformed JSON in " + filename + ": " + str(error)
            ) from None
        if not isinstance(payload, list):
            raise ProviderError(filename + " must contain a JSON list")
        return payload

    def _build(self, filename: str, factory, label: str) -> list:
        built = []
        for entry in self._read_json_list(filename):
            try:
                built.append(factory(entry))
            except ModelError as error:
                self.skipped.append(label + ": " + str(error))
        return built

    # ---- the three reads ----------------------------------------------

    def calendar_events(self) -> list[CalendarEvent]:
        events = self._build(
            self.CALENDAR_FILE, CalendarEvent.from_dict, "calendar"
        )
        return sorted(events, key=lambda e: (e.start, e.event_id))

    def email_messages(self) -> list[EmailMessage]:
        messages = self._build(self.EMAIL_FILE, EmailMessage.from_dict, "email")
        return sorted(messages, key=lambda m: (m.received, m.message_id), reverse=True)

    def contacts(self) -> list[Contact]:
        found = self._build(self.CONTACTS_FILE, Contact.from_dict, "contact")
        return sorted(found, key=lambda c: c.display_name.lower())

    # ---- reporting ----------------------------------------------------

    def status(self) -> dict:
        """What the provider could and could not read. Never hides a gap."""
        return {
            "provider": self.name,
            "data_root": str(self.data_root),
            "data_root_exists": self.data_root.exists(),
            "missing_files": list(self.missing),
            "skipped_entries": list(self.skipped),
            "live_connection": False,
            "source": "local sample fixture files, not a live mailbox",
        }
