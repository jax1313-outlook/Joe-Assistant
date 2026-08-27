"""Command-line interface for Assistant Outlook.

    py -m assistant_outlook brief
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timezone

from .awareness import Awareness, AwarenessError
from .models import parse_moment, to_iso
from .provider import JsonFileProvider, ProviderError, resolve_data_root

DIVIDER = "-" * 72
READ_ONLY_NOTICE = (
    "Read only. This component cannot send, reply, accept, decline, schedule, "
    "modify, or approve anything. Every decision stays with Mike Zachary."
)


def build_awareness(args) -> Awareness:
    return Awareness(JsonFileProvider(getattr(args, "data_root", None)))


def _when(args):
    value = getattr(args, "now", None)
    return parse_moment(value) if value else None


def _clock(moment) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M") + " UTC"


def cmd_brief(args) -> int:
    awareness = build_awareness(args)
    when = _when(args)
    brief = awareness.day_brief(when)
    if args.json:
        print(json.dumps(brief.to_dict(), indent=2))
        return 0
    print(DIVIDER)
    print("DAY BRIEF  " + brief.date)
    print(DIVIDER)
    if not brief.events:
        print("  Nothing on the calendar for this day.")
    for event in brief.events:
        print(
            "  {0}  {1:<32} {2}".format(
                event["start"][11:16], event["subject"][:32], event["location"]
            )
        )
        print(
            "      {0} min   response: {1}".format(
                event["duration_minutes"], event["response_status"]
            )
        )
    if brief.conflicts:
        print()
        print("  CONFLICTS")
        for conflict in brief.conflicts:
            print(
                "    {0} overlaps {1} by {2} min".format(
                    conflict["first_subject"],
                    conflict["second_subject"],
                    conflict["overlap_minutes"],
                )
            )
    if brief.unanswered_invitations:
        print()
        print("  NO RESPONSE RECORDED  (this component cannot answer them)")
        for event in brief.unanswered_invitations:
            print("    " + event["subject"] + "  [" + event["response_status"] + "]")
    print()
    print("  " + READ_ONLY_NOTICE)
    return 0


def cmd_next(args) -> int:
    awareness = build_awareness(args)
    when = _when(args)
    current = awareness.current_event(when)
    upcoming = awareness.next_event(when)
    if args.json:
        print(json.dumps({
            "current": current.to_dict() if current else None,
            "next": upcoming.to_dict() if upcoming else None,
        }, indent=2))
        return 0
    print(DIVIDER)
    print("NEXT ON THE CALENDAR")
    print(DIVIDER)
    if current:
        print("  happening now   " + current.subject)
        print("                  until " + _clock(current.end))
    else:
        print("  happening now   nothing")
    if upcoming:
        print("  next            " + upcoming.subject)
        print("                  starts " + _clock(upcoming.start))
        print("                  " + (upcoming.location or "(no location)"))
        print("                  response: " + upcoming.response_status)
    else:
        print("  next            nothing scheduled")
    return 0


def cmd_events(args) -> int:
    awareness = build_awareness(args)
    events = awareness.events()
    if args.json:
        print(json.dumps([e.to_dict() for e in events], indent=2))
        return 0
    print(DIVIDER)
    print("CALENDAR  ({0} event(s))".format(len(events)))
    print(DIVIDER)
    for event in events:
        print(
            "  {0:<10} {1}  {2:<34} {3}".format(
                event.event_id,
                to_iso(event.start)[:16].replace("T", " "),
                event.subject[:34],
                event.response_status,
            )
        )
    conflicts = awareness.conflicts()
    if conflicts:
        print()
        print("  CONFLICTS ({0})".format(len(conflicts)))
        for conflict in conflicts:
            print(
                "    {0} <-> {1}   {2} min".format(
                    conflict.first_id, conflict.second_id, conflict.overlap_minutes
                )
            )
    return 0


def cmd_mail(args) -> int:
    awareness = build_awareness(args)
    messages = awareness.unread() if args.unread else awareness.messages()
    if args.json:
        print(json.dumps([m.to_dict() for m in messages], indent=2))
        return 0
    print(DIVIDER)
    print(("UNREAD MAIL" if args.unread else "MAIL") + "  ({0})".format(len(messages)))
    print(DIVIDER)
    for message in messages:
        print(
            "  {0:<10} {1}  {2:<38}".format(
                message.message_id,
                to_iso(message.received)[:16].replace("T", " "),
                message.subject[:38],
            )
        )
        print(
            "      from {0}   {1}   {2}".format(
                message.sender,
                "unread" if not message.is_read else "read",
                message.importance,
            )
        )
    print()
    print("  " + READ_ONLY_NOTICE)
    return 0


def cmd_attention(args) -> int:
    awareness = build_awareness(args)
    flags = awareness.flagged(_when(args))
    if args.json:
        print(json.dumps([f.to_dict() for f in flags], indent=2))
        return 0
    print(DIVIDER)
    print("MAIL WORTH A LOOK  ({0})".format(len(flags)))
    print(DIVIDER)
    if not flags:
        print("  Nothing flagged.")
    for flag in flags:
        print()
        print("  " + flag.subject)
        print("    from " + flag.sender + "   " + flag.received[:16].replace("T", " "))
        print("    noticed because: " + "; ".join(flag.reasons))
        print("    decided: False    acted on: False")
    print()
    print("  These are pattern matches on subject and preview text, not")
    print("  judgements. Nothing here has been answered, accepted, or decided.")
    return 0


def cmd_contacts(args) -> int:
    awareness = build_awareness(args)
    found = awareness.find_contacts(args.query) if args.query else awareness.contacts()
    if args.json:
        print(json.dumps([c.to_dict() for c in found], indent=2))
        return 0
    print(DIVIDER)
    print("CONTACTS  ({0})".format(len(found)))
    print(DIVIDER)
    for contact in found:
        print("  {0:<10} {1:<22} {2}".format(
            contact.contact_id, contact.display_name, contact.email
        ))
        print("      {0}   {1}   {2}".format(
            contact.company, contact.role, contact.phone
        ))
    return 0


def cmd_status(args) -> int:
    awareness = build_awareness(args)
    status = awareness.status()
    if args.json:
        print(json.dumps(status, indent=2))
        return 0
    print(DIVIDER)
    print("ASSISTANT OUTLOOK STATUS")
    print(DIVIDER)
    for key in (
        "provider", "data_root", "data_root_exists", "source", "live_connection",
        "events", "messages", "contacts",
    ):
        print("  {0:<24} {1}".format(key, status.get(key)))
    if status.get("missing_files"):
        print("  missing files            " + ", ".join(status["missing_files"]))
    if status.get("skipped_entries"):
        print("  skipped entries          " + str(len(status["skipped_entries"])))
        for note in status["skipped_entries"]:
            print("      " + note)
    print(DIVIDER)
    for key in (
        "can_send", "can_reply", "can_schedule", "can_modify",
        "can_accept_or_decline", "has_approval_authority",
    ):
        print("  {0:<24} {1}".format(key, status.get(key)))
    print()
    print("  " + READ_ONLY_NOTICE)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assistant-outlook",
        description=(
            "Assistant Outlook - read-only calendar, email, and contact "
            "awareness. Workstream 4."
        ),
    )
    parser.add_argument("--data-root", dest="data_root", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--now", default=None,
        help="Evaluate as at this ISO-8601 moment instead of the real clock.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("brief", help="What one day looks like.").set_defaults(func=cmd_brief)
    sub.add_parser("next", help="What is happening now and next.").set_defaults(func=cmd_next)
    sub.add_parser("events", help="All calendar events and conflicts.").set_defaults(func=cmd_events)

    p_mail = sub.add_parser("mail", help="Mail, newest first.")
    p_mail.add_argument("--unread", action="store_true")
    p_mail.set_defaults(func=cmd_mail)

    sub.add_parser("attention", help="Mail worth a look, with reasons.").set_defaults(
        func=cmd_attention
    )

    p_contacts = sub.add_parser("contacts", help="List or search contacts.")
    p_contacts.add_argument("query", nargs="?", default=None)
    p_contacts.set_defaults(func=cmd_contacts)

    sub.add_parser("status", help="Provider and capability self-check.").set_defaults(
        func=cmd_status
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (AwarenessError, ProviderError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
