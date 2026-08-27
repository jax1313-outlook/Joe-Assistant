"""Speaking a load card to a driver.

A load card is the handoff object. It presents an opportunity, a score, the
special requirements, the operational considerations and a recommendation, and
then it asks for a decision. It creates no operational truth: nothing becomes
authoritative until Mike decides. That is what makes it safe for JOE to carry -
JOE presents the card and relays the answer, and at no point holds the
decision itself.

The card shape is DISPATCH'S, not JOE's. Fields here are read, never invented,
and a field Dispatch does not supply is reported missing rather than filled in.
An assumed rate on a load card is the same failure as an assumed rate in an
email, and it arrives faster.

ONE SENTENCE, IN PRIORITY ORDER. Mike hears one sentence and asks for more if
he wants it. Which sentence depends on what would decide the load:

  1. A hard stop is the whole answer. Rate and score are irrelevant if the
     load cannot legally or physically be run, and leading with the money
     would bury it.
  2. Equipment that does not match is next, for the same reason - a flatbed
     load pays nothing to a dry van.
  3. Otherwise: the lane, the money, and the score. That is the shape of the
     decision when there is a decision to make.

A missing rate is not silence. "No rate posted" is a fact Mike acts on - it
means the load needs a phone call - so it is said, not skipped.
"""

from __future__ import annotations

# Mirrors DRAFT ONLY / NOT SENT. A card on a screen must never read as though
# the load were taken.
CARD_LABEL = "OPPORTUNITY ONLY\nNOT ACCEPTED"


def _city(place) -> str:
    """"Jacksonville, FL 32202" -> "Jacksonville". Spoken, the state and the
    ZIP are noise; they stay in the written card."""
    text = str(place or "").strip()
    return text.split(",")[0].strip() if text else ""


def _money(card) -> str:
    """What the load pays, or the fact that nobody said."""
    rate = card.get("rate")
    rpm = card.get("rpm")
    if rate is None:
        return "no rate posted"
    money = "$" + format(int(rate), ",") if float(rate) == int(rate) \
        else "$" + format(float(rate), ",.2f")
    if rpm is None:
        return money + ", no rate per mile given"
    return money + " at " + format(float(rpm), ".2f") + " a mile"


def spoken(card) -> str:
    """The one sentence. What would decide this load, and nothing else."""
    if not card:
        return "No load card."

    if card.get("hard_stop"):
        reason = str(card.get("hard_stop_reason") or "").strip()
        return "Hard stop: " + (reason or "no reason recorded") + "."

    equipment = str(card.get("equipment_required") or "").strip()
    if str(card.get("equipment_match") or "").lower() == "mismatch":
        needed = (" - needs " + equipment) if equipment else ""
        return "Equipment mismatch" + needed + "."

    origin = _city(card.get("origin"))
    destination = _city(card.get("destination"))
    lane = (origin + " to " + destination) if origin and destination else ""

    parts = [p for p in (equipment, lane) if p]
    miles = card.get("distance_miles")
    if miles:
        parts.append(format(int(miles), ",") + " miles")
    parts.append(_money(card))
    score = card.get("score")
    if score is not None:
        parts.append("scores " + str(score))
    return ", ".join(parts) + "."


def _row(label, value, missing="not stated") -> str:
    text = "" if value is None else str(value).strip()
    return "  " + label.ljust(22) + (text or missing)


def written(card) -> str:
    """The whole card, for the screen Mike reads parked.

    Every field Dispatch supplied, and an honest word for every field it did
    not. It ends by asking for a decision, because that is what a card is for.
    """
    if not card:
        return CARD_LABEL + "\n\nNo load card."

    lines = [CARD_LABEL, "", str(card.get("title") or "Load"), ""]

    if card.get("hard_stop"):
        lines += ["  HARD STOP             "
                  + str(card.get("hard_stop_reason") or "no reason recorded"),
                  ""]

    lines += [
        _row("Load", card.get("load_id")),
        _row("From", card.get("origin")),
        _row("To", card.get("destination")),
        _row("Distance", (format(int(card["distance_miles"]), ",") + " miles")
             if card.get("distance_miles") else None, "not stated"),
        _row("Deadhead", (format(float(card["deadhead_miles"]), ".0f") + " miles")
             if card.get("deadhead_miles") is not None else None, "not computed"),
        "",
        _row("Pays", _money(card)),
        _row("Score", card.get("score"), "not scored"),
        "",
        _row("Equipment", card.get("equipment_required")),
        _row("Match", card.get("equipment_match")),
        _row("Weight", (format(int(card["weight_lbs"]), ",") + " lbs")
             if card.get("weight_lbs") else None),
        _row("Pickup", card.get("pickup_window"), "no window given"),
        _row("Delivery", card.get("delivery_window"), "no window given"),
        "",
        _row("Broker", card.get("broker")),
        _row("Contact", card.get("broker_email") or card.get("broker_phone")),
    ]

    considerations = [
        ("Broker history", card.get("broker_intelligence")),
        ("Detention", card.get("detention_history")),
        ("Location", card.get("location_intelligence")),
        ("Position impact", card.get("position_impact")),
        ("Return home", card.get("return_home")),
        ("Hours of service", card.get("hos_risk")),
        ("Route", card.get("route_risk")),
        ("Tomorrow", card.get("tomorrow_position_risk")),
        ("Economics", card.get("economic_opportunity")),
    ]
    present = [(label, value) for label, value in considerations if value]
    if present:
        lines += ["", "OPERATIONAL CONSIDERATIONS"]
        lines += [_row(label, value) for label, value in present]

    if card.get("notes"):
        lines += ["", "NOTES", "  " + str(card["notes"])]

    lines += [
        "",
        "DECISION REQUIRED",
        "  This card asks. It decides nothing, and nothing here is accepted.",
        "  Go or no-go is yours.",
    ]
    return "\n".join(lines)
