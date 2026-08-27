"""Command-line interface for Assistant Memory.

    py -m assistant_memory list
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta

from .clock import FixedClock, SystemClock
from .record import RECORD_FIELDS, RetentionState
from .retention import Operation, RetentionEngine, RetentionError
from .store import MemoryStore, StoreError

DIVIDER = "-" * 68


def build_engine(args) -> RetentionEngine:
    store = MemoryStore(getattr(args, "folder_root", None))
    advance = getattr(args, "advance_hours", 0.0) or 0.0
    clock = (
        FixedClock(SystemClock().now() + timedelta(hours=advance))
        if advance
        else SystemClock()
    )
    return RetentionEngine(store=store, clock=clock)


def render_record(record) -> str:
    lines = [DIVIDER, "RETENTION RECORD  " + record.record_id, DIVIDER]
    for name in RECORD_FIELDS:
        if name == "record_id":
            continue
        value = getattr(record, name)
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value) if value else "(none)"
        if value in (None, ""):
            value = "(none)"
        lines.append("  {0:<22} {1}".format(name, value))
    if record.state == RetentionState.TEMPORARY:
        lines.append("")
        lines.append("  NOTICE: temporary. This will expire unless preserved.")
    elif record.state in RetentionState.NON_EXPIRING:
        lines.append("")
        lines.append("  NOTICE: held locally in this workstream's store.")
        lines.append("          Not routed anywhere. Nothing was produced.")
    return "\n".join(lines)


def render_table(records, title: str) -> str:
    lines = [DIVIDER, title + "  ({0} record(s))".format(len(records)), DIVIDER]
    if not records:
        lines.append("  (none)")
        return "\n".join(lines)
    lines.append(
        "  {0:<28} {1:<12} {2:<7} {3:<26} {4}".format(
            "RECORD_ID", "STATE", "LEVEL", "EXPIRES_AT (UTC)", "DRIVER_REQUEST"
        )
    )
    for record in records:
        lines.append(
            "  {0:<28} {1:<12} {2:<7} {3:<26} {4}".format(
                record.record_id,
                record.state,
                record.interaction_level.replace("LEVEL_", "L"),
                record.expires_at or "(no expiration)",
                (record.driver_request or "(purged)")[:40],
            )
        )
    return "\n".join(lines)


def render_result(result) -> str:
    lines = [
        DIVIDER,
        "OPERATION  " + result.operation,
        DIVIDER,
        "  record                 " + result.record_id,
        "  state                  " + result.previous_state + " -> " + result.new_state,
        "  interaction_level      " + result.previous_level + " -> " + result.new_level,
        "  expires_at             " + str(result.expires_at or "(no expiration)"),
    ]
    if result.changes:
        lines.append("  changes:")
        for change in result.changes:
            lines.append("    - " + change)
    lines.append("")
    lines.append("  NOTICE: " + result.notice)
    return "\n".join(lines)


# ---- subcommands --------------------------------------------------------


def cmd_new(args) -> int:
    engine = build_engine(args)
    record = engine.create(
        driver_request=args.request,
        assistant_response=args.response,
        source_channel=args.channel,
    )
    print(json.dumps(record.to_dict(), indent=2) if args.json else render_record(record))
    return 0


def cmd_op(args) -> int:
    engine = build_engine(args)
    options = {}
    for name in ("related_load", "related_mission", "destination"):
        value = getattr(args, name, None)
        if value:
            options[name] = value
    if args.operation == Operation.DELETE and getattr(args, "reason", None):
        options["reason"] = args.reason
    try:
        result = engine.apply(args.record_id, args.operation, **options)
    except (RetentionError, StoreError) as error:
        print("REFUSED: " + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(render_result(result))
        print()
        print(render_record(engine.get(args.record_id)))
    return 0


def cmd_show(args) -> int:
    engine = build_engine(args)
    try:
        record = engine.get(args.record_id)
    except StoreError as error:
        print("NOT FOUND: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(record.to_dict(), indent=2) if args.json else render_record(record))
    return 0


def cmd_list(args) -> int:
    engine = build_engine(args)
    expired = engine.sweep()
    records = engine.store.list_active(state=args.state)
    if args.json:
        print(json.dumps({
            "expired_during_this_sweep": [r.record_id for r in expired],
            "active": [r.to_dict() for r in records],
        }, indent=2))
        return 0
    if expired:
        print("Swept {0} record(s) into EXPIRED before listing.".format(len(expired)))
    print(render_table(records, "ACTIVE RETENTION SET"))
    return 0


def cmd_expired(args) -> int:
    engine = build_engine(args)
    records = engine.list_expired()
    print(
        json.dumps([r.to_dict() for r in records], indent=2)
        if args.json
        else render_table(records, "EXPIRED (absent from active, not promoted)")
    )
    return 0


def cmd_deleted(args) -> int:
    engine = build_engine(args)
    records = engine.list_deleted()
    print(
        json.dumps([r.to_dict() for r in records], indent=2)
        if args.json
        else render_table(records, "DELETED (tombstones, content purged)")
    )
    return 0


def cmd_sweep(args) -> int:
    engine = build_engine(args)
    expired = engine.sweep()
    now = engine.clock.now()
    if args.json:
        print(json.dumps({
            "swept_at": now.isoformat(),
            "simulated_advance_hours": args.advance_hours or 0.0,
            "expired": [r.record_id for r in expired],
        }, indent=2))
        return 0
    label = (
        "SIMULATED clock advanced {0} hour(s)".format(args.advance_hours)
        if args.advance_hours
        else "real time"
    )
    print(DIVIDER)
    print("SWEEP  (" + label + ")")
    print("  evaluated at (UTC)     " + now.isoformat())
    print("  expired this sweep     " + str(len(expired)))
    print(DIVIDER)
    for record in expired:
        print("  " + record.record_id + "  -> EXPIRED  (content purged, not promoted)")
    if not expired:
        print("  (nothing reached its expiration)")
    return 0


def cmd_doctor(args) -> int:
    store = MemoryStore(getattr(args, "folder_root", None))
    print(DIVIDER)
    print("ASSISTANT MEMORY BOUNDARY CHECK")
    print(DIVIDER)
    print("  folder root            " + str(store.folder_root))
    print("  data store             " + str(store.data_root))
    blocked = False
    try:
        store.assert_within_folder("C:/Windows/Temp/should_never_write.json")
    except StoreError:
        blocked = True
    print("  writes outside blocked " + str(blocked))
    records = store.list_all()
    stray = [
        r for r in records
        if not str(store.path_for(r.record_id, r.state)).startswith(str(store.folder_root))
    ]
    print("  records on disk        " + str(len(records)))
    print("  records outside folder " + str(len(stray)))
    print("  network modules        none (stdlib only)")
    print("  routing / printing / sending   none implemented")
    return 0 if blocked and not stray else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assistant-memory",
        description="Assistant Memory - Sandbox retention. Workstream 2.",
    )
    parser.add_argument("--folder-root", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="Create a temporary Level 1 record.")
    p_new.add_argument("--request", required=True)
    p_new.add_argument("--response", default=None)
    p_new.add_argument("--channel", default="local")
    p_new.set_defaults(func=cmd_new)

    for name, help_text in (
        ("level-1", "Hold temporarily; reset the three-hour window."),
        ("level-2", "Preserve as SAVED for parked review."),
        ("level-3", "Preserve as FORMAL."),
        ("print-ready", "Preserve as PRINT_READY. Does not change the level."),
        ("delete", "Delete: purge content, leave the active set."),
    ):
        operation = name.upper().replace("-", "_")
        p = sub.add_parser(name, help=help_text)
        p.add_argument("record_id")
        if operation in ("LEVEL_2", "LEVEL_3", "PRINT_READY"):
            p.add_argument("--related-load", dest="related_load", default=None)
            p.add_argument("--related-mission", dest="related_mission", default=None)
            p.add_argument("--destination", default=None)
        if operation == "DELETE":
            p.add_argument("--reason", default=None)
        p.set_defaults(func=cmd_op, operation=operation)

    p_show = sub.add_parser("show", help="Show one record in full.")
    p_show.add_argument("record_id")
    p_show.set_defaults(func=cmd_show)

    p_list = sub.add_parser("list", help="List the active set. Sweeps first.")
    p_list.add_argument("--state", default=None, choices=list(RetentionState.ALL))
    p_list.set_defaults(func=cmd_list)

    sub.add_parser("expired", help="List expired tombstones.").set_defaults(func=cmd_expired)
    sub.add_parser("deleted", help="List deleted tombstones.").set_defaults(func=cmd_deleted)

    p_sweep = sub.add_parser("sweep", help="Expire whatever has reached its time.")
    p_sweep.add_argument("--advance-hours", type=float, default=0.0)
    p_sweep.set_defaults(func=cmd_sweep)

    sub.add_parser("doctor", help="Boundary and containment self-check.").set_defaults(
        func=cmd_doctor
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "advance_hours"):
        args.advance_hours = 0.0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
