"""Reading a listing to JOE one field at a time — against Dispatch's own form.

**Owner ruling, 2026-09-08.** He asked *"How can Joe not know the forms that are
in the company library?"* and then *"build B, publish the template from
Dispatch."*

JOE's eleven invented fields and eleven invented questions were **deleted, not
synchronised.** These tests are mostly about that deletion holding: the form
arrives from Dispatch, and nothing here may quietly grow a second one.

The published shape is a fixture rather than a live call -- JOE's suite must not
need a running node -- and `test_the_fixture_matches_what_dispatch_publishes`
in Dispatch's own suite is what keeps the fixture honest.
"""

from __future__ import annotations

import pytest

from app import field_capture as fc
from app.co_driver import _is_bare_wake


PUBLISHED = {
    "ok": True,
    "sections": ["MISSION SOURCE", "LOAD CONTROL", "PICKUP", "DELIVERY", "CARGO"],
    "capture_only": [{"key": "source_board", "label": "Board",
                      "spoken": "Which board is it on?", "hint": ""}],
    "fields": [
        {"key": "customer", "label": "Customer / Shipper / Broker",
         "section": "MISSION SOURCE", "required": True, "hint": "",
         "spoken": "Who is the customer, shipper or broker?", "choices": [],
         "opportunity_field": ""},
        {"key": "customer_poc", "label": "Their contact",
         "section": "MISSION SOURCE", "required": False, "hint": "",
         "spoken": "Who is the contact there?", "choices": [],
         "opportunity_field": "contact"},
        {"key": "load_number", "label": "Load number (theirs)",
         "section": "LOAD CONTROL", "required": False, "hint": "",
         "spoken": "Do they have a load number for it?", "choices": [],
         "opportunity_field": ""},
        {"key": "service", "label": "Service type", "section": "LOAD CONTROL",
         "required": False, "hint": "", "spoken": "What kind of run is it?",
         "choices": ["LTL Freight", "Courier", "Medical"],
         "opportunity_field": "equipment"},
        {"key": "rate", "label": "Rate", "section": "LOAD CONTROL",
         "required": True, "hint": "", "spoken": "What does it pay?",
         "choices": [], "opportunity_field": "rate"},
        {"key": "pickup_location", "label": "Pickup facility and address",
         "section": "PICKUP", "required": True, "hint": "",
         "spoken": "Where does the truck load?", "choices": [],
         "opportunity_field": "origin"},
        {"key": "pickup_window", "label": "Pickup window", "section": "PICKUP",
         "required": False, "hint": "", "spoken": "When can it be picked up?",
         "choices": [], "opportunity_field": "pickup_date"},
        {"key": "delivery_location", "label": "Delivery facility and address",
         "section": "DELIVERY", "required": True, "hint": "",
         "spoken": "Where does it deliver?", "choices": [],
         "opportunity_field": "destination"},
        {"key": "cargo_lines", "label": "Cargo", "section": "CARGO",
         "required": False, "hint": "", "spoken": "What is the freight?",
         "choices": [], "opportunity_field": "pieces_weight"},
        {"key": "notes", "label": "Notes", "section": "CARGO",
         "required": False, "hint": "", "spoken": "Anything else?",
         "choices": [], "opportunity_field": "notes"},
    ],
    "opportunity": {
        "fields": ["source_board", "origin", "destination", "rate",
                   "pieces_weight", "equipment", "pickup_date",
                   "delivery_date", "contact", "notes", "captured_via"],
        "required": ["source_board", "origin", "destination", "rate"],
        "dictation_order": [],
    },
}


@pytest.fixture
def capture():
    return fc.Capture(PUBLISHED, channel="VOICE")


class TestTheFormComesFromDispatch:
    """**The deletion, held in place.** JOE knows no fields of its own."""

    def test_the_module_declares_no_field_list(self):
        for gone in ("FIELD_ORDER", "REQUIRED", "LABEL_FOR", "ASKS",
                     "NOT_IN_CONTRACT", "LABELS"):
            assert not hasattr(fc, gone), (
                "%s came back -- the form belongs to Dispatch" % gone)

    def test_the_fields_are_the_published_ones(self, capture):
        assert capture.order[1:] == tuple(f["key"] for f in PUBLISHED["fields"])

    def test_the_question_is_the_form_s_own_words(self, capture):
        capture.go_to("customer")
        assert capture.asking == "Who is the customer, shipper or broker?"

    def test_the_choices_are_offered_because_the_form_gave_them(self, capture):
        capture.go_to("service")
        assert capture.choices == ("LTL Freight", "Courier", "Medical")

    def test_what_the_contract_requires_arrives_with_the_form(self, capture):
        """**Dispatch decides what is required, not JOE.**"""
        assert capture.contract_required == ("source_board", "origin",
                                             "destination", "rate")

    def test_no_form_means_no_capture_and_no_remembered_copy(self):
        """A cached form is the defect this rewrite removed, with a longer
        fuse."""
        with pytest.raises(fc.NoForm):
            fc.Capture({"mode": "UNAVAILABLE", "note": "Dispatch did not answer"})


class TestSynonymsAreVocabularyNotStructure:
    def test_every_synonym_names_a_field_the_form_has(self, capture):
        """Checked at runtime, so a field renamed in Dispatch fails loudly here
        instead of quietly matching nothing and looking like a recognition
        problem."""
        known = set(capture.by_key)
        for key in fc.SYNONYMS:
            if key in known:
                continue
            assert key in capture.unknown_synonyms

    def test_an_unknown_synonym_is_reported(self):
        published = dict(PUBLISHED)
        published["fields"] = [f for f in PUBLISHED["fields"]
                               if f["key"] != "cargo_lines"]
        assert "cargo_lines" in fc.Capture(published).unknown_synonyms

    def test_synonyms_add_no_field(self, capture):
        assert set(capture.by_key) <= (
            {f["key"] for f in PUBLISHED["fields"]} | {"source_board"})


class TestNamingAField:
    @pytest.mark.parametrize("spoken,key,value", [
        ("board, DAT", "source_board", "DAT"),
        ("broker, XPO Logistics", "customer", "XPO Logistics"),
        ("origin, Savannah Georgia", "pickup_location", "Savannah Georgia"),
        ("destination, Tampa", "delivery_location", "Tampa"),
        ("rate, twenty two hundred", "rate", "twenty two hundred"),
        ("load number, BCDH56238", "load_number", "BCDH56238"),
        ("equipment, dry van", "service", "dry van"),
    ])
    def test_a_synonym_finds_the_field(self, capture, spoken, key, value):
        assert capture.name_of(spoken) == (key, value)

    def test_the_form_s_own_label_works_too(self, capture):
        assert capture.name_of("their contact, Jeff")[0] == "customer_poc"

    @pytest.mark.parametrize("spoken", [
        "Savannah Georgia", "twenty two hundred", "the weather is nice",
    ])
    def test_an_unlabelled_phrase_is_refused_not_filed(self, capture, spoken):
        """**A value in the wrong field is worse than a value missing**, because
        a gap is visible on the card and a wrong lane is not."""
        with pytest.raises(fc.NothingRecognised):
            capture.name_of(spoken)


class TestMikeMovesTheCursor:
    def test_a_field_takes_as_many_breaths_as_it_takes(self, capture):
        capture.go_to("pickup_location")
        capture.add("1472 Highway 516")
        capture.add("Savannah, Georgia")
        assert capture.values["pickup_location"] == "1472 Highway 516 Savannah, Georgia"

    def test_speaking_does_not_move_him_on(self, capture):
        here = capture.field
        capture.add("something")
        assert capture.field == here

    def test_it_starts_on_the_capture_time_question(self, capture):
        """Which board is not a fact about the freight, so the Mission Card does
        not carry it -- and without it the contract would refuse every capture
        read off the card."""
        assert capture.field == "source_board"
        assert capture.asking == "Which board is it on?"

    def test_it_cannot_walk_off_either_end(self, capture):
        assert capture.retreat() == "source_board"
        for _ in range(len(capture.order) + 5):
            capture.advance()
        assert capture.field == capture.order[-1]


class TestWhatGoesToDispatch:
    def _full(self, capture):
        for spoken in ("board, DAT", "origin, Savannah", "destination, Tampa",
                       "rate, twenty two hundred"):
            key, value = capture.name_of(spoken)
            capture.go_to(key)
            capture.add(value)
        return capture

    def test_nothing_is_missing_once_the_contract_is_satisfied(self, capture):
        assert self._full(capture).missing == []

    def test_the_contract_field_names_are_used_not_the_card_s(self, capture):
        payload = self._full(capture).payload()
        assert payload["origin"] == "Savannah"
        assert "pickup_location" not in payload

    def test_a_spoken_rate_arrives_as_a_number(self, capture):
        assert self._full(capture).payload()["rate"] == 2200.0

    def test_a_field_the_contract_cannot_carry_is_kept_in_notes(self, capture):
        capture.go_to("load_number")
        capture.add("BCDH56238")
        notes = capture.payload()["notes"]
        assert "BCDH56238" in notes and "Load number" in notes

    def test_the_customer_is_kept_even_though_the_contract_has_no_field(self, capture):
        """The card's "Customer / Shipper / Broker" maps to nothing in the
        seventh contract -- only "Their contact" does. Losing the company name
        because a contract has not caught up would be the program deciding what
        matters."""
        capture.go_to("customer")
        capture.add("XPO Logistics")
        assert "XPO Logistics" in capture.payload()["notes"]

    def test_what_was_heard_is_kept(self, capture):
        capture.go_to("rate")
        capture.add("twenty two hundred")
        assert "twenty two hundred" in capture.payload()["raw_dictation"]


class TestTheCard:
    def test_it_shows_where_he_is(self, capture):
        capture.go_to("rate")
        marked = [l for l in capture.lines() if l.strip().startswith(">")]
        assert len(marked) == 1 and "Rate" in marked[0]

    def test_it_does_not_print_thirty_three_empty_rows(self, capture):
        """A glance is the point. Filled, current, and still-needed -- nothing
        else, unless everything is asked for."""
        assert len(capture.lines()) < len(capture.lines(everything=True))

    def test_it_names_what_is_still_needed(self, capture):
        assert "still needed" in "\n".join(capture.lines())


class TestTheCommands:
    @pytest.mark.parametrize("spoken,expected", [
        ("next", "NEXT"), ("Next field.", "NEXT"), ("move on", "NEXT"),
        ("skip", "SKIP"), ("back", "BACK"), ("done", "DONE"), ("Done!", "DONE"),
        ("cancel", "CANCEL"), ("scratch that", "SCRATCH"),
        ("DAT", ""), ("Savannah, Georgia", ""),
    ])
    def test_one_reader_decides(self, spoken, expected):
        assert fc.command(spoken) == expected

    def test_no_command_is_also_a_field_name(self, capture):
        for spoken in fc.NEXT + fc.SKIP + fc.BACK + fc.DONE + fc.CANCEL:
            with pytest.raises(fc.NothingRecognised):
                capture.name_of(spoken)


class TestWhichModeMikeGets:
    @pytest.mark.parametrize("spoken", ["Log this.", "Log this one.", "log it"])
    def test_the_bare_wake_phrase_starts_a_field_by_field_read(self, spoken):
        assert _is_bare_wake(spoken)

    def test_a_whole_listing_stays_a_one_shot_capture(self):
        assert not _is_bare_wake("Log this one. DAT, Jacksonville to Tampa, $750")
