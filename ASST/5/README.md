# ASST\5 - Assistant Research

Analysis over supplied sources: findings, confidence, uncertainties,
recommendations, source reporting.

**Research may recommend. Research may not approve, decide, or alter doctrine.**

## Read this first

**It does not go and find anything.** No web search, no browsing, no downloads,
no network access. You supply the sources; it tells you what they say, how well
supported each point is, and what is still not known.

## Use it

```bash
Source\research.cmd brief ..\Data\brief_northbound_lane.json
```

```bash
Source\research.cmd uncertainties ..\Data\brief_northbound_lane.json
```

```bash
Source\research.cmd authority
```

## Test it

```bash
Tests\run_tests.cmd
```

78 tests.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is and the boundary that defines it
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - the confidence rule and authority mechanics
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The four things to know

**Confidence is a count, not an opinion.** Two supporting sources with no
contradiction is `CONFIRMED`. One is `SUPPORTED`. Any disagreement is
`CONTESTED`. You can predict every result by counting.

**Company material does not automatically win.** A Company Library document
contradicted by a phone call comes out `CONTESTED`, not settled. Standing
changes how a source is reported; it never settles a disagreement.

**Every finding states what is not known.** No finding can have a blank
uncertainty.

**Wording that claims authority is refused, not softened.** Try:

```bash
Source\research.cmd check "I approve the lane and have booked the load."
```

## Isolation

This folder imports nothing from workstreams 1-4 and 6, imports no networking
module, and writes nothing anywhere.
