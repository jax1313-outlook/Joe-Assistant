# Dispatch Agent Integration Map

**Mission:** BOOTSTRAP THE DISPATCH COPILOT AGENT, §10.B
**Status:** **INCOMPLETE — BLOCKED.** The Dispatch columns cannot be filled.
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

---

## Why this document is incomplete, and what that means

§10.B requires, for every Dispatch service: the owning module, the source of
truth, the existing interface, and the current implementation status. §5
requires file paths, symbols, tests, and proof for every classification.

**The authoritative Dispatch repository is not available to this workspace.**
Mike confirmed this on 2026-08-25. Re-checked today: no Dispatch tree has
appeared, and no card symbols exist anywhere reachable.

**Every Dispatch-side classification is therefore `NOT ASSESSED`, which is not
the same as `NOT FOUND`.** The prior mission's correction applies with full
force: absence of evidence in a workspace that was never given the repository is
not evidence of absence.

What follows is **the Joe side of each row, which is knowable**, and the shape
of the question to ask of Dispatch once it is available. It is a scaffold, and
it is labelled as one.

---

## 1. The map — Joe side known, Dispatch side blocked

Legend: **Joe capability** is real and measured. **Dispatch** columns are the
questions to answer, not answers.

### Retrieval

| Dispatch service | Joe capability that would use it | Joe's evidence | Required adapter | Authority | Dispatch status |
| --- | --- | --- | --- | --- | --- |
| Opportunity Card | card retrieval and read-back | none — Joe has no card model | Card Read (Contract A) | INFORM | **NOT ASSESSED** |
| Mission Card Engine | "what is my current mission" | none | Card Read | INFORM | **NOT ASSESSED** |
| Current Mission Resolver | resolving "this load", "the current run" | `app/router.py` subject extraction, 228 loc | Card Resolution (Contract B) | INFORM | **NOT ASSESSED** |
| Calendar | date-filtered schedule answers | **proven** — `adapters/outlook_com.py`, chronological, recurrences expanded, proof 10/19 | ownership decision needed: Outlook or Dispatch Calendar | INFORM | **NOT ASSESSED** |
| Library | document retrieval and explanation | **proven** — `adapters/library_fs.py`, 34 documents indexed | Librarian interface; Joe's own index becomes legacy | INFORM | **NOT ASSESSED** |
| Archive | historical retrieval | none | Archive read interface | INFORM | **NOT ASSESSED** |

### Explanation

| Dispatch service | Joe capability | Joe's evidence | Authority | Dispatch status |
| --- | --- | --- | --- | --- |
| Config Review results | explain a pass/warning/fail and its limiting factor | `_handle_explain`, six reasoning modes, mode contract enforced in the governance gate | REVIEW to trigger, INFORM to explain | **NOT ASSESSED** |
| Score changes | explain why a score moved | none | INFORM | **NOT ASSESSED** |
| Route Risk findings | explain a risk event | `ROUTE_RISK_EVENT` source class **defined and produced by nothing** | INFORM | **NOT ASSESSED** |
| Alert Cards | announce an alert in plain language | alert voice doctrine specified, **not implemented** | INFORM | **NOT ASSESSED** |
| Mission status | summarise where a mission stands | `_handle_summarize` | INFORM | **NOT ASSESSED** |

### Drafting

| Dispatch service | Joe capability | Joe's evidence | Authority | Dispatch status |
| --- | --- | --- | --- | --- |
| Publisher requests | request a packet from current card state | `_handle_draft`, always marked DRAFT ONLY / NOT SENT | DRAFT | **NOT ASSESSED** |
| Communications | draft a broker email | same | DRAFT | **NOT ASSESSED** |
| Packet production | trigger production | none | EXECUTE — **see conflict C-1** | **NOT ASSESSED** |

### Monitoring

| Dispatch service | Joe capability | Joe's evidence | Authority | Dispatch status |
| --- | --- | --- | --- | --- |
| Dispatch health | report observable condition | `CapabilityStatus` with the LIVE / READY / UNKNOWN vocabulary — **directly reusable** | INFORM | **NOT ASSESSED** |
| Plugin condition | report which plugins are degraded | same pattern | INFORM | **NOT ASSESSED** |
| Publisher status | report production failures | none | INFORM | **NOT ASSESSED** |
| Outlook transport status | report delivery failures | read-side proven; transport is Dispatch-owned | INFORM | **NOT ASSESSED** |
| Active alerts | report waiting alerts | none | INFORM | **NOT ASSESSED** |
| Failed handoffs | report stalled workflows | none | INFORM | **NOT ASSESSED** |

**Joe's status vocabulary is the strongest reusable asset in this whole table.**
`LIVE` means a real service answered; `READY` means reachable but not yet used;
`UNKNOWN` never collapses into absent; a timeout is never cached as absence.
That discipline is exactly what Job 2 (Systems Monitor) requires, and it already
exists and is tested.

### Execution

| Dispatch service | Joe capability | Joe's evidence | Authority | Dispatch status |
| --- | --- | --- | --- | --- |
| Validated service calls | request a bounded workflow | **none — no execute path exists anywhere in Joe** | EXECUTE | **NOT ASSESSED** |
| Authorized card changes | update a card field | none | EXECUTE + card resolution + old-value match | **NOT ASSESSED** |
| Publisher production | regenerate from current card | none | EXECUTE | **NOT ASSESSED** |
| Outlook send | transmit an approved packet | **none, deliberately** — 21 write calls refused, `WRITE_AUTHORITY = "none"` | EXECUTE | **NOT ASSESSED** |
| Transaction record | record what happened | `app/logbook.py`, 46 loc, **0 tests** | — | **NOT ASSESSED** |

---

## 2. Failure behaviour — the one column Joe can already fill

This is Joe's strongest existing discipline and it should govern every row above.

| Failure | Required behaviour | Already implemented |
| --- | --- | --- |
| Dispatch unreachable | report **UNKNOWN**, never "no cards" | the pattern exists — `MailboxRegistry._failed`, `knows_account` tri-state |
| A read times out | unknown, and **never cached as absence** | yes, and tested |
| A card does not resolve | say so; never invent a card | pattern exists in mailbox lookup |
| Many cards match | ask which; never guess | not implemented |
| A workflow fails | report the exact failure, never a predicted success | `_reasoned` reports provider failure honestly |
| One service fails | the others keep working | proven — per-mailbox failure isolation |

---

## 3. What must be true before this document can be completed

1. The authoritative Dispatch repository is made available for review
2. Its card schema, service interfaces, and plugin lifecycle are readable
3. Its Transaction Log — or the confirmation that none exists — is established

Until then every Dispatch column stays `NOT ASSESSED`, and **no build work
should assume any of them.**

---

Mike Zachary remains final authority.
