# Sandbox Engine v1 - Operator Guide

**For:** Mike Zachary
**Version:** 1.0.0
**Location:** `D:\Sandbox\Assistan_Building`

---

## What this is, in one paragraph

Every Assistant interaction starts as a temporary written record that disappears
after three hours. If it matters, you say so in ordinary words and it stops
disappearing. That is the whole engine. It holds records, it recognizes your
commands, and it expires what you never came back to. It does not send anything,
decide anything, or talk to any other system.

## Start here

Open a terminal and run:

```bash
D:\Sandbox\Assistan_Building\Build\run_proof.cmd
```

That creates a record, saves one, formalizes one, marks one print-ready, deletes
one, and expires one on a simulated clock — then writes down exactly what
happened in `Testing\LOCAL_PROOF_REPORT_v1.md`. Takes a couple of seconds.

## The four things you will actually do

**1. See what is in the Sandbox right now**

```bash
D:\Sandbox\Assistan_Building\Build\sandbox.cmd list
```

You get one line per record: its id, its state, its level, when it expires, and
the first part of the request. Anything that has run out of time is expired
before the list prints, so what you see is current.

**2. Put an interaction into the Sandbox**

```bash
sandbox.cmd new --request "Broker offered 2.10 on the Charlotte run" --response "Below your recorded floor for that lane."
```

It prints the full record and gives you a `sandbox_id` — something like
`SBX-20260824-181943-885AB8`. That is what you refer to it by.

**3. Tell it what to do with a record**

Ordinary words. Capitalization and punctuation do not matter.

```bash
sandbox.cmd command SBX-20260824-181943-885AB8 "Save this"
sandbox.cmd command SBX-20260824-181943-885AB8 "Put this under Load 123"
sandbox.cmd command SBX-20260824-181943-885AB8 "Level 3 this under Ideas"
sandbox.cmd command SBX-20260824-181943-885AB8 "Print this"
sandbox.cmd command SBX-20260824-181943-885AB8 "Delete this"
```

It tells you what it recognized, what changed, and one short notice about what
is now true.

**4. Look at one record in full**

```bash
sandbox.cmd show SBX-20260824-181943-885AB8
```

## What each command does

| You say | What happens |
| --- | --- |
| `Level 1`, `Just answer it`, `Just tell me what matters`, `No need to save this`, `Let it expire` | Stays temporary. Three-hour clock restarts. Nothing operational is created. |
| `Save this`, `Keep this`, `Level 2 this`, `Put this under Load 123`, `Attach this to the mission`, `Keep this for parked review` | Clock stops. State becomes `SAVED`. Whatever load, mission, customer, or broker you named is kept on the record. |
| `Level 3 this`, `Build a report`, `Formal presentation`, `Write this up`, `Research this completely`, `Level 3 this under Ideas` | Clock stops. State becomes `FORMAL`. The destination you named is kept. A formal-artifact request is written with your citations and sources. |
| `Print this`, `Make this printable`, `Write this so I can print later` | Clock stops. State becomes `PRINT_READY`. A print-ready request is written and held for your review. |
| `Delete this`, `Remove this`, `Forget this` | Leaves the active Sandbox. Content is erased. It goes nowhere else. |
| Anything else | Nothing changes, and it says so. |

Unsure how something will be read? Ask first — this changes nothing:

```bash
sandbox.cmd parse "Level 3 this under XPO Load 123"
```

## The six states

| State | Expires? | What it means |
| --- | --- | --- |
| `TEMPORARY` | Yes, 3 hours | The default. Where everything starts. |
| `SAVED` | No | Level 2. Parked for review. |
| `FORMAL` | No | Level 3. A formal work product has been requested. |
| `PRINT_READY` | No | A print-ready artifact has been requested and is held. |
| `DELETED` | — | You deleted it. Content erased. |
| `EXPIRED` | — | Three hours passed and you never came back. Content erased. |

A record never moves backward. Saying `Level 1` to something you already saved
is refused rather than quietly undoing your save. Deleted and expired records
accept no further commands.

## Where your files are

```
D:\Sandbox\Assistan_Building\
  Sandbox\active\        the live records
  Sandbox\expired\       what ran out of time
  Sandbox\deleted\       what you deleted
  Artifacts\requests\    artifact requests, .json and readable .md
```

Plain text files. Open any of them in Notepad. Nothing is hidden or encoded.

## Checking the boundaries yourself

```bash
sandbox.cmd doctor
```

Prints where it is writing, confirms it cannot write outside the project,
counts the records on disk, and confirms no network or vendor module is loaded.

```bash
D:\Sandbox\Assistan_Building\Build\run_tests.cmd
```

Runs 47 automated tests. Output also lands in `Testing\_last_test_run.txt`.

## Proving expiration without waiting three hours

```bash
sandbox.cmd sweep --advance-hours 3.1
```

Runs the expiry check against a clock moved forward 3.1 hours. Anything that
would have run out by then is expired for real. Useful once; be aware it does
apply to records currently in the Sandbox.

---

## What this will NOT do — read this part

This matters more than the feature list.

**It does not produce reports.** `Level 3 this` writes a *request* for a formal
work product. The report itself does not exist. The request file says so on its
first page.

**It does not print.** `Print this` writes a *request*. No printer is contacted.
Nothing comes out of anything. Every print request carries
`physical_print_performed: false`.

**It does not send email, place calls, commit money, or accept loads.** There is
no code in it that could. Not disabled — absent.

**It does not talk to Dispatch, Outlook, Microsoft Graph, Microsoft 365 Copilot,
COMI, Publisher, Company Library, Research Library, or Archive.** Nothing is
read from them and nothing is written to them.

**It does not reach the internet.** It imports no networking module at all.

**It does not run in the background.** This is the one to remember: records
expire when the engine runs a sweep, not on a timer. If you never open it,
nothing expires. `sandbox.cmd list` sweeps before it prints, so opening the list
is enough.

**It does not decide anything.** It holds, classifies, and prepares. Every
operational decision stays with you.

**"Saved" means saved here, on this disk.** It does not mean backed up,
synchronized, or filed in Company Library. The engine will never tell you
otherwise.

## If something goes wrong

**`py was not found`** — Python is not installed or the `py` launcher is
missing. Install Python 3.10 or newer from python.org. Note that `python` on
this machine is the Microsoft Store stub, not a real interpreter, which is why
everything here uses `py`.

**`NOT FOUND: no sandbox record found`** — wrong id, or the record was deleted or
expired. `sandbox.cmd expired` and `sandbox.cmd deleted` will show you.

**`REFUSED: ... is EXPIRED`** — the three hours ran out before you came back. The
record is gone and was not promoted anywhere. That is the design working.

**`REFUSED: ... Level 1 will not downgrade`** — you asked to make a saved record
temporary again. Delete it if you want it gone.

## Reference

- Design: `Architecture\SANDBOX_ENGINE_ARCHITECTURE_v1.md`
- Boundaries and conflict rulings: `Constitution\SANDBOX_ENGINE_BOUNDARIES_v1.md`
- Operating context: `Context\SANDBOX_ENGINE_CONTEXT_v1.md`
- Full command reference: `Build\README.md`
- Test results: `Testing\SANDBOX_ENGINE_TEST_REPORT_v1.md`
- Proof results: `Testing\LOCAL_PROOF_REPORT_v1.md`

## Your ruling on Print (C4) — settled

You were asked whether `Print this` should raise a Level 1 record to Level 2.

**You ruled no.** Print is a state, not a level:

```
  interaction_level  =  LEVEL_1   (unchanged)
  state              =  PRINT_READY
```

So when you say `Print this` on a Level 1 record, the clock stops, the state
becomes `PRINT_READY`, and it still reads Level 1 in every listing. That is
correct and intended — `PRINT_READY` is the one state that does not expire while
still carrying Level 1.

This is now doctrine and is locked by two automated tests. Changing it takes a
new ruling from you, not a code decision. Recorded in
`Constitution\SANDBOX_ENGINE_BOUNDARIES_v1.md`, section C4.

**No open questions remain.**
