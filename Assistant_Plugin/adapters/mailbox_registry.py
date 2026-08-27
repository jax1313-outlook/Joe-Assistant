"""Email Connection Layer v1 - the mailbox registry.

Replaces the single `outlook.account` string. That model could name one mailbox
and assumed it held mail, calendar, AND contacts. On this profile it does not:
Ops@l1truck.com holds 127 messages, no calendar, and no contacts. Pointing the
one setting at Ops@ therefore answered every calendar question with silence -
truthfully, and uselessly.

WHAT THIS LAYER GUARANTEES

  Discovery reconciles THREE Outlook views, not one.
      Namespace.Accounts  - full accounts
      Namespace.Stores    - accounts PLUS shared and additional mailboxes
      Namespace.Folders   - the mailbox roots actually mounted
  A shared mailbox appears in Stores and Folders but NOT in Accounts. Reading
  Accounts alone - which the old adapter did - would silently hide one.

  Three truth states, never two.
      present  - Outlook answered, and exposed the mailbox
      absent   - Outlook answered, and did not expose it
      unknown  - Outlook could not be asked
  A timeout is unknown. It is never absent. Failed discovery is never cached,
  so a mailbox that was unreachable for a minute is not declared gone.

  Mail, calendar, and contacts are chosen SEPARATELY. No mailbox is assumed to
  supply all three.

  Read-only. There is no send path, no delete, no move, no flag, no rule. Not
  "disabled" - absent.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from contracts import SourceClass

# ---- what an Outlook object turns out to be -----------------------------
FULL_ACCOUNT = "full account"
SHARED_MAILBOX = "shared mailbox"
ADDITIONAL_STORE = "additional store"
DATA_FILE = "data file"
UNKNOWN_OBJECT = "unknown Outlook object"

# ---- truth states -------------------------------------------------------
PRESENT = "present"
ABSENT = "absent"
UNKNOWN = "unknown"

# ---- what a mailbox can supply ------------------------------------------
MAIL = "mail"
CALENDAR = "calendar"
CONTACTS = "contacts"
CAPABILITIES = (MAIL, CALENDAR, CONTACTS)

# Read-only, and this is the enforced list rather than a comment.
READ_AUTHORITY = "read"
WRITE_AUTHORITY = "none"

_DISCOVERY = r"""
$ErrorActionPreference='Stop'
$out = [ordered]@{ ok=$false; accounts=@(); stores=@(); folders=@(); error='' }
try {
  $wasRunning = @(Get-Process OUTLOOK -ErrorAction SilentlyContinue).Count -gt 0
  $ol = New-Object -ComObject Outlook.Application
  $ns = $ol.GetNamespace('MAPI')

  $rows = @()
  foreach ($a in $ns.Accounts) {
    $store = ''
    try { $store = [string]$a.DeliveryStore.DisplayName } catch {}
    $rows += [ordered]@{
      display_name = [string]$a.DisplayName
      smtp         = [string]$a.SmtpAddress
      store        = $store
    }
  }
  $out.accounts = $rows

  $rows = @()
  foreach ($s in $ns.Stores) {
    $path = ''
    try { $path = [string]$s.FilePath } catch {}
    # What this mailbox actually HOLDS. A mailbox that is present but has no
    # calendar must never be offered as the calendar source - that answers
    # every calendar question with silence while looking like an answer.
    $mail = -1; $cal = -1; $con = -1
    try { $mail = [int]$s.GetDefaultFolder(6).Items.Count } catch {}
    try { $cal  = [int]$s.GetDefaultFolder(9).Items.Count } catch {}
    try { $con  = [int]$s.GetDefaultFolder(10).Items.Count } catch {}
    $rows += [ordered]@{
      display_name = [string]$s.DisplayName
      exchange_type = [int]$s.ExchangeStoreType
      file_path    = $path
      is_data_file = [bool]$s.IsDataFileStore
      mail_count   = $mail
      calendar_count = $cal
      contacts_count = $con
    }
  }
  $out.stores = $rows

  $rows = @()
  foreach ($f in $ns.Folders) { $rows += [string]$f.Name }
  $out.folders = $rows

  $out.ok = $true
  if (-not $wasRunning) { $ol.Quit() }
} catch {
  $out.error = $_.Exception.Message
}
$out | ConvertTo-Json -Depth 5 -Compress
"""


@dataclass
class MailboxConnection:
    """One configured mailbox, and everything known about it."""

    connection_id: str
    friendly_name: str
    address: str
    enabled: bool = True
    provider: str = "Outlook Desktop"

    # filled by discovery
    status: str = UNKNOWN
    object_type: str = UNKNOWN_OBJECT
    discovered_in: list = field(default_factory=list)
    last_success: str = ""
    last_failure: str = ""
    failure_message: str = ""

    read_authority: str = READ_AUTHORITY
    write_authority: str = WRITE_AUTHORITY
    provenance_class: str = SourceClass.LOCAL_OUTLOOK

    # what this mailbox is the default source for
    default_for: list = field(default_factory=list)

    # How many items each folder holds. -1 means the folder could not be read,
    # which is NOT the same as holding nothing.
    holdings: dict = field(default_factory=dict)

    def holds(self, capability: str) -> bool:
        """Does this mailbox actually have anything of this kind?

        Unreadable (-1) counts as "maybe" rather than "no" - refusing to use a
        mailbox because one folder failed to answer would be treating a
        failure as a fact."""
        count = self.holdings.get(capability)
        if count is None or count < 0:
            return True
        return count > 0

    @property
    def usable(self) -> bool:
        return self.enabled and self.status == PRESENT

    @property
    def display(self) -> str:
        """What an operator sees. No COM terms, no connection ids."""
        label = {PRESENT: "LIVE", ABSENT: "NOT MOUNTED",
                 UNKNOWN: "UNKNOWN"}[self.status]
        if self.enabled is False:
            label = "OFF"
        return label

    def to_dict(self) -> dict:
        return {
            "connection_id": self.connection_id,
            "friendly_name": self.friendly_name,
            "address": self.address,
            "provider": self.provider,
            "object_type": self.object_type,
            "status": self.status,
            "display": self.display,
            "enabled": self.enabled,
            "default_for": list(self.default_for),
            "read_authority": self.read_authority,
            "write_authority": self.write_authority,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "failure_message": self.failure_message,
            "discovered_in": list(self.discovered_in),
            "holdings": dict(self.holdings),
            "provenance_class": self.provenance_class,
        }


@dataclass
class Discovery:
    """What Outlook exposed, reconciled across all three views."""

    ok: bool = False
    error: str = ""
    accounts: list = field(default_factory=list)
    stores: list = field(default_factory=list)
    folders: list = field(default_factory=list)

    def classify(self, address: str) -> tuple:
        """(status, object_type, views) for one mailbox address.

        UNKNOWN when Outlook could not be asked. Never absent on a failure -
        that conflation is how a working mailbox gets declared gone.
        """
        if not self.ok:
            return UNKNOWN, UNKNOWN_OBJECT, []

        views = []
        account = _find(self.accounts, address, "smtp", "display_name")
        store = _find(self.stores, address, "display_name")
        folder = next((f for f in self.folders if _same(f, address)), None)

        if account:
            views.append("Accounts")
        if store:
            views.append("Stores")
        if folder:
            views.append("Folders")

        if not views:
            return ABSENT, UNKNOWN_OBJECT, []

        return PRESENT, _object_type(account, store), views


def _same(a, b) -> bool:
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def _find(rows, address, *keys):
    for row in rows or []:
        for key in keys:
            if _same(str(row.get(key, "")), address):
                return row
    return None


def _object_type(account, store) -> str:
    """What kind of Outlook object this is.

    A shared mailbox is the case that matters: it appears in Stores but not in
    Accounts. Reading Accounts alone reports it as absent, which is how a
    mounted mailbox becomes invisible.
    """
    if account and store:
        return FULL_ACCOUNT
    if store and not account:
        path = str(store.get("file_path", "") or "").lower()
        if path.endswith(".pst"):
            return DATA_FILE
        if int(store.get("exchange_type", -1) or -1) >= 0:
            return SHARED_MAILBOX
        return ADDITIONAL_STORE
    if account and not store:
        return FULL_ACCOUNT
    return UNKNOWN_OBJECT


class MailboxRegistry:
    """The configured mailboxes, and which one answers which question."""

    name = "mailbox-registry"

    def __init__(self, connections=None, defaults=None, timeout_seconds=90,
                 logger=None, enabled=True) -> None:
        self.connections = list(connections or [])
        self.defaults = dict(defaults or {})
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self._logger = logger
        self.last_discovery: Discovery | None = None
        self.last_error = ""

    # ---- discovery -----------------------------------------------------

    def discover(self) -> Discovery:
        """Ask Outlook what it exposes. Never caches a failure."""
        if not self.enabled:
            self.last_discovery = Discovery(ok=True)
            return self.last_discovery

        try:
            finished = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _DISCOVERY],
                capture_output=True, text=True,
                # Real mail carries characters PowerShell does not
                # emit as clean UTF-8. Strict decoding raised
                # UnicodeDecodeError inside the reader THREAD, which
                # killed the read and surfaced as "Outlook returned
                # nothing" - a live mailbox reported as unreadable
                # because one subject line had an odd byte.
                encoding="utf-8", errors="replace", timeout=self.timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            raw = (finished.stdout or "").strip()
            payload = json.loads(raw) if raw else {}
        except subprocess.TimeoutExpired:
            return self._failed("Outlook did not respond within "
                                + str(self.timeout_seconds) + " seconds")
        except json.JSONDecodeError:
            return self._failed("Outlook returned output that could not be read")
        except Exception as error:  # noqa: BLE001
            return self._failed(str(error))

        if not payload.get("ok"):
            return self._failed(str(payload.get("error") or "unknown Outlook error"))

        discovery = Discovery(
            ok=True,
            accounts=_as_list(payload.get("accounts")),
            stores=_as_list(payload.get("stores")),
            folders=[str(f) for f in _as_list(payload.get("folders"))],
        )
        self.last_discovery = discovery
        self.last_error = ""
        self._apply(discovery)
        return discovery

    def _failed(self, message: str) -> Discovery:
        """A failure is UNKNOWN, and is not remembered as absence."""
        self.last_error = message
        self.last_discovery = None          # do not cache ignorance
        self._log("mailbox_discovery_failed", message)
        for connection in self.connections:
            connection.status = UNKNOWN
            connection.last_failure = message
            connection.failure_message = message
        return Discovery(ok=False, error=message)

    def _apply(self, discovery: Discovery) -> None:
        from adapters.outlook_com import stamp

        for connection in self.connections:
            status, object_type, views = discovery.classify(connection.address)
            connection.status = status
            connection.object_type = object_type
            connection.discovered_in = views
            store = _find(discovery.stores, connection.address, "display_name")
            if store:
                # `or -1` here would turn a genuine count of ZERO into -1,
                # which this code reads as "unknown". An empty calendar would
                # then be indistinguishable from an unreadable one - the exact
                # conflation this layer exists to prevent, introduced by a
                # falsy-zero idiom.
                connection.holdings = {
                    MAIL: _count(store.get("mail_count")),
                    CALENDAR: _count(store.get("calendar_count")),
                    CONTACTS: _count(store.get("contacts_count")),
                }
            if status == PRESENT:
                connection.last_success = stamp()
                connection.failure_message = ""
            elif status == ABSENT:
                connection.failure_message = (
                    "not mounted in Outlook Desktop on this machine")
            self._log("mailbox_status",
                      connection.address + " = " + status
                      + (" (" + object_type + ")" if views else ""))

    # ---- lookup --------------------------------------------------------

    def get(self, wanted: str):
        """By connection id, friendly name, or address."""
        for connection in self.connections:
            if wanted and (
                connection.connection_id.lower() == wanted.strip().lower()
                or _same(connection.friendly_name, wanted)
                or _same(connection.address, wanted)
            ):
                return connection
        return None

    @property
    def enabled_connections(self) -> list:
        return [c for c in self.connections if c.enabled]

    @property
    def usable_connections(self) -> list:
        return [c for c in self.connections if c.usable]

    def source_for(self, capability: str):
        """Which mailbox answers a mail / calendar / contacts question.

        A mailbox must be usable AND actually hold this kind of thing. On this
        profile Ops@l1truck.com holds 127 messages and no calendar; offering it
        as the calendar source answered every calendar question with "nothing
        scheduled", which was true of Ops@ and false of Mike's day.

        The configured default wins when it qualifies. Otherwise the first
        mailbox that does answers, and fallback_note says so - falling back
        silently would let Mike believe he read a mailbox he did not.
        """
        preferred = self.defaults.get(capability, "")
        if preferred:
            connection = self.get(preferred)
            if connection is not None and connection.usable \
                    and connection.holds(capability):
                return connection
        for connection in self.usable_connections:
            if connection.holds(capability):
                return connection
        return None

    def sources_for(self, capability: str) -> list:
        """Every enabled mailbox that could answer this kind of question."""
        return [c for c in self.usable_connections if c.holds(capability)]

    def fallback_note(self, capability: str) -> str:
        """Why this capability answered from where it did, or not at all.

        Runs even with no configured default. "No approved mailbox holds a
        calendar" is the single most useful thing JOE can say when it cannot
        answer a calendar question - the alternative is reporting an empty day,
        which is true of the mailbox and false of Mike."""
        preferred = self.defaults.get(capability, "")
        if not preferred:
            if self.source_for(capability) is None:
                if not self.usable_connections:
                    return "no approved mailbox is available"
                holders = [c.friendly_name for c in self.connections
                           if c.enabled and c.holds(capability)]
                if not holders:
                    return ("no approved mailbox holds any " + capability
                            + ". JOE is not reading an empty one - there is "
                              "nothing configured that has any.")
                return ("no available mailbox holds " + capability)
            return ""
        connection = self.get(preferred)
        chosen = self.source_for(capability)
        if connection is None:
            return ("the configured default " + capability + " source \""
                    + preferred + "\" is not a configured mailbox")
        if connection.usable and connection.holds(capability):
            return ""
        if connection.usable and not connection.holds(capability):
            chosen = self.source_for(capability)
            if chosen is None:
                return ("no configured mailbox holds any " + capability
                        + "; \"" + connection.friendly_name + "\" has none")
            return ("\"" + connection.friendly_name + "\" holds no " + capability
                    + ", so \"" + chosen.friendly_name + "\" answered instead")
        if chosen is None:
            return ("the default " + capability + " source \""
                    + connection.friendly_name + "\" is " + connection.status
                    + ", and no other mailbox is available")
        return ("the default " + capability + " source \""
                + connection.friendly_name + "\" is " + connection.status
                + ", so \"" + chosen.friendly_name + "\" answered instead")

    # ---- reporting -----------------------------------------------------

    def report(self) -> dict:
        return {
            "ok": self.last_discovery is not None,
            "error": self.last_error,
            "connections": [c.to_dict() for c in self.connections],
            "defaults": dict(self.defaults),
            "sources": {
                capability: (self.source_for(capability).friendly_name
                             if self.source_for(capability) else "")
                for capability in CAPABILITIES
            },
            "notes": {
                capability: self.fallback_note(capability)
                for capability in CAPABILITIES
                if self.fallback_note(capability)
            },
        }

    def _log(self, event: str, detail: str) -> None:
        if self._logger is None:
            return
        try:
            self._logger(event, detail)
        except Exception:  # noqa: BLE001
            pass


def _count(value) -> int:
    """A folder count, preserving the difference between 0 and unknown.

    Returns -1 only when the value is genuinely missing or unreadable. Zero
    means the folder was read and is empty, which is a fact."""
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return list(value)


def from_config(section: dict, logger=None, timeout_seconds=90) -> MailboxRegistry:
    """Build the registry from the `outlook` configuration section."""
    connections = []
    for row in section.get("accounts") or []:
        address = str(row.get("address", "")).strip()
        if not address:
            continue
        connections.append(MailboxConnection(
            connection_id=str(row.get("id") or address.split("@")[0]).lower(),
            friendly_name=str(row.get("friendly_name") or address),
            address=address,
            enabled=bool(row.get("enabled", True)),
        ))

    defaults = {
        MAIL: str(section.get("default_mail_source", "")),
        CALENDAR: str(section.get("default_calendar_source", "")),
        CONTACTS: str(section.get("default_contacts_source", "")),
    }
    registry = MailboxRegistry(
        connections=connections, defaults=defaults, logger=logger,
        timeout_seconds=timeout_seconds,
        enabled=bool(section.get("enabled", True)),
    )
    for capability, wanted in defaults.items():
        connection = registry.get(wanted) if wanted else None
        if connection is not None:
            connection.default_for.append(capability)
    return registry
