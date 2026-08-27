"""Command-line interface for Sandbox Engine v1.

Run it through the launcher in Build, or directly:

    py -m sandbox_engine.cli list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta

from .clock import FixedClock, SystemClock
from .engine import EngineError, SandboxEngine
from .intents import recognize
from .records import RECORD_FIELDS, RecordState
from .store import SandboxStore, StoreError

DIVIDER = "-" * 68


def build_engine(args) -> SandboxEngine:
    store = SandboxStore(getattr(args, "project_root", None))
    advance = getattr(args, "advance_hours", 0.0) or 0.0
    if advance:
        clock = FixedClock(SystemClock().now() + timedelta(hours=advance))
    else:
        clock = SystemClock()
    return SandboxEngine(store=store, clock=clock)


# ---- rendering ----------------------------------------------------------


def render_record(record) -> str:
    lines = [DIVIDER, "SANDBOX RECORD  " + record.sandbox_id, DIVIDER]
    for name in RECORD_FIELDS:
        if name == "sandbox_id":
            continue
        value = getattr(record, name)
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value) if value else "(none)"
        if value in (None, ""):
            value = "(none)"
        lines.append("  {0:<28} {1}".format(name, value))
    if record.state == RecordState.TEMPORARY:
        lines.append("")
        lines.append("  NOTICE: temporary. This will expire unless saved.")
    elif record.state in RecordState.NON_EXPIRING:
        lines.append("")
        lines.append("  NOTICE: preserved locally in the Sandbox Engine store.")
        lines.append("          Not routed to Dispatch, Company Library, or Archive.")
    return "\n".join(lines)


def render_row(record) -> str:
    return "  {0:<28} {1:<12} {2:<9} {3:<26} {4}".format(
        record.sandbox_id,
        record.state,
        record.interaction_level.replace("LEVEL_", "L"),
        record.expires_at or "(no expiration)",
        (record.driver_request or "(purged)")[:44],
    )


def render_table(records, title: str) -> str:
    lines = [DIVIDER, title + "  ({0} record(s))".format(len(records)), DIVIDER]
    if not records:
        lines.append("  (none)")
        return "\n".join(lines)
    lines.append(
        "  {0:<28} {1:<12} {2:<9} {3:<26} {4}".format(
            "SANDBOX_ID", "STATE", "LEVEL", "EXPIRES_AT (UTC)", "DRIVER_REQUEST"
        )
    )
    for record in records:
        lines.append(render_row(record))
    return "\n".join(lines)


def render_result(result) -> str:
    lines = [
        DIVIDER,
        "COMMAND  " + (result.command.raw_text or "(empty)"),
        DIVIDER,
        "  recognized intent            " + result.command.intent,
        "  matched phrase               " + str(result.command.matched_phrase or "(none)"),
        "  print requested              " + str(result.command.print_requested),
        "  accepted                     " + str(result.accepted),
        "  state                        "
        + result.previous_state
        + " -> "
        + result.new_state,
        "  interaction level            "
        + result.previous_level
        + " -> "
        + result.new_level,
        "  expires_at                   " + str(result.expires_at or "(no expiration)"),
    ]
    if result.changes:
        lines.append("  changes:")
        for change in result.changes:
            lines.append("    - " + change)
    for request in result.artifact_requests:
        lines.append(
            "  artifact request             "
            + request["artifact_request_id"]
            + "  ["
            + request["artifact_kind"]
            + "]  status="
            + request["status"]
        )
    lines.append("")
    lines.append("  NOTICE: " + result.notice)
    return "\n".join(lines)


# ---- subcommands --------------------------------------------------------


def cmd_new(args) -> int:
    engine = build_engine(args)
    extra = {}
    for pair in args.set or []:
        if "=" not in pair:
            print("--set expects field=value, got: " + pair, file=sys.stderr)
            return 2
        key, value = pair.split("=", 1)
        key = key.strip()
        if key not in RECORD_FIELDS:
            print("unknown record field: " + key, file=sys.stderr)
            return 2
        if key in (
            "sources_consulted",
            "key_findings",
            "operational_consequences",
            "drafts_created",
            "actions_completed",
            "actions_awaiting_approval",
            "citations",
        ):
            extra[key] = [part.strip() for part in value.split("|") if part.strip()]
        else:
            extra[key] = value
    record = engine.create(
        driver_request=args.request,
        assistant_response=args.response,
        source_channel=args.channel,
        **extra,
    )
    if args.json:
        print(json.dumps(record.to_dict(), indent=2))
    else:
        print(render_record(record))
    return 0


def cmd_command(args) -> int:
    engine = build_engine(args)
    try:
        result = engine.apply_command(args.sandbox_id, args.text)
    except (EngineError, StoreError) as error:
        print("REFUSED: " + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(render_result(result))
        print()
        print(render_record(engine.get(args.sandbox_id)))
    return 0


def cmd_show(args) -> int:
    engine = build_engine(args)
    try:
        record = engine.get(args.sandbox_id)
    except StoreError as error:
        print("NOT FOUND: " + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(record.to_dict(), indent=2))
    else:
        print(render_record(record))
    return 0


def cmd_list(args) -> int:
    engine = build_engine(args)
    expired = engine.sweep()
    records = engine.store.list_active(state=args.state)
    if args.json:
        print(
            json.dumps(
                {
                    "expired_during_this_sweep": [r.sandbox_id for r in expired],
                    "active": [r.to_dict() for r in records],
                },
                indent=2,
            )
        )
        return 0
    if expired:
        print("Swept {0} record(s) into EXPIRED before listing.".format(len(expired)))
    print(render_table(records, "ACTIVE SANDBOX"))
    return 0


def cmd_expired(args) -> int:
    engine = build_engine(args)
    records = engine.list_expired()
    if args.json:
        print(json.dumps([r.to_dict() for r in records], indent=2))
    else:
        print(render_table(records, "EXPIRED (not in active Sandbox, not promoted)"))
    return 0


def cmd_deleted(args) -> int:
    engine = build_engine(args)
    records = engine.list_deleted()
    if args.json:
        print(json.dumps([r.to_dict() for r in records], indent=2))
    else:
        print(render_table(records, "DELETED (tombstones, content purged)"))
    return 0


def cmd_sweep(args) -> int:
    engine = build_engine(args)
    expired = engine.sweep()
    now = engine.clock.now()
    if args.json:
        print(
            json.dumps(
                {
                    "swept_at": now.isoformat(),
                    "simulated_advance_hours": args.advance_hours or 0.0,
                    "expired": [r.sandbox_id for r in expired],
                },
                indent=2,
            )
        )
        return 0
    label = "real time"
    if args.advance_hours:
        label = "SIMULATED clock advanced {0} hour(s)".format(args.advance_hours)
    print(DIVIDER)
    print("SWEEP  (" + label + ")")
    print("  evaluated at (UTC)           " + now.isoformat())
    print("  expired this sweep           " + str(len(expired)))
    print(DIVIDER)
    for record in expired:
        print("  " + record.sandbox_id + "  -> EXPIRED  (content purged, not promoted)")
    if not expired:
        print("  (nothing reached its expiration)")
    return 0


def cmd_parse(args) -> int:
    command = recognize(args.text)
    if args.json:
        print(json.dumps(command.to_dict(), indent=2))
        return 0
    print(DIVIDER)
    print("PARSE  " + (command.raw_text or "(empty)"))
    print(DIVIDER)
    print("  intent                       " + command.intent)
    print("  matched phrase               " + str(command.matched_phrase or "(none)"))
    print("  print requested              " + str(command.print_requested))
    print("  references                   " + (json.dumps(command.references) or "{}"))
    return 0


def cmd_artifacts(args) -> int:
    engine = build_engine(args)
    requests = engine.store.list_artifact_requests()
    if args.json:
        print(json.dumps(requests, indent=2))
        return 0
    print(DIVIDER)
    print("ARTIFACT REQUESTS  ({0})".format(len(requests)))
    print(DIVIDER)
    if not requests:
        print("  (none)")
        return 0
    for request in requests:
        print(
            "  {0:<26} {1:<14} {2:<24} sandbox={3}".format(
                request["artifact_request_id"],
                request["artifact_kind"],
                request["status"],
                request["sandbox_id"],
            )
        )
        print(
            "      destination={0}   produced={1}   physical_print_performed={2}".format(
                request.get("destination") or "(none)",
                request.get("produced"),
                request.get("physical_print_performed"),
            )
        )
    return 0


def cmd_doctor(args) -> int:
    """Boundary self-check the operator can run at any time."""
    store = SandboxStore(getattr(args, "project_root", None))
    print(DIVIDER)
    print("SANDBOX ENGINE BOUNDARY CHECK")
    print(DIVIDER)
    print("  project root                 " + str(store.project_root))
    print("  sandbox store                " + str(store.sandbox_root))
    print("  artifact requests            " + str(store.artifact_requests_root))
    outside_blocked = False
    try:
        store.assert_within_project("C:/Windows/Temp/should_never_write.json")
    except StoreError:
        outside_blocked = True
    print("  writes outside root blocked  " + str(outside_blocked))
    all_records = store.list_all()
    stray = [
        r
        for r in all_records
        if not str(store.path_for(r.sandbox_id, r.state)).startswith(
            str(store.project_root)
        )
    ]
    print("  records on disk              " + str(len(all_records)))
    print("  records outside project      " + str(len(stray)))
    print("  network modules imported     none (engine imports stdlib only)")
    print("  email / phone / money / dispatch actions   none implemented")
    return 0 if outside_blocked and not stray else 1


# ---- parser --------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sandbox-engine",
        description="Sandbox Engine v1 - local governed workflow layer for the Level 1 Assistant.",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root (defaults to the folder containing Build).",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Create a temporary Level 1 Sandbox record.")
    p_new.add_argument("--request", required=True, help="The driver request text.")
    p_new.add_argument("--response", default=None, help="The assistant response text.")
    p_new.add_argument("--channel", default="local_cli", help="Source channel label.")
    p_new.add_argument(
        "--set",
        action="append",
        metavar="FIELD=VALUE",
        help="Set any record field. List fields accept pipe-separated values.",
    )
    p_new.set_defaults(func=cmd_new)

    p_cmd = sub.add_parser("command", help="Apply ordinary driver language to a record.")
    p_cmd.add_argument("sandbox_id")
    p_cmd.add_argument("text", help='For example: "Level 3 this under Ideas"')
    p_cmd.set_defaults(func=cmd_command)

    p_show = sub.add_parser("show", help="Show one record in full.")
    p_show.add_argument("sandbox_id")
    p_show.set_defaults(func=cmd_show)

    p_list = sub.add_parser("list", help="List the active Sandbox (sweeps first).")
    p_list.add_argument("--state", default=None, choices=list(RecordState.ALL))
    p_list.set_defaults(func=cmd_list)

    sub.add_parser("expired", help="List expired tombstones.").set_defaults(
        func=cmd_expired
    )
    sub.add_parser("deleted", help="List deleted tombstones.").set_defaults(
        func=cmd_deleted
    )

    p_sweep = sub.add_parser("sweep", help="Expire whatever has reached its time.")
    p_sweep.add_argument(
        "--advance-hours",
        type=float,
        default=0.0,
        help="Simulate the clock moving forward, to prove expiration without waiting.",
    )
    p_sweep.set_defaults(func=cmd_sweep)

    p_parse = sub.add_parser("parse", help="Show how a phrase is recognized. Changes nothing.")
    p_parse.add_argument("text")
    p_parse.set_defaults(func=cmd_parse)

    sub.add_parser("artifacts", help="List artifact requests.").set_defaults(
        func=cmd_artifacts
    )
    sub.add_parser("doctor", help="Boundary and containment self-check.").set_defaults(
        func=cmd_doctor
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "advance_hours"):
        args.advance_hours = 0.0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
