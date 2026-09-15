"""`python -m dispatch_governance` — what governs this, and has it moved?

Three commands, and the exit codes are the part CI reads:

    show <repo>     what a builder starting in that repository must follow
    answer <q>      which document decides one specific question
    check           compare every registered document against the checkouts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dispatch_governance.drift import blocking, check_drift, render_drift
from dispatch_governance.registry import DEFAULT_REGISTRY, load_registry


def _cmd_show(args) -> int:
    registry = load_registry(args.registry)
    binding = registry.binding_for(args.repo)
    print(f"\n  Current authority for {args.repo}:\n")
    if not binding:
        print("    Nothing in this repository is CURRENT governance.")
        print(f"    The programme authority is {registry.authority}.\n")
    for doc in binding:
        print(f"    {doc.doc_id}")
        print(f"      {doc.repo}/{doc.path}")
        print(f"      scope: {doc.scope}")
        if doc.note:
            print(f"      note:  {doc.note}")
    stale = [d for d in registry.for_repo(args.repo) if d.status == "SUPERSEDED"]
    if stale:
        print("\n    Superseded documents still present in this repository:")
        for doc in stale:
            print(f"      {doc.path}  ->  superseded by {doc.superseded_by}")
        print("    They are history. They do not authorise code.")
    print()
    return 0


def _cmd_answer(args) -> int:
    registry = load_registry(args.registry)
    doc = registry.answer(args.question)
    if doc is None:
        print(f"  No registered document answers {args.question!r}.")
        print("  Registered questions:")
        for question in sorted(registry.answers):
            print(f"    {question}")
        return 1
    print(f"\n  {args.question}\n")
    print(f"    {doc.doc_id}  [{doc.status}]")
    print(f"    {doc.repo}/{doc.path}")
    if doc.note:
        print(f"    {doc.note}")
    print()
    return 0


def _cmd_check(args) -> int:
    registry = load_registry(args.registry)
    findings = check_drift(registry, args.workspace, require_pointer=not args.no_pointer_check)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print(render_drift(findings))
    return 1 if blocking(findings) else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dispatch_governance",
        description="What governs this repository, and has it drifted?",
    )
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    sub = parser.add_subparsers(dest="command", required=True)

    p_show = sub.add_parser("show", help="what a builder in this repository must follow")
    p_show.add_argument("repo")
    p_show.set_defaults(func=_cmd_show)

    p_answer = sub.add_parser("answer", help="which document decides one question")
    p_answer.add_argument("question")
    p_answer.set_defaults(func=_cmd_answer)

    p_check = sub.add_parser("check", help="compare the registry against local checkouts")
    p_check.add_argument("workspace", type=Path, help="directory holding one clone per repository")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--no-pointer-check", action="store_true",
                         help="do not require a GOVERNANCE.md beside a superseded document")
    p_check.set_defaults(func=_cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
