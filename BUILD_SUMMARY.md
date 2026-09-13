# BUILD SUMMARY — Claude build, Phase 3

**Destination: `D:\Claude-Build`.** This package is produced for transfer into
that folder. See `TRANSFER_TO_D_DRIVE.md`.

**Authority: Mike Zachary.** Nothing here decides anything. Every finding below
is a recommendation or a measurement, and the two items that need a person are
named in §5.

---

## What this build is

Three phases against one question: what is wrong with Dispatch that is hard to
see from inside it, and what is the strongest thing that can be done about it.

| Phase | What it produced |
|---|---|
| 1 | Ten findings, each with a measurement rather than an opinion |
| 2 | Twelve corrections to Dispatch, plus the sandbox's own governance registry, worker bus, Joe conversation layer and Microsoft 365 adapter layer |
| 3 | The two open items Phase 2 recorded as unfinished, both now closed and measured |

Phase 2's corrections are open as a thirteen-PR stack against production
Dispatch. Phase 3's two corrections are patches `0013` and `0014` in
`Dispatch_Corrections/patches/`, held here rather than pushed.

---

## Phase 3, in numbers

| | Before | After |
|---|---|---|
| Dispatch suite | 4,171 | **4,217** |
| 12 processes queueing one action each | store held **2** | store holds **12** |
| Capacity checks reachable from a real load | **0** | stop ceiling, out-of-route, window validity, appointment order, forward walk |
| Mutating store functions under a lock | 0 of 41 | **41 of 41** |

Both numbers were measured before the change as well as after. The "before"
column is not an estimate.

---

## The two things Phase 3 closed

### The capacity engine's appointment checks had never run

`dispatch/capacity.py` could evaluate stop sequences and appointment windows
from the day it was written — stop ceilings, out-of-route miles, a window that
closes before it opens, a delivery whose appointment opens before its pickup,
and a forward walk that arrives, waits, serves and drives on.

None of it ran. `scoring.assess_capacity()` called the engine without the
`stops=` argument, so every one of those checks was unreachable code **with
passing unit tests** — the most convincing kind of dead code there is.

`dispatch/load_stops.py` is the missing constructor. Most of it is about
refusing to invent what the load does not record:

- **No naive timestamp reaches the engine.** It treats one as BLOCKING and is
  right to — `06:00` is not an instant. But Dispatch's own `pickup_datetime` is
  routinely naive, so passing those raw would have turned a correct refusal into
  a false alarm on nearly every load.
- **A single recorded time is not a window.** Setting `end = start` would have
  produced a "complete" window demanding arrival to the second.
- **An unknown distance is `None`, not `0.0`.** Zero drive hours claims the
  truck arrives the instant it leaves.
- **An unrecorded dwell stays `None`.** Zero would make every appointment look
  reachable.

### The JSON stores lost concurrent updates

Twelve processes, twelve records queued, **two** in the store. Nothing corrupt;
ten records simply absent, with nothing anywhere saying so.

`store_lock()` and `guarded()` hold an exclusive cross-process lock across the
whole read-modify-write, applied to all 41 mutating functions across all 11
stores. Twelve of twelve afterwards, repeatably.

---

## §5 — what still needs Mike

1. **`DISPATCH_CONSTITUTION_v3`'s ratification status.** It is headed "Current
   Controlled Constitution – v3 Replacement Draft", which is contradictory, and
   no repository holds an approval record. Registered ADVISORY, which is true
   under either reading. Inferring it was ratified would be the manufactured
   approval `CLAUDE.md` §4 forbids outright.

2. **`Claude/` and `Publisher/` each need a `GOVERNANCE.md` pointer.** The drift
   detector reports both as BLOCKING and is correct. This build may only write
   to its own folder, so both are reported rather than fixed.

---

## What is not claimed

Nothing here has run on Mike's laptop. No Microsoft call has been made from any
repository. The twenty-step proof path now *runs*; it has not been *walked*.

`CLAUDE.md` §6: the repository test suite is evidence of software behaviour
only, and is never operational proof.

Full list: `Dispatch_Corrections/docs/KNOWN_LIMITATIONS.md`.
