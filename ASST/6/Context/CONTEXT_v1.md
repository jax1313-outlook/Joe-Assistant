# Workstream 6 - Assistant Voice - Context

**Component:** Assistant Voice
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\6`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

The voice transport layer. Three jobs:

- **speech to text** - carry what the driver said into text
- **text to speech** - carry text back out to the driver
- **driver interaction** - turn taking, queueing, barge-in, and shaping text so
  it is safe to hear at speed

## Transport only

This layer moves words. It does not understand them.

No reasoning. No memory. No library, email, calendar, or research. It has no
idea what a load is. Hand it a sentence and it carries the sentence; hand it a
question and it carries the question, without answering it.

That boundary is what makes voice safe to build separately: a transport layer
that also thinks is two components pretending to be one, and when it gets
something wrong you cannot tell which half failed.

## The most important limitation, stated first

**No real speech engine is bound.** No microphone, no speaker, no audio device,
no Windows SAPI, no cloud speech service, no wake word.

What exists is a pair of **ports** - one for speech to text, one for text to
speech - and text-only engines that move text through exactly the path real
engines would use. Every result reports `audio_produced: False`. Every status
reports `real_audio_input: False` and `real_audio_output: False`.

Binding a real engine needs hardware, a vendor decision, and a mission that has
both. This one has neither, so the engines are honest stand-ins rather than
something that looks like it works.

The **turn-taking, barge-in, and driver-mode shaping are real** and fully
tested. Those are the parts that would have been hard to get right later.

## Driver mode

The doctrine says a spoken answer states three things:

1. what changed
2. why it matters
3. whether a decision or action is required

This layer builds exactly that, from parts it is given, and enforces two more
rules of its own:

- **Never read citations, URLs, or footnote markers aloud.** They are stripped
  before anything is spoken.
- **Never read a long written product aloud.** Anything that would exceed 60
  spoken words is deferred: the driver is told a written result exists, roughly
  how long it is, and where it is held.

**It does not summarize.** Summarizing is reasoning. Handed something too long,
this layer defers to the written copy rather than inventing a shorter version it
has no business producing.

## Barge-in

The behavior worth having. A driver who starts talking while the Assistant is
mid-sentence gets the Assistant to stop, and anything still queued is dropped
and marked interrupted.

In a moving truck a system that talks over the driver is worse than one that
says nothing at all. Barge-in is on by default and can be turned off.

## Confidence is carried, not judged

When a transcript arrives with low confidence, this layer records that fact and
passes the text through **unchanged**. It does not correct, guess, or clean up
what it thinks it heard. Whoever consumes the transcript can see the confidence
and decide what to do about it.

## What it deliberately is not

- no real audio input or output
- no reasoning, answering, or interpreting
- no memory - nothing survives a session
- no library, research, email, calendar, or contacts
- no network access
- no writing to disk

## Runtime

Python 3.10 or newer through the `py` launcher. Verified on this machine:
Python 3.14.5. Standard library only. Nothing is installed, and notably no
`pyaudio`, `sounddevice`, `pyttsx3`, `speech_recognition`, or `pywin32`.

## Relationship to other workstreams

None. This folder does not know any other workstream exists. It imports nothing
from folders 1 through 5.
