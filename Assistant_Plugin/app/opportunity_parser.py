"""Dictation parser for Opportunity Capture.

Parses natural speech or text dictation into structured fields for the seventh contract
(POST /api/joe/opportunity).

Canonical fields:
- source_board (e.g., DAT, Truckstop, CH Robinson, Uber Freight, RXO)
- origin (City/State or location)
- destination (City/State or location)
- rate (float / integer)
- pieces_weight (e.g. "one pallet", "42000 lbs")
- equipment (e.g. "dry van", "reefer", "flatbed")
- pickup_date (e.g. "Thursday", "2026-09-10")
- delivery_date (optional)
- contact (optional)
- notes (optional)
"""

from __future__ import annotations

import re
from typing import Any, Dict


# ---------------------------------------------------------------- misheard

# WHY THIS EXISTS. The recognizer is a general-purpose English model and it has
# never heard of freight. Spoken into it, a real load came back:
#
#     said     DAT, Jacksonville to Tampa, one pallet, dry van, $750
#     heard    Dad, Jacksonville to Tampa, one pallet, drive-in, 750
#
# The lane, the rate and the pieces survived. **The two words that came back
# wrong were the board and the equipment** - the two that name what the load is.
# A capture logged as board "DAD" is not a capture, it is a row Mike has to find
# and fix later, and he is driving.
#
# This is not a spell-checker and must not become one. It is a short list of
# what THIS model does to THESE words, and every entry is a mishearing that was
# actually observed or is a plain homophone of a term in the list Mike uses.

#: Board names, corrected ONLY in the leading position - the token or two before
#: the first comma, which is where a dictated board always is. "That" and "dad"
#: are ordinary English everywhere else in a sentence and are left alone there;
#: rewriting them globally would be worse than the mishearing.
_MISHEARD_BOARD = (
    (r"^(?:d\.?\s*a\.?\s*t\.?|dad|that|dat)\b", "DAT"),
    # "Trucks stop" is what the recognizer actually returned for Truckstop --
    # it hears a plural where the brand has none, so the s is optional here.
    (r"^trucks?\s*stop\b", "Truckstop"),
    (r"^trucks?\s*(?:smarter|smart|smarts)\b", "TruckSmarter"),
    (r"^(?:1\s*2\s*3|one\s*two\s*three|won\s*too\s*three)\s*load\s*board\b",
     "123Loadboard"),
    (r"^load\s*board\s*(?:1\s*2\s*3|one\s*two\s*three)\b", "123Loadboard"),
)

#: Equipment. Safe to correct anywhere: none of these left-hand forms means
#: anything else inside a load dictation.
_MISHEARD_EQUIPMENT = (
    (r"\bdrive[\s\-]?ins?\b", "dry van"),
    (r"\bdriven\b", "dry van"),
    (r"\bdry[\s\-]?vans?\b", "dry van"),
    # "Refer", "Riefer" and "reaper" have all come back for reefer. The model
    # is reaching for an English word and there is no English word there.
    (r"\brefers?\b", "reefer"),
    (r"\brie?fers?\b", "reefer"),
    (r"\breapers?\b", "reefer"),
    (r"\bflat[\s\-]bed\b", "flatbed"),
    (r"\bstep[\s\-]deck\b", "stepdeck"),
    (r"\bpower[\s\-]only\b", "power only"),
)

#: Spoken money. **A rate is said out loud, not read out** -- "seven fifty",
#: "twelve hundred", "twenty two hundred" -- and the recognizer writes what it
#: hears, which is words. Digits are the exception, not the rule.
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9}
#: "Twelve hundred" and "fifteen hundred" are the commonest rates a driver
#: says, and neither is reachable from the two tables above.
_TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
          "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
          "eighteen": 18, "nineteen": 19}


def correct_mishearings(text: str) -> str:
    """Repair what a general-purpose recognizer does to freight vocabulary.

    Returns the text with the board, the equipment and a spoken rate put back.
    **It corrects; it never invents.** A word it does not recognise is left
    exactly as it was heard, because a wrong capture Mike trusts is worse than
    a gap he can see.
    """
    out = (text or "").strip()
    if not out:
        return out

    for pattern, replacement in _MISHEARD_BOARD:
        fixed = re.sub(pattern, replacement, out, count=1, flags=re.IGNORECASE)
        if fixed != out:
            out = fixed
            break

    for pattern, replacement in _MISHEARD_EQUIPMENT:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)

    # "seven fifty" -> 750; "twenty two hundred" -> 2200; "eight hundred" -> 800
    def _tens_ones_hundred(match):
        return str((_TENS[match.group(1).lower()] + _ONES[match.group(2).lower()]) * 100)

    out = re.sub(r"\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s\-]"
                 r"(one|two|three|four|five|six|seven|eight|nine)\s+hundred\b",
                 _tens_ones_hundred, out, flags=re.IGNORECASE)
    out = re.sub(r"\b(ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
                 r"seventeen|eighteen|nineteen)\s+hundred\b",
                 lambda m: str(_TEENS[m.group(1).lower()] * 100), out, flags=re.IGNORECASE)
    out = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine)\s+hundred\b",
                 lambda m: str(_ONES[m.group(1).lower()] * 100), out, flags=re.IGNORECASE)
    out = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine)\s+"
                 r"(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b",
                 lambda m: str(_ONES[m.group(1).lower()] * 100 + _TENS[m.group(2).lower()]),
                 out, flags=re.IGNORECASE)
    return out


def parse_dictation(raw_text: str, channel: str = "VOICE") -> Dict[str, Any]:
    """Extract load card fields from a dictation string."""
    text = (raw_text or "").strip()

    # Strip prefixes like "Joe, log this one:" or "log load:" if present
    cleaned = re.sub(
        r"^(?:joe,?\s*)?(?:please\s*)?(?:log|capture)\s+(?:this\s+)?(?:one|load|opportunity)?:?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # A spoken wake phrase ends however the recognizer decided to punctuate it:
    # "log this one:" typed, "log this one." heard. Whatever it left behind goes,
    # or the board sits one character further along than every pattern below
    # expects and comes back UNKNOWN.
    cleaned = cleaned.lstrip(".,:;- ").strip()

    # Corrected AFTER the wake phrase comes off, because the board mishearings
    # are anchored to the front of the dictation and the front of the dictation
    # is where "Joe, log this one." was sitting.
    #
    # Only speech is corrected. Text Mike typed is text Mike meant, and running
    # a mishearing table over it would change words he chose on purpose.
    if str(channel).upper() == "VOICE":
        cleaned = correct_mishearings(cleaned)

    result: Dict[str, Any] = {
        "source_board": "UNKNOWN",
        "origin": "",
        "destination": "",
        "rate": None,
        "pieces_weight": "",
        "equipment": "",
        "pickup_date": "",
        "delivery_date": "",
        "contact": "",
        "notes": "",
        "captured_via": channel.upper(),
        "raw_dictation": text,
    }

    if not cleaned:
        return result

    # 1. Parse Rate ($1234 or $ 1234 or 1234 dollars or 750)
    rate_match = re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*dollars?|\b([1-9]\d{2,4})\b", cleaned, re.IGNORECASE)
    if rate_match:
        val_str = (rate_match.group(1) or rate_match.group(2) or rate_match.group(3)).replace(",", "")
        try:
            result["rate"] = float(val_str)
        except (ValueError, AttributeError):
            pass

    # 2. Parse Board (Common boards: DAT, Truckstop, CH Robinson, TQL, RXO, Uber, etc.)
    # Often specified at the beginning or as board: XYZ
    board_match = re.search(
        # Mike\'s four come first: DAT, Truckstop, 123Loadboard, TruckSmarter.
        r"\b(DAT|Truckstop|123Loadboard|TruckSmarter|CH Robinson|TQL|RXO|Uber Freight|Convoy|Landstar)\b",
        cleaned,
        re.IGNORECASE,
    )
    if board_match:
        result["source_board"] = board_match.group(1).upper()
    else:
        # Fallback: check first token if capitalized/short
        first_part = cleaned.split(",")[0].split(".")[0].strip()
        first_word = first_part.split()[0] if first_part else ""
        if len(first_word) <= 12 and first_word.isupper():
            result["source_board"] = first_word

    # 3. Parse Origin and Destination (e.g. "Jacksonville to Tampa" or "from Jacksonville to Tampa")
    lane_match = re.search(
        r"(?:from\s+)?([A-Za-z\s\.\-]+?)\s+(?:to|->|-)\s+([A-Za-z\s\.\-]+?)(?:,|\.|\$|\bpickup\b|\bdeliver\b|\bvan\b|\breefer\b|\bflatbed\b|\bpallet\b|\bweight\b|$)",
        cleaned,
        re.IGNORECASE,
    )
    if lane_match:
        orig = lane_match.group(1).strip()
        dest = lane_match.group(2).strip()
        # Clean up board name or keywords if captured in origin
        if result["source_board"] != "UNKNOWN":
            orig = re.sub(r"^\b" + re.escape(result["source_board"]) + r"\b[\s,:\.]*", "", orig, flags=re.IGNORECASE).strip()
        result["origin"] = orig
        result["destination"] = dest

    # 4. Parse Equipment
    equip_match = re.search(
        r"\b(dry van|reefer|flatbed|stepdeck|power only|box truck|van|container)\b",
        cleaned,
        re.IGNORECASE,
    )
    if equip_match:
        result["equipment"] = equip_match.group(1).lower()

    # 5. Parse Pieces / Weight
    pieces_match = re.search(
        r"\b(\d+\s*pallets?|one pallet|two pallets|\d+\s*lbs?|\d+\s*k|\d+\s*pieces?)\b",
        cleaned,
        re.IGNORECASE,
    )
    if pieces_match:
        result["pieces_weight"] = pieces_match.group(1).lower()

    # 6. Parse Pickup / Delivery Date
    pickup_match = re.search(
        r"\bpickup\s+([A-Za-z0-9/\-]+(?:\s+[A-Za-z0-9/\-]+)?)\b",
        cleaned,
        re.IGNORECASE,
    )
    if pickup_match:
        result["pickup_date"] = pickup_match.group(1).strip()
    else:
        # Try finding weekday after pickup or just weekday mention
        day_match = re.search(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|today|tomorrow)\b", cleaned, re.IGNORECASE)
        if day_match:
            result["pickup_date"] = day_match.group(1).capitalize()

    deliver_match = re.search(
        r"\b(?:deliver|delivery)\s+([A-Za-z0-9/\-]+(?:\s+[A-Za-z0-9/\-]+)?)\b",
        cleaned,
        re.IGNORECASE,
    )
    if deliver_match:
        result["delivery_date"] = deliver_match.group(1).strip()

    # 7. Parse Contact / Notes
    broker_match = re.search(r"\b(?:broker|contact)\s+([^,\.]+)", cleaned, re.IGNORECASE)
    if broker_match:
        result["contact"] = broker_match.group(1).strip()

    notes_match = re.search(r"\bnotes?:?\s*([^,\.]+)", cleaned, re.IGNORECASE)
    if notes_match:
        result["notes"] = notes_match.group(1).strip()

    return result
