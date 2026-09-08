"""JOE's half of Opportunity Capture: hear it, route it, parse it, say it back.

**These tests do not touch Dispatch, and that is the point.** An earlier version
of this file called `AssistantService()` with the real configuration and wrote a
row into Mike's live database on every run. It passed. It also meant `pytest`
was a way to put freight in the operational store, which is not something a test
run should be able to do.

The line is drawn where the doctrine draws it. **JOE routes, parses, and speaks.
Dispatch decides, deduplicates and mints the identity.** Everything on JOE's
side of that line is tested here against a port that answers like Dispatch;
everything on Dispatch's side is tested in Dispatch, where the dedup rule
actually lives.
"""

import unittest

from app.opportunity_parser import parse_dictation
from app.service import AssistantService
from contracts import Capability


class FakeDispatch:
    """Answers the shape `/api/joe/opportunity` answers, and nothing more.

    It mints no identity of its own beyond the one it is told to return, because
    the real port does not either -- Dispatch is the sole identity authority and
    a client that can produce an `OPP-` id is a second one.
    """

    def __init__(self, answer=None):
        self.calls = []
        self.answer = answer or {
            "ok": True, "verdict": "NEW", "opportunity_id": "OPP-TEST01",
            "echo": "LOGGED. OPPORTUNITY OPP-TEST01. DAT, JACKSONVILLE TO TAMPA, "
                    "$750, PICKUP THURSDAY.",
        }

    def submit_opportunity(self, fields, *, token="", driver=""):
        self.calls.append({"fields": dict(fields), "token": token, "driver": driver})
        answer = dict(self.answer)
        answer.setdefault("mode", "LIVE_DISPATCH")
        return answer


class OpportunityLoopCase(unittest.TestCase):
    def setUp(self):
        self.service = AssistantService()
        self.port = FakeDispatch()
        self.service.dispatch = self.port
        # Speaking shells out to PowerShell. The loop is what is under test.
        self.service.speak = lambda text: {"spoken": text}


class TestItReachesTheRightCapability(OpportunityLoopCase):
    def test_log_this_one_is_a_capture(self):
        response = self.service.ask(
            "Joe, log this one: DAT, Jacksonville to Tampa, one pallet, dry van, "
            "$750, pickup Thursday.", channel="voice").response
        self.assertEqual(response.capability, Capability.OPPORTUNITY)

    def test_the_echo_is_what_is_spoken(self):
        """The read-back is the only place a misheard board gets caught, so it
        must not be reshaped by driver-mode summarizing on the way out."""
        response = self.service.ask("log this one: DAT, Tampa to Miami, $900",
                                    channel="voice").response
        self.assertEqual(response.spoken_summary, response.answer)
        self.assertTrue(response.answer.startswith("LOGGED. OPPORTUNITY OPP-"))


class TestWhatIsSentToDispatch(OpportunityLoopCase):
    def test_the_parsed_fields_travel_not_the_sentence(self):
        self.service.ask("log this one: DAT, Jacksonville to Tampa, dry van, $750",
                         channel="voice")
        sent = self.port.calls[0]["fields"]
        self.assertEqual(sent["source_board"], "DAT")
        self.assertEqual(sent["origin"], "Jacksonville")
        self.assertEqual(sent["destination"], "Tampa")
        self.assertEqual(sent["rate"], 750.0)

    def test_every_call_carries_the_driver(self):
        """Dispatch requires it on every call: an action with nobody's name on
        it is an action nobody authorised."""
        self.service.ask("log this one: DAT, Tampa to Miami, $900", channel="voice")
        self.assertTrue(self.port.calls[0]["driver"])

    def test_the_channel_is_recorded_as_spoken(self):
        self.service.ask("log this one: DAT, Tampa to Miami, $900", channel="voice")
        self.assertEqual(self.port.calls[0]["fields"]["captured_via"], "VOICE")


class TestFailureIsAudible(OpportunityLoopCase):
    """A silent failure is the classic 70 MPH violation and this program has
    already shipped one."""

    def test_an_unreachable_node_does_not_report_a_capture(self):
        self.port.answer = {"mode": "UNAVAILABLE", "ok": False,
                            "note": "Dispatch did not answer: URLError"}
        response = self.service.ask("log this one: DAT, Tampa to Miami, $900",
                                    channel="voice").response
        self.assertIn("NOT LOGGED", response.answer)
        self.assertNotIn("OPP-", response.answer)
        self.assertIn("DISPATCH DID NOT RECORD THIS CAPTURE", response.written)

    def test_a_refusal_says_what_the_node_said(self):
        self.port.answer = {"mode": "REFUSED", "ok": False, "status": 400,
                            "note": "board, lane or rate missing"}
        response = self.service.ask("log this one: DAT, Tampa to Miami, $900",
                                    channel="voice").response
        self.assertIn("board, lane or rate missing", response.written)

    def test_an_unwritten_capture_is_never_called_live(self):
        """The truth vocabulary is the whole mechanism. A queued capture is not
        a recorded one."""
        self.port.answer = {"mode": "UNAVAILABLE", "ok": False, "note": "no answer"}
        response = self.service.ask("log this one: DAT, Tampa to Miami, $900",
                                    channel="voice").response
        self.assertTrue(all(p.mode != "LIVE" for p in response.provenance))


class TestTheParserAlone(unittest.TestCase):
    def test_sparse_capture_is_valid_capture(self):
        """Board and lane are what a load is. A rate is worth one question and
        the question is asked of Mike, not of the queue."""
        parsed = parse_dictation("DAT, Ocala to Tampa", channel="VOICE")
        self.assertEqual(parsed["source_board"], "DAT")
        self.assertEqual(parsed["destination"], "Tampa")
        self.assertIsNone(parsed["rate"])

    def test_what_was_heard_is_kept_uncorrected(self):
        """The corrected text is what gets parsed; the heard text is what gets
        shown. Losing the original would hide the mishearing that produced the
        capture."""
        parsed = parse_dictation("log this one Dad, Tampa to Miami, 900",
                                 channel="VOICE")
        self.assertEqual(parsed["source_board"], "DAT")
        self.assertIn("Dad", parsed["raw_dictation"])


if __name__ == "__main__":
    unittest.main()
