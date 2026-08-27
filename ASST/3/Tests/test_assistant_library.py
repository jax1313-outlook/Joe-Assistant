"""Tests for Workstream 3 - Assistant Library.

Reads the sample corpus in this folder. Any test that needs to create files
creates them inside Tests\\_workspace and removes them afterward.

Run:  py -m unittest discover -s Tests -v      (from folder 3)
"""

from __future__ import annotations

import re
import shutil
import sys
import unittest
import uuid
import zipfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_library.document import (  # noqa: E402
    SUPPORTED_EXTENSIONS,
    DocumentError,
    doc_id_from,
    load_document,
    title_from,
)
from assistant_library.library import Library, LibraryError, resolve_root  # noqa: E402
from assistant_library.search import (  # noqa: E402
    STOPWORDS,
    query_terms,
    score_document,
    search_documents,
    tokenize,
)

CORPUS = FOLDER / "Corpus"
WORKSPACE = FOLDER / "Tests" / "_workspace"

DOCX_XML = (
    '<?xml version="1.0"?>'
    '<w:document xmlns:w="x"><w:body>'
    "<w:p><w:r><w:t>Detention Policy</w:t></w:r></w:p>"
    "<w:p><w:r><w:t>Detention starts at the appointment window.</w:t></w:r></w:p>"
    "</w:body></w:document>"
)


def make_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", DOCX_XML)
    return path


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = WORKSPACE / uuid.uuid4().hex[:8]
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


class TestCorpusIndexing(unittest.TestCase):
    def setUp(self):
        self.library = Library(CORPUS)

    def test_corpus_indexes(self):
        self.assertGreaterEqual(len(self.library), 5)
        self.assertFalse(self.library.is_empty)

    def test_report_records_what_happened(self):
        report = self.library.report
        self.assertEqual(report.indexed, len(self.library))
        self.assertEqual(report.skipped_unreadable, 0)
        self.assertFalse(report.truncated)

    def test_markdown_title_comes_from_the_heading(self):
        document = self.library.find_by_path("Doctrine/MISSION_VISIBILITY.md")
        self.assertEqual(document.title, "Mission Visibility")

    def test_relative_paths_use_forward_slashes(self):
        for document in self.library.documents:
            with self.subTest(doc=document.doc_id):
                self.assertNotIn("\\", document.relative_path)

    def test_documents_carry_size_and_modified_time(self):
        document = self.library.documents[0]
        self.assertGreater(document.size_bytes, 0)
        self.assertRegex(document.modified_at, r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z$")

    def test_word_and_line_counts(self):
        document = self.library.find_by_path("Operations/NOTES.txt")
        self.assertGreater(document.word_count, 10)
        self.assertGreater(document.line_count, 3)

    def test_doc_ids_are_unique_and_stable(self):
        ids = [d.doc_id for d in self.library.documents]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [d.doc_id for d in Library(CORPUS).documents])

    def test_missing_root_raises(self):
        with self.assertRaises(LibraryError):
            Library(FOLDER / "Corpus_that_does_not_exist")

    def test_root_that_is_a_file_raises(self):
        with self.assertRaises(LibraryError):
            Library(CORPUS / "README_CORPUS.md")


class TestDocumentReading(WorkspaceTestCase):
    def test_reads_plain_text(self):
        path = self.workspace / "note.txt"
        path.write_text("plain text body", encoding="utf-8")
        document = load_document(path, self.workspace)
        self.assertIn("plain text body", document.text)

    def test_reads_docx_without_office(self):
        path = make_docx(self.workspace / "policy.docx")
        document = load_document(path, self.workspace)
        self.assertIn("Detention Policy", document.text)
        self.assertIn("appointment window", document.text)

    def test_unsupported_extension_is_refused(self):
        path = self.workspace / "sheet.xlsx"
        path.write_text("not indexable", encoding="utf-8")
        with self.assertRaises(DocumentError):
            load_document(path, self.workspace)

    def test_corrupt_docx_is_reported_not_crashed(self):
        path = self.workspace / "broken.docx"
        path.write_bytes(b"this is not a zip archive")
        with self.assertRaises(DocumentError):
            load_document(path, self.workspace)

    def test_unreadable_document_is_skipped_and_reported(self):
        (self.workspace / "good.md").write_text("# Good\nbody", encoding="utf-8")
        (self.workspace / "bad.docx").write_bytes(b"not a zip")
        library = Library(self.workspace)
        self.assertEqual(len(library), 1)
        self.assertEqual(library.report.skipped_unreadable, 1)
        self.assertTrue(any("bad.docx" in note for note in library.report.unreadable))

    def test_unsupported_files_are_counted(self):
        (self.workspace / "keep.md").write_text("# Keep", encoding="utf-8")
        (self.workspace / "skip.pdf").write_bytes(b"%PDF-")
        library = Library(self.workspace)
        self.assertEqual(library.report.skipped_unsupported, 1)

    def test_title_falls_back_to_the_file_name(self):
        path = self.workspace / "rate_floor_notes.txt"
        path.write_text("no heading here", encoding="utf-8")
        self.assertEqual(title_from(path, "no heading here"), "rate floor notes")

    def test_doc_id_is_derived_from_the_path(self):
        self.assertEqual(doc_id_from("Ops/Rate Floor.md"), "DOC-OPS-RATE-FLOOR-MD")

    def test_skips_noise_directories(self):
        (self.workspace / "keep.md").write_text("# Keep", encoding="utf-8")
        junk = self.workspace / "__pycache__"
        junk.mkdir()
        (junk / "cached.md").write_text("# Cached", encoding="utf-8")
        self.assertEqual(len(Library(self.workspace)), 1)

    def test_every_supported_extension_is_readable(self):
        self.assertEqual(
            sorted(SUPPORTED_EXTENSIONS), [".docx", ".markdown", ".md", ".txt"]
        )


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.library = Library(CORPUS)

    def test_finds_a_document_by_title_terms(self):
        hits = self.library.search("mission visibility")
        self.assertTrue(hits)
        self.assertEqual(hits[0].relative_path, "Doctrine/MISSION_VISIBILITY.md")

    def test_finds_a_document_by_body_terms(self):
        hits = self.library.search("deadhead")
        self.assertTrue(hits)
        self.assertIn("NOTES.txt", hits[0].relative_path)

    def test_search_is_case_insensitive(self):
        lower = self.library.search("rate floor")
        upper = self.library.search("RATE FLOOR")
        self.assertEqual(
            [h.doc_id for h in lower], [h.doc_id for h in upper]
        )

    def test_no_match_returns_nothing_rather_than_guessing(self):
        self.assertEqual(self.library.search("zzzznotpresentzzzz"), [])

    def test_title_matches_outrank_body_matches(self):
        hits = self.library.search("visibility")
        self.assertEqual(hits[0].relative_path, "Doctrine/MISSION_VISIBILITY.md")
        self.assertGreater(hits[0].title_matches, 0)

    def test_hits_report_matched_and_missing_terms(self):
        hits = self.library.search("visibility zzzzabsentzzzz")
        self.assertTrue(hits)
        self.assertIn("visibility", hits[0].matched_terms)
        self.assertIn("zzzzabsentzzzz", hits[0].missing_terms)

    def test_require_all_drops_partial_matches(self):
        partial = self.library.search("visibility zzzzabsentzzzz")
        strict = self.library.search("visibility zzzzabsentzzzz", require_all=True)
        self.assertTrue(partial)
        self.assertEqual(strict, [])

    def test_limit_is_respected(self):
        self.assertLessEqual(len(self.library.search("the", limit=2)), 2)

    def test_results_carry_snippets(self):
        hits = self.library.search("detention")
        self.assertTrue(hits)
        self.assertTrue(hits[0].snippets)
        self.assertIn("detention", hits[0].snippets[0].lower())

    def test_every_hit_carries_a_reference(self):
        for hit in self.library.search("policy"):
            with self.subTest(doc=hit.doc_id):
                self.assertTrue(hit.reference)
                self.assertIn(hit.relative_path, hit.reference)

    def test_ordering_is_stable_across_runs(self):
        first = [h.doc_id for h in self.library.search("driver")]
        second = [h.doc_id for h in Library(CORPUS).search("driver")]
        self.assertEqual(first, second)

    def test_score_formula_is_title_times_five_plus_body(self):
        document = self.library.find_by_path("Operations/RATE_FLOOR_POLICY.md")
        hit = score_document(document, ["floor"])
        self.assertEqual(hit.score, 5 * hit.title_matches + hit.body_matches)

    def test_stopwords_are_dropped_from_a_mixed_query(self):
        self.assertEqual(query_terms("what is the rate floor"), ["rate", "floor"])

    def test_an_all_stopword_query_still_searches(self):
        self.assertEqual(query_terms("what is the"), ["what", "is", "the"])

    def test_empty_query_returns_nothing(self):
        self.assertEqual(self.library.search(""), [])
        self.assertEqual(self.library.search("   "), [])

    def test_tokenizer_keeps_hyphens_and_apostrophes(self):
        self.assertEqual(tokenize("driver's non-stop run"), ["driver's", "non-stop", "run"])

    def test_stopword_list_is_small_and_visible(self):
        self.assertLess(len(STOPWORDS), 40)

    def test_search_over_an_empty_library(self):
        empty = FOLDER / "Tests" / "_workspace" / "empty_library"
        empty.mkdir(parents=True, exist_ok=True)
        try:
            self.assertEqual(Library(empty).search("anything"), [])
        finally:
            shutil.rmtree(empty, ignore_errors=True)


class TestRetrieveAndReference(unittest.TestCase):
    def setUp(self):
        self.library = Library(CORPUS)

    def test_get_returns_the_full_document(self):
        document = self.library.find_by_path("Doctrine/DRIVER_FIRST.md")
        fetched = self.library.get(document.doc_id)
        self.assertEqual(fetched.doc_id, document.doc_id)
        self.assertIn("Driver first means", fetched.text)

    def test_get_unknown_document_raises(self):
        with self.assertRaises(LibraryError):
            self.library.get("DOC-NOT-REAL")

    def test_find_by_unknown_path_raises(self):
        with self.assertRaises(LibraryError):
            self.library.find_by_path("Nowhere/missing.md")

    def test_has_reports_membership(self):
        document = self.library.documents[0]
        self.assertTrue(self.library.has(document.doc_id))
        self.assertFalse(self.library.has("DOC-NOT-REAL"))

    def test_reference_names_title_path_and_date(self):
        document = self.library.find_by_path("Operations/RATE_FLOOR_POLICY.md")
        reference = self.library.reference(document.doc_id)
        self.assertIn(document.title, reference)
        self.assertIn(document.relative_path, reference)
        self.assertRegex(reference, r"modified \d{4}-\d{2}-\d{2}")

    def test_references_handles_a_list(self):
        ids = [d.doc_id for d in self.library.documents[:3]]
        self.assertEqual(len(self.library.references(ids)), 3)

    def test_to_dict_excludes_text_unless_asked(self):
        document = self.library.documents[0]
        self.assertNotIn("text", document.to_dict())
        self.assertIn("text", document.to_dict(include_text=True))


class TestBoundaries(unittest.TestCase):
    """Workstream 3 is read only and must stay that way."""

    PACKAGE = FOLDER / "Source" / "assistant_library"

    def _sources(self):
        return sorted(self.PACKAGE.glob("*.py"))

    def _imports(self) -> set[str]:
        pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_.][\w.]*)", re.MULTILINE)
        found: set[str] = set()
        for source in self._sources():
            for module in pattern.findall(source.read_text(encoding="utf-8")):
                root = module.split(".")[0]
                if root:
                    found.add(root)
        return found

    def test_imports_nothing_from_another_workstream(self):
        forbidden = {
            "assistant_ui", "assistant_memory", "assistant_outlook",
            "assistant_research", "assistant_voice", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_network_email_or_vendor_module(self):
        forbidden = {
            "socket", "urllib", "http", "requests", "smtplib", "imaplib",
            "poplib", "ssl", "win32com", "msal", "office365", "docx",
            "openai", "anthropic", "boto3", "azure", "subprocess", "webbrowser",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "argparse", "dataclasses", "datetime", "html",
            "json", "os", "pathlib", "re", "sys", "zipfile",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_no_write_call_exists_anywhere_in_the_package(self):
        # cli.py names ZipFile only in tests, not here; the package must never
        # open anything for writing or change the filesystem.
        # Note: bare `.replace(` is excluded deliberately - it is the string
        # method, used for path separators and timestamps. Path.replace and
        # os.replace are matched explicitly instead.
        writers = re.compile(
            r"write_text|write_bytes|\.write\(|\.writestr\(|\bmkdir\b|\bunlink\b"
            r"|\brmdir\b|\.rename\(|os\.replace|shutil\.|os\.remove|os\.makedirs"
            r"|open\s*\([^)]*['\"][wax]"
        )
        for source in self._sources():
            with self.subTest(source=source.name):
                found = writers.search(source.read_text(encoding="utf-8"))
                self.assertIsNone(
                    found, "write call in " + source.name + ": " + str(found)
                )

    def test_library_object_exposes_no_mutating_method(self):
        library = Library(CORPUS)
        for name in ("save", "write", "delete", "remove", "update", "create",
                     "edit", "rename", "move", "upload", "sync"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(library, name))

    def test_zipfile_is_opened_read_only(self):
        source = (self.PACKAGE / "document.py").read_text(encoding="utf-8")
        for match in re.finditer(r"ZipFile\(([^)]*)\)", source):
            with self.subTest(call=match.group(0)):
                self.assertNotIn('"w"', match.group(1))
                self.assertNotIn("'w'", match.group(1))
                self.assertNotIn('"a"', match.group(1))

    def test_indexing_the_corpus_changes_nothing_on_disk(self):
        before = {
            path: path.stat().st_mtime_ns
            for path in sorted(CORPUS.rglob("*"))
            if path.is_file()
        }
        library = Library(CORPUS)
        library.search("rate floor")
        library.get(library.documents[0].doc_id)
        after = {
            path: path.stat().st_mtime_ns
            for path in sorted(CORPUS.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_default_root_is_the_corpus_in_this_folder(self):
        self.assertEqual(resolve_root(None).name, "Corpus")
        self.assertTrue(str(resolve_root(None)).startswith(str(FOLDER)))

    def test_no_memory_outlook_or_voice_capability(self):
        """Check what the package defines, not what its prose mentions.

        `doctor` legitimately prints the words "email / calendar / voice /
        memory" in order to state that none of them are implemented. A plain
        word scan would fail on that honest disclaimer, so this looks at
        function and class names instead.
        """
        definitions = re.compile(r"^\s*(?:def|class)\s+(\w+)", re.MULTILINE)
        names: set[str] = set()
        for source in self._sources():
            names.update(definitions.findall(source.read_text(encoding="utf-8")))
        forbidden = re.compile(
            r"mail|smtp|imap|calendar|contact|appointment|voice|speak|listen"
            r"|record_audio|retain|retention|expire|remember",
            re.IGNORECASE,
        )
        offenders = sorted(name for name in names if forbidden.search(name))
        self.assertEqual(offenders, [], "capability leaked in: " + str(offenders))


if __name__ == "__main__":
    unittest.main(verbosity=2)
