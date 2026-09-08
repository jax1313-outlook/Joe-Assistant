import unittest
from app.opportunity_parser import parse_dictation


class TestOpportunityParser(unittest.TestCase):
    def test_parse_full_dictation(self):
        phrase = "Joe, log this one: DAT, Jacksonville to Tampa, one pallet, dry van, $750, pickup Thursday."
        parsed = parse_dictation(phrase, channel="VOICE")
        
        self.assertEqual(parsed["source_board"], "DAT")
        self.assertEqual(parsed["origin"], "Jacksonville")
        self.assertEqual(parsed["destination"], "Tampa")
        self.assertEqual(parsed["pieces_weight"], "one pallet")
        self.assertEqual(parsed["equipment"], "dry van")
        self.assertEqual(parsed["rate"], 750.0)
        self.assertEqual(parsed["pickup_date"], "Thursday")
        self.assertEqual(parsed["captured_via"], "VOICE")

    def test_parse_sparse_dictation(self):
        phrase = "log load: Truckstop, Atlanta to Miami, $1200"
        parsed = parse_dictation(phrase, channel="TEXT")
        
        self.assertEqual(parsed["source_board"], "TRUCKSTOP")
        self.assertEqual(parsed["origin"], "Atlanta")
        self.assertEqual(parsed["destination"], "Miami")
        self.assertEqual(parsed["rate"], 1200.0)
        self.assertEqual(parsed["captured_via"], "TEXT")


if __name__ == "__main__":
    unittest.main()
