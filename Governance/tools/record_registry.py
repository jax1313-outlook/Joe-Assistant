#!/usr/bin/env python3
"""Record the governance registry from a workspace of checkouts.

Run deliberately, never automatically. The registry is a set of *claims about
authority*, and a tool that regenerated it on every commit would silently
re-bless whatever a document currently says -- which is exactly the drift the
detector exists to catch. What this script does is record the hashes and the
adjudication once, so that afterwards a change is visible.

    python Governance/tools/record_registry.py /path/to/workspace
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dispatch_governance.registry import (  # noqa: E402
    ADVISORY,
    CURRENT,
    HISTORICAL,
    SUPERSEDED,
    GovernanceDocument,
    GovernanceRegistry,
)

V3_NOTE = (
    "Describes the intended organisational shape of the programme. It is later than v2 and "
    "supersedes it as a statement of intent. It authorises no code: where it names a "
    "component, that is a description of an intended function, not a licence to build one "
    "into Dispatch."
)
V2_NOTE = (
    "Superseded by v3 as a statement of intent. Retained and readable -- Dispatch/CLAUDE.md "
    "section 7 forbids editing an old decision to hide its history. It does not govern any "
    "repository now."
)
CM_NOTE = (
    "Context, not authority. Superseded by the architecture document in the production "
    "repository, which is the one kept current."
)
MGR_NOTE = (
    "A component description carried in a worker repository. It is history: "
    "Dispatch/docs/MANAGER.md records that Manager was named and never built, and "
    "Dispatch/CLAUDE.md section 5.6 forbids creating, restoring, referencing or inferring "
    "one in code."
)

#: (doc_id, repo, path, status, scope, superseded_by, note)
ADJUDICATION: tuple[tuple, ...] = (
    ("DISPATCH_CLAUDE_MD", "Dispatch", "CLAUDE.md", CURRENT,
     "Programme authority for everything that runs: boundaries, the truth vocabulary, what "
     "may and may not be built.", "",
     "Declares itself the first file to read, and its clauses are the only governance in the "
     "programme enforced by a test that fails a build "
     "(Dispatch/tests/test_repository_doctrine.py)."),
    ("DISPATCH_DECISION_LOG", "Dispatch", "DECISION_LOG.md", CURRENT,
     "Every adjudicated decision, in order, with its date and reasoning.", "",
     "The record CLAUDE.md section 7 requires a conflict to be reported into."),
    ("DISPATCH_REPOSITORY_DOCTRINE_TEST", "Dispatch", "tests/test_repository_doctrine.py", CURRENT,
     "The clauses of CLAUDE.md asserted against the repository rather than trusted.", "",
     "Governance that is executable. Where a document and this file disagree about what the "
     "code may contain, this file is what actually decides, because it is what refuses the "
     "merge."),
    ("DISPATCH_PURPOSE_STATEMENT", "Dispatch", "DISPATCH_PURPOSE_STATEMENT.md", CURRENT,
     "The four verbs every feature is measured against.", "", ""),
    ("DISPATCH_DRIVER_FIRST", "Dispatch", "DRIVER_FIRST_DOCTRINE_v2.md", CURRENT,
     "D1-D15, binding on every driver-facing surface.", "", ""),
    ("DISPATCH_AUTHORITY_AND_BOUNDARIES", "Dispatch",
     "docs/governance/DISPATCH_AUTHORITY_AND_BOUNDARIES.md", CURRENT,
     "Human authority: who decides, and what software may never claim.", "", ""),
    ("DISPATCH_ARCHITECTURE", "Dispatch", "docs/architecture/DISPATCH_ARCHITECTURE.md", CURRENT,
     "The architecture and the document map.", "", ""),
    ("DISPATCH_MANAGER_RECORD", "Dispatch", "docs/MANAGER.md", HISTORICAL,
     "The permanent record of Manager: named in planning, never built.", "",
     "Authorises no code, no route, no data model and no runtime behaviour. This is the "
     "document that settles the Manager question for code."),
    ("CONSTITUTION_V3", "Claude-3", "DISPATCH_CONSTITUTION_v3.md", ADVISORY,
     "Programme intent: layers, organisational functions, cognitive functions.", "", V3_NOTE),
    ("CONSTITUTION_V3_LIBRARY_COPY", "Library", "DISPATCH_CONSTITUTION_v3.md", ADVISORY,
     "Byte-identical copy of CONSTITUTION_V3.", "",
     "A copy, not a second authority. Identical bytes as of the recorded date; the drift "
     "detector is what notices if that stops being true."),
    ("CONSTITUTION_V2_CLAUDE", "Claude", "DISPATCH_CONSTITUTION_v2.md", SUPERSEDED,
     "Programme intent, earlier revision.", "CONSTITUTION_V3", V2_NOTE),
    ("CONSTITUTION_V2_JOE_ASSISTANT", "Joe-Assistant", "DISPATCH_CONSTITUTION_v2.md", SUPERSEDED,
     "Programme intent, earlier revision.", "CONSTITUTION_V3", V2_NOTE),
    ("CONSTITUTION_V2_PUBLISHER", "Publisher", "DISPATCH_CONSTITUTION_v2.md", SUPERSEDED,
     "Programme intent, earlier revision.", "CONSTITUTION_V3", V2_NOTE),
    ("CONTEXT_MASTER_V2_CLAUDE", "Claude", "DISPATCH_CONTEXT_MASTER_v2.md", SUPERSEDED,
     "Programme context, earlier revision.", "DISPATCH_ARCHITECTURE", CM_NOTE),
    ("CONTEXT_MASTER_V2_JOE_ASSISTANT", "Joe-Assistant", "DISPATCH_CONTEXT_MASTER_v2.md",
     SUPERSEDED, "Programme context, earlier revision.", "DISPATCH_ARCHITECTURE", CM_NOTE),
    ("CONTEXT_MASTER_V2_PUBLISHER", "Publisher", "DISPATCH_CONTEXT_MASTER_v2.md", SUPERSEDED,
     "Programme context, earlier revision.", "DISPATCH_ARCHITECTURE", CM_NOTE),
    ("MANAGER_DOC_CLAUDE", "Claude", "MANAGER.md", HISTORICAL,
     "A description of the Manager function.", "", MGR_NOTE),
    ("MANAGER_DOC_CLAUDE_3", "Claude-3", "MANAGER.md", HISTORICAL,
     "A description of the Manager function.", "", MGR_NOTE),
    ("MANAGER_DOC_LIBRARY", "Library", "MANAGER.md", HISTORICAL,
     "A description of the Manager function.", "", MGR_NOTE),
    ("LIBRARY_CHARTER", "Library", "README.md", CURRENT,
     "What the Library worker is and what it may do, inside its own repository.", "", ""),
    ("PUBLISHER_CHARTER", "Publisher", "README.md", CURRENT,
     "What the Publisher worker is and what it may do, inside its own repository.", "", ""),
    ("SANDBOX_CHARTER", "Joe-Assistant", "READ ME.md", CURRENT,
     "This repository is the proving ground, not production.", "",
     "States its own promotion path: Test-Grounds -> Review -> Hold -> Review -> Dispatch. "
     "It is why work lands here first."),
    ("HOLD_CHARTER", "Hold", "README.md", CURRENT,
     "The staging repository between the proving ground and production.", "", ""),
)

ANSWERS = {
    "may a Manager component be built into Dispatch": "DISPATCH_MANAGER_RECORD",
    "what words may a status use": "DISPATCH_CLAUDE_MD",
    "who has final authority": "DISPATCH_AUTHORITY_AND_BOUNDARIES",
    "what governs a driver-facing screen": "DISPATCH_DRIVER_FIRST",
    "what is the programme trying to do": "DISPATCH_PURPOSE_STATEMENT",
    "where is a decision recorded": "DISPATCH_DECISION_LOG",
    "what enforces doctrine": "DISPATCH_REPOSITORY_DOCTRINE_TEST",
    "what is the intended organisational shape": "CONSTITUTION_V3",
    "may this repository ship to production": "SANDBOX_CHARTER",
}

UNRESOLVED = [
    {
        "id": "U-01",
        "question": "Does Dispatch/CLAUDE.md supersede DISPATCH_CONSTITUTION_v3, or are they "
                    "different kinds of document?",
        "resolved_from_repository_evidence": True,
        "finding": "Different kinds. v3 describes an intended organisational shape; CLAUDE.md "
                   "governs what the running program may contain and is enforced by "
                   "tests/test_repository_doctrine.py. Neither supersedes the other; they "
                   "answer different questions, and the registry records which question each "
                   "answers.",
        "residual_risk": "A future v4 ruling directly on code would create a genuine conflict. "
                         "Nothing in the repositories does so today.",
    },
    {
        "id": "U-02",
        "question": "Which repository is authoritative for a worker's own charter?",
        "resolved_from_repository_evidence": True,
        "finding": "Its own. Library, Publisher and the sandbox each define their scope in "
                   "their own README, and no production document contradicts them.",
        "residual_risk": "None observed.",
    },
    {
        "id": "U-03",
        "question": "Is DISPATCH_CONSTITUTION_v3 approved, or a draft?",
        "resolved_from_repository_evidence": False,
        "finding": "Its own header reads 'Current Controlled Constitution - v3 Replacement "
                   "Draft'. 'Current Controlled' and 'Replacement Draft' are contradictory, "
                   "and no repository contains an approval record for it. Registered ADVISORY, "
                   "which is true under either reading, and no code decision rests on it.",
        "residual_risk": "If v3 was in fact ratified, its status should be raised for questions "
                         "of intent. THIS REQUIRES MIKE. Resolved no further from repository "
                         "evidence alone, because inferring an approval is the one thing the "
                         "authority doctrine forbids outright.",
    },
    {
        "id": "U-04",
        "question": "Hold/ carries MANAGER_CONSTITUTION_v1 twice.",
        "resolved_from_repository_evidence": False,
        "finding": "Two identical copies inside one repository, describing a component "
                   "production forbids in code. Left in place and unregistered: Hold is a "
                   "staging repository and its library_seed is data, not governance of Dispatch.",
        "residual_risk": "If Hold's library_seed is promoted into Library as doctrine, this "
                         "document travels with it. Flagged for review before any such "
                         "promotion.",
    },
]


def build(workspace: Path, *, recorded_at: str) -> GovernanceRegistry:
    documents = []
    for doc_id, repo, path, status, scope, superseded_by, note in ADJUDICATION:
        target = workspace / repo / path
        digest = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else ""
        documents.append(
            GovernanceDocument(
                doc_id=doc_id, repo=repo, path=path, status=status, scope=scope,
                sha256=digest, superseded_by=superseded_by, recorded_at=recorded_at, note=note,
            )
        )
    return GovernanceRegistry(
        version="1", authority="DISPATCH_CLAUDE_MD", generated_at=recorded_at,
        documents=documents, answers=dict(ANSWERS), unresolved=list(UNRESOLVED),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workspace", type=Path, help="directory holding one clone per repository")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent.parent / "GOVERNANCE_REGISTRY.json")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)

    registry = build(args.workspace, recorded_at=args.date)
    problems = registry.validate()
    if problems:
        for problem in problems:
            print(f"  refused: {problem}", file=sys.stderr)
        return 1

    registry.save(args.output)
    missing = [d.doc_id for d in registry.documents if not d.sha256]
    print(f"  recorded {len(registry.documents)} documents -> {args.output}")
    if missing:
        print(f"  {len(missing)} not present in the workspace and recorded with no hash:")
        for doc_id in missing:
            print(f"    {doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
