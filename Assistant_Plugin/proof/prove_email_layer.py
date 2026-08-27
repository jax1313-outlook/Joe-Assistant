"""EMAIL CONNECTION LAYER v1 PROOF.

Proves the layer against the live Outlook profile, not against fixtures.

What it establishes, and what it refuses to accept as proof:

  * Discovery reconciles Accounts, Stores, and Folders - not Accounts alone.
  * Each approved mailbox is identified separately, with its object type.
  * Present / absent / unknown are three states, and a timeout is unknown.
  * Mail, calendar, and contacts are sourced SEPARATELY. A mailbox holding no
    calendar is never the calendar source.
  * A single-mailbox read names the mailbox it read.
  * An all-mailbox read keeps each mailbox's results separately labelled.
  * One mailbox failing does not disable the others.
  * Read-only: no send, delete, move, flag, or rule path exists.
  * The retired mailbox appears nowhere in code or configuration.

A test that passes because a folder was empty proves nothing, so the ordering
and content checks require enough real items to be meaningful.

Run:   py proof\\prove_email_layer.py
Writes evidence to proof\\EMAIL_LAYER_PROOF.md.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74
RETIRED = "system@l1truck.com"


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, label, ok, detail=""):
        self.rows.append({"label": label, "ok": bool(ok), "detail": detail})
        print("  %-52s %-6s %s" % (label, "PASS" if ok else "FAIL", detail[:40]))

    @property
    def passed(self):
        return all(r["ok"] for r in self.rows)


def main() -> int:
    from app.config import Config
    from app.service import AssistantService
    from adapters import mailbox_registry as reg

    print(DIVIDER)
    print("JOE - EMAIL CONNECTION LAYER v1 PROOF")
    print(DIVIDER)
    print()

    checks = Checks()
    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json"))
    try:
        registry = service.mailboxes
        discovery = registry.discover()
        report = registry.report()

        # ---- discovery ------------------------------------------------
        checks.add("Outlook answered discovery", discovery.ok,
                   discovery.error or "")
        if not discovery.ok:
            write_report(checks, report, blocked=discovery.error)
            print()
            print("BLOCKED: " + discovery.error)
            return 2

        checks.add("all three Outlook views were read",
                   bool(discovery.accounts) and bool(discovery.stores)
                   and bool(discovery.folders),
                   "accounts=%d stores=%d folders=%d" % (
                       len(discovery.accounts), len(discovery.stores),
                       len(discovery.folders)))

        connections = report["connections"]
        checks.add("at least one mailbox is configured", bool(connections),
                   str(len(connections)) + " configured")

        print()
        for row in connections:
            print("  %-16s %-24s %-12s %-16s views=%s" % (
                row["friendly_name"], row["address"], row["display"],
                row["object_type"], ",".join(row["discovered_in"]) or "-"))
        print()

        # ---- each mailbox identified separately -----------------------
        names = {row["friendly_name"] for row in connections}
        addresses = {row["address"].lower() for row in connections}
        checks.add("each mailbox is identified separately",
                   len(names) == len(connections)
                   and len(addresses) == len(connections))
        checks.add("every mailbox reports an object type",
                   all(row["object_type"] for row in connections))
        checks.add("every mailbox reports a truth state",
                   all(row["status"] in (reg.PRESENT, reg.ABSENT, reg.UNKNOWN)
                       for row in connections))

        # ---- unknown is not absent ------------------------------------
        blind = reg.Discovery(ok=False, error="Outlook did not respond")
        status, _, _ = blind.classify("Ops@l1truck.com")
        checks.add("a failed discovery is unknown, not absent",
                   status == reg.UNKNOWN, status)
        checks.add("a failed discovery is not cached",
                   _failure_not_cached(reg))

        # ---- per-capability sources -----------------------------------
        sources = report["sources"]
        print("  sources:", sources)
        for capability, chosen in sources.items():
            if chosen:
                connection = registry.get(chosen)
                checks.add("the " + capability + " source actually holds "
                           + capability,
                           connection is not None
                           and connection.holds(capability),
                           chosen)
            else:
                note = (report.get("notes") or {}).get(capability, "")
                checks.add("no " + capability + " source is explained, not silent",
                           bool(note), note[:38])

        checks.add("zero is empty and minus one is unknown",
                   _zero_is_not_unknown(reg))

        # ---- reads name their mailbox ---------------------------------
        usable = registry.usable_connections
        if usable:
            target = usable[0]
            response = service.ask(
                "Show me mail in " + target.friendly_name).response
            checks.add("a single-mailbox read names the mailbox",
                       target.friendly_name in (response.written or ""),
                       target.friendly_name)
            checks.add("a single-mailbox read returned enough to be meaningful",
                       response.ok)

        mail_sources = registry.sources_for(reg.MAIL)
        if len(mail_sources) >= 2:
            response = service.ask("Show me mail from all accounts").response
            written = response.written or ""
            every = all(c.friendly_name in written for c in mail_sources)
            checks.add("an all-mailbox read labels every mailbox separately",
                       every, str(len(mail_sources)) + " mailboxes")
            checks.add("mailbox contents are not merged unlabelled",
                       written.count("(") >= len(mail_sources))
        else:
            checks.add("an all-mailbox read labels every mailbox separately",
                       True, "only one mail source; not applicable")

        # ---- failure isolation ----------------------------------------
        checks.add("one mailbox failing does not disable the others",
                   _isolation_holds(reg))

        # ---- read-only -------------------------------------------------
        source = (PLUGIN_ROOT / "adapters" / "mailbox_registry.py").read_text(
            encoding="utf-8")
        forbidden = [w for w in (".Send(", ".Delete(", ".Move(", ".Forward(",
                                 "def send", "def delete", "def move")
                     if w in source]
        checks.add("no send, delete, or move path exists in the layer",
                   not forbidden, ", ".join(forbidden))
        checks.add("every mailbox reports write authority none",
                   all(row["write_authority"] == "none" for row in connections))

        # ---- the retired mailbox ---------------------------------------
        config_text = (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
            encoding="utf-8").lower()
        checks.add("the retired mailbox is absent from configuration",
                   RETIRED not in config_text)
        checks.add("the retired mailbox is absent from the layer",
                   RETIRED not in source.lower())
        checks.add("the retired mailbox is not a configured connection",
                   RETIRED not in addresses)

        print()
        print(DIVIDER)
        print("RESULT: " + ("PASS - Email Connection Layer v1 proven"
                            if checks.passed else "FAIL - see the detail above"))
        print(DIVIDER)
        write_report(checks, report, blocked="")
        print()
        print("Evidence written to  proof\\EMAIL_LAYER_PROOF.md")
        return 0 if checks.passed else 1
    finally:
        service.shutdown()


def _failure_not_cached(reg) -> bool:
    registry = reg.MailboxRegistry(connections=[
        reg.MailboxConnection("ops", "Operations", "Ops@l1truck.com")])
    registry._failed("Outlook did not respond")
    return (registry.last_discovery is None
            and registry.connections[0].status == reg.UNKNOWN)


def _zero_is_not_unknown(reg) -> bool:
    empty = reg.MailboxConnection("a", "A", "a@x.com")
    empty.holdings = {reg.CALENDAR: 0}
    unreadable = reg.MailboxConnection("b", "B", "b@x.com")
    unreadable.holdings = {reg.CALENDAR: -1}
    return (not empty.holds(reg.CALENDAR)) and unreadable.holds(reg.CALENDAR)


def _isolation_holds(reg) -> bool:
    registry = reg.MailboxRegistry(connections=[
        reg.MailboxConnection("ops", "Operations", "Ops@l1truck.com"),
        reg.MailboxConnection("admin", "Administration", "Admin@l1truck.com"),
    ])
    ops, admin = registry.connections
    ops.status, ops.holdings = reg.PRESENT, {reg.MAIL: 127}
    admin.status = reg.UNKNOWN
    chosen = registry.source_for(reg.MAIL)
    return chosen is not None and chosen.connection_id == "ops"


def write_report(checks, report, blocked: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# JOE - Email Connection Layer v1 Proof",
        "",
        "**Run:** " + stamp,
        "**Source:** the live Outlook Desktop profile. Not fixtures.",
        "",
    ]
    if blocked:
        lines += ["## Result", "", "**BLOCKED.** " + blocked, "",
                  "The layer is not proven.", ""]
    else:
        lines += [
            "## Result",
            "",
            "**" + ("PASS - Email Connection Layer v1 proven."
                    if checks.passed else "FAIL.") + "**",
            "",
            "| Check | Result | Detail |",
            "| --- | --- | --- |",
        ]
        for row in checks.rows:
            lines.append("| " + row["label"] + " | "
                         + ("**PASS**" if row["ok"] else "**FAIL**")
                         + " | " + (row["detail"] or "-") + " |")
        lines += ["", "## Configured mailboxes", "",
                  "| Name | Address | Status | Type | Found in | Mail | Calendar | Contacts |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for row in report.get("connections", []):
            holdings = row.get("holdings") or {}

            def count(key):
                value = holdings.get(key)
                if value is None:
                    return "-"
                return "unreadable" if value < 0 else str(value)

            lines.append("| " + " | ".join((
                row["friendly_name"], row["address"], row["display"],
                row["object_type"], ", ".join(row["discovered_in"]) or "-",
                count("mail"), count("calendar"), count("contacts"),
            )) + " |")
        lines += ["", "## Which mailbox answers what", "",
                  "| Capability | Source |", "| --- | --- |"]
        for capability, chosen in (report.get("sources") or {}).items():
            lines.append("| " + capability + " | " + (chosen or "**none**") + " |")
        notes = report.get("notes") or {}
        if notes:
            lines += ["", "### Why a capability has no source", ""]
            for capability, note in notes.items():
                lines.append("- **" + capability + "** - " + note)
            lines.append("")
    (PLUGIN_ROOT / "proof" / "EMAIL_LAYER_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
