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


#: A spelled-out word, as the recognizer writes one.
#:
#: MEASURED, NOT GUESSED. Windows spoke each of these and the same model JOE
#: listens with read them back:
#:
#:     said   "Pickettville, P I C K E T T V I L L E, Road"
#:     heard  "Picketville, PICKETTVILA, Road."
#:
#:     said   "Pickettville. P. I. C. K. E. T. T. V. I. L. L. E. Road"
#:     heard  "Picketville. PICKETTVILLE Road"
#:
#: **It collapses spelled letters into one run-together capitalised word.** That
#: is the pattern, and it is the only reliable way to get a street name, a
#: person's name or a small town into JOE -- the model has never met them and
#: no correction table can hold them all.
#:
#: The second form came back exactly right and the first did not, which is worth
#: knowing at the wheel: **spell with a beat between the letters.**
_SPELLED = re.compile(r"\b([A-Z]{3,})\b")

#: How different the spelled word may be from the word it replaces.
#:
#: The guard matters more than the feature. "Broker name, XPO Logistics" also
#: contains a capitalised run, and `name` must not become `XPO`. Requiring the
#: same first letter and a similar length keeps the correction to what it is
#: for: a word said, then spelled.
_SPELLED_LENGTH_SLACK = 4

#: How many words back to look for the word being spelled. Two, because
#: "Penske Logistics, P E N S K E" puts the spelling after *Logistics* --
#: which is how a person actually says a company name -- and any further
#: back starts reaching into a different clause.
_SPELLED_LOOKBACK_WORDS = 3


def apply_spelled_corrections(text: str) -> str:
    """Let a spelled word replace the one it was spelled for.

        "Pickettville, PICKETTVILLE, Road"  ->  "Pickettville Road"

    **Owner ruling, 2026-09-08:** *"for street names, what we do is just allow
    me to spell the name."* It is the answer to the limit the first live test
    found: the recognizer got `Jeff Tissue` right because that is ordinary
    English, and got `Penske` and `Picketville` wrong because it has never met
    them. A correction table can hold a closed vocabulary -- four load boards,
    eight equipment types. It cannot hold every street in Florida.

    **It corrects; it never invents.** A capitalised word that is not a
    plausible spelling of its neighbour is left exactly where it is, because an
    acronym in a company name is not a correction and must not be treated as
    one.
    """
    if not (text or "").strip():
        return (text or "").strip()

    # Word tokens and the punctuation between them, kept apart so a word can be
    # removed without taking its neighbours' commas with it.
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*|[^A-Za-z]+", text.strip())
    drop = set()

    for position, token in enumerate(tokens):
        if not (token.isupper() and token.isalpha() and len(token) >= 3):
            continue
        # Look back a few words, not just one. "Penske Logistics, P E N S K E"
        # puts the spelling after *Logistics*, and the word it belongs to is one
        # further back -- which is how a real person says a company name.
        looked_at = 0
        for earlier in range(position - 1, -1, -1):
            candidate = tokens[earlier]
            if not candidate.isalpha():
                continue
            looked_at += 1
            if looked_at > _SPELLED_LOOKBACK_WORDS:
                break
            if (candidate[:1].lower() == token[:1].lower()
                    and abs(len(candidate) - len(token)) <= _SPELLED_LENGTH_SLACK
                    and not candidate.isupper()):
                # The correction goes where the WORD was, not where the spelling
                # was. "Penske Logistics, P E N S K E" must come back as
                # "Penske Logistics", not as "Logistics, Penske" -- the spelling
                # is an aside, and an aside does not take the sentence's place.
                tokens[earlier] = token.capitalize()
                drop.add(position)
                # ...and one of the commas around it, or "Pickettville,
                # PICKETTVILLE, Road" comes back as "Pickettville, Road".
                # The one after, when there is one: the aside was parenthetical
                # and both its commas should not survive it.
                if position + 1 < len(tokens) and not tokens[position + 1].isalpha():
                    drop.add(position + 1)
                elif position - 1 > earlier and not tokens[position - 1].isalpha():
                    drop.add(position - 1)
                break

    rebuilt = "".join(t for i, t in enumerate(tokens) if i not in drop)
    return re.sub(r"\s{2,}", " ", rebuilt).strip()


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
        # Spelling first: a spelled word is Mike overriding the recognizer
        # deliberately, and it must not be second-guessed by a table afterwards.
        cleaned = apply_spelled_corrections(cleaned)
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
