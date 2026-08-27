"""MICROPHONE TEST AND DIAGNOSTICS.

Answers one question: can JOE hear Mike through the headset he already wears?

It runs in two parts.

    DIAGNOSTICS  - no speech needed. Lists every recording device Windows
                   knows, says which one JOE will actually record from, and
                   names anything blocking it. Safe to run any time.

    LIVE TEST    - needs Mike to speak. Confirms real audio reaches the
                   recognizer, and confirms JOE does NOT hear its own voice
                   while it is speaking.

The self-hearing test matters more than it looks. If JOE hears its own answer
it treats it as the next question and talks to itself indefinitely, hands-free
and unstoppable without reaching for the keyboard - the exact situation Driver
Mode exists to avoid.

Run:   launchers\\MIC_TEST.cmd
   or: py proof\\prove_microphone.py            (diagnostics + live test)
       py proof\\prove_microphone.py --list     (diagnostics only)

Writes evidence to proof\\MICROPHONE_PROOF.md. No raw audio is retained.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

DIVIDER = "=" * 74
TEST_PHRASE = "Joe can you hear me through the headset"
PASS_THRESHOLD = 0.5


def show_diagnostics(service) -> dict:
    diag = service.microphones.diagnostics()
    print(DIVIDER)
    print("MICROPHONE DIAGNOSTICS")
    print(DIVIDER)
    print()
    print("  JOE will record from   " + (diag["in_use"] or "(nothing connected)")
          + ("" if diag.get("default_resolved", True)
             else "   (a guess - Windows did not name a default)"))
    print("  device status          " + diag["in_use_status"])
    print("  your preference        " + (diag["preferred"] or "(none - Windows default)"))
    print("  preference honoured    " + str(diag["preference_honoured"]))
    print()
    print("  Recording devices Windows knows about:")
    for device in diag["devices"]:
        mark = "->" if device["name"] == diag["in_use"] else "  "
        flags = []
        if device["bluetooth"]:
            flags.append("bluetooth")
        if device["is_loopback"]:
            flags.append("LOOPBACK - never used")
        print("   %s %-34s %-26s %s" % (
            mark, device["name"][:34], device["status"], " ".join(flags)))
    print()
    if diag["bluetooth_present"]:
        print("  A Bluetooth headset is known to Windows.")
        print("  Connected right now:   " + str(diag["bluetooth_connected"]))
        if not diag["bluetooth_connected"]:
            print()
            print("  To use it: connect the headset, then make sure Windows")
            print("  Sound settings has it as the DEFAULT recording device.")
            print("  JOE records from the Windows default and cannot override it.")
    else:
        print("  No Bluetooth headset is known to Windows.")
    if diag["blocker"]:
        print()
        print("  BLOCKING: " + diag["blocker"])
    print()
    print("  " + diag["selection_note"])
    print()
    return diag


def live_test(service, diag) -> dict:
    """Speak, then confirm JOE cannot hear itself."""
    result = {
        "attempted": False, "heard": "", "overlap": 0.0, "recognized": False,
        "self_heard": None, "device": diag["in_use"], "error": "",
    }
    if not diag["in_use"]:
        print("BLOCKED: no recording device is connected. Nothing to test.")
        return result

    print(DIVIDER)
    print("LIVE MICROPHONE TEST")
    print(DIVIDER)
    print()
    print("  Recording from: " + diag["in_use"])
    print()
    print('  Say, clearly:   "' + TEST_PHRASE + '"')
    print()
    try:
        input("  Press Enter when ready, then speak...")
    except EOFError:
        print()
        print("BLOCKED: this needs a console, with you present to speak.")
        print(r"  Double-click  launchers\MIC_TEST.cmd")
        result["error"] = "no console; nobody present to speak"
        return result

    print("  listening...")
    result["attempted"] = True
    try:
        heard = service.listen(8) or {}
    except Exception as error:  # noqa: BLE001
        heard = {}
        result["error"] = str(error)

    text = str(heard.get("text") or "")
    result["heard"] = text
    result["recognized"] = bool(heard.get("recognized")) and bool(text)
    result["overlap"] = _overlap(TEST_PHRASE, text)

    print()
    print("  expected    " + TEST_PHRASE)
    print("  heard       " + (text or "(nothing recognized)"))
    print("  word match  " + str(round(result["overlap"] * 100)) + "%")
    if heard.get("error"):
        print("  error       " + str(heard["error"]))
    print()

    # ---- the self-hearing test ------------------------------------------
    print(DIVIDER)
    print("SELF-HEARING TEST  -  does JOE hear its own voice?")
    print(DIVIDER)
    print()
    print("  JOE will speak. Stay quiet. Nothing you hear should come back")
    print("  as a recognized request.")
    print()
    result["self_heard"] = _self_hearing_test(service)
    print("  JOE heard itself: " + str(result["self_heard"]))
    if result["self_heard"]:
        print()
        print("  FAIL. JOE would treat its own answer as the next question.")
    print()
    return result


def _self_hearing_test(service) -> bool:
    """Speak while the loop's suppression is engaged, then check nothing came back."""
    from app.driver_voice import DriverVoiceLoop

    captured = []

    def listen(seconds):
        # Only called when the loop believes it is safe to listen. If the
        # suppression works, this is never entered while speaking.
        result = service.listen(3) or {}
        text = str(result.get("text") or "")
        if text:
            captured.append(text)
        return text

    loop = DriverVoiceLoop(
        listen=listen,
        speak=lambda text: bool((service.speak(text) or {}).get("spoken")),
        ask=lambda text, short=False, save=False: ("", ""),
        listen_seconds=3, pause_seconds=0,
    )
    loop.start()
    time.sleep(0.2)
    loop.say(
        "This is Joe speaking a test sentence. If the microphone were open "
        "right now, these words would come back as your next question."
    )
    time.sleep(0.5)
    loop.stop()
    loop.join()
    # Anything captured that echoes JOE's own words is a self-hearing failure.
    return any("joe speaking" in c.lower() or "test sentence" in c.lower()
               for c in captured)


def _overlap(expected: str, heard: str) -> float:
    def words(text):
        keep = [c.lower() if (c.isalnum() or c.isspace()) else " " for c in text or ""]
        return "".join(keep).split()

    want, got = words(expected), list(words(heard))
    if not want:
        return 0.0
    matched = 0
    for word in want:
        if word in got:
            got.remove(word)
            matched += 1
    return matched / len(want)


def main() -> int:
    from app.config import Config
    from app.service import AssistantService

    list_only = "--list" in sys.argv
    print(DIVIDER)
    print("JOE - MICROPHONE TEST")
    print(DIVIDER)
    print()

    service = AssistantService(
        Config.load(PLUGIN_ROOT / "configuration" / "joe.config.json")
    )
    try:
        diag = show_diagnostics(service)
        if list_only:
            write_report(diag, None)
            print("Evidence written to  proof\\MICROPHONE_PROOF.md")
            return 0 if diag["in_use"] else 2

        result = live_test(service, diag)
        write_report(diag, result)

        print(DIVIDER)
        if not result["attempted"]:
            print("RESULT: NOT TESTED - " + (result["error"] or "no device"))
            verdict = 2
        elif result["recognized"] and result["overlap"] >= PASS_THRESHOLD \
                and not result["self_heard"]:
            print("RESULT: PASS - JOE heard you, and did not hear itself")
            verdict = 0
        else:
            print("RESULT: FAIL - see the detail above")
            verdict = 1
        print(DIVIDER)
        print()
        print("Evidence written to  proof\\MICROPHONE_PROOF.md")
        return verdict
    finally:
        service.shutdown()


def write_report(diag, result) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# JOE - Microphone Test and Diagnostics",
        "",
        "**Run:** " + stamp,
        "",
        "No raw audio is retained. Only recognized text and outcomes.",
        "",
        "## What JOE records from",
        "",
        "| | |",
        "| --- | --- |",
        "| Device in use | " + (diag["in_use"] or "**nothing connected**") + " |",
        "| Status | " + diag["in_use_status"] + " |",
        "| Preference | " + (diag["preferred"] or "(none - Windows default)") + " |",
        "| Preference honoured | " + str(diag["preference_honoured"]) + " |",
        "| Bluetooth headset known | " + str(diag["bluetooth_present"]) + " |",
        "| Bluetooth headset connected | " + str(diag["bluetooth_connected"]) + " |",
        "",
        "> " + diag["selection_note"],
        "",
        "## Recording devices Windows knows about",
        "",
        "| Device | Status | Notes |",
        "| --- | --- | --- |",
    ]
    for device in diag["devices"]:
        notes = []
        if device["name"] == diag["in_use"]:
            notes.append("**JOE records from this one**")
        if device["bluetooth"]:
            notes.append("bluetooth")
        if device["is_loopback"]:
            notes.append("loopback - never used, it would hear JOE's own output")
        lines.append("| " + device["name"] + " | " + device["status"]
                     + " | " + (", ".join(notes) or "-") + " |")
    lines.append("")
    if diag["blocker"]:
        lines += ["**Blocking:** " + diag["blocker"], ""]

    lines += ["## Live test", ""]
    if result is None:
        lines += ["Diagnostics only. No speech was attempted.", ""]
    elif not result["attempted"]:
        lines += ["**NOT TESTED.** " + (result["error"] or "no device connected"),
                  "", "The microphone is not proven and must not be reported as "
                  "working.", ""]
    else:
        passed = (result["recognized"] and result["overlap"] >= PASS_THRESHOLD
                  and not result["self_heard"])
        lines += [
            "**" + ("PASS - JOE heard Mike, and did not hear itself."
                    if passed else "FAIL.") + "**",
            "",
            "| | |",
            "| --- | --- |",
            "| Device | " + (result["device"] or "-") + " |",
            "| Expected phrase | " + TEST_PHRASE + " |",
            "| Recognized text | " + (result["heard"] or "*(nothing recognized)*") + " |",
            "| Word match | " + str(round(result["overlap"] * 100)) + "% |",
            "| JOE heard itself | " + str(result["self_heard"]) + " |",
            "",
        ]
        if result["error"]:
            lines += ["Technical error: `" + result["error"] + "`", ""]
        if result["self_heard"]:
            lines += [
                "**Self-hearing failure.** JOE would treat its own answer as the "
                "next question and talk to itself. Driver Mode is not safe to "
                "use until this passes.", "",
            ]
    (PLUGIN_ROOT / "proof" / "MICROPHONE_PROOF.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
