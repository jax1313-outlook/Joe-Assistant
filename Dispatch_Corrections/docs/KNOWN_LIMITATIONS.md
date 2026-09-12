# Known limitations, and what is not claimed

Written to the standard `Dispatch/CLAUDE.md` §6 sets: *never represent an
interface definition as a working integration, or test success as operational
deployment proof.*

---

## 1. Nothing here has been run on Mike's machine

The Dispatch suite is 4,171 passing tests and the sandbox suite is 681. Both are
evidence of **software behaviour**. Neither says whether Dispatch starts on a
Windows laptop, finds the `D:` drive, or keeps a load across a restart.

The twenty-step proof path now *runs*, which it did not before. It has not been
*walked*.

## 2. No Microsoft call has been made from any repository

Every Microsoft capability is `UNCONFIGURED`. The device-code flow, the Graph
client, the six adapters and the transports are implemented to Microsoft's
published protocols and exercised through injected openers against recorded
response shapes.

That proves request shapes, paging, delta handling, retry rules, error
translation and refusals. It proves **nothing about connectivity**, and no test
in either repository claims otherwise.

## 3. What is deliberately not built

| Not built | Why |
|---|---|
| A calendar mirror / `sync` | `CLAUDE.md` §5.5 forbids a second scheduling system. |
| A Teams bot | A bot answering in a channel is a second interface to Dispatch with its own authority story, and no doctrine covers one. |
| `.docx` authoring | Graph converts an uploaded document to PDF; it does not author one. Writing OOXML is a dependency and a body of work not taken. A `.docx` request is refused **by name**. |
| Resumable uploads | Files over 4 MB are refused with the reason. Graph's simple upload stops there. |
| Azure Speech adapters | Status reporting is written; the adapters are not. The stack falls back to the text engines and reports `SIMULATED`. |
| A local SharePoint or Teams substitute | A folder on this laptop is not a shared site, and writing a file does not tell anybody. Both report `ABSENT`. |
| Locking on the remaining JSON stores | Only the **lockout counter** moved to SQLite. Eleven other stores in `portal/models/` still lose a concurrent update, and `portal/models/__init__.py` still says so. See §5. |

## 4. The capacity engine is wired, and thinly exercised

`DynamicCapacity` can now be reached: a profile per truck, a load-page panel, an
API. What is exercised is the **physical** dimension — weight, volume, linear
feet, pallets.

The stop-sequence and appointment-window paths take a `CapacityStop`, and nothing
in production constructs one. `assess_load_capacity()` evaluates the load against
the asset; it does not build a route. That is the next piece of this work and it
is not in this series.

## 5. Eleven JSON stores still lose concurrent updates

`portal/models/atomic_write_json` is honest about it and nothing about that
changed. What changed is that the one field where a lost update was a **security**
failure — the lockout counter — moved to SQLite.

The remaining stores hold conflict notices, publisher queue entries, library
records, the sandbox and the archive index. A lost update there costs a record,
not a lockout, and on a single-operator system concurrency is rare. It is a real
limitation and it is stated rather than fixed, because fixing it properly means
moving those stores into SQLite and that is a larger change than this mission's
findings support.

## 6. `verify_money_integrity` reports; it does not correct

An amount that was never a whole number of cents — a third-party import, a
four-decimal per-mile rate — is reported on `/maintenance` and left alone. Which
way `10.007` should go is a decision about somebody's invoice.

## 7. The governance registry covers 23 of 87 documents

The 23 are the ones that **assert authority**. The remaining 64 are context,
matrices and reports. Registering them without reading each one would be the
unverified claim the truth vocabulary exists to prevent.

## 8. Two governance findings are outstanding and correct

`Claude/` and `Publisher/` each carry a superseded constitution and no
`GOVERNANCE.md` saying so. The drift detector reports both as **BLOCKING**. This
work may only write to the sandbox; the exact files are generated into
`Governance/pointers/` and placing them is a human action.

## 9. `DISPATCH_CONSTITUTION_v3`'s status is unresolved

Its header reads *"Current Controlled Constitution - v3 Replacement Draft"* —
contradictory — and no repository holds an approval record. Registered `ADVISORY`,
which is true under either reading. **Requires Mike.**

## 10. The benchmark is one machine

7,786 ms → 47 ms at 2,000 loads was measured on this container with the real
portal test client. The *shape* of the improvement — constant connection count
rather than two per load — is what
`tests/test_dashboard_scaling.py` pins, because a wall-clock assertion on a
shared runner tests the runner.

## 11. Joe's voice has never heard anything

`voice/providers.py` reports what is installed. On any machine without Azure
credentials or a Whisper model that is the text engines, which report
`SIMULATED`: text in, text out. Nothing was heard and nothing was said aloud.

## 12. The worker bus is in-process

Intelligence, Publisher and Joe are separate *programs* with separate
repositories, connected here by an in-process mediator. That is the right shape
for a single-operator laptop and it is not a distributed system: there is no
queue, no retry across a restart, and no way for a worker to run on another
machine. Making it one is a different design and nothing here assumes it.
