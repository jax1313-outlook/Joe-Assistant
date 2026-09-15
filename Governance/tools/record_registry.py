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

    # ---- Phase 3: surfaced by screening for authority language, then read ----
    #
    # Governance/tools/screen_authority.py ranks every unregistered document by
    # how binding its language sounds. As a classifier it fails -- CLAUDE.md
    # scores 38 and a document that explicitly disclaims authority scores 65.
    # As a reading list it worked, and reading what it surfaced found these.

    ("ASSISTANT_PLUGIN_CONTEXT_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/01_CONTEXT_v1.md", CURRENT,
     "What the Assistant is for, and the standing it is built under.", "",
     "Self-declared Doctrine."),
    ("ASSISTANT_PLUGIN_CONSTITUTION_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/02_CONSTITUTION_v1.md", CURRENT,
     "The Assistant's own constitution: its standing as a plug-in, and the eight "
     "functions Article II permits.", "",
     "Self-declared 'Doctrine. Binding on all Assistant work.', final authority Mike "
     "Zachary. DECISION_LOG cites its Article II when ruling that JOE cannot transmit. "
     "It was governing the Assistant work in this repository the whole time and was "
     "not in the registry -- the largest gap the Phase 3 screen found."),
    ("ASSISTANT_PLUGIN_ARCHITECTURE_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/03_ARCHITECTURE_v1.md", CURRENT,
     "Architectural principle for the Assistant. No interface specification.", "",
     "Self-declared Doctrine."),
    ("ASSISTANT_PLUGIN_GOVERNANCE_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/04_GOVERNANCE_v1.md", CURRENT,
     "How the Assistant's own doctrine changes, and who may change it.", "",
     "Self-declared Doctrine."),
    ("ASSISTANT_PLUGIN_REPOSITORY_RECOMMENDATION_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/05_REPOSITORY_RECOMMENDATION_v1.md", ADVISORY,
     "Where the Assistant should live -- recommended, not decided.", "",
     "Self-declared 'Recommendation. Doctrine only -- no repository is created.' "
     "ADVISORY so it cannot be read as having settled the question."),
    ("ASSISTANT_PLUGIN_RESEARCH_TRUTH_DOCTRINE_V1", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/06_KNOWLEDGE_RESEARCH_TRUTH_DOCTRINE_v1.md", CURRENT,
     "What the Assistant may claim to know, and how a research answer is qualified.", "",
     "Self-declared 'Approved Direction for Implementation'."),
    ("ASSISTANT_PLUGIN_AMENDMENT_1_SIGNED", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/AMENDMENT_1_TRANSMISSION_SIGNED.md", CURRENT,
     "Amendment 1 to the Assistant Plugin Constitution, on transmission.", "",
     "Self-declared 'SIGNED by Mike Zachary.'"),
    ("ASSISTANT_PLUGIN_AMENDMENT_1_CONDITIONS", "Joe-Assistant",
     "ASSISTANT_PLUGIN_CONSTITUTION_v1/AMENDMENT_1_TRANSMISSION_PROPOSED.md", CURRENT,
     "The operating conditions Amendment 1 runs under.", "",
     "A naming trap, and the clearest argument for a registry over a filename: the "
     "file is called PROPOSED and its status line reads 'IN FORCE as the operating "
     "conditions of Amendment 1.' Sorted by filename, the signed amendment looks "
     "binding and this looks like a draft. Registered CURRENT on what it says about "
     "itself; the contradiction is recorded, not resolved."),

    ("DISPATCH_CF04_LIFECYCLE_AUTHORITY", "Dispatch",
     "DISPATCH_CF04_LIFECYCLE_AUTHORITY_MODEL_v1.md", CURRENT,
     "CF-04 adjudicated: the Spine is the authoritative lifecycle engine and "
     "Opportunity advises.", "",
     "Carries Mike's ruling verbatim, dated 2026-08-23, and CLAUDE.md 5.1 cites it. "
     "An adjudicated ruling that was not in the registry."),
    ("DISPATCH_CONFLICT_AUTHORITY_REGISTER", "Dispatch",
     "DISPATCH_CONFLICT_AND_AUTHORITY_REGISTER.md", CURRENT,
     "The CF-01 to CF-10 conflict register.", "",
     "Deliberately NOT marked superseded. CF-04 supersedes the framing of one row out "
     "of ten and the other nine are live, so flattening the document to SUPERSEDED "
     "would bury nine open conflicts -- a worse error than one stale row. Read its "
     "CF-04 row against DISPATCH_CF04_LIFECYCLE_AUTHORITY_MODEL_v1.md."),
    ("DISPATCH_RECOVERY_WAVE_1_REPORT", "Dispatch",
     "DISPATCH_RECOVERY_WAVE_1_REPORT.md", CURRENT,
     "Recovery Wave 1 findings.", "",
     "Same treatment as the conflict register: its CF-04 framing is superseded, the "
     "rest of the report is not."),

    ("CLAUDE_PROGRAM_MAP", "Claude", "DISPATCH_PROGRAM_MAP.md", ADVISORY,
     "A total programme map, offered as a proposal.", "",
     "Registered precisely because it reads as authoritative and is not. It scores "
     "higher on authority language than CLAUDE.md, and its own header says 'Status: "
     "Proposal / Planning Draft -- NOT an approved controlling document' and 'This "
     "document is a recommendation only. No action is authorized.' An agent "
     "cold-starting in Claude/ and finding a 'Total Program Map' could build from it. "
     "ADVISORY says do not."),

    # ---- Phase 3, second pass: screened on self-declared status, not language ----
    #
    # The word-count score produced a 171-document queue and could not tell a
    # constitution from a disclaimer. Screening instead on what a document says
    # about itself in its own status line -- the structural signal ADR-22 named
    # -- produced 22, and these nine are production Dispatch doctrine that was
    # never registered. Two of them are issued by Mike personally.

    ("DISPATCH_ACCESSORIAL_POLICY_DOCTRINE", "Dispatch",
     "docs/DISPATCH_ACCESSORIAL_POLICY_DOCTRINE.md", CURRENT,
     "Accessorials are company policy, not application settings.", "",
     "'DOCTRINE. Issued by the operator, 30 August 2026.' Issued by Mike himself, in "
     "the production repository, and absent from the registry until now -- which is "
     "the exact failure a governance registry exists to prevent. It supersedes the "
     "accessorials block in DISPATCH_POLICY_PROFILE_SPEC.md."),
    ("DISPATCH_CAPACITY_PLAN_DOCTRINE", "Dispatch",
     "docs/DISPATCH_CAPACITY_PLAN_DOCTRINE.md", CURRENT,
     "Day plans, stop sequences and capacity allocations remain recommendations until "
     "a human approves them.", "",
     "'DOCTRINE. Issued by the operator, 30 August 2026.' Directly governs the capacity "
     "stop work built earlier in Phase 3, which was written advisory and non-mutating "
     "before this document had been read. Compliance was checked afterwards, not "
     "assumed: dispatch/load_stops.py reserves nothing and decides nothing."),
    ("DISPATCH_SYSTEM_INDEPENDENCE_DOCTRINE", "Dispatch",
     "docs/DISPATCH_SYSTEM_INDEPENDENCE_DOCTRINE.md", CURRENT,
     "Dispatch remains operable when every external system is down.", "",
     "Named as a standing criterion for this whole mission and never registered. "
     "'Not degraded into uselessness. Operable.'"),
    ("DISPATCH_DETERMINISTIC_CHASSIS", "Dispatch",
     "docs/DISPATCH_DETERMINISTIC_CHASSIS.md", CURRENT,
     "The engine is deterministic, the operator owns the policy, the human owns the "
     "decision.", "",
     "Self-declared DOCTRINE. Same inputs, same policy profile, same outputs."),
    ("DISPATCH_FACT_AND_PROVENANCE_DOCTRINE", "Dispatch",
     "docs/DISPATCH_FACT_AND_PROVENANCE_DOCTRINE.md", CURRENT,
     "Dispatch does not invent facts, and every fact carries its origin.", "",
     "Self-declared DOCTRINE. 'A number on a screen that cannot be traced to a source "
     "is not information. It is a guess.'"),
    ("DISPATCH_CONFIGURABLE_BUSINESS_POLICY_DOCTRINE", "Dispatch",
     "docs/DISPATCH_CONFIGURABLE_BUSINESS_POLICY_DOCTRINE.md", CURRENT,
     "Dispatch owns the engine; the operator owns the settings.", "",
     "Self-declared DOCTRINE."),
    ("DISPATCH_EXTERNAL_ADAPTER_BOUNDARIES", "Dispatch",
     "docs/DISPATCH_EXTERNAL_ADAPTER_BOUNDARIES.md", CURRENT,
     "An adapter is the only place in Dispatch that knows a specific external system "
     "exists.", "",
     "Self-declared DOCTRINE, and the doctrine the provider-neutral transport and the "
     "Microsoft adapter layer were built to."),
    ("DISPATCH_STATE_TRANSITION_RULES", "Dispatch",
     "docs/DISPATCH_STATE_TRANSITION_RULES.md", CURRENT,
     "The Mission Record is created once and enriched for life. It is never copied and "
     "never changes identity.", "",
     "Self-declared DOCTRINE that 'describes rules current code already partly "
     "implements' -- so the gap between it and the code is itself a finding, and it "
     "could not be seen while the document was unregistered."),
    ("DISPATCH_BUILD_MATRIX_V1", "Dispatch", "DISPATCH_BUILD_MATRIX_v1.md", CURRENT,
     "The build matrix, and the authority it claims to run under.", "",
     "Bears on the unresolved question in section 9: its header reads 'Mike Zachary "
     "remains final authority (Constitution v3 3, 22)' -- a production Dispatch "
     "document treating v3 as authoritative and citing its sections. That is evidence "
     "about v3's standing and it is not a ratification record, so v3 stays ADVISORY "
     "and the citation is recorded here for Mike to weigh."),
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
