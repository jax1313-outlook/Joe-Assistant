# 03_DISPATCH_AGENT_RELATIONSHIP_MATRIX

**Program:** Dispatch  
**Owner:** Mike Zachary / Level 1 Transport  
**Status:** Source of Truth / Governance Stack  
**Rule:** No amendments. Rewrite and replace the governing file when doctrine changes.  


## 1. Purpose

The Agent Relationship Matrix defines communication paths, handoff paths, escalation paths, approval paths, forbidden paths, and ownership boundaries for Dispatch agents.

Charters answer: Who am I?  
The Relationship Matrix answers: Who may I work with?

## 2. Global Rule

Every agent has:

```text
May Receive From
May Send To
Must Escalate To
Must Not Bypass
May Not Contact
Forbidden Relationships
```

## 3. Relationship Table

| Agent | May Receive From | May Send To | Must Escalate To | Forbidden / Must Not Bypass |
|---|---|---|---|---|
| Manager | All agents, Mike | All agents, Mike | Mike | May not make final decisions |
| Publisher | Manager, Library, Intelligence, Mike-provided sources | Manager, Library Candidate Queue, Archive | Manager | No public/agency/customer/broker contact without approved workflow; no Library truth promotion |
| Library | Manager, Publisher Candidate Queue, Mike | Publisher, Intelligence, Manager, Portal | Manager | No unapproved truth; no Archive merge |
| Archive | Publisher, Manager, Automation, Mike | Retrieval references, Manager, Portal | Manager | No active drafts as final; no direct Library truth update |
| Intelligence | Acquisition, Processing/Rules, Library, Manager, Mike | Publisher, Manager, Archive | Manager | No final pursuit decisions; no research-as-truth |
| Dispatcher | Manager, Intelligence, Library, Mike | Manager, Publisher, Archive, Portal | Manager | No load commitment; no rate decision |
| Portal | Approved sources only | Humans via display, Manager via alerts | Manager | No record ownership; no decision making |
| Automation | Approved workflows, Manager | Approved destinations only | Manager | No self-triggered actions; no external action without approved trigger |
| Acquisition | Authorized sources, Manager, Mike | Processing/Rules, Intelligence | Manager | No interpretation; no scoring |
| Processing / Rules | Acquisition, Manager | Intelligence, Manager | Manager | No doctrine creation; no rule changes without approval |
| Refinement Analyst | All agents for review | Manager, Mike | Manager/Mike | No implementation; no approval |

## 4. Approved Handoff Paths

```text
Acquisition → Processing / Rules → Intelligence → Manager
Intelligence → Manager → Publisher → Library Candidate → Archive
Publisher → Manager → Mike Review → Library Candidate → Archive
Library → Publisher / Intelligence / Manager / Portal
Archive → Portal reference / Manager reference / Library review candidate only when approved
Dispatcher → Manager → Publisher → Archive → Portal
Automation → approved routes only
Portal → displays and routes only
Refinement Analyst → Manager / Mike only
```

## 5. Forbidden Relationships

```text
Publisher → Library Truth without approval
Publisher → Public Submission without approval
Publisher → Agency Contact without approved workflow
Research Scout → Publisher production command
Research Scout → Dispatch authority
Archive → Library Truth without review
Portal → System of Record
Automation → External Action without approved trigger
Processing / Rules → Scoring Doctrine Change
Intelligence → Final Pursuit Decision
Dispatcher → Company Commitment
Manager → Final Approval
Any Agent → Mike bypass
```

## 6. Relationship Compliance Test

Every build must answer:

```text
Which agents are affected?
What relationships are affected?
Does this create a new relationship?
Does this create a forbidden relationship?
Does this bypass Manager?
Does this bypass Mike?
Does this shift authority?
Does this blur Library and Archive?
```

If any answer indicates drift, STOP and produce a Conflict Notice.
