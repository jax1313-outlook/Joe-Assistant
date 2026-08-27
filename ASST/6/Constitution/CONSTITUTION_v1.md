# Workstream 6 - Assistant Voice - Constitution

**Component:** Assistant Voice
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\6`.

---

## 1. Authority

Mike Zachary remains final authority. This layer carries words. It decides
nothing, answers nothing, and has no authority of any kind.

## 2. Transport only - the defining rule

1. **No reasoning.** No `answer`, `understand`, `interpret`, `reason`, `think`,
   `decide`, `summarize`, or `translate` method exists.
2. **No memory.** No `remember`, `recall`, `store`, or `save` method exists.
   Nothing survives a session.
3. **No retrieval.** No `search` or `retrieve` method exists.
4. **No canned answers.** The package contains no reply table, response map,
   `def answer`, or `def reply`. A transport layer with answers in it is
   reasoning smuggled in through the back door.

Enforced by `test_no_reasoning_memory_or_retrieval_method_exists` (fourteen
names), `test_the_package_never_answers_a_question`, and
`test_nothing_persists_between_sessions`, which speaks into one session, closes
it, opens another, and asserts the second remembers nothing.

## 3. It does not summarize

Handed something too long to speak, this layer **defers to the written copy**.
It states that a written result exists, roughly how long it is, and where it is
held.

It does not produce a shorter version. Summarizing is reasoning, and a summary
this layer invented would be a claim about content it does not understand -
spoken aloud, to a driver, at speed, with no way to check it.

Every brief reports `summarized: False`.

## 4. Honesty about audio

1. **No real speech engine is bound in this workstream.**
2. Every `SpeechResult` reports `audio_produced: False`.
3. Every engine status reports `real_audio_input: False` /
   `real_audio_output: False`.
4. Every session status reports both as `False`.
5. `NOT_IMPLEMENTED_ENGINES` names what is missing: microphone capture, audio
   playback, Windows SAPI, cloud speech, wake-word detection, speaker
   identification.

A transcript from the text engine is tagged with that engine's name, so typed
text can never be mistaken for something actually heard. Every transcript also
reports `interpreted: False` and `understood: False`.

## 5. Speech safety

1. **URLs, bracketed citations, and footnote markers are stripped** before
   anything is spoken.
2. **A spoken turn may not exceed `MAX_SPOKEN_WORDS` (60).** This is the one
   limit, and it is checked against the **assembled** turn, not the raw text.
3. **Text that would exceed it is deferred**, never truncated mid-sentence and
   never summarized.
4. **A deferred turn is itself checked** against the limit.

`test_prepare_never_returns_an_over_length_turn` covers eight lengths spanning
the boundary and asserts every result fits.

## 6. Barge-in

1. When the driver speaks while the Assistant is speaking, the Assistant stops.
2. Everything queued is dropped and marked `interrupted: True` with a reason.
3. This is on by default.

A system that talks over a driver in a moving truck is worse than one that says
nothing.

## 7. Confidence is carried, never repaired

A low-confidence transcript is recorded as low confidence and its text is passed
through **unchanged**. This layer does not correct, guess, complete, or clean up
what it thinks it heard. Guessing at a misheard instruction is how a voice
system causes an operational mistake.

## 8. Isolation - absolute

1. This folder writes no file outside `ASST\6`. It writes no file at all.
2. This folder imports nothing from workstreams 1, 2, 3, 4, or 5.
3. This folder assumes no other workstream exists.
4. There is no integration code here, and none may be added.

Allowed imports, asserted by test: `__future__`, `argparse`, `dataclasses`,
`datetime`, `itertools`, `json`, `re`, `sys`. Nothing else - no audio library,
no network module, no vendor SDK.

## 9. Hard prohibitions

There is no code path in this component that could:

1. Answer a question or interpret an instruction.
2. Remember anything between sessions.
3. Search, retrieve, or look anything up.
4. Record or play audio.
5. Reach the network.
6. Write any file.
7. Send anything anywhere.
8. Summarize.

## 10. What must not happen without a new decision

- Do not add reasoning, answers, or interpretation to this layer.
- Do not add persistence.
- Do not add summarization when text is too long. Defer instead.
- Do not introduce a second length threshold. One limit, checked against the
  assembled turn.
- Do not let this layer "improve" a low-confidence transcript.
- Do not bind a real speech engine without a decision about hardware and vendor.
  When one is bound, the honesty flags in section 4 must reflect reality.
