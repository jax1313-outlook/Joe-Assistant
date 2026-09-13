"""The transfer package must not carry what `.gitignore` says never leaves.

`ROOT_MANIFEST.md` is built by walking the filesystem, and a filesystem walk has
no idea what "untracked" means. The first build of it listed **129 files it
should never have seen**: 128 memory records under
`Assistant_Plugin/runtime_data/memory/`, which `.gitignore` describes as
"carrying real driver requests and assistant responses", and a runtime log. The
same directory holds the DPAPI-encrypted Microsoft 365 token cache.

Nothing was leaked -- the package was never copied anywhere -- and that is
exactly why this test exists now rather than after it was. The rule is one line:
a file `.gitignore` excludes is not part of the package, whatever a walk finds
lying in the tree.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "Dispatch_Corrections" / "verify_manifest.py"


@pytest.fixture(scope="module")
def verifier():
    """Load the packager by path: it is a standalone script on purpose, so that
    it runs on a machine with nothing installed."""
    spec = importlib.util.spec_from_file_location("verify_manifest", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTheWalkRefusesRuntimeState:
    def test_no_packaged_file_is_one_git_ignores(self, verifier):
        patterns = verifier.ignore_patterns()
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in verifier.walk()
            if verifier.is_ignored(path.relative_to(ROOT).as_posix(), patterns)
        ]
        assert offenders == []

    def test_the_two_directories_that_must_never_ship_are_matched(self, verifier):
        """Named rather than left to the general rule, because these two are the
        ones that carry a token cache and a driver's own words."""
        patterns = verifier.ignore_patterns()
        assert verifier.is_ignored(
            "Assistant_Plugin/runtime_data/memory/Data/active/MEM-1.json", patterns
        )
        assert verifier.is_ignored("Assistant_Plugin/logs/joe.log", patterns)

    def test_a_source_file_is_still_packaged(self, verifier):
        """The guard must exclude runtime state without quietly excluding the
        program. A packager that ships nothing also ships no secrets."""
        patterns = verifier.ignore_patterns()
        assert not verifier.is_ignored("Workers/worker_bus/host.py", patterns)
        assert not verifier.is_ignored("Assistant_Plugin/app/main.py", patterns)
        packaged = {p.relative_to(ROOT).as_posix() for p in verifier.walk()}
        assert "Workers/worker_bus/__main__.py" in packaged
        assert "ROOT_MANIFEST.md" not in packaged  # it cannot list itself


class TestTheRulesAreReadRatherThanRestated:
    def test_it_reads_the_repository_gitignore(self, verifier):
        patterns = verifier.ignore_patterns()
        assert "Assistant_Plugin/runtime_data" in patterns
        assert "__pycache__" in patterns

    def test_comments_blanks_and_negations_are_skipped(self, verifier, tmp_path, monkeypatch):
        (tmp_path / ".gitignore").write_text(
            "# a comment\n\nbuild/\n!build/keep.txt\n", encoding="utf-8"
        )
        monkeypatch.setattr(verifier, "GITIGNORE", tmp_path / ".gitignore")
        patterns = verifier.ignore_patterns()
        assert patterns == ["build"]
        # The negation is dropped rather than honoured, so an unsupported rule
        # can only exclude more, never less. `build/keep.txt` stays excluded.
        assert verifier.is_ignored("build/keep.txt", patterns)

    def test_a_missing_gitignore_is_not_an_error(self, verifier, tmp_path, monkeypatch):
        monkeypatch.setattr(verifier, "GITIGNORE", tmp_path / "nothing-here")
        assert verifier.ignore_patterns() == []

    def test_a_bare_name_matches_at_any_depth(self, verifier):
        patterns = ["__pycache__", "*.pyc"]
        assert verifier.is_ignored("a/b/__pycache__/c.txt", patterns)
        assert verifier.is_ignored("a/b/c.pyc", patterns)
        assert not verifier.is_ignored("a/b/c.py", patterns)

    def test_a_rooted_rule_does_not_match_a_similar_name_elsewhere(self, verifier):
        patterns = ["Assistant_Plugin/logs"]
        assert verifier.is_ignored("Assistant_Plugin/logs/joe.log", patterns)
        assert not verifier.is_ignored("Workers/logs/other.log", patterns)

    def test_a_wildcard_segment_is_honoured(self, verifier):
        patterns = ["ASST/*/Tests/_workspace"]
        assert verifier.is_ignored("ASST/1/Tests/_workspace/scratch.txt", patterns)
        assert not verifier.is_ignored("ASST/1/Tests/test_real.py", patterns)


class TestTheManifestOnDisk:
    """Two invariants, and deliberately not a third.

    A file added to the tree makes the manifest stale until somebody runs
    `--write`, and that is what the `EXTRA` report is for. Asserting it here
    would turn every ordinary commit red, so this checks only the two
    differences that mean something went wrong: a listed file that is gone, and
    a listed file that should never have been listed at all.
    """

    def test_it_lists_nothing_git_ignores(self, verifier):
        patterns = verifier.ignore_patterns()
        offenders = [rel for rel in verifier.read_manifest() if verifier.is_ignored(rel, patterns)]
        assert offenders == []

    def test_every_listed_file_is_still_here(self, verifier):
        missing = [rel for rel in verifier.read_manifest() if not (ROOT / rel).is_file()]
        assert missing == []
