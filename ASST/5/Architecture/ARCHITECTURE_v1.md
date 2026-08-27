# Workstream 5 - Assistant Research - Architecture

**Component:** Assistant Research
**Version:** 1.0.0

---

## 1. Shape

```
                    +---------------------------+
                    |          cli.py           |  operator surface
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |         record.py         |  assembles and renders
                    |  ResearchRecord           |
                    +----+---------------+------+
                         |               |
                         v               v
              +----------------+  +------------------+
              |  analysis.py   |  |   authority.py   |
              |  findings,     |  |  the boundary:   |
              |  confidence,   |  |  recommend only  |
              |  uncertainty   |  |  refuse claims   |
              +--------+-------+  +------------------+
                       |
                       v
              +----------------+
              |   sources.py   |  supplied sources and their claims
              +----------------+
```

`authority.py` sits beside the analysis rather than under it, because the
boundary applies to anything the component says, not just to findings.

## 2. Modules

| Module | Responsibility | Tests |
| --- | --- | --- |
| `sources.py` | `Source`, `Claim`, `SourceKind`, standing, citations. Frozen dataclasses. | 12 |
| `analysis.py` | `Finding`, `Confidence`, the counting rule, uncertainty text. | 18 |
| `authority.py` | `Recommendation`, `FORBIDDEN_PHRASES`, refusal. | 16 |
| `record.py` | `ResearchRecord`: assembly, reporting, rendering, input loading. | 24 |
| `cli.py` | `brief`, `analyze`, `sources`, `topics`, `uncertainties`, `check`, `authority`. | exercised manually |

**Third-party dependencies: zero.** Imports: `__future__`, `argparse`,
`dataclasses`, `datetime`, `json`, `os`, `pathlib`, `re`, `sys`.

No `requests`, no `urllib`, no `httpx`, no `bs4`, no `selenium`. A research
component that cannot fetch should not be able to construct a request either.

## 3. The confidence rule, in full

```
    supporting >= 2  and  contradicting == 0   ->  CONFIRMED
    supporting == 1  and  contradicting == 0   ->  SUPPORTED
    supporting >= 1  and  contradicting >= 1   ->  CONTESTED
    supporting == 0  and  contradicting >= 1   ->  CONTRADICTED
    supporting == 0  and  contradicting == 0   ->  UNSUPPORTED
```

Counting, not weighing. Any result can be predicted by reading the claims.

**Source standing is deliberately not in this rule.** Approved company material
is reported with higher standing but does not outvote anything. A company
document contradicted by a phone call is `CONTESTED`. Letting standing settle
contests would mean a disagreement could disappear from the report because one
side had a better label - which is exactly the failure a research component
exists to prevent.

## 4. Uncertainty text

Chosen by confidence level, never blank:

| Confidence | Uncertainty says |
| --- | --- |
| `CONTESTED` | how many on each side, and that it is not settled |
| `CONTRADICTED` | everything supplied contradicts it |
| `UNSUPPORTED` | nothing supplied speaks to it |
| `SUPPORTED` | rests on a single source; agreement not established |
| `CONFIRMED`, no company backing | sources agree, but research is not doctrine |
| `CONFIRMED`, with company backing | sources agree, no unresolved conflict |

## 5. The authority boundary, mechanically

```
  Recommendation(statement=..., rationale=...)
        |
        +-- statement empty?                    ->  AuthorityError
        |
        +-- statement contains a forbidden phrase?  ->  AuthorityError
        +-- rationale contains one?                 ->  AuthorityError
        |
        +-- construct, with:
                is_recommendation_only = True
                approved               = False
                decided                = False
                acted_on               = False
                doctrine_changed       = False
```

`to_dict()` emits those four values as **literals**, not from the attributes.
Someone who sets `rec.approved = True` still gets `approved: False` in the
reported record. That is deliberate: the reported record is the thing that
travels, so the reported record is the thing that must be honest.

Refusal covers three families of claim:

| Family | Examples |
| --- | --- |
| approval / decision | `i approve`, `the decision is`, `i authorize`, `is approved` |
| completed action | `booked the load`, `load accepted`, `i dispatched`, `payment sent`, `email sent` |
| doctrine change | `this is now policy`, `doctrine is updated`, `policy is changed` |

The `RECOMMENDING_PHRASES` list works the other way: its absence is *reported*
as `uses_recommending_language: False`, not refused. Phrasing is not always the
author's choice, so a weak signal is surfaced rather than blocked.

## 6. The research record

```
  question
  scope
  sources[]        -> id, title, kind, standing, origin, retrieved_at, claims, citation
  findings[]       -> topic, confidence, supporting[], contradicting[], uncertainty
  uncertainties[]  -> one per finding, never empty
  citations[]      -> deduplicated, in source order
  recommendation   -> statement, rationale, open questions, fixed flags
  is_approved_doctrine: False
  is_a_decision: False
  decision_required_from: "Mike Zachary"
```

`render()` produces the readable report: findings with both sides shown,
contradictions marked `CONTRADICTS`, findings without company backing marked,
uncertainties in their own section, and the recommendation followed by
`approved=False  decided=False  acted_on=False  doctrine_changed=False`.

## 7. Input

Two supplied shapes, both read-only JSON:

- **a brief** - `{question, scope, topics?, sources[], recommendation?}`
- **a source file** - a JSON list of sources

| Situation | Behavior |
| --- | --- |
| File missing | `RecordError` |
| Malformed JSON | `RecordError` naming the file |
| Wrong top-level type | `RecordError` |
| Bad source inside | `RecordError` naming the file |
| Recommendation claims authority | `AuthorityError` - the brief is refused |

Malformed input raises rather than yielding an empty analysis. Reporting "no
findings" from a file that failed to parse would read as "nothing was found",
which is a different and much more dangerous statement.

## 8. What was deliberately left out

- **Fetching, browsing, and search.** Discovering sources is a separate job. Put
  in here it would make this component a web client with an analysis feature.
- **Natural-language claim extraction.** Claims are supplied as structured
  topic/statement/supports triples. Extracting them from prose would need a
  model and would make every finding unreviewable.
- **Source reliability weighting.** Standing is reported; it does not score. See
  section 3.
- **Topic clustering or synonym matching.** Topics match exactly, so a reviewer
  can see why two claims landed together.
- **Any persistence.** Nothing is stored between runs.
