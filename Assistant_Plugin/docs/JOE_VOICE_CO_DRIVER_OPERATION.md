# JOE — VOICE CO-DRIVER · how to run it

**Operator document.** How to start, use, test and stop spoken Opportunity
Capture. Analysis of how it was built is not here; this is the page you read
with the laptop open.

---

## WHAT IT DOES

You speak a board listing out loud. JOE hears it, reads it back, and Dispatch
records it as an Opportunity with a real id.

    You say    "Log this one. DAT, Jacksonville to Tampa, one pallet,
                dry van, seven fifty, pickup Thursday."

    JOE says   "LOGGED. OPPORTUNITY OPP-3E8FBC1892. DAT, JACKSONVILLE TO
                TAMPA, $750, PICKUP THURSDAY."

**That sentence back is the safety mechanism, not a courtesy.** You are looking
at the listing while JOE reads back the board, the lane and the rate. If it
misheard, that is where you catch it, and it is the only place you will.

---

## BEFORE THE FIRST RUN — three things, once

| | | |
|---|---|---|
| 1 | **Dispatch must be running** | Double-click `DISPATCH_START_HERE.cmd` in `D:\Dispatch` |
| 2 | **`DISPATCH_JOE_TOKEN` must be set** | Already set on this machine. To check: `echo %DISPATCH_JOE_TOKEN%` in a *new* window |
| 3 | **A microphone must be connected** | Any. JOE names the one it settled on |

Nothing else. **No Microsoft account, no tenant, no licence, no gateway, no
network.** The recognizer runs on this laptop and the model is already
downloaded — spoken capture works with no signal at all, which is the point.

---

## RUNNING IT

**Double-click `JOE_CO_DRIVER.cmd`.**

It opens a window and states what it found, in the truth vocabulary:

```
  JOE - VOICE CO-DRIVER
  Opportunity capture. Speak a board listing; Dispatch records it.

    Microphone       LIVE          Windows default
    Recognizer       CONFIGURED    faster-whisper base, local, no network
    Dispatch node    LIVE          http://127.0.0.1:8080
    Driver           CONFIGURED    mike
```

**If any line says `UNCONFIGURED` or `UNAVAILABLE`, it stops and tells you
which.** It does not start half-working.

Then:

| | |
|---|---|
| **ENTER** | speak a listing — you get 12 seconds |
| **Q** then ENTER | stop |
| **Ctrl-C** | stop, mid-recording, nothing is written |

---

## HOW TO SAY IT

Say it the way it reads on the board. Start with **"log this one"** — that is
what tells JOE this sentence is a capture and not conversation.

> **"Log this one. Truckstop, Ocala to Savannah, two pallets, reefer, twelve
> hundred, pickup Friday."**

**Board and lane are what a load is.** Everything else is optional — *a capture
with gaps beats a listing lost to the next screen.* Say the rate as you would
say it: *"seven fifty"*, *"twelve hundred"*, *"twenty two hundred"* all work.

**All four of your boards are recognised:** DAT, Truckstop, 123Loadboard,
TruckSmarter.

### If you do not say "log this one"

Nothing is written and it says so. That is deliberate — every other thing JOE
does is a read, and this one writes. A sentence spoken in the cab should not
become a row in the database because the microphone was open.

---

## WHAT IT SAYS WHEN SOMETHING IS WRONG

| It says | It means |
|---|---|
| `NOTHING HEARD` | The microphone carried no speech. Nothing was written |
| `NOT A CAPTURE` | The wake phrase was not in what it heard. Nothing was written |
| `NOT LOGGED. DISPATCH DID NOT ANSWER.` | The node is not running or not reachable. **Nothing was written and no id was invented** |
| `MERGED INTO EXISTING. OPPORTUNITY OPP-…` | Dispatch recognised this as the same load you already logged and filled in the gaps |

**There is no silent failure path.** If you hear nothing, something is wrong
with the speaker, not with the capture.

---

## THE ONE THING TO WATCH

The recognizer is a general-purpose English model and it has never heard of
freight. JOE corrects the words it is known to get wrong — it has returned
*"Dad"* for **DAT**, *"Trucks stop"* for **Truckstop**, *"drive-in"* for **dry
van** and *"Riefer"* for **reefer** — and those corrections are tested against
the real recordings.

**It corrects; it never invents.** A word it does not recognise comes through
exactly as heard, because a wrong capture you trust is worse than a gap you can
see. So: listen to the read-back. If the board is wrong, say it again.

---

## TESTING IT WITHOUT A MICROPHONE

Everything except the microphone can be proven from a keyboard:

```bash
cd "D:\Joe Assistant\Assistant_Plugin" && set PYTHONPATH=. && py -3 -m pytest tests/test_misheard_freight.py tests/test_opportunity_loop.py -q
```

**These tests write nothing to Dispatch.** They test JOE's half — routing,
parsing, the read-back, and the honest failure — against a stand-in port.
Dispatch's half is tested in Dispatch.

To exercise the whole path including a real write, use rehearsal mode so nothing
lands in live data untagged:

```bash
cd "D:\Dispatch" && py -3 -c "from dispatch import rehearsal; print(rehearsal.start_session(label='voice capture', actor_id='mike')['session_id'])"
```

Start Dispatch with `DISPATCH_REHEARSAL_SESSION` set to the id it prints, and
every capture made in that session is tagged and visibly marked wherever it is
displayed.

---

## WHERE THE PARTS ARE

| | |
|---|---|
| The loop | `app/co_driver.py` — thin on purpose |
| Hearing | `adapters/whisper_listen.py` |
| The wake phrase | `app/router.py` |
| Parsing and mishearing repair | `app/opportunity_parser.py` |
| Talking to Dispatch | `adapters/dispatch_port.py` · `submit_opportunity` |
| Speaking | `adapters/voice_sapi.py` |
| The contract | Dispatch: `POST /api/joe/opportunity` |

**JOE mints no identity and keeps no copy.** Dispatch is the sole identity
authority; if it did not answer, there is no id and JOE says so.
