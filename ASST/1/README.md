# ASST\1 - Assistant UI

The driver-facing Assistant window. **UI only** - not connected to memory,
library, email, research, or voice.

## Open it

```bash
Source\run_ui.cmd
```

## Test it

```bash
Tests\run_tests.cmd
```

39 tests, headless. No window opens.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is and who operates it
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - how it is put together
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The one thing to know

Every button records a **request**. Nothing here saves, prints, files, or
deletes anything outside this window. Every recorded request shows
`performed=False`, on purpose.

## Evidence

`Tests\_window_screenshot.png` - the window running on this desktop, populated,
with all four buttons enabled.

## Isolation

This folder imports nothing from workstreams 2-6 and writes nothing outside
`ASST\1`. It can be reviewed on its own.
