"""VOICE INPUT PROOF - requires Mike physically at the microphone.

This cannot be passed by a program talking to itself. A microphone being
detected, an engine loading, the OS granting permission, a fixture supplying
text, or a mocked phrase are NONE of them proof. The only thing that proves
voice input is Mike speaking and the recognizer returning what he said.

The full required flow, per phrase:

    Mike presses Listen  ->  Mike speaks  ->  JOE receives real microphone
    audio  ->  speech becomes text  ->  the recognized text is shown  ->  it
    goes through the NORMAL reasoning path  ->  a written answer appears  ->
    JOE speaks the short answer aloud  ->  the written interaction stays in
    history.

Raw audio is never retained. Only recognized text, timings, and outcomes.

Run:   launchers\\PROVE_VOICE_INPUT.cmd
   or: py proof\\prove_voice_input.py

Writes evidence to proof\\VOICE_INPUT_PROOF.md. Records failure as failure.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74

# Fixed by mission, so recognized text is compared against something rather
# than judged by eye. Each exercises a different path on purpose:
#   1 - Outlook calendar retrieval
#   2 - reasoning and explanation
#   3 - a retention command, which must act on the PREVIOUS interaction
PHRASES = (
    "What is on my calendar tomorrow?",
    "Joe, explain what matters about today.",
    "Save this.",
)

RETENTION_PHRASE_INDEX = 2   # zero-based: "Save this."
PASS_THRESHOLD = 0.6
LISTEN_SECONDS = 8


def normalise(text: str) -> str:
    keep = [c.lower() for c in text if c.isalnum() or c.isspace()]
    return " ".join("".join(keep).split())


def word_overlap(expected: str, heard: str) -> float:
    """Fraction of the expected words present in what was heard.

    Each heard word is consumed once, so repeating a word cannot satisfy two
    different expected words. Padding is forgiven - recognizers pad - but
    absence is not."""
    want = normalise(expected).split()
    got = normalise(heard).split()
    if not want:
        return 0.0
    matched = 0
    remaining = list(got)
    for word in want:
        if word in remaining:
            remaining.remove(word)
            matched += 1
    return matched / len(want)


def microphone_status(probe: dict) -> str:
    if not probe.get("stt_engine_available"):
        return "UNAVAILABLE - " + (probe.get("blocker") or "no recognition engine")
    recognizers = probe.get("recognizers") or []
    if not recognizers:
        return "ENGINE PRESENT, NO RECOGNIZER"
    return "READY - " + ", ".join(recognizers)


def main() -> int:
    from app.config import Config
    from app.service import AssistantService

    print(DIVIDER)
    print("JOE - VOICE INPUT PROOF")
    print(DIVIDER)
    print()
    print("This needs you to speak. Nothing here can pass without your voice.")
    print("Raw audio is not kept - only what was recognized.")
    print()

    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json")
    )
    try:
        probe = service.voice.probe()
        mic = microphone_status(probe)
        print("  microphone status      " + mic)
        print("  text-to-speech         " + str(probe.get("tts_available")))
        print()

        if not probe.get("stt_engine_available"):
            print("BLOCKED: no speech recognition engine on this machine.")
            write_report([], blocked=probe.get("blocker") or "no recognition engine",
                         mic=mic)
            return 2

        attempts = []
        for number, phrase in enumerate(PHRASES):
            attempt = run_one_phrase(service, number, phrase, mic)
            if attempt is None:          # no console; refuse to record anything
                write_report([], blocked="run without a console; nobody was "
                                         "present to speak", mic=mic)
                return 2
            attempts.append(attempt)

        passed = sum(1 for a in attempts if a["ok"])
        print(DIVIDER)
        print("RESULT: " + str(passed) + " of " + str(len(attempts))
              + " phrases recognized and processed end to end")
        print(DIVIDER)
        if passed < len(attempts):
            print()
            print("Voice input is NOT proven. Do not report it as working.")
        write_report(attempts, blocked="", mic=mic)
        print()
        print("Evidence written to  proof\\VOICE_INPUT_PROOF.md")
        return 0 if passed == len(attempts) else 1
    finally:
        service.shutdown()


def run_one_phrase(service, number: int, phrase: str, mic: str):
    """One phrase, through the whole flow. None means no console."""
    from app.config import Config  # noqa: F401  (kept for symmetry)

    print(DIVIDER)
    print("PHRASE " + str(number + 1) + " of " + str(len(PHRASES)))
    print(DIVIDER)
    print()
    print('  Say, clearly:   "' + phrase + '"')
    print()

    while True:
        try:
            reply = input("  Press Enter to start listening (or 's' to skip): ")
        except EOFError:
            print()
            print("BLOCKED: this must be run from a console, with you present.")
            print(r"  Double-click  launchers\PROVE_VOICE_INPUT.cmd")
            return None

        if reply.strip().lower() == "s":
            return {
                "phrase": phrase, "recognized": "", "overlap": 0.0, "ok": False,
                "error": "skipped by the operator", "mic": mic,
                "received_at": "", "processed": False, "written": "",
                "spoken": False, "retained": "", "capability": "",
            }

        print("  listening...")
        started = time.time()
        try:
            heard = service.voice.listen(seconds=LISTEN_SECONDS)
        except Exception as error:  # noqa: BLE001
            heard = {"recognized": False, "text": "", "error": str(error)}
        received_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        elapsed = time.time() - started

        recognized = str(heard.get("text") or "")
        overlap = word_overlap(phrase, recognized)
        heard_ok = bool(heard.get("recognized")) and overlap >= PASS_THRESHOLD

        print()
        print("  time received      " + received_at + "   (" + str(round(elapsed, 1)) + "s)")
        print("  expected           " + phrase)
        print("  recognized         " + (recognized or "(nothing recognized)"))
        print("  word match         " + str(round(overlap * 100)) + "%")
        if heard.get("error"):
            print("  error              " + str(heard["error"]))

        if heard_ok:
            break

        print()
        print("  NOT RECOGNIZED WELL ENOUGH. Nothing was invented to fill the gap.")
        try:
            again = input("  Retry this phrase? (y/n): ")
        except EOFError:
            again = "n"
        if again.strip().lower() != "y":
            return {
                "phrase": phrase, "recognized": recognized, "overlap": overlap,
                "ok": False, "error": str(heard.get("error") or ""), "mic": mic,
                "received_at": received_at, "processed": False, "written": "",
                "spoken": False, "retained": "", "capability": "",
            }
        print()

    # ---- the recognized text goes through the NORMAL path, not a side door --
    print()
    print("  sending the recognized text through the normal reasoning path...")
    result = service.ask(recognized)
    response = result.response
    written = (response.answer or response.written or "").strip()
    spoken_text = (response.spoken_summary or response.answer or "").strip()

    print("  capability         " + str(response.capability))
    print("  written answer     " + (written.splitlines()[0][:70] if written else "(none)"))

    # ---- spoken aloud ------------------------------------------------------
    spoken_ok = False
    if spoken_text:
        try:
            attempt = service.voice.speak(spoken_text[:400])
            spoken_ok = bool(getattr(attempt, "spoken", False))
        except Exception as error:  # noqa: BLE001
            print("  speech error       " + str(error))
    print("  spoken aloud       " + str(spoken_ok))

    # ---- retention ---------------------------------------------------------
    retained = ""
    try:
        record = service.memory.store.load(result.record_id)
        retained = str(record.interaction_level) + " / " + str(record.state)
    except Exception:  # noqa: BLE001
        retained = "(no record)"
    print("  retained as        " + retained)
    print()

    return {
        "phrase": phrase,
        "recognized": recognized,
        "overlap": overlap,
        "ok": bool(written) and spoken_ok,
        "error": str(heard.get("error") or ""),
        "mic": mic,
        "received_at": received_at,
        "processed": True,
        "written": written,
        "spoken": spoken_ok,
        "retained": retained,
        "capability": str(response.capability),
    }


def write_report(attempts: list, blocked: str, mic: str = "") -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# JOE - Voice Input Proof",
        "",
        "**Run:** " + stamp,
        "**Microphone status:** " + (mic or "(not reached)"),
        "**Requires:** Mike physically at the microphone. This cannot be automated.",
        "",
        "Raw audio is not retained. Only recognized text, timings, and outcomes.",
        "",
    ]
    if blocked:
        lines += [
            "## Result", "", "**BLOCKED.** " + blocked, "",
            "Voice input is NOT proven and must not be reported as working, "
            "connected, or complete.", "",
        ]
    elif not attempts:
        lines += ["## Result", "", "**NOT RUN.** No phrase was attempted.", ""]
    else:
        passed = sum(1 for a in attempts if a["ok"])
        lines += [
            "## Result",
            "",
            "**" + str(passed) + " of " + str(len(attempts))
            + " phrases recognized and processed end to end.**",
            "",
        ]
        if passed < len(attempts):
            lines += [
                "**Voice input is NOT proven.** It must not be described as "
                "working, connected, or complete.", "",
            ]
        for number, a in enumerate(attempts, start=1):
            lines += [
                "### Phrase " + str(number),
                "",
                "| | |",
                "| --- | --- |",
                "| Exact phrase expected | " + a["phrase"] + " |",
                "| Exact recognized text | "
                + (a["recognized"] or "*(nothing recognized)*") + " |",
                "| Word match | " + str(round(a["overlap"] * 100)) + "% |",
                "| Microphone status | " + (a.get("mic") or "") + " |",
                "| Time received | " + (a.get("received_at") or "-") + " |",
                "| Entered normal processing | " + str(a.get("processed")) + " |",
                "| Capability reached | " + (a.get("capability") or "-") + " |",
                "| Written response | "
                + ("produced" if a.get("written") else "**none**") + " |",
                "| Spoken response | "
                + ("spoken aloud" if a.get("spoken") else "**not spoken**") + " |",
                "| Retained as | " + (a.get("retained") or "-") + " |",
                "| Result | " + ("**PASS**" if a["ok"] else "**FAIL**") + " |",
                "",
            ]
            if a.get("error"):
                lines += ["Technical error: `" + a["error"] + "`", ""]
            if a.get("written"):
                lines += ["Written answer:", "", "```", a["written"][:1500], "```", ""]
        if passed == len(attempts):
            lines += [
                "Voice input is proven for these phrases, spoken by Mike, on this "
                "machine, with this microphone. It is not proven for road noise, "
                "another speaker, or another device.", "",
            ]
    (PLUGIN_ROOT / "proof" / "VOICE_INPUT_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
