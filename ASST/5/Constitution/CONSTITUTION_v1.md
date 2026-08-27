# Workstream 5 - Assistant Research - Constitution

**Component:** Assistant Research
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\5`.

---

## 1. Authority - the defining rule

**Research may recommend.**
**Research may not approve.**
**Research may not decide.**
**Research may not alter doctrine.**

Mike Zachary remains final authority.

This is enforced four ways, not asserted once:

1. **Fixed flags.** Every `Recommendation` reports `approved=False`,
   `decided=False`, `acted_on=False`, `doctrine_changed=False`. `to_dict()`
   emits those literals, so even setting the attributes by hand does not change
   the reported record. `test_flags_cannot_be_flipped_in_the_output` proves it.
2. **Refused wording.** Text claiming a decision raises `AuthorityError` at
   construction. Thirty-plus phrases are listed in `FORBIDDEN_PHRASES`:
   `i approve`, `we approve`, `the decision is`, `i authorize`, `load accepted`,
   `booked the load`, `i dispatched`, `payment sent`, `funds committed`,
   `this is now policy`, `doctrine is updated`, `email sent`, `i have signed`,
   and more. The rationale is checked as well as the statement.
3. **No such methods.** The record and the recommendation expose no `approve`,
   `decide`, `authorize`, `accept_load`, `dispatch`, `commit`, `pay`, `send`,
   `publish`, `set_doctrine`, or `update_policy`.
4. **Named ownership.** Every recommendation carries
   `decision_required_from: "Mike Zachary"`.

**Refusal, not softening.** Language claiming authority is rejected outright.
The component does not quietly reword it into something acceptable, because a
reworded claim still reached the page once.

## 2. Research is not doctrine

Only material supplied as `kind: company` reports
`is_approved_company_truth: True`. Public sources are reported as "public
source, not approved company truth". Personal sources are "stated by a person,
unverified".

No amount of agreement changes this. Two public sources agreeing produces
`CONFIRMED` confidence **and** an uncertainty reading "Sources agree, but none
is approved company material. Research is not doctrine."

**Standing never overrides arithmetic.** Approved company material does not win
a contest automatically. A company document contradicted by a broker's call is
`CONTESTED`, not settled. Standing changes how a source is *reported*, never
whether a disagreement exists.

## 3. Uncertainty is mandatory

Every finding states what is not known. A blank uncertainty field would be the
component claiming more than it knows, so there is no path that produces one.
`test_every_finding_states_an_uncertainty` covers every confidence level.

Contradicting evidence is **never dropped**. A contested finding records both
sides, with citations, and says plainly that it is not settled.

## 4. No fetching

1. This component does not search, browse, download, or fetch.
2. It imports no networking module at all.
3. Sources are supplied as JSON and read.

Enforced by `test_imports_no_network_or_vendor_module`,
`test_uses_only_the_standard_library`, and `test_nothing_fetches_or_browses`,
which fails if `urlopen`, `requests.get`, `fetch(`, `http://`, or `download`
appears anywhere in the source.

## 5. Isolation - absolute

1. This folder writes no file outside `ASST\5`. It writes no file at all.
2. This folder imports nothing from workstreams 1, 2, 3, 4, or 6.
3. This folder assumes no other workstream exists.
4. There is no integration code here, and none may be added.

Allowed imports, asserted by test: `__future__`, `argparse`, `dataclasses`,
`datetime`, `json`, `os`, `pathlib`, `re`, `sys`. Nothing else.

## 6. Hard prohibitions

There is no code path in this component that could:

1. Approve anything.
2. Decide anything.
3. Alter doctrine or policy.
4. Accept, book, or dispatch a load.
5. Commit money or authorize payment.
6. Send an email or any communication.
7. Reach the network.
8. Write any file.
9. Retain anything between runs.

## 7. Honesty rules

- **Every claim carries its source.** Findings list supporting and contradicting
  entries with citation and standing.
- **Every finding states its uncertainty.**
- **Every recommendation is labelled a recommendation** and names who decides.
- **Research is labelled research**, never doctrine.
- **A finding resting only on public or personal sources is flagged as such**,
  both in the data and in the rendered report.
- **Malformed input raises.** A broken source file raises rather than reporting
  an empty analysis. Reporting "no findings" from a file that failed to parse
  would be a lie.
- **The sample data says it is sample data.**

## 8. What must not happen without a new decision

- Do not add approval, decision, or doctrine-setting capability.
- Do not weaken `FORBIDDEN_PHRASES` or make refusal into rewording.
- Do not let `approved`, `decided`, `acted_on`, or `doctrine_changed` become
  reportable as `True`.
- Do not let source standing override the confidence arithmetic.
- Do not add fetching, searching, or browsing. That is a separate component and
  a separate decision.
- Do not allow a finding to be produced without an uncertainty.
