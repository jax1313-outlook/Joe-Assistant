# JOE - Build Report

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Location:** `D:\SANDBOX\Assistan_Building\Assistant_Plugin`
**Built:** 2026-08-25
**Final authority:** Mike Zachary

---

## MISSION RESULT

The assembled JOE, the Level 1 Assistant exists locally, launches from a
double-clickable Windows launcher, and operates. 106 assembly tests pass. 18 of
18 local proof steps pass. Three of the six external capabilities are **live**;
three are not, and each is reported truthfully in the running program.

Nothing was merged into Dispatch. No repository was created. No pull request
was made. Dispatch was never contacted.

## APPLICATION LAUNCH PATH

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\START_JOE.cmd
```

Double-click. Window appeared in **4.6 seconds**, title
`JOE, the Level 1 Assistant`, process `pythonw`, **0 console
windows**.

## LIVE CONNECTION RESULTS

Measured, not assumed:

| Capability | Result | Evidence |
| --- | --- | --- |
| **Library** | **LIVE** | Company Library indexed, 28 documents + 6 sample = 34. Real documents returned (e.g. `Constitutions/DISPATCH_CONSTITUTION_v3.md`) |
| **Outlook** | **LIVE, read-only** | Outlook 16.0.0.20326, profile "Outlook". Calendar 601 items, Inbox 273, Contacts 145. `live_connection: True`. Calendar returned in **date order**, recurrences expanded, 14-day window |
| **Voice output** | **LIVE** | System.Speech; voices Microsoft David Desktop, Microsoft Zira Desktop; rendered 115,546-byte WAV; **spoke aloud** during proof |
| **Voice input** | **engine binds, unproven** | Recognizer `MS-1033-80-DESK`; Internal Microphone (Conexant ISST Audio) present. Recognition needs a person at the mic |
| **Research** | **SAMPLE DATA** | No provider configured. Fixtures only, labelled everywhere |
| **Dispatch** | **NOT CONNECTED** | No published interface exists. Contract only |
| **Printing** | **NOT IMPLEMENTED** | Request recorded; nothing printed |
| **Reasoning provider** | **NOT CONNECTED** | Cannot compose original answers |

## TEST RESULTS

**106 assembly tests. 105 passed, 1 skipped, 0 failed.**

The skip is the live-Outlook calendar ordering test, which runs only with
`ASSISTANT_TEST_OUTLOOK=1`. It was run separately against the real calendar and
passed.

| Group | Tests |
| --- | --- |
| `TestLaunch` | 8 |
| `TestRouting` | 12 |
| `TestRetention` | 18 |
| `TestSelection` | 8 |
| `TestLabelling` | 8 |
| `TestGovernance` | 12 |
| `TestAdapters` | 17 |
| `TestDispatchBoundary` | 8 |
| `TestContainment` | 7 |
| `TestDriverMode` | 4 |
| `TestCognitiveLoad` | 4 |

Plus **350 component tests** in `ASST\1..6`, unchanged and still passing.
**Combined: 456.**

Detail: `JOE_TEST_REPORT_v1.md`.

## LOCAL PROOF RESULTS

**18 of 18 steps passed.** Full evidence:
`JOE_LOCAL_PROOF_REPORT_v1.md`.

Selected observations:

```
 1  window visible True, 4.6 s, title matched, 0 consoles
 4  created 3:00:00 before expiry - exactly three hours
 5  TEMPORARY -> SAVED, LEVEL_1 -> LEVEL_2, expiry cleared
 6  FORMAL / LEVEL_3, destination "Ideas", artifact produced=False
 7  TEMPORARY -> PRINT_READY, LEVEL_1 -> LEVEL_1 (unchanged)
 8  DELETED, driver_request purged, refuses later commands
 9  Company Library live, sample labelled separately
10  Outlook LIVE, date_with_recurrences, 9 of 601 in a 14-day window,
    chronological True, 0 writes
12  TTS bound, 115546-byte WAV, spoken aloud True
13  restart restored 6 records; SAVED / FORMAL / PRINT_READY preserved
16  dispatch connected False, no write method exists, 0 operational writes
17  3 escape attempts blocked, 0 records outside the plugin
```

## EXACT FILES CREATED

110 files under `Assistant_Plugin\`. By area:

**Application core (5)** — `app\__init__.py`, `bootstrap.py`, `config.py`,
`logbook.py`, `router.py`, `service.py`

**Adapters (6)** — `adapters\__init__.py`, `outlook_com.py`, `voice_sapi.py`,
`research_provider.py`, `library_fs.py`, `dispatch_port.py`

**Contracts and governance (2)** — `contracts\__init__.py`,
`governance\__init__.py`

**Entry point and UI (2)** — `joe_main.py`, `ui\window.py`

**Launchers (8)** — `START_JOE.cmd`, and in `launchers\`:
`STOP_JOE.cmd`, `RESTART_JOE.cmd`, `JOE_STATUS.cmd`,
`RUN_TESTS.cmd`, `RUN_PROOF.cmd`, `OPEN_LOGS.cmd`, `OPEN_DATA.cmd`

**Configuration (2)** — `joe.config.json`,
`joe.config.template.json`

**Tests and proof (2)** — `tests\test_assistant_plugin.py`,
`proof\run_proof.py`

**Documents (11)** — the full set in `docs\`, listed in section
"REQUIRED DOCUMENTS" below

**Deployment (4 + candidate)** — `Deployment\README.md`, `VERSION.txt`,
`DEPENDENCIES.txt`, `PACKAGE_ASSISTANT.cmd`, and
`Deployment\Assistant_Plugin_v1.0.0\` (93 files, 0.65 MB)

**Packaged components (copied unchanged)** — `ui\assistant_ui\`,
`memory\assistant_memory\`, `library\assistant_library\`,
`outlook\assistant_outlook\`, `research\assistant_research\`,
`voice\assistant_voice\`, plus `library\sample_corpus\`,
`outlook\sample_data\`, `research\fixtures\`, and
`memory\retention_language.py` (reused verbatim from Sandbox Engine v1)

## EXACT FILES MODIFIED

**Outside the plugin folder: none.**

The six workstream folders `ASST\1..6` were **not modified**. Verified: zero
files changed since the build began. **No workstream defect required
correction**, so the defect-correction procedure in mission section 6 was not
invoked.

Files modified inside the plugin during the build, after being created by it:

| File | Change | Why |
| --- | --- | --- |
| `app/service.py` | retention commands no longer create a record or move the selection | defect found by running - see below |
| `app/router.py` | explicit retrieval verbs outrank topical words; calendar patterns narrowed | defect found by running - see below |
| `contracts/__init__.py` | added `READY` mode and `chip()` | Outlook lazy state displayed as UNAVAILABLE when it was ready |
| `governance/__init__.py` | HELP exempted from the provenance check | help text was falsely flagged as an operational claim |
| `ui/window.py` | compact status chips with hover detail | status strip overflowed and hid two capabilities |
| `tests/test_assistant_plugin.py` | first-party-only source scanning | two of my own tests matched their own patterns |
| `configuration/joe.config.template.json` | regenerated by JSON edit | template shipped a machine-specific path |
| `adapters/outlook_com.py` | calendar sorted by `[Start]`, recurrences expanded, restricted to a date window; ordering reported | **fix requested by Mike** - calendar returned folder order |
| `app/service.py` | calendar response states its window and ordering | same fix |
| `configuration/*.json` | `calendar_window_days`, `calendar_look_back_days` | same fix |

## EXACT COMMANDS RUN

```
py -m unittest discover -s tests -v
py proof\run_proof.py --speak
py joe_main.py --status
py joe_main.py --headless "Find the rate floor policy"
launchers\RUN_TESTS.cmd
launchers\RUN_PROOF.cmd
Deployment\PACKAGE_ASSISTANT.cmd
START_JOE.cmd                       (via Start-Process, the double-click path)
```

Capability probes, before building: PowerShell checks for System.Speech
synthesis and recognition, audio devices, Outlook COM registration, Outlook
profiles, and one read-only Outlook COM connection.

## DEFECTS FOUND AND FIXED

The first two were found by operating the assembled program; neither would have
been caught by reading it. The third was flagged as a limitation in the first
build and fixed on request.

**1. Retention commands hit the wrong record.** `ask("Save this")` saved
correctly, then created a *new* record for the phrase itself and selected it -
so a following `"Print this"` landed on the "Save this" record. Fixed: a
retention command acts on the selected record, creates nothing, and does not
move the selection. Three tests now hold it.

**2. "Look up the appointment policy" went to the calendar.** The Operations
route matched the bare word `appointment`. Fixed: explicit retrieval verbs
outrank topical words; calendar patterns narrowed to `my appointments` and
`appointments today/tomorrow/this week`.

**3. Calendar came back in folder order, not date order.** Flagged as a known
limitation in the first build; **fixed on request**. Against the real calendar,
folder order interleaved past and future (`08/11 -> 12/11 -> 12/18 -> 07/15`),
so "what is on tomorrow" could not be answered. Now sorted by start time, with
recurring events expanded, restricted to a 14-day window from midnight today.
The three fallback levels each report themselves rather than degrading
silently. Seven tests hold it, one reading the live calendar.

**4. The deployment template shipped a machine-specific OneDrive path.** My
verification check passed because the placeholder string appeared in the
*comment* it had just inserted, not in the path. Fixed by editing the JSON
structurally and verifying the path **values**, not the file text.

---

## IMPLEMENTED AND OPERATIONALLY PROVEN

1. Double-click launch from `START_JOE.cmd`; window visible in 4.6 s with
   no console.
2. Typed request producing a visible written response.
3. Complete written interaction record, kept for parked review.
4. Interaction history with state, level, and a marked selection.
5. Level 1 default, `TEMPORARY`, three-hour expiry, measured exactly.
6. Save to Level 2 `SAVED`, expiry cleared.
7. Level 3 to `FORMAL`, destination preserved, artifact request created and
   reported as not produced.
8. Print to `PRINT_READY` **without changing interaction level**, expiry
   cleared, no claim of physical printing.
9. Delete: content purged, removed from the active view, later commands refused.
10. Expiration by sweep-on-access, with expired records absent from the view.
11. **Live Library search** of the real Company Library, with company and
    sample material separately labelled.
12. **Live read-only Outlook**: calendar, mail, and contacts, with provenance
    and as-of time. **Calendar in date order**, soonest first, recurrences
    expanded, within a stated window - verified chronological against the real
    calendar.
13. **Live spoken output**: engine bound, WAV rendered, spoke aloud.
14. Truthful capability labelling for all five capabilities.
15. Research correctly reported as SAMPLE DATA, never as live.
16. Governance refusal of approval claims, action claims, and
    silence-is-consent phrasing.
17. Stale-data warnings on live readings older than 15 minutes.
18. Adapter failure isolation - a failing capability leaves the rest working.
19. Records surviving close and reopen.
20. Operation with Outlook unavailable.
21. Operation with voice unavailable.
22. Path containment - three escape attempts blocked, zero records outside.
23. Dispatch never contacted; no operational write method exists.
24. Deployment candidate built and run standalone from its own folder.

## IMPLEMENTED BUT NOT OPERATIONALLY PROVEN

1. **Voice input.** Recognizer binds, microphone present, Listen button wired.
   Recognition of real speech is not proven - it needs a person at the mic.
2. **The tkinter window's click and keyboard paths.** Exercised by hand and
   captured in a screenshot; no automated UI driver.
3. **Real three-hour expiration.** Proven on a simulated clock only.
4. **Mail and contact ordering.** Only the calendar was date-ordered. Inbox and
   contact order is whatever Outlook returns - usually, but not guaranteed to
   be, by received time.
5. **`JOE_ROOT` / `JOE_CONFIG` overrides.**
6. **Behaviour at scale** - large Library, large mailbox, long session.
7. **Any machine other than this one.**

## NOT IMPLEMENTED

1. **Any reasoning or language provider.** JOE cannot compose an
   original answer.
2. **Summarize, draft, and train capabilities** - permitted by doctrine,
   not built.
3. **Printing.** Request only.
4. **Dispatch integration.** Contract only.
5. **Background expiration timer.**
6. **Hands-free or wake-word voice activation.**
7. **PDF, xlsx, pptx, doc Library formats.**
8. **Outlook write of any kind** - deliberately absent, permanently.
9. **Message editing, search, export, clipboard.**
10. **Multiple conversations or sessions.**
11. **Encryption or access control on records.**
12. **Any network capability.**

## BLOCKED BY EXTERNAL SERVICE OR CREDENTIAL

| Capability | Exact blocker | What would unblock it |
| --- | --- | --- |
| **Research (live)** | No approved research provider or credential is configured | Mike approves a provider; an adapter is written in `adapters\`; `research.provider` is set |
| **Reasoning provider** | None approved or configured | Mike approves a provider and supplies a credential |
| **Dispatch integration** | **No approved Dispatch interface has been published** | Dispatch publishes a named, versioned, read-only interface. This is Dispatch's decision, on Dispatch's terms. JOE waits. |
| **Voice input proof** | Requires a person to speak into the microphone | Mike presses Listen and speaks |
| **Printing** | No printing service is bound | A separate mission binding a print path |

Nothing is blocked by a missing credential JOE could have obtained.
The Outlook connection uses the Windows session already signed in; no API key,
token, or password exists anywhere in this program.

## KNOWN LIMITATIONS

Full list: `JOE_KNOWN_LIMITATIONS_v1.md`. The three that matter
most:

1. **No reasoning provider.** The program finds, reads, watches, and keeps. It
   does not think. Ask it something with no source and it says so.
2. **No expiration timer.** Records expire when the program checks, and it
   checks whenever it shows the history. If it is never opened, nothing expires.
3. **Only the calendar is date-ordered.** Mail and contacts still come back in
   folder order.

## DISPATCH INDEPENDENCE RESULT

**PASS.**

- Dispatch was **never contacted**. `dispatch_contacted` is a literal `False`;
  `operational_writes` is `0`.
- **No Assistant code was copied into Dispatch.** Verified by search.
- **No Dispatch path, endpoint, credential, or handle** exists anywhere in the
  program.
- **No Dispatch pull request** was created. **No repository** was created.
- JOE has run only ever with Dispatch absent - which is the strongest
  form of the removability proof available: it has never had it.
- **Removing JOE is a folder deletion.**

All fourteen drift tests in mission section 23 pass. Verified independently of
the proof harness: 0 Manager classes, 0 networking imports in first-party code,
0 files written outside the plugin, 0 modifications to `ASST\1..6`.

## DEPLOYMENT READINESS RESULT

**Ready for local use by Mike Zachary. Not ready to be called complete.**

Ready:

- installs by copying a folder; uninstalls by deleting it
- launches by double-click, no command line
- 98 assembly + 350 component tests pass
- 18 of 18 proof steps pass
- deployment candidate built (90 files, 0.53 MB) and verified running
  standalone with only the shipped template
- Dispatch independence proven

Not ready, and why the word "complete" is not used:

- **Research runs on fixtures**, so per the evidence standard this capability is
  not complete.
- **Voice input is unproven.**
- **Dispatch integration does not exist** - only a contract.
- **No reasoning provider**, which is the largest functional gap.

## REVIEW HANDOFF LOCATION

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\docs\JOE_REVIEW_HANDOFF_v1.md
```

## REQUIRED DOCUMENTS

All eleven exist in `Assistant_Plugin\docs\`:

```
JOE_CONTEXT_v1.md
JOE_CONSTITUTION_v1.md
JOE_ARCHITECTURE_v1.md
JOE_INTERFACE_CONTRACT_v1.md
JOE_OPERATOR_GUIDE_v1.md
JOE_DEPLOYMENT_GUIDE_v1.md
JOE_TEST_REPORT_v1.md
JOE_LOCAL_PROOF_REPORT_v1.md
JOE_BUILD_REPORT_v1.md
JOE_KNOWN_LIMITATIONS_v1.md
JOE_REVIEW_HANDOFF_v1.md
```

Governing doctrine is cited, not duplicated:
`JOE_CONSTITUTION_v1\` (v1.0, Documents 1-5).

**Mike Zachary remains final authority.**
