# Phase 2 — implementation summary

**Sandbox:** `jax1313-outlook/Joe-Assistant`, branch
`claude/dispatch-top-improvements-rwf14h`.
**Production `Dispatch`:** read-only evidence throughout. Nothing was written to
it, pushed to it, or opened against it.

---

## Where the work is

| Area | Location | What it is |
|---|---|---|
| The ten corrections | `Dispatch_Corrections/patches/` | A twelve-commit series against `Dispatch@3c03ab2`, applyable with `git am`. Verified by applying it to a clean checkout and running the suite. |
| Governance resolution | `Governance/` | Registry, CLI, drift detector, pointer generator, resolution record. |
| Three workers | `Workers/` | Contracts, mediator, audit, four bounded adapters. |
| Joe | `Assistant_Plugin/conversation/`, `Assistant_Plugin/voice/providers.py` | Read-back, capture, bounded reasoning, session, voice provider survey. |
| Microsoft 365 | `Assistant_Plugin/m365/` | Six ports, one Graph client, Graph adapters, local substitutes. |
| Evidence | `Dispatch_Corrections/evidence/` | Output of `collect_evidence.py`, verbatim. |

## Why the corrections are a patch series and not a fork

Copying `Dispatch/` into the sandbox would have created a second copy of 34,000
lines of freight code — which is the exact defect Recommendation 10 is about, one
layer down. `Dispatch/CLAUDE.md` §5.4 is explicit that operational truth lives in
Dispatch and "a plug-in's copy is a copy".

So the corrections were developed on a local, never-pushed branch of a read-only
clone, exported as patches, and **verified by re-applying them to a clean
checkout**. The suite result in the evidence report is from that re-application,
not from the working tree they were written in.

## The ten, and what each turned out to be

| # | Recommendation | What was done | Where it landed |
|---|---|---|---|
| 1 | Operational proof commands are invalid | Built the missing `verify` capability rather than deleting the step; corrected steps 19 and 20 to the real CLI; added a contract test that parses **every** scripted command through its own parser | `dispatch/proof.py`, `scripts/dispatch_proof.py`, `tests/test_proof_command_contract.py`, `tests/test_proof_persistence_verify.py` |
| 2 | `DynamicCapacity` has no production caller | **Wired**, not reserved — the `docs/MANAGER.md` precedent covers a capability never built, not working code. One table was all that was missing | `dispatch/capacity_store.py`, `dispatch/services.py`, `portal/routes/dispatch_api.py`, `tests/test_capacity_is_reachable.py` |
| 3 | `/home` is O(total loads) | Schema built once per process; two rollups replace two queries per load. **7,786 ms → 47 ms** at 2,000 loads | `dispatch/db.py`, `dispatch/store.py`, `dispatch/services.py`, `tests/test_dashboard_scaling.py` |
| 4 | Money is float everywhere | Integer cents with ROUND_HALF_UP; generated `_cents` columns as a DDL-only migration; every sum, product and comparison in cents | `dispatch/money.py`, `dispatch/money_schema.py`, `tests/test_money.py` |
| 5 | Nothing ever takes a backup | Launcher menu, three CLI commands, a portal page, a schedule printer, and a restore proof that records **who** performed it | `dispatch_launcher/backup_actions.py`, `portal/routes/maintenance.py`, `tests/test_backup_activation.py` |
| 6 | No locking; the PIN lockout is defeatable | Counters moved to SQLite with a single-statement increment; `busy_timeout`. **12 concurrent failures: recorded as 1 before, 12 after** | `dispatch/authcounters.py`, `tests/test_auth_lockout_concurrency.py` |
| 7 | No business operation is atomic | `unit_of_work()` that nested `get_connection()` joins; `@atomic` on sixteen operations; sends deferred past commit | `dispatch/db.py`, `dispatch/services.py`, `tests/test_atomic_service_operations.py` |
| 8 | No transport; the chosen auth is being closed | A port and four adapters; delegated device-code auth with no client secret anywhere | `dispatch/transport/`, `dispatch/msauth.py`, `dispatch/outbound.py`, `tests/test_transport.py`, `tests/test_msauth.py` |
| 9 | Delivery failures are invisible | Every attempt recorded **before** the send; bounded backoff; operator-triggered retry; structured logging with rotation; surfaced on `/home` and `/maintenance` | `dispatch/delivery.py`, `dispatch/observability.py`, `dispatch/notifications_retry.py`, `tests/test_delivery_visibility.py` |
| 10 | Governance has forked | One machine-discoverable registry, a drift detector that finds the fork, and pointers that mark superseded documents **without touching them** | `Governance/` (sandbox) |

## Found while doing the work, and fixed

These were not in the ten. Each was discovered because the corrections exercised
a path nothing had exercised.

1. **The capacity engine could never have worked with the portal's own input
   format.** `parse_operational_timestamp` rejects a timestamp with no offset —
   correctly — and the load form's placeholder was `YYYY-MM-DD HH:MM`. Every load
   entered as documented would have produced a `SEVERITY_BLOCKING` finding.
   `dispatch/timestamps.py`.
2. **The calendar silently dropped loads.** `get_load_calendar()` matched a month
   by string prefix on a free-text field, so `9/14/2026 08:00` — what a US
   dispatcher writes — simply was not there. No error, no row.
3. **The calendar filed a delivery on the wrong day.** The day was sliced off the
   raw string, so `2026-09-15T01:00Z` landed on the 15th when in Eastern time it
   is the evening of the 14th.
4. **Every timestamp was rendered raw**, including on the rate confirmation a
   broker receives and on the driver's own screen. A 70 MPH failure (D2).
5. **A fourth hand-rolled datetime parser** in `portal/models/conflict.py` had no
   offset format, so it would have silently stopped detecting *every* booking
   conflict the moment appointments became unambiguous.
6. **A fork/exec race in the launcher** — `/proc/<pid>/cmdline` is empty between
   fork and exec, so `control.start()` could record a null command line for the
   process it must later identify before `stop()` signals it. Found by the suite
   under load, never in isolation.
7. **`joe.config.json` hardcodes a Windows separator** (`research\fixtures`). Off
   Windows that is one filename containing a backslash: the fixture corpus
   vanished and research degraded to `UNAVAILABLE`, silently.
8. **`assert_within_plugin` passed `C:/Windows/Temp/x` on POSIX**, where it is
   not absolute and resolves *under* the plugin root. The containment test was
   passing on a developer's machine and meaning nothing.
9. **A regex classified `"when's delivery"` as an open question** (`deliver\b`
   does not match before the "y"), sending a stored fact to a reasoning provider.
10. **The coverage gate was line-only and named different packages in two
    places** — CI enforced one gate and `pytest --cov` locally gave another, and
    `dispatch_launcher/` (3,943 lines) was in neither.

## The numbers

| | Before | After |
|---|---|---|
| Dispatch suite | 3,909 passed | **4,171 passed**, 0 failed, 0 skipped |
| Gated coverage | 94.74%, line-only, three packages | **91.39%**, **branch**, **four packages** |
| `/home` at 2,000 loads | 7,786 ms | **47 ms** |
| `/home` at 5,000 loads | ~19 s (extrapolated; unmeasurable in practice) | **102 ms** |
| `get_connection()` | 1.22 ms | 0.75 ms cold, **0.006 ms** inside a unit of work |
| 12 concurrent PIN failures | recorded as **1** | recorded as **12** |
| Proof path commands that run | **0 of 3** | **3 of 3** |
| Sandbox suite | 451 passed, 12 failed | **681 passed**, 12 skipped (Tk, stated) |

The coverage figure went **down** because the gate got stronger: branch coverage
counts the false paths, and in this repository the false paths are the refusals.
