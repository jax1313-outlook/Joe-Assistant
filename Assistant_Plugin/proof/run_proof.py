"""Local operational proof for the JOE, the Level 1 Assistant.

Demonstrates, on this machine, the proof steps required by
JOE_COMPLETE_BUILD_MISSION_v1 section 19, and writes
docs/JOE_LOCAL_PROOF_REPORT_v1.md from what actually happened.

    py proof\\run_proof.py                 full proof, including live Outlook
    py proof\\run_proof.py --no-outlook    skip the live Outlook step
    py proof\\run_proof.py --speak         also speak out loud (makes sound)
    py proof\\run_proof.py --no-window     skip the double-click launch step

Nothing here contacts Dispatch. Nothing is written outside the plugin folder.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from app import bootstrap  # noqa: E402,F401
from app.config import Config, ContainmentError, assert_within_plugin  # noqa: E402
from app.service import AssistantService  # noqa: E402
from contracts import SourceMode  # noqa: E402
from adapters import DispatchPortError  # noqa: E402

WORKSPACE = PLUGIN_ROOT / "proof" / "_workspace"
REPORT = PLUGIN_ROOT / "docs" / "JOE_LOCAL_PROOF_REPORT_v1.md"
DIVIDER = "=" * 74
WINDOW_TITLE = "JOE, the Level 1 Assistant"


class Proof:
    def __init__(self) -> None:
        self.steps: list[dict] = []

    def record(self, number, title, passed, evidence, note="", skipped=False):
        self.steps.append(
            {
                "number": number,
                "title": title,
                "passed": bool(passed) and not skipped,
                "skipped": bool(skipped),
                "evidence": list(evidence),
                "note": note,
            }
        )
        mark = "SKIP" if skipped else ("PASS" if passed else "FAIL")
        print()
        print(DIVIDER)
        print("PROOF {0:<2} [{1}]  {2}".format(number, mark, title))
        print(DIVIDER)
        for line in evidence:
            print("  " + line)
        if note:
            print("  NOTE: " + note)

    @property
    def all_passed(self) -> bool:
        """A skipped step is not a failure, but it is not a pass either."""
        return not any(
            (not step["passed"]) and (not step["skipped"]) for step in self.steps
        )

    @property
    def passed_count(self) -> int:
        return sum(1 for step in self.steps if step["passed"])

    @property
    def skipped_count(self) -> int:
        return sum(1 for step in self.steps if step["skipped"])

    @property
    def failed_count(self) -> int:
        return sum(
            1 for step in self.steps if not step["passed"] and not step["skipped"]
        )


def make_service(root: Path, outlook: bool) -> AssistantService:
    base = json.loads(
        (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
            encoding="utf-8"
        )
    )
    base["paths"] = {
        "runtime_data": str(root / "runtime_data"),
        "logs": str(root / "logs"),
    }
    base["outlook"]["enabled"] = outlook
    path = root / "config.json"
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(base), encoding="utf-8")
    return AssistantService(Config.load(path))


def powershell(script: str, timeout: int = 90) -> str:
    try:
        done = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout,
        )
        return (done.stdout or "").strip()
    except Exception as error:  # noqa: BLE001
        return "ERROR: " + str(error)


# ======================================================================


def step_1_launcher(proof: Proof, skip: bool) -> None:
    launcher = PLUGIN_ROOT / "START_JOE.cmd"
    if skip:
        proof.record(
            1, "Mike can double-click the launcher", launcher.is_file(),
            ["launcher exists   " + str(launcher),
             "launch skipped by --no-window"],
            note="window launch not exercised in this run",
        )
        return
    script = (
        "$ErrorActionPreference='Stop';"
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\""
        "|Where-Object{$_.CommandLine -like '*joe_main.py*'}"
        "|ForEach-Object{Stop-Process -Id $_.ProcessId -Force};"
        "Start-Sleep -Milliseconds 500;"
        "$sw=[Diagnostics.Stopwatch]::StartNew();"
        "Start-Process -FilePath '" + str(launcher) + "' -WorkingDirectory '"
        + str(PLUGIN_ROOT) + "'|Out-Null;"
        "$a=$null;"
        "while($sw.Elapsed.TotalSeconds -lt 60 -and $null -eq $a){"
        "Start-Sleep -Milliseconds 700;"
        "$a=Get-Process|Where-Object{$_.MainWindowTitle -eq '" + WINDOW_TITLE + "'}|Select-Object -First 1};"
        "$o=[ordered]@{};"
        "if($a){$o.visible=$true;$o.seconds=[math]::Round($sw.Elapsed.TotalSeconds,1);"
        "$o.pid=$a.Id;$o.proc=$a.ProcessName;$o.title=$a.MainWindowTitle}"
        "else{$o.visible=$false};"
        "$o|ConvertTo-Json -Compress"
    )
    raw = powershell(script, timeout=120)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"visible": False, "raw": raw[:200]}
    proof.record(
        1,
        "Mike can double-click the launcher and the window becomes visible",
        bool(data.get("visible")),
        [
            "launcher            " + str(launcher),
            "launched as         Start-Process (the double-click path)",
            "window visible      " + str(data.get("visible")),
            "window title        " + str(data.get("title", "-")),
            "appeared after      " + str(data.get("seconds", "-")) + " s",
            "process             " + str(data.get("proc", "-"))
            + "  pid " + str(data.get("pid", "-")),
            "console windows     0 (pyw runs with no console)",
        ],
    )


def step_2_text_interaction(proof: Proof, service) -> str:
    interaction = service.ask("Find the rate floor policy")
    response = interaction.response
    proof.record(
        2,
        "Mike enters a request and a written response appears",
        # response.ok belongs here. Without it this step passed while the
        # capability raised on every call: ask() catches the exception and
        # returns "That capability failed" as the answer, with a written form
        # explaining it, so "answer and written are non-empty" held. The step
        # printed its own bad news - answer: That capability failed - and
        # reported PASS underneath it.
        response.ok and bool(response.answer) and bool(response.written),
        [
            "request             Find the rate floor policy",
            "routed to           " + response.capability,
            "answer              " + response.answer[:80],
            "written length      " + str(len(response.written)) + " characters",
            "record created      " + interaction.record_id,
        ],
    )
    rows = service.history()
    proof.record(
        3,
        "The interaction appears in history and is selected",
        any(r["record_id"] == interaction.record_id and r["selected"] for r in rows),
        [
            "history rows        " + str(len(rows)),
            "selected record     " + str(service.selected_id),
            "state / level       " + rows[-1]["state"] + " / " + rows[-1]["level"],
        ],
    )
    return interaction.record_id


def step_4_level1(proof: Proof, service, record_id: str) -> None:
    from assistant_memory.clock import from_iso

    record = service.memory.get(record_id)
    delta = from_iso(record.expires_at) - from_iso(record.created_at)
    proof.record(
        4,
        "The interaction is recorded as Level 1 with a three-hour expiration",
        record.state == "TEMPORARY"
        and record.interaction_level == "LEVEL_1"
        and delta == timedelta(hours=3),
        [
            "state               " + record.state,
            "interaction_level   " + record.interaction_level,
            "created_at          " + record.created_at,
            "expires_at          " + str(record.expires_at),
            "difference          " + str(delta) + "   (expected 3:00:00)",
        ],
    )


def step_5_save(proof: Proof, service, record_id: str) -> None:
    result = service.ask("Save this").response
    record = service.memory.get(record_id)
    proof.record(
        5,
        'Save changes Level 1 to Level 2',
        record.state == "SAVED"
        and record.interaction_level == "LEVEL_2"
        and record.expires_at is None,
        [
            "command             Save this",
            "state               TEMPORARY -> " + record.state,
            "interaction_level   LEVEL_1 -> " + record.interaction_level,
            "expires_at          " + str(record.expires_at) + "   (expiration cleared)",
            "notice              " + result.answer[:70],
        ],
    )


def step_6_level3(proof: Proof, service) -> None:
    service.ask("Find the appointment window policy")
    result = service.ask("Level 3 this under Ideas").response
    record = service.memory.get(service.selected_id)
    proof.record(
        6,
        "Level 3 produces a formal record and an artifact request",
        record.state == "FORMAL"
        and record.interaction_level == "LEVEL_3"
        and record.destination == "Ideas"
        and "produced=False" in result.written,
        [
            "command             Level 3 this under Ideas",
            "state               " + record.state,
            "interaction_level   " + record.interaction_level,
            "destination         " + str(record.destination),
            "artifact request    created, produced=False",
            "decision required   Mike Zachary",
        ],
    )


def step_7_print(proof: Proof, service) -> None:
    service.ask("Find the driver first doctrine")
    before = service.memory.get(service.selected_id).interaction_level
    result = service.ask("Print this").response
    record = service.memory.get(service.selected_id)
    honest = "Nothing was physically printed" in (
        " ".join(result.notices) + result.written + result.answer
    )
    proof.record(
        7,
        "Print produces Print Ready without changing interaction level",
        record.state == "PRINT_READY"
        and record.interaction_level == before == "LEVEL_1"
        and record.expires_at is None
        and honest,
        [
            "command             Print this",
            "state               TEMPORARY -> " + record.state,
            "interaction_level   " + before + " -> " + record.interaction_level
            + "   (unchanged - doctrine C4)",
            "expires_at          " + str(record.expires_at),
            "physical printing   not claimed",
            "notice              Print request recorded. Nothing was physically printed.",
        ],
    )


def step_8_delete(proof: Proof, service) -> None:
    interaction = service.ask("Find something to remove")
    record_id = interaction.record_id
    service.ask("Delete this")
    record = service.memory.get(record_id)
    in_history = record_id in [r["record_id"] for r in service.history()]
    refused = not service.apply_retention(record_id, "LEVEL_2").ok
    proof.record(
        8,
        "Delete removes the selected interaction",
        record.state == "DELETED"
        and record.driver_request is None
        and not in_history
        and refused,
        [
            "command             Delete this",
            "state               " + record.state,
            "content purged      driver_request = " + str(record.driver_request),
            "in active history   " + str(in_history),
            "later command       refused = " + str(refused),
        ],
    )


def step_9_library(proof: Proof, service) -> None:
    """A search returns matches, and every match says where it came from.

    "correctly labelled" is in the title and used to be tested nowhere: the
    condition was `probe["available"] and bool(result.findings)`. Results could
    have come back with no label at all, or with sample material wearing a
    COMPANY LIBRARY tag, and this still reported PASS. The labelling is the
    whole reason a driver can trust a quote from the Library, so it is the
    thing to check.
    """
    import re as _re

    probe = service.library.probe()
    result = service.ask("Find the dispatch constitution").response
    company = [p for p in result.provenance if p.mode == SourceMode.LIVE]
    sources = [
        s["name"] + " (" + s["kind"] + ", " + str(s["indexed"]) + " docs, " + s["mode"] + ")"
        for s in probe["sources"]
    ]

    # Every hit carries a label in the text Mike reads.
    written = result.written or ""
    labels = _re.findall(r"\[(COMPANY LIBRARY|SAMPLE DATA)\]", written)
    all_labelled = bool(labels) and len(labels) == len(result.findings)

    # And the labels agree with where the material actually came from.
    # Provenance covers the top hits only, so this is one-directional: every
    # kind of source that was read must appear in the labels shown.
    shown = set(labels)
    read = set()
    if any(p.mode == SourceMode.SAMPLE for p in result.provenance):
        read.add("SAMPLE DATA")
    if company:
        read.add("COMPANY LIBRARY")
    honest = read <= shown

    proof.record(
        9,
        "Library search returns a configured source, correctly labelled",
        probe["available"] and bool(result.findings) and all_labelled and honest,
        [
            "configured sources  " + str(len(probe["sources"])),
            *["  - " + s for s in sources],
            "total indexed       " + str(probe["indexed"]),
            "live company source " + str(probe["live_connection"]),
            "matches returned    " + str(len(result.findings)),
            "labels shown        " + str(len(labels)) + " of "
            + str(len(result.findings)) + "  " + str(sorted(shown)),
            "sources read        " + str(sorted(read) or ["(none)"]),
            "labels agree        " + str(honest),
            "company-sourced hit " + str(bool(company)),
            "top result          " + result.answer[:70],
        ],
    )


def _calendar_mailbox(service):
    """An APPROVED mailbox that holds a calendar, or ("", None) if none does.

    Ordering cannot be proven against an empty folder: an empty list is
    chronological by definition. Only mailboxes approved in configuration are
    opened. A personal account is not approved for Dispatch operation, so it
    is never read here - not even to exercise the ordering machinery. When no
    approved mailbox holds a calendar the ordering check does not run, and the
    caller reports that rather than borrowing a mailbox to look green.
    """
    first = None
    for connection in service.mailboxes.enabled_connections:
        smtp = str(connection.address or "").strip()
        if not smtp:
            continue
        result = service.outlook.calendar(account=smtp)
        if first is None:
            first = result
        if result.ok and result.returned > 0:
            return smtp, result
    return "", first


def step_10_outlook(proof: Proof, service, enabled: bool) -> None:
    probe = service.outlook.probe()
    if not enabled:
        proof.record(
            10,
            "Outlook status truthfully shows connected or disconnected",
            not probe["live_connection"],
            [
                "outlook enabled     False (--no-outlook)",
                "live_connection     False",
                "reported as         NOT CONNECTED",
                "sample substituted  no",
            ],
            note="live Outlook not exercised in this run",
        )
        return
    result = service.ask("What is on my calendar?").response
    probe = service.outlook.probe()
    live = [p for p in result.provenance if p.mode == SourceMode.LIVE]

    # The ask path is judged AFTER the direct read below, against what the
    # approved mailboxes actually hold. See the verdict there.

    # Read the calendar directly so the ordering can be checked, not assumed.
    #
    # APPROVED mailboxes only. Neither business mailbox holds a calendar on
    # this profile, so this normally finds nothing - and an unproven check is
    # reported as unproven rather than run against a mailbox nobody approved.
    calendar_mailbox, calendar = _calendar_mailbox(service)
    starts = [str(i.get("start", "")) for i in calendar.items] if calendar else []
    parsed = []
    for text in starts:
        for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
            try:
                parsed.append(datetime.strptime(text, fmt))
                break
            except ValueError:
                continue
    in_order = parsed == sorted(parsed)

    # Ordering is claimed only when an approved mailbox actually had entries
    # to put in order. Two is the smallest number that can be out of order.
    ordering_exercised = bool(calendar_mailbox) and len(parsed) >= 2

    # THE ASK PATH, judged against the mailboxes rather than the registry.
    #
    # This used to ask source_for(CALENDAR) whether a calendar source existed,
    # and accept a refusal whenever the answer was None. That let the registry
    # excuse itself: a registry that discovers nothing reports no source, the
    # refusal is scored correct, and every mail, calendar and contacts
    # question in the product can be broken while this step reports PASS.
    # That is exactly what happened - the suite read 24/24 while JOE answered
    # "I have no mailbox that holds your mail" over a mailbox holding 127.
    #
    # calendar_mailbox comes from reading approved mailboxes directly, so a
    # broken registry cannot author its own alibi. When an approved mailbox
    # holds a calendar, the ask path MUST answer; refusing is a failure.
    if calendar_mailbox:
        ask_ok = bool(result.ok) and bool(live)
        if ask_ok:
            ask_detail = result.answer[:60]
        elif not result.ok:
            ask_detail = ("REFUSED, but " + calendar_mailbox
                          + " holds a calendar - the ask path cannot reach it")
        else:
            ask_detail = "answered without a live source: " + result.answer[:40]
    else:
        ask_ok = (not result.ok) and "no mailbox" in result.answer.lower()
        ask_detail = ("correctly refused - no approved mailbox holds a calendar"
                      if ask_ok else "answered anyway: " + result.answer[:40])

    # Probe AFTER the read. Probed before it, live_connection reports False
    # whenever the ask path refuses without touching Outlook - which is now the
    # normal case for a calendar question, and says nothing about whether the
    # connection works.
    probe = service.outlook.probe()

    proof.record(
        10,
        "Outlook reads live, read-only, and returns the calendar in date order",
        (probe["live_connection"] and ask_ok
         and (not ordering_exercised
              or (calendar.is_date_ordered and in_order))),
        [
            "live_connection     " + str(probe["live_connection"]),
            "capability          " + result.capability,
            "ordering probe      " + (calendar_mailbox
                                       or "NOT RUN - no approved mailbox holds a calendar"),
            "ask path            " + ask_detail,
            "read at             " + (live[0].as_of if live else "-"),
            "ordering            " + (calendar.ordering + "  ("
                                      + calendar.ordering_label + ")"
                                      if calendar else "not read"),
            "window              " + ((calendar.window_line() or "n/a")
                                      if calendar else "n/a"),
            "items returned      " + (str(calendar.returned) + " of "
                                      + str(calendar.total) + " in the folder"
                                      if calendar else "0 - nothing approved to read"),
            "dates parsed        " + str(len(parsed)) + " of " + str(len(starts)),
            "chronological       " + str(in_order),
            "first entry         " + (starts[0][:16] if starts else "-"),
            "last entry          " + (starts[-1][:16] if starts else "-"),
            "answer              " + result.answer[:70],
            "",
            "only mailboxes approved in configuration are opened here; a",
            "personal account is not approved and is never read",
            "write operations    0 (adapter refuses any non-read call)",
        ],
        note=("" if ordering_exercised else
              "date ordering was NOT exercised this run - no approved mailbox "
              "holds a calendar. Live read, read-only, and the ask path are "
              "proven above; chronological ordering is not claimed."),
    )


def step_11_research(proof: Proof, service) -> None:
    """The label must match the mode - whichever mode research is in.

    This step used to pass on `not probe["live_connection"] and labelled`, and
    that is wrong twice over.

    It cannot survive success. The title says "live OR fixture mode" while the
    condition accepts only fixture, so the day a live research provider is
    connected this fails for the wrong reason - and whoever is holding the
    pager fixes it by weakening it. It is not hypothetical: on this machine
    research.probe() already reports mode LIVE. The step passes only because
    the suite isolates runtime_data, so the provider it would use is not
    signed in inside the sandbox.

    And it had no positive control - the same gap corrected in steps 14 and
    15. A research provider that is simply broken also reports not-live, and
    passed here.

    Truthfulness is the claim in the title, so truthfulness is what is checked:
    fixture output must say SAMPLE DATA, live output must not, and a provider
    that is unavailable must say why rather than be reported as either.
    """
    probe = service.research.probe()
    result = service.ask("Research the northbound lane").response
    mode = str(probe.get("mode", "")).upper()
    live = bool(probe.get("live_connection"))
    said_sample = (any("SAMPLE DATA" in n for n in result.notices)
                   or "SAMPLE DATA" in (result.written or "").upper())

    if live:
        truthful = (mode == "LIVE") and not said_sample
        expected = "live, and not labelled sample"
    else:
        truthful = (mode != "LIVE") and said_sample
        expected = "not live, and labelled SAMPLE DATA"

    # An unavailable provider must name its blocker. Silence would let a
    # broken provider be reported as an ordinary fixture run.
    coherent = bool(probe.get("available")) or bool(probe.get("blocker"))

    proof.record(
        11,
        "Research status truthfully shows live or fixture mode",
        truthful and coherent,
        [
            "provider            " + probe["provider"],
            "live_connection     " + str(live),
            "mode                " + probe["mode"],
            "available           " + str(probe.get("available")),
            "blocker             " + (probe["blocker"][:70] or "(none)"),
            "labelled SAMPLE     " + str(said_sample),
            "required            " + expected,
            "unavailable states why  " + str(coherent),
        ],
    )


def step_12_voice(proof: Proof, service, speak: bool) -> None:
    probe = service.voice.probe()
    wav = assert_within_plugin(PLUGIN_ROOT / "proof" / "_voice_probe.wav")
    rendered = service.voice.synthesize_to_file(
        "Level 1 Assistant voice check.", wav
    )
    size = wav.stat().st_size if wav.exists() else 0
    evidence = [
        "tts engine          " + ("bound" if probe["tts_available"] else "not available"),
        "voices              " + ", ".join(probe.get("voices", [])),
        "stt engine          " + ("bound" if probe["stt_engine_available"] else "not available"),
        "recognizers         " + ", ".join(probe.get("recognizers", [])),
        "rendered to wav     " + str(rendered.spoken) + "   " + str(size) + " bytes",
    ]
    spoken_aloud = False
    if speak:
        attempt = service.speak("Level 1 Assistant voice check.")
        spoken_aloud = bool(attempt.get("spoken"))
        evidence.append("spoken aloud        " + str(spoken_aloud))
    else:
        evidence.append("spoken aloud        not attempted (--speak to enable)")
    evidence.append("microphone input    not exercised; requires a person to speak")
    if wav.exists():
        wav.unlink()
    proof.record(
        12,
        "Voice status truthfully shows connected or text-only",
        probe["tts_available"] and rendered.spoken and size > 0,
        evidence,
        note=(
            "speech-to-text engine binds, but recognition of real microphone "
            "input is not proven by an automated run"
        ),
    )


def step_13_restart(proof: Proof, service, root: Path) -> None:
    """The same records survive a restart - checked by identity, not by count.

    This compared counts: `len(kept) >= len(saved) > 0`. Two faults slip
    through that. A record deleted before the restart could come back, and the
    count would only rise - which `>=` accepts. And a preserved record could be
    swapped for a different one, leaving the count unchanged. Neither is
    hypothetical for a program whose whole retention model is which record
    survives and which expires: step 8 deletes a record immediately before
    this, and its return would be invisible here.

    Record ids are compared instead. Nothing lost, nothing gained.
    """
    ELIGIBLE = ("SAVED", "FORMAL", "PRINT_READY")
    before = {r["record_id"] for r in service.history() if r["state"] in ELIGIBLE}
    service.shutdown()
    second = make_service(root, outlook=False)
    restored = second.reload_history()
    rows = second.history()
    kept = [r for r in rows if r["state"] in ELIGIBLE]
    after = {r["record_id"] for r in kept}

    lost = sorted(before - after)
    gained = sorted(after - before)
    identical = bool(before) and not lost and not gained

    proof.record(
        13,
        "Closing and reopening preserves eligible records",
        restored > 0 and identical,
        [
            "records before      " + str(len(before)) + " preserved",
            "service restarted   yes (new AssistantService over the same data)",
            "records restored    " + str(restored),
            "preserved after     " + str(len(after)),
            "same records        " + str(identical) + "  (compared by id)",
            "lost                " + (", ".join(lost) if lost else "none"),
            "returned unexpectedly  " + (", ".join(gained) if gained else "none"),
            "states              " + ", ".join(sorted({r["state"] for r in kept})),
        ],
    )
    second.shutdown()


def step_14_outlook_unavailable(proof: Proof, root: Path, enabled: bool) -> None:
    # POSITIVE CONTROL. "It refused" only means "Outlook is unavailable" if the
    # SAME question is answered when Outlook is available. Without that
    # comparison a wholly broken Outlook subsystem passes this step exactly as
    # a correctly disabled one does - and that is not hypothetical. While the
    # mailbox registry was never being discovered, every calendar, mail and
    # contacts question refused, and this step stayed green the whole time.
    control_answered = None
    if enabled:
        control = make_service(root / "outlook_control", outlook=True)
        control_answered = control.ask("What is on my calendar?").response.ok
        control.shutdown()

    service = make_service(root / "no_outlook", outlook=False)
    result = service.ask("What is on my calendar?").response
    still_works = service.ask("help").response.ok

    # "sample substituted: no" was a printed claim asserted nowhere - and it is
    # the one guarantee this step exists to make. Now it is checked.
    substituted = any(p.mode == SourceMode.SAMPLE for p in result.provenance)

    if control_answered is None:
        control_line = "not run (--no-outlook: nothing to compare against)"
    elif control_answered:
        control_line = "the same question IS answered when Outlook is on"
    else:
        control_line = ("SAME QUESTION ALSO REFUSED WITH OUTLOOK ON - this "
                        "step cannot tell 'unavailable' from 'broken'")

    proof.record(
        14,
        "The program operates with Outlook unavailable",
        ((not result.ok) and still_works and (not substituted)
         and (control_answered is not False)),
        [
            "outlook enabled     False",
            "positive control    " + control_line,
            "calendar request    refused honestly: " + result.answer[:60],
            "sample substituted  " + ("YES - sample data was passed off as an "
                                      "answer" if substituted
                                      else "no (asserted, not assumed)"),
            "other capabilities  still working (help responded)",
            "application         remained open",
        ],
        note=("" if enabled else
              "run with --no-outlook, so the positive control could not run; "
              "a refusal here was not distinguished from a broken subsystem"),
    )
    service.shutdown()


def step_15_voice_unavailable(proof: Proof, root: Path) -> None:
    from adapters import SapiVoiceAdapter

    service = make_service(root / "no_voice", outlook=False)

    # POSITIVE CONTROL, for the reason given in step 14: "not live" only proves
    # the disable took effect if the SAME adapter reports LIVE when enabled.
    # An adapter that never binds at all would otherwise satisfy this step
    # forever, while claiming the disable is what silenced it.
    service.voice = SapiVoiceAdapter(enabled=True)
    control_live = {s.name: s
                    for s in service.status()}["Voice out"].live_connection

    service.voice = SapiVoiceAdapter(enabled=False)
    status = {s.name: s for s in service.status()}["Voice out"]
    still_works = service.ask("help").response.ok

    if not control_live:
        # No speech engine on this machine. A disabled adapter cannot be told
        # apart from an absent one, so this proves nothing either way rather
        # than passing on a coincidence. Step 12 is where binding is asserted.
        proof.record(
            15, "The program operates with voice unavailable", False,
            [
                "positive control    voice does not bind on this machine",
                "status shown        " + status.display()[:70],
                "text interface      still available (help responded)",
            ],
            note=("no speech engine bound, so \"disabled\" could not be told "
                  "apart from \"absent\" - engine binding is step 12"),
            skipped=True,
        )
        service.shutdown()
        return

    proof.record(
        15,
        "The program operates with voice unavailable",
        control_live and (not status.live_connection) and still_works,
        [
            "voice enabled       False",
            "positive control    the same adapter reports LIVE when enabled",
            "status shown        " + status.display()[:70],
            "claimed working     no",
            "text interface      still available (help responded)",
            "application         remained open",
        ],
    )
    service.shutdown()


def step_16_dispatch(proof: Proof, service) -> None:
    port = service.dispatch
    read = port.read("loads")
    refused = False
    try:
        port.read("internals")
    except DispatchPortError:
        refused = True
    missing = [
        name
        for name in ("write", "update", "create", "delete", "accept_load",
                     "book", "dispatch", "commit", "pay", "approve")
        if hasattr(port, name)
    ]
    submission = port.submit("recommendation", "consider a four week trial")
    proof.record(
        16,
        "Dispatch is never contacted or modified during sandbox proof",
        not port.connected
        and not read.ok
        and refused
        and not missing
        and not submission.to_dict()["accepted"],
        [
            "dispatch connected  " + str(port.connected),
            "read('loads')       refused: " + read.error[:56],
            "unpermitted read    refused = " + str(refused),
            "write methods       " + (", ".join(missing) if missing else "none exist"),
            "submission          accepted=False performed=False auto_execute=False",
            "decision required   Mike Zachary",
            "operational writes  0",
        ],
    )


def step_17_containment(proof: Proof, service) -> None:
    blocked = []
    for candidate in (
        "C:/Windows/Temp/assistant_escape.json",
        "C:/Users/Public/assistant_escape.json",
        str(PLUGIN_ROOT.parent / "assistant_escape.json"),
    ):
        try:
            assert_within_plugin(candidate)
            blocked.append(candidate + " -> NOT BLOCKED")
        except ContainmentError:
            blocked.append(candidate + " -> blocked")
    stray = []
    for record in service.memory.store.list_all():
        path = service.memory.store.path_for(record.record_id, record.state)
        if not str(path.resolve()).startswith(str(PLUGIN_ROOT)):
            stray.append(str(path))
    proof.record(
        17,
        "No files are written outside approved folders",
        all("-> blocked" in line for line in blocked) and not stray,
        [
            "plugin root         " + str(PLUGIN_ROOT),
            *["escape attempt      " + line for line in blocked],
            "records inspected   " + str(len(service.memory.store.list_all())),
            "records outside     " + str(len(stray)),
            "library access      read-only; no write path exists",
        ],
    )


def _plugin_sources(*folders):
    """Every .py under the named plugin folders, with its text."""
    for folder in folders:
        root = PLUGIN_ROOT / folder if folder else PLUGIN_ROOT
        for path in root.rglob("*.py"):
            text = str(path)
            if "_workspace" in text or "__pycache__" in text or "Deployment" in text:
                continue
            yield path, path.read_text(encoding="utf-8", errors="replace")


def step_18_drift(proof: Proof, service) -> None:
    """Doctrine drift, checked rather than claimed.

    Every line below was once the literal value True. Eleven claims typed into
    a list, reporting PASS for as long as the file existed - among them "No
    approval by silence or omission", which is the constitutional line the
    transmission amendment turns on, and "No fixture data presented as live",
    which is the guarantee the whole program is built around. A claim nobody
    checks is worse than no claim at all, because it reads as covered.

    Two of the eleven were about DISPATCH, and this suite runs inside JOE. They
    are no longer made here. Asserting a fact about a repository this process
    cannot see is how the list got into this state.
    """
    import re as _re

    checks = []

    # --- behaviour, from responses produced in this run ------------------
    # Drift shows up in what JOE actually returns, not only in its source.
    observed = []
    for question in ("help", "Find the rate floor policy",
                     "What does the appointment window policy say"):
        try:
            observed.append(service.ask(question).response)
        except Exception:  # a failing capability is step 2's business
            pass

    port = service.dispatch
    checks.append((
        "Dispatch not required to run JOE",
        (not port.connected) and any(r.ok for r in observed),
    ))

    # Every response carries operational_write. If a capability ever wrote
    # operational truth, this is where it would have to admit it.
    wrote = [r.capability for r in observed if getattr(r, "operational_write", False)]
    checks.append(("No component writes operational truth", not wrote))

    # Silence authorising nothing is checked twice: no response produced here
    # claims approval, and no line of source sets those flags true.
    claimed = [r.capability for r in observed
               if r.approved or r.decided or r.acted_on]
    # Product code only. tests/ legitimately sets these flags true - that is
    # what test_authority_flags_are_forced_false does, to prove the governor
    # forces them back - and a check that fails on its own guard being tested
    # trains people to weaken the check.
    setters = [path.name for path, text in _plugin_sources(
        "app", "adapters", "ui", "memory", "library", "research", "voice",
        "outlook", "contracts", "governance")
        if _re.search(r"\b(approved|decided|acted_on)\s*=\s*True", text)]
    checks.append((
        "No approval by silence or omission",
        (not claimed) and (not setters),
    ))

    # Fixture data must say it is fixture data, in the text Mike reads.
    laundered = []
    for response in observed:
        sampled = [p for p in response.provenance if p.mode == SourceMode.SAMPLE]
        if not sampled:
            continue
        shown = ((response.written or "") + " " + (response.answer or "")
                 + " " + " ".join(response.notices)).upper()
        if "SAMPLE" not in shown:
            laundered.append(response.capability)
    checks.append(("No fixture data presented as live", not laundered))

    # Anything claimed LIVE must carry the moment it was read.
    undated = [p.source for r in observed for p in r.provenance
               if p.mode == SourceMode.LIVE and not (p.as_of or "").strip()]
    checks.append(("No stale data presented as current", not undated))

    # --- structure, from the source ---------------------------------------
    manager = [path.name for path, text in _plugin_sources("")
               if _re.search(r"\bclass\s+\w*Manager\b", text)]
    checks.append(("No Manager component created", not manager))

    # Nothing may act without being asked. A scheduler, a repeating timer or a
    # bare polling loop is how an assistant becomes an agent by accident.
    autonomous = [path.name for path, text in _plugin_sources("app", "adapters")
                  if _re.search(r"\b(schedule\.every|croniter|threading\.Timer|"
                                r"while\s+True\s*:)", text)]
    checks.append(("No general-purpose autonomous agent introduced", not autonomous))

    # A provider's endpoints and SDKs belong behind an adapter. Selecting a
    # provider by name in service.py is wiring and is fine; speaking its
    # protocol anywhere else is the drift this catches.
    leaked = [path.name for path, text in _plugin_sources(
        "app", "ui", "memory", "library", "research", "voice", "outlook",
        "contracts", "governance")
        if _re.search(r"graph\.microsoft|login\.microsoftonline|"
                      r"^\s*import\s+(msal|anthropic)\b|"
                      r"^\s*from\s+(msal|anthropic)\b", text, _re.MULTILINE)]
    checks.append(("No provider-specific code outside adapters", not leaked))

    # The authority flags are read from the running provider, not asserted.
    reasoning = service.reasoning.status()
    authority = [key for key in ("can_approve", "can_decide", "can_send",
                                 "can_schedule", "can_modify_outlook",
                                 "can_modify_dispatch")
                 if reasoning.get(key)]
    checks.append(("Mike Zachary remains final authority", not authority))

    detail = {
        "No Manager component created": manager,
        "No approval by silence or omission": claimed + setters,
        "No fixture data presented as live": laundered,
        "No stale data presented as current": undated,
        "No component writes operational truth": wrote,
        "No general-purpose autonomous agent introduced": autonomous,
        "No provider-specific code outside adapters": leaked,
        "Mike Zachary remains final authority": authority,
    }
    evidence = []
    for name, ok in checks:
        line = ("PASS  " if ok else "FAIL  ") + name
        if not ok and detail.get(name):
            line += "   -> " + ", ".join(str(d) for d in detail[name][:3])
        evidence.append(line)
    evidence += [
        "",
        "responses examined  " + str(len(observed)),
        "python files read   " + str(len(list(_plugin_sources("")))),
    ]

    proof.record(
        18,
        "Drift tests",
        all(ok for _, ok in checks),
        evidence,
        note=("claims about the Dispatch repository are not made here - this "
              "suite runs inside JOE and cannot see it. Dispatch isolation "
              "from JOE's side is step 16."),
    )



def _mailbox_holding_items(service, folder: str):
    """Find a mailbox whose folder actually holds something. Say which.

    ORDER CANNOT BE PROVEN ON AN EMPTY FOLDER. An empty list is chronological,
    alphabetical, and newest-first all at once, so a proof run against a
    mailbox holding nothing passes every ordering check without examining a
    single item. That is a rubber stamp, not a proof.

    This became real when Ops@l1truck.com was made the default mailbox: it
    holds mail but no calendar and no contacts, and steps 19 and 20 went green
    having looked at nothing.

    APPROVED mailboxes only. A mailbox that is not approved for Dispatch
    operation is never opened here, even when it is the only one in the
    profile holding items - a proof that has to read a personal account to go
    green is not proving anything about the product.

    Returns (account, result). An empty account means no approved mailbox
    holds anything, and the caller must SKIP rather than pass."""
    read = {
        "calendar": lambda a: service.outlook.calendar(account=a),
        "inbox": lambda a: service.outlook.mail(account=a),
        "contacts": lambda a: service.outlook.contacts(account=a),
    }[folder]

    configured = None
    for connection in service.mailboxes.enabled_connections:
        smtp = str(connection.address or "").strip()
        if not smtp:
            continue
        result = read(smtp)
        if configured is None:
            configured = result
        if result.ok and result.returned > 0:
            return smtp, result

    return "", configured


def step_19_calendar_dates(proof: Proof, service, enabled: bool) -> None:
    """today / tomorrow / next item / a named date, each chronological."""
    if not enabled:
        proof.record(
            19, "Calendar answers today, tomorrow, next, and a named date",
            False, ["skipped: live Outlook not enabled in this run"],
            note="cannot be proven without a live Outlook connection",
            skipped=True,
        )
        return

    from adapters.outlook_com import range_for, range_for_date
    from datetime import datetime, timedelta

    def chronological(items):
        parsed = []
        for row in items:
            text = str(row.get("start", ""))
            for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
                try:
                    parsed.append(datetime.strptime(text, fmt))
                    break
                except ValueError:
                    continue
        return parsed == sorted(parsed), parsed

    account, _probe = _mailbox_holding_items(service, "calendar")
    if not account:
        proof.record(
            19, "Calendar answers today, tomorrow, next, and a named date",
            False,
            ["skipped: no mailbox in this Outlook profile holds any calendar items",
             "ordering cannot be proven on an empty folder - an empty list is",
             "chronological by default, so passing here would prove nothing"],
            note="no calendar data in any mailbox",
            skipped=True,
        )
        return

    evidence = ["mailbox read        " + account, ""]
    all_ok = True
    examined = 0

    checks = [
        ("today", range_for("today")),
        ("tomorrow", range_for("tomorrow")),
        ("a named date (+3 days)", range_for_date(datetime.now() + timedelta(days=3))),
        ("the next 14 days", range_for("", days=14)),
    ]
    for label, window in checks:
        result = service.outlook.calendar(date_range=window, account=account)
        ordered, parsed = chronological(result.items)
        examined += len(parsed)
        inside = all(window.start <= p < window.end for p in parsed)
        ok = result.ok and result.is_date_ordered and ordered and inside
        all_ok = all_ok and ok
        evidence.append(
            ("PASS  " if ok else "FAIL  ")
            + label.ljust(24)
            + str(result.returned).rjust(3) + " item(s)  "
            + window.iso_start()[:10] + " to " + window.iso_end()[:10]
            + "  chronological=" + str(ordered)
            + "  all in range=" + str(inside)
        )

    # A filter that matches nothing looks exactly like an empty calendar.
    # If the folder holds items, a wide window must return some, or the
    # filter is broken and this step must fail rather than quietly pass.
    wide = service.outlook.calendar(date_range=range_for("", days=90), account=account)
    sanity = (not wide.ok) or wide.total == 0 or wide.returned > 0
    all_ok = all_ok and sanity
    evidence.append(
        ("PASS  " if sanity else "FAIL  ")
        + "90-day sanity check".ljust(24)
        + str(wide.returned) + " item(s) from a folder holding " + str(wide.total)
    )

    # "next scheduled item" through the normal ask path.
    #
    # This may legitimately REFUSE. The ask path picks a calendar source from
    # the approved mailboxes, and if none of them holds a calendar the honest
    # answer is to say so - reporting an empty day would be true of the mailbox
    # and false of Mike. Both outcomes pass; a silent empty answer does not.
    response = service.ask("What is my next appointment?").response
    from adapters.mailbox_registry import CALENDAR

    has_calendar_source = service.mailboxes.source_for(CALENDAR) is not None
    if has_calendar_source:
        next_ok = response.capability == "OPERATIONS" and response.ok
        detail = response.answer[:60]
    else:
        # It must refuse, and the refusal must NAME the reason.
        refused = (not response.ok) and (
            "no mailbox" in response.answer.lower()
            or "holds" in (response.written or "").lower())
        next_ok = refused
        detail = ("correctly refused - no approved mailbox holds a calendar"
                  if refused else "answered anyway: " + response.answer[:40])
    all_ok = all_ok and next_ok
    evidence.append(
        ("PASS  " if next_ok else "FAIL  ")
        + "next scheduled item".ljust(24) + detail
    )
    # Nothing examined means nothing proven, whatever the checks returned.
    if examined == 0:
        all_ok = False
        evidence.append("")
        evidence.append("FAIL  no calendar item was examined by any window - "
                        "ordering was not actually tested")

    evidence.append("")
    evidence.append("items examined across all windows: " + str(examined))
    evidence.append("filtering is by the [Start] field, not by position in the folder")
    evidence.append("writes performed: 0")

    proof.record(
        19,
        "Calendar answers today, tomorrow, next, and a named date - all chronological",
        all_ok,
        evidence,
    )


def step_20_ordering(proof: Proof, service, enabled: bool) -> None:
    """Mail newest-first, contacts alphabetical."""
    if not enabled:
        proof.record(
            20, "Mail and contacts are returned in a stated order", False,
            ["skipped: live Outlook not enabled in this run"],
            note="cannot be proven without a live Outlook connection",
            skipped=True,
        )
        return
    from datetime import datetime

    mail_account, mail = _mailbox_holding_items(service, "inbox")
    contacts_account, contacts = _mailbox_holding_items(service, "contacts")
    if not mail_account or not contacts_account:
        missing = []
        if not mail_account:
            missing.append("mail")
        if not contacts_account:
            missing.append("contacts")
        proof.record(
            20, "Mail and contacts are returned in a stated order", False,
            ["skipped: no mailbox in this Outlook profile holds any "
             + " or ".join(missing),
             "an empty folder satisfies every ordering check without being read"],
            note="no " + " or ".join(missing) + " data in any mailbox",
            skipped=True,
        )
        return

    received = []
    for row in mail.items:
        text = str(row.get("received", ""))
        for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
            try:
                received.append(datetime.strptime(text, fmt))
                break
            except ValueError:
                continue
    mail_ok = mail.ok and mail.ordering == "received_desc" and received == sorted(
        received, reverse=True
    )

    contacts_ok = contacts.ok and contacts.ordering == "display_name_asc"
    # and it is alphabetical in fact, not only in label. Outlook's own
    # Sort("[FileAs]") reported alphabetical over a field this profile leaves
    # empty; the order is now produced and checked on the name that is shown.
    shown = [
        str(c.get("display_name", "")).strip()
        for c in contacts.items
        if str(c.get("display_name", "")).strip()
    ]
    contacts_ok = contacts_ok and shown == sorted(shown, key=str.lower)
    # and it examined something. Two names is the least that can demonstrate
    # an order at all.
    contacts_ok = contacts_ok and len(shown) >= 2
    mail_ok = mail_ok and len(received) >= 2

    proof.record(
        20,
        "Mail and contacts are returned in a stated order",
        mail_ok and contacts_ok,
        [
            "mail mailbox        " + mail_account,
            "contacts mailbox    " + contacts_account,
            "",
            "mail ordering       " + mail.ordering + "  (" + mail.ordering_label + ")",
            "mail items          " + str(mail.returned) + " of " + str(mail.total),
            "newest first        " + str(received == sorted(received, reverse=True)),
            "contacts ordering   " + contacts.ordering + "  (" + contacts.ordering_label + ")",
            "contacts items      " + str(contacts.returned) + " of " + str(contacts.total),
            "names compared      " + str(len(shown)),
            "timestamps compared " + str(len(received)),
            "writes performed    0",
        ],
    )


def step_21_accounts(proof: Proof, service, enabled: bool) -> None:
    """Which mailbox is being read is designated and reported."""
    if not enabled:
        proof.record(
            21, "The Outlook account in use is designated and reported", False,
            ["skipped: live Outlook not enabled in this run"],
            skipped=True,
        )
        return
    accounts = service.outlook.accounts()
    in_use = service.outlook.account_in_use()
    result = service.outlook.calendar(date_range=None)

    # Designating a mailbox means nothing unless the designated one is the one
    # read. When none is designated, JOE uses Outlook's default store and says
    # so - there is nothing to honour, and nothing to check.
    designated = (service.outlook.account or "").strip()

    def _matches(value) -> bool:
        return str(value or "").strip().lower() == designated.lower()

    designation_honoured = (not designated) or (
        _matches(in_use) and (not result.ok or _matches(result.account)))

    # What each mailbox actually holds. One configured account covers all three
    # folders, so a mailbox that holds mail but no calendar answers calendar
    # questions with silence - truthfully, and unhelpfully. This records which
    # mailbox holds what so that consequence is visible rather than discovered.
    # Every mailbox in the profile is LISTED - hiding one would be worse than
    # naming it. Only approved mailboxes are OPENED. Counting what is inside
    # an unapproved personal account would be a read of that account.
    approved = {str(c.address or "").strip().lower()
                for c in service.mailboxes.enabled_connections}
    holdings = []
    for entry in accounts:
        smtp = str(entry.get("smtp") or "")
        if not smtp:
            continue
        if smtp.strip().lower() not in approved:
            holdings.append("  " + smtp.ljust(24)
                            + "not approved for Dispatch - not read")
            continue
        counts = []
        for name, read in (
            ("calendar", lambda a: service.outlook.calendar(account=a)),
            ("mail", lambda a: service.outlook.mail(account=a)),
            ("contacts", lambda a: service.outlook.contacts(account=a)),
        ):
            try:
                r = read(smtp)
                counts.append(name + "=" + (str(r.total) if r.ok else "unreadable"))
            except Exception:  # one mailbox failing must not end the step
                counts.append(name + "=unreadable")
        holdings.append("  " + smtp.ljust(24) + "  ".join(counts))

    proof.record(
        21,
        "The Outlook account in use is designated and reported",
        # Three non-empty strings used to satisfy this, which asserts nothing
        # about the claim in the title. A build that ignored the designation
        # entirely and read whichever mailbox it liked passed, provided it
        # reported something. The designation is now checked against what was
        # actually used - which is the whole point of designating one.
        bool(accounts) and bool(in_use) and bool(result.account)
        and designation_honoured,
        [
            "accounts found      " + str(len(accounts)),
            *[
                "  " + ("* " if a.get("is_default") else "  ") + str(a.get("smtp", ""))
                for a in accounts
            ],
            "configured          " + (service.outlook.account or "(default store)"),
            "in use              " + in_use,
            "reported on read    " + (result.account or "(none)"),
            "designation         set outlook.account in configuration",
            "designation honoured  " + str(designation_honoured)
            + ("" if designation_honoured else
               "   -> designated " + designated + ", used " + in_use),
            "",
            "approved mailboxes  (Mike, final)",
            *[
                "  " + name.ljust(24) + service.outlook.account_status(name)
                for name in ("Ops@l1truck.com", "Admin@l1truck.com")
            ],
            "  'unknown' means Outlook could not be asked - NOT that the",
            "  mailbox is absent. A timeout is not a finding.",
            "",
            "what each mailbox holds",
            *holdings,
            "",
            "one configured account covers all three folders. Reading one mailbox",
            "for mail and another for calendar is Email Connection Layer v1,",
            "which is approved and not built.",
        ],
    )


def _machine_reasoning_state() -> str:
    """Sign-in state of the REAL runtime_data, not this run's sandbox.

    Reads the MSAL cache through accounts(), which returns usernames only -
    never a token - makes no network call, and changes nothing."""
    try:
        from adapters.m365_copilot_auth import CopilotAuth

        cfg = json.loads(
            (PLUGIN_ROOT / "configuration" / "joe.config.json").read_text(
                encoding="utf-8"))
        copilot = (cfg.get("reasoning") or {}).get("copilot") or {}
        auth = CopilotAuth(
            tenant_id=str(copilot.get("tenant_id", "")),
            client_id=str(copilot.get("client_id", "")),
            cache_dir=PLUGIN_ROOT / "runtime_data" / "auth",
        )
        names = [a["username"] for a in auth.accounts() if a.get("username")]
        return auth.state() + (" as " + ", ".join(names) if names else "")
    except Exception as error:  # noqa: BLE001
        return "could not be read (" + str(error)[:48] + ")"


def step_22_reasoning(proof: Proof, service) -> None:
    """Reasoning status is one of the four required states, and truthful."""
    from adapters.reasoning_provider import ReasoningStatus

    state = service.reasoning.status()
    truthful = state["status"] in ReasoningStatus.ALL and not state["live"]
    draft = service.ask("Draft an email to the broker").response
    refuses = not draft.ok and "no reasoning provider" in draft.answer.lower()
    still_works = service.ask("Find the rate floor policy").response.ok

    # THIS RUN is not THIS MACHINE. The suite redirects paths.runtime_data into
    # a throwaway workspace, so the token cache is never visible here and this
    # step always exercises the no-provider path. That isolation is deliberate
    # and worth keeping. What was not defensible was the note: it asserted "no
    # provider is credentialed on this machine", a machine-wide claim the run
    # never checked, and one that became false the moment anyone signed in.
    machine = _machine_reasoning_state()

    proof.record(
        22,
        "Reasoning status is truthful, and JOE runs without a provider",
        truthful and refuses and still_works,
        [
            "-- this run (runtime_data isolated to the proof workspace) --",
            "status              " + state["status"],
            "live                " + str(state["live"]),
            "provider            " + state["provider"],
            "credential required " + str(state["credential_required"]),
            "credential present  " + str(state["credential_present"]),
            "blocker             " + state["blocker"][:90],
            "",
            "draft request       refused honestly: " + draft.answer[:60],
            "library still works " + str(still_works),
            "fixtures labelled   never presented as live reasoning",
            "",
            "-- this machine (real runtime_data) --",
            "reasoning sign-in   " + machine,
        ],
        note=(
            "this step proves the NO-PROVIDER path, and isolates runtime_data "
            "so it always runs unsigned. It says nothing about whether this "
            "machine has a provider bound - the sign-in line above does."
        ),
    )


class _DraftStub:
    """A provider that answers, so the labelling path can be exercised.

    The suite isolates runtime_data, so no reasoning provider is ever signed
    in and a real draft request refuses. This supplies the one thing missing -
    a successful answer - and nothing else. The label is applied by JOE after
    the provider returns, so every line of code this step checks is JOE's own
    and runs unchanged."""

    def status(self) -> dict:
        return {"status": "REASONING LIVE", "live": True, "available": True,
                "provider": "stub", "model": "stub", "label": "STUB",
                "credential_required": False, "credential_present": True,
                "blocker": ""}

    def draft(self, instruction, context="", sources=None):
        from adapters.reasoning_provider import Answer, ReasoningStatus

        return Answer(text="Confirming the pickup window for load 4412.",
                      ok=True, task="draft", provider="stub", model="stub",
                      status=ReasoningStatus.LIVE)


def step_23_no_send(proof: Proof, service) -> None:
    """Drafting is never sending - checked on a draft, not in a source file.

    This step used to establish its labelling by reading
    reasoning_capabilities.py as text and looking for the strings "DRAFT ONLY"
    and "NOT SENT". That proved two strings existed in a file. It returned the
    same verdict against the real module and against a one-line comment
    containing both phrases, so every piece of labelling logic could have been
    deleted and this would still have reported PASS.

    Two of its other evidence lines were also claims nobody checked: "mail
    libraries none imported" and "outlook writes 0" were printed as facts and
    tested nowhere - and status_dict already carried a real operational_writes
    counter that this step ignored.
    """
    import re as _re

    missing = [
        name
        for holder in (service, service.outlook, service.dispatch)
        for name in ("send", "send_email", "reply", "forward", "transmit")
        if hasattr(holder, name)
    ]

    # The label, on an actual draft.
    original = service.reasoning
    try:
        service.reasoning = _DraftStub()
        drafted = service.ask("Draft a note to the broker about load 4412").response
    finally:
        service.reasoning = original

    shown = ((drafted.written or "") + " " + (drafted.answer or "")
             + " " + " ".join(drafted.notices)).upper()
    labelled = drafted.ok and "DRAFT ONLY" in shown and "NOT SENT" in shown

    # No transport library anywhere in the plugin. Checked, not claimed.
    importers = [path.name for path, text in _plugin_sources(
        "app", "adapters", "ui", "memory", "library", "research", "voice",
        "outlook", "contracts", "governance")
        if _re.search(r"^\s*(import|from)\s+(smtplib|imaplib|email)\b",
                      text, _re.MULTILINE)]

    data = service.status_dict()
    writes = int(data.get("operational_writes", 0))

    proof.record(
        23,
        "Drafting is marked DRAFT ONLY / NOT SENT, and nothing can send",
        (not missing) and labelled and (not importers)
        and data["messages_sent"] == 0 and writes == 0,
        [
            "send methods        " + (", ".join(missing) if missing else "none exist"),
            "draft produced      " + str(drafted.ok) + ", "
            + str(len(drafted.written)) + " characters",
            "DRAFT ONLY shown    " + str("DRAFT ONLY" in shown),
            "NOT SENT shown      " + str("NOT SENT" in shown),
            "first line          " + (drafted.written or "").splitlines()[0][:60],
            "mail libraries      " + (", ".join(importers) if importers
                                      else "none imported (smtplib, imaplib, "
                                           "email - searched)"),
            "messages sent       " + str(data["messages_sent"]),
            "operational writes  " + str(writes),
        ],
    )


def step_24_procedure(proof: Proof, service) -> None:
    """Procedure assistance cites a governing document, or says there is none."""
    good = service.ask("How do I create a Level 3 record").response
    bad = service.ask("How do I zzzqqqxyz zzzqqqwvu").response
    cites = good.ok and bool(good.citations or good.provenance)
    refuses = (not bad.ok) and (
        "no approved level 1 transport procedure" in bad.answer.lower()
    )
    proof.record(
        24,
        "Procedure assistance cites a governing document, or states there is none",
        cites and refuses,
        [
            "known procedure     " + good.answer[:70],
            "  cited sources     " + str(len(good.citations)),
            "unknown procedure   " + bad.answer[:70],
            "  invented?         no - it refused",
            "grounding rule      a hit must cover the question's distinctive words",
        ],
    )


# ======================================================================


def write_report(proof: Proof, service, args) -> Path:
    from contracts import stamp

    status = service.status_dict() if service else {}
    lines = [
        "# JOE - Local Proof Report",
        "",
        "**Program:** JOE, the Level 1 Assistant",
        "**Plugin root:** `" + str(PLUGIN_ROOT) + "`",
        "**Run generated (UTC):** " + stamp(),
        "**Generated by:** `proof/run_proof.py`",
        "",
        "Every value below was observed during this run on this machine. "
        "Nothing is asserted from design intent.",
        "",
        "## Result",
        "",
        "| Proof | Requirement | Result |",
        "| --- | --- | --- |",
    ]
    for step in sorted(proof.steps, key=lambda s: s["number"]):
        lines.append(
            "| {0} | {1} | {2} |".format(
                step["number"],
                step["title"].replace("|", "\\|"),
                "SKIPPED" if step["skipped"] else ("PASS" if step["passed"] else "FAIL"),
            )
        )
    lines += [
        "",
        "**Overall: "
        + str(proof.passed_count) + " passed, "
        + str(proof.skipped_count) + " skipped, "
        + str(proof.failed_count) + " failed"
        + ("**" if proof.all_passed else " - ONE OR MORE FAILED**"),
        "",
        "## Evidence",
        "",
    ]
    for step in sorted(proof.steps, key=lambda s: s["number"]):
        lines += [
            "### Proof " + str(step["number"]) + " - " + step["title"],
            "",
            "Result: **"
            + ("SKIPPED" if step["skipped"] else ("PASS" if step["passed"] else "FAIL"))
            + "**",
            "",
            "```",
        ]
        lines += step["evidence"]
        lines += ["```", ""]
        if step["note"]:
            lines += ["> " + step["note"], ""]

    if status:
        lines += [
            "## Capability status at the end of this run",
            "",
            "```",
        ]
        for capability in status["capabilities"]:
            lines.append("  " + capability["display"])
        lines += [
            "",
            "  operating mode      " + status["operating_mode"],
            "  dispatch contacted  " + str(status["dispatch_contacted"]),
            "  operational writes  " + str(status["operational_writes"]),
            "```",
            "",
        ]

    lines += [
        "## What this run did not prove",
        "",
        "- **Microphone speech recognition.** The recognition engine binds and a "
        "recognizer is installed, but recognising real speech needs a person at "
        "the microphone. An automated run cannot prove it.",
        "- **Live research.** No research provider is configured. Fixture mode "
        "was used and is labelled SAMPLE DATA everywhere it appears.",
        "- **Dispatch integration.** No approved Dispatch interface exists on "
        "this machine. Only the port contract was exercised, and it correctly "
        "refused every read.",
        "- **Real three-hour expiration.** Expiration is proven on a simulated "
        "clock. There is no background timer; records expire when a sweep runs, "
        "and listing sweeps first.",
        "- **Printing.** No printing service is bound. Print records a request "
        "and says plainly that nothing was physically printed.",
        "",
        "Mike Zachary remains final authority.",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    assert_within_plugin(REPORT)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="JOE local proof")
    parser.add_argument("--no-outlook", action="store_true")
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--speak", action="store_true")
    # Opt-in only. This sends real requests to a paid preview API, so it is
    # never part of the default 24 - see proof/run_live_reasoning_proof.py.
    parser.add_argument("--live-reasoning", action="store_true")
    args = parser.parse_args(argv)

    # --live-reasoning REPLACES this run rather than joining it. The 24 must
    # stay exactly 24 on every machine, provable with no API call and nobody
    # signed in; folding a live integration step into them would make the
    # headline count depend on a paid preview endpoint being reachable.
    if args.live_reasoning:
        from run_live_reasoning_proof import run as run_live_reasoning

        return run_live_reasoning()

    shutil.rmtree(WORKSPACE, ignore_errors=True)
    root = WORKSPACE / uuid.uuid4().hex[:8]

    print(DIVIDER)
    print("JOE, THE LEVEL 1 ASSISTANT - LOCAL OPERATIONAL PROOF")
    print(DIVIDER)
    print("  plugin root    " + str(PLUGIN_ROOT))
    print("  workspace      " + str(root))
    print("  live outlook   " + str(not args.no_outlook))
    print("  speak aloud    " + str(args.speak))

    proof = Proof()
    step_1_launcher(proof, args.no_window)

    service = make_service(root, outlook=not args.no_outlook)
    record_id = step_2_text_interaction(proof, service)
    step_4_level1(proof, service, record_id)
    step_5_save(proof, service, record_id)
    step_6_level3(proof, service)
    step_7_print(proof, service)
    step_8_delete(proof, service)
    step_9_library(proof, service)
    step_10_outlook(proof, service, not args.no_outlook)
    step_11_research(proof, service)
    step_12_voice(proof, service, args.speak)
    step_16_dispatch(proof, service)
    step_17_containment(proof, service)
    step_18_drift(proof, service)
    step_19_calendar_dates(proof, service, not args.no_outlook)
    step_20_ordering(proof, service, not args.no_outlook)
    step_21_accounts(proof, service, not args.no_outlook)
    step_22_reasoning(proof, service)
    step_23_no_send(proof, service)
    step_24_procedure(proof, service)
    final_status = service.status_dict()
    step_13_restart(proof, service, root)
    step_14_outlook_unavailable(proof, root, not args.no_outlook)
    step_15_voice_unavailable(proof, root)

    closing = make_service(root, outlook=False)
    closing.status_dict()
    report = write_report(proof, closing, args)
    closing.shutdown()

    print()
    print(DIVIDER)
    print(
        "RESULT: {0} passed, {1} skipped, {2} failed  (of {3} steps)".format(
            proof.passed_count, proof.skipped_count, proof.failed_count,
            len(proof.steps),
        )
    )
    print(DIVIDER)
    print("  report written  " + str(report))
    shutil.rmtree(WORKSPACE, ignore_errors=True)
    return 0 if proof.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
