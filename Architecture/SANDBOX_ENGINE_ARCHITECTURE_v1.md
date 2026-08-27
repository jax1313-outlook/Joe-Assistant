# Sandbox Engine v1 - Architecture

**Project:** Level 1 Assistant - local governed workflow layer
**Version:** 1.0.0
**Final authority:** Mike Zachary
**Project root:** `D:\Sandbox\Assistan_Building`

---

## 1. What this is

The Sandbox Engine is the **local governed workflow layer** for the Level 1
Assistant. It owns the lifecycle of Assistant interaction records: creation,
retention, command recognition, state, expiration, and artifact requests.

It is not a language model, not a chatbot, and not a replacement for
Microsoft 365 Copilot, Dispatch, Outlook, COMI, Publisher, Company Library, or
Research Library. Reasoning, research, retrieval, and voice stay where they
already are. This layer governs what happens to the written record afterward.

## 2. Position in the stack

```
   Driver speaks or types
            |
            v
   +---------------------------+
   |  Reasoning / research     |   Microsoft 365 Copilot, or any provider.
   |  retrieval, chat, voice   |   Outside this engine. Vendor-specific.
   +---------------------------+
            |
            |  request text + response text + research material
            v
   +---------------------------+
   |    SANDBOX ENGINE v1      |   THIS BUILD.
   |  record state             |   Deterministic. No model required.
   |  three-hour retention     |   Standard library only.
   |  command recognition      |   No network code.
   |  routing requests         |
   +---------------------------+
            |
            |  requests only - never automatic writes
            v
   +---------------------------+
   |  Dispatch, Company        |   NOT BUILT. NOT CONTACTED.
   |  Library, Research        |   A later integration layer would read
   |  Library, Archive,        |   the requests this engine produces.
   |  Publisher, printer       |
   +---------------------------+
```

The bottom box is deliberately unbuilt. Level 3 and Print produce **artifact
requests** on disk. Nothing consumes them yet, and the engine says so.

## 3. Modules

All source lives in `Build/sandbox_engine/`.

| Module | Responsibility | Depends on |
| --- | --- | --- |
| `clock.py` | Every time reading in the engine. `SystemClock` for real use, `FixedClock` for proving expiration without waiting. | stdlib `datetime` |
| `records.py` | `SandboxRecord`, the 26 required fields, `RecordState`, `InteractionLevel`, state and level ranking, content purging. | `clock` |
| `intents.py` | Deterministic recognition of driver language into one of six intents, plus load / mission / customer / broker / destination extraction. | stdlib `re` |
| `store.py` | JSON-per-record filesystem store. Active / expired / deleted buckets. Project-root containment enforcement. Artifact request writing. | `records` |
| `engine.py` | Lifecycle rules: creation, state transitions, expiration sweep, artifact requests. The only module that decides anything. | all of the above |
| `cli.py` | Operator surface. Rendering, argument parsing, boundary self-check. | all of the above |

Dependency direction is one-way. `clock`, `intents`, and `records` know nothing
about the store or the engine, so each can be tested in isolation.

**Total third-party dependencies: zero.** The engine imports only
`__future__`, `argparse`, `dataclasses`, `datetime`, `json`, `os`, `pathlib`,
`re`, `sys`, `uuid`. This is verified by an automated test and by proof 10.

## 4. Record states

```
                  (creation)
                       |
                       v
                  TEMPORARY  ------ 3h untouched, sweep runs ------> EXPIRED
                   |  |  |                                          (terminal)
       Level 2 ----+  |  +---- Print                                content purged
          |           |          |
          v           |          v
        SAVED         |     PRINT_READY
          |           |          |
          |        Level 3       |
          |           |          |
          +---------> FORMAL <---+
                       |
   any non-terminal ---+---- Delete ----> DELETED (terminal, content purged)
```

| State | Expires? | Meaning |
| --- | --- | --- |
| `TEMPORARY` | Yes, 3h | The default. Every interaction starts here. |
| `SAVED` | No | Level 2 parked-review record. |
| `FORMAL` | No | Level 3 formal cited work product requested. |
| `PRINT_READY` | No | Print-ready artifact requested and held for review. Does **not** change `interaction_level` — see below. |
| `DELETED` | n/a | Terminal. Content purged. Tombstone retained. |
| `EXPIRED` | n/a | Terminal. Content purged. Never promoted anywhere. |

**No downgrades.** State rank is `TEMPORARY(0) < SAVED(1) < PRINT_READY(2) <
FORMAL(3)`. A command that would lower the rank leaves the state alone and says
so. `Level 1` against an already-preserved record is refused outright rather
than silently un-saving it. Rank exists only to prevent accidental loss; it is
not a claim about which level matters more.

**Terminal is terminal.** No command is accepted against a `DELETED` or
`EXPIRED` record.

**State and interaction level are independent.** By ruling (doctrine C4, decided
by Mike Zachary), Print changes the state and leaves the level alone. Print is a
state, not a level. A Level 1 record that is printed reads `LEVEL_1` /
`PRINT_READY`, and `PRINT_READY` is the one state that does not expire while
still carrying `LEVEL_1`. Level 2 and Level 3 raise both; Print raises only the
state. See `Constitution/SANDBOX_ENGINE_BOUNDARIES_v1.md`, section C4.

## 5. Command recognition

Deterministic regular expressions over normalized text. No model is involved,
so behavior is reviewable, testable, and identical on every run.

Normalization: lowercase, curly apostrophes folded, whitespace collapsed,
surrounding punctuation stripped. `"  LEVEL 3 THIS under Ideas!! "` and
`"level 3 this under ideas"` are the same input.

Precedence, highest first:

1. **`LEVEL_1`** - leads because its decline phrases contain the words other
   intents match on. `"no need to save this"` contains `"save this"`.
2. **`DELETE`**
3. **`LEVEL_3`**
4. **`LEVEL_2`**
5. **`PRINT`**
6. **`NONE`** - unrecognized language changes nothing.

`print_requested` is computed independently of the winning intent, so
`"Level 3 this under Ideas with a formal printable report"` resolves to
`LEVEL_3` **and** raises a print-ready artifact request alongside the formal
one.

Reference extraction runs against the driver's original text, so their own
capitalization is what gets stored:

| Pattern | Field |
| --- | --- |
| `under <phrase>` | `destination` |
| `load 123`, `load #123` | `related_load` (as `Load 123`) |
| `<org> load 123` | organization prefixed onto `destination` |
| `mission <name>` / `the mission` | `related_mission` (`(unspecified)` when unnamed) |
| `customer <name>` | `related_customer` |
| `broker <name>` | `related_broker` |

## 6. Expiration

`expires_at = created_at + 3 hours`, set at creation. Only `TEMPORARY` records
carry an expiry; the moment a record is preserved, `expires_at` becomes `null`.

Expiration is evaluated by `sweep()`, which runs automatically before every
active listing and can be run directly. On expiry the engine marks the record
`EXPIRED`, **purges its content fields**, records the reason, and moves the file
out of `Sandbox/active` into `Sandbox/expired`. It is never promoted into
Company Library, Research Library, Archive, a load, or a mission.

**There is no background scheduler.** A record past its time is expired the
next time a sweep runs. Between the moment and the sweep, the record is stale
but not yet marked. This is stated plainly rather than papered over; see the
limitations section of the test report.

Proving expiration does not require waiting three hours. Every time reading
goes through `Clock`, so tests and the proof script substitute a `FixedClock`
and advance it in code.

## 7. Storage layout

```
D:\Sandbox\Assistan_Building\
  Sandbox\
    active\     SBX-<stamp>-<id>.json    TEMPORARY, SAVED, FORMAL, PRINT_READY
    expired\    SBX-<stamp>-<id>.json    EXPIRED tombstones, content purged
    deleted\    SBX-<stamp>-<id>.json    DELETED tombstones, content purged
  Artifacts\
    requests\   AR-<stamp>-<id>.json     machine-readable artifact request
                AR-<stamp>-<id>.md       the same request, readable
```

One JSON file per record, human-readable, no database. A record that changes
bucket is written to the new location and removed from the old one in the same
operation.

`SandboxStore.assert_within_project()` resolves every write path and refuses
anything outside the project root. This is why proof 9 can state that nothing
escaped `D:\Sandbox\Assistan_Building` — the store cannot write there.

The root is `Build\..` by default, or the `SANDBOX_ENGINE_ROOT` environment
variable, or an explicit `--project-root`.

## 8. Artifact requests

Level 3 and Print create a **request**, never a finished product. Each request
carries `status: REQUESTED_NOT_PRODUCED`, `produced: false`, and
`physical_print_performed: false`, and its readable companion document opens by
stating that nothing was produced, printed, or routed.

The engine has no code path that could set those flags to true. That is the
design, not an oversight: producing the artifact and routing it into Dispatch,
Company Library, Research Library, or Archive belongs to a later integration
layer that does not exist yet.

## 9. Vendor separation

Nothing Microsoft-specific, Anthropic-specific, or otherwise provider-specific
appears in `Build/sandbox_engine/`. The engine takes text in and governs the
record. Whoever produced that text — Copilot, another provider, or a person
typing — is outside its concern and outside its imports.

A future integration layer belongs in a separate package that depends on the
engine. The engine must not learn to depend on it.

## 10. Extension points, deliberately left open

- `source_channel` is a free string. A voice, phone, or portal channel would set
  it without any engine change.
- `Clock` injection means a scheduler could drive sweeps on a timer.
- Artifact requests are plain JSON on disk. A routing layer would read that
  directory.
- `retention_hours` is a constructor argument. The three-hour default comes from
  doctrine, not from a hard-coded constant buried in logic.

None of these are built. They are noted so the next mission does not have to
reverse a decision made here.
