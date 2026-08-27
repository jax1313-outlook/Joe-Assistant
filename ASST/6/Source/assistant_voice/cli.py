"""Command-line interface for Assistant Voice.

    py -m assistant_voice status
"""

from __future__ import annotations

import argparse
import json
import sys

from .driver_mode import (
    MAX_SPOKEN_WORDS,
    TOO_LONG_TO_READ_WORDS,
    DriverModeError,
    build_brief,
    check_length,
    prepare_for_speech,
    strip_unspeakable,
)
from .engines import (
    NOT_IMPLEMENTED_ENGINES,
    SilentTextToSpeech,
    TextSpeechToText,
    TextTextToSpeech,
)
from .session import SessionError, VoiceSession
from .utterance import UtteranceError

DIVIDER = "-" * 72
TRANSPORT_NOTICE = (
    "Voice transport only. No real microphone or speaker is used, nothing is "
    "interpreted, nothing is remembered, and no reasoning happens here."
)


def make_session(args) -> VoiceSession:
    tts = SilentTextToSpeech() if getattr(args, "silent", False) else TextTextToSpeech()
    confidence = getattr(args, "confidence", 1.0)
    return VoiceSession(
        stt=TextSpeechToText(confidence=confidence),
        tts=tts,
        allow_barge_in=not getattr(args, "no_barge_in", False),
    )


def cmd_say(args) -> int:
    session = make_session(args)
    try:
        brief = prepare_for_speech(args.text, args.location or "")
    except DriverModeError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    result = session.say(brief.spoken_text())
    fits, note = check_length(brief)
    if args.json:
        print(json.dumps({
            "brief": brief.to_dict(),
            "result": result.to_dict(),
            "fits_driver_mode": fits,
            "length_note": note,
        }, indent=2))
        return 0
    print(DIVIDER)
    print("SPOKEN TURN")
    print(DIVIDER)
    print("  " + brief.spoken_text())
    print()
    print("  words                    " + str(brief.spoken_word_count))
    print("  fits driver mode         " + str(fits) + "  (" + note + ")")
    print("  deferred to written copy " + str(brief.deferred))
    if brief.deferred:
        print("  defer reason             " + brief.defer_reason)
    print("  removed unspeakable      " + str(brief.removed_unspeakable))
    print("  summarized               False")
    print("  audio produced           False")
    print("  engine                   " + result.engine)
    print()
    print("  " + TRANSPORT_NOTICE)
    return 0


def cmd_brief(args) -> int:
    try:
        brief = build_brief(
            what_changed=args.changed,
            why_it_matters=args.matters or "",
            decision_required=args.decision or "",
            written_result_location=args.location or "",
        )
    except DriverModeError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    fits, note = check_length(brief)
    if args.json:
        print(json.dumps({**brief.to_dict(), "fits_driver_mode": fits, "length_note": note}, indent=2))
        return 0
    print(DIVIDER)
    print("DRIVER MODE BRIEF")
    print(DIVIDER)
    print("  what changed        " + brief.what_changed)
    print("  why it matters      " + (brief.why_it_matters or "(not supplied)"))
    print("  decision required   " + (brief.decision_required or "(none supplied)"))
    print("  written result      " + (brief.written_result_location or "(not stated)"))
    print(DIVIDER)
    print("  " + brief.spoken_text())
    print(DIVIDER)
    print("  words               " + str(brief.spoken_word_count))
    print("  fits driver mode    " + str(fits) + "  (" + note + ")")
    print("  summarized          False")
    return 0


def cmd_listen(args) -> int:
    session = make_session(args)
    transcript = session.listen(args.text)
    if args.json:
        print(json.dumps(transcript.to_dict(), indent=2))
        return 0
    print(DIVIDER)
    print("HEARD")
    print(DIVIDER)
    print("  text              " + (transcript.text or "(nothing)"))
    print("  confidence        " + str(transcript.confidence))
    print("  low confidence    " + str(transcript.is_low_confidence))
    print("  engine            " + transcript.engine)
    print("  interpreted       False")
    print("  understood        False")
    print()
    print("  " + TRANSPORT_NOTICE)
    return 0


def cmd_demo(args) -> int:
    """Run a short session showing queueing and barge-in."""
    session = make_session(args)
    session.enqueue("Pickup window moved to twelve hundred.")
    session.enqueue("The Richmond delivery now overlaps it by thirty minutes.")
    session.enqueue("This third line will be dropped when you interrupt.")
    session.state = "SPEAKING"
    session.barge_in()
    session.listen("what changed")
    session.say("Two appointments overlap. Nothing is decided.")
    session.close()
    if args.json:
        print(json.dumps({
            "status": session.status(),
            "events": session.transcript_log(),
        }, indent=2))
        return 0
    print(DIVIDER)
    print("VOICE SESSION DEMONSTRATION")
    print(DIVIDER)
    for event in session.events:
        print("  {0:<16} {1}".format(event.kind, event.detail))
    print(DIVIDER)
    status = session.status()
    for key in ("state", "stt_engine", "tts_engine", "heard", "spoken", "queued"):
        print("  {0:<28} {1}".format(key, status[key]))
    print()
    print("  " + TRANSPORT_NOTICE)
    return 0


def cmd_clean(args) -> int:
    cleaned = strip_unspeakable(args.text)
    if args.json:
        print(json.dumps({"original": args.text, "speakable": cleaned}, indent=2))
        return 0
    print(DIVIDER)
    print("UNSPEAKABLE CONTENT REMOVED")
    print(DIVIDER)
    print("  original   " + args.text)
    print("  speakable  " + cleaned)
    return 0


def cmd_status(args) -> int:
    session = make_session(args)
    status = session.status()
    status.update({
        "max_spoken_words": MAX_SPOKEN_WORDS,
        "too_long_to_read_words": TOO_LONG_TO_READ_WORDS,
        "not_implemented": list(NOT_IMPLEMENTED_ENGINES),
    })
    if args.json:
        print(json.dumps(status, indent=2))
        return 0
    print(DIVIDER)
    print("ASSISTANT VOICE STATUS")
    print(DIVIDER)
    for key in ("state", "stt_engine", "tts_engine", "allow_barge_in",
                "max_spoken_words", "too_long_to_read_words"):
        print("  {0:<32} {1}".format(key, status[key]))
    print(DIVIDER)
    for key in ("real_audio_input", "real_audio_output", "interprets_speech",
                "remembers_between_sessions", "has_reasoning"):
        print("  {0:<32} {1}".format(key, status[key]))
    print(DIVIDER)
    print("  NOT IMPLEMENTED:")
    for item in NOT_IMPLEMENTED_ENGINES:
        print("    - " + item)
    print()
    print("  " + TRANSPORT_NOTICE)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="assistant-voice",
        description=(
            "Assistant Voice - speech transport and driver-mode shaping. "
            "Workstream 6."
        ),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--silent", action="store_true", help="Use the silent output engine.")
    parser.add_argument("--no-barge-in", dest="no_barge_in", action="store_true")
    parser.add_argument("--confidence", type=float, default=1.0)
    sub = parser.add_subparsers(dest="command", required=True)

    p_say = sub.add_parser("say", help="Prepare and deliver a spoken turn.")
    p_say.add_argument("text")
    p_say.add_argument("--location", default=None, help="Where the written result is held.")
    p_say.set_defaults(func=cmd_say)

    p_brief = sub.add_parser("brief", help="Build a driver-mode brief from parts.")
    p_brief.add_argument("changed", help="What changed.")
    p_brief.add_argument("--matters", default=None, help="Why it matters.")
    p_brief.add_argument("--decision", default=None, help="Decision or action required.")
    p_brief.add_argument("--location", default=None)
    p_brief.set_defaults(func=cmd_brief)

    p_listen = sub.add_parser("listen", help="Pass text through the speech-to-text port.")
    p_listen.add_argument("text")
    p_listen.set_defaults(func=cmd_listen)

    p_clean = sub.add_parser("clean", help="Show what would be stripped before speaking.")
    p_clean.add_argument("text")
    p_clean.set_defaults(func=cmd_clean)

    sub.add_parser("demo", help="Short session showing queueing and barge-in.").set_defaults(
        func=cmd_demo
    )
    sub.add_parser("status", help="Engines, limits, and what is not implemented.").set_defaults(
        func=cmd_status
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SessionError, UtteranceError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
