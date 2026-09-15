# Complete file inventory

Generated from `git`, not written by hand. The hash is the first 12 characters
of the file's SHA-256, so the package can be checked against a checkout.

> **This is the Phase 2 inventory, and it is a snapshot of that delivery.** Line
> counts and hashes below are from when it was generated and later work has
> moved past several of them. For what is in the package *now*, with a full
> SHA-256 per file and a checker that runs on a machine with nothing installed,
> use `ROOT_MANIFEST.md` and `Dispatch_Corrections/verify_manifest.py`. Kept
> rather than regenerated because it is the record of what Phase 2 delivered,
> and overwriting it would erase that.

## Added — sandbox `jax1313-outlook/Joe-Assistant`

**`Dispatch_Corrections/docs/`** — The merge package documents

| File | Lines | sha256 |
|---|---:|---|
| `Dispatch_Corrections/docs/ARCHITECTURAL_DECISIONS.md` | 220 | `c4bf69da8834` |
| `Dispatch_Corrections/docs/EXTERNAL_ACTIVATION.md` | 133 | `a2b86fc90db7` |
| `Dispatch_Corrections/docs/IMPLEMENTATION_SUMMARY.md` | 99 | `7d290f65eb65` |
| `Dispatch_Corrections/docs/JOE_IMPLEMENTATION.md` | 155 | `883ae710b074` |
| `KNOWN_LIMITATIONS.md` | 110 | `5e6c215b08f0` |
| `MERGE_PLAN.md` | 123 | `78d5a077d523` |
| `Dispatch_Corrections/docs/MIGRATION_PLAN.md` | 155 | `a03ffdc9f9c2` |
| `Dispatch_Corrections/docs/ROLLBACK_PLAN.md` | 147 | `d8443f90c1cd` |
| `Dispatch_Corrections/docs/SECURITY_FINDINGS.md` | 157 | `a121f689c470` |
| `Dispatch_Corrections/docs/VERIFICATION_PLAN.md` | 87 | `1b6d406154f6` |
| `Dispatch_Corrections/docs/WORKER_CONTRACTS.md` | 162 | `fb9bfaa88c7e` |

**`Dispatch_Corrections/evidence/`** — The sixteen completion-evidence items, run

| File | Lines | sha256 |
|---|---:|---|
| `Dispatch_Corrections/evidence/COMPLETION_EVIDENCE.json` | 176 | `e8084a95b25a` |
| `Dispatch_Corrections/evidence/COMPLETION_EVIDENCE.md` | 270 | `a1cf30be643f` |

**`Dispatch_Corrections/collect_evidence.py`** — The script that produced the evidence

| File | Lines | sha256 |
|---|---:|---|
| `Dispatch_Corrections/collect_evidence.py` | 516 | `f348edbc998c` |

**`Dispatch_Corrections/README.md`** — Where to start

| File | Lines | sha256 |
|---|---:|---|
| `Dispatch_Corrections/README.md` | 75 | `663f8876e9cf` |

**`Governance/`** — Canonical governance, drift detection, pointers

| File | Lines | sha256 |
|---|---:|---|
| `Governance/GOVERNANCE_REGISTRY.json` | 301 | `39585525389c` |
| `Governance/GOVERNANCE_RESOLUTION_v1.md` | 182 | `6b51fa22fbb1` |
| `Governance/dispatch_governance/__init__.py` | 41 | `cd2083f96fc6` |
| `Governance/dispatch_governance/__main__.py` | 3 | `214038c12d80` |
| `Governance/dispatch_governance/cli.py` | 103 | `7b70c03328cf` |
| `Governance/dispatch_governance/drift.py` | 176 | `539dede11992` |
| `Governance/dispatch_governance/registry.py` | 205 | `588f62c879bf` |
| `Governance/pointers/Claude-GOVERNANCE.md` | 54 | `3317b7ca5005` |
| `Governance/pointers/Joe-Assistant-GOVERNANCE.md` | 55 | `8344b284dff7` |
| `Governance/pointers/Publisher-GOVERNANCE.md` | 54 | `ef15bacfb63a` |
| `Governance/tests/test_governance.py` | 281 | `f9f7fda22607` |
| `Governance/tools/record_registry.py` | 223 | `2db505f55780` |
| `Governance/tools/write_pointers.py` | 144 | `b5f0029de465` |

**`Workers/`** — Bounded worker contracts, mediator, audit

| File | Lines | sha256 |
|---|---:|---|
| `Workers/tests/test_worker_bus.py` | 371 | `f4136c54bc20` |
| `Workers/worker_bus/audit.py` | 99 | `6e3fbe59bb40` |
| `Workers/worker_bus/bus.py` | 270 | `cdd29c1815c4` |
| `Workers/worker_bus/contracts.py` | 210 | `d3a33cbad552` |
| `Workers/worker_bus/workers/__init__.py` | 15 | `5005f139de1b` |
| `Workers/worker_bus/workers/intelligence.py` | 185 | `c9a0da10df88` |
| `Workers/worker_bus/workers/joe.py` | 153 | `ec65fd85c24a` |
| `Workers/worker_bus/workers/library.py` | 92 | `6d46185a36e5` |
| `Workers/worker_bus/workers/publisher.py` | 199 | `e8d3e5805b32` |

**`Assistant_Plugin/conversation/`** — Joe: retrieval, read-back, reasoning, capture, session

| File | Lines | sha256 |
|---|---:|---|
| `Assistant_Plugin/conversation/__init__.py` | 15 | `fb671dd0ad77` |
| `Assistant_Plugin/conversation/capture.py` | 138 | `79392aee10c5` |
| `Assistant_Plugin/conversation/mission_record.py` | 142 | `41722281e620` |
| `Assistant_Plugin/conversation/orchestrator.py` | 186 | `f74131c148d8` |
| `Assistant_Plugin/conversation/readback.py` | 234 | `53f5fbcd87f7` |
| `Assistant_Plugin/conversation/session.py` | 193 | `8b1011e87bd5` |

**`Assistant_Plugin/m365/`** — Microsoft 365 behind provider-neutral ports

| File | Lines | sha256 |
|---|---:|---|
| `Assistant_Plugin/m365/__init__.py` | 13 | `c91773b89cec` |
| `Assistant_Plugin/m365/adapters/__init__.py` | 1 | `0fe0a9880427` |
| `Assistant_Plugin/m365/adapters/graph.py` | 423 | `818fc831d091` |
| `Assistant_Plugin/m365/adapters/local.py` | 181 | `521d9d857150` |
| `Assistant_Plugin/m365/graph_client.py` | 235 | `7d3ebeb57438` |
| `Assistant_Plugin/m365/ports.py` | 169 | `28e83c191269` |
| `Assistant_Plugin/m365/registry.py` | 131 | `7acc907c9a98` |

**`Assistant_Plugin/voice/providers.py`** — Which voice this machine actually has

| File | Lines | sha256 |
|---|---:|---|
| `Assistant_Plugin/voice/providers.py` | 212 | `1f2fe53e1cd7` |

**`Assistant_Plugin/tests/test_conversation.py`** — Joe's contracts

| File | Lines | sha256 |
|---|---:|---|
| `Assistant_Plugin/tests/test_conversation.py` | 431 | `59efe3025820` |

**`Assistant_Plugin/tests/test_m365.py`** — The Graph client, adapters and substitutes

| File | Lines | sha256 |
|---|---:|---|
| `Assistant_Plugin/tests/test_m365.py` | 321 | `de06203b5761` |

**`GOVERNANCE.md`** — This repository's pointer to current authority

| File | Lines | sha256 |
|---|---:|---|
| `GOVERNANCE.md` | 55 | `8344b284dff7` |

**`PHASE_2_DELIVERABLE.md`** — The deliverable index

| File | Lines | sha256 |
|---|---:|---|
| `PHASE_2_DELIVERABLE.md` | 82 | `2ff0aa9b32ef` |

**`conftest.py`** — One command runs all three suites

| File | Lines | sha256 |
|---|---:|---|
| `conftest.py` | 35 | `e861f0b54601` |

**`pytest.ini`** — Which suites; which archived copies are not collected

| File | Lines | sha256 |
|---|---:|---|
| `pytest.ini` | 12 | `67aa15de2e98` |

**`docs/M365_ACTIVATION.md`** — What has to be true before Microsoft is LIVE

| File | Lines | sha256 |
|---|---:|---|
| `docs/M365_ACTIVATION.md` | 147 | `103cce10a835` |

## Changed — existing files in the sandbox

| File | Lines | sha256 | Why |
|---|---:|---|---|
| `Assistant_Plugin/app/config.py` | 257 | `bb1c7295ba7c` | Separator portability; cross-platform containment |
| `Assistant_Plugin/tests/test_joe.py` | 3756 | `5dee9f45b3e5` | Tk skips, stated |

## Production patch series — applies to `Dispatch@3c03ab2`

| # | Patch | Lines | sha256 |
|---:|---|---:|---|
| 1 | `0001-Repair-the-operational-proof-path-and-make-it-execut.patch` | 685 | `b7b95490eb32` |
| 2 | `0002-Build-the-schema-once-per-process-wait-for-a-write-l.patch` | 262 | `3b8827a8b2c3` |
| 3 | `0003-Replace-the-dashboard-s-per-load-queries-with-two-ro.patch` | 472 | `572d56154c1a` |
| 4 | `0004-Make-multi-step-service-operations-atomic-and-defer-.patch` | 607 | `21164f9224d9` |
| 5 | `0005-Move-the-PIN-lockout-counters-where-a-transaction-pr.patch` | 730 | `98cbcbe123fe` |
| 6 | `0006-Money-becomes-whole-cents-exactly-everywhere-it-is-a.patch` | 972 | `cde1cf53da71` |
| 7 | `0007-Give-the-operator-a-way-to-take-a-backup-and-to-prov.patch` | 1126 | `cc650bfa995f` |
| 8 | `0008-Put-a-provider-neutral-transport-behind-the-mail-pat.patch` | 2162 | `8e64b8170b89` |
| 9 | `0009-Record-every-outbound-attempt-log-it-and-give-the-lo.patch` | 1415 | `aefd6716b28a` |
| 10 | `0010-Wire-the-capacity-engine-into-production-and-make-ap.patch` | 1645 | `0d6eb971b117` |
| 11 | `0011-Measure-branch-coverage-and-measure-the-launcher.patch` | 133 | `fda98059130c` |
| 12 | `0012-Record-what-governs-this-repository-and-adjudicate-t.patch` | 167 | `599ba7be3e88` |

```bash
git checkout -b dispatch/phase-2-corrections 3c03ab2
git am Dispatch_Corrections/patches/*.patch
python -m pytest -o addopts="" -q        # 4,171 passed
```

## Totals

- **58** files added to the sandbox, **9,357** lines
- **12** patches, **10,376** lines, against `Dispatch@3c03ab2`
- **2** existing sandbox files changed
