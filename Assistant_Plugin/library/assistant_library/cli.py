"""Command-line interface for Assistant Library.

    py -m assistant_library search "mission visibility"
"""

from __future__ import annotations

import argparse
import json
import sys

from .library import ENV_ROOT, Library, LibraryError, resolve_root

DIVIDER = "-" * 72
READ_ONLY_NOTICE = (
    "Read only. This component never writes, edits, moves, or deletes a "
    "library document."
)


def open_library(args) -> Library:
    return Library(getattr(args, "root", None))


def cmd_index(args) -> int:
    try:
        library = open_library(args)
    except LibraryError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    report = library.report
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    print(DIVIDER)
    print("LIBRARY INDEX")
    print(DIVIDER)
    print("  root                   " + report.root)
    print("  documents indexed      " + str(report.indexed))
    print("  skipped (unsupported)  " + str(report.skipped_unsupported))
    print("  skipped (unreadable)   " + str(report.skipped_unreadable))
    for note in report.unreadable:
        print("      " + note)
    if report.truncated:
        print("  TRUNCATED: document limit reached; not everything was indexed.")
    print()
    print("  " + READ_ONLY_NOTICE)
    return 0


def cmd_list(args) -> int:
    try:
        library = open_library(args)
    except LibraryError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    documents = library.documents
    if args.json:
        print(json.dumps([d.to_dict() for d in documents], indent=2))
        return 0
    print(DIVIDER)
    print("LIBRARY DOCUMENTS  ({0})".format(len(documents)))
    print(DIVIDER)
    if not documents:
        print("  (none)")
        return 0
    print("  {0:<44} {1:<7} {2}".format("DOC_ID", "WORDS", "PATH"))
    for document in documents:
        print(
            "  {0:<44} {1:<7} {2}".format(
                document.doc_id, document.word_count, document.relative_path
            )
        )
    return 0


def cmd_search(args) -> int:
    try:
        library = open_library(args)
    except LibraryError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    hits = library.search(args.query, require_all=args.all, limit=args.limit)
    if args.json:
        print(json.dumps([h.to_dict() for h in hits], indent=2))
        return 0
    print(DIVIDER)
    print('SEARCH  "' + args.query + '"')
    print(DIVIDER)
    print("  root            " + str(library.root))
    print("  documents       " + str(len(library)))
    print("  matches         " + str(len(hits)))
    if args.all:
        print("  mode            every term required")
    print(DIVIDER)
    if not hits:
        print("  No document matched. Nothing was inferred or invented.")
        return 0
    for position, hit in enumerate(hits, start=1):
        print()
        print("  {0}. {1}   [score {2}]".format(position, hit.title, hit.score))
        print("     " + hit.relative_path)
        print("     doc_id: " + hit.doc_id)
        print(
            "     matched: "
            + (", ".join(hit.matched_terms) or "(none)")
            + ("   missing: " + ", ".join(hit.missing_terms) if hit.missing_terms else "")
        )
        for snippet in hit.snippets:
            print("     > " + snippet)
    return 0


def cmd_get(args) -> int:
    try:
        library = open_library(args)
        document = library.get(args.doc_id)
    except LibraryError as error:
        print("NOT FOUND: " + str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(document.to_dict(include_text=True), indent=2))
        return 0
    print(DIVIDER)
    print("DOCUMENT  " + document.title)
    print(DIVIDER)
    print("  doc_id        " + document.doc_id)
    print("  path          " + document.relative_path)
    print("  extension     " + document.extension)
    print("  size          " + str(document.size_bytes) + " bytes")
    print("  modified      " + document.modified_at)
    print("  words         " + str(document.word_count))
    print("  reference     " + document.reference())
    print(DIVIDER)
    text = document.text
    if args.lines and args.lines > 0:
        lines = text.splitlines()[: args.lines]
        text = "\n".join(lines)
        if len(document.text.splitlines()) > args.lines:
            text += "\n... (" + str(len(document.text.splitlines())) + " lines total)"
    print(text)
    return 0


def cmd_reference(args) -> int:
    try:
        library = open_library(args)
        reference = library.reference(args.doc_id)
    except LibraryError as error:
        print("NOT FOUND: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps({"doc_id": args.doc_id, "reference": reference}, indent=2)
          if args.json else reference)
    return 0


def cmd_doctor(args) -> int:
    root = resolve_root(getattr(args, "root", None))
    print(DIVIDER)
    print("ASSISTANT LIBRARY BOUNDARY CHECK")
    print(DIVIDER)
    print("  configured root        " + str(root))
    print("  root exists            " + str(root.exists()))
    print("  environment override   " + ENV_ROOT + "=" + str(__import__("os").environ.get(ENV_ROOT, "(unset)")))
    print("  access mode            READ ONLY")
    print("  write calls in package none")
    print("  network modules        none (stdlib only)")
    print("  email / calendar / voice / memory   none implemented")
    try:
        library = Library(root)
        print("  documents indexed      " + str(len(library)))
    except LibraryError as error:
        print("  documents indexed      unavailable: " + str(error))
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assistant-library",
        description="Assistant Library - read-only Company Library access. Workstream 3.",
    )
    parser.add_argument(
        "--root", default=None,
        help="Library root. Defaults to the sample corpus in this folder.",
    )
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("index", help="Index the root and report what was read.").set_defaults(
        func=cmd_index
    )
    sub.add_parser("list", help="List indexed documents.").set_defaults(func=cmd_list)

    p_search = sub.add_parser("search", help="Search the library.")
    p_search.add_argument("query")
    p_search.add_argument("--all", action="store_true", help="Require every term.")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.set_defaults(func=cmd_search)

    p_get = sub.add_parser("get", help="Retrieve one document.")
    p_get.add_argument("doc_id")
    p_get.add_argument("--lines", type=int, default=0, help="Show only the first N lines.")
    p_get.set_defaults(func=cmd_get)

    p_ref = sub.add_parser("reference", help="Print a citable reference.")
    p_ref.add_argument("doc_id")
    p_ref.set_defaults(func=cmd_reference)

    sub.add_parser("doctor", help="Boundary and access self-check.").set_defaults(
        func=cmd_doctor
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
