# Workstream 5 - Assistant Research - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\5`

---

## Read this first

**This does not go and find anything.** No web search, no browsing, no
downloads, no network access at all.

You give it sources. It tells you what they say, how well supported each point
is, what is *not* known, and what might be worth doing. Where the sources come
from is not this component's job.

## What it gives you

For every topic your sources touch:

- **the finding** - what they say, both for and against
- **the confidence** - by count, not opinion
- **the uncertainty** - what is still not known, always stated
- **the citations** - where each statement came from and what standing it has
- **a recommendation** - if one was supplied, clearly labelled as a
  recommendation and referred to you for the decision

## The command

```bash
D:\SANDBOX\Assistan_Building\ASST\5\Source\research.cmd brief ..\Data\brief_northbound_lane.json
```

## Run the sample

```bash
research.cmd brief ..\Data\brief_northbound_lane.json
```

That produces a full record. From the sample data:

```
  lane clears the recorded floor
    confidence:  CONFIRMED  (two or more sources agree and none contradict)
    supports:    The recorded floor for this lane is 2.35 per mile.
                 - Rate Floor Policy (Company Library, ...)  [approved company material]
    supports:    Twelve-week average on this lane was 2.48 per mile.
                 - Internal lane history (Load records, ...)  [operational record]

  volume is steady enough to dedicate
    confidence:  CONTESTED  (sources disagree; both sides are recorded below)
    supports:    Loads were available in 11 of the last 12 weeks.
    CONTRADICTS: Corridor volume declined 9 percent quarter over quarter.
    uncertainty: Sources disagree. 1 support, 1 contradict. This is not settled.
```

The contested one is the useful one. It did not quietly pick a side.

## Just the uncertainties

```bash
research.cmd uncertainties ..\Data\brief_northbound_lane.json
```

## Just the sources and their standing

```bash
research.cmd sources ..\Data\sources_rate_floor.json
```

Shows each source, what standing it has, and whether it counts as approved
company truth.

## Analyze a bare source file

```bash
research.cmd analyze ..\Data\sources_rate_floor.json --question "Should we hold the floor?"
```

## How confidence is decided

| Sources supporting | Sources contradicting | Confidence |
| --- | --- | --- |
| 2 or more | none | `CONFIRMED` |
| 1 | none | `SUPPORTED` |
| any | 1 or more | `CONTESTED` |
| none | 1 or more | `CONTRADICTED` |
| none | none | `UNSUPPORTED` |

That is the whole rule. You can predict any result by counting.

**Company material does not automatically win.** A Company Library document
contradicted by a broker's phone call comes out `CONTESTED`, not settled. The
document is reported with higher standing, but a disagreement stays a
disagreement. That is on purpose.

## Check whether wording crosses the line

```bash
research.cmd check "Recommend a four week trial, then review."
```

```bash
research.cmd check "I approve the lane and have booked the load."
```

The second one comes back:

```
  RESULT   REFUSED
  reason   claims authority research does not have
             found: "i approve"
             found: "booked the load"
```

Research may recommend. It may not approve, decide, or change doctrine. Wording
that claims otherwise is **refused**, not quietly reworded.

## See the authority boundary

```bash
research.cmd authority
```

```
  may_recommend                    True
  may_approve                      False
  may_decide                       False
  may_alter_doctrine               False
  may_accept_or_dispatch_loads     False
  may_commit_money                 False
  may_send_communications          False
  has_network_access               False
  fetches_sources                  False
  final_authority                  Mike Zachary
```

## Writing your own brief

A brief is a JSON file:

```json
{
  "question": "...",
  "scope": "...",
  "sources": [
    {
      "source_id": "SRC-001",
      "title": "...",
      "kind": "company | operational | public | personal | unknown",
      "origin": "...",
      "retrieved_at": "2026-08-20T10:00:00Z",
      "claims": [
        { "topic": "...", "statement": "...", "supports": true }
      ]
    }
  ],
  "recommendation": {
    "statement": "...",
    "rationale": "...",
    "open_questions": ["..."]
  }
}
```

Set `"supports": false` on a claim that argues **against** the topic. Those are
never dropped - they are what produces a `CONTESTED` finding.

The `kind` matters. Only `company` is reported as approved company truth.

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\5\Tests\run_tests.cmd
```

78 tests.

## What this will NOT do - read this part

**It will not approve anything.** Not a rate, not a lane, not a load.

**It will not decide anything.** Every recommendation says
`approved=False decided=False acted_on=False doctrine_changed=False` and names
you as the person who decides.

**It will not change doctrine or policy.**

**It will not go and find sources.** No search, no browsing, no network.

**It will not treat research as company truth.** Even five agreeing public
sources produce an uncertainty line reading "Research is not doctrine."

**It will not hide a disagreement.** Contradicting evidence is always shown.

**It will not remember anything.** Nothing is stored between runs.

## If something goes wrong

**`py was not found`** — install Python 3.10 or newer from python.org. `python`
on this machine is the Microsoft Store stub, which is why everything uses `py`.

**`ERROR: file not found`** — check the path. Bare filenames are also looked up
in `ASST\5\Data`.

**`ERROR: malformed JSON in ...`** — the brief is broken. This is deliberate: it
refuses to report "no findings" from a file it could not read, because that
would read as "nothing was found".

**`REFUSED: research may recommend but may not approve...`** — the
recommendation in your brief claims a decision. Reword it as a recommendation.

**A topic shows `UNSUPPORTED`** — no source made a claim with that exact topic
string. Topics match exactly; there is no synonym matching.
