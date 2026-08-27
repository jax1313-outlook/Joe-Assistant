# ASST\4 - Assistant Outlook

**Read-only** calendar, email, and contact awareness. No sending, no
modification, no scheduling, no approval authority.

## Read this first

**Not connected to a real mailbox.** No Outlook, Exchange, or Microsoft Graph
connection exists in this component. It reads sample fixture files in `Data\`.
The awareness logic is real and tested; the data is sample data.

```bash
Source\outlook.cmd status
```

prints `live_connection: False` every run.

## Use it

```bash
Source\outlook.cmd --now 2026-08-26T08:00:00Z brief
```

```bash
Source\outlook.cmd attention
```

Global options (`--now`, `--data-root`, `--json`) go **before** the subcommand.

## Test it

```bash
Tests\run_tests.cmd
```

63 tests.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is, and the live-connection gap
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - the port, the models, the arithmetic
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The three things to know

**It cannot act.** No send, reply, accept, decline, schedule, or modify method
exists. The provider port defines three methods and all three are reads.

**Flagging is noticing, not deciding.** A flagged message shows why it surfaced
and reports `decided: False`, `acted_on: False`. It over-flags on purpose,
because the rule is a visible word list you can audit.

**Everything is UTC.** A brief showing "12:00" means 12:00 UTC.

## Isolation

This folder imports nothing from workstreams 1, 2, 3, 5, and 6, and writes
nothing anywhere. It imports no mail library at all - not even `email`.
