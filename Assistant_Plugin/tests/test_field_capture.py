"""Reading a listing to JOE one field at a time.

**The Owner's working method, 2026-09-08:** open a listing on a load board, say
*"log this"*, and read it out field by field while the card fills in a window
beside it.

Every phrase in this file is one a person would actually say to a screen. The
ones that matter most are the refusals: **a value in the wrong field is worse
than a value missing**, because a gap is visible on the card and a wrong lane is
not.
"""

from __future__ import annotations

import pytest

from app import field_capture as fc
from app.co_driver import _is_bare_wake


class TestOneFieldAtATime:
    @pytest.mark.parametrize("spoken,field,value", [
        ("board, DAT", "source_board", "DAT"),
        ("load board, Truckstop", "source_board", "Truckstop"),
        ("broker name, XPO Logistics", "contact", "XPO Logistics"),
        ("customer, Penske Logistics", "contact", "Penske Logistics"),
        ("origin, Savannah, Georgia", "origin", "Savannah, Georgia"),
        ("destination, Tampa, Florida", "destination", "Tampa, Florida"),
        ("equipment, dry van", "equipment", "dry van"),
        ("rate, twenty two hundred", "rate", "twenty two hundred"),
        ("pickup date, Thursday", "pickup_date", "Thursday"),
        ("delivery date, Friday", "delivery_date", "Friday"),
        ("notes, driver assist unload", "notes", "driver assist unload"),
    ])
    def test_a_labelled_field_lands_where_it_was_named(self, spoken, field, value):
        assert fc.split_label(spoken) == (field, value)

    def test_the_longer_label_wins(self):
        """"Pickup date" must never lose to "pickup", or a Thursday becomes a
        place."""
        assert fc.split_label("pickup date, Thursday")[0] == "pickup_date"

    def test_an_address_read_the_way_it_is_written(self):
        """Measured on the recognizer: "fourteen seventy two Highway five one
        six" comes back as "1472 Highway 516". The label survives and so do the
        numbers."""
        field, value = fc.split_label("address, 1472 Highway 516, Savannah, Georgia")
        assert field == "origin"
        assert value == "1472 Highway 516, Savannah, Georgia"


class TestItNeverGuesses:
    """**The rule this module is built around.** JOE files what it was told and
    refuses what it was not."""

    @pytest.mark.parametrize("spoken", [
        "Savannah Georgia",
        "twenty two hundred",
        "the weather is nice",
        "it says something about a lumper fee",
    ])
    def test_an_unlabelled_phrase_is_refused_not_filed(self, spoken):
        with pytest.raises(fc.NothingRecognised):
            fc.split_label(spoken)

    def test_a_label_with_nothing_after_it_is_refused(self):
        with pytest.raises(fc.NothingRecognised):
            fc.split_label("rate,")

    def test_a_refusal_changes_nothing(self):
        capture = fc.Capture()
        capture.apply("board, DAT")
        with pytest.raises(fc.NothingRecognised):
            capture.apply("some rambling with no field in it")
        assert capture.fields["source_board"] == "DAT"
        assert capture.last_filled == "source_board"


class TestCorrectingWhatItHeard:
    def test_scratch_that_clears_the_field_just_filled(self):
        """What a person says the moment the read-back comes out wrong."""
        capture = fc.Capture()
        capture.apply("board, DAT")
        capture.apply("origin, Savannah")
        assert capture.scratch() == "origin"
        assert capture.fields["origin"] == ""
        assert capture.fields["source_board"] == "DAT"

    def test_scratching_twice_does_not_walk_backwards(self):
        """One undo, not a history. Reaching further back means Mike loses a
        field he cannot see going."""
        capture = fc.Capture()
        capture.apply("board, DAT")
        capture.apply("origin, Savannah")
        capture.scratch()
        assert capture.scratch() == ""
        assert capture.fields["source_board"] == "DAT"

    def test_saying_a_field_again_replaces_it(self):
        capture = fc.Capture()
        capture.apply("origin, Savannah")
        capture.apply("origin, Ocala")
        assert capture.fields["origin"] == "Ocala"

    def test_a_spelled_name_is_taken_over_what_was_heard(self):
        """The Owner's own fix for a word the model has never met."""
        capture = fc.Capture(channel="VOICE")
        capture.apply("origin, Picketville, PICKETTVILLE, Road")
        assert "Pickettville" in capture.fields["origin"]


class TestWhatGoesToDispatch:
    def test_a_spoken_rate_reaches_dispatch_as_a_number(self):
        """"Twenty two hundred" has to arrive as 2200. The conversion already
        exists in the one-shot parser and is reused rather than rewritten."""
        capture = fc.Capture()
        capture.apply("board, DAT")
        capture.apply("origin, Ocala")
        capture.apply("destination, Tampa")
        capture.apply("rate, twenty two hundred")
        assert capture.payload()["rate"] == 2200.0

    def test_empty_fields_are_not_sent(self):
        capture = fc.Capture()
        capture.apply("board, DAT")
        assert "notes" not in capture.payload()

    def test_the_channel_travels_with_it(self):
        assert fc.Capture(channel="VOICE").payload()["captured_via"] == "VOICE"

    def test_what_was_heard_is_kept(self):
        """Every utterance, in order. If a capture turns out wrong, the record
        of what was actually said is the only way to find out why."""
        capture = fc.Capture()
        capture.apply("board, DAT")
        capture.apply("origin, Ocala")
        assert "board, DAT" in capture.payload()["raw_dictation"]


class TestBoardAndLaneAreWhatALoadIs:
    def test_a_capture_is_not_ready_without_them(self):
        capture = fc.Capture()
        capture.apply("rate, seven fifty")
        assert set(capture.missing) == {"source_board", "origin", "destination"}

    def test_it_is_ready_with_them_and_nothing_else(self):
        """Sparse capture is valid capture. The rate is worth a question and the
        question is asked of Mike, not of the card."""
        capture = fc.Capture()
        capture.apply("board, DAT")
        capture.apply("origin, Ocala")
        capture.apply("destination, Tampa")
        assert capture.missing == []

    def test_the_card_marks_what_is_still_needed(self):
        capture = fc.Capture()
        capture.apply("board, DAT")
        card = "\n".join(capture.lines())
        assert "still needed" in card
        assert "Origin" in card and "Destination" in card


class TestTheThreeCommands:
    @pytest.mark.parametrize("spoken", ["done", "that's it", "log it", "send it"])
    def test_done(self, spoken):
        assert fc.is_done(spoken)

    @pytest.mark.parametrize("spoken", ["cancel", "forget it", "start over"])
    def test_cancel(self, spoken):
        assert fc.is_cancel(spoken)

    @pytest.mark.parametrize("spoken", ["scratch that", "undo", "strike that"])
    def test_scratch(self, spoken):
        assert fc.is_scratch(spoken)

    def test_the_commands_never_overlap(self):
        """Nothing that sounds like DONE may cancel, and nothing that sounds
        like CANCEL may send. One is a write and the other is a discard."""
        assert not (set(fc.DONE) & set(fc.CANCEL))
        assert not (set(fc.DONE) & set(fc.SCRATCH))
        assert not (set(fc.CANCEL) & set(fc.SCRATCH))

    def test_a_command_is_not_mistaken_for_a_field(self):
        for spoken in list(fc.DONE) + list(fc.CANCEL) + list(fc.SCRATCH):
            with pytest.raises(fc.NothingRecognised):
                fc.split_label(spoken)


class TestWhichModeMikeGets:
    """He chooses by how he pauses, and nothing else. Both are valid; one is a
    listing already read, the other is a listing being read."""

    @pytest.mark.parametrize("spoken", [
        "Log this.", "Log this one.", "Joe, log this one", "log it",
    ])
    def test_the_bare_wake_phrase_starts_a_field_by_field_read(self, spoken):
        assert _is_bare_wake(spoken)

    @pytest.mark.parametrize("spoken", [
        "Log this one. DAT, Jacksonville to Tampa, seven fifty",
        "log this one DAT Ocala to Tampa",
    ])
    def test_a_whole_listing_stays_a_one_shot_capture(self, spoken):
        assert not _is_bare_wake(spoken)


class TestTheFieldOrderBelongsToDispatch:
    def test_it_is_recorded_where_the_authority_is(self):
        """`dispatch.opportunity.dictation_order()` derives this order from the
        Mission Card template and is the authority. JOE cannot import Dispatch --
        two repositories, both with a package called `adapters` -- so this is a
        copy, and a copy needs a test that says so.

        **If the two ever disagree, Dispatch wins.**
        """
        assert "dictation_order" in fc.__doc__ or "dictation_order" in (
            open(fc.__file__, encoding="utf-8").read())
        assert set(fc.REQUIRED) == {"source_board", "origin", "destination"}
