# ASSISTANT_PLUGIN_CONSTITUTION_v1

Doctrine governing all Assistant work.

**Final authority: Mike Zachary.**

---

## The premise

> **The Assistant is a Dispatch Plugin.**
> Dispatch is the General Contractor, the System of Record, and the Operational
> Authority. The Assistant is a specialized staff function.

## The documents

| # | Document | Answers |
| --- | --- | --- |
| 1 | [`01_CONTEXT_v1.md`](01_CONTEXT_v1.md) | What is the Assistant, and why did that need deciding? |
| 2 | [`02_CONSTITUTION_v1.md`](02_CONSTITUTION_v1.md) | What may it do, what may it never do, and how is that enforced? |
| 3 | [`03_ARCHITECTURE_v1.md`](03_ARCHITECTURE_v1.md) | What shape must plugin work take? |
| 4 | [`04_GOVERNANCE_v1.md`](04_GOVERNANCE_v1.md) | Who decides, how does this change, what happens on a breach? |
| 5 | [`05_REPOSITORY_RECOMMENDATION_v1.md`](05_REPOSITORY_RECOMMENDATION_v1.md) | Where should the code live, and why? |

Read in order. Document 2 is the binding one.

## The rules, in short

**The Assistant may:** research, retrieve, summarize, explain, draft,
recommend, monitor, remember.

**The Assistant may not:** approve, own records, alter operational truth,
replace Dispatch authority.

**Its purpose:** reduce owner/operator cognitive load — by carrying the
preparation, never the decision.

## The three tests

Every proposed Assistant capability must pass all three, at design time:

1. **Removability** — would Dispatch still work if this were deleted tomorrow?
2. **Authority** — does it approve, own, alter truth, or stand in for Dispatch?
3. **Load** — does it reduce what Mike must carry, or add to it?

## The line that decides most cases

> **Degradation is permitted. Incapacity is not.**

Removing the Assistant may make things harder, slower, and more tedious. It may
never make anything impossible.

## Status

Doctrine only. No code, no integration, no deployment work was performed.

Nothing already built violates this doctrine, and no migration is proposed by
it.
