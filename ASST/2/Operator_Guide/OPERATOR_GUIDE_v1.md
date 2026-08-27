# Workstream 2 - Assistant Memory - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\2`

---

## What this is

The retention store. Records start temporary and disappear after three hours
unless you say otherwise. That is the whole component.

## The command

```bash
D:\SANDBOX\Assistan_Building\ASST\2\Source\memory.cmd list
```

Everything below uses `memory.cmd`.

## See what is being held

```bash
memory.cmd list
```

One line per record: id, state, level, when it expires, and the start of the
request. Anything past its time is expired before the list prints, so what you
see is current.

## Put something into retention

```bash
memory.cmd new --request "Broker offered 2.10 on the Charlotte run" --response "Below your recorded floor."
```

It prints the record and gives you an id like `MEM-20260825-011405-CAB7F2`.
It starts `TEMPORARY` at Level 1 and expires in three hours.

## Change what happens to it

```bash
memory.cmd level-2 MEM-20260825-011405-CAB7F2 --related-load "Load 123"
```

```bash
memory.cmd level-3 MEM-20260825-011405-CAB7F2 --destination "Ideas"
```

```bash
memory.cmd print-ready MEM-20260825-011405-CAB7F2
```

```bash
memory.cmd delete MEM-20260825-011405-CAB7F2 --reason "no longer needed"
```

```bash
memory.cmd level-1 MEM-20260825-011405-CAB7F2
```

## What each one does

| Command | State becomes | Level becomes | Expires? |
| --- | --- | --- | --- |
| `level-1` | stays `TEMPORARY` | `LEVEL_1` | yes, clock restarts |
| `level-2` | `SAVED` | `LEVEL_2` | **no** |
| `level-3` | `FORMAL` | `LEVEL_3` | **no** |
| `print-ready` | `PRINT_READY` | **unchanged** | **no** |
| `delete` | `DELETED` | unchanged | n/a, content erased |

`print-ready` leaving the level alone is deliberate. Print is a state, not a
level. A Level 1 record you mark print ready reads `LEVEL_1` / `PRINT_READY` and
stops expiring. That is correct.

A record never moves backward. `level-1` on something you already preserved is
refused rather than quietly un-preserving it. Deleted and expired records accept
no further commands.

## Look at one record

```bash
memory.cmd show MEM-20260825-011405-CAB7F2
```

```bash
memory.cmd expired
```

```bash
memory.cmd deleted
```

## Prove expiration without waiting three hours

```bash
memory.cmd sweep --advance-hours 3.1
```

Runs the expiry check against a clock moved 3.1 hours forward. Anything that
would have run out by then is expired for real: content erased, moved out of the
active set, promoted nowhere.

## Check the boundaries yourself

```bash
memory.cmd doctor
```

Prints where it writes, confirms it cannot write outside folder 2, counts the
records on disk, and confirms no network module is loaded.

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\2\Tests\run_tests.cmd
```

45 tests. Output also lands in `Tests\_last_test_run.txt`.

## Where your files are

```
ASST\2\Data\active\     what is being held
ASST\2\Data\expired\    what ran out of time
ASST\2\Data\deleted\    what you deleted
```

Plain JSON. Open any of them in Notepad.

## What this will NOT do - read this part

**It does not run in the background.** This is the one to remember. Records
expire when a sweep runs, not on a timer. If you never open it, nothing expires.
`memory.cmd list` sweeps before it prints, so opening the list is enough.

**It does not produce anything.** `level-3` marks a record formal. It does not
write a report.

**It does not print.** `print-ready` marks a record. No printer is contacted.

**It does not file anything anywhere.** Nothing is routed to a library, an
archive, or any operational system. "Held" means held in `ASST\2\Data` on this
disk.

**It does not understand ordinary language.** Commands are explicit
(`level-2`, `print-ready`). Interpreting what you said is a different job and is
not in this component.

**It does not send email, place calls, or reach the network.** There is no code
in it that could.

## If something goes wrong

**`py was not found`** — install Python 3.10 or newer from python.org. `python`
on this machine is the Microsoft Store stub, which is why everything uses `py`.

**`NOT FOUND: no record found`** — wrong id, or it was deleted or expired. Check
`memory.cmd expired` and `memory.cmd deleted`.

**`REFUSED: ... is EXPIRED`** — the three hours ran out. The record is gone and
was promoted nowhere. That is the design working.

**`REFUSED: ... Level 1 will not downgrade`** — you asked to make a preserved
record temporary again. Delete it if you want it gone.
