# Workstream 6 - Assistant Voice - Build Report

**Component:** Assistant Voice
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\6`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build speech-to-text, text-to-speech, and the driver interaction layer.

No reasoning. No memory. No Outlook. No library. Voice transport only.

## FILES CREATED

```
ASST\6\
  README.md                                     reviewer entry point
  BUILD_REPORT_v1.md                            this file
  TEST_REPORT_v1.md                             full test results
  Context\CONTEXT_v1.md                         what this is and the audio gap
  Constitution\CONSTITUTION_v1.md               binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md               ports, state machine, driver mode
  Operator_Guide\OPERATOR_GUIDE_v1.md           how Mike runs it
  Source\voice.cmd                              launcher
  Source\assistant_voice\__init__.py            package exports
  Source\assistant_voice\__main__.py            py -m assistant_voice entry
  Source\assistant_voice\utterance.py           utterances, transcripts, results
  Source\assistant_voice\engines.py             the two ports + text-only engines
  Source\assistant_voice\driver_mode.py         stripping, shaping, length, deferral
  Source\assistant_voice\session.py             turn taking, queueing, barge-in
  Source\assistant_voice\cli.py                 operator interface
  Tests\run_tests.cmd                           test launcher
  Tests\test_assistant_voice.py                 72 tests
  Tests\_last_test_run.txt                      raw output of the last run
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\6\Tests\run_tests.cmd
py -m assistant_voice brief "Pickup window moved to twelve hundred" --matters "..." --decision "..." --location "the Sandbox"
py -m assistant_voice say <90 words of report text> --location "the Sandbox"
py -m assistant_voice say "Pickup window moved to twelve hundred." --location "the Sandbox"
py -m assistant_voice demo
```

## TEST RESULTS

**72 tests. 72 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestUtterance` | 6 |
| `TestEngines` | 13 |
| `TestDriverMode` | 23 |
| `TestSession` | 21 |
| `TestBoundaries` | 9 |

Live operator run:

```
brief  -> "Pickup window moved to twelve hundred. It now overlaps the Richmond
           delivery by thirty minutes. You need to pick one before you roll.
           Full written result is in the Sandbox."
           30 words, fits driver mode True, summarized False

say (90 words)
       -> "There is a written result ready. It runs to about 90 words, too long
           to read at speed. Read it when you are stopped. Full written result
           is in the Sandbox."
           deferred True, summarized False

demo   -> queued x3, barge_in dropped 3 queued utterance(s), heard, spoken, closed
```

Detail in `TEST_REPORT_v1.md`.

## PROVEN CAPABILITIES

1. Carries text through a speech-to-text port and returns a tagged transcript.
2. Carries text through a text-to-speech port and returns a result.
3. Reports confidence as given and flags low confidence without altering text.
4. Refuses out-of-range confidence values.
5. Distinguishes "nothing was spoken" from "something was spoken".
6. Never reports audio as produced, on any engine.
7. Queues utterances without speaking them.
8. Speaks a queue in order.
9. Runs a full session state machine: idle, listening, speaking, closed.
10. Barge-in: stops the engine, drops the queue, marks each dropped utterance
    interrupted with a reason, and records the event.
11. Triggers barge-in automatically when listening begins mid-speech.
12. Allows barge-in to be disabled.
13. Refuses every operation after a session is closed.
14. Records an ordered event log of everything that happened.
15. Builds the three-part driver-mode brief.
16. States "No decision needed right now" when none is supplied.
17. Strips URLs, citations, footnote markers, and markdown before speaking.
18. Reports whether unspeakable content was removed.
19. Enforces one spoken-length limit against the assembled turn.
20. Defers over-long text to its written copy instead of summarizing.
21. Produces a deferred turn that is itself within the limit.
22. Never claims to have summarized, interpreted, or understood anything.
23. Retains nothing between sessions.
24. Contains no reasoning, memory, retrieval, or canned-answer capability.
25. Writes no file and imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. The CLI. Exercised by hand, not by the automated suite.
2. `Transcript.is_final`. Carried, but the text engine always sets it `True`.
3. Streaming or interim transcripts. The port allows them; nothing exercises them.
4. Event ordering under interleavings beyond the tested sequences.
5. Behavior over very long sessions.
6. Non-ASCII or non-English text through the stripping rules.
7. The `--confidence` and `--silent` flag plumbing.

## NOT IMPLEMENTED

1. **Microphone capture.**
2. **Audio playback.**
3. **Windows SAPI / System.Speech, or any local speech engine.**
4. **Any cloud speech service.**
5. Wake-word detection.
6. Speaker identification or diarization.
7. Voice activity detection or endpointing.
8. Any reasoning, answering, or interpretation.
9. Any summarization.
10. Any memory or persistence.
11. Any library, research, email, calendar, or contact capability.
12. Any network capability.
13. Language detection or translation.
14. Command or intent recognition.
15. Any user interface. Command line only.

## KNOWN LIMITATIONS

1. **Nothing makes a sound.** The largest gap. Transport, turn taking,
   barge-in, and shaping are real and tested; the engines are text-only.
2. The 60-word limit is a judgement, not a measurement. Not calibrated against
   real speech rates or road testing.
3. Stripping is pattern-based. An unusual citation format will survive.
4. Barge-in is turn-level, not word-level.
5. Low-confidence text passes through unchanged - deliberate, but a misheard
   instruction travels onward as misheard, with its confidence attached.
6. No session transcript survives. Good for privacy, nothing to review after.
7. Verified on Windows 11, Python 3.14.5 only.
8. This layer understands nothing. What was said, and what to say back, belongs
   elsewhere.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. Every command and every test runs
with no audio device, no network, and no setup.

**The biggest thing to know: nothing makes a sound.** No microphone, no speaker,
no SAPI, no cloud service. This is not buried - it is the second heading of the
context document, `voice.cmd status` prints `real_audio_input: False` and
`real_audio_output: False` on every run, and `NOT_IMPLEMENTED_ENGINES` names the
six things that are missing.

**What that leaves is deliberately the valuable half.** Turn taking, barge-in,
and the driver-mode shaping rules are real and fully tested. Those are the parts
that are painful to retrofit once a speech engine is attached; the engine itself
is a port implementation and a vendor decision.

**Two ports, deliberately small.** `transcribe(audio_reference)` and
`speak(utterance)` / `stop()`. `transcribe` takes a *reference* - a string here,
audio in a real build - so binding a real engine later changes nothing above it.

**Barge-in is the behavior worth having.** A driver who starts talking gets the
Assistant to stop, and everything queued is dropped, marked `interrupted: True`
with a reason, and recorded - not lost silently. In a moving truck a system that
talks over the driver is worse than one that says nothing.

**It defers, it does not summarize.** Handed a report, this layer says a written
result exists, roughly how long it is, and where it is held. A summary would be
this layer making a claim about content it does not understand, spoken aloud, at
speed, with no way to check it. Every brief reports `summarized: False`.

**It does not repair what it misheard.** Low confidence is recorded and the text
passes through unchanged. Guessing at a misheard instruction is how a voice
system causes an operational mistake, and downstream would never know.

**A real bug was found by running it, and is documented rather than quietly
fixed.** An earlier draft had two length thresholds - a 60-word spoken limit and
a separate 90-word defer threshold. Text between them passed the defer check,
picked up about twelve words of scaffolding, and came out at 102 words: reported
as `fits driver mode: False` and spoken anyway. Reading the code would not have
caught it. There is now one limit, checked against the assembled turn, and
`test_prepare_never_returns_an_over_length_turn` covers eight lengths across the
boundary. The before-and-after output is in `TEST_REPORT_v1.md`.

**No audio library is imported at all** - not `wave`, not `audioop`, not
`pyaudio`, not `pyttsx3`. A transport layer that cannot reach a device cannot
quietly start doing so.
