# Workstream 6 - Assistant Voice - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\6`

---

## Read this first

**Nothing here makes a sound.** No microphone, no speaker, no Windows speech, no
cloud service. Text goes in, text comes out, along exactly the path a real
speech engine would use.

What **is** real and tested: the turn taking, the barge-in, and the rules that
shape text so it is safe to hear at speed. Those are the parts that would have
been painful to get right after a speech engine was bolted on.

```bash
D:\SANDBOX\Assistan_Building\ASST\6\Source\voice.cmd status
```

tells you exactly what is and is not there.

## Build a driver-mode brief

This is the useful part. Give it the three things a spoken answer needs:

```bash
voice.cmd brief "Pickup window moved to twelve hundred" --matters "It now overlaps the Richmond delivery by thirty minutes" --decision "You need to pick one before you roll" --location "the Sandbox"
```

Out comes:

```
  Pickup window moved to twelve hundred. It now overlaps the Richmond delivery
  by thirty minutes. You need to pick one before you roll. Full written result
  is in the Sandbox.

  words               30
  fits driver mode    True
  summarized          False
```

Leave off `--decision` and it says "No decision needed right now." rather than
leaving you wondering.

## Speak arbitrary text

```bash
voice.cmd say "Two stops tomorrow, both live unload." --location "the Sandbox"
```

Short text gets spoken. **Long text does not.** Hand it a report and you get:

```
  There is a written result ready. It runs to about 90 words, too long to read
  at speed. Read it when you are stopped. Full written result is in the Sandbox.

  deferred to written copy True
  summarized               False
```

It does **not** summarize. It tells you a written result exists and where it is.
Summarizing would be this layer making a claim about content it does not
understand, read to you at seventy miles an hour.

## See what gets stripped before speaking

```bash
voice.cmd clean "Rates cleared the floor [Rate Floor Policy, p. 3], see https://example.invalid/x"
```

URLs, citations, footnote markers, and markdown are removed. Nobody wants a URL
read aloud in a truck.

## Pass text through the listening side

```bash
voice.cmd listen "what changed"
```

```bash
voice.cmd --confidence 0.3 listen "mumbled something"
```

The second one is flagged low confidence and the text is passed through
**exactly as received**. This layer never guesses at what you probably meant.
Guessing at a misheard instruction is how a voice system causes a real mistake.

## Watch barge-in work

```bash
voice.cmd demo
```

```
  session_opened   voice transport session opened
  queued           Pickup window moved to twelve hundred.
  queued           The Richmond delivery now overlaps it by thirty minutes.
  queued           This third line will be dropped when you interrupt.
  barge_in         driver interrupted; stopped speaking and dropped 3 queued utterance(s)
  heard            what changed
  spoken           delivered to the text engine; no audio was produced
  session_closed   voice transport session closed
```

That is the behavior worth having. You start talking, it stops. Anything queued
is dropped and marked interrupted - not lost silently, you can still see what it
was about to say.

Turn it off with `--no-barge-in` if you ever want it to finish.

## Turn output off

```bash
voice.cmd --silent say "anything"
```

Reports `spoken: False` with a reason, so "voice is off" is distinguishable from
"something was said".

## Check what is and is not there

```bash
voice.cmd status
```

```
  real_audio_input                 False
  real_audio_output                False
  interprets_speech                False
  remembers_between_sessions       False
  has_reasoning                    False

  NOT IMPLEMENTED:
    - microphone capture
    - audio playback
    - Windows SAPI / System.Speech
    - any cloud speech service
    - wake-word detection
    - speaker identification
```

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\6\Tests\run_tests.cmd
```

72 tests. No audio device needed.

## What this will NOT do - read this part

**It will not make a sound.** No engine is bound.

**It will not answer anything.** Ask it a question and it carries the question.
There is no reasoning in it and no table of canned replies.

**It will not remember.** Close a session and it is gone. Nothing is written to
disk at all.

**It will not summarize.** Too long means deferred to the written copy.

**It will not fix what it misheard.** Low confidence is reported; the text is
passed through unchanged.

**It will not look anything up, send anything, or reach the network.**

## If something goes wrong

**`py was not found`** — install Python 3.10 or newer from python.org. `python`
on this machine is the Microsoft Store stub, which is why everything uses `py`.

**`ERROR: nothing speakable in the supplied text`** — everything in it was a URL
or a citation, so after stripping there was nothing left to say.

**`ERROR: a driver brief needs something that changed`** — the first argument to
`brief` was empty or was stripped to nothing.

**Your text came back deferred and you wanted it spoken** — it is over 60 words
once assembled. Shorten what you pass in, or use `brief` with the three parts
kept tight.

**Global options were rejected** — `--silent`, `--confidence`, `--no-barge-in`,
and `--json` go **before** the subcommand.
