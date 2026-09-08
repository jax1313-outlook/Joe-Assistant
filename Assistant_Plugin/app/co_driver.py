"""JOE as a voice co-driver: speak a board listing, hear it back, find it logged.

    python -m app.co_driver

WHAT THIS IS. The whole loop, end to end, with nothing simulated in it:

    microphone  ->  faster-whisper  ->  JOE's router  ->  the dictation parser
                ->  POST /api/joe/opportunity  ->  Dispatch mints the id
                ->  Windows speaks the echo back

Every piece of that already existed. This file is the wire between them, and it
is deliberately thin: if something here grows a rule, the rule is in the wrong
place.

WHY IT ASKS BEFORE IT LISTENS. Nothing executes by default, and a program that
holds the microphone open is a program recording a cab. Mike presses Enter, JOE
records for a fixed few seconds, and the microphone closes again. There is no
wake word listening in the background and there is not going to be one.

WHAT IT REFUSES TO DO. It does not log anything Dispatch did not confirm, and it
does not invent an id when Dispatch is unreachable -- Dispatch is the sole
identity authority and a capture it never saw is a capture that did not happen.
It says so out loud, in the same voice it uses for success, because a failure
Mike cannot hear is the 70 MPH defect this program has already shipped once.

THE ONE SENTENCE IT SAYS BACK is the whole safety mechanism. Mike is looking at
the board listing while JOE reads back the board, the lane and the rate. If the
recognizer heard "Dad" for DAT, that sentence is where he catches it, and it is
the only place he will.
"""

from __future__ import annotations

import sys

from . import bootstrap  # noqa: F401  - installs component import paths
from .service import AssistantService

# Long enough for a full listing spoken at a normal pace -- board, lane, pieces,
# equipment, rate, pickup -- and short enough that a mis-start is cheap to redo.
LISTEN_SECONDS = 12

WAKE = "log this one"

BANNER = """
  JOE - VOICE CO-DRIVER
  Opportunity capture. Speak a board listing; Dispatch records it.
"""

HOW = """
  Say it the way it reads on the board:

      "Log this one. DAT, Jacksonville to Tampa, one pallet, dry van,
       seven fifty, pickup Thursday."

  Board and lane are what a load is. Everything else is optional -- a capture
  with gaps beats a listing lost to the next screen.

  ENTER  speak a listing        Q then ENTER  stop
"""


def _listener(service):
    """The recognizer JOE is configured to hear through.

    Reused, not rebuilt: this is the same adapter the rest of JOE listens with,
    holding the same model and the same microphone preference.
    """
    from adapters import whisper_listen

    voice = service.config.section("voice")
    whisper = dict(voice.get("whisper") or {})
    return whisper_listen.WhisperListener(
        model=str(whisper.get("model", "")),
        device=str(voice.get("preferred_microphone", "")),
        compute_type=str(whisper.get("compute_type", "")),
        enabled=bool(voice.get("enabled", True)),
    )


def _status(service, listener) -> tuple[bool, list]:
    """What is true about this machine right now, in the locked vocabulary.

    Returned rather than printed so the caller decides what to do with a
    blocker. Nothing here guesses: every line is a measurement.
    """
    import os

    lines = []
    ready = True

    probe = listener.probe()
    if probe.get("blocker"):
        lines.append(("Microphone", "UNAVAILABLE", probe["blocker"]))
        ready = False
    else:
        lines.append(("Microphone", "LIVE", probe.get("device", "") or "Windows default"))

    lines.append(("Recognizer", "CONFIGURED",
                  "faster-whisper " + listener.model_name + ", local, no network"))

    endpoint = str(service.config.get("dispatch", "endpoint", "") or "")
    token = str(os.environ.get("DISPATCH_JOE_TOKEN") or "")
    if not endpoint:
        lines.append(("Dispatch node", "UNCONFIGURED",
                      "set dispatch.endpoint in joe.config.json"))
        ready = False
    elif not token:
        lines.append(("Dispatch node", "UNCONFIGURED",
                      "DISPATCH_JOE_TOKEN is not set in this environment"))
        ready = False
    else:
        lines.append(("Dispatch node", _reachable(endpoint), endpoint))

    lines.append(("Driver", "CONFIGURED", service.driver))
    return ready, lines


def _reachable(endpoint: str) -> str:
    """LIVE means the node answered just now. Nothing weaker earns the word."""
    import urllib.error
    import urllib.request

    try:
        urllib.request.urlopen(endpoint.rstrip("/") + "/login", timeout=3)
    except urllib.error.HTTPError:
        return "LIVE"          # it answered; what it said is not our business
    except Exception:          # noqa: BLE001
        return "UNAVAILABLE"
    return "LIVE"


def _capture_once(service, listener) -> None:
    print()
    print("  SPEAK NOW -- %d seconds" % LISTEN_SECONDS, flush=True)
    heard = listener.listen(seconds=LISTEN_SECONDS)

    if not heard.get("recognized"):
        # A recognizer that guesses is worse than one that fails, so this is the
        # honest end of the road and not a retry loop.
        print("  NOTHING HEARD. " + (heard.get("error") or "").upper())
        return

    spoken = heard["text"].strip()
    print("  HEARD: " + spoken)

    if WAKE not in spoken.lower() and "log this" not in spoken.lower():
        # Deliberate. Every other capability JOE has is a read; this one writes,
        # and writing on a sentence that was not addressed to it is how a
        # conversation in the cab becomes a row in the database.
        print("  NOT A CAPTURE. Say \"log this one\" first. Nothing was written.")
        return

    answer = service.ask(spoken, channel="voice").response
    print()
    print("  " + (answer.spoken_summary or answer.answer or "").strip())
    for notice in getattr(answer, "notices", []) or []:
        print("  " + str(notice))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    print(BANNER)
    service = AssistantService()
    listener = _listener(service)

    ready, lines = _status(service, listener)
    for label, state, detail in lines:
        print("    %-16s %-13s %s" % (label, state, detail))

    if not ready:
        print()
        print("  NOT READY. Nothing above is guessed; fix what is UNCONFIGURED")
        print("  or UNAVAILABLE and run this again.")
        return 1

    print(HOW)

    while True:
        try:
            answer = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if answer in ("q", "quit", "exit", "stop"):
            return 0
        try:
            _capture_once(service, listener)
        except KeyboardInterrupt:
            print()
            print("  STOPPED. Nothing was written.")
        except Exception as failure:  # noqa: BLE001
            # Reported, never swallowed. The defect this program has already
            # shipped once was a driver tapping a button and being told it
            # worked when it had not.
            print("  NOT LOGGED. %s: %s" % (type(failure).__name__, failure))


if __name__ == "__main__":
    raise SystemExit(main())
