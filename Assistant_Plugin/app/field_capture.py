"""Reading a listing to JOE, one field at a time.

**The Owner's working method, 2026-09-08, in his words:**

> *"I will go to a load board, sign in with my credentials, and sort through the
> load opportunities, open one that I want to capture, and say, log this, and
> then begin reading the information field by field, broker name, XPO Logistics,
> address, Savannah, Georgia fourteen seventy two, Highway five one six...
> then the Joe program should fill out the mission card as I'm speaking."*

WHY THIS IS EASIER THAN A SENTENCE, NOT HARDER. A whole listing spoken in one
breath has to be pulled apart by grammar and position, and a comma in the wrong
place moves a city into the rate. **A label anchors it.** Measured on the same
model JOE listens with:

    said   "Broker name, X P O Logistics"
    heard  "broker name, xpologistics"

    said   "Address, fourteen seventy two Highway five one six, Savannah, Georgia"
    heard  "Address, 1472 Highway 516, Savannah, Georgia"

The label survived both times, and every spoken number came back as digits.

**A field ends when he stops talking.** Three seconds of silence, the rule built
the same morning for a different reason -- so the loop is: speak a field, silence
ends it, the field lands, speak the next. **That is not streaming. That is a
loop**, and it needs no live transcription, no socket and no redrawing form. JOE
prints the card between fields in its own window, and Windows puts that window
next to the load board.

WHAT IT WILL NOT DO. **It never guesses which field a phrase belongs to.** A
phrase with no label it recognises is reported, not filed somewhere plausible --
a value in the wrong field is worse than a value missing, because a gap is
visible and a wrong lane is not.
"""

from __future__ import annotations

import re

from .opportunity_parser import (apply_spelled_corrections, correct_mishearings,
                                 parse_dictation)

#: The contract's fields, in the order the Mission Card declares them.
#:
#: **Dispatch owns this order**, in `dispatch.opportunity.dictation_order()`,
#: which derives it from the Mission Card template rather than hardcoding it.
#: JOE cannot import Dispatch -- two repositories, both with a package called
#: `adapters` -- so this is the same order, and `test_field_capture.py` holds a
#: note about which one is authoritative if they ever disagree.
FIELD_ORDER = (
    "source_board", "contact", "origin", "destination", "pieces_weight",
    "equipment", "rate", "pickup_date", "delivery_date", "notes",
)

#: Board and lane are what a load *is*. Without them there is nothing to log and
#: nothing to deduplicate against.
REQUIRED = ("source_board", "origin", "destination")

#: What a person calls each field out loud. Longest first, so "pickup date" is
#: matched before "pickup".
LABELS = {
    "source_board": ("load board", "source board", "board", "posted on", "source"),
    "contact": ("broker name", "customer name", "shipper name", "contact name",
                "point of contact", "broker", "customer", "shipper", "contact"),
    "origin": ("pick up location", "pickup location", "origin address",
               "shipper address", "origin", "pick up from", "picking up at",
               "from", "address"),
    "destination": ("delivery location", "delivery address", "consignee address",
                    "destination", "consignee", "deliver to", "delivering to",
                    "to"),
    "pieces_weight": ("pieces and weight", "pieces", "weight", "cargo", "freight",
                      "pallets", "commodity"),
    "equipment": ("equipment", "trailer type", "trailer", "truck type"),
    "rate": ("rate", "pay", "price", "amount", "revenue", "line haul", "linehaul"),
    "pickup_date": ("pick up date", "pickup date", "pick up day", "pickup day",
                    "pick up window", "pickup window", "picking up"),
    "delivery_date": ("delivery date", "delivery day", "delivery window",
                      "deliver by", "delivering"),
    "notes": ("notes", "note", "comment", "comments", "remarks"),
}

#: Said on its own, these end the capture and send it.
DONE = ("done", "that's it", "thats it", "that is it", "log it", "send it",
        "submit", "that's all", "thats all", "finished", "end of load")

#: ...and these throw it away. Deliberately distinct words: nothing that sounds
#: like "done" may cancel, and nothing that sounds like "cancel" may send.
CANCEL = ("cancel", "scrap it", "forget it", "throw it out", "start over")

#: Clearing one field. "Scratch that" clears the one just filled, which is what
#: a person says the moment they hear the read-back come out wrong.
SCRATCH = ("scratch that", "scratch it", "undo that", "undo", "no not that",
           "strike that")

_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
         "sunday", "today", "tomorrow", "tonight", "asap")


class NothingRecognised(ValueError):
    """The phrase named no field, and JOE will not guess which one it meant."""


def _normalise(text: str) -> str:
    # The recognizer punctuates what it hears, and it heard "Done!". A
    # command that fails because of an exclamation mark is a command that
    # fails, and Mike would say it again louder -- which adds one.
    return re.sub(r"\s+", " ", (text or "").strip().lower()).strip(" .,:;-!?\"'")


def is_done(text: str) -> bool:
    return _normalise(text) in DONE


def is_cancel(text: str) -> bool:
    return _normalise(text) in CANCEL


def is_scratch(text: str) -> bool:
    return _normalise(text) in SCRATCH


def split_label(text: str) -> tuple:
    """Return `(field, value)` for one spoken field, or raise.

    Labels are matched longest-first so "pickup date" never loses to "pickup",
    and "pickup" followed by a weekday is read as a date rather than a place --
    which is how "pickup Thursday" is said and meant.
    """
    spoken = (text or "").strip().strip(".")
    if not spoken:
        raise NothingRecognised("nothing was said")

    candidates = []
    for field, labels in LABELS.items():
        for label in labels:
            candidates.append((len(label), label, field))
    candidates.sort(reverse=True)

    lowered = spoken.lower()
    for _length, label, field in candidates:
        # The full stop belongs to the separator. "Board. D. A. T." is how the
        # recognizer punctuates a label said with a pause after it, and leaving
        # the stop in front of the value left a space there -- which stopped the
        # board correction matching, because that one is anchored to the front.
        match = re.match(r"^%s\b[\s,:.\-]*" % re.escape(label), lowered)
        if not match:
            continue
        value = spoken[match.end():].strip().strip(",.")
        if not value:
            raise NothingRecognised("%r with nothing after it" % label)
        # "pickup Thursday" is a date; "pickup 1472 Highway 516" is a place.
        if field == "origin" and label in ("pick up from", "picking up at"):
            if value.split()[0].lower().strip(",") in _DAYS:
                field = "pickup_date"
        return field, value

    raise NothingRecognised(spoken)


class Capture:
    """One listing, filled in as it is read out.

    Holds no opinion about how it is displayed or where it is sent. The console
    prints it; `DispatchPort` sends it; neither belongs here.
    """

    def __init__(self, channel: str = "VOICE"):
        self.channel = str(channel).upper()
        self.fields = {name: "" for name in FIELD_ORDER}
        self.last_filled = ""
        self.heard = []

    # ---- filling ------------------------------------------------------

    def apply(self, spoken: str) -> tuple:
        """Take one utterance. Returns `(field, value)`; raises if unrecognised.

        The spoken text is corrected before it is split, in the same order the
        one-shot parser uses: a spelling is Mike overriding the recognizer
        deliberately, so it goes first and the mishearing table never gets to
        argue with it.
        """
        text = spoken
        if self.channel == "VOICE":
            text = correct_mishearings(apply_spelled_corrections(text))
        field, value = split_label(text)
        if self.channel == "VOICE" and field == "source_board":
            # The board corrections are anchored to the front of a dictation,
            # because "that" and "dad" are ordinary English anywhere else. Read
            # field by field, the front of the *value* is that place.
            value = correct_mishearings(value)
        self.fields[field] = value.strip()
        self.last_filled = field
        self.heard.append(spoken)
        return field, value

    def scratch(self) -> str:
        """Clear the field just filled. Returns which one, or ""."""
        field, self.last_filled = self.last_filled, ""
        if field:
            self.fields[field] = ""
        return field

    # ---- state --------------------------------------------------------

    @property
    def missing(self) -> list:
        return [f for f in REQUIRED if not self.fields[f]]

    @property
    def empty(self) -> bool:
        return not any(self.fields.values())

    def payload(self) -> dict:
        """What goes to the seventh contract.

        The rate is re-read through the one-shot parser rather than sent as
        spoken, because "twenty two hundred" has to reach Dispatch as 2200 and
        that conversion already exists and is already tested.
        """
        sent = {name: value for name, value in self.fields.items() if value}
        if sent.get("rate"):
            parsed = parse_dictation("x to y " + sent["rate"], channel=self.channel)
            if parsed.get("rate"):
                sent["rate"] = parsed["rate"]
        sent["captured_via"] = self.channel
        sent["raw_dictation"] = " | ".join(self.heard)
        return sent

    # ---- the card, as it stands ---------------------------------------

    LABEL_FOR = {
        "source_board": "Board", "contact": "Customer", "origin": "Origin",
        "destination": "Destination", "pieces_weight": "Pieces / weight",
        "equipment": "Equipment", "rate": "Rate", "pickup_date": "Pickup",
        "delivery_date": "Delivery", "notes": "Notes",
    }

    def lines(self) -> list:
        """The card as it stands, for a window sitting beside the load board.

        Required fields that are still empty are marked, because the one thing
        Mike needs to see at a glance is what would stop this being logged.
        """
        out = ["  MISSION CARD - reading in progress", ""]
        for name in FIELD_ORDER:
            value = self.fields[name]
            mark = " *" if (name in REQUIRED and not value) else "  "
            out.append("   %s %-16s %s" % (mark.strip() or " ",
                                           self.LABEL_FOR[name] + ":",
                                           value or "-"))
        out.append("")
        if self.missing:
            out.append("   * still needed: %s"
                       % ", ".join(self.LABEL_FOR[f] for f in self.missing))
        else:
            out.append("   Ready. Say DONE to log it.")
        return out
