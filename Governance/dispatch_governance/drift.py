"""Has a governing document moved since we said what it was?

Three kinds of drift, and they need different answers:

**A CURRENT document changed.** Someone edited the thing that governs. That may
be entirely correct -- doctrine evolves -- but the registry now describes a
document that no longer exists in that form, and a builder trusting the registry
is trusting a stale claim. Re-record it deliberately.

**A SUPERSEDED document is still sitting in a worker repository.** This is the
finding that matters most and the one nothing could see before. A repository
whose only constitution is a superseded one will be read, in full, by the next
agent that starts there -- and `DISPATCH_CONSTITUTION_v2` mandates a Manager that
`Dispatch/CLAUDE.md` forbids and `test_repository_doctrine.py` fails a build over.
The document being outdated is not the problem; the problem is that nothing in
that repository says so.

**A registered document is gone.** Either it was deleted deliberately and the
registry should say so, or something was lost.

The detector works on a local checkout of each repository. No network, no
credentials, and it runs the same way on a laptop and in CI -- a governance check
that needs an API token is a governance check that does not run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from dispatch_governance.registry import (
    ADVISORY,
    CURRENT,
    HISTORICAL,
    SUPERSEDED,
    GovernanceRegistry,
)

#: Severities. BLOCKING means a build should fail; the rest are reports.
BLOCKING = "BLOCKING"
ADVISORY_FINDING = "ADVISORY"
INFO = "INFO"


@dataclass(frozen=True)
class DriftFinding:
    code: str
    severity: str
    doc_id: str
    repo: str
    path: str
    message: str
    remedy: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_drift(
    registry: GovernanceRegistry,
    workspace: Path | str,
    *,
    require_pointer: bool = True,
    pointer_name: str = "GOVERNANCE.md",
) -> list[DriftFinding]:
    """Compare the registry against checkouts under `workspace`.

    `workspace` holds one directory per repository, named as the registry names
    it -- which is how a developer's `git clone` layout and CI's checkout are the
    same input.
    """
    root = Path(workspace)
    findings: list[DriftFinding] = []
    repos_with_stale_authority: dict[str, list[str]] = {}

    for doc in registry.documents:
        if doc.repo == "*":
            continue
        repo_dir = root / doc.repo
        if not repo_dir.is_dir():
            findings.append(
                DriftFinding(
                    "REPO_NOT_CHECKED_OUT", INFO, doc.doc_id, doc.repo, doc.path,
                    f"{doc.repo} is not present under {root}; nothing was checked for it.",
                    f"Clone it beside the others, or drop it from the registry.",
                )
            )
            continue

        target = repo_dir / doc.path
        if not target.is_file():
            findings.append(
                DriftFinding(
                    "DOCUMENT_MISSING",
                    BLOCKING if doc.status == CURRENT else ADVISORY_FINDING,
                    doc.doc_id, doc.repo, doc.path,
                    f"{doc.path} is registered in {doc.repo} and is not there.",
                    "Either it was removed deliberately -- record that -- or something was lost.",
                )
            )
            continue

        actual = _sha256(target)
        if doc.sha256 and actual != doc.sha256:
            findings.append(
                DriftFinding(
                    "CONTENT_CHANGED",
                    BLOCKING if doc.status == CURRENT else INFO,
                    doc.doc_id, doc.repo, doc.path,
                    f"{doc.path} has changed since the registry recorded it "
                    f"({doc.sha256[:12]} -> {actual[:12]}).",
                    "Doctrine may change; the registry must be re-recorded when it does, "
                    "or it is describing a document that no longer exists.",
                )
            )

        if doc.status == SUPERSEDED:
            repos_with_stale_authority.setdefault(doc.repo, []).append(doc.doc_id)

    # The finding nothing could see before: a repository carrying a superseded
    # constitution and nothing beside it saying so.
    if require_pointer:
        for repo, stale in sorted(repos_with_stale_authority.items()):
            pointer = root / repo / pointer_name
            if pointer.is_file():
                continue
            findings.append(
                DriftFinding(
                    "STALE_AUTHORITY_UNMARKED", BLOCKING, ",".join(sorted(stale)), repo,
                    pointer_name,
                    f"{repo} carries {len(stale)} superseded governing document(s) "
                    f"({', '.join(sorted(stale))}) and no {pointer_name} saying what "
                    "actually governs. An agent starting there reads the superseded one "
                    "and follows it.",
                    f"Add {pointer_name} naming the current authority. The document itself "
                    "stays -- history is kept, it just stops being read as current.",
                )
            )

    findings.extend(_registry_problems(registry))
    return findings


def _registry_problems(registry: GovernanceRegistry) -> list[DriftFinding]:
    return [
        DriftFinding("REGISTRY_INCOHERENT", BLOCKING, "", "*", "GOVERNANCE_REGISTRY.json",
                     problem, "Fix the registry before trusting anything it says.")
        for problem in registry.validate()
    ]


def render_drift(findings: list[DriftFinding]) -> str:
    if not findings:
        return "  No governance drift. Every registered document is where and as recorded.\n"
    lines = []
    for severity in (BLOCKING, ADVISORY_FINDING, INFO):
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        lines.append(f"  {severity} ({len(group)})")
        for finding in group:
            lines.append(f"    [{finding.code}] {finding.repo}/{finding.path}")
            lines.append(f"      {finding.message}")
            if finding.remedy:
                lines.append(f"      -> {finding.remedy}")
        lines.append("")
    return "\n".join(lines)


def blocking(findings: list[DriftFinding]) -> list[DriftFinding]:
    return [f for f in findings if f.severity == BLOCKING]
