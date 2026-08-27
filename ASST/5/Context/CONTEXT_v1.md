# Workstream 5 - Assistant Research - Context

**Component:** Assistant Research
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\5`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

Analysis over supplied sources. It produces:

- **findings** - what the sources say about each topic
- **confidence** - how well supported each finding is, by count
- **uncertainties** - what is *not* known, stated for every finding
- **recommendations** - what might be worth doing
- **source reporting** - where every statement came from, and what standing it has

## The boundary that defines it

**Research may recommend. Research may not approve, may not decide, and may not
alter doctrine.**

That is not a policy note in a document. It is mechanical:

- A `Recommendation` carries `approved=False`, `decided=False`, `acted_on=False`,
  `doctrine_changed=False`. There is no code path that reports them otherwise -
  even setting the attributes by hand does not change the reported record.
- A recommendation whose wording claims a decision is **refused at
  construction**, not softened. Thirty-plus phrases - `I approve`,
  `the decision is`, `booked the load`, `payment sent`, `this is now policy`,
  `email sent` - raise `AuthorityError`.
- Every finding and every record reports `is_approved_doctrine: False` and
  `is_a_decision: False`.
- Every recommendation names who the decision belongs to: Mike Zachary.

## The most important limitation, stated first

**This component does not fetch anything.** No web search, no browsing, no
downloads, no network access at all. It imports no networking module.

Sources are **supplied** to it as JSON. It reads what it is given, analyses it,
and reports it with origins attached. Discovering sources is a different job and
is **NOT IMPLEMENTED** here.

So the analysis is real and tested. Where the sources come from is somebody
else's problem, on purpose - it keeps this component reviewable and keeps it
from quietly becoming a web client.

## How confidence is decided

Counting, not judgement:

| Supporting | Contradicting | Confidence |
| --- | --- | --- |
| 2 or more | 0 | `CONFIRMED` |
| 1 | 0 | `SUPPORTED` |
| 1 or more | 1 or more | `CONTESTED` |
| 0 | 1 or more | `CONTRADICTED` |
| 0 | 0 | `UNSUPPORTED` |

A reviewer can predict any result by counting the claims.

**Approved company material does not win a contest automatically.** It has
higher *standing* - it is reported as approved company material while a public
source is reported as "not approved company truth" - but disagreement stays
disagreement. A company document and a broker's phone call that conflict produce
`CONTESTED`, not a quiet win for the document. There is a test for exactly this.

## Uncertainty is never blank

Every finding states what is not known, in plain words:

- contested → "Sources disagree. 1 support, 1 contradict. This is not settled
  and should not be treated as settled."
- single source → "Rests on a single source. A second source has not been
  supplied, so agreement has not been established."
- agreement with no company backing → "Sources agree, but none is approved
  company material. Research is not doctrine."
- nothing said → "No supplied source speaks to this. Nothing is known either
  way."

A finding with an empty uncertainty field would be the component claiming more
than it knows. That cannot happen; a test asserts every finding has one.

## Source standing

| Kind | Reported as |
| --- | --- |
| `company` | approved company material |
| `operational` | operational record |
| `public` | public source, **not approved company truth** |
| `personal` | stated by a person, unverified |
| `unknown` | origin not recorded |

Only `company` returns `is_approved_company_truth: True`. No number of agreeing
public sources changes that. **Research is not doctrine**, however well
supported.

## What it deliberately is not

- no fetching, browsing, searching, or downloading
- no approval, decision, or doctrine authority
- no accepting or dispatching loads, and no committing money
- no sending anything
- no retention or memory between runs
- no library, email, calendar, or voice
- no user interface beyond the command line

## Runtime

Python 3.10 or newer through the `py` launcher. Verified on this machine:
Python 3.14.5. Standard library only. Nothing is installed.

## Relationship to other workstreams

None. This folder does not know any other workstream exists. It imports nothing
from folders 1, 2, 3, 4, or 6.
