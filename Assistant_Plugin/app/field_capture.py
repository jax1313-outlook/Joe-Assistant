"""Reading a listing to JOE, one field at a time — from Dispatch's own form.

**The Owner's working method, 2026-09-08:** open a listing on a load board, say
*"log this"*, and read it out field by field while the card fills in a window
beside it.

**JOE DOES NOT KNOW THE FORM. IT ASKS.** This module held eleven fields and
eleven questions written by Code, until the Owner asked the obvious thing:

> *"How can Joe not know the forms that are in the company library? ... the
> level four agent should know all the documents and should be able to follow
> along in a field by field narration. Am I correct?"*

He was correct, and the copy was already wrong -- it had no load number, which
the Mission Card has always had. Dispatch's `mission_template.py` holds
**thirty-three fields, each already carrying the question to ask**, and its own
comment says *"a template read aloud badly is a template nobody finishes."*

The eleven were **deleted, not synchronised.** Two lists that must agree will
eventually disagree, and the second one is always the one nobody updates.

WHAT LIVES HERE NOW, and why it is not a second form:

    Dispatch owns    which fields exist / their order / their labels / the
                     question to ask / the choices to offer / which of them
                     feed the seventh contract
    JOE owns         the OTHER WORDS a person says for a field

The second is vocabulary, not structure. A form has no reason to know that a man
reading a board says *"broker"* where the card says *"Customer / Shipper /
Broker"*. **Every synonym is checked against the published form when a capture
starts**, so a field renamed in Dispatch fails here loudly instead of quietly
matching nothing.

WHAT ENDS A FIELD. Mike does. Silence ends an *utterance* -- that is what stopped
a countdown cutting him off mid-sentence -- and it must not also end a *field*:
he is reading off a board, and a pause while he finds the next value is a man
working, not a man finished.
"""

from __future__ import annotations

import re

from .opportunity_parser import (apply_spelled_corrections, collapse_phonetic,
                                 correct_mishearings, parse_dictation)

#: The other words a person says for a field, keyed by the form's own field key.
#:
#: **This is vocabulary, not structure.** It adds no field, changes no order and
#: invents no question -- every one of those comes from Dispatch. It exists
#: because a man reading a load board says "broker" where the card says
#: "Customer / Shipper / Broker", and the form has no reason to know that.
#:
#: A key here that the form does not have is a bug, not a feature, and `Capture`
#: reports it rather than ignoring it.
SYNONYMS = {
    "customer": ("broker", "broker name", "customer name", "shipper name",
                 "posted by"),
    "customer_poc": ("contact", "point of contact", "their contact", "poc"),
    "customer_phone": ("phone", "phone number", "their phone"),
    "load_number": ("load number", "load id", "reference", "reference number",
                    "pro number", "order number", "their number"),
    "pickup_location": ("origin", "pick up", "pickup", "from", "shipper address",
                        "picking up at", "loading at"),
    "delivery_location": ("destination", "deliver to", "delivering to",
                          "consignee", "drop", "dropping at"),
    "pickup_window": ("pickup date", "pick up date", "pickup day",
                      "pickup window", "when do we load"),
    "delivery_window": ("delivery date", "delivery day", "delivery window",
                        "deliver by"),
    "cargo_lines": ("cargo", "freight", "pieces", "weight", "commodity",
                    "pallets", "product"),
    "service": ("equipment", "trailer", "trailer type", "service type",
                "truck type", "kind of run"),
    "rate": ("rate", "pay", "price", "amount", "linehaul", "line haul"),
    "notes": ("notes", "note", "comment", "comments", "remarks",
              "special instructions", "instructions"),
    "control_name": ("load control", "who to call", "dispatcher"),
    "control_phone": ("load control phone",),
    # Capture-time, published by Dispatch alongside the card.
    "source_board": ("board", "load board", "posted on", "source board"),
}

#: Fields where a reference is read out phonetically -- "bravo charlie delta" --
#: and is only useful collapsed. Keyed by the form's field key.
PHONETIC_FIELDS = ("load_number", "control_ref", "source_board")

#: Move to the next field. **Mike moves the cursor. Nothing else does.**
NEXT = ("next", "next field", "next one", "okay next", "ok next", "go on",
        "move on", "continue")

#: Leave this one empty and move on. Sparse capture is valid capture.
SKIP = ("skip", "skip it", "none", "nothing", "not given", "blank", "leave it")

#: Back up one field.
BACK = ("back", "go back", "back up", "previous", "last one")

#: End the capture and send it.
DONE = ("done", "that's it", "thats it", "that is it", "log it", "send it",
        "submit", "that's all", "thats all", "finished", "end of load")

#: ...and throw it away. Deliberately distinct words: nothing that sounds like
#: "done" may cancel, and nothing that sounds like "cancel" may send.
CANCEL = ("cancel", "scrap it", "forget it", "throw it out", "start over")

#: Empty the field he is on.
SCRATCH = ("scratch that", "scratch it", "undo that", "undo", "no not that",
           "strike that")


class NothingRecognised(ValueError):
    """The phrase named no field, and JOE will not guess which one it meant."""


class NoForm(RuntimeError):
    """Dispatch did not publish the form, so there is nothing to fill in.

    **There is no fallback and there must not be one.** A remembered form is the
    defect that produced this rewrite, with a longer fuse.
    """


def _normalise(text: str) -> str:
    # The recognizer punctuates what it hears, and it heard "Done!". A command
    # that fails because of an exclamation mark is one Mike says again louder,
    # which adds one.
    return re.sub(r"\s+", " ", (text or "").strip().lower()).strip(" .,:;-!?\"'")


def is_next(text: str) -> bool:
    return _normalise(text) in NEXT


def is_skip(text: str) -> bool:
    return _normalise(text) in SKIP


def is_back(text: str) -> bool:
    return _normalise(text) in BACK


def is_done(text: str) -> bool:
    return _normalise(text) in DONE


def is_cancel(text: str) -> bool:
    return _normalise(text) in CANCEL


def is_scratch(text: str) -> bool:
    return _normalise(text) in SCRATCH


def command(text: str) -> str:
    """Which command was that, if any. "" when it is content, not a command."""
    for name, check in (("NEXT", is_next), ("SKIP", is_skip), ("BACK", is_back),
                        ("DONE", is_done), ("CANCEL", is_cancel),
                        ("SCRATCH", is_scratch)):
        if check(text):
            return name
    return ""


class Capture:
    """One listing, filled in as it is read out, against Dispatch's own form.

    Construct it with what `/api/joe/mission-template` published. It holds no
    opinion about how it is displayed or where it is sent -- the console prints
    it, `DispatchPort` sends it, and neither belongs here.
    """

    def __init__(self, published: dict, channel: str = "VOICE"):
        fields = (published or {}).get("fields")
        if not fields:
            raise NoForm("Dispatch published no form: %s"
                         % ((published or {}).get("note") or "no fields"))

        self.channel = str(channel).upper()

        # Capture-time facts come first: which board this was found on is not a
        # fact about the freight, so the Mission Card does not carry it -- and
        # without it the seventh contract would refuse every capture read off
        # the card. Dispatch publishes these with their own questions.
        capture_only = [dict(spec, section="CAPTURE",
                             opportunity_field=spec["key"])
                        for spec in (published or {}).get("capture_only") or ()]

        #: The form, exactly as Dispatch published it. Never edited here.
        self.form = capture_only + list(fields)
        self.order = tuple(f["key"] for f in self.form)
        self.by_key = {f["key"]: f for f in self.form}

        contract = (published or {}).get("opportunity") or {}
        self.contract_fields = tuple(contract.get("fields") or ())
        #: What the seventh contract will refuse a capture without. **Dispatch
        #: decides this, not JOE** -- it arrives with the form.
        self.contract_required = tuple(contract.get("required") or ())

        self.values = {key: "" for key in self.order}
        self.cursor = 0
        self.heard = []

        #: Synonyms whose field Dispatch does not have. **Reported, not
        #: ignored**: a field renamed upstream would otherwise fail silently,
        #: matching nothing and looking like a recognition problem.
        self.unknown_synonyms = tuple(sorted(set(SYNONYMS) - set(self.by_key)))

    # ---- what to say and what to ask ----------------------------------

    def label(self, key: str = "") -> str:
        return self.by_key[key or self.field]["label"]

    @property
    def field(self) -> str:
        return self.order[min(self.cursor, len(self.order) - 1)]

    @property
    def asking(self) -> str:
        """The question, in the form's own words. **Never JOE's.**"""
        return self.by_key[self.field].get("spoken") or self.label()

    @property
    def choices(self) -> tuple:
        return tuple(self.by_key[self.field].get("choices") or ())

    # ---- where he is --------------------------------------------------

    def advance(self) -> str:
        self.cursor = min(self.cursor + 1, len(self.order) - 1)
        return self.field

    def retreat(self) -> str:
        self.cursor = max(self.cursor - 1, 0)
        return self.field

    def go_to(self, key: str) -> str:
        if key in self.by_key:
            self.cursor = self.order.index(key)
        return self.field

    # ---- filling ------------------------------------------------------

    def add(self, spoken: str) -> str:
        """Put what was said into the field he is on, appending to what is there.

        **Appending, not replacing.** An address may take three breaths, and
        losing the first two because he paused to read the third is the defect
        this whole design exists to avoid.
        """
        text = self._corrected(spoken)
        self.heard.append(spoken)
        existing = self.values[self.field]
        self.values[self.field] = (existing + " " + text).strip() if existing else text
        return self.values[self.field]

    def clear_current(self) -> str:
        self.values[self.field] = ""
        return self.field

    def _corrected(self, spoken: str) -> str:
        if self.channel != "VOICE":
            return spoken.strip()
        text = correct_mishearings(apply_spelled_corrections(spoken))
        if self.field in PHONETIC_FIELDS:
            text = collapse_phonetic(text)
        return text.strip()

    def name_of(self, spoken: str) -> tuple:
        """Return `(field_key, value)` when a phrase names a field, or raise.

        **Labels come from the published form**; the everyday words come from
        `SYNONYMS`. Longest first, so "pickup date" never loses to "pickup".
        """
        text = (spoken or "").strip().strip(".")
        if not text:
            raise NothingRecognised("nothing was said")

        names = []
        for key, field in self.by_key.items():
            label = re.sub(r"\(.*?\)", "", field["label"]).strip().lower()
            for word in (label,) + tuple(SYNONYMS.get(key, ())):
                if word:
                    names.append((len(word), word, key))
        names.sort(reverse=True)

        lowered = text.lower()
        for _length, word, key in names:
            match = re.match(r"^%s\b[\s,:.\-]*" % re.escape(word), lowered)
            if not match:
                continue
            value = text[match.end():].strip().strip(",.")
            if not value:
                raise NothingRecognised("%r with nothing after it" % word)
            return key, value

        raise NothingRecognised(text)

    # ---- state --------------------------------------------------------

    @property
    def missing(self) -> list:
        """Contract fields still empty. **Dispatch decides what is required**,
        not JOE -- the list arrives with the form."""
        need = [key for key, field in self.by_key.items()
                if field.get("opportunity_field") in self.contract_required
                and not self.values[key]]
        return [k for k in self.order if k in need]

    def payload(self) -> dict:
        """What goes to the seventh contract.

        Fields the contract cannot carry are **named and kept in notes**, not
        dropped: losing a load number because a contract has not caught up with
        a screen would be the program deciding what matters.
        """
        sent, carried = {}, []
        for key in self.order:
            value = self.values[key]
            if not value:
                continue
            onto = self.by_key[key].get("opportunity_field")
            if onto:
                sent[onto] = value
            else:
                carried.append("%s %s" % (self.label(key), value))

        if sent.get("rate"):
            parsed = parse_dictation("x to y " + str(sent["rate"]),
                                     channel=self.channel)
            if parsed.get("rate"):
                sent["rate"] = parsed["rate"]

        if carried:
            existing = [sent["notes"]] if sent.get("notes") else []
            sent["notes"] = " | ".join(carried + existing)

        sent["captured_via"] = self.channel
        sent["raw_dictation"] = " | ".join(self.heard)
        return sent

    # ---- the card, as it stands ---------------------------------------

    def lines(self, *, everything: bool = False) -> list:
        """The card as it stands, for a window beside the load board.

        **The arrow is the most important character on it.** Thirty-three fields
        do not fit a glance, so unless asked for everything this shows what has
        been filled, the field he is on, and what is still needed.
        """
        out = ["  MISSION CARD", ""]
        section = ""
        for key in self.order:
            value = self.values[key]
            here = key == self.field
            needed = key in self.missing
            if not everything and not (value or here or needed):
                continue
            if self.by_key[key]["section"] != section:
                section = self.by_key[key]["section"]
                out.append("   %s" % section)
            out.append("  %s %s %-30s %s" % (">" if here else " ",
                                             "*" if needed else " ",
                                             self.label(key) + ":",
                                             value or "-"))
        out.append("")
        if self.missing:
            out.append("    * still needed: %s"
                       % ", ".join(self.label(k) for k in self.missing))
        else:
            out.append("    Ready. Say DONE to log it.")
        return out
