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

from .opportunity_parser import (apply_spelled_corrections, collapse_phonetic,
                                 correct_mishearings, parse_dictation)

#: The contract's fields, in the order the Mission Card declares them.
#:
#: **Dispatch owns this order**, in `dispatch.opportunity.dictation_order()`,
#: which derives it from the Mission Card template rather than hardcoding it.
#: JOE cannot import Dispatch -- two repositories, both with a package called
#: `adapters` -- so this is the same order, and `test_field_capture.py` holds a
#: note about which one is authoritative if they ever disagree.
FIELD_ORDER = (
    "source_board", "load_number", "contact", "origin", "destination",
    "pieces_weight", "equipment", "rate", "pickup_date", "delivery_date",
    "notes",
)

#: Fields the Opportunity contract does not carry. They are still asked for and
#: still kept -- they travel to Dispatch inside `notes`, named, rather than being
#: dropped on the floor because a contract has not caught up with a screen.
#:
#: `load_number` is on the Mission Card as "Load number (theirs)". Adding it to
#: the seventh contract is a Class 3 change and is the Owner's to rule.
NOT_IN_CONTRACT = ("load_number",)

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
                      "pallets", "commodity", "commodities", "product"),
    "equipment": ("equipment", "trailer type", "trailer", "truck type"),
    "rate": ("rate", "pay", "price", "amount", "revenue", "line haul", "linehaul"),
    "pickup_date": ("pick up date", "pickup date", "pick up day", "pickup day",
                    "pick up window", "pickup window", "picking up"),
    "delivery_date": ("delivery date", "delivery day", "delivery window",
                      "deliver by", "delivering"),
    "notes": ("special instructions", "special instruction", "instructions",
              "notes", "note", "comment", "comments", "remarks"),
    # The Mission Card has "Load number (theirs)" and the Opportunity contract
    # does not carry it. Until that is ruled, the broker's own number goes into
    # notes with its name on it rather than being dropped.
    "load_number": ("load number", "load id", "reference number", "reference",
                    "their number", "pro number", "order number"),
}

#: **Move to the next field.** Owner ruling, 2026-09-08, after the first live
#: run: *"the movement field by field, it should allow me to give the command to
#: move to the next field. Otherwise, it is going to constantly truncate the
#: input."*
#:
#: He is right, and it is the same mistake in a new place. Silence ends an
#: UTTERANCE -- that is what stopped the countdown cutting him off mid-sentence.
#: It must not also end a FIELD: he is reading off a board, and a pause while he
#: finds the next value is a man working, not a man finished. **Mike moves the
#: cursor. Nothing else does.**
NEXT = ("next", "next field", "next one", "okay next", "ok next", "go on",
        "move on", "continue")

#: Leave this one empty and move on. Sparse capture is valid capture.
SKIP = ("skip", "skip it", "none", "nothing", "not given", "blank", "leave it")

#: Back up one field, for when he hears the read-back and it went in the wrong
#: place.
BACK = ("back", "go back", "back up", "previous", "last one")

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


def is_next(text: str) -> bool:
    return _normalise(text) in NEXT


def is_skip(text: str) -> bool:
    return _normalise(text) in SKIP


def is_back(text: str) -> bool:
    return _normalise(text) in BACK


def command(text: str) -> str:
    """Which command was that, if any. "" when it is content, not a command.

    One place, so the console cannot check them in a different order than the
    tests do -- and so that a word can never be both a command and a value.
    """
    for name, check in (("NEXT", is_next), ("SKIP", is_skip), ("BACK", is_back),
                        ("DONE", is_done), ("CANCEL", is_cancel),
                        ("SCRATCH", is_scratch)):
        if check(text):
            return name
    return ""


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
        #: Which field Mike is on. **He moves it. Nothing else does.** Silence
        #: ends an utterance; only NEXT, SKIP, BACK or naming a field moves the
        #: cursor -- because a pause while he reads the next value off a board
        #: is a man working, not a man finished.
        self.cursor = 0

    # ---- where he is --------------------------------------------------

    @property
    def field(self) -> str:
        """The field being filled right now."""
        return FIELD_ORDER[min(self.cursor, len(FIELD_ORDER) - 1)]

    @property
    def asking(self) -> str:
        return self.ASKS[self.field]

    def advance(self) -> str:
        """Move to the next field. Returns the one now being asked for."""
        self.cursor = min(self.cursor + 1, len(FIELD_ORDER) - 1)
        return self.field

    def retreat(self) -> str:
        self.cursor = max(self.cursor - 1, 0)
        return self.field

    def go_to(self, field: str) -> str:
        if field in FIELD_ORDER:
            self.cursor = FIELD_ORDER.index(field)
        return self.field

    def add(self, spoken: str) -> str:
        """Put what was said into the field he is on, appending to what is there.

        **Appending, not replacing.** He may need three breaths for an address,
        and losing the first two because he paused to read the third is the
        defect this whole design exists to avoid.
        """
        text = self._corrected(spoken)
        self.heard.append(spoken)
        existing = self.fields[self.field]
        self.fields[self.field] = (existing + " " + text).strip() if existing else text
        self.last_filled = self.field
        return self.fields[self.field]

    def clear_current(self) -> str:
        """Empty the field he is on, without moving."""
        self.fields[self.field] = ""
        return self.field

    def _corrected(self, spoken: str) -> str:
        if self.channel != "VOICE":
            return spoken.strip()
        text = correct_mishearings(apply_spelled_corrections(spoken))
        # A reference read phonetically -- "bravo charlie delta hotel five six"
        # -- is only useful collapsed, and only these fields ever hold one.
        if self.field in ("load_number", "source_board"):
            text = collapse_phonetic(text)
        return text.strip()

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
        sent = {name: value for name, value in self.fields.items()
                if value and name not in NOT_IN_CONTRACT}
        # Named, not dropped. The contract has no place for their load number
        # yet, and losing it because a contract has not caught up with a screen
        # would be the program deciding what matters.
        carried = ["%s %s" % (self.LABEL_FOR[name], self.fields[name])
                   for name in NOT_IN_CONTRACT if self.fields[name]]
        if carried:
            sent["notes"] = " | ".join(carried + ([sent["notes"]]
                                                  if sent.get("notes") else []))
        if sent.get("rate"):
            parsed = parse_dictation("x to y " + sent["rate"], channel=self.channel)
            if parsed.get("rate"):
                sent["rate"] = parsed["rate"]
        sent["captured_via"] = self.channel
        sent["raw_dictation"] = " | ".join(self.heard)
        return sent

    # ---- the card, as it stands ---------------------------------------

    LABEL_FOR = {
        "source_board": "Board", "load_number": "Their load number",
        "contact": "Customer", "origin": "Origin",
        "destination": "Destination", "pieces_weight": "Pieces / weight",
        "equipment": "Equipment", "rate": "Rate", "pickup_date": "Pickup",
        "delivery_date": "Delivery", "notes": "Notes",
    }

    #: What JOE asks, in the words a person would use. Spoken and printed.
    ASKS = {
        "source_board": "Which board?",
        "load_number": "Their load number?",
        "contact": "Who is the customer?",
        "origin": "Picking up where?",
        "destination": "Delivering where?",
        "pieces_weight": "What is the freight?",
        "equipment": "What trailer?",
        "rate": "What does it pay?",
        "pickup_date": "Picking up when?",
        "delivery_date": "Delivering when?",
        "notes": "Anything else?",
    }

    def lines(self) -> list:
        """The card as it stands, for a window sitting beside the load board.

        **The arrow is the most important character on it.** Mike needs to know
        which field he is filling without being told, because being told costs a
        sentence every time.
        """
        out = ["  MISSION CARD", ""]
        for name in FIELD_ORDER:
            value = self.fields[name]
            here = ">" if name == self.field else " "
            need = "*" if (name in REQUIRED and not value) else " "
            out.append("  %s %s %-19s %s" % (here, need,
                                             self.LABEL_FOR[name] + ":",
                                             value or "-"))
        out.append("")
        if self.missing:
            out.append("    * still needed: %s"
                       % ", ".join(self.LABEL_FOR[f] for f in self.missing))
        else:
            out.append("    Ready. Say DONE to log it.")
        return out
