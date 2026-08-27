# ASST\2 - Assistant Memory

The Sandbox retention system. Records start temporary and expire in three hours
unless preserved. **Retention only** - no UI, no library, no email, no research,
no voice, no routing.

## Use it

```bash
Source\memory.cmd list
```

## Test it

```bash
Tests\run_tests.cmd
```

45 tests.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is and the doctrine it follows
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - states, storage, module design
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The two things to know

**Nothing expires on a timer.** Records expire when a sweep runs. `list` sweeps
before it prints, so opening the list is enough.

**Nothing is routed anywhere.** "Held" means held in `ASST\2\Data` on this disk.
Level 3 produces no report. Print Ready contacts no printer.

## Isolation

This folder imports nothing from workstreams 1 and 3-6, and nothing from the
existing Sandbox Engine - whose doctrine it follows and whose code it does not
touch. It writes nothing outside `ASST\2`.
