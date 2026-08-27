# Workstream 5 - Assistant Research - Build Report

**Component:** Assistant Research
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\5`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build research, analysis, findings, recommendations, uncertainties, and source
reporting.

Research may recommend. Research may not approve. Research may not decide.
Research may not alter doctrine.

## FILES CREATED

```
ASST\5\
  README.md                                       reviewer entry point
  BUILD_REPORT_v1.md                              this file
  TEST_REPORT_v1.md                               full test results
  Context\CONTEXT_v1.md                           what this is and the boundary
  Constitution\CONSTITUTION_v1.md                 binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md                 confidence rule, authority mechanics
  Operator_Guide\OPERATOR_GUIDE_v1.md             how Mike runs it
  Source\research.cmd                             launcher
  Source\assistant_research\__init__.py           package exports
  Source\assistant_research\__main__.py           py -m assistant_research entry
  Source\assistant_research\sources.py            sources, claims, standing, citations
  Source\assistant_research\analysis.py           findings, confidence, uncertainty
  Source\assistant_research\authority.py          the recommend-only boundary
  Source\assistant_research\record.py             record assembly, rendering, input
  Source\assistant_research\cli.py                operator interface
  Data\README_DATA.md                             what the sample input is and is not
  Data\brief_northbound_lane.json                 sample brief, 3 sources, 3 topics
  Data\sources_rate_floor.json                    sample source file, contested topic
  Tests\run_tests.cmd                             test launcher
  Tests\test_assistant_research.py                78 tests
  Tests\_last_test_run.txt                        raw output of the last run
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\5\Tests\run_tests.cmd
py -m assistant_research brief ../Data/brief_northbound_lane.json
py -m assistant_research check "Recommend a four week trial, then review."
py -m assistant_research check "I approve the lane and have booked the load."
```

## TEST RESULTS

**78 tests. 78 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestSources` | 12 |
| `TestAnalysis` | 18 |
| `TestAuthority` | 16 |
| `TestRecord` | 17 |
| `TestRecordEdges` | 7 |
| `TestBoundaries` | 8 |

Live operator run against the sample brief:

```
  lane clears the recorded floor        CONFIRMED   company + operational
  volume is steady enough to dedicate   CONTESTED   1 support, 1 contradict
  deadhead is acceptable                SUPPORTED   public only, flagged
```

Every finding carried an uncertainty. The public-only finding was marked
"no approved company material supports this."

```
check "Recommend a four week trial, then review."      -> allowed
check "I approve the lane and have booked the load."   -> REFUSED
                                    found: "i approve", "booked the load"
```

Detail in `TEST_REPORT_v1.md`.

## PROVEN CAPABILITIES

1. Reads supplied sources with kind, origin, retrieval time, and claims.
2. Reports source standing, distinguishing approved company material from public
   and personal sources.
3. Reports only `company` sources as approved company truth.
4. Produces a finding per topic from supporting and contradicting claims.
5. Assigns confidence by the stated counting rule, across all five levels.
6. Keeps contradicting evidence and reports both sides of a contested topic.
7. Does not let source standing settle a disagreement.
8. States an uncertainty for every finding, at every confidence level.
9. Flags findings resting only on public or personal sources.
10. Flags findings backed by approved company material.
11. Collects deduplicated citations.
12. Counts sources by kind.
13. Refuses recommendation wording that claims approval.
14. Refuses wording that claims a completed action.
15. Refuses wording that claims a doctrine or policy change.
16. Checks the rationale as well as the statement.
17. Reports the four authority flags as `False` even when set otherwise.
18. Names Mike Zachary as the decision holder on every recommendation.
19. Reports `is_approved_doctrine: False` and `is_a_decision: False` throughout.
20. Renders a readable report showing contradictions and undecided status.
21. Raises on missing, malformed, or wrongly typed input, naming the file.
22. Refuses a supplied brief whose recommendation claims authority.
23. Contains no fetch, browse, or network capability.
24. Contains no write call and changes nothing on disk.
25. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. The CLI. Exercised by hand, not by the automated suite.
2. The `ASSISTANT_RESEARCH_DATA` environment override.
3. The `topics` field in a brief, including topics no source mentions.
4. `uses_recommending_language`. Computed and reported; nothing acts on it.
5. Sources with no `retrieved_at`. Allowed; only the with-date path is asserted.
6. Behavior with many sources or topics. Largest test set is three and three.
7. Non-ASCII source text.

## NOT IMPLEMENTED

1. Any fetching, browsing, searching, or downloading. No network access.
2. Natural-language claim extraction. Claims are supplied structured.
3. Any approval, decision, or doctrine-setting capability.
4. Accepting or dispatching loads; committing money.
5. Sending any communication.
6. Source reliability scoring or weighting.
7. Topic clustering, synonym matching, or fuzzy topic matching.
8. Any retention or memory between runs.
9. Any library, email, calendar, or voice capability.
10. Any user interface. Command line only.
11. Report export to any document format.

## KNOWN LIMITATIONS

1. **It cannot find sources.** Everything depends on what is supplied. A
   one-sided source set produces a confident-looking `CONFIRMED` that is only as
   good as the sourcing.
2. Topics match exactly. "rate floor" and "rate floors" are different topics.
3. The confidence rule counts sources, not quality. Two weak sources agreeing
   produce `CONFIRMED`; the uncertainty line names the standing, but the count
   is the count.
4. Refusal is phrase-based. Wording that claims authority using phrasing not on
   the list will pass.
5. `supports` is binary. Partial agreement must be entered as one or the other.
6. Everything is UTC.
7. Verified on Windows 11, Python 3.14.5 only.
8. A recommendation is still only a recommendation. The decision stays with
   Mike Zachary.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. The component ships with two sample
briefs, so every command and every test runs with no network and no setup.

**The authority boundary is mechanical, not a promise.** This is the piece to
check. Four independent mechanisms:

- `Recommendation.to_dict()` emits `approved`, `decided`, `acted_on`, and
  `doctrine_changed` as **literals**, not from the attributes. A test sets all
  three to `True` by hand and asserts the reported record still says `False` -
  because the reported record is the thing that travels, so it is the thing that
  must be honest.
- Wording that claims a decision, a completed action, or a doctrine change
  **raises at construction**. Thirty-plus phrases, checked against both the
  statement and the rationale, case-insensitively, and applied to supplied
  briefs as well as objects built in code.
- **Refusal, not softening.** The component does not quietly reword an
  overreaching claim into something acceptable. A reworded claim still reached
  the page once.
- No `approve`, `decide`, `authorize`, `accept_load`, `dispatch`, `commit`,
  `pay`, `send`, `publish`, `set_doctrine`, or `update_policy` method exists.

**The design decision worth your attention: standing does not settle contests.**
Approved company material is reported with higher standing than a public source
or a phone call - but it does not outvote them. A company document contradicted
by a broker's call comes out `CONTESTED`, and there is a test for exactly that.
Letting standing settle disagreements would mean a real conflict could disappear
from the report because one side had a better label. That is precisely the
failure a research component exists to prevent.

**Uncertainty is mandatory and cannot be blank.** Every finding at every
confidence level states what is not known. A finding with an empty uncertainty
would be the component claiming more than it knows.

**Research is never doctrine.** Five agreeing public sources still produce
`CONFIRMED` **plus** an uncertainty line reading "Sources agree, but none is
approved company material. Research is not doctrine."

**It does not fetch, and cannot.** No networking module is imported, and a test
fails the build if `urlopen`, `requests.get`, `fetch(`, `http://`, or `download`
appears anywhere. Source discovery is a separate job; putting it here would make
this a web client with an analysis feature attached.

**Malformed input raises rather than reporting nothing.** "No findings" reads as
"nothing was found", which is a very different and more dangerous statement than
"the file would not parse."

**The honest gap.** This component is only as good as the sources handed to it.
It can tell you a topic rests on one source, or that two sources disagree, or
that nothing supplied is approved company material - but it cannot tell you what
nobody gave it.
