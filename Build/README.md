# Sandbox Engine v1 - Build

Local governed workflow layer for the Level 1 Assistant.
Version 1.0.0. Final authority: Mike Zachary.

---

## Requirements

Python 3.10 or newer, reachable through the `py` launcher.
On this machine: **Python 3.14.5**, already present.

Nothing to install. No package manager, no virtual environment, no
third-party libraries. The engine uses the Python standard library only.

## Three commands

Run these from anywhere. Double-clicking works too, though a terminal shows
the output better.

**See everything working, end to end:**

```bash
D:\Sandbox\Assistan_Building\Build\run_proof.cmd
```

**Run the automated tests:**

```bash
D:\Sandbox\Assistan_Building\Build\run_tests.cmd
```

**Use the engine:**

```bash
D:\Sandbox\Assistan_Building\Build\sandbox.cmd list
```

`run_proof.cmd` resets the demonstration Sandbox so the visible result is
reproducible. Pass `--no-reset` to keep what is already there.

## Everyday use

Create a record. It starts temporary and expires in three hours.

```bash
sandbox.cmd new --request "What matters about tomorrow's run?" --response "Two stops, both live unload."
```

That prints a `sandbox_id` like `SBX-20260824-181943-F8605B`. Give it a command
in ordinary words:

```bash
sandbox.cmd command SBX-20260824-181943-F8605B "Save this"
```

Other commands, all in plain language:

```bash
sandbox.cmd command <id> "Put this under Load 123"
sandbox.cmd command <id> "Level 3 this under Ideas"
sandbox.cmd command <id> "Print this"
sandbox.cmd command <id> "Delete this"
```

Look at what is there:

```bash
sandbox.cmd list
sandbox.cmd show <id>
sandbox.cmd artifacts
sandbox.cmd expired
sandbox.cmd deleted
```

## All subcommands

| Command | What it does |
| --- | --- |
| `new --request TEXT` | Create a temporary Level 1 record. `--response`, `--channel`, and `--set FIELD=VALUE` are optional. |
| `command <id> "TEXT"` | Apply ordinary driver language to a record. |
| `show <id>` | Show one record in full. |
| `list [--state STATE]` | List the active Sandbox. Sweeps expired records first. |
| `expired` | List expired tombstones. |
| `deleted` | List deleted tombstones. |
| `sweep [--advance-hours N]` | Expire whatever has reached its time. `--advance-hours` simulates the clock moving forward. |
| `parse "TEXT"` | Show how a phrase is recognized. Changes nothing. |
| `artifacts` | List artifact requests. |
| `doctor` | Boundary and containment self-check. |

Global options come **before** the subcommand:

```bash
sandbox.cmd --json list
sandbox.cmd --project-root "D:\somewhere\else" list
```

`--set` accepts any of the 26 record fields. List fields take pipe-separated
values:

```bash
sandbox.cmd new --request "Research the northbound lane" ^
  --set research_scope="Public rate sources" ^
  --set "citations=https://example.invalid/a|https://example.invalid/b"
```

## Proving expiration without waiting three hours

```bash
sandbox.cmd sweep --advance-hours 3.1
```

This runs the sweep against a clock moved 3.1 hours forward. Anything created
more than 3.1 hours ago in that simulated frame is expired, its content purged,
and it leaves the active Sandbox.

`run_proof.cmd` does the same thing in an isolated store so the visible
demonstration records are not swept.

## What happens to a record

```
  new  ->  TEMPORARY  (expires in 3 hours)
             |
             +--  "Save this"              ->  SAVED        no expiration
             +--  "Level 3 this under X"   ->  FORMAL       no expiration, artifact request
             +--  "Print this"             ->  PRINT_READY  no expiration, artifact request
             +--  "Delete this"            ->  DELETED      content purged
             +--  (three hours, untouched) ->  EXPIRED      content purged, promoted nowhere
```

State never moves backward. `Level 1` against an already-preserved record is
refused rather than silently un-saving it. `DELETED` and `EXPIRED` accept no
further commands.

Level 2 and Level 3 raise both the state and the interaction level. **Print
raises only the state** — by ruling, Print is a state, not a level, so a printed
Level 1 record reads `LEVEL_1` / `PRINT_READY`.

## Where files land

```
D:\Sandbox\Assistan_Building\
  Sandbox\active\      live records
  Sandbox\expired\     expired tombstones
  Sandbox\deleted\     deleted tombstones
  Artifacts\requests\  artifact requests (.json and .md)
  Testing\             tests, proof script, reports
```

Plain JSON, one file per record. Open them in any editor.

The store refuses to write outside the project root. `sandbox.cmd doctor`
confirms it.

## What this does not do

- It does not produce artifacts. Level 3 and Print create **requests**.
- It does not print. Nothing here contacts a printer.
- It does not send email, place calls, commit money, or accept loads.
- It does not talk to Dispatch, Outlook, Microsoft Graph, Copilot, COMI,
  Publisher, Company Library, Research Library, or Archive.
- It does not reach the network. It imports no networking module at all.
- It does not run in the background. Expiration happens when a sweep runs, and
  `list` sweeps first.

## Source layout

```
Build\
  sandbox.cmd              main launcher
  run_tests.cmd            automated tests
  run_proof.cmd            ten local proofs, regenerates the proof report
  README.md                this file
  sandbox_engine\
    __init__.py            package exports
    clock.py               injectable clock (real and simulated)
    records.py             record model, states, levels, the 26 fields
    intents.py             deterministic command recognition
    store.py               JSON store, containment enforcement
    engine.py              lifecycle rules and transitions
    cli.py                 operator interface
```

Design: `..\Architecture\SANDBOX_ENGINE_ARCHITECTURE_v1.md`
Boundaries: `..\Constitution\SANDBOX_ENGINE_BOUNDARIES_v1.md`
Context: `..\Context\SANDBOX_ENGINE_CONTEXT_v1.md`
Operator guide: `..\Artifacts\SANDBOX_ENGINE_OPERATOR_GUIDE_v1.md`

## If `py` is not found

The launchers stop with a clear message. Install Python 3.10 or newer from
python.org and make sure the `py` launcher is included. `python` on this machine
is the Microsoft Store stub, not an interpreter, which is why the launchers use
`py`.
