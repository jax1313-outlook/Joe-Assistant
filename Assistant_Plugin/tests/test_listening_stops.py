"""When JOE stops listening.

**The rule this file exists for, in the Owner's words, 2026-09-08:**

> *"It did cut me off. And in real operations, there should be no cutoff.
> Silence for three seconds should mean that's a break."*

The first version gave him a fixed twelve seconds. He spoke a broker's details
into it and it took the last three digits of the phone number -- `904-674-9`,
nine digits of ten -- because the clock ran out mid-sentence.

**That window was never tested, because testing it needed a person.** So the
decision is a pure function now, and this is the test that would have caught it.
"""

from __future__ import annotations

import pytest

from adapters.whisper_listen import (NOTHING_SAID_SECONDS,
                                     SILENCE_ENDS_IT_SECONDS, stop_listening)


class TestSilenceEndsIt:
    def test_three_seconds_after_he_stops(self):
        assert stop_listening(spoke=True, since_sound=SILENCE_ENDS_IT_SECONDS,
                              since_start=30.0)

    def test_a_pause_to_think_is_not_a_break(self):
        """He is reading a rate off a screen, or working out a pickup day. Two
        seconds of quiet is a man thinking, not a man finished."""
        assert stop_listening(spoke=True, since_sound=2.0, since_start=30.0) == ""

    def test_a_long_sentence_is_never_cut_off(self):
        """**The defect, as a test.** Two minutes into a sentence, still
        talking: the answer is still keep listening. No clock ends a sentence."""
        assert stop_listening(spoke=True, since_sound=0.2, since_start=119.0) == ""


class TestNobodySaidAnything:
    def test_a_stray_enter_does_not_record_the_cab(self):
        """Silence can only end a recording that started. Without this rule, an
        accidental keypress with nobody speaking holds the microphone open for
        the whole ceiling -- two minutes of recording a truck cab, which is the
        one thing this program must not do."""
        assert stop_listening(spoke=False, since_sound=0.0,
                              since_start=NOTHING_SAID_SECONDS)

    def test_it_waits_for_a_slow_start(self):
        """A Bluetooth headset takes a moment, and a man collects his thought
        before he speaks. Giving up at two seconds would lose the first words."""
        assert stop_listening(spoke=False, since_sound=0.0, since_start=3.0) == ""

    def test_the_two_rules_do_not_fight(self):
        """Once he has spoken, the eight-second rule is finished with -- only
        silence ends it after that."""
        assert stop_listening(spoke=True, since_sound=0.5,
                              since_start=NOTHING_SAID_SECONDS * 3) == ""


class TestItSaysWhy:
    @pytest.mark.parametrize("spoke,since_sound,since_start,expected", [
        (True, 5.0, 30.0, "he stopped talking"),
        (False, 0.0, 20.0, "nobody said anything"),
    ])
    def test_the_reason_comes_back_with_the_decision(self, spoke, since_sound,
                                                     since_start, expected):
        """A stop with no reason is a stop nobody can debug at the roadside."""
        assert stop_listening(spoke=spoke, since_sound=since_sound,
                              since_start=since_start) == expected
