# DISPATCH — OPERATIONAL READINESS MISSION

**Issued by:** Mike Zachary, Owner/Operator, Level 1 Transport — final authority
**Executed by:** Claude Code (implementation engineer)
**Program:** Dispatch (never "L2-COS")
**Repository authority:** `Dispatch/portal/` is Dispatch. The Jules portal is a read-only design archive.

---

## 0. How to read this mission

This is one mission with four tasks. Run every independent task at once. Respect the dependency map in Section 7. Do not stop to ask for approval on anything Section 8 does not reserve for Mike. Do not stop between tasks. Deliver one consolidated pull request for application changes, one completion report, and the local-machine artifacts described in Section 10.

Where this mission says "prove," it means: produce evidence a skeptical person can inspect — a log, a hash, a screenshot path, a process ID, a record identifier, a file path. A statement that something works is not proof.

Where this mission says "label," it means the label must be visible in the user-facing surface and in the stored record, not only in a comment or a log.

---

## 1. Authority and truth rules (locked — apply to every task)

### 1.1 Mike is final authority

Never manufacture, infer, default, auto-populate, seed, or test-fixture any of the following attributions:

```
Verified by Mike Zachary
Approved by Mike Zachary
Accepted by Mike Zachary
Authorized by Mike Zachary
Confirmed by Mike Zachary
```

Any record of a Mike-authorized action must originate from an explicit authenticated human action and must retain: actor, timestamp, action, previous state, resulting state, source, audit reference. If you need a human-decision record during rehearsal, the actor is the authenticated account performing the rehearsal, labeled as rehearsal, never impersonating Mike.

### 1.2 Spine + Opportunity

Spine owns lifecycle authority, transition rules, transition validation, audit history, Current Reality. Opportunity owns discovery, scoring, revenue analysis, Dynamic Capacity, risk findings, Scheduler inputs, recommendations. Required flow:

```
OPPORTUNITY → SCORE → DYNAMIC CAPACITY → SCHEDULER REVIEW → HUMAN DECISION → SPINE TRANSITION → CURRENT REALITY
```

Opportunity recommends. The human decides. Spine transitions. `loads.status` remains the live operational load-status system; do not replace it wholesale.

### 1.3 Current Reality vs Possible Future

Possible Future (candidate loads, projections, scores, estimated capacity, proposed schedules, route alternatives, recommendations) may never silently mutate Current Reality (committed missions, authenticated human decisions, actual operational events, driver-reported milestones, evidence, current truck and load state). Nothing you build in this mission may cross that line, including connectors, rehearsal data, or launcher actions.

### 1.4 Driver-First / 70 MPH phone-call test

Any driver-facing surface you touch must let Mike obtain essential mission information within seconds while operating a commercial vehicle: minimal taps, clear refusals, no silent failure, Current Mission central, familiar driver terminology.

### 1.5 Scheduling truth

Outlook is the single source of scheduling truth. Dispatch may evaluate fit, present schedule information, request event creation after human authorization, and show Outlook-derived capacity. Dispatch may not create a second scheduling truth. The Driver Portal Calendar is a presentation layer over Outlook data.

### 1.6 HOS / ELD boundary

Dispatch is not an ELD. The driver is responsible for legal HOS compliance. Remove any readiness claim, status indicator, or documentation statement that implies verified HOS or ELD information unless a live trusted external source supplies it. Arrival, pickup, departure, delivery, and exception buttons are the required operational visibility. If you find HOS/ELD assumptions in readiness language, code paths, or docs, correct them in this mission and list each correction in the completion report.

### 1.7 Fuel receipts

Every fuel receipt must carry driver identity, truck identity, timestamp, jurisdiction, receipt evidence. An active load is optional. Never create an artificial load association.

### 1.8 Truth labeling vocabulary

Use exactly these status words wherever an external dependency, data source, or proof state is reported. Do not invent synonyms or softer variants.

| Word | Meaning |
|---|---|
| `LIVE` | Actual communication with the real external system occurred and is evidenced |
| `CONFIGURED` | Credentials/endpoints present and validated; no live exchange evidenced yet |
| `UNCONFIGURED` | Required configuration absent |
| `SIMULATED` | A mock or stand-in produced the data |
| `UNAVAILABLE` | Configured but the last attempt failed |
| `MANUAL` | A human performed the step outside Dispatch and recorded it |
| `ABSENT` | The step was not performed at all |
| `UNVERIFIED` | Implemented in code but not proven on Mike's machine |

`LIVE`, `CONNECTED`, `VERIFIED`, `CURRENT` may only appear when actual evidence supports them.

### 1.9 Application code vs local-machine proof

Two categories of output exist and must never be conflated:

- **Application code** — changes to the Dispatch repository, delivered via the consolidated PR, proven by repository tests.
- **Local-machine proof** — evidence that Dispatch operates on Mike's actual Windows machine, produced by running the software there. Repository tests (currently 3,087 passed / 93.73% coverage) are evidence of software behavior only. They are not operational proof and must not be cited as such.

In every report, every readiness statement must be tagged either **IMPLEMENTED** (code exists and tests pass) or **OPERATIONALLY PROVEN** (executed on Mike's machine with evidence). Anything not proven is `UNVERIFIED`.

---

## 2. Before you begin — reconnaissance (do this first, all tasks depend on it)

1. Inspect the repository: existing launch scripts, entry points, configuration loading, secret handling, database path resolution, Operations/Archive/Memory root resolution, backup/restore implementation, existing test layout, existing external-integration stubs, existing Outlook code paths.
2. Record the current commit hash and application version string. These appear in every artifact you produce.
3. Identify the Windows environment facts you can determine from the repository (Python version expectations, dependencies, service model). Do not assume facts about Mike's machine that the repository cannot tell you; list them as questions in the completion report.
4. Inspect the Jules portal only for presentation and cockpit ideas relevant to the Launcher status display. Adopt none of its runtime, security model, state handling, static sample behavior, or simulated upload behavior.
5. Confirm the Task 3 paths exist and are reachable: Sandbox `D:\Sandbox\Play Pen`, output folder `D:\Sandbox\Play Pen\Dispatch`. Both are designated by Mike. Keep the paths configurable in tooling, but these are the values for this mission. If the output folder does not exist, create it; that is the only write permitted under the Sandbox.

Write a short reconnaissance note (`docs/readiness/RECON.md`) summarizing what you found before starting implementation. This note is part of the PR.

---

## 3. TASK 1 — Dispatch Launcher and Control Center

### 3.1 Objective

Give Mike a normal, obvious, Windows-native way to Start, Stop, Restart, Open, and inspect Dispatch without typing Python commands.

### 3.2 Implementation choice

Choose the simplest reliable Windows-native presentation compatible with the current repository. Options include a batch file, PowerShell, a Python desktop control panel, a system-tray utility, a local control page, or a combination. Inspect existing launchers first, then select the least complex sound implementation. State your choice and the rejected alternatives in one paragraph in the completion report.

The launcher is an operating control for the existing Dispatch portal. It must not become a second Dispatch application, must not duplicate portal logic, and must not hold operational state of its own beyond process and configuration observation.

### 3.3 Required controls and displays

Controls: Start, Stop, Restart, Open Portal.

Displays (each read from the actual runtime configuration, not hard-coded):

- running / stopped status with process ID when running
- application version and commit
- portal address
- database location
- Operations root
- Archive root
- Memory root
- active configuration mode
- development vs operational mode
- whether default or missing secrets prevent operation (name the setting, never the value)
- backup status: last backup time and location if any; never claim the backup is valid unless a restore verification record exists
- most recent launch failure in plain language (e.g., "Dispatch could not start because port 8000 is already in use," not a stack trace; keep the stack trace in the log)

### 3.4 Process safety

- Start creates exactly one server process and records its PID.
- A second Start while running does nothing except report "already running."
- Stop terminates the actual server process and confirms it is gone (poll the PID; report if it did not exit and what to do).
- Restart proves the original process is dead before launching the new one.
- Detect and report orphaned processes from a prior crash rather than starting a duplicate.
- Logs are preserved in a logs directory outside version control. Redact any secret values before writing. Add the logs path to `.gitignore` if not already present.

### 3.5 Acceptance evidence (local-machine proof)

Produce `proof/launcher/LAUNCHER_PROOF.md` containing, with timestamps and PIDs:

1. Start created one live server process.
2. A second Start did not create a duplicate.
3. Open Portal reached the running Dispatch portal (HTTP response evidence).
4. Stop terminated the actual server process.
5. Restart showed the original PID dead before the new PID existed.
6. Status reported correctly in both states.
7. Each displayed storage path was compared with the path Dispatch actually used (show both values side by side).
8. Each failure message was triggered at least once and reproduced verbatim.

Any item you cannot execute on the target machine is `UNVERIFIED`, with the exact command Mike should run to verify it.

---

## 4. TASK 2 — Real-Load Operational Proof System

### 4.1 Objective

Prove that Mike can move one complete Level 1 Transport load through Dispatch on his own Windows machine — not that the test suite passes.

### 4.2 Safety boundary

Do not require a real revenue load. Build:

1. **Rehearsal mode** — operational-proof data that is unmistakably labeled at the record level and in every user-facing surface (e.g., a `REHEARSAL` tag on load, driver, truck, evidence, and milestone records; a visible banner in driver and portal views). No rehearsal record may ever display as an unlabeled live mission. Rehearsal records must be excludable from operational queries and reports, and it must be possible to purge them without touching live data.
2. **Real-load readiness checklist** — the conditions that must all be true before Mike runs a live load through Dispatch.
3. **Optional live-load procedure** — written but gated on the rehearsal passing and on a Mike decision.

Rehearsal mode is application code and ships in the PR with tests. It must not weaken any production path.

### 4.3 Proof path

Build a step-by-step procedure, supporting utilities (readiness checks, evidence collector, hash tool, restore verifier), and a report generator that walks this path in order:

```
 1. Start Dispatch (via Task 1 launcher)
 2. Authenticate
 3. Create or confirm Driver
 4. Create or confirm Truck
 5. Create Load
 6. Assign Driver
 7. Assign Truck
 8. Record human decision where required (authenticated actor, rehearsal-labeled)
 9. Create or confirm Outlook schedule information where authorized
10. Driver receives mission
11. Driver reports milestones (arrival, pickup, departure, delivery)
12. Driver uploads pickup evidence
13. Driver reports an exception if applicable
14. Driver uploads POD and delivery evidence
15. Load reaches delivered or closed state through governed Spine transitions
16. Application stops completely (via launcher; PID confirmed dead)
17. Application restarts
18. Load, milestones, and evidence remain (record IDs and file hashes compared)
19. Backup is created
20. Restore is proven in an isolated destination (never the live database or evidence store)
```

Every step records: who performed it (Mike / Code-automated / not performed), timestamp, record identifiers created or touched, and result. Step 9 must record Outlook status as `LIVE`, `SIMULATED`, `MANUAL`, or `ABSENT`.

### 4.4 Readiness checks

Before step 1, the utility verifies and reports: database path exists and is writable; evidence-storage path exists and is writable; backup destination exists and is separate from the live paths; restore destination exists, is empty or purgeable, and is separate from both; no default secrets in operational mode; application commit and version.

### 4.5 Proof report

Generate `proof/load/OPERATIONAL_LOAD_PROOF.md` containing:

- what Mike personally performed
- what Code verified automatically
- what remains `UNVERIFIED`
- exact database path
- exact evidence-storage path
- exact backup path
- exact restore destination
- original and restored record identifiers, side by side
- SHA-256 hashes of every evidence file, original vs restored
- application commit and version
- Outlook interaction status per Section 1.8
- a single line at the top: **REHEARSAL PASSED** / **REHEARSAL FAILED at step N** / **REHEARSAL NOT YET RUN ON TARGET MACHINE**

If you cannot run the rehearsal on Mike's machine, the report must still be generated in template form with every step marked `UNVERIFIED` and the exact commands Mike runs to execute each step.

---

## 5. TASK 3 — Sandbox Knowledge Recovery and Organization Experiment

### 5.1 Objective

Read Mike's Sandbox folder, inventory and classify its contents, and produce a knowledge map and organization proposal. Move nothing.

### 5.2 Hard safety rules

The first pass is read-only. Under no circumstances may any file in the Sandbox be moved, renamed, deleted, overwritten, deduplicated, converted, archived, uploaded, committed to Git, or treated as accepted doctrine. Open files read-only. Do not execute any script, notebook, or binary found in the Sandbox. Do not follow links or fetch external resources referenced in Sandbox files. Write outputs only to `D:\Sandbox\Play Pen\Dispatch`. Mike has designated this folder inside the Sandbox; it is the single permitted write location, and creating it is the single permitted structural change. Because it sits inside the read scope, the inventory tooling must exclude `D:\Sandbox\Play Pen\Dispatch` from its own inventory and classification so the outputs never feed back into the map. Existing contents of that folder, if any, are inventoried once and reported separately as "prior output-folder contents"; they are not overwritten — use timestamped output filenames.

If the tooling you build for this task (an inventory script, a classifier) lives in the repository, it ships in the PR with tests proving it performs no write operations against its input path.

### 5.3 Classification

Assign every file one primary class and any number of secondary classes from exactly this set:

```
Knowledge · Evidence · Research · Decision · Doctrine · Draft · Duplicate · Historical · Personal · Sensitive · Unknown
```

Rules of interpretation, which must be stated in the knowledge map:

- Architecture research is not accepted architecture.
- Notes are not doctrine.
- AI-generated reports are not human decisions.
- A file is `Decision` only if it records an explicit human decision with an identifiable actor; otherwise it is at most a `Decision` candidate.
- `Doctrine` is assigned only to material that matches doctrine already locked in this mission or in the repository; everything else that looks like doctrine is a `Doctrine` candidate.
- When in doubt, `Unknown`. Never upgrade confidence to make the map look complete.

Also identify: Dispatch-related vs non-Dispatch material, likely duplicates (by hash and by near-content), unresolved questions, superseded ideas, prompt assets, reusable Company Library candidates, and sensitive material (credentials, personal data, financial data, third-party confidential material). For sensitive material, record the path and category only — never copy contents into any report.

### 5.4 Required outputs (in `D:\Sandbox\Play Pen\Dispatch`)

```
SANDBOX_FILE_INVENTORY            — every file: path, size, modified, hash, primary class, secondary classes, Dispatch-related Y/N
SANDBOX_KNOWLEDGE_MAP             — narrative map of what exists, how it relates, what appears current vs superseded
DISPATCH_RESEARCH_CANDIDATES      — architecture and research material relevant to Dispatch, with why
POSSIBLE_DUPLICATES               — groups of exact and near duplicates with the evidence for the match
GOVERNANCE_AND_DOCTRINE_CANDIDATES — material that reads as doctrine, tagged candidate, with what locked doctrine it matches or conflicts with
MIKE_DECISION_CANDIDATES          — questions and choices that appear to need Mike's decision, and any recorded decisions found
SENSITIVE_MATERIAL_REPORT         — paths and categories only
PROPOSED_FOLDER_STRUCTURE         — a target structure organized around: repositories contain implementation truth; folders contain research and knowledge evidence; Mike supplies operational truth and authority
PROPOSED_ORGANIZATION_ACTIONS     — numbered list of moves/renames/merges, each reversible, each awaiting Mike's separate approval; nothing executed
```

Every output carries a header stating: generated by Claude Code, date, Sandbox path read, output path, "READ-ONLY PASS — NO FILES WERE MODIFIED," and "Nothing in this report is accepted doctrine or a Mike decision."

---

## 6. TASK 4 — Connector Architecture

### 6.1 Objective

Give Dispatch a governed, reusable boundary for external systems before any of those systems are selected or activated, with one working mock connector and no false connection claims anywhere.

### 6.2 Architectural position

Connectors transport and normalize information. They do not own lifecycle transitions, human decisions, pricing authority, acceptance authority, scheduling truth, or operational doctrine. The chain is: Intelligence Layer acquires; Intelligence Analyst reasons; Route Risk evaluates mission consequence; COMI routes communications; Publisher produces approved communications; Spine owns lifecycle truth; Mike decides. A connector may never call Spine transition code, never write to `loads.status`, and never write to any Current Reality table. Enforce this structurally (module boundaries, import rules, or tests), not by convention alone.

### 6.3 Connector contract

Define one interface/protocol every connector implements, supporting where applicable:

connector identity · provider identity · capability declaration · configuration status · authentication status (never exposing secrets) · connection health · last successful communication · source timestamp · received timestamp · source reference · freshness · confidence · normalized payload · error result · retry status · audit event · status from the Section 1.8 vocabulary (`LIVE`, `CONFIGURED`, `UNCONFIGURED`, `SIMULATED`, `UNAVAILABLE`).

Every payload a connector returns must carry its status and provenance. Any consumer displaying connector data must display the status. A `SIMULATED` or `UNAVAILABLE` payload must never render as operational intelligence without that label.

### 6.4 Connectors to define

Create registered connector definitions (interface implementations may be skeletal but must return truthful `UNCONFIGURED` status) for:

```
Route Risk Connector
Accounting Connector
Scanner Connector
Outlook Connector
Email Transport Connector
Load Board Connector
Mapping and Routing Connector
Future External Intelligence Connector
```

Where the repository already has Outlook, email, or other integration code, wrap or migrate it behind the contract rather than duplicating it. Do not change existing Outlook behavior beyond routing it through the boundary; scheduling truth rules in Section 1.5 are unchanged.

### 6.5 Route Risk specifics

Route Risk is an Operational Intelligence function, not a weather/traffic feed. Its connector may collect weather, traffic, DOT restrictions, law-enforcement conditions, port conditions, disaster conditions, fuel conditions, security conditions, road restrictions, mission-specific advisories. Its evaluation layer (separate from the connector) may produce route findings, affected-area references, consequence levels, COMI notification requirements, Mission Visibility updates, stakeholder communication inputs, map-visual requirements. Route Risk must not accept or cancel loads and must not change Current Reality without a governed Spine event or human authority. Build the connector and the normalized payload shape; the evaluation layer is in scope only as an interface and one test proving it cannot write to Current Reality.

### 6.6 Mock connector

Implement one safe mock connector (choose Route Risk or Mapping) that returns clearly `SIMULATED` data, exercises the full contract including error, retry, and audit paths, and is used by the connector tests and, optionally, by Task 2 rehearsal mode.

### 6.7 Resilience

Prove that an `UNCONFIGURED` or `UNAVAILABLE` connector does not prevent Dispatch's core local operation (Task 2 proof path must complete with every connector unconfigured except where the step explicitly requires one). A function that requires a connector fails with a clear, labeled refusal, not a silent degradation.

### 6.8 Acceptance evidence (repository)

- interface/protocol tests
- the mock connector with tests
- simulated labeling visible in any consuming surface
- failure handling tests (timeout, auth failure, malformed payload)
- configuration validation tests
- secret redaction tests (no secret value appears in status, logs, errors, or audit)
- a test asserting no connector can emit `LIVE`/`CONNECTED`/`VERIFIED`/`CURRENT` without evidence of a real exchange
- audit records for every connector attempt
- `docs/connectors/PROVIDER_INSERTION.md` documenting how a future real provider is added for each connector, with the Mike decisions that gate activation
- the Section 6.7 proof

---

## 7. Dependency map and parallelism

Run in parallel from the start: Task 1, Task 3, Task 4, and the application-code portions of Task 2 (rehearsal mode, readiness utilities, report generator).

Ordered dependencies:

- Task 2 proof execution (steps 1, 16, 17) uses the Task 1 launcher. Build Task 1 controls before executing the Task 2 rehearsal run.
- Task 2 step 9 and connector resilience proof (6.7) use the Task 4 boundary. Land the connector contract and Outlook wrapping before the rehearsal run.
- Task 3 has no dependencies on the others and none of the others depend on it.
- The completion report is written last.

Do not insert resolve stops between tasks or between sub-steps. The only halts permitted are the Mike-only items in Section 8, and those are recorded as questions in the completion report, not blocking pauses — proceed with the rest of the mission.

---

## 8. Mike-only decisions — do not resolve, do not default

Record each as a question in the completion report with your recommendation clearly marked as a recommendation. Proceed with everything that does not depend on the answer.

1. Any execution of `PROPOSED_ORGANIZATION_ACTIONS` from Task 3.
2. Acceptance of any `Doctrine` or `Decision` candidate as actual doctrine or decision.
3. Running a live revenue load through Dispatch.
4. Activating any real external provider behind any connector.
5. Any live Outlook event creation not already governed by existing authorized code paths.
6. Any change to `loads.status` semantics or Spine transition rules.
7. Any change to the authoritative-portal decision.
8. Any HOS/ELD input, now or later.
9. Any deletion or purge of data, including rehearsal data, on Mike's machine.
10. Any change to the designated Task 3 paths (`D:\Sandbox\Play Pen` and `D:\Sandbox\Play Pen\Dispatch`).
11. Any Windows-environment fact the repository could not establish and you needed to assume.

---

## 9. Prohibited actions

- Creating any record bearing a Mike attribution from Section 1.1.
- Letting rehearsal, sample, mock, or simulated data appear unlabeled anywhere.
- Citing repository test results as operational proof.
- Reporting `LIVE`, `CONNECTED`, `VERIFIED`, or `CURRENT` without evidence.
- Modifying, moving, or executing anything in the Sandbox.
- Committing runtime secrets, logs containing secrets, rehearsal databases, evidence files, or backups to Git.
- Restoring a backup into the live database or live evidence store.
- Adopting Jules portal runtime, security, state, or upload behavior.
- Weakening fail-closed authentication, CSRF protection, token expiration/revocation, or ownership protections for convenience in any task.
- Giving a connector, the launcher, or Route Risk any path to Current Reality.
- Skipping existing tests, adding warnings, or lowering coverage. The suite must remain at 0 failed / 0 skipped / 0 warnings; coverage must not drop below the current 93.73%.

---

## 10. Deliverables

### 10.1 One consolidated pull request (application code)

Contains: Task 1 launcher and its repository-side support; Task 2 rehearsal mode, readiness utilities, proof-report generator, and procedure docs; Task 3 read-only inventory/classification tooling if it lives in the repo; Task 4 connector contract, registry, eight connector definitions, mock connector, boundary enforcement, docs; `docs/readiness/RECON.md`; HOS/ELD language corrections; `.gitignore` additions; all tests. PR description summarizes each task in a few lines and links to the completion report.

### 10.2 Local-machine artifacts (not committed)

- `proof/launcher/LAUNCHER_PROOF.md` and launcher logs
- `proof/load/OPERATIONAL_LOAD_PROOF.md` with evidence hashes, backup, and restore-destination listing
- the nine Task 3 outputs in the designated output folder

### 10.3 One completion report — `docs/readiness/COMPLETION_REPORT.md` (committed)

Structure, in this order:

1. **Readiness statement** — one paragraph. Every claim tagged IMPLEMENTED, OPERATIONALLY PROVEN, or UNVERIFIED.
2. **Commit and version** at completion; test totals and coverage before and after.
3. **Task 1** — implementation choice and rejected alternatives; proof summary with pointer to `LAUNCHER_PROOF.md`; unverified items with exact verification commands.
4. **Task 2** — rehearsal result line; what Mike performed / Code verified / remains unverified; the exact paths; Outlook status; pointer to `OPERATIONAL_LOAD_PROOF.md`; real-load readiness checklist status.
5. **Task 3** — files inventoried, class counts, sensitive-material count (no contents), confirmation of read-only pass, pointer to outputs; explicit statement that no organization action was taken.
6. **Task 4** — connectors defined and their statuses (expected: all `UNCONFIGURED` except the mock at `SIMULATED`); resilience proof result; provider insertion doc pointer.
7. **HOS/ELD corrections** — each location changed and the before/after language.
8. **Mike-only decisions** — the Section 8 list with your recommendations, marked as recommendations.
9. **Doctrine compliance check** — one line per Section 1 item confirming compliance or describing the deviation and why.
10. **Known gaps and risks** — plain language, no softening.

Write the report so Mike can read Section 1 alone, at a fuel stop, and know exactly where Dispatch stands.

---

## 11. Closing instruction

Work at maximum practical capacity. Prefer the boring, proven, inspectable implementation over the clever one. When you are uncertain whether something is proven, it is not. When you are uncertain whether a decision is Mike's, it is. Everything else, proceed.
