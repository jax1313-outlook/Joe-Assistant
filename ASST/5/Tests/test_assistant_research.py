"""Tests for Workstream 5 - Assistant Research.

Reads the sample briefs in this folder. Any test needing its own input writes
it inside Tests\\_workspace and removes it afterward.

Run:  py -m unittest discover -s Tests -v      (from folder 5)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import unittest
import uuid
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FOLDER / "Source"))

from assistant_research.analysis import (  # noqa: E402
    CONFIDENCE_MEANING,
    Confidence,
    analyze,
    analyze_topic,
    topics_in,
)
from assistant_research.authority import (  # noqa: E402
    AUTHORITY_STATEMENT,
    FORBIDDEN_PHRASES,
    AuthorityError,
    Recommendation,
    assert_no_authority_claim,
    find_authority_claims,
)
from assistant_research.record import (  # noqa: E402
    RecordError,
    ResearchRecord,
    load_brief,
    load_sources,
    record_from_brief,
    resolve_data_root,
)
from assistant_research.sources import (  # noqa: E402
    Claim,
    Source,
    SourceError,
    SourceKind,
)

DATA = FOLDER / "Data"
BRIEF = DATA / "brief_northbound_lane.json"
SOURCES = DATA / "sources_rate_floor.json"
WORKSPACE = FOLDER / "Tests" / "_workspace"


def source(source_id, kind, *claims, **extra):
    payload = {
        "source_id": source_id,
        "title": extra.get("title", source_id),
        "kind": kind,
        "origin": extra.get("origin", "test"),
        "claims": [
            {"topic": topic, "statement": statement, "supports": supports}
            for topic, statement, supports in claims
        ],
    }
    return Source.from_dict(payload)


class TestSources(unittest.TestCase):
    def test_source_requires_an_id(self):
        with self.assertRaises(SourceError):
            Source.from_dict({"title": "no id"})

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(SourceError):
            Source.from_dict({"source_id": "S1", "kind": "gossip"})

    def test_every_kind_has_a_standing(self):
        for kind in SourceKind.ALL:
            with self.subTest(kind=kind):
                built = Source.from_dict({"source_id": "S1", "kind": kind})
                self.assertTrue(built.standing)

    def test_only_company_material_is_approved_company_truth(self):
        for kind in SourceKind.ALL:
            with self.subTest(kind=kind):
                built = Source.from_dict({"source_id": "S1", "kind": kind})
                self.assertEqual(
                    built.is_approved_company_truth, kind == SourceKind.COMPANY
                )

    def test_public_source_is_never_approved_truth(self):
        built = Source.from_dict({"source_id": "S1", "kind": SourceKind.PUBLIC})
        self.assertFalse(built.is_approved_company_truth)
        self.assertIn("not approved company truth", built.standing)

    def test_claim_requires_topic_and_statement(self):
        for bad in [{"topic": "t"}, {"statement": "s"}, {"topic": "", "statement": "s"}]:
            with self.subTest(payload=bad):
                with self.assertRaises(SourceError):
                    Claim.from_dict(bad)

    def test_claims_default_to_supporting(self):
        claim = Claim.from_dict({"topic": "t", "statement": "s"})
        self.assertTrue(claim.supports)

    def test_contradicting_claims_are_kept(self):
        claim = Claim.from_dict({"topic": "t", "statement": "s", "supports": False})
        self.assertFalse(claim.supports)

    def test_unreadable_timestamp_raises(self):
        with self.assertRaises(SourceError):
            Source.from_dict({"source_id": "S1", "retrieved_at": "not a date"})

    def test_citation_names_title_origin_and_date(self):
        built = Source.from_dict({
            "source_id": "S1", "title": "Rate Index",
            "origin": "https://example.invalid/x",
            "retrieved_at": "2026-08-23T14:30:00Z",
        })
        citation = built.citation()
        self.assertIn("Rate Index", citation)
        self.assertIn("example.invalid", citation)
        self.assertIn("2026-08-23", citation)

    def test_topics_are_listed_in_first_seen_order(self):
        built = source("S1", SourceKind.PUBLIC,
                       ("b", "s1", True), ("a", "s2", True), ("b", "s3", True))
        self.assertEqual(built.topics(), ["b", "a"])

    def test_sources_are_frozen(self):
        built = source("S1", SourceKind.PUBLIC, ("t", "s", True))
        with self.assertRaises(Exception):
            built.source_id = "changed"  # type: ignore[misc]


class TestAnalysis(unittest.TestCase):
    TOPIC = "the lane clears the floor"

    def test_two_supporting_sources_confirm(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.OPERATIONAL, (self.TOPIC, "also yes", True)),
        ])
        self.assertEqual(finding.confidence, Confidence.CONFIRMED)
        self.assertEqual(finding.support_count, 2)

    def test_one_supporting_source_is_supported_only(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
        ])
        self.assertEqual(finding.confidence, Confidence.SUPPORTED)

    def test_disagreement_is_contested(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.PUBLIC, (self.TOPIC, "no", False)),
        ])
        self.assertEqual(finding.confidence, Confidence.CONTESTED)
        self.assertEqual(finding.support_count, 1)
        self.assertEqual(finding.contradiction_count, 1)

    def test_company_material_does_not_win_a_contest_automatically(self):
        # Approved company material outranks a public source in *standing*,
        # never in arithmetic. Disagreement stays disagreement.
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.PERSONAL, (self.TOPIC, "no", False)),
        ])
        self.assertEqual(finding.confidence, Confidence.CONTESTED)

    def test_only_contradiction_is_contradicted(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.PUBLIC, (self.TOPIC, "no", False)),
        ])
        self.assertEqual(finding.confidence, Confidence.CONTRADICTED)

    def test_no_source_is_unsupported(self):
        finding = analyze_topic("nobody mentions this", [
            source("S1", SourceKind.PUBLIC, (self.TOPIC, "yes", True)),
        ])
        self.assertEqual(finding.confidence, Confidence.UNSUPPORTED)
        self.assertEqual(finding.support_count, 0)

    def test_every_confidence_level_has_a_meaning(self):
        for level in Confidence.ALL:
            with self.subTest(level=level):
                self.assertTrue(CONFIDENCE_MEANING[level])

    def test_every_finding_states_an_uncertainty(self):
        sources = [
            source("S1", SourceKind.COMPANY, ("a", "yes", True)),
            source("S2", SourceKind.PUBLIC, ("a", "no", False), ("b", "yes", True)),
        ]
        for finding in analyze(sources) + [analyze_topic("unseen", sources)]:
            with self.subTest(topic=finding.topic):
                self.assertTrue(finding.uncertainty.strip())

    def test_contested_uncertainty_says_it_is_not_settled(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.PUBLIC, (self.TOPIC, "no", False)),
        ])
        self.assertIn("not settled", finding.uncertainty)

    def test_single_source_uncertainty_says_so(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
        ])
        self.assertIn("single source", finding.uncertainty)

    def test_agreement_without_company_material_is_noted(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.PUBLIC, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.PERSONAL, (self.TOPIC, "yes", True)),
        ])
        self.assertEqual(finding.confidence, Confidence.CONFIRMED)
        self.assertTrue(finding.rests_only_on_public_or_personal)
        self.assertIn("Research is not doctrine", finding.uncertainty)

    def test_finding_flags_approved_company_material(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
        ])
        self.assertTrue(finding.rests_on_approved_company_material)
        self.assertFalse(finding.rests_only_on_public_or_personal)

    def test_findings_never_claim_doctrine_or_decision(self):
        sources = [source("S1", SourceKind.COMPANY, ("a", "yes", True))]
        for finding in analyze(sources):
            data = finding.to_dict()
            with self.subTest(topic=finding.topic):
                self.assertFalse(data["is_approved_doctrine"])
                self.assertFalse(data["is_a_decision"])

    def test_findings_carry_citations(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True), title="Policy"),
        ])
        self.assertTrue(finding.citations())
        self.assertIn("Policy", finding.citations()[0])

    def test_contradicting_evidence_is_never_dropped(self):
        finding = analyze_topic(self.TOPIC, [
            source("S1", SourceKind.COMPANY, (self.TOPIC, "yes", True)),
            source("S2", SourceKind.PUBLIC, (self.TOPIC, "the contrary view", False)),
        ])
        statements = [entry["statement"] for entry in finding.contradicting]
        self.assertIn("the contrary view", statements)

    def test_topic_ordering_is_stable(self):
        sources = [
            source("S1", SourceKind.PUBLIC, ("z", "s", True), ("a", "s", True)),
            source("S2", SourceKind.PUBLIC, ("m", "s", True)),
        ]
        self.assertEqual(topics_in(sources), ["z", "a", "m"])
        self.assertEqual([f.topic for f in analyze(sources)], ["z", "a", "m"])

    def test_analyze_with_no_sources(self):
        self.assertEqual(analyze([]), [])

    def test_is_settled_only_for_confirmed_and_supported(self):
        settled = {Confidence.CONFIRMED, Confidence.SUPPORTED}
        for level in Confidence.ALL:
            finding = analyze_topic("t", [])
            finding.confidence = level
            with self.subTest(level=level):
                self.assertEqual(finding.is_settled, level in settled)


class TestAuthority(unittest.TestCase):
    def test_a_plain_recommendation_is_allowed(self):
        rec = Recommendation(statement="Recommend a four week trial, then review.")
        self.assertTrue(rec.is_recommendation_only)
        self.assertTrue(rec.uses_recommending_language)

    def test_approval_language_is_refused(self):
        for text in [
            "I approve the lane.",
            "We approve this rate.",
            "The decision is to run it.",
            "I authorize the counter.",
            "This is now policy.",
        ]:
            with self.subTest(text=text):
                with self.assertRaises(AuthorityError):
                    Recommendation(statement=text)

    def test_action_claims_are_refused(self):
        for text in [
            "I have booked the load.",
            "Load accepted at 2.40.",
            "Email sent to the broker.",
            "Payment sent this morning.",
            "I dispatched the driver.",
        ]:
            with self.subTest(text=text):
                with self.assertRaises(AuthorityError):
                    Recommendation(statement=text)

    def test_doctrine_change_claims_are_refused(self):
        for text in ["Doctrine is updated.", "Policy is changed.", "This becomes doctrine."]:
            with self.subTest(text=text):
                with self.assertRaises(AuthorityError):
                    Recommendation(statement=text)

    def test_refusal_applies_to_the_rationale_too(self):
        with self.assertRaises(AuthorityError):
            Recommendation(statement="Recommend a trial.", rationale="I approve it anyway.")

    def test_refusal_is_case_insensitive(self):
        with self.assertRaises(AuthorityError):
            Recommendation(statement="I APPROVE the lane.")

    def test_an_empty_recommendation_is_refused(self):
        for text in ["", "   "]:
            with self.subTest(text=repr(text)):
                with self.assertRaises(AuthorityError):
                    Recommendation(statement=text)

    def test_flags_are_always_false(self):
        rec = Recommendation(statement="Consider a trial.")
        data = rec.to_dict()
        for key in ("approved", "decided", "acted_on", "doctrine_changed"):
            with self.subTest(key=key):
                self.assertFalse(data[key])
        self.assertTrue(data["is_recommendation_only"])

    def test_flags_cannot_be_flipped_in_the_output(self):
        rec = Recommendation(statement="Consider a trial.")
        rec.approved = True          # even if someone sets the attribute...
        rec.decided = True
        rec.doctrine_changed = True
        data = rec.to_dict()         # ...the reported record is still honest
        self.assertFalse(data["approved"])
        self.assertFalse(data["decided"])
        self.assertFalse(data["doctrine_changed"])

    def test_decision_is_always_referred_to_mike(self):
        rec = Recommendation(statement="Consider a trial.")
        self.assertEqual(rec.decision_required_from, "Mike Zachary")

    def test_open_questions_are_carried(self):
        rec = Recommendation(
            statement="Consider a trial.", open_questions=["What does fuel do?"]
        )
        self.assertEqual(rec.to_dict()["open_questions"], ["What does fuel do?"])

    def test_find_authority_claims_reports_every_match(self):
        found = find_authority_claims("I approve this and I have booked the load.")
        self.assertIn("i approve", found)
        self.assertIn("booked the load", found)

    def test_clean_text_reports_no_claims(self):
        self.assertEqual(find_authority_claims("Recommend reviewing in four weeks."), [])

    def test_assert_helper_passes_clean_text(self):
        assert_no_authority_claim("Suggest a trial period.")

    def test_the_forbidden_list_is_substantial_and_visible(self):
        self.assertGreater(len(FORBIDDEN_PHRASES), 20)

    def test_the_authority_statement_names_the_boundary(self):
        for phrase in ("may recommend", "may not approve", "Mike Zachary"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, AUTHORITY_STATEMENT)


class TestRecord(unittest.TestCase):
    def setUp(self):
        self.record = record_from_brief(load_brief(BRIEF))

    def test_the_sample_brief_builds(self):
        self.assertEqual(len(self.record.sources), 3)
        self.assertEqual(len(self.record.findings), 3)

    def test_a_record_needs_a_question(self):
        with self.assertRaises(RecordError):
            ResearchRecord.build(question="  ", sources=[])

    def test_confidence_is_assigned_per_topic(self):
        levels = {f.topic: f.confidence for f in self.record.findings}
        self.assertEqual(levels["lane clears the recorded floor"], Confidence.CONFIRMED)
        self.assertEqual(
            levels["volume is steady enough to dedicate"], Confidence.CONTESTED
        )
        self.assertEqual(levels["deadhead is acceptable"], Confidence.SUPPORTED)

    def test_contested_findings_are_listed(self):
        self.assertEqual(len(self.record.contested), 1)

    def test_settled_findings_are_listed(self):
        self.assertEqual(len(self.record.settled), 2)

    def test_every_finding_produces_an_uncertainty(self):
        self.assertEqual(len(self.record.uncertainties), len(self.record.findings))
        for item in self.record.uncertainties:
            with self.subTest(topic=item["topic"]):
                self.assertTrue(item["uncertainty"].strip())

    def test_citations_are_collected_without_duplicates(self):
        citations = self.record.citations()
        self.assertEqual(len(citations), len(set(citations)))
        self.assertEqual(len(citations), 3)

    def test_source_kinds_are_counted(self):
        counts = self.record.source_kind_counts()
        self.assertEqual(counts[SourceKind.COMPANY], 1)
        self.assertEqual(counts[SourceKind.OPERATIONAL], 1)
        self.assertEqual(counts[SourceKind.PUBLIC], 1)

    def test_record_reports_whether_company_material_is_involved(self):
        self.assertTrue(self.record.rests_on_approved_company_material)

    def test_the_record_never_claims_doctrine_or_decision(self):
        data = self.record.to_dict()
        self.assertFalse(data["is_approved_doctrine"])
        self.assertFalse(data["is_a_decision"])
        self.assertEqual(data["decision_required_from"], "Mike Zachary")

    def test_the_recommendation_is_carried_and_flagged(self):
        rec = self.record.to_dict()["recommendation"]
        self.assertIsNotNone(rec)
        self.assertTrue(rec["is_recommendation_only"])
        self.assertFalse(rec["approved"])
        self.assertEqual(len(rec["open_questions"]), 2)

    def test_render_states_the_authority_boundary(self):
        rendered = self.record.render()
        self.assertIn("may not approve", rendered)
        self.assertIn("Mike Zachary", rendered)

    def test_render_shows_contradicting_evidence(self):
        self.assertIn("CONTRADICTS", self.record.render())

    def test_render_marks_findings_without_company_backing(self):
        self.assertIn("no approved company material supports this", self.record.render())

    def test_render_declares_the_recommendation_as_not_decided(self):
        rendered = self.record.render()
        self.assertIn("recommendation only", rendered)
        self.assertIn("approved=False", rendered)

    def test_standalone_source_file_loads_and_analyzes(self):
        sources = load_sources(SOURCES)
        record = ResearchRecord.build(question="Should we hold the floor?", sources=sources)
        self.assertEqual(len(record.findings), 1)
        self.assertEqual(record.findings[0].confidence, Confidence.CONTESTED)

    def test_default_data_root_is_this_folder(self):
        self.assertEqual(resolve_data_root(None).name, "Data")
        self.assertTrue(str(resolve_data_root(None)).startswith(str(FOLDER)))


class TestRecordEdges(unittest.TestCase):
    def setUp(self):
        self.workspace = WORKSPACE / uuid.uuid4().hex[:8]
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def write(self, name, payload, raw=None):
        path = self.workspace / name
        path.write_text(
            raw if raw is not None else json.dumps(payload), encoding="utf-8"
        )
        return path

    def test_missing_file_raises(self):
        with self.assertRaises(RecordError):
            load_sources(self.workspace / "nothing.json")
        with self.assertRaises(RecordError):
            load_brief(self.workspace / "nothing.json")

    def test_malformed_json_raises(self):
        path = self.write("bad.json", None, raw="{ not json")
        with self.assertRaises(RecordError):
            load_sources(path)

    def test_sources_file_must_be_a_list(self):
        path = self.write("obj.json", {"source_id": "S1"})
        with self.assertRaises(RecordError):
            load_sources(path)

    def test_brief_must_be_an_object(self):
        path = self.write("list.json", [1, 2, 3])
        with self.assertRaises(RecordError):
            load_brief(path)

    def test_a_bad_source_in_a_file_raises_with_context(self):
        path = self.write("bad_source.json", [{"title": "no id"}])
        with self.assertRaises(RecordError) as caught:
            load_sources(path)
        self.assertIn("bad_source.json", str(caught.exception))

    def test_a_brief_with_no_sources_still_builds(self):
        record = record_from_brief({"question": "Anything known?", "sources": []})
        self.assertEqual(record.findings, [])
        self.assertEqual(record.citations(), [])
        self.assertIn("No findings", record.render())

    def test_a_brief_with_approval_language_is_refused(self):
        with self.assertRaises(AuthorityError):
            record_from_brief({
                "question": "Run the lane?",
                "sources": [],
                "recommendation": {"statement": "I approve running the lane."},
            })


class TestBoundaries(unittest.TestCase):
    PACKAGE = FOLDER / "Source" / "assistant_research"

    def _sources(self):
        return sorted(self.PACKAGE.glob("*.py"))

    def _imports(self) -> set[str]:
        pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z_.][\w.]*)", re.MULTILINE)
        found: set[str] = set()
        for source_file in self._sources():
            for module in pattern.findall(source_file.read_text(encoding="utf-8")):
                root = module.split(".")[0]
                if root:
                    found.add(root)
        return found

    def test_imports_nothing_from_another_workstream(self):
        forbidden = {
            "assistant_ui", "assistant_memory", "assistant_library",
            "assistant_outlook", "assistant_voice", "sandbox_engine",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_imports_no_network_or_vendor_module(self):
        forbidden = {
            "socket", "urllib", "http", "requests", "httpx", "ssl", "ftplib",
            "smtplib", "imaplib", "win32com", "msal", "office365", "openai",
            "anthropic", "boto3", "azure", "subprocess", "webbrowser",
            "selenium", "bs4",
        }
        self.assertEqual(self._imports() & forbidden, set())

    def test_uses_only_the_standard_library(self):
        allowed = {
            "__future__", "argparse", "dataclasses", "datetime", "json",
            "os", "pathlib", "re", "sys",
        }
        self.assertEqual(self._imports() - allowed, set())

    def test_nothing_fetches_or_browses(self):
        joined = " ".join(s.read_text(encoding="utf-8") for s in self._sources())
        for word in ("urlopen", "requests.get", "fetch(", "http://", "download"):
            with self.subTest(word=word):
                self.assertNotIn(word, joined)

    def test_no_approval_or_decision_method_exists(self):
        record = record_from_brief(load_brief(BRIEF))
        for name in ("approve", "decide", "authorize", "accept_load", "dispatch",
                     "commit", "pay", "send", "publish", "set_doctrine",
                     "update_policy"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(record, name))
                if record.recommendation:
                    self.assertFalse(hasattr(record.recommendation, name))

    def test_no_write_call_exists_anywhere_in_the_package(self):
        writers = re.compile(
            r"write_text|write_bytes|\.write\(|\bmkdir\b|\bunlink\b|\brmdir\b"
            r"|\.rename\(|os\.replace|shutil\.|os\.remove|os\.makedirs"
            r"|open\s*\([^)]*['\"][wax]"
        )
        for source_file in self._sources():
            with self.subTest(source=source_file.name):
                self.assertIsNone(
                    writers.search(source_file.read_text(encoding="utf-8"))
                )

    def test_reading_a_brief_changes_nothing_on_disk(self):
        before = {
            path: path.stat().st_mtime_ns
            for path in sorted(DATA.rglob("*")) if path.is_file()
        }
        record_from_brief(load_brief(BRIEF)).render()
        after = {
            path: path.stat().st_mtime_ns
            for path in sorted(DATA.rglob("*")) if path.is_file()
        }
        self.assertEqual(before, after)

    def test_research_is_never_reported_as_doctrine(self):
        record = record_from_brief(load_brief(BRIEF))
        data = record.to_dict()
        self.assertFalse(data["is_approved_doctrine"])
        for finding in data["findings"]:
            with self.subTest(topic=finding["topic"]):
                self.assertFalse(finding["is_approved_doctrine"])
                self.assertFalse(finding["is_a_decision"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
