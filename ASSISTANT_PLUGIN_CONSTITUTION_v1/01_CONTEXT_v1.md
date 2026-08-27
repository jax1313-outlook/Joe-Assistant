# ASSISTANT PLUGIN CONSTITUTION v1
## Document 1 of 5 — Context

**Subject:** The Level 1 Assistant as a Dispatch Plugin
**Version:** 1.0
**Final authority:** Mike Zachary
**Status:** Doctrine. No code, no integration, no deployment.

---

## 1. What this document set decides

It decides **what the Assistant is**, and therefore what every future piece of
Assistant work is allowed to be.

One sentence carries it:

> **The Assistant is a Dispatch Plugin. Dispatch is the General Contractor,
> the System of Record, and the Operational Authority. The Assistant is a
> specialized staff function.**

Everything else in these five documents is that sentence worked out in enough
detail that it can be applied to a decision nobody has thought of yet.

## 2. Why this needed deciding now

A component that is not told what it is will drift into whatever is convenient.

The Assistant is the most useful-feeling part of the operation. It answers
things. It finds things. It remembers things. That usefulness is precisely the
risk: the easier it is to ask the Assistant, the more likely it becomes the
place people actually look — and the moment that happens it has become the
system of record in practice, whatever any document says.

That drift does not announce itself. Nobody decides to hand authority to a
helper. It happens one convenient shortcut at a time, and it is discovered
during a dispute, when two systems disagree about a rate and nobody can say
which one is right.

This doctrine exists to make that outcome structurally impossible rather than
merely discouraged.

## 3. The staff/line distinction

"Specialized staff function" is not decoration. It is the whole model, borrowed
from organizational doctrine that has been tested for a very long time.

| | Line authority | Staff function |
| --- | --- | --- |
| Holds | command | expertise |
| Does | decides, orders, owns the outcome | researches, prepares, advises |
| Answerable for | the result | the quality of the preparation |
| In this operation | **Dispatch**, under Mike Zachary | **the Assistant** |

A staff officer can be more knowledgeable than the commander on a given subject.
That does not give the staff officer command. The value of a staff function
comes entirely from the fact that it does **not** command — it can look at a
problem without owning the outcome, which is what lets it be candid.

A staff function that starts issuing orders destroys the chain of command **and**
loses the thing that made it useful. Both failures at once.

The Assistant has expertise authority. It has no command authority. That is not
a limitation on a good idea. It is what makes the idea work.

## 4. What the Assistant is for

**Reducing owner/operator cognitive load.**

Mike Zachary is a driver and an owner. The scarcest resources in this operation
are his time and his attention. The Assistant exists to spend less of both.

It does that by carrying the work that *surrounds* a decision:

- finding what is already known
- reading what arrived
- assembling what is relevant
- laying out the options and what is uncertain about each
- drafting what would have to be written
- watching for what changed
- holding what would otherwise have to be remembered

And then handing all of it to Mike, who decides.

### The distinction that matters most

**Carry the preparation. Never carry the decision.**

Removing decisions from Mike would not be reducing his cognitive load. It would
be replacing his authority — which is prohibited, and which is a different thing
wearing the same clothes.

A capability that removes a decision from Mike has failed, no matter how much
time it appears to save. A capability that makes a decision take four seconds
instead of forty minutes has succeeded.

## 5. What "plugin" means here

Not a metaphor. Three concrete properties:

**1. Dispatch is complete without it.**
Dispatch is a finished thing. The Assistant attaches to it. Removing the
Assistant returns Dispatch to a complete, working state — not a broken one with
a hole in it.

**2. The dependency runs one way.**
The Assistant depends on Dispatch. Dispatch does not depend on the Assistant,
does not know it exists, and is never held back waiting for it.

**3. Contact happens only through controlled interfaces.**
No shared database. No shared files. No back doors. No ambient access. A named,
published, enumerated surface, and nothing else.

## 6. The removability test

This is the sharpest instrument in the whole doctrine, and it is worth stating
here because everything else follows from it:

> **If the Assistant plugin were deleted tomorrow, would Dispatch still work?**

If the answer is anything other than an immediate yes, the capability under
discussion does not belong in the Assistant.

It is not a thought experiment. It is the acceptance test for every future piece
of Assistant work, and it is defined precisely in Document 2, section 4.

## 7. What this changes about work already done

The six Assistant workstreams already built — UI, Memory, Library, Outlook,
Research, Voice — were built as isolated bounded components with no integration.
That was correct and remains correct.

This doctrine reclassifies them. They are not six pieces of a future Assistant
system that will eventually be woven into Dispatch. They are **plugin
components**, and they are to be designed, reviewed, and extended on that
assumption from here forward.

Three specific consequences, stated now so they are not discovered later:

- **Assistant Memory must never become the system of record.** It holds
  temporary interaction records that expire. It does not hold operational truth,
  and the moment anyone looks to it to settle a question about a load, something
  has gone wrong. Its existing doctrine — records expire, nothing is promoted,
  nothing is routed anywhere — is exactly right and must be preserved.
- **Assistant Outlook and Assistant Library being read-only is not a v1
  shortcut.** It is doctrine. Read-only is what a staff function gets.
- **Assistant Research recommending but never approving is not a v1 shortcut
  either.** It is the staff/line distinction in code, and the mechanical
  enforcement already built there is the model for how the rest of this doctrine
  should be enforced everywhere.

None of these components requires modification because of this document. They
were built conservatively enough to be governed by it. That is the point of
having built them conservatively.

## 8. What this document set does not do

- It does not integrate anything.
- It does not specify any interface in technical detail. Document 3 says what
  the properties of a controlled interface must be; it does not name endpoints.
- It does not authorize any deployment.
- It does not modify Dispatch, or say anything about what Dispatch should do
  internally. Dispatch doctrine is Dispatch's own.
- It does not decide anything Mike Zachary has not decided. Where this document
  goes beyond the stated mission, it is working out consequences, not adding
  authority — and every such consequence is marked in Document 4, section 7, so
  it can be overruled deliberately.

## 9. Reading order

| Document | Answers |
| --- | --- |
| **1 — Context** (this) | What is the Assistant, and why does that need deciding? |
| **2 — Constitution** | What may it do, what may it never do, and how is that enforced? |
| **3 — Architecture** | What shape must plugin work take? |
| **4 — Governance** | Who decides, how does this change, what happens on a breach? |
| **5 — Repository Recommendation** | Where should the code live, and why? |

Mike Zachary remains final authority over all five.
