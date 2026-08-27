"""Which mailboxes Amendment 1 approves for sending. One list, one place.

Amendment 1, signed by Mike Zachary on 27 August 2026, names exactly two:

    ops@l1truck.com
    admin@l1truck.com

WHY THIS IS NOT READ FROM CONFIGURATION. Configuration says what is *connected*.
This says what is *approved to send*, and those are different questions with
different authorities behind them. A mailbox added to joe.config.json is a
machine setting; a mailbox added here would be a constitutional amendment.
Reading the send list from a config file would let an edit to a settings file
widen JOE's transmission authority silently, which is exactly the drift the
knowledge doctrine was written to end.

jax1313@outlook.com is Mike's personal address. It is not approved, has never
been configured, and is not discovered by the mailbox registry. It is named
here only so that its absence is deliberate and visible rather than incidental.
"""

from __future__ import annotations

# Amendment 1, Approved Mailboxes. Lower case; comparison is case-insensitive.
APPROVED_SENDERS = (
    "ops@l1truck.com",
    "admin@l1truck.com",
)

# Named so that "why isn't my personal email here" has an answer in the source
# rather than only in a conversation.
EXPLICITLY_NOT_APPROVED = (
    "jax1313@outlook.com",
)


def normalise(address: str) -> str:
    return str(address or "").strip().lower()


def is_approved_sender(address: str) -> bool:
    """True only for a mailbox Amendment 1 names."""
    return normalise(address) in APPROVED_SENDERS


def refusal_for(address: str) -> str:
    """Why this mailbox may not send, in words that name the authority."""
    wanted = normalise(address)
    if not wanted:
        return "no mailbox was named"
    if wanted in EXPLICITLY_NOT_APPROVED:
        return (
            wanted + " is a personal account and is not approved for Level 1 "
            "Transport operation. Amendment 1 approves "
            + " and ".join(APPROVED_SENDERS) + "."
        )
    return (
        wanted + " is not an approved sending mailbox. Amendment 1 approves "
        + " and ".join(APPROVED_SENDERS) + ", and adding one is an amendment, "
        "not a setting."
    )
