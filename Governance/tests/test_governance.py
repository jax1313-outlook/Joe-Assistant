"""The governance registry is coherent, and the drift detector finds the fork.

Phase 1 found five repositories carrying a constitution, two different
constitutions, and a production repository carrying neither -- with all of the
constitutions naming a Manager component that `Dispatch/CLAUDE.md` forbids and
`Dispatch/tests/test_repository_doctrine.py` fails a build over.

These tests pin the resolution: which document answers which question, that a
superseded document can never be the answer to anything, and that a repository
carrying one without saying so is a blocking finding rather than a silent
condition somebody has to notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dispatch_governance.drift import BLOCKING, blocking, check_drift, render_drift
from dispatch_governance.registry import (
    ADVISORY,
    CURRENT,
    HISTORICAL,
    SUPERSEDED,
    GovernanceDocument,
    GovernanceRegistry,
    load_registry,
)

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "GOVERNANCE_REGISTRY.json"


@pytest.fixture
def registry() -> GovernanceRegistry:
    return load_registry(REGISTRY_PATH)


class TestTheRecordedRegistry:
    def test_it_is_coherent(self, registry):
        assert registry.validate() == []

    def test_there_is_exactly_one_programme_authority(self, registry):
        authority = registry.get(registry.authority)
        assert authority is not None
        assert authority.status == CURRENT
        assert authority.repo == "Dispatch"
        assert authority.path == "CLAUDE.md"

    def test_every_recorded_document_has_a_hash(self, registry):
        """A registry entry with no hash is a claim nothing can check."""
        missing = [d.doc_id for d in registry.documents if not d.sha256]
        assert missing == [], f"recorded with no hash: {missing}"

    def test_both_constitutions_are_registered_and_neither_governs_code(self, registry):
        v2 = [d for d in registry.documents if d.doc_id.startswith("CONSTITUTION_V2")]
        v3 = registry.get("CONSTITUTION_V3")
        assert len(v2) == 3, "v2 is present in Claude, Joe-Assistant and Publisher"
        assert all(d.status == SUPERSEDED for d in v2)
        assert all(d.superseded_by == "CONSTITUTION_V3" for d in v2)
        assert v3.status == ADVISORY
        assert "authorises no code" in v3.note

    def test_the_manager_question_is_answered_by_the_record_of_it(self, registry):
        answer = registry.answer("may a Manager component be built into Dispatch")
        assert answer.doc_id == "DISPATCH_MANAGER_RECORD"
        assert answer.repo == "Dispatch"
        assert answer.path == "docs/MANAGER.md"
        assert answer.status == HISTORICAL
        # Neither created because an older document requires one, nor removed
        # because another forbids one. The record says it was never built and
        # authorises nothing; the enforced test is what keeps it that way.
        assert "Authorises no code" in answer.note

    def test_the_enforcing_test_is_itself_registered_as_authority(self, registry):
        doc = registry.get("DISPATCH_REPOSITORY_DOCTRINE_TEST")
        assert doc.status == CURRENT
        assert doc.path.endswith("test_repository_doctrine.py")

    def test_a_worker_repository_has_no_current_constitution_of_its_own(self, registry):
        for repo in ("Claude", "Publisher", "Joe-Assistant"):
            binding = {d.path for d in registry.binding_for(repo)}
            assert "DISPATCH_CONSTITUTION_v2.md" not in binding

    def test_unresolved_conflicts_are_recorded_rather_than_decided(self, registry):
        unresolved = {u["id"]: u for u in registry.unresolved}
        assert "U-03" in unresolved
        assert unresolved["U-03"]["resolved_from_repository_evidence"] is False
        # Inferring that a document headed "Replacement Draft" was ratified is
        # exactly the manufactured approval the authority doctrine forbids.
        assert "REQUIRES MIKE" in unresolved["U-03"]["residual_risk"]

    def test_every_unresolved_item_says_whether_evidence_settled_it(self, registry):
        for item in registry.unresolved:
            assert isinstance(item["resolved_from_repository_evidence"], bool)
            assert item["finding"]
            assert item["residual_risk"]


class TestTheRules:
    def test_a_superseded_document_must_name_its_successor(self):
        with pytest.raises(ValueError, match="names nothing that replaced it"):
            GovernanceDocument(
                doc_id="X", repo="R", path="p.md", status=SUPERSEDED, scope="s",
            )

    def test_an_unknown_status_is_refused(self):
        with pytest.raises(ValueError, match="unknown governance status"):
            GovernanceDocument(doc_id="X", repo="R", path="p.md", status="MOSTLY", scope="s")

    def test_an_answer_may_not_point_at_something_superseded(self):
        registry = GovernanceRegistry(
            documents=[
                GovernanceDocument("NEW", "R", "new.md", CURRENT, "s"),
                GovernanceDocument("OLD", "R", "old.md", SUPERSEDED, "s", superseded_by="NEW"),
            ],
            answers={"what governs": "OLD"},
        )
        problems = registry.validate()
        assert any("SUPERSEDED" in p for p in problems)

    def test_an_advisory_document_may_answer_a_question_of_intent(self):
        registry = GovernanceRegistry(
            documents=[GovernanceDocument("INTENT", "R", "c.md", ADVISORY, "s")],
            answers={"what is intended": "INTENT"},
        )
        assert registry.validate() == []

    def test_a_supersession_chain_that_points_at_a_dead_end_is_caught(self):
        registry = GovernanceRegistry(
            documents=[
                GovernanceDocument("A", "R", "a.md", SUPERSEDED, "s", superseded_by="B"),
                GovernanceDocument("B", "R", "b.md", SUPERSEDED, "s", superseded_by="C"),
                GovernanceDocument("C", "R", "c.md", CURRENT, "s"),
            ],
        )
        problems = registry.validate()
        assert any("itself superseded" in p for p in problems)


def _workspace(tmp_path: Path, files: dict) -> Path:
    for rel, text in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


class TestDriftDetection:
    def _registry(self, tmp_path: Path) -> GovernanceRegistry:
        import hashlib

        def sha(rel):
            return hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest()

        return GovernanceRegistry(
            authority="AUTH",
            documents=[
                GovernanceDocument("AUTH", "Dispatch", "CLAUDE.md", CURRENT, "authority",
                                   sha256=sha("Dispatch/CLAUDE.md")),
                GovernanceDocument("OLD_CONST", "Worker", "CONSTITUTION_v2.md", SUPERSEDED,
                                   "intent", superseded_by="AUTH",
                                   sha256=sha("Worker/CONSTITUTION_v2.md")),
            ],
        )

    @pytest.fixture
    def workspace(self, tmp_path):
        return _workspace(tmp_path, {
            "Dispatch/CLAUDE.md": "the authority\n",
            "Worker/CONSTITUTION_v2.md": "an older constitution\n",
        })

    def test_a_worker_carrying_a_superseded_constitution_and_no_pointer_is_blocking(
        self, workspace
    ):
        findings = check_drift(self._registry(workspace), workspace)
        stale = [f for f in findings if f.code == "STALE_AUTHORITY_UNMARKED"]
        assert len(stale) == 1
        assert stale[0].severity == BLOCKING
        assert stale[0].repo == "Worker"
        assert "reads the superseded one and follows it" in stale[0].message

    def test_a_pointer_clears_it_without_the_document_being_deleted(self, workspace):
        (workspace / "Worker" / "GOVERNANCE.md").write_text("see Dispatch/CLAUDE.md", encoding="utf-8")
        findings = check_drift(self._registry(workspace), workspace)
        assert not [f for f in findings if f.code == "STALE_AUTHORITY_UNMARKED"]
        # History is kept. That is the whole shape of the fix.
        assert (workspace / "Worker" / "CONSTITUTION_v2.md").is_file()

    def test_an_edited_authority_is_blocking(self, workspace):
        registry = self._registry(workspace)
        (workspace / "Dispatch" / "CLAUDE.md").write_text("edited\n", encoding="utf-8")
        findings = check_drift(registry, workspace)
        changed = [f for f in findings if f.code == "CONTENT_CHANGED"]
        assert changed and changed[0].severity == BLOCKING

    def test_an_edited_superseded_document_is_only_information(self, workspace):
        registry = self._registry(workspace)
        (workspace / "Worker" / "CONSTITUTION_v2.md").write_text("edited\n", encoding="utf-8")
        findings = check_drift(registry, workspace)
        changed = [f for f in findings if f.code == "CONTENT_CHANGED"]
        assert changed and changed[0].severity != BLOCKING

    def test_a_missing_authority_is_blocking(self, workspace):
        registry = self._registry(workspace)
        (workspace / "Dispatch" / "CLAUDE.md").unlink()
        findings = check_drift(registry, workspace)
        assert any(f.code == "DOCUMENT_MISSING" and f.severity == BLOCKING for f in findings)

    def test_an_absent_repository_is_reported_not_assumed_clean(self, workspace):
        registry = self._registry(workspace)
        import shutil

        shutil.rmtree(workspace / "Worker")
        findings = check_drift(registry, workspace)
        assert any(f.code == "REPO_NOT_CHECKED_OUT" for f in findings)

    def test_a_clean_workspace_produces_nothing(self, workspace):
        (workspace / "Worker" / "GOVERNANCE.md").write_text("see Dispatch/CLAUDE.md", encoding="utf-8")
        findings = check_drift(self._registry(workspace), workspace)
        assert findings == []
        assert "No governance drift" in render_drift(findings)

    def test_an_incoherent_registry_is_itself_a_blocking_finding(self, workspace):
        registry = self._registry(workspace)
        registry.answers["q"] = "NOT_REGISTERED"
        findings = check_drift(registry, workspace)
        assert any(f.code == "REGISTRY_INCOHERENT" and f.severity == BLOCKING for f in findings)

    def test_the_exit_code_is_what_ci_reads(self, workspace):
        assert blocking(check_drift(self._registry(workspace), workspace))
        (workspace / "Worker" / "GOVERNANCE.md").write_text("x", encoding="utf-8")
        assert not blocking(check_drift(self._registry(workspace), workspace))


class TestThePointerThisRepositoryCarries:
    def test_it_exists(self):
        pointer = Path(__file__).resolve().parent.parent.parent / "GOVERNANCE.md"
        assert pointer.is_file(), (
            "this repository carries a superseded constitution; without a pointer the "
            "next agent to start here reads it as current"
        )

    def test_it_names_the_authority_and_the_manager_ruling(self):
        text = (Path(__file__).resolve().parent.parent.parent / "GOVERNANCE.md").read_text(
            encoding="utf-8"
        )
        assert "Dispatch/CLAUDE.md" in text
        assert "There is no Manager component" in text
        assert "DISPATCH_CONSTITUTION_v2.md" in text

    def test_pointers_are_provided_for_the_repositories_this_one_cannot_write_to(self):
        pointers = Path(__file__).resolve().parent.parent / "pointers"
        names = {p.name for p in pointers.glob("*.md")}
        assert {"Claude-GOVERNANCE.md", "Publisher-GOVERNANCE.md"} <= names


class TestTheCli:
    def _run(self, argv):
        from dispatch_governance.cli import build_parser

        args = build_parser().parse_args(argv)
        return args.func(args)

    def test_show_reports_a_repository(self, capsys):
        assert self._run(["--registry", str(REGISTRY_PATH), "show", "Joe-Assistant"]) == 0
        out = capsys.readouterr().out
        assert "Superseded documents still present" in out

    def test_answer_names_the_deciding_document(self, capsys):
        assert self._run([
            "--registry", str(REGISTRY_PATH), "answer",
            "may a Manager component be built into Dispatch",
        ]) == 0
        assert "docs/MANAGER.md" in capsys.readouterr().out

    def test_an_unknown_question_lists_the_known_ones(self, capsys):
        assert self._run(["--registry", str(REGISTRY_PATH), "answer", "what colour"]) == 1
        assert "Registered questions" in capsys.readouterr().out
