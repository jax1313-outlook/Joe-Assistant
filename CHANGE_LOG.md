# CHANGE LOG — Claude build

Newest first. Every entry names what was measured, not only what was written.

Destination: `D:\Claude-Build`. Authority: Mike Zachary.

---

## Phase 3 — 2026-09-13

Closed the two items Phase 2 recorded as unfinished. Both were fixed and
measured before and after; neither number is an estimate.

### `0014` — Stop the JSON stores losing a concurrent update

Closes `KNOWN_LIMITATIONS` §5, which Phase 2 stated rather than fixed.

`atomic_write_json` guaranteed no reader sees half a file. It could not stop two
writers overwriting each other: both read, both mutate their own copy, and the
second `os.replace` wins.

| | |
|---|---|
| Before | 12 processes queued one action each; the store held **2** |
| After | **12 of 12**, repeatably over four runs |
| Scope | all **41** mutating functions across all **11** stores |

`store_lock()` + a `guarded()` decorator holding the lock across the whole
read-modify-write. The decorator was chosen over restructuring: every mutator
already reads, edits and saves, so one line above each fixes the race without
touching 138 call sites. Mirrors the `@atomic` decorator the service layer
already uses, so there is one idiom for this rather than two.

Lock file sits *beside* the store — `os.replace` swaps the file on every write,
so a lock on its inode stops describing the file that is there, and a store that
does not exist yet still needs one. Reentrant per thread; blocking, not
timing out. `fcntl` and `msvcrt` both, because Dispatch runs on Windows and the
suite runs on POSIX.

### `0013` — Build capacity stops from real loads

Closes `KNOWN_LIMITATIONS` §4, which named this as "the next piece of this work".

`dispatch/capacity.py` could evaluate stop sequences and appointment windows
from the day it was written. None of it ran: `scoring.assess_capacity()` called
the engine without `stops=`, so every check was unreachable code **with passing
unit tests**.

Now reachable on a real load, with no new data recorded: a delivery whose
appointment opens before its pickup, and a window that closes before it opens —
both BLOCKING.

Four refusals, each guarding against an answer that would look right:

| Refusal | What the alternative would have done |
|---|---|
| No naive timestamp reaches the engine | Correct BLOCKING refusal becomes a false alarm on nearly every load |
| A single recorded time is not a window | A zero-width window demands arrival to the second |
| An unknown distance is `None`, not `0.0` | Claims the truck arrives the instant it leaves |
| An unrecorded dwell stays `None` | Makes every appointment look reachable |

The forward walk turns itself on when a distance and a dwell exist. Demonstrated:
600 miles with a 1.5-hour dwell projects both arrivals and reports a delivery
window 5.5 hours out of reach.

### Packaging

`ROOT_MANIFEST.md` (522 files, SHA-256 each), `verify_manifest.py` — proven to
exit 1 on a tampered file and 0 on a clean tree — `TRANSFER_TO_D_DRIVE.md`,
`BUILD_SUMMARY.md`, and `claude-build-phase3.zip`.

**Dispatch suite: 4,171 → 4,217.**

---

## Phase 2 — 2026-09-12

Twelve corrections to Dispatch, plus this repository's own governance registry,
worker bus, Joe conversation layer and Microsoft 365 adapter layer.

| | Before | After |
|---|---|---|
| Dispatch suite | 3,909 | 4,171 |
| Coverage gate | 94.74% line, 3 packages | 91.39% branch, 4 packages |
| `/home` at 2,000 loads | 7,786 ms | 47 ms |
| 12 concurrent PIN failures | recorded as **1** | recorded as **12** |
| Proof-path commands that run | 0 of 3 | 3 of 3 |
| Sandbox suite | 451 passed, 12 failed | 681 passed, 12 skipped |

Patches `0001`–`0012`. Open as PRs #130–#142 against `jax1313-outlook/Dispatch`,
as a linear stack to be merged in number order.

Also in Phase 2, and found by running the code rather than reading it:

- `after_commit` reset to an empty list instead of `None`, so callbacks outside a
  transaction queued onto a list nobody drained.
- `PRAGMA table_info` does not list VIRTUAL generated columns; `table_xinfo`
  does. The money migration reported 0 of 10 columns present when all 10 were.
- `BackupStatus.describe()` did not exist. `status_line()` raised on every call
  and had no test *and* no caller.
- The booking-conflict parser returned `None` for any offset-bearing timestamp —
  and `None` means "no conflict found". A double booking read as clear.

### After the PRs opened — a defect CI found

`PRAGMA journal_mode` does not honour `busy_timeout`: SQLite returns
`SQLITE_BUSY` immediately for a journal-mode change rather than invoking the
busy handler. Setting it per connection put an unprotectable exclusive lock on
the first thing every connection did.

| 8 threads opening a fresh database | |
|---|---|
| before | 2 of 40 raised `database is locked` |
| after an ordering-only fix | 1 of 40 — **still wrong** |
| after the real fix | **0 of 150** |

The first fix was wrong and the reproduction said so. Ordering cannot help a
statement that ignores the timeout. Fixed at the bottom of the stack and the
twelve PRs above it rebased.

---

## Phase 1 — 2026-09-12

Ten findings, each with a measurement rather than an opinion. Accepted as the
baseline for Phase 2.
