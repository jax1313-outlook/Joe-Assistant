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
listens until he stops talking, and the microphone closes again. There is no
wake word listening in the background and there is not going to be one.

**Three seconds of silence ends it. A clock does not.** The first version gave
him a fixed twelve seconds and cut him off mid-sentence, taking the last three
digits of a phone number with it. Owner ruling, 2026-09-08: *"in real
operations, there should be no cutoff. Silence for three seconds should mean
that's a break."* That is the 70 MPH Test -- a man reading a board should not
also be racing a countdown he cannot see.

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

# **A ceiling, not a duration.** Three seconds of silence ends the recording --
# Owner ruling, 2026-09-08, after twelve seconds cut him off mid-sentence and
# took the last three digits of a phone number with it: "in real operations,
# there should be no cutoff."
#
# This number exists only so a microphone left open by a fault stops on its own.
# It should never be the thing that ends a sentence, and two minutes is far
# longer than anything a person says to a co-driver in one breath.
LISTEN_CEILING_SECONDS = 120

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

  Take as long as you need. It stops three seconds after you do.

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
        # `device_in_use`, not `device` -- the key I first read does not exist,
        # so every run reported "Windows default" whatever it was actually bound
        # to. Naming the wrong microphone is worse than naming none: Mike speaks
        # into the headset while JOE listens to the laptop lid.
        #
        # Windows writes the Bluetooth name across two lines. One line here.
        device = " ".join((probe.get("device_in_use") or "").split()) \
            or "Windows default"
        chosen = "chosen" if probe.get("device_chosen_by_joe") else "Windows default"
        lines.append(("Microphone", "LIVE", "%s  [%s]" % (device, chosen)))

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
    print("  SPEAK NOW -- stop when you are done, it listens for the silence",
          flush=True)
    heard = listener.listen(seconds=LISTEN_CEILING_SECONDS)

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

    # **Two ways to say the same thing, and Mike chooses by how he pauses.**
    #
    # "Log this one. DAT, Jacksonville to Tampa, seven fifty" -- the whole
    # listing in one breath, parsed as a sentence. Fast, and it is what a
    # listing already read looks like.
    #
    # "Log this." then a pause -- the field-by-field read, which is how he
    # described working from a board: open a listing and read it out, label by
    # label, with the card filling beside it.
    if _is_bare_wake(spoken):
        _capture_by_field(service, listener)
        return

    answer = service.ask(spoken, channel="voice").response
    print()
    print("  " + (answer.spoken_summary or answer.answer or "").strip())
    for notice in getattr(answer, "notices", []) or []:
        print("  " + str(notice))


def _is_bare_wake(spoken: str) -> bool:
    """Was that just the wake phrase, with no listing after it?"""
    import re

    rest = re.sub(r"^\s*(?:joe[,.\s]+)?log\s+(?:this|it)\s*(?:one|load|opportunity)?",
                  "", spoken.strip(), flags=re.IGNORECASE)
    return not re.sub(r"[^A-Za-z0-9]", "", rest)


def _capture_by_field(service, listener) -> None:
    """Read a listing to JOE, one field at a time, at Mike's pace.

    **He moves the cursor. Nothing else does.** Owner ruling, 2026-09-08, after
    the first live run: *"the movement field by field, it should allow me to give
    the command to move to the next field. Otherwise, it is going to constantly
    truncate the input."*

    Silence ends an *utterance* -- that is what stopped the countdown cutting him
    off mid-sentence. It must not also end a *field*: he is reading off a board,
    and a pause while he finds the next value is a man working, not a man
    finished. So a field takes as many breaths as it takes, and NEXT ends it.

    **JOE names the field it is waiting for, every time.** The first live run
    failed partly because he did not know what it wanted -- he said "Special
    instructions" and "Comment" as labels on their own, waiting to be asked.
    Being asked is cheaper than remembering.
    """
    from . import field_capture as fc
    from .service import _dispatch_token

    token = _dispatch_token()
    published = service.dispatch.mission_template(token=token,
                                                  driver=service.driver)
    try:
        capture = fc.Capture(published, channel="VOICE")
    except fc.NoForm as no_form:
        # **No fallback, and there must not be one.** A remembered form is the
        # defect this whole change exists to remove, with a longer fuse.
        print()
        print("  NO FORM. Dispatch did not publish the Mission Card.")
        print("  %s" % no_form)
        print("  Nothing was written.")
        return

    if capture.unknown_synonyms:
        # Loudly, not silently: a field renamed in Dispatch would otherwise just
        # stop matching and look like a recognition problem.
        print()
        print("  NOTE: JOE knows words for fields Dispatch no longer has -- %s."
              % ", ".join(capture.unknown_synonyms))

    print()
    print("  READING A LISTING from Dispatch's own Mission Card (%d fields)."
          % len(capture.form))
    print("  JOE asks; you answer; you say when to move on.")
    print()
    print("     NEXT      this field is finished, go to the next")
    print("     SKIP      leave it empty and go on")
    print("     BACK      go back one field")
    print("     SCRATCH   empty this field and start it again")
    print("     DONE      log it            CANCEL   throw it away")
    print()
    print("  Take as many breaths as you need. Only NEXT moves you on.")

    quiet = 0
    while True:
        print()
        print("  %s   [%s]" % (capture.asking, capture.label()), flush=True)
        if capture.choices:
            print("     one of: %s" % " / ".join(capture.choices))
        heard = listener.listen(seconds=LISTEN_CEILING_SECONDS)

        if not heard.get("recognized"):
            quiet += 1
            if quiet >= 3:
                # Three silences in a row is a man who has stepped away or is
                # reading. Stop asking into an empty room -- the microphone is
                # open in a truck cab and that is not nothing.
                print("  STILL HERE. Press ENTER when you are ready, or type Q.")
                try:
                    if input("  > ").strip().lower().startswith("q"):
                        print("  STOPPED. Nothing was written.")
                        return
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                quiet = 0
            else:
                print("  (nothing heard)")
            continue
        quiet = 0

        spoken = heard["text"].strip()
        print("  HEARD: " + spoken)

        order = fc.command(spoken)
        if order == "CANCEL":
            print("  CANCELLED. Nothing was written.")
            return
        if order == "BACK":
            print("  BACK TO %s." % capture.label(capture.retreat()).upper())
            continue
        if order == "SKIP":
            capture.advance()
            continue
        if order == "SCRATCH":
            print("  CLEARED %s." % capture.label(capture.clear_current()).upper())
            print("\n".join(capture.lines()))
            continue
        if order == "NEXT":
            capture.advance()
            print("\n".join(capture.lines()))
            continue
        if order == "DONE":
            if capture.missing:
                # Board and lane are what a load is. Refusing here is cheaper
                # than a row Mike has to find and fix later.
                print("  NOT LOGGED. Still needed: %s."
                      % ", ".join(capture.label(f) for f in capture.missing))
                capture.go_to(capture.missing[0])
                continue
            break

        # Not a command, so it is content. Naming a field jumps to it; anything
        # else fills the field he is on.
        try:
            field, value = capture.name_of(spoken)
        except fc.NothingRecognised:
            print("  %s: %s" % (capture.label().upper(),
                                capture.add(spoken)))
            continue

        capture.go_to(field)
        capture.clear_current()
        print("  %s: %s" % (capture.label(field).upper(), capture.add(value)))

    result = service.dispatch.submit_opportunity(
        capture.payload(), token=token, driver=service.driver)

    print()
    if result.get("mode") == "LIVE_DISPATCH":
        echo = str(result.get("echo") or "LOGGED. OPPORTUNITY %s."
                   % result.get("opportunity_id", ""))
        print("  " + echo)
        service.speak(echo)
    else:
        note = str(result.get("note") or "").strip()
        print("  NOT LOGGED. DISPATCH DID NOT RECORD THIS CAPTURE. " + note)
        service.speak("NOT LOGGED. DISPATCH DID NOT ANSWER.")


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
        print("  and run this again.")
        return 1

    if any(state == "UNAVAILABLE" for _, state, _ in lines):
        # Not a refusal. CONOPS v1.1 treats the link as intermittent by design
        # and the node may come up in a minute -- each capture asks it again.
        # But saying nothing here would let Mike speak six listings into a
        # program that cannot record any of them.
        print()
        print("  DISPATCH IS NOT ANSWERING. You can start it and carry on --")
        print("  every capture asks again. Until it answers, nothing is recorded")
        print("  and JOE will say so each time.")

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
