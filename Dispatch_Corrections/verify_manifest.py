#!/usr/bin/env python3
"""Check this tree against ROOT_MANIFEST.md.

A manifest of checksums nobody can check is decoration. This is the checker,
and it is deliberately dependency-free and short enough to read before trusting
it: standard library only, one pass, exit 1 on any mismatch.

    python Dispatch_Corrections/verify_manifest.py            # check
    python Dispatch_Corrections/verify_manifest.py --write    # regenerate

Reports three kinds of difference, because they mean different things:

  CHANGED  the file is here and its contents differ -- something edited it
  MISSING  the manifest lists it and it is not here -- something was lost
  EXTRA    it is here and the manifest does not list it -- something was added

An EXTRA is not automatically wrong; a copy that picked up a stray file is
different from one that dropped a real one, and saying which is which is the
whole point of separating them.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "ROOT_MANIFEST.md"

#: Never listed: caches, the git database, and the archive of this tree itself.
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
SKIP_NAMES = {"claude-build-phase3.zip", "ROOT_MANIFEST.md"}

ROW = re.compile(r"^\| `([^`]+)` \| (\d+) \| `([0-9a-f]{64})` \|$")


def walk() -> list[Path]:
    found = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
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
        "archive of this tree, and this file itself.",
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


def main() -> int:
    if "--write" in sys.argv:
        MANIFEST.write_text(render(), encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(ROOT)}")
        return 0

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
