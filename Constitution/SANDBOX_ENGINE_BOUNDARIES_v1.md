# Sandbox Engine v1 - Boundaries

**Project:** Level 1 Assistant - local governed workflow layer
**Version:** 1.0.0
**Final authority:** Mike Zachary

This document states what Sandbox Engine v1 may do, what it may not do, and how
the conflicts in the governing documents were resolved. It governs the code in
`Build/sandbox_engine/`.

---

## 1. Authority

**Mike Zachary remains final authority.**

The engine may hold, classify, preserve, expire, and prepare requests. It may
not decide anything operational. It has no autonomous behavior: nothing happens
except in response to a command the operator issues.

## 2. Hard prohibitions

These are not policy statements. There is **no code path** in the engine that
could perform any of them, and an automated test asserts the absence of every
network and vendor import that would be required.

The engine does not and cannot:

1. Send email.
2. Place calls or dial.
3. Commit money, approve a rate, or authorize a payment.
4. Accept, book, or dispatch a load.
5. Approve a contract, or sign or submit anything on Mike's behalf.
6. Alter approved doctrine or change policy.
7. Make an autonomous operational decision.
8. Contact, read, or modify Dispatch.
9. Contact, read, or modify Outlook or Microsoft Graph.
10. Write into Company Library, Research Library, or Archive.
11. Operate a printer or cause physical printing.
12. Reach any network endpoint. It imports no networking module at all.
13. Write any file outside `D:\Sandbox\Assistan_Building`.

Verified imports of the whole engine package: `__future__`, `argparse`,
`dataclasses`, `datetime`, `json`, `os`, `pathlib`, `re`, `sys`, `uuid`.
Nothing else. Nothing third-party.

## 3. Honesty rules

- **Never claim a completed action the system did not confirm.** Level 3 and
  Print produce requests carrying `produced: false` and
  `physical_print_performed: false`. Their readable documents open by stating
  that nothing was produced, printed, or routed.
- **Never describe Sandbox material as permanently saved.** A preserved record
  is described as held locally in the Sandbox Engine store, explicitly not
  routed to Dispatch, Company Library, or Archive.
- **Never promote an expired record.** On expiry the record is marked, its
  content is purged, and it leaves the active Sandbox. There is no path from
  `EXPIRED` to anywhere else.
- **Say what is not proven.** Every report this build produces carries a
  section listing what was not operationally proven.

## 4. Containment

`SandboxStore.assert_within_project()` resolves every write path and raises
`StoreError` if it falls outside the project root. The check runs on directory
creation, record writes, and artifact request writes.

Test data is confined to `Sandbox/` and `Testing/`:

- the automated suite writes only under `Testing/_test_workspace/` and removes
  it afterward;
- the proof run writes demonstration records into `Sandbox/` and the simulated
  expiration into `Testing/_proof_expiry/`.

No unrelated Level 1 Transport file is read at runtime. The two governing
documents were read once, during design, and copied unmodified into
`Governing_Inputs/` for reference. The originals were not touched.

## 5. Conflicts in the governing documents, and how they were resolved

Recorded so the resolutions can be overruled deliberately rather than
rediscovered by accident.

### C1 - Timer and routing were listed as deferred

`LEVEL1_ASSISTANT_BUILD_PACKAGE_v1.docx` lists "Three-hour Sandbox timer and
deletion" and "Level 2 and Level 3 routing" under **capabilities reserved for
Copilot Studio / Dispatch integration**. The mission for this build orders that
layer built now.

**Resolved:** the mission is later and more specific. The three-hour lifecycle
is built locally. Routing is **not** built — Level 2 and Level 3 preserve the
requested destination and, for Level 3, raise a request. No system is written to.

### C2 - "Make this printable" is listed under both LEVEL 3 and PRINT

Both the agent configuration and the mission list that exact phrase under both
headings.

**Resolved:** explicit Level 3 language wins (`level 3`, `build a report`,
`formal presentation`, `write this up`, `research this completely`). Bare print
language resolves to PRINT. When both appear in one sentence the record becomes
`FORMAL` and a print-ready artifact request is raised alongside the formal one,
so neither instruction is dropped.

### C3 - "Let it expire" is listed under both LEVEL 1 and DELETE

The mission lists it under both. The agent configuration lists it only under
Level 1.

**Resolved:** the configuration breaks the tie. `"Let it expire"` is `LEVEL_1` —
the record is left to run out its three hours naturally rather than being
deleted immediately. The practical difference is small; it is recorded because
the two commands have different audit trails (`expired:` versus
`driver command:` in `deletion_reason`).

### C4 - SETTLED BY RULING: Print does not change the interaction level

**Question put to Mike Zachary:** PRINT must prevent expiration and land the
record in a "parked-review or print-ready state." Parked review is Level 2
language, but the mission does not say Print raises `interaction_level`, and
this build was instructed not to reinterpret Level doctrine. Does `Print this`
raise a Level 1 record to Level 2?

**Ruling by Mike Zachary: No.**

```
  interaction_level  =  LEVEL_1   (unchanged)
  state              =  PRINT_READY
```

**This is now doctrine, not a default.** Print is a state, not a level. It
changes what condition the record is in; it does not change what kind of
interaction it was. A record printed straight from Level 1 reads `LEVEL_1` /
`PRINT_READY`, and expiration is cleared.

The engine already behaved this way, so the ruling required no code change. It
is now locked by `test_print_does_not_raise_the_interaction_level` and
`test_print_from_level_2_does_not_change_the_level` in
`Testing/test_sandbox_engine.py`, and cited in
`engine.py::_apply_print`. Changing this behavior now requires a new ruling,
not a code decision.

Consequence to be aware of: `PRINT_READY` is the one state that does not expire
while still carrying `LEVEL_1`. That combination is correct and intended.

### C5 - Runtime

Neither governing document names a runtime. This machine has no Node.js, and
`python` on `PATH` is the Microsoft Store stub, not an interpreter.

**Resolved:** Python 3 through the `py` launcher (3.14.5 present), standard
library only. The launchers check for `py` and print a clear message if it is
missing.

### C6 - The original folder set lives inside Company Library

The seven project folders and both governing files were found under
`...\Company Library\Assistant\Assistant_Building\`. The mission forbids placing
records in Company Library.

**Resolved:** the build lives at `D:\Sandbox\Assistan_Building`. Nothing is
written to Company Library. The OneDrive originals were left untouched.

## 6. Decisions made inside the engine that doctrine did not dictate

Stated plainly so they are reviewable rather than invisible:

1. **Content is purged on expiry and on delete.** A tombstone keeps
   `sandbox_id`, timestamps, state, and reason so the lifecycle stays auditable,
   but the material itself is removed. Sandbox content is temporary by doctrine;
   keeping the full text of an expired record would contradict that.
2. **Explicit `Level 1` resets the three-hour window.** The doctrine expires
   records that are *untouched*. An explicit Level 1 command is a touch, and the
   mission says Level 1 should "set the three-hour expiration."
3. **State never downgrades.** See the architecture document. Rank prevents
   accidental loss; it is not a doctrine claim.
4. **`related_mission` becomes `(unspecified)`** when the driver says "the
   mission" without naming one, rather than being dropped. The reference was
   stated; only the name was not.
5. **An organization named before a load number** (as in "XPO Load 123") is kept
   in `destination`, not written to `related_broker`. Deterministic code cannot
   tell a broker from a customer from a lane name, and guessing would put a
   wrong value in an operational field.

## 7. What must not happen in the next mission without a new decision

- Do not let the engine acquire a network import.
- Do not let the engine write outside the project root.
- Do not let an artifact request set `produced` or `physical_print_performed`
  to true without a real confirmation from a real system.
- Do not add routing into Dispatch, Company Library, Research Library, or
  Archive inside `Build/sandbox_engine/`. That belongs in a separate package
  that depends on the engine, never the reverse.
- Do not rename Sandbox.
