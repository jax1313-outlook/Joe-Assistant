# Workstream 5 - Assistant Research - Test Report

**Component:** Assistant Research
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, standard library only

---

## Result

**78 tests. 78 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\5\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_research.py`.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestSources` | 12 | Sources need ids; unknown kinds refused; every kind has a standing; **only company material is approved company truth**; public is never approved truth; claims need topic and statement; claims default to supporting; contradicting claims are kept; bad timestamps raise; citations name title/origin/date; topic ordering; sources are frozen. |
| `TestAnalysis` | 18 | Every branch of the confidence rule; **company material does not win a contest automatically**; every level has a stated meaning; **every finding states an uncertainty**; contested says "not settled"; single-source says so; agreement without company backing says research is not doctrine; company backing is flagged; findings never claim doctrine or decision; citations carried; **contradicting evidence is never dropped**; topic ordering stable; empty input; `is_settled` semantics. |
| `TestAuthority` | 16 | Plain recommendations allowed; **approval language refused**; **action claims refused**; **doctrine-change claims refused**; the rationale is checked too; refusal is case-insensitive; empty refused; flags always false; **flags cannot be flipped in the output**; decision always referred to Mike Zachary; open questions carried; claim detection reports every match; clean text passes; the forbidden list is substantial; the authority statement names the boundary. |
| `TestRecord` | 17 | The sample brief builds; a question is required; confidence assigned per topic; contested and settled listed; every finding produces an uncertainty; citations deduplicated; source kinds counted; company involvement reported; **the record never claims doctrine or decision**; the recommendation is carried and flagged; render states the authority boundary, shows contradictions, marks findings without company backing, and declares the recommendation undecided; standalone source files work; the default data root is this folder. |
| `TestRecordEdges` | 7 | Missing files raise; malformed JSON raises; wrong top-level types raise; a bad source raises **with the filename**; an empty brief still builds and says "No findings"; **a brief containing approval language is refused**. |
| `TestBoundaries` | 8 | No workstream import; no network or vendor import; standard library only; **nothing fetches or browses**; no approval or decision method exists; no write call anywhere; reading changes nothing on disk; research is never reported as doctrine. |

## The authority proofs

Four tests carry the defining rule of this workstream:

1. `test_approval_language_is_refused` - `I approve the lane`,
   `The decision is to run it`, `I authorize the counter`, `This is now policy`
   all raise `AuthorityError` at construction.
2. `test_action_claims_are_refused` - `I have booked the load`,
   `Load accepted at 2.40`, `Email sent to the broker`, `Payment sent this
   morning`, `I dispatched the driver` all raise.
3. `test_flags_cannot_be_flipped_in_the_output` - sets `approved`, `decided`,
   and `doctrine_changed` to `True` by hand, then asserts the reported record
   still says `False`. The record that travels is the record that must be
   honest.
4. `test_a_brief_with_approval_language_is_refused` - the refusal reaches
   supplied input, not just objects built in code.

## The arithmetic proof

`test_company_material_does_not_win_a_contest_automatically` builds a company
source and a personal source that disagree, and asserts the result is
`CONTESTED`. Standing changes how a source is reported; it never settles a
disagreement.

## Operator verification

```
research.cmd brief ..\Data\brief_northbound_lane.json
  -> 3 sources, 3 findings:
       "lane clears the recorded floor"        CONFIRMED  (company + operational)
       "volume is steady enough to dedicate"   CONTESTED  (1 support, 1 contradict)
       "deadhead is acceptable"                SUPPORTED  (public only, flagged)
     every finding carried an uncertainty; the public-only finding was marked
     "no approved company material supports this"

research.cmd check "Recommend a four week trial, then review."
  -> allowed as a recommendation

research.cmd check "I approve the lane and have booked the load."
  -> REFUSED; found: "i approve", "booked the load"
```

## Boundary verification

Imports across the whole package: `__future__`, `argparse`, `dataclasses`,
`datetime`, `json`, `os`, `pathlib`, `re`, `sys`. Nothing else.

Absent by test: `socket`, `urllib`, `http`, `requests`, `httpx`, `ssl`,
`ftplib`, `smtplib`, `selenium`, `bs4`, and every vendor module.
`test_nothing_fetches_or_browses` additionally fails if `urlopen`,
`requests.get`, `fetch(`, `http://`, or `download` appears anywhere in the
source.

---

## PROVEN CAPABILITIES

1. Reads supplied sources with kind, origin, retrieval time, and claims.
2. Reports source standing, distinguishing approved company material from
   public and personal sources.
3. Reports only `company` sources as approved company truth.
4. Produces a finding per topic from supporting and contradicting claims.
5. Assigns confidence by the stated counting rule, across all five levels.
6. Keeps contradicting evidence and reports both sides of a contested topic.
7. Does **not** let source standing settle a disagreement.
8. States an uncertainty for every finding, at every confidence level.
9. Flags findings that rest only on public or personal sources.
10. Flags findings backed by approved company material.
11. Collects deduplicated citations.
12. Counts sources by kind.
13. Refuses recommendation wording that claims approval.
14. Refuses wording that claims a completed action.
15. Refuses wording that claims a doctrine or policy change.
16. Checks the rationale as well as the statement.
17. Reports `approved`, `decided`, `acted_on`, `doctrine_changed` as `False`
    even when the attributes are set otherwise.
18. Names Mike Zachary as the decision holder on every recommendation.
19. Reports `is_approved_doctrine: False` and `is_a_decision: False` on every
    finding and record.
20. Renders a readable report showing contradictions and undecided status.
21. Raises on missing, malformed, or wrongly typed input, naming the file.
22. Refuses a supplied brief whose recommendation claims authority.
23. Contains no fetch, browse, or network capability.
24. Contains no write call and changes nothing on disk.
25. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. **The CLI.** Exercised by hand as recorded above; no automated test drives
   `cli.py`.
2. **The `ASSISTANT_RESEARCH_DATA` environment override.** Implemented in
   `resolve_data_root()`; tests use explicit paths.
3. **The `topics` field in a brief.** `ResearchRecord.build` accepts an explicit
   topic list, including topics no source mentions, but no test supplies one
   through a brief file.
4. **`uses_recommending_language`.** Computed and reported; nothing acts on it.
5. **`Source.retrieved_at` absence.** Sources without a retrieval date are
   allowed and produce a shorter citation; only the with-date path is asserted.
6. **Behavior with many sources or topics.** The largest test set is three
   sources and three topics.
7. **Non-ASCII source text.** Read as UTF-8; not exercised.

## NOT IMPLEMENTED

1. **Any fetching, browsing, searching, or downloading.** No network access.
2. **Natural-language claim extraction.** Claims are supplied as structured
   topic / statement / supports triples.
3. **Any approval, decision, or doctrine-setting capability.**
4. **Accepting or dispatching loads; committing money.**
5. **Sending any communication.**
6. **Source reliability scoring or weighting.** Standing is reported, not scored.
7. **Topic clustering, synonym matching, or fuzzy topic matching.** Topics match
   exactly.
8. **Any retention or memory between runs.**
9. **Any library, email, calendar, or voice capability.**
10. **Any user interface.** Command line only.
11. **Report export to any document format.**

## KNOWN LIMITATIONS

1. **It cannot find sources.** Everything depends on what is supplied. A
   one-sided source set produces a confident-looking `CONFIRMED` finding that is
   only as good as the sourcing - which is why single-source findings are
   labelled `SUPPORTED` and say so.
2. **Topics match exactly.** "rate floor" and "rate floors" are different
   topics. No stemming or clustering, so a reviewer can always see why two
   claims landed together.
3. **The confidence rule counts sources, not quality.** Two weak sources agreeing
   produce `CONFIRMED`. The uncertainty line names the standing, but the count
   is the count.
4. **Refusal is phrase-based.** Wording that claims authority using phrasing not
   on the list will pass. The list is visible and auditable, which is the
   trade-off taken deliberately.
5. **`supports` is binary.** A source that partly agrees must be entered as one
   or the other.
6. **Everything is UTC** and reported as UTC.
7. Verified on Windows 11 with Python 3.14.5 only.
8. **A recommendation is still only a recommendation.** Nothing this component
   produces is a decision, and the decision stays with Mike Zachary.
