"""Staged transmission under Amendment 1. INERT - it cannot send.

WHAT THIS IS. The clerk that prepares an envelope, reads it back, waits to be
told, and then hands it to a transport that does not exist yet. Every condition
Mike ruled binding on 27 August 2026 is enforced here, at the seam, before any
transport is ever bound.

WHAT THIS IS NOT. A send path. There is no SMTP client, no MailItem, no outbox,
no network call, and no import that could reach one. `transmit()` returns a
refusal listing why, and it will keep returning a refusal after a transport is
written, until the gate below is deliberately opened.

    Building the envelope is reversible. Sending it is not. The gate belongs
    where the consequence is.

THE CONDITIONS, and where each one lives:

  2.3.1  explicit authorisation, per message   approve() binds to one id
  2.3.2  read-back before authorisation        approve() refuses without a
                                               read_back() on THAT id
  2.3.3  nothing supplied that Mike did not    stage() rejects a binding fact
         state                                 whose origin is JOE
  2.3.4  a withdrawal window                   withdraw() until transmitted;
                                               approval also expires
  2.3.5  Dispatch owns the record              the local record is marked
                                               PROVISIONAL and says so
  2.3.6  an unheard command is not a command   approve() refuses below a
                                               confidence floor
  6.1    hearing proven first                  arming_state() reads the real
                                               hearing proof for this machine

WHY THE FACTS CARRY AN ORIGIN. The failure this prevents is quiet and
plausible: JOE fills in a rate, a date, or a term that nobody stated, the
read-back sounds right because it is fluent, and Mike approves a number he
never chose. A binding fact whose origin is JOE is refused at staging - before
it can ever reach a read-back and sound authoritative.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Mike's own list, 27 August 2026. Matched on the whole utterance after
# normalisation, never as a substring: "don't send that" must never approve.
APPROVAL_PHRASES = frozenset({
    "send", "send it", "send it now",
    "approved send", "approved, send",
    "transmit", "transmit it",
    "looks good send", "looks good, send",
    "good send", "yes send", "ok send", "okay send",
})

# Anything that reads as a refusal wins over anything that reads as approval.
# "no, don't send" contains "send"; matching the whole utterance handles that,
# and this list is the belt to that pair of braces.
REFUSAL_MARKERS = ("not", "n't", "no ", "stop", "cancel", "wait", "hold", "don")

WITHDRAWAL_PHRASES = frozenset({
    "stop", "cancel", "withdraw", "hold", "hold it", "belay", "no",
    "stop it", "cancel that", "don't send", "do not send", "abort",
})

# 2.3.6. Below this, JOE did not hear a command; it heard a noise that
# resembled one. Whisper reports 0.0-1.0.
MINIMUM_APPROVAL_CONFIDENCE = 0.75

# 2.3.2 / 2.3.4. A read-back goes stale. Approving a summary heard four minutes
# ago approves whatever has happened since.
READBACK_VALID_SECONDS = 120


class State:
    STAGED = "STAGED"
    READ_BACK = "READ_BACK"
    APPROVED = "APPROVED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    REFUSED = "REFUSED"
    TRANSMITTED = "TRANSMITTED"      # unreachable in this build


class TransmissionError(RuntimeError):
    pass


@dataclass(frozen=True)
class BindingFact:
    """One value the transmission turns on, and who supplied it.

    origin is never "JOE". A fact JOE inferred, calculated, remembered, or
    found plausible is not a fact Mike stated, and 2.3.3 is the rule that a
    transmission may carry only what a human put in it.
    """

    label: str
    value: str
    origin: str          # MIKE | DISPATCH | LIBRARY | OUTLOOK | BROKER

    FORBIDDEN_ORIGIN = "JOE"

    def is_originated_by_joe(self) -> bool:
        return self.origin.strip().upper() == self.FORBIDDEN_ORIGIN


@dataclass
class Transmission:
    """One envelope, staged and waiting. Never sent by this build."""

    mailbox: str
    recipients: tuple
    subject: str
    body: str
    facts: tuple = ()
    attachments: tuple = ()
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: str = State.STAGED
    staged_at: str = ""
    read_back_at: str = ""
    approved_at: str = ""
    refusal: str = ""

    def read_back_is_current(self, now=None) -> bool:
        """2.3.2. A stale read-back is not a read-back."""
        if not self.read_back_at:
            return False
        now = now or datetime.now(timezone.utc)
        spoken = datetime.fromisoformat(self.read_back_at)
        return (now - spoken) <= timedelta(seconds=READBACK_VALID_SECONDS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise(phrase: str) -> str:
    keep = [c.lower() if (c.isalnum() or c.isspace() or c == "'") else " "
            for c in (phrase or "")]
    return " ".join("".join(keep).split())


def is_approval(phrase: str) -> bool:
    """Whole-utterance match, refusals excluded first.

    Substring matching would make "no, don't send that" an approval. It is the
    opposite of one, and on a voice channel that mistake sends a packet.
    """
    said = _normalise(phrase)
    if not said:
        return False
    if any(marker in said for marker in REFUSAL_MARKERS):
        return False
    return said in APPROVAL_PHRASES


def is_withdrawal(phrase: str) -> bool:
    return _normalise(phrase) in WITHDRAWAL_PHRASES


# ---- the gate ----------------------------------------------------------

def arming_state(config=None, runtime_data=None) -> dict:
    """Why JOE cannot transmit. Every blocker, measured, not assumed.

    This is deliberately a list rather than a boolean. "Not armed" is a
    conclusion; the blockers are the evidence for it, and a status line that
    says only "disabled" teaches Mike nothing about what would change it.
    """
    blockers = []

    # 1. The one that cannot be configured away: there is no transport.
    blockers.append(
        "no transport exists - this build has no SMTP client, no MailItem, "
        "no outbox, and no code path that could reach one"
    )

    # 2. The Outlook guard forbids .Send( outright.
    try:
        from adapters.outlook_com import FORBIDDEN_COM_CALLS
        if ".Send(" in FORBIDDEN_COM_CALLS:
            blockers.append(
                "the Outlook read-only guard refuses any script containing "
                ".Send( - adapters/outlook_com.py"
            )
    except Exception:  # noqa: BLE001 - absence of the adapter is not a pass
        blockers.append("the Outlook adapter could not be read to confirm its guard")

    # 3. Configuration.
    outlook = (config or {}).get("outlook", {}) if isinstance(config, dict) else {}
    if outlook.get("read_only", True):
        blockers.append("outlook.read_only is true in configuration")

    # 4. Condition 6.1 - hearing proven on THIS machine.
    if runtime_data is not None:
        try:
            from .hearing_proof import last as last_hearing
            proof = last_hearing(runtime_data)
            if not (proof and proof.get("passed")):
                blockers.append(
                    "condition 6.1 - hearing has not been proven on this "
                    "machine; run proof\\prove_microphone.py --say "
                    '"JOE send it now"'
                )
        except Exception:  # noqa: BLE001
            blockers.append("condition 6.1 - the hearing proof could not be read")
    else:
        blockers.append("condition 6.1 - hearing proof was not checked")

    return {"armed": False, "blockers": blockers}


# ---- staging -----------------------------------------------------------

def stage(mailbox: str, recipients, subject: str, body: str,
          facts=(), attachments=()) -> Transmission:
    """Prepare an envelope. 2.3.3 is enforced here, before anything is spoken.

    A fact JOE originated is refused at staging rather than at approval,
    because by approval time it has already been read aloud in JOE's confident
    voice and has started to sound like something Mike said.
    """
    from app.mailbox_authority import is_approved_sender

    if not is_approved_sender(mailbox):
        raise TransmissionError(
            "not an approved sending mailbox under Amendment 1: " + str(mailbox))

    recipients = tuple(r for r in (recipients or ()) if str(r).strip())
    if not recipients:
        raise TransmissionError("a transmission needs at least one recipient")

    facts = tuple(facts or ())
    invented = [f.label for f in facts if f.is_originated_by_joe()]
    if invented:
        raise TransmissionError(
            "condition 2.3.3 - these values were originated by JOE and may not "
            "appear in a transmission: " + ", ".join(invented))

    return Transmission(
        mailbox=mailbox,
        recipients=recipients,
        subject=str(subject or ""),
        body=str(body or ""),
        facts=facts,
        attachments=tuple(attachments or ()),
        staged_at=_now(),
    )


def read_back(transmission: Transmission) -> str:
    """2.3.2. What Mike hears before he is asked to approve anything.

    Ordered so the irreversible parts come first. Mike is driving; if he stops
    listening after two sentences he has still heard who it goes to and what
    changed.
    """
    lines = [
        "Ready for review.",
        "To " + ", ".join(transmission.recipients)
        + ", from " + transmission.mailbox + ".",
        "Subject: " + (transmission.subject or "(none)") + ".",
    ]
    for fact in transmission.facts:
        lines.append(fact.label + ": " + fact.value + ".")
    if transmission.attachments:
        lines.append(
            str(len(transmission.attachments)) + " attachment"
            + ("s" if len(transmission.attachments) != 1 else "")
            + ": " + ", ".join(transmission.attachments) + ".")
    else:
        lines.append("No attachments.")
    lines.append("Say send to transmit, or stop to hold it.")

    transmission.state = State.READ_BACK
    transmission.read_back_at = _now()
    return " ".join(lines)


def approve(transmission: Transmission, phrase: str,
            confidence: float = 1.0, now=None) -> Transmission:
    """2.3.1, 2.3.2, 2.3.6. Bind one approval to one read-back envelope."""
    if transmission.state == State.WITHDRAWN:
        transmission.refusal = "that was already withdrawn"
        return transmission

    if transmission.state != State.READ_BACK:
        transmission.state = State.REFUSED
        transmission.refusal = (
            "condition 2.3.2 - nothing was read back, so there is nothing to "
            "approve")
        return transmission

    if not transmission.read_back_is_current(now):
        transmission.state = State.EXPIRED
        transmission.refusal = (
            "the read-back is stale; I will read it again before you approve it")
        return transmission

    if not is_approval(phrase):
        transmission.refusal = "that was not an approval"
        return transmission

    if float(confidence) < MINIMUM_APPROVAL_CONFIDENCE:
        transmission.state = State.REFUSED
        transmission.refusal = (
            "condition 2.3.6 - I am not confident I heard that. Say it again.")
        return transmission

    transmission.state = State.APPROVED
    transmission.approved_at = _now()
    transmission.refusal = ""
    return transmission


def withdraw(transmission: Transmission) -> Transmission:
    """2.3.4. Until it is transmitted, it can be stopped."""
    if transmission.state == State.TRANSMITTED:
        raise TransmissionError(
            "it has already gone; JOE cannot unsend, and will not claim to")
    transmission.state = State.WITHDRAWN
    return transmission


# ---- the part that does not work, on purpose ---------------------------

def transmit(transmission: Transmission, config=None, runtime_data=None) -> dict:
    """INERT. Returns a refusal, and never sends anything.

    This exists so the seam is real and testable now rather than being written
    in a hurry beside a working transport later. It refuses in a fixed order:
    the gate first, so that "it was approved" can never on its own be mistaken
    for "it went".
    """
    gate = arming_state(config, runtime_data)
    if not gate["armed"]:
        return {
            "sent": False,
            "state": transmission.state,
            "reason": "transmission is not armed in this build",
            "blockers": gate["blockers"],
            "record": provisional_record(transmission, sent=False),
        }

    # Unreachable in this build. Left as the explicit refusal it is, so that
    # arming the gate alone can never be enough to send.
    return {
        "sent": False,
        "state": transmission.state,
        "reason": "no transport is bound; arming the gate does not create one",
        "blockers": ["no transport is bound"],
        "record": provisional_record(transmission, sent=False),
    }


def provisional_record(transmission: Transmission, sent: bool) -> dict:
    """2.3.5, in Mike's words.

    > JOE may retain a temporary interaction record showing that transmission
    > occurred, but JOE shall never become the authoritative source of
    > transmission history.

    So every record says so on its face. `authoritative` is False and
    `owner` names Dispatch, whether or not Dispatch is bound yet - a record
    that forgets who owns it is how JOE would become the owner by default.
    """
    return {
        "transmission_id": transmission.id,
        "mailbox": transmission.mailbox,
        "recipients": list(transmission.recipients),
        "subject": transmission.subject,
        "attachments": list(transmission.attachments),
        "facts": [
            {"label": f.label, "value": f.value, "origin": f.origin}
            for f in transmission.facts
        ],
        "state": transmission.state,
        "staged_at": transmission.staged_at,
        "read_back_at": transmission.read_back_at,
        "approved_at": transmission.approved_at,
        "sent": bool(sent),
        "authoritative": False,
        "owner": "Dispatch",
        "note": (
            "PROVISIONAL. JOE is not the authoritative source of transmission "
            "history. Hand to Dispatch when it is bound."
        ),
    }
