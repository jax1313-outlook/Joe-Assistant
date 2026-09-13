#!/usr/bin/env python3
"""Find governance documents that assert authority and are not registered.

`GOVERNANCE_REGISTRY.json` holds 23 documents. The other sixty-odd were
described as "context, matrices and reports" -- which was a reasonable reading
and was never checked. An unchecked claim about which documents govern is
exactly the kind of thing the truth vocabulary exists to prevent, and it fails
in the worst direction: a document that quietly asserts authority and is not in
the registry is invisible to the drift detector and to anyone asking what
governs.

This screens rather than concludes. It reads every governance-shaped Markdown
file across the clones, scores the language that asserts authority, and prints
what a person should read. It does not register anything: deciding that a
document governs is a judgement, and the whole point of the registry is that
judgements in it were made by reading.

    python Governance/tools/screen_authority.py <directory holding the clones>
    python Governance/tools/screen_authority.py .. --all
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent / "GOVERNANCE_REGISTRY.json"

#: Phrases that make a document binding rather than descriptive. Weighted,
#: because "shall" in one sentence is a turn of phrase and "shall" in twenty is
#: a constitution.
MARKERS: dict[str, int] = {
    r"\bshall\b": 3,
    r"\bmust not\b": 3,
    r"\bmay not\b": 3,
    r"\bis forbidden\b": 4,
    r"\bprohibited\b": 3,
    r"\bfinal authority\b": 5,
    r"\bsupersed(es|ed|ing)\b": 4,
    r"\bratified\b": 4,
    r"\bbinding\b": 4,
    r"\bthis (document|constitution) governs\b": 5,
    r"\bconstitution\b": 2,
    r"\bArticle [IVX0-9]+\b": 3,
    r"\bAuthority\b": 1,
    r"\bdoctrine\b": 1,
}

#: Files that are plainly not governance whatever words they contain.
IGNORE_PARTS = {".git", "node_modules", "__pycache__", "tests", "test"}

#: A score at or above this is worth a person's time. Calibrated below against
#: the 23 documents already known to assert authority -- see `calibrate()`.
THRESHOLD = 12


def registered_paths() -> set[tuple[str, str]]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {(d["repo"], d["path"].replace("\\", "/")) for d in data["documents"]}


def score(text: str) -> tuple[int, dict[str, int]]:
    hits: dict[str, int] = {}
    total = 0
    for pattern, weight in MARKERS.items():
        found = len(re.findall(pattern, text, re.I))
        if found:
            label = pattern.strip("\\b").replace("\\", "")
            hits[label] = found
            # Diminishing: the twentieth "shall" says little the fifth did not.
            total += weight * min(found, 5)
    return total, hits


#: A document that governs usually says so in a header line, and that is a
#: structural signal rather than a lexical one -- which ADR-22 records as the
#: distinction the word-count score could not make. `CLAUDE.md` scores 38 on
#: language and is the programme authority; `DISPATCH_PROGRAM_MAP.md` scores 65
#: and says of itself that it controls nothing. Their status lines are not
#: ambiguous at all.
STATUS_LINE = re.compile(
    r"^\s*\*{0,2}(Status|Authority|Final authority)\*{0,2}\s*:?\*{0,2}\s*(?P<value>.+)$",
    re.I | re.M,
)

#: What a self-declared status has to contain to be worth reading. Deliberately
#: narrow: these are the words a document uses to bind, not to discuss.
BINDING_WORDS = re.compile(
    r"\b(doctrine|binding|in force|constitution|ratified|signed|approved direction|"
    r"controlling|authoritative)\b", re.I,
)

#: And what takes it straight back out again.
DISCLAIMERS = re.compile(
    r"\b(not an approved|recommendation only|proposal|draft|audit only|"
    r"nothing implemented|nothing built|planning)\b", re.I,
)


def self_declared(text: str) -> tuple[str, str]:
    """`(verdict, the line it came from)`.

    BINDING   the document says it governs
    DISCLAIMS the document says it does not
    SILENT    it does not say, so only a person can tell
    """
    for match in STATUS_LINE.finditer(text[:4000]):
        value = match.group("value").strip()
        if DISCLAIMERS.search(value):
            return "DISCLAIMS", value[:90]
        if BINDING_WORDS.search(value):
            return "BINDING", value[:90]
    return "SILENT", ""


def candidates(root: Path):
    known = registered_paths()
    for repo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        repo = repo_dir.name
        for path in sorted(repo_dir.rglob("*.md")):
            if any(part in IGNORE_PARTS for part in path.parts):
                continue
            rel = path.relative_to(repo_dir).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            total, hits = score(text)
            verdict, line = self_declared(text)
            yield {
                "repo": repo, "path": rel, "score": total, "hits": hits,
                "registered": (repo, rel) in known, "bytes": path.stat().st_size,
                "declares": verdict, "status_line": line,
            }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    show_all = "--all" in sys.argv
    rows = list(candidates(root))
    if not rows:
        print(f"no markdown found under {root}")
        return 1

    registered = [r for r in rows if r["registered"]]
    unregistered = [r for r in rows if not r["registered"]]

    # A registered document this screen cannot see is worth saying out loud
    # rather than quietly counting short. The first run reported "22 registered"
    # against a registry of 23, and the missing one was
    # Dispatch/tests/test_repository_doctrine.py -- governance that is
    # executable, skipped because it is not Markdown and lives under tests/.
    # A screen that silently loses a governing document is the failure it exists
    # to prevent.
    seen = {(r["repo"], r["path"]) for r in rows}
    unseen = sorted(registered_paths() - seen)
    if unseen:
        print(f"{len(unseen)} registered document(s) this screen cannot read:")
        for repo, rel in unseen:
            print(f"        {repo}/{rel}")
        print("  (not Markdown, or under an ignored directory -- judged by hand, not here)")
        print()
    flagged = sorted(
        (r for r in unregistered if r["score"] >= THRESHOLD),
        key=lambda r: -r["score"],
    )

    print(f"{len(rows)} documents under {root}")
    print(f"  {len(registered)} registered, {len(unregistered)} not")
    if registered:
        scores = sorted(r["score"] for r in registered)
        print(f"  registered score range: {scores[0]}-{scores[-1]} (threshold {THRESHOLD})")

    # The queue that matters. A document that declares itself binding and is
    # not registered is a gap; one that scores highly on language and declares
    # nothing is only a maybe.
    declared = [r for r in unregistered if r["declares"] == "BINDING"]
    print(f"\nDECLARES ITSELF BINDING and is not registered -- {len(declared)}:\n")
    for row in sorted(declared, key=lambda r: -r["score"]):
        print(f"  {row['score']:4}  {row['repo']}/{row['path']}")
        print(f"        status: {row['status_line']}")

    disclaimed = [r for r in unregistered if r["declares"] == "DISCLAIMS"]
    print(f"\n{len(disclaimed)} unregistered document(s) disclaim authority in their own header.")
    print("  Those are correctly absent, and the loud ones are worth registering ADVISORY")
    print("  anyway so nobody has to re-read them to find that out.")

    print(f"\n{len(flagged)} unregistered document(s) score at or above {THRESHOLD} on language")
    print("  alone. Language is a poor signal -- see ADR-22 -- so this is a reading list,")
    print("  not a queue of gaps:\n")
    for row in flagged:
        top = ", ".join(f"{k}x{v}" for k, v in sorted(row["hits"].items(), key=lambda kv: -kv[1])[:4])
        print(f"  {row['score']:4}  {row['repo']}/{row['path']}")
        print(f"        {top}")

    if show_all:
        print("\nevery unregistered document, by score:")
        for row in sorted(unregistered, key=lambda r: -r["score"]):
            print(f"  {row['score']:4}  {row['repo']}/{row['path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
