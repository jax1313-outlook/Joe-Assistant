# 08_DISPATCH_BUILD_VALIDATION_STANDARD

**Program:** Dispatch  
**Owner:** Mike Zachary / Level 1 Transport  
**Status:** Source of Truth / Governance Stack  
**Rule:** No amendments. Rewrite and replace the governing file when doctrine changes.  


## 1. Purpose

Define required governance validation for every serious Dispatch design, implementation, code review, walkthrough, PR review, deployment, or architecture review.

## 2. Required Validation Report

Every build must return:

```text
BUILD VALIDATION REPORT

Constitution Compliance: PASS / FAIL
Agent Governance Compliance: PASS / FAIL
Relationship Compliance: PASS / FAIL
Authority Compliance: PASS / FAIL
Learning Compliance: PASS / FAIL
Conflict Compliance: PASS / FAIL
Semantic Review: PASS / FAIL
Drift Check: PASS / FAIL

Files Inspected:
Files Modified:
Tests Added:
Tests Run:
Tests Passed:
Walkthrough Performed:
Conflict Notices Created:
Decision Needed From Mike:
```

## 3. PASS Criteria

A build may pass only when:

- no role boundaries are violated
- no forbidden relationship is created
- no authority shifts to an agent
- no unapproved source becomes truth
- no draft is promoted into Library truth
- Archive and Library remain separate
- Portal remains presentation only
- Automation remains execution only
- Manager does not become final authority
- Mike approval gates remain intact

## 4. FAIL Rule

Any FAIL requires:

```text
STOP
Generate Conflict Notice
No merge
No deployment
No implementation continuation
```

## 5. Semantic Review Requirement

Builders must evaluate meaning, not only code. Passing tests, clean merge, and working UI do not prove governance compliance.

## 6. Required Closing

```text
This validation report is a recommendation only.
No action is authorized.
Mike decides.
```
