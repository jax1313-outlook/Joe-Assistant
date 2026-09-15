# Phase 2 — the deliverable

**Sandbox:** `jax1313-outlook/Joe-Assistant`, branch
`claude/dispatch-top-improvements-rwf14h`.
**Production `Dispatch`:** read-only evidence. Nothing written, pushed, or opened
against it.

---

## Where everything is

```
Dispatch_Corrections/        the merge package for production Dispatch
  README.md                  ← start here
  patches/                   12 commits, applies to Dispatch@3c03ab2
  docs/                      11 documents: summary, ADRs, merge, migration,
                             rollback, verification, security, limitations,
                             activation, worker contracts, Joe
  evidence/                  COMPLETION_EVIDENCE.md — the 16 items, run
  collect_evidence.py        the script that produced it

Governance/                  the constitutional fork, and how it closes
  GOVERNANCE_REGISTRY.json   23 documents, hashed, with status and successor
  GOVERNANCE_RESOLUTION_v1.md
  dispatch_governance/       show / answer / check  (exit 1 on blocking)
  tools/                     record the registry; write the pointers
  pointers/                  the files Claude/ and Publisher/ each need

Workers/                     three bounded workers and a mediator
  worker_bus/                contracts, bus, audit
  worker_bus/workers/        Intelligence, Publisher, Joe, Library

Assistant_Plugin/
  conversation/              Joe: retrieval, read-back, reasoning, capture, session
  m365/                      Microsoft behind six provider-neutral ports
  voice/providers.py         which voice this machine actually has

GOVERNANCE.md                this repository's pointer to current authority
docs/M365_ACTIVATION.md      what has to be true before Microsoft is LIVE
```

## Run it

```bash
python -m pytest -o addopts="" -q                    # 681 passed, 12 skipped
cd Governance && python -m dispatch_governance check /path/to/workspace
python -m dispatch_governance answer "may a Manager component be built into Dispatch"
```

## What was asked, and where the answer is

| Asked | Answer |
|---|---|
| All ten recommendations | `Dispatch_Corrections/patches/` — verified against a fresh checkout |
| Every decision recorded with its rationale | `docs/ARCHITECTURAL_DECISIONS.md` — 17 ADRs |
| Governance resolved without blindly combining constitutions | `Governance/GOVERNANCE_RESOLUTION_v1.md` |
| Manager resolved from current evidence | Neither built nor removed. `docs/MANAGER.md` is the only document stating its implementation status. ADR-11. |
| Three workers, bounded, not a monolith | `Workers/` — the bus refuses worker-to-worker calls |
| Joe's reasoning and voice, provider-neutral | `Assistant_Plugin/conversation/`, `voice/providers.py` |
| Microsoft 365, replaceable wheel | `Assistant_Plugin/m365/` — six ports, one client, local substitutes |
| Sixteen completion-evidence items | `Dispatch_Corrections/evidence/COMPLETION_EVIDENCE.md` |
| Merge package | `MERGE_PLAN.md` + rollback + verification + migration |

## The numbers

| | Before | After |
|---|---|---|
| Dispatch suite | 3,909 | **4,171** |
| Coverage gate | 94.74% line, 3 packages | **91.39% branch, 4 packages** |
| `/home` at 2,000 loads | 7,786 ms | **47 ms** |
| 12 concurrent PIN failures | recorded as **1** | recorded as **12** |
| Proof-path commands that run | **0 of 3** | **3 of 3** |
| Sandbox suite | 451 passed, 12 failed | **681 passed**, 12 skipped |

## What is not claimed

Nothing has run on Mike's laptop. No Microsoft call has been made from any
repository. Two governance findings are outstanding and correct — `Claude/` and
`Publisher/` need a pointer file each, and this work may only write here.
`DISPATCH_CONSTITUTION_v3`'s ratification status requires Mike.

Full list: `KNOWN_LIMITATIONS.md`.
