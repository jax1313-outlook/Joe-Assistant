#!/usr/bin/env python3
"""Check this tree against ROOT_MANIFEST.md.

A manifest of checksums nobody can check is decoration. This is the checker,
and it is deliberately dependency-free and short enough to read before trusting
it: standard library only, one pass, exit 1 on any mismatch.

    python Dispatch_Corrections/verify_manifest.py            # check
    python Dispatch_Corrections/verify_manifest.py --write    # regenerate
    python Dispatch_Corrections/verify_manifest.py --archive  # rebuild the zip

`--archive` builds the zip from the manifest's own file list rather than from a
second walk, so the archive and the checksums cannot describe different sets of
files. They did once: the archive carried 129 runtime files -- memory records
and a log -- that no manifest should have listed.

Reports three kinds of difference, because they mean different things:

  CHANGED  the file is here and its contents differ -- something edited it
  MISSING  the manifest lists it and it is not here -- something was lost
  EXTRA    it is here and the manifest does not list it -- something was added

An EXTRA is not automatically wrong; a copy that picked up a stray file is
different from one that dropped a real one, and saying which is which is the
whole point of separating them.
"""

from __future__ import annotations

import fnmatch
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "ROOT_MANIFEST.md"
GITIGNORE = ROOT / ".gitignore"

#: Never listed: caches, the git database, and the archive of this tree itself.
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
SKIP_NAMES = {"claude-build-phase3.zip", "ROOT_MANIFEST.md"}

ROW = re.compile(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|$")


def ignore_patterns() -> list[str]:
    """The `.gitignore` rules, so the package cannot ship what must never leave.

    This exists because the walk below found 256 files it should never have
    seen: `Assistant_Plugin/runtime_data/`, which `.gitignore` describes as the
    DPAPI-encrypted Microsoft 365 token cache and "memory records carrying real
    driver requests and assistant responses". A test run had written them, they
    were correctly untracked, and a manifest that walks the filesystem does not
    know what "untracked" means -- so the package would have carried a token
    cache and a driver's words to whatever machine it was copied onto.

    Reading the rules rather than restating them is the point. A hard-coded
    list would drift from `.gitignore` silently, and the drift would be in the
    direction of shipping something. Only the plain forms are honoured -- a
    literal path, a directory, one `*` -- which is all this repository's rules
    use; negations are ignored, so an unsupported rule can only *exclude* more,
    never less.
    """
    if not GITIGNORE.is_file():
        return []
    patterns = []
    for raw in GITIGNORE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/").lstrip("/"))
    return patterns


def is_ignored(rel: str, patterns: list[str]) -> bool:
    """Whether `rel` -- a POSIX path relative to the root -- is under a rule."""
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel, f"{pattern}/*"):
            return True
        # A bare name (`__pycache__`, `*.pyc`) matches at any depth, which is
        # what git does with a pattern containing no slash.
        if "/" not in pattern and any(
            fnmatch.fnmatch(part, pattern) for part in rel.split("/")
        ):
            return True
    return False


def walk() -> list[Path]:
    patterns = ignore_patterns()
    found = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        if is_ignored(path.relative_to(ROOT).as_posix(), patterns):
            continue
        found.append(path)
    return found


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def render() -> str:
    files = walk()
    total = sum(f.stat().st_size for f in files)
    lines = [
        "# ROOT MANIFEST",
        "",
        "Every file in this package, with its size and SHA-256, so a copy into",
        "`D:\\Claude-Build` can be proved complete rather than assumed complete.",
        "",
        "Check it with:",
        "",
        "    python Dispatch_Corrections/verify_manifest.py",
        "",
        f"**{len(files):,} files, {total:,} bytes.**",
        "",
        "Excluded: `.git/`, `__pycache__/`, `.pytest_cache/`, compiled Python, the",
        "archive of this tree, this file itself, and everything `.gitignore` names --",
        "which is where the runtime token cache and the memory records live.",
        "",
        "| Path | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for f in files:
        lines.append(f"| `{f.relative_to(ROOT).as_posix()}` | {f.stat().st_size} | `{digest(f)}` |")
    lines.append("")
    return "\n".join(lines)


def read_manifest() -> dict[str, tuple[int, str]]:
    if not MANIFEST.exists():
        sys.exit(f"no manifest at {MANIFEST}")
    listed = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line.strip())
        if m:
            listed[m.group(1)] = (int(m.group(2)), m.group(3))
    return listed


ARCHIVE = ROOT / "claude-build-phase3.zip"

#: Everything in the archive sits under this one folder, so extracting at the
#: root of `D:` lands the package at `D:\\Claude-Build` with nothing to rename.
TOP_LEVEL = "Claude-Build"


def write_archive() -> int:
    """The zip, built from the manifest so the two cannot disagree."""
    import zipfile

    listed = read_manifest()
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(listed):
            archive.write(ROOT / rel, f"{TOP_LEVEL}/{rel}")
        # The manifest itself travels inside, or a copy has no way to check
        # itself once it is unpacked somewhere else.
        archive.write(MANIFEST, f"{TOP_LEVEL}/{MANIFEST.name}")
    print(f"wrote {ARCHIVE.name}: {len(listed):,} files, {ARCHIVE.stat().st_size:,} bytes")
    return 0


def main() -> int:
    if "--write" in sys.argv:
        MANIFEST.write_text(render(), encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
        return 0

    if "--archive" in sys.argv:
        return write_archive()

    listed = read_manifest()
    present = {f.relative_to(ROOT).as_posix(): f for f in walk()}

    problems = 0
    for rel, (size, sha) in sorted(listed.items()):
        path = present.pop(rel, None)
        if path is None:
            print(f"MISSING  {rel}")
            problems += 1
        elif path.stat().st_size != size or digest(path) != sha:
            print(f"CHANGED  {rel}")
            problems += 1
    for rel in sorted(present):
        print(f"EXTRA    {rel}")
        problems += 1

    if problems:
        print(f"\n{problems} difference(s). This copy is not the package that was built.")
        return 1
    print(f"{len(listed):,} files, every checksum matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
