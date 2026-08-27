# JOE — Proof Audit

**Program:** JOE, the Level 1 Assistant
**Audited:** 27 August 2026
**Scope:** the twenty proofs not already corrected (1–9, 11–13, 16–21, 23, 24)
**Question asked of each:** *can this proof fail?*

---

## Status: closed

All seven items were corrected on the day of the audit, each verified by
planting the fault it was blind to and confirming the proof fails.

| | Fault planted | Result |
| --- | --- | --- |
| D1 | Approval setter, Manager class, provider SDK outside adapters, polling loop | all four caught, each named |
| D2 | Library capability raising on every call | caught |
| D3 | A draft returned with no label | caught |
| D4 | Research reporting LIVE while its output says SAMPLE | caught |
| D5 | A mailbox in use that is not the designated one | caught |
| W1 | Search results with the source labels stripped | caught |
| W2 | A preserved record lost, and a record reappearing | both caught |

Two claims in D1 were removed rather than made real: "Assistant not required to
run Dispatch" and "No Assistant code copied into Dispatch" are facts about the
Dispatch repository, and this suite runs inside JOE and cannot see it.

---

## Why this audit exists

Four proofs were examined earlier the same day, for an unrelated reason. All
four could report PASS while the thing they described was broken — and one of
them did: the suite read 24 of 24 while mail, calendar and contacts all refused
in the product, because the proof that would have caught it accepted a refusal
as evidence of correct behaviour.

Four out of four is a bad ratio to extrapolate from optimistically. This audit
covers the other twenty.

**Result: thirteen sound, five defective, two weak.** The defects are listed
first because they are the ones that matter.

---

## Defects

### D1 — Proof 18: eight of ten drift tests are the literal value `True`

The most serious finding. `step_18_drift` builds a list of checks and passes
when `all(ok for _, ok in checks)`. Eight entries are hardcoded:

```python
checks.append(("Dispatch not required to run JOE", True))
checks.append(("Assistant not required to run Dispatch", True))
checks.append(("No Assistant code copied into Dispatch", True))
checks.append(("No component writes operational truth", True))
checks.append(("No approval by silence or omission", True))
checks.append(("No fixture data presented as live", True))
checks.append(("No stale data presented as current", True))
checks.append(("No general-purpose autonomous agent introduced", True))
```

These are not tests. They are claims typed into a list, and they will report
PASS for as long as the file exists.

This is the step meant to catch the system drifting away from its own doctrine.
Among the things it does not check: *no approval by silence or omission* — the
constitutional line the transmission amendment turns on — and *no fixture data
presented as live*, which is the guarantee the whole program is built around.

Its note says each item is "additionally asserted by the automated suite". That
may be so; the 329-test suite could assert these behaviours without using this
wording, and **this audit did not establish either way**. It does not change
the finding: a step that reports PASS on a hardcoded `True` is not evidence,
whatever exists elsewhere.

### D2 — Proof 2: passes with the capability entirely broken

*Demonstrated, not inferred.* The pass condition is:

```python
bool(response.answer) and bool(response.written)
```

`response.ok` is never consulted. When a capability raises, `ask()` catches it
and returns a response whose `answer` and `written` are both filled in — so the
condition holds.

With the Library capability patched to raise on every call, Proof 2 reported
PASS, and its own evidence line read:

```
answer   That capability failed. Everything else is still working.
```

### D3 — Proof 23: checks that a string exists in a file

*Demonstrated.* `labelled` is established by reading `reasoning_capabilities.py`
as text:

```python
labelled = "DRAFT ONLY" in source and "NOT SENT" in source
```

That proves two strings appear in a source file. It does not prove any draft was
ever labelled. The check returns the same verdict against the real file and
against a one-line comment containing both phrases. Delete every piece of
labelling logic, leave a comment behind, and this passes.

The behaviour itself is correct — a live draft request was observed carrying
`DRAFT ONLY / NOT SENT` — which is precisely why the gap is easy to miss.

### D4 — Proof 11: no positive control, and it cannot survive success

```python
not probe["live_connection"] and labelled
```

Two problems. A research provider that is simply broken also reports not-live,
and passes — the same missing positive control corrected in proofs 14 and 15.

And the step is titled *"Research status truthfully shows live **or** fixture
mode"* while the condition accepts only fixture. The day a live research
provider is connected, this proof fails for the wrong reason, and whoever is
holding the pager will "fix" it by weakening it.

### D5 — Proof 21: never checks that the designation is honoured

```python
bool(accounts) and bool(in_use) and bool(result.account)
```

Three non-empty strings. Nothing compares `in_use` against the configured
account, which is the entire claim in the title — *"The Outlook account in use
is designated and reported."* A build that ignored the designation completely
and read whatever mailbox it liked would satisfy this, provided it reported
*something*.

Worth noting: this is the step whose output prompted an investigation earlier
the same day into an apparent mailbox mismatch. It reported the fact and
asserted nothing about it.

---

## Weak, but not defective

### W1 — Proof 9: the title claims a check the condition does not make

Titled *"Library search returns a configured source, correctly labelled"*;
passes on `probe["available"] and bool(result.findings)`. Nothing tests the
labelling. The same shape as the printed-but-unasserted claim corrected in
proof 14.

### W2 — Proof 13: proves nothing was lost, not that nothing extra survived

```python
restored > 0 and len(kept) >= len(saved) > 0
```

`>=` means a build that preserved records it should have expired passes. The
title is *"preserves eligible records"*; ineligible ones surviving is not
caught.

---

## Sound

Thirteen proofs hold up. Each asserts something a broken build would fail:

| | |
| --- | --- |
| 1 | Window actually became visible |
| 3 | Record present in history and selected |
| 4 | Exact state, level, and a three-hour expiry to the second |
| 5, 6, 7, 8 | Each retention transition checked by state, level and expiry |
| 12 | Requires a real engine and a rendered file with bytes in it |
| 16 | Dispatch absence asserted several ways, including a refused submission |
| 17 | Actively attempts writes outside the root and confirms each was blocked |
| 19 | **Notable.** Carries a 90-day sanity check for exactly the empty-calendar trap: *"A filter that matches nothing looks exactly like an empty calendar."* Suspected, then cleared |
| 20 | Checks order *in fact*, not only the ordering label, and requires at least two items so a short list cannot pass trivially |
| 24 | A positive and a negative case: a known procedure must cite, an unknown one must refuse |

Proofs 19, 20 and 24 are the model the defective ones should be corrected
toward.

---

## Found while auditing: a failing test, and its cause

The 329-test automated suite had not been run in this session. It failed:

```
AssertionError: 'SIGNED OUT' not found in ('NOT CONFIGURED', 'LIBRARY MISSING')
```

`TestCopilotAuthentication` constructs `CopilotAuth(cache_dir=...)` with no ids,
which falls back to `ASSISTANT_COPILOT_TENANT_ID` and
`ASSISTANT_COPILOT_CLIENT_ID`. Those were moved into the environment earlier the
same day, so the object was configured where the test assumed it would not be.
An empty string cannot override the fallback — `""` is falsy, so it reads the
environment regardless.

The product behaviour is correct. The test was environment-dependent: it passed
on a machine that had never signed in and failed on one that had. It now clears
those variables for its duration and restores them afterwards. **329 pass, both
with the environment set and without it.**

Also worth recording: **the proof suite reported 24 of 24 throughout.** It does
not run the automated tests, so a failing test is invisible to it.

---

## Recommended order

1. **Proof 18** — replace eight hardcoded `True` values with real checks, or
   remove the claims. A claim nobody checks is worse than an absent one,
   because it reads as covered.
2. **Proof 23** — assert the label on an actual draft, not on a source file.
3. **Proof 2** — check `response.ok`.
4. **Proof 21** — assert the configured designation is the one used.
5. **Proof 11** — add a positive control; let the step accept a live provider.
6. **W1, W2** — tighten when convenient.
