"""Command-line interface for Assistant Research.

    py -m assistant_research brief Data\\brief_northbound_lane.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import CONFIDENCE_MEANING, Confidence, analyze, topics_in
from .authority import (
    AUTHORITY_STATEMENT,
    AuthorityError,
    Recommendation,
    find_authority_claims,
)
from .record import (
    RecordError,
    ResearchRecord,
    load_brief,
    load_sources,
    record_from_brief,
    resolve_data_root,
)
from .sources import SourceError

DIVIDER = "-" * 72


def _resolve(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.exists():
        return candidate
    fallback = resolve_data_root(None) / path_text
    if fallback.exists():
        return fallback
    raise RecordError("file not found: " + str(path_text))


def cmd_brief(args) -> int:
    record = record_from_brief(load_brief(_resolve(args.path)))
    print(json.dumps(record.to_dict(), indent=2) if args.json else record.render())
    return 0


def cmd_analyze(args) -> int:
    sources = load_sources(_resolve(args.path))
    record = ResearchRecord.build(
        question=args.question or "(no question stated)",
        scope=args.scope or "",
        sources=sources,
    )
    print(json.dumps(record.to_dict(), indent=2) if args.json else record.render())
    return 0


def cmd_sources(args) -> int:
    sources = load_sources(_resolve(args.path))
    if args.json:
        print(json.dumps([s.to_dict() for s in sources], indent=2))
        return 0
    print(DIVIDER)
    print("SOURCES  ({0})".format(len(sources)))
    print(DIVIDER)
    for source in sources:
        print("  {0:<10} {1}".format(source.source_id, source.citation()))
        print("      standing: " + source.standing)
        print("      approved company truth: " + str(source.is_approved_company_truth))
        for claim in source.claims:
            marker = "supports   " if claim.supports else "CONTRADICTS"
            print("      " + marker + "  [" + claim.topic + "] " + claim.statement)
    print()
    print("  " + AUTHORITY_STATEMENT)
    return 0


def cmd_topics(args) -> int:
    sources = load_sources(_resolve(args.path))
    found = topics_in(sources)
    if args.json:
        print(json.dumps(found, indent=2))
        return 0
    print(DIVIDER)
    print("TOPICS  ({0})".format(len(found)))
    print(DIVIDER)
    for topic in found:
        print("  " + topic)
    return 0


def cmd_uncertainties(args) -> int:
    record = record_from_brief(load_brief(_resolve(args.path)))
    if args.json:
        print(json.dumps(record.uncertainties, indent=2))
        return 0
    print(DIVIDER)
    print("UNCERTAINTIES  ({0})".format(len(record.uncertainties)))
    print(DIVIDER)
    for item in record.uncertainties:
        print()
        print("  " + item["topic"] + "  [" + item["confidence"] + "]")
        print("    " + item["uncertainty"])
    if record.contested:
        print()
        print("  " + str(len(record.contested)) + " topic(s) are CONTESTED and not settled.")
    return 0


def cmd_check(args) -> int:
    """Check text for language that claims authority research does not have."""
    text = args.text
    found = find_authority_claims(text)
    if args.json:
        print(json.dumps({"text": text, "refused_phrases": found, "allowed": not found}, indent=2))
        return 0 if not found else 1
    print(DIVIDER)
    print("AUTHORITY CHECK")
    print(DIVIDER)
    print("  text     " + text)
    if found:
        print("  RESULT   REFUSED")
        print("  reason   claims authority research does not have")
        for phrase in found:
            print('             found: "' + phrase + '"')
        print()
        print("  " + AUTHORITY_STATEMENT)
        return 1
    print("  RESULT   allowed as a recommendation")
    print()
    print("  " + AUTHORITY_STATEMENT)
    return 0


def cmd_authority(args) -> int:
    info = {
        "authority": AUTHORITY_STATEMENT,
        "may_recommend": True,
        "may_approve": False,
        "may_decide": False,
        "may_alter_doctrine": False,
        "may_accept_or_dispatch_loads": False,
        "may_commit_money": False,
        "may_send_communications": False,
        "has_network_access": False,
        "fetches_sources": False,
        "final_authority": "Mike Zachary",
    }
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    print(DIVIDER)
    print("ASSISTANT RESEARCH AUTHORITY")
    print(DIVIDER)
    for key, value in info.items():
        if key == "authority":
            continue
        print("  {0:<32} {1}".format(key, value))
    print()
    print("  " + AUTHORITY_STATEMENT)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assistant-research",
        description=(
            "Assistant Research - analysis, findings, recommendations, "
            "uncertainties, source reporting. Workstream 5."
        ),
    )
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_brief = sub.add_parser("brief", help="Build a full research record from a brief.")
    p_brief.add_argument("path")
    p_brief.set_defaults(func=cmd_brief)

    p_analyze = sub.add_parser("analyze", help="Analyze a source file.")
    p_analyze.add_argument("path")
    p_analyze.add_argument("--question", default=None)
    p_analyze.add_argument("--scope", default=None)
    p_analyze.set_defaults(func=cmd_analyze)

    p_sources = sub.add_parser("sources", help="List supplied sources and their standing.")
    p_sources.add_argument("path")
    p_sources.set_defaults(func=cmd_sources)

    p_topics = sub.add_parser("topics", help="List topics the sources speak to.")
    p_topics.add_argument("path")
    p_topics.set_defaults(func=cmd_topics)

    p_unc = sub.add_parser("uncertainties", help="What is not known, per topic.")
    p_unc.add_argument("path")
    p_unc.set_defaults(func=cmd_uncertainties)

    p_check = sub.add_parser("check", help="Check text for authority claims.")
    p_check.add_argument("text")
    p_check.set_defaults(func=cmd_check)

    sub.add_parser("authority", help="What this component may and may not do.").set_defaults(
        func=cmd_authority
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (RecordError, SourceError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    except AuthorityError as error:
        print("REFUSED: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
