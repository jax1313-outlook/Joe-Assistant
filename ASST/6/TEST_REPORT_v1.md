# Workstream 6 - Assistant Voice - Test Report

**Component:** Assistant Voice
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, standard library only

---

## Result

**72 tests. 72 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\6\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_voice.py`.

The suite needs no microphone, no speaker, and no audio device.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestUtterance` | 6 | Inbound and outbound directions; blank text refused; unknown direction refused; text stripped; ids unique; word counts. |
| `TestEngines` | 13 | Text STT returns what it was given and tags the engine; empty input yields an empty transcript; **confidence is carried, not judged**; the threshold is visible; out-of-range confidence refused; text TTS records what would be said and **never claims audio**; the silent engine speaks nothing and says so; stops are counted; both ports declare no real audio; the not-implemented list is explicit. |
| `TestDriverMode` | 23 | The three-part brief; "No decision needed right now" when none supplied; written location stated; empty change refused; **URLs, bracketed citations, footnote markers, and markdown stripped**; removal reported both ways; short text spoken; **long text deferred, not summarized**; a deferred turn is itself short enough; **`prepare_for_speech` never returns an over-length turn across eight lengths**; the defer threshold equals the spoken limit; deferral names the written location and the reason; unspeakable-only input refused; over-long briefs rejected by `check_length`; word counting; briefs never claim to have summarized or interpreted. |
| `TestSession` | 21 | Opens idle and records it; enqueue does not speak; flush speaks in order; `say` queues and speaks; returns to idle; listening records what was heard; empty input recorded as `heard_nothing`; **low confidence recorded, text unchanged**; **barge-in drops the queue, marks utterances interrupted, and stops the engine**; **listening while speaking triggers barge-in**; barge-in can be disabled; the silent engine reports nothing spoken; closing clears the queue; **no operation after closing**; closing twice is harmless; events recorded in order; status declares no audio, no reasoning, no memory; the log serializes. |
| `TestBoundaries` | 9 | No workstream import; **no audio, network, or vendor import**; standard library only; **no reasoning, memory, or retrieval method** (fourteen names); no write call anywhere; **nothing persists between sessions**; transcripts never claim understanding; no speech result ever claims audio; **the package never answers a question**. |

## The transport-only proofs

Four tests carry the defining rule:

1. `test_no_reasoning_memory_or_retrieval_method_exists` - fourteen names
   checked: `answer`, `understand`, `interpret`, `reason`, `think`, `decide`,
   `remember`, `recall`, `store`, `save`, `search`, `retrieve`, `summarize`,
   `translate`.
2. `test_the_package_never_answers_a_question` - fails if a reply table,
   response map, `def answer`, or `def reply` appears in the source. A transport
   layer with answers in it is reasoning smuggled in.
3. `test_nothing_persists_between_sessions` - speaks into one session, closes
   it, opens another, and asserts the second remembers nothing.
4. `test_transcripts_never_claim_understanding` - every transcript reports
   `interpreted: False` and `understood: False`.

## The bug this build found and closed

`test_prepare_never_returns_an_over_length_turn` exists because of a real defect
found by **running** the component, not by reading it.

An earlier draft had two thresholds: a 60-word spoken limit and a separate
90-word "too long to read" threshold. Text between them passed the defer check,
then had roughly twelve words of scaffolding added ("No decision needed right
now", "Full written result is in ..."), and came out over the spoken limit -
reported as `fits driver mode: False` and spoken anyway.

Observed before the fix, with 84 words of input:

```
  words                    102
  fits driver mode         False  (over the 60 word driver-mode limit)
  deferred to written copy False        <- spoken regardless
```

After: one limit, checked against the **assembled** turn.

```
  words                    31
  fits driver mode         True
  deferred to written copy True
  defer reason             longer than 60 words; not read aloud
```

The test now covers eight lengths spanning the boundary - 10, 40, 55, 58, 60,
65, 90, 200 words - and asserts every result fits.

## Operator verification

```
voice.cmd brief "Pickup window moved to twelve hundred" --matters "..." --decision "..." --location "the Sandbox"
  -> 30 words, fits driver mode, summarized False

voice.cmd say <90 words of report text> --location "the Sandbox"
  -> deferred to written copy True, 31 words, summarized False

voice.cmd demo
  -> queued x3, barge_in dropped 3 queued utterance(s), heard, spoken, closed
```

## Boundary verification

Imports across the whole package: `__future__`, `argparse`, `dataclasses`,
`datetime`, `itertools`, `json`, `re`, `sys`. Nothing else.

Absent by test: `wave`, `audioop`, `sounddevice`, `pyaudio`,
`speech_recognition`, `pyttsx3`, `win32com`, `comtypes`, `socket`, `urllib`,
`http`, `requests`, `ssl`, and every vendor module.

---

## PROVEN CAPABILITIES

1. Carries text through a speech-to-text port and returns a tagged transcript.
2. Carries text through a text-to-speech port and returns a result.
3. Reports confidence as given and flags low confidence without altering text.
4. Refuses out-of-range confidence values.
5. Distinguishes "nothing was spoken" from "something was spoken" via the silent
   engine.
6. Never reports audio as produced, on any engine.
7. Queues utterances without speaking them.
8. Speaks a queue in order.
9. Runs a full session state machine: idle, listening, speaking, closed.
10. **Barge-in**: stops the engine, drops the queue, marks each dropped
    utterance interrupted with a reason, and records the event.
11. Triggers barge-in automatically when listening begins mid-speech.
12. Allows barge-in to be disabled.
13. Refuses every operation after a session is closed.
14. Records an ordered event log of everything that happened.
15. Builds the three-part driver-mode brief.
16. States "No decision needed right now" when no decision is supplied.
17. Strips URLs, bracketed citations, footnote markers, and markdown before
    speaking.
18. Reports whether unspeakable content was removed.
19. Enforces one spoken-length limit against the assembled turn.
20. Defers over-long text to its written copy instead of summarizing it.
21. Produces a deferred turn that is itself within the limit.
22. Never claims to have summarized, interpreted, or understood anything.
23. Retains nothing between sessions.
24. Contains no reasoning, memory, retrieval, or canned-answer capability.
25. Writes no file and imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. **The CLI.** Exercised by hand as recorded above; no automated test drives
   `cli.py`.
2. **`Transcript.is_final`.** Modelled and carried; the text engine always sets
   it `True`, so partial-transcript handling is untested.
3. **Streaming or interim transcripts.** The port shape allows them; nothing
   exercises them.
4. **`SessionEvent` ordering under interleaved speaking and listening beyond
   the tested sequences.**
5. **Behavior with very long sessions.** The largest test uses a handful of
   turns.
6. **Non-ASCII or non-English text** through the stripping rules.
7. **The `--confidence` and `--silent` CLI flags.** Wired to tested code paths;
   the flag plumbing itself is unproven.

## NOT IMPLEMENTED

1. **Microphone capture.** No audio input of any kind.
2. **Audio playback.** No audio output of any kind.
3. **Windows SAPI / System.Speech, or any local speech engine.**
4. **Any cloud speech service.**
5. **Wake-word detection.**
6. **Speaker identification or diarization.**
7. **Voice activity detection or endpointing.**
8. **Any reasoning, answering, or interpretation.**
9. **Any summarization.**
10. **Any memory or persistence.**
11. **Any library, research, email, calendar, or contact capability.**
12. **Any network capability.**
13. **Language detection or translation.**
14. **Command or intent recognition.**
15. **Any user interface.** Command line only.

## KNOWN LIMITATIONS

1. **Nothing makes a sound.** This is the largest gap. The transport, turn
   taking, barge-in, and shaping rules are real and tested; the engines are
   text-only stand-ins.
2. **The 60-word limit is a judgement, not a measurement.** It was not
   calibrated against real speech rates or road testing.
3. **Stripping is pattern-based.** An unusual citation format will survive and
   be spoken. The patterns are visible in `driver_mode.py`.
4. **Barge-in is turn-level, not word-level.** With a real engine, stopping
   mid-word would depend on that engine's behavior, which is untested here.
5. **Low-confidence text is passed through unchanged**, which is deliberate but
   means a misheard instruction travels onward exactly as misheard - with its
   confidence attached.
6. **No session transcript survives.** Good for privacy, but nothing can be
   reviewed after the fact.
7. Verified on Windows 11 with Python 3.14.5 only.
8. **This layer understands nothing.** Everything about what was said, and what
   to say back, belongs somewhere else.
