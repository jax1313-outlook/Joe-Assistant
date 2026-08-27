# Workstream 6 - Assistant Voice - Architecture

**Component:** Assistant Voice
**Version:** 1.0.0

---

## 1. Shape

```
                    +---------------------------+
                    |          cli.py           |  operator surface
                    +-------------+-------------+
                                  |
                +-----------------+------------------+
                |                                    |
                v                                    v
    +---------------------------+      +---------------------------+
    |        session.py         |      |     driver_mode.py        |
    |  turn taking, queueing,   |      |  strip, shape, defer,      |
    |  barge-in, event log      |      |  length limit              |
    +-------------+-------------+      +---------------------------+
                  |                            (pure functions,
                  v                             no session state)
    +---------------------------+
    |        engines.py         |   TWO PORTS
    |  SpeechToTextEngine       |   transcribe()
    |  TextToSpeechEngine       |   speak() / stop()
    |  + text-only engines      |   no real audio bound
    +-------------+-------------+
                  |
                  v
    +---------------------------+
    |       utterance.py        |  transport objects
    +---------------------------+
```

`driver_mode.py` holds no session state - it is a set of pure functions over
text. That keeps the shaping rules testable in isolation and keeps the session
free of judgement about content.

## 2. Modules

| Module | Responsibility | Tests |
| --- | --- | --- |
| `utterance.py` | `Utterance`, `Transcript`, `SpeechResult`, direction, ids, confidence flags. | 6 |
| `engines.py` | The two ports, plus `TextSpeechToText`, `TextTextToSpeech`, `SilentTextToSpeech`. | 13 |
| `driver_mode.py` | Stripping, three-part brief, length limit, deferral. | 23 |
| `session.py` | `VoiceSession`: state machine, queue, barge-in, event log. | 21 |
| `cli.py` | `say`, `brief`, `listen`, `clean`, `demo`, `status`. | exercised manually |

**Third-party dependencies: zero.** Imports: `__future__`, `argparse`,
`dataclasses`, `datetime`, `itertools`, `json`, `re`, `sys`.

No `pyaudio`, `sounddevice`, `pyttsx3`, `speech_recognition`, `win32com`, or
`comtypes`. No networking module. A transport layer that cannot reach a device
or a service cannot quietly start doing so.

## 3. The two ports

```
  SpeechToTextEngine                TextToSpeechEngine
    transcribe(audio_reference)       speak(utterance) -> SpeechResult
      -> Transcript                   stop()
    status()                          status()
```

Small on purpose. `transcribe` takes a *reference* to whatever the caller has -
a string in this build, audio in a real one - so binding a real engine later
does not change the session, the driver-mode rules, or anything above.

Three engines are built, all text-only:

| Engine | Behavior | Reports |
| --- | --- | --- |
| `text-stt` | returns typed text as a transcript | `real_audio_input: False`, tagged with the engine name |
| `text-tts` | collects what would have been said | `spoken: True`, `audio_produced: False` |
| `silent-tts` | accepts and speaks nothing | `spoken: False` with a reason |

`silent-tts` exists so "voice output is off" is distinguishable from "something
was said". Both produce a `SpeechResult`; only one has `spoken: True`.

## 4. Session state machine

```
    IDLE  --enqueue-->  IDLE  (queued, not spoken)
    IDLE  --flush/say-->  SPEAKING  -->  IDLE
    IDLE  --listen-->  LISTENING  -->  IDLE
 SPEAKING --listen-->  [barge-in]  -->  LISTENING  -->  IDLE
    any   --close-->  CLOSED   (terminal; every operation raises)
```

Every transition appends a `SessionEvent`. The event log is the session's whole
audit trail: `session_opened`, `queued`, `spoken` / `not_spoken`, `heard`,
`heard_nothing`, `low_confidence`, `barge_in`, `session_closed`.

## 5. Barge-in

```
  driver speaks while state == SPEAKING
        |
        +-- tts.stop()
        +-- every queued utterance -> SpeechResult{spoken: False, interrupted: True,
        |                              reason: "dropped by barge-in; the driver spoke"}
        +-- queue cleared
        +-- state -> IDLE
        +-- event recorded with the drop count
```

Dropped utterances are **recorded**, not discarded silently. A driver who
interrupts can still see what the Assistant was about to say.

Barge-in can be switched off with `allow_barge_in=False`, in which case
listening while speaking does not interrupt.

## 6. Driver mode

**The three-part brief:**

```
  <what changed>. <why it matters>. <decision required>.
  [Full written result is in <location>.]
```

When no decision is supplied, the turn says "No decision needed right now."
rather than leaving it ambiguous.

**Stripping, before anything is spoken:**

| Removed | Pattern |
| --- | --- |
| URLs | `https?://...`, `www....` |
| bracketed citations | `[...]`, `(... retrieved/source/ibid/p. N ...)` |
| footnote markers | `[1]`, `[^1]`, `(1)` |
| markdown marks | `*`, `#`, backticks |

**The length rule - one limit, applied to the assembled turn:**

```
  MAX_SPOKEN_WORDS = 60
  TOO_LONG_TO_READ_WORDS = MAX_SPOKEN_WORDS   (same number, by definition)

  prepare_for_speech(text):
      cleaned = strip_unspeakable(text)
      if cleaned is empty            -> refuse
      if cleaned is over the limit   -> defer
      brief = build the turn
      if the ASSEMBLED turn is over  -> defer
      otherwise                      -> speak it
```

**A bug this closes.** An earlier draft had a separate, higher "too long to
read" threshold of 90 words above the 60-word spoken limit. Text between the
two passed the defer check, then had ~12 words of scaffolding added, and came
out over the spoken limit anyway - reported as not fitting driver mode but
spoken regardless. It was found by running the component, not by reading it. One
limit, checked against the assembled turn, closes the gap;
`test_prepare_never_returns_an_over_length_turn` covers eight lengths across the
boundary.

**Deferral, not summary:**

```
  "There is a written result ready. It runs to about N words, too long to read
   at speed. Read it when you are stopped. Full written result is in X."
```

That is the honest answer to being handed a report. A summary would be this
layer making a claim about content it does not understand.

## 7. Confidence

`Transcript.confidence` is whatever the engine reported.
`is_low_confidence` is `confidence < 0.6`. The session records a
`low_confidence` event and passes the text through **unchanged**.

No correction, no completion, no cleanup. Guessing at a misheard instruction is
how a voice system causes an operational mistake, and it would be indetectable
downstream.

## 8. What was deliberately left out

- **Any real speech engine.** Needs hardware and a vendor decision. Declared
  NOT IMPLEMENTED rather than half-bound to something that looks like it works.
- **Summarization.** See section 6.
- **Wake-word detection, speaker identification, endpointing, VAD.** All need
  real audio.
- **Persistence.** Nothing survives a session, so there is no transcript file to
  secure and no retention question to answer here.
- **Language detection or translation.** Reasoning about content.
- **Any command recognition.** This layer carries what was said. Deciding what
  it meant belongs elsewhere.
