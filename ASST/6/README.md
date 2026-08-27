# ASST\6 - Assistant Voice

Speech transport and driver-mode shaping. **Voice transport only** - no
reasoning, no memory, no library, no email.

## Read this first

**Nothing here makes a sound.** No microphone, no speaker, no SAPI, no cloud
service. Text goes in and out along the path a real engine would use.

What is real and tested: turn taking, barge-in, and the rules that shape text so
it is safe to hear at speed.

```bash
Source\voice.cmd status
```

## Use it

```bash
Source\voice.cmd brief "Pickup window moved to twelve hundred" --matters "It overlaps the Richmond delivery by thirty minutes" --decision "Pick one before you roll" --location "the Sandbox"
```

```bash
Source\voice.cmd demo
```

Global options (`--silent`, `--confidence`, `--no-barge-in`, `--json`) go
**before** the subcommand.

## Test it

```bash
Tests\run_tests.cmd
```

72 tests. No audio device needed.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is and the audio gap
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - the ports, state machine, driver mode
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The four things to know

**It understands nothing.** No reasoning, no answers, no canned replies. Ask it
a question and it carries the question.

**It defers, it never summarizes.** Text over 60 spoken words becomes "there is
a written result ready, here is where it is."

**Barge-in works.** Start talking and it stops; queued lines are dropped and
marked interrupted, not lost silently.

**It never repairs what it misheard.** Low confidence is reported; the text
passes through unchanged.

## Isolation

This folder imports nothing from workstreams 1-5, imports no audio or network
module, and writes nothing anywhere.
