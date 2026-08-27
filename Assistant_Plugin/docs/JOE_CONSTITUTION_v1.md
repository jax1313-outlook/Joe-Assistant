# JOE - Program Constitution

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Final authority:** Mike Zachary

**This document does not restate doctrine.** The governing Constitution is:

> `D:\SANDBOX\Assistan_Building\JOE_CONSTITUTION_v1\02_CONSTITUTION_v1.md`  (v1.0)

That document governs. This one records **how this program enforces it in
code**, and where the enforcement lives, so a reviewer can check the claim
rather than accept it.

---

## 1. Precedence

Per governing Constitution Article IX:

1. Mike Zachary
2. Dispatch Core doctrine
3. `JOE_CONSTITUTION_v1` (the governing document set)
4. **This program constitution** and the six component constitutions
5. Implementation decisions

Where this document conflicts with the governing set, the governing set wins
and this document is corrected.

## 2. Permitted functions, as built

The governing Constitution permits: monitor, explain, research, retrieve,
summarize, draft, recommend, remember, train, procedure assistance, surface
uncertainty, submit requests.

Built and reachable in this program:

| Function | Where | State |
| --- | --- | --- |
| Retrieve | `LIBRARY` capability, `adapters/library_fs.py` | live |
| Explain | `EXPLAIN` capability | live, Library-backed |
| Monitor | `OPERATIONS` capability, `adapters/outlook_com.py` | live, read-only |
| Research | `RESEARCH` capability, `adapters/research_provider.py` | fixture only |
| Surface uncertainty | every `AssistantResponse.uncertainty` | live |
| Remember | `memory/` retention records | live |
| Recommend | research recommendations | fixture-sourced |
| Submit requests | `adapters/dispatch_port.py` | port defined, unconnected |
| Summarize / draft / train | **not implemented** - see Known Limitations | — |

## 3. Prohibitions, and the code that enforces them

| Prohibition | Enforcement | Location |
| --- | --- | --- |
| **May not approve** | 30+ phrases refused; response replaced with a refusal | `governance/__init__.py` `FORBIDDEN_CLAIMS` |
| **May not treat silence as consent** | 6 approval-by-omission patterns refused | `governance/__init__.py` `SILENCE_CONSENT_PATTERNS` |
| **May not execute unless rejected** | `ActionRequest.auto_execute` emitted as literal `False`; nothing drains the queue | `contracts/__init__.py`, `adapters/dispatch_port.py` |
| **May not decide** | `approved` / `decided` / `acted_on` / `operational_write` emitted as literals; a `True` attribute is forced back and reported | `contracts`, `governance` |
| **May not own Dispatch records** | no Dispatch read ever succeeds; no copy is retained | `adapters/dispatch_port.py` |
| **May not alter operational truth** | no write, update, create, delete, book, commit, or pay method exists on the port | `adapters/dispatch_port.py` |
| **May not write to Dispatch directly** | port exposes `read()` and `submit()` only; `submit` returns `accepted=False` | `adapters/dispatch_port.py` |
| **May not represent stale as current** | live readings older than 15 minutes get a "may not be current" notice | `governance` `is_stale()` |
| **May not present fixtures as live** | every SAMPLE provenance forces a "SAMPLE DATA" notice | `governance` |
| **May not claim printing** | Print emits "Print request recorded. Nothing was physically printed." | `app/service.py` |
| **May not widen its own access** | reads outside `READABLE_FACTS` raise; submissions outside `SUBMITTABLE` raise | `adapters/dispatch_port.py` |
| **Outlook may not send or modify** | generated PowerShell scanned for 20 non-read calls; refuses to run if one appears | `adapters/outlook_com.py` |

## 4. The governance gate

Every response passes `Governor.enforce()` before it reaches the window.

A **critical** finding does not get softened or reworded. The response is
**replaced** with a refusal naming the rule it broke - because a reworded claim
still reached the page once.

Non-critical findings add a visible notice and let the response through.

## 5. Removability

Governing Constitution Article V. In this program:

- Dispatch is never contacted. `status_dict()["dispatch_contacted"]` is a
  literal `False`.
- No Dispatch path, endpoint, credential, or data handle appears anywhere.
- The plugin runs, and every capability except Dispatch works, with Dispatch
  absent - which is the only state it has ever run in.

**Degradation is permitted; incapacity is not.** Proven in reverse: this
program has never had Dispatch, and Dispatch has never had this program.

## 6. Containment

`app/config.py::assert_within_plugin()` resolves every write path and raises
`ContainmentError` outside the plugin root. It runs on runtime data, logs,
records, and proof artifacts.

**Reading outside the plugin is permitted and intended** - the Library and
Outlook capabilities read Mike's own approved material. **Writing outside is
impossible.**

## 7. No Manager

There is no Manager component, module, class, agent, or authority path in this
program. A test walks every Python file and fails the build if a class matching
`*Manager` appears.

Governing model:

```
Mike Zachary  =  Final Human Authority
Dispatch      =  General Contractor, System of Record, Operational Authority
Assistant     =  Specialized Staff Plugin
```

## 8. Cognitive load

Governing Constitution Article VII, Test 3. In this program:

- No record ID is ever required. Ordinary sentences act on the selection.
- No confirmation queue exists. `dispatch.pending()` is empty in normal use.
- No notification system exists.
- No setting must be managed to operate; the configuration file has working
  defaults.
- The answer comes first; the full written response follows for parked review.
- A retention command does not create a record of its own, so the history does
  not fill with "Save this" entries.

## 9. What must not change without a ruling from Mike Zachary

- Do not add an approval, decision, or auto-execute path.
- Do not give the Dispatch port a write method.
- Do not let a fixture be reported as live.
- Do not let Print claim physical printing.
- Do not add a Manager.
- Do not make Dispatch depend on this program in any way.
- Do not remove the governance gate or weaken its refusal into rewording.
