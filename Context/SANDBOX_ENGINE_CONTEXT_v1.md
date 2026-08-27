# Sandbox Engine v1 - Operating Context

**Project:** Level 1 Assistant - local governed workflow layer
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## 1. Where this sits in the operation

Level 1 Transport already has systems that do specific jobs. The Sandbox Engine
does not do any of their jobs.

| System | Its job | The engine's relationship to it |
| --- | --- | --- |
| **Microsoft 365 Copilot** | Reasoning, research, company-knowledge retrieval, chat, voice | Supplies text. Not called by the engine. Not replaced. |
| **Dispatch** | Freight workflow and operational system | Untouched. Not read, not written, not integrated. |
| **Outlook** | Scheduling authority and email transport | Untouched. The engine cannot send mail. |
| **Company Library** | Approved company facts and reusable assets | Never written. Records do not go here. |
| **Research Library** | Research knowledge, not truth or doctrine | Never written. |
| **COMI** | Communication workflow and routing | Untouched. |
| **Publisher** | Approved-format communications and artifacts | Would consume artifact requests one day. Not connected. |
| **Archive** | Long-term retention | Never written. Expired records never land here. |

The engine occupies the gap none of them fill: **what happens to the written
record of an Assistant interaction between the moment it is produced and the
moment a person decides it matters.**

## 2. The problem it solves

Without this layer, every Assistant interaction is either lost immediately or
kept forever. Neither is right.

Most interactions are worth nothing an hour later — a question about the next
scale, a rate that was never going to work. A few are worth keeping, and a
smaller few are worth writing up formally. The driver knows which is which, but
only after the answer exists, and often while driving.

So the default is temporary, the driver's ordinary words change that default,
and nothing becomes permanent by accident.

## 3. Who operates it

**Primary operator: Mike Zachary.** Owner/operator, final authority, frequently
driving.

Design consequences:

- Commands are ordinary speech, not syntax. `"Save this"` works. There is no
  required prefix, flag, or keyword form.
- Capitalization and punctuation are irrelevant.
- Every state change reports one short notice, in plain language, stating what
  is true. No enthusiasm, no ceremony, no repeated prompting to save something.
- Unrecognized language changes nothing and says so, rather than guessing.

## 4. The three levels in operating terms

| Level | Driver says | What the engine does |
| --- | --- | --- |
| **Level 1 — answer it** | `Level 1`, `Just answer it`, `Just tell me what matters`, `No need to save this`, `Let it expire` | Holds the written record temporarily. Three hours. Nothing operational is created. |
| **Level 2 — save it** | `Save this`, `Keep this`, `Level 2 this`, `Put this under Load 123`, `Attach this to the mission`, `Keep this for parked review` | Stops the clock. Marks it `SAVED`. Keeps the load, mission, customer, broker, or folder reference the driver stated. |
| **Level 3 — build it** | `Level 3 this`, `Build a report`, `Formal presentation`, `Write this up`, `Research this completely`, `Level 3 this under XPO Load 123`, `Level 3 this under Ideas` | Stops the clock. Marks it `FORMAL`. Keeps the destination. Raises a formal-artifact request carrying the citations and sources. |
| **Print** | `Print this`, `Make this printable`, `Write this so I can print later` | Stops the clock. Marks it `PRINT_READY`. Leaves the interaction level where it was — Print is a state, not a level (ruled by Mike Zachary, doctrine C4). Raises a print-ready request and states plainly that no printer was contacted. |
| **Delete** | `Delete this`, `Remove this`, `Forget this` | Removes it from the active Sandbox, purges the content, promotes it nowhere. |

## 5. Why three hours

Three hours comes from the governing configuration, not from this build. It
covers a normal working stretch — a driver who asks a question at a stop and
decides two hours later that the answer mattered still has it. Past that, the
question has usually resolved itself.

The value lives in one place (`DEFAULT_RETENTION_HOURS` in `records.py`) and is
a constructor argument on the engine, so changing it is a doctrine decision, not
a code hunt.

## 6. What "temporary" means here, exactly

A `TEMPORARY` record is a written record on this machine, in a plain JSON file,
that will be marked expired and have its content purged once three hours pass
and a sweep runs.

It is **not** backed up, **not** synchronized, **not** in Company Library, and
**not** in Dispatch. Nothing in the engine describes it as saved.

## 7. Realistic use, end to end

Driver, at a stop, asks Copilot about a broker's offer. Copilot answers. The
written interaction is placed in the Sandbox as `TEMPORARY`, expiring in three
hours.

- If the driver says nothing further, it expires. No operational record was ever
  created, and nothing reaches Company Library or Dispatch.
- If the driver says `"Put this under Load 123"`, it becomes `SAVED`, the clock
  stops, and `Load 123` is preserved on the record for parked review.
- If the driver says `"Level 3 this under Ideas"`, it becomes `FORMAL`, the
  destination `Ideas` is preserved, and a formal-artifact request is written
  carrying the citations. The report itself does not exist yet, and the request
  says so.
- If the driver says `"Print this"`, a print-ready request is raised and held.
  Nothing prints.

In every branch, the decision stayed with the driver and no system was written
to.

## 8. What is deliberately absent

Not built, not started, and out of scope for this mission:

- phone integration and call-state handoff
- email reading or sending
- Outlook or Microsoft Graph integration
- voice recognition and voice-first Driver Portal interface
- Dispatch integration and load/mission record routing
- an approval viewer
- cross-channel continuity across voice, chat, email, phone, and portal
- any Assistant interface beyond the local command line
- production of the artifacts that Level 3 and Print request

Each of these is a separate decision. None of them were started early, and
nothing in this build assumes a particular answer for any of them.

## 9. Machine and runtime facts, as found

- Project root: `D:\Sandbox\Assistan_Building` — created by this build; it did
  not previously exist.
- Governing documents were found under
  `C:\Users\jax13\OneDrive - Level 1 Transport Inc (1)\Copilot WorkSpace\Company Library\Assistant\Assistant_Building\`
  and copied unmodified into `Governing_Inputs\`. The originals were not
  changed.
- Runtime: Python 3.14.5 through the `py` launcher.
- No Node.js on this machine. `python` on `PATH` is the Microsoft Store stub,
  not an interpreter — which is why every launcher calls `py`.
- No installation, package manager, or virtual environment is required.
