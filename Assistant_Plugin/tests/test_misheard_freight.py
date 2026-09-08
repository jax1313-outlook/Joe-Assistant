"""What a general-purpose recognizer does to freight vocabulary.

**Every string in this file was produced by the recognizer**, not invented for a
test. Windows' synthesizer spoke a real listing into a WAV file and
faster-whisper read it back; what came out is what is asserted here.

The point of the file is the shape of the failure. The lane, the rate and the
pieces survived every time. **What came back wrong was the board and the
equipment** -- the two words that say what the load actually is -- because they
are the two the model has never met. Everything else it can spell.

A capture logged with board `DAD` is not a capture. It is a row Mike has to find
later, and he was driving when he made it.
"""

from __future__ import annotations

import pytest

from app.opportunity_parser import correct_mishearings, parse_dictation


# (what was spoken, what the recognizer actually returned)
OBSERVED = [
    ("DAT, Jacksonville to Tampa, one pallet, dry van, $750, pickup Thursday",
     "Dad, Jacksonville to Tampa, one pallet, drive-in, 750, pick up Thursday."),
    ("Truckstop, Ocala to Savannah, two pallets, reefer, twelve hundred, pickup Friday",
     "Trucks stop, Ocala to Savannah, two pallets, Riefer, 1200, pick up Friday."),
]


class TestTheBoardSurvivesRecognition:
    """The board is the load's provenance. Without it a capture cannot be
    deduplicated against anything, which is most of what the seventh contract
    is for."""

    @pytest.mark.parametrize("spoken,heard", OBSERVED)
    def test_the_board_is_recovered_from_what_was_heard(self, spoken, heard):
        assert (parse_dictation(heard, channel="VOICE")["source_board"]
                == parse_dictation(spoken, channel="CHAT")["source_board"])

    @pytest.mark.parametrize("heard,expected", [
        ("Dad, Tampa to Miami", "DAT"),
        ("that, Tampa to Miami", "DAT"),
        ("D.A.T., Tampa to Miami", "DAT"),
        ("Trucks stop, Tampa to Miami", "TRUCKSTOP"),
        ("truck stop, Tampa to Miami", "TRUCKSTOP"),
        ("truck smarter, Tampa to Miami", "TRUCKSMARTER"),
        ("123 load board, Tampa to Miami", "123LOADBOARD"),
        ("one two three load board, Tampa to Miami", "123LOADBOARD"),
    ])
    def test_all_four_of_mikes_boards(self, heard, expected):
        assert parse_dictation(heard, channel="VOICE")["source_board"] == expected

    def test_a_board_it_does_not_know_is_left_alone_not_guessed(self):
        """It corrects; it never invents. An unrecognised word stays as it was
        heard, because a wrong capture Mike trusts is worse than a gap he can
        see."""
        heard = "Landstar, Tampa to Miami, 900"
        assert correct_mishearings(heard) == heard


class TestEquipment:
    @pytest.mark.parametrize("heard,expected", [
        ("Tampa to Miami, drive-in, 900", "dry van"),
        ("Tampa to Miami, driven, 900", "dry van"),
        ("Tampa to Miami, Riefer, 900", "reefer"),
        ("Tampa to Miami, refer, 900", "reefer"),
        ("Tampa to Miami, flat bed, 900", "flatbed"),
        ("Tampa to Miami, step deck, 900", "stepdeck"),
    ])
    def test_equipment_is_recovered(self, heard, expected):
        assert parse_dictation(heard, channel="VOICE")["equipment"] == expected


class TestSpokenRates:
    """A rate is said out loud, not read out. "Seven fifty" is the normal case
    and digits are the exception."""

    @pytest.mark.parametrize("heard,expected", [
        ("DAT, Tampa to Miami, seven fifty", 750.0),
        ("DAT, Tampa to Miami, eight hundred", 800.0),
        ("DAT, Tampa to Miami, twelve hundred", 1200.0),
        ("DAT, Tampa to Miami, twenty two hundred", 2200.0),
        ("DAT, Tampa to Miami, $1,450", 1450.0),
    ])
    def test_a_spoken_rate_becomes_a_number(self, heard, expected):
        assert parse_dictation(heard, channel="VOICE")["rate"] == expected


class TestOnlySpeechIsCorrected:
    def test_typed_text_is_left_exactly_as_typed(self):
        """Text Mike typed is text Mike meant. "That" is an ordinary English
        word and rewriting it into a load board because it sat at the front of
        a sentence would be the mishearing table causing the defect it exists
        to prevent."""
        typed = "log this one that, Tampa to Miami, 900"
        assert parse_dictation(typed, channel="CHAT")["source_board"] != "DAT"

    def test_ordinary_words_mid_sentence_are_not_boards(self):
        """The board corrections are anchored to the front of the dictation
        because that is where a dictated board is. Anywhere else, "that" is
        just "that"."""
        heard = "DAT, Tampa to Miami, notes: he said that the dock closes at four"
        parsed = parse_dictation(heard, channel="VOICE")
        assert parsed["source_board"] == "DAT"
        assert "that" in correct_mishearings(heard)


class TestTheWakePhraseComesOffHoweverItIsPunctuated:
    @pytest.mark.parametrize("prefix", [
        "Joe, log this one: ", "Joe, log this one. ", "log this one, ",
        "Log this load - ", "capture opportunity: ",
    ])
    def test_the_board_is_not_hidden_by_the_punctuation(self, prefix):
        """Typed, the wake phrase ends in a colon. Spoken, the recognizer ends
        it in a full stop. One stray character in front of the board sent the
        whole capture back as UNKNOWN."""
        parsed = parse_dictation(prefix + "DAT, Tampa to Miami, 900", channel="VOICE")
        assert parsed["source_board"] == "DAT"
        assert parsed["origin"] == "Tampa"
