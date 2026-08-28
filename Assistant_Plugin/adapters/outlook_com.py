"""Outlook adapter - live, read-only, via Windows COM.

Provider-specific code lives here and nowhere else. The Outlook capability
module knows nothing about COM, PowerShell, or Windows.

READ ONLY, structurally:
  - the PowerShell it runs is generated from a fixed template in this file
  - the template contains no Send, Save, Delete, Move, Reply, or Create call
  - a guard scans the generated script and refuses to run it if one appears

ACCOUNTS: a mailbox may hold several accounts. `accounts()` lists them and
`account=` selects one; empty means the Outlook default store. Which account
was read is carried on every result, so an answer can never be silently about
the wrong mailbox.

ORDERING: none of the three folders is chronological by default.
  calendar  Sort([Start]) + IncludeRecurrences + Restrict to a date range
  mail      Sort([ReceivedTime], descending)  - newest first
  contacts  Sort([FileAs])            - alphabetical by File As, which
                                        Outlook stores last name first;
                                        File As is returned so the order
                                        is visible on screen
Whatever ordering was actually achieved is reported, never assumed.

LAZY: Outlook is contacted only when a capability asks for data. Opening the
Assistant never starts Outlook.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from contracts import Provenance, SourceClass, SourceMode, stamp

# Any of these appearing in a generated script means the adapter has become a
# writer. Refuse to run rather than find out afterwards.
# Contacts are sorted in Python, so the whole folder is fetched first. 2000 is
# a guard against a pathological address book, not an expected size.
_CONTACTS_FETCH_MAX = 2000

# How much of a message body to carry out of Outlook. A body is unbounded -
# a long forwarded thread runs to hundreds of kilobytes - and every one of
# those bytes would travel through JSON, into memory, and potentially into a
# reasoning provider's context. The cap is generous enough for an ordinary
# broker exchange and the row says when it bit, so a truncated body is never
# mistaken for a short one.
BODY_MAX_CHARS = 20000

FORBIDDEN_COM_CALLS = (
    ".Send(", ".Send()", ".Save(", ".Save()", ".Delete(", ".Delete()",
    ".Move(", ".Reply(", ".ReplyAll(", ".Forward(", ".Add(", ".CreateItem(",
    ".Respond(", ".Accept(", ".Decline(", ".MarkAsTask(", ".SaveAs(",
    "-Force", "Remove-Item", "Set-Content", "Out-File",
)

# olFolderCalendar=9, olFolderInbox=6, olFolderContacts=10
_FOLDER_ID = {"calendar": 9, "inbox": 6, "contacts": 10}

# Outlook's Restrict filter wants a US-style short date, e.g. "08/25/2026 12:00 AM".
# This is a PYTHON strftime format that produces that shape. It is deliberately
# not the .NET format string ("MM/dd/yyyy hh:mm tt") - Python returns those
# characters literally, which produced a filter that matched nothing and an
# empty calendar that looked like a genuinely empty day.
_PS_DATE = "%m/%d/%Y %I:%M %p"

# What a correctly formatted filter date must look like.
_PS_DATE_SHAPE = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2} (?:AM|PM)$")

# Raw C0 control bytes, which JSON forbids inside a string. Tab, CR and LF are
# included because ConvertTo-Json escapes those itself - anything left RAW in
# the output is a byte Windows PowerShell failed to escape, whatever it is.
# Anything below a space. Built from ord() rather than written as a regex
# escape, because expressing this range as \x00 in source is exactly how a
# real NUL byte got into this file once already.
_LOWEST_PRINTABLE = 32


# Free text travels out of PowerShell as base64, and is decoded here.
#
# WHY. Windows PowerShell 5.1's ConvertTo-Json emitted SOME quotes unescaped
# inside long message bodies - 3,654 bare quotes against 36 escaped ones in one
# real inbox - producing JSON that cannot be parsed:
#
#     Expecting ',' delimiter: line 1 column 136222
#
# and the whole mail read failed with "Outlook returned output that could not
# be read". A message body is arbitrary text written by strangers: quotes,
# control bytes, anything. Handing it to a serialiser that escapes it almost
# correctly is a defect waiting for the wrong email.
#
# Base64 has no quotes, no control bytes and no escaping. There is nothing left
# to get wrong.
_B64_FIELDS = ("subject", "sender", "sender_address", "to", "cc", "body")
_B64_ATTACHMENT_FIELDS = ("name", "display_name")


def _decode_b64(value: str) -> str:
    try:
        return base64.b64decode(str(value or "")).decode("utf-8", "replace")
    except (ValueError, binascii.Error):
        return ""


def decode_row(row: dict) -> dict:
    """Turn every *_b64 field back into the plain field it stands for."""
    if not isinstance(row, dict):
        return row
    for field in _B64_FIELDS:
        key = field + "_b64"
        if key in row:
            row[field] = _decode_b64(row.pop(key))
    for attachment in row.get("attachments") or []:
        if not isinstance(attachment, dict):
            continue
        for field in _B64_ATTACHMENT_FIELDS:
            key = field + "_b64"
            if key in attachment:
                attachment[field] = _decode_b64(attachment.pop(key))
    return row

def json_safe(text: str) -> tuple[str, int]:
    """Remove control bytes PowerShell left unescaped. Returns (text, removed).

    Windows PowerShell 5.1's ConvertTo-Json escapes tab, CR and LF and emits
    the other C0 controls RAW, which is not valid JSON. One real broker mail
    carrying a single 0x1A cost an entire read of 25 messages:

        Invalid control character at: line 1 column 11706

    and every message in that batch was lost to one invisible byte in one body.

    Stripping in PowerShell was tried first and did not work - the -replace
    matched nothing on the offending message even though the same expression
    removes those characters in isolation. Rather than keep guessing at
    PowerShell's regex semantics, the repair happens here, where it covers
    every field at once and can be tested without Outlook.

    Removing them cannot corrupt real content: a control byte carries no
    meaning in a subject, an address, or a message body, and any that were
    MEANT to be there would have arrived escaped.
    """
    original = text or ""
    cleaned = "".join(c for c in original if ord(c) >= _LOWEST_PRINTABLE)
    return cleaned, len(original) - len(cleaned)


_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$out = [ordered]@{ ok = $false; started_by_probe = $false; items = @(); ordering = 'folder' }
try {
  $wasRunning = [bool](Get-Process outlook -ErrorAction SilentlyContinue)
  $ol = New-Object -ComObject Outlook.Application
  if (-not $wasRunning) { $out.started_by_probe = $true }
  $ns = $ol.GetNamespace('MAPI')
  $out.profile = $ns.CurrentProfileName
  $out.outlook_version = $ol.Version

  $wanted = '__ACCOUNT__'
  $folder = $null
  if ($wanted -ne '') {
    foreach ($a in $ns.Accounts) {
      if ($a.SmtpAddress -eq $wanted -or $a.DisplayName -eq $wanted) {
        $folder = $a.DeliveryStore.GetDefaultFolder(__FOLDER__)
        $out.account = $a.SmtpAddress
        break
      }
    }
    if ($null -eq $folder) { throw "account not found in this Outlook profile: $wanted" }
  } else {
    $folder = $ns.GetDefaultFolder(__FOLDER__)
    try { $out.account = $ns.Accounts.Item(1).SmtpAddress } catch { $out.account = '(default store)' }
  }

  function B64 { param([string]$s)
    if ($null -eq $s) { $s = '' }
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($s))
  }
  $out.folder = $folder.Name
  $out.folder_total = $folder.Items.Count
  $source = $folder.Items
__PREPARE__
  $n = 0
  $rows = @()
  foreach ($i in $source) {
    $n++
    if ($n -gt __MAX__) { break }
    $row = [ordered]@{}
    __FIELDS__
    $rows += $row
  }
  $out.items = $rows
  $out.returned = $rows.Count
  $out.ok = $true
  if ($out.started_by_probe) { $ol.Quit() }
} catch {
  $out.ok = $false
  $out.error = $_.Exception.Message
}
$out | ConvertTo-Json -Depth 6 -Compress
"""

_ACCOUNTS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$out = [ordered]@{ ok = $false; accounts = @() }
try {
  $wasRunning = [bool](Get-Process outlook -ErrorAction SilentlyContinue)
  $ol = New-Object -ComObject Outlook.Application
  $ns = $ol.GetNamespace('MAPI')
  $rows = @()
  $first = $true
  foreach ($a in $ns.Accounts) {
    $row = [ordered]@{}
    $row.display_name = [string]$a.DisplayName
    $row.smtp = [string]$a.SmtpAddress
    $row.is_default = $first
    try { $row.store = [string]$a.DeliveryStore.DisplayName } catch { $row.store = '' }
    $rows += $row
    $first = $false
  }
  $out.accounts = $rows
  $out.count = $rows.Count
  $out.profile = $ns.CurrentProfileName
  $out.ok = $true
  if (-not $wasRunning) { $ol.Quit() }
} catch {
  $out.ok = $false
  $out.error = $_.Exception.Message
}
$out | ConvertTo-Json -Depth 6 -Compress
"""

# Per-folder preparation of the item collection.
#
# An Outlook Items collection is in folder order by default, which is not
# chronological and not alphabetical. Every folder therefore gets an explicit
# ordering step, and each records what it actually achieved so the application
# can report the truth rather than the best case.
#
# Sort, IncludeRecurrences, and Restrict act on this in-memory view. None of
# them writes to the mailbox; no item is created, changed, moved, or saved.
_PREPARE = {
    # calendar: chronological, recurrences expanded, restricted to a range.
    # The range is required once recurrences are included - a series with no
    # end date would otherwise iterate forever.
    "calendar": r"""
  try {
    $source.Sort("[Start]")
    $out.ordering = 'date_no_recurrences'
    try {
      $source.IncludeRecurrences = $true
      $filter = "[Start] >= '__START__' AND [Start] <= '__END__'"
      $out.filter = $filter
      $filtered = $source.Restrict($filter)
      $null = $filtered.Count
      $source = $filtered
      $out.ordering = 'date_with_recurrences'
      $out.window_start = '__WSTART__'
      $out.window_end = '__WEND__'
      $out.window_label = '__WLABEL__'
    } catch {
      $out.ordering_note = $_.Exception.Message
      $source = $folder.Items
      $source.Sort("[Start]")
    }
  } catch {
    $out.ordering = 'folder'
    $out.ordering_note = $_.Exception.Message
  }
""",
    # mail: newest first. $true is the descending flag.
    "inbox": r"""
  try {
    $source.Sort("[ReceivedTime]", $true)
    $out.ordering = 'received_desc'
  } catch {
    $out.ordering = 'folder'
    $out.ordering_note = $_.Exception.Message
  }
""",
    # contacts: Outlook cannot be trusted to sort this folder.
    #
    # [FileAs] is the field Outlook files a contact under, so Sort("[FileAs]")
    # is the documented way to get an alphabetical address book. On this
    # profile it is EMPTY on every synced contact - LastName is populated,
    # FileAs is not. Sorting on an empty key returns something close to folder
    # order for those contacts, and last-name order for the few that are
    # properly filed. The folder was therefore reported as "alphabetical by
    # name" while reading, on screen, as unsorted. That is the exact complaint
    # this was supposed to have fixed.
    #
    # The sort is still asked for - it costs nothing and helps where FileAs
    # exists - but the order that is REPORTED is produced in Python, over the
    # whole folder, on the name that is actually displayed. See _sort_contacts.
    "contacts": r"""
  try {
    $source.Sort("[FileAs]")
    $out.ordering = 'file_as_asc'
  } catch {
    $out.ordering = 'folder'
    $out.ordering_note = $_.Exception.Message
  }
""",
}

_FIELDS = {
    "calendar": (
        "$row.subject = [string]$i.Subject\n"
        "    $row.start = [string]$i.Start\n"
        "    $row.end = [string]$i.End\n"
        "    $row.location = [string]$i.Location\n"
        "    $row.organizer = [string]$i.Organizer\n"
        "    $row.all_day = [bool]$i.AllDayEvent"
    ),
    # Stage A. Every line below is a PROPERTY READ. No entry of
    # FORBIDDEN_COM_CALLS appears here, which is why _assert_read_only() passes
    # over it unchanged - the richer read adds information, not authority.
    #
    # Each field is wrapped on its own. A message with an unreadable property -
    # a corrupt item, a delegated mailbox that withholds a field, a meeting
    # request that has no Body - must not take the whole row down with it, and
    # must not silently return an empty string that reads like an empty field.
    # The name of every field that failed is carried out in `field_errors`, so
    # "not readable" and "empty" stay different facts.
    #
    # Arrays are built with += rather than .Add(), which the guard forbids.
    "inbox": (
        "$errs = @()\n"
        # identity: the message, and the thread it belongs to
        "    $row.entry_id = ''\n"
        "    try { $row.entry_id = [string]$i.EntryID } catch { $errs += 'entry_id' }\n"
        "    $row.conversation_id = ''\n"
        "    try { $row.conversation_id = [string]$i.ConversationID } catch { $errs += 'conversation_id' }\n"
        "    $row.subject_b64 = ''\n"
        "    try { $row.subject_b64 = B64 ([string]$i.Subject) } catch { $errs += 'subject' }\n"
        # sender: display name, and the real SMTP address behind it
        "    $row.sender_b64 = ''\n"
        "    try { $row.sender_b64 = B64 ([string]$i.SenderName) } catch { $errs += 'sender' }\n"
        "    $row.sender_address_b64 = ''\n"
        "    $row.sender_address_resolved = $false\n"
        "    try {\n"
        "      $addr = ''\n"
        # An Exchange sender's SenderEmailAddress is a legacyExchangeDN
        # (/O=.../CN=RECIPIENTS/CN=...), not an address anyone can reply to.
        # GetExchangeUser() resolves it. It is a read.
        "      if ($i.SenderEmailType -eq 'EX') {\n"
        "        try { $ex = $i.Sender.GetExchangeUser(); if ($ex) { $addr = [string]$ex.PrimarySmtpAddress; $row.sender_address_resolved = $true } } catch { }\n"
        "      }\n"
        "      if ($addr -eq '') { $addr = [string]$i.SenderEmailAddress }\n"
        "      $row.sender_address_b64 = B64 $addr\n"
        "    } catch { $errs += 'sender_address' }\n"
        # recipients
        "    $row.to_b64 = ''\n"
        "    try { $row.to_b64 = B64 ([string]$i.To) } catch { $errs += 'to' }\n"
        "    $row.cc_b64 = ''\n"
        "    try { $row.cc_b64 = B64 ([string]$i.CC) } catch { $errs += 'cc' }\n"
        # state
        "    $row.received = ''\n"
        "    try { $row.received = [string]$i.ReceivedTime } catch { $errs += 'received' }\n"
        "    $row.unread = $false\n"
        "    try { $row.unread = [bool]$i.UnRead } catch { $errs += 'unread' }\n"
        "    $row.importance = 1\n"
        "    try { $row.importance = [int]$i.Importance } catch { $errs += 'importance' }\n"
        # body, capped and honest about the cap
        "    $row.body_b64 = ''\n"
        "    $row.body_truncated = $false\n"
        "    $row.body_length = 0\n"
        "    try {\n"
        "      $b = [string]$i.Body\n"
        "      $row.body_length = $b.Length\n"
        # Windows PowerShell 5.1 ConvertTo-Json escapes tab, CR and LF and
        # emits the other C0 controls RAW, which is not valid JSON. One real
        # message carrying one invisible byte cost the whole read of 25:
        # "Invalid control character at column 11551", and every message in
        # that batch was lost with it. Strip the ones JSON cannot carry, keep
        # the three that mean something in a body, and say when it happened.
        "      if ($b.Length -gt __BODYMAX__) { $row.body_b64 = B64 ($b.Substring(0, __BODYMAX__)); $row.body_truncated = $true }\n"
        "      else { $row.body_b64 = B64 $b }\n"
        "    } catch { $errs += 'body' }\n"
        # attachments: names, types, sizes, identities. NOT contents.
        "    $row.has_attachments = $false\n"
        "    $atts = @()\n"
        "    try {\n"
        "      $row.has_attachments = [bool]($i.Attachments.Count -gt 0)\n"
        "      foreach ($a in $i.Attachments) {\n"
        "        $one = [ordered]@{ name_b64 = ''; display_name_b64 = ''; size = 0; type = 0; index = 0 }\n"
        "        try { $one.name_b64 = B64 ([string]$a.FileName) } catch { }\n"
        "        try { $one.display_name_b64 = B64 ([string]$a.DisplayName) } catch { }\n"
        "        try { $one.size = [int]$a.Size } catch { }\n"
        "        try { $one.type = [int]$a.Type } catch { }\n"
        "        try { $one.index = [int]$a.Index } catch { }\n"
        "        $atts += $one\n"
        "      }\n"
        "    } catch { $errs += 'attachments' }\n"
        "    $row.attachments = $atts\n"
        "    $row.field_errors = $errs"
    ),
    "contacts": (
        "$row.display_name = [string]$i.FullName\n"
        "    $row.file_as = [string]$i.FileAs\n"
        "    $row.email = [string]$i.Email1Address\n"
        "    $row.company = [string]$i.CompanyName\n"
        "    $row.phone = [string]$i.BusinessTelephoneNumber\n"
        "    $row.role = [string]$i.JobTitle"
    ),
}

ORDERING_LABEL = {
    "date_with_recurrences": "date order, recurring events included",
    "date_no_recurrences": "date order, recurring events NOT expanded",
    "received_desc": "newest received first",
    "display_name_asc": "alphabetical by the name shown",
    "file_as_asc": (
        "alphabetical by Outlook's File As name, which is usually last name "
        "first - so the displayed names will not read alphabetically"
    ),
    "folder": "folder order, NOT sorted",
}


class OutlookAdapterError(RuntimeError):
    pass


@dataclass
class DateRange:
    """A requested calendar range, with the words Mike used."""

    start: datetime
    end: datetime
    label: str

    @staticmethod
    def _formatted(moment: datetime) -> str:
        """Format for the Outlook filter, and refuse anything that is not a date.

        A malformed filter date does not raise in Outlook - it simply matches
        nothing, which is indistinguishable from an empty day. Checking the
        shape here turns a silent wrong answer into a loud failure.
        """
        text = moment.strftime(_PS_DATE)
        if not _PS_DATE_SHAPE.match(text):
            raise OutlookAdapterError(
                "calendar filter date is malformed: " + repr(text)
                + " - the format string is not producing a date"
            )
        return text

    def ps_start(self) -> str:
        return self._formatted(self.start)

    def ps_end(self) -> str:
        return self._formatted(self.end)

    def iso_start(self) -> str:
        return self.start.strftime("%Y-%m-%dT%H:%M:%S")

    def iso_end(self) -> str:
        return self.end.strftime("%Y-%m-%dT%H:%M:%S")


def range_for(label: str, days: int = 14, now: datetime | None = None) -> DateRange:
    """Build a calendar range from an ordinary word.

    Deterministic. `today`, `tomorrow`, `this week`, `next week`, `upcoming`,
    or a window of `days` starting at midnight today.
    """
    moment = now or datetime.now()
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    key = (label or "").strip().lower()
    if key == "today":
        return DateRange(midnight, midnight + timedelta(days=1), "today")
    if key == "tomorrow":
        start = midnight + timedelta(days=1)
        return DateRange(start, start + timedelta(days=1), "tomorrow")
    if key in ("this week", "week"):
        return DateRange(midnight, midnight + timedelta(days=7), "the next 7 days")
    if key == "next week":
        start = midnight + timedelta(days=7)
        return DateRange(start, start + timedelta(days=7), "next week")
    return DateRange(
        midnight, midnight + timedelta(days=days), "the next " + str(days) + " days"
    )


def range_for_date(target: datetime) -> DateRange:
    """A single named day."""
    start = target.replace(hour=0, minute=0, second=0, microsecond=0)
    return DateRange(start, start + timedelta(days=1), start.strftime("%A %d %B"))


@dataclass
class OutlookResult:
    ok: bool
    folder: str = ""
    items: list = field(default_factory=list)
    total: int = 0            # items in the folder
    returned: int = 0         # items actually handed back
    account: str = ""
    profile: str = ""
    version: str = ""
    error: str = ""
    ordering: str = "folder"
    ordering_note: str = ""
    window_start: str = ""
    window_end: str = ""
    window_label: str = ""
    read_at: str = field(default_factory=stamp)

    @property
    def live(self) -> bool:
        return self.ok

    @property
    def is_sorted(self) -> bool:
        return self.ordering != "folder"

    @property
    def is_date_ordered(self) -> bool:
        return self.ordering.startswith("date")

    @property
    def ordering_label(self) -> str:
        return ORDERING_LABEL.get(self.ordering, self.ordering)

    def window_line(self) -> str:
        if not self.window_start:
            return ""
        return (
            self.window_label
            + "  ("
            + self.window_start[:10]
            + " to "
            + self.window_end[:10]
            + ")"
        )

    def provenance(self) -> Provenance:
        if not self.ok:
            return Provenance(
                source="Outlook (read-only)",
                mode=SourceMode.UNAVAILABLE,
                as_of=self.read_at,
                detail=self.error,
                source_class=SourceClass.LOCAL_OUTLOOK,
            )
        detail = self.folder
        if self.account:
            detail += " / " + self.account
        detail += ", " + str(self.returned) + " of " + str(self.total)
        if self.window_start:
            detail += " in " + self.window_line()
        detail += ", " + self.ordering_label
        return Provenance(
            source="Outlook (read-only)",
            mode=SourceMode.LIVE,
            as_of=self.read_at,
            detail=detail,
            source_class=SourceClass.LOCAL_OUTLOOK,
        )


class OutlookComAdapter:
    """Live read-only Outlook access. Contacts Outlook only when asked."""

    name = "outlook-com"

    def __init__(
        self,
        enabled: bool = True,
        max_items: int = 60,
        timeout_seconds: int = 90,
        calendar_window_days: int = 14,
        account: str = "",
    ) -> None:
        self.enabled = enabled
        self.max_items = max(1, int(max_items))
        self.timeout_seconds = max(10, int(timeout_seconds))
        self.calendar_window_days = max(1, int(calendar_window_days))
        # Empty means the Outlook default store. A mailbox may hold several
        # accounts, so which one was read is carried on every result.
        self.account = (account or "").strip()
        self.last_error = ""
        self.last_connected_at = ""
        self.attempted = False
        self._accounts: list[dict] | None = None
        # False until an enumeration actually succeeds. An empty account
        # list means nothing without it. See accounts().
        self.accounts_known = False

    # ---- guard --------------------------------------------------------

    @staticmethod
    def _assert_read_only(script: str) -> None:
        for call in FORBIDDEN_COM_CALLS:
            if call in script:
                raise OutlookAdapterError(
                    "refused to run: generated script contains a non-read call ("
                    + call
                    + ")"
                )

    def _build_script(
        self, folder: str, date_range: DateRange | None = None, account: str | None = None
    ) -> str:
        if folder not in _FOLDER_ID:
            raise OutlookAdapterError("unknown folder: " + str(folder))
        wanted = self.account if account is None else (account or "")
        if "'" in wanted:
            raise OutlookAdapterError("account name contains an unsupported character")

        prepare = _PREPARE[folder]
        if folder == "calendar":
            window = date_range or range_for("", self.calendar_window_days)
            prepare = (
                prepare.replace("__START__", window.ps_start())
                .replace("__END__", window.ps_end())
                .replace("__WSTART__", window.iso_start())
                .replace("__WEND__", window.iso_end())
                .replace("__WLABEL__", window.label)
            )

        script = (
            _SCRIPT.replace("__FOLDER__", str(_FOLDER_ID[folder]))
            # Contacts are sorted in Python over the WHOLE folder (see
            # _sort_contacts), so the fetch must not be truncated first -
            # sorting an arbitrary 60 of 145 would alphabetise a slice and
            # look like an alphabetised address book.
            .replace("__MAX__", str(_CONTACTS_FETCH_MAX if folder == "contacts"
                                    else self.max_items))
            .replace("__ACCOUNT__", wanted)
            .replace("__PREPARE__", prepare)
            .replace("__FIELDS__", _FIELDS[folder])
            .replace("__BODYMAX__", str(BODY_MAX_CHARS))
        )
        self._assert_read_only(script)
        return script

    # ---- running ------------------------------------------------------

    def _powershell(self, script: str, timeout: int | None = None) -> tuple[bool, str, str]:
        try:
            done = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True, text=True,
                # Real mail carries characters PowerShell does not
                # emit as clean UTF-8. Strict decoding raised
                # UnicodeDecodeError inside the reader THREAD, which
                # killed the read and surfaced as "Outlook returned
                # nothing" - a live mailbox reported as unreadable
                # because one subject line had an odd byte.
                encoding="utf-8", errors="replace",
                timeout=timeout or self.timeout_seconds,
                # Without this, every Outlook read flashes a black console
                # window on screen. Mike is driving; a window that appears and
                # vanishes is a thing to look at and a thing to wonder about.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            return False, "", "PowerShell was not found on this machine"
        except subprocess.TimeoutExpired:
            return False, "", (
                "Outlook did not respond within "
                + str(timeout or self.timeout_seconds)
                + " seconds"
            )
        return True, (done.stdout or "").strip(), (done.stderr or "").strip()

    def _run(
        self,
        folder: str,
        date_range: DateRange | None = None,
        account: str | None = None,
    ) -> OutlookResult:
        if not self.enabled:
            return OutlookResult(ok=False, error="Outlook is disabled in configuration")
        script = self._build_script(folder, date_range, account)
        self.attempted = True
        ran, out, err = self._powershell(script)
        if not ran or not out:
            self.last_error = err or "Outlook returned nothing"
            return OutlookResult(ok=False, error=self.last_error)
        try:
            payload = json.loads(json_safe(out)[0])
        except json.JSONDecodeError:
            self.last_error = "Outlook returned output that could not be read"
            return OutlookResult(ok=False, error=self.last_error)
        if not payload.get("ok"):
            self.last_error = str(payload.get("error", "unknown Outlook error"))
            return OutlookResult(ok=False, error=self.last_error)

        items = payload.get("items") or []
        if isinstance(items, dict):
            items = [items]
        # Free text came out as base64 so PowerShell's JSON escaping could not
        # mangle it. Put it back before anyone downstream sees a row.
        items = [decode_row(dict(row)) if isinstance(row, dict) else row
                 for row in items]

        ordering = str(payload.get("ordering", "folder"))
        ordering_note = str(payload.get("ordering_note", ""))
        returned = int(payload.get("returned", len(items)))
        # Runs even for an empty folder. Otherwise a mailbox with no contacts
        # reports PowerShell's 'file_as_asc' - an ordering this program no
        # longer uses - for a list it never touched.
        if folder == "contacts":
            items, ordering, ordering_note = self._sort_contacts(items, self.max_items)
            returned = len(items)

        self.last_error = ""
        self.last_connected_at = stamp()
        return OutlookResult(
            ok=True,
            folder=str(payload.get("folder", folder)),
            items=list(items),
            total=int(payload.get("folder_total", len(items))),
            returned=returned,
            account=str(payload.get("account", "")),
            profile=str(payload.get("profile", "")),
            version=str(payload.get("outlook_version", "")),
            ordering=ordering,
            ordering_note=ordering_note,
            window_start=str(payload.get("window_start", "")),
            window_end=str(payload.get("window_end", "")),
            window_label=str(payload.get("window_label", "")),
            read_at=self.last_connected_at,
        )

    # ---- contacts ordering --------------------------------------------

    @staticmethod
    def _sort_contacts(items: list[dict], limit: int) -> tuple[list[dict], str, str]:
        """Order contacts by the name that is shown, and say so truthfully.

        Returns (items, ordering, note). Nothing is invented and nothing is
        dropped except by the limit, which is reported."""
        named = [i for i in items if str(i.get("display_name", "")).strip()]
        unnamed = [i for i in items if not str(i.get("display_name", "")).strip()]
        named.sort(key=lambda i: str(i.get("display_name", "")).strip().lower())
        ordered = named + unnamed
        note = ""
        if unnamed:
            note = (
                str(len(unnamed)) + " contact(s) have no name in Outlook and are "
                "listed last, in folder order"
            )
        return ordered[:limit], "display_name_asc", note

    # ---- the reads ----------------------------------------------------

    def calendar(
        self, date_range: DateRange | None = None, account: str | None = None
    ) -> OutlookResult:
        return self._run("calendar", date_range=date_range, account=account)

    def mail(self, account: str | None = None) -> OutlookResult:
        return self._run("inbox", account=account)

    def contacts(self, account: str | None = None) -> OutlookResult:
        return self._run("contacts", account=account)

    # ---- accounts -----------------------------------------------------

    def accounts(self, refresh: bool = False) -> list[dict]:
        """Every account in the Outlook profile. Read-only.

        An empty list from here means one of two very different things, and
        `accounts_known` is what tells them apart:

          True  - Outlook answered, and the profile really has no accounts.
          False - Outlook could not be asked. The empty list is ignorance,
                  not a finding.

        A failed enumeration is NOT cached. Outlook can be busy for a minute
        and fine the next, and caching a failure turned a transient timeout
        into a permanent "there are no mailboxes"."""
        if self._accounts is not None and not refresh:
            return self._accounts
        if not self.enabled:
            self._accounts = []
            self.accounts_known = True   # disabled by configuration, not unknown
            return self._accounts

        def unknown(reason: str) -> list[dict]:
            self.last_error = reason
            self.accounts_known = False
            self._accounts = None        # do not cache ignorance
            return []

        self._assert_read_only(_ACCOUNTS_SCRIPT)
        ran, out, err = self._powershell(_ACCOUNTS_SCRIPT)
        if not ran or not out:
            return unknown(err or "could not list Outlook accounts")
        try:
            payload = json.loads(json_safe(out)[0])
        except json.JSONDecodeError:
            return unknown("Outlook returned output that could not be read")
        if not payload.get("ok"):
            return unknown(str(payload.get("error", "unknown Outlook error")))

        rows = payload.get("accounts") or []
        if isinstance(rows, dict):
            rows = [rows]
        self._accounts = [dict(r) for r in rows]
        self.accounts_known = True
        return self._accounts

    def account_in_use(self) -> str:
        """The designated account, or the default if none is designated."""
        if self.account:
            return self.account
        found = self.accounts()
        for row in found:
            if row.get("is_default"):
                return str(row.get("smtp", ""))
        return str(found[0].get("smtp", "")) if found else "(default store)"

    def knows_account(self, wanted: str) -> bool | None:
        """True present, False absent, **None means Outlook could not be asked**.

        None is falsy, so `if knows_account(x)` behaves as before. Code that
        needs to tell "this mailbox is not in the profile" apart from "Outlook
        did not answer" must test `is None` - and it matters: reporting a
        timeout as a missing mailbox is how a working mailbox gets declared
        absent."""
        found = self.accounts()
        if not self.accounts_known:
            return None
        target = (wanted or "").strip().lower()
        return any(
            target in (str(r.get("smtp", "")).lower(), str(r.get("display_name", "")).lower())
            for r in found
        )

    def account_status(self, wanted: str) -> str:
        """"present", "absent", or "unknown". For anything a person will read."""
        answer = self.knows_account(wanted)
        if answer is None:
            return "unknown"
        return "present" if answer else "absent"

    # ---- capability reporting -----------------------------------------

    def probe(self) -> dict:
        """Cheap availability check. Does NOT start Outlook."""
        if not self.enabled:
            return {
                "available": False,
                "live_connection": False,
                "blocker": "disabled in configuration",
                "account": self.account,
            }
        script = (
            "$k='HKLM:\\SOFTWARE\\Classes\\Outlook.Application';"
            "$p='HKCU:\\SOFTWARE\\Microsoft\\Office\\16.0\\Outlook\\Profiles';"
            "$o=[ordered]@{com=(Test-Path $k);profiles=(Test-Path $p)};"
            "$o|ConvertTo-Json -Compress"
        )
        ran, out, _ = self._powershell(script, timeout=30)
        try:
            payload = json.loads(json_safe(out or "{}")[0])
        except json.JSONDecodeError:
            payload = {}
        registered = bool(payload.get("com")) and bool(payload.get("profiles"))
        return {
            "available": registered,
            "live_connection": bool(self.last_connected_at) and not self.last_error,
            "blocker": "" if registered else "Outlook is not installed or has no profile",
            "last_connected_at": self.last_connected_at,
            "last_error": self.last_error,
            "account": self.account or "(default store)",
        }
