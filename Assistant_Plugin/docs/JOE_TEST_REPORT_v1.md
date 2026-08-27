# JOE - Test Report

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py` / `pyw`, tkinter 8.6, standard library only

---

## Result

**259 tests. 258 passed. 1 skipped. 0 failed. 0 errors.**

The skip is the live-Outlook calendar ordering test, which runs only with
`ASSISTANT_TEST_OUTLOOK=1` so the suite never starts Outlook by surprise. It was
run separately with Outlook enabled and passed.

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\launchers\RUN_TESTS.cmd
```

Underneath: `py -m unittest discover -s tests -v`.
Raw output: `logs\last_test_run.txt`. Source: `tests\test_assistant_plugin.py`.

Every test writes only inside `tests\_workspace`, removed in `tearDown`. No
test contacts Dispatch. Outlook is disabled during tests unless
`ASSISTANT_TEST_OUTLOOK=1`, so the suite never starts Outlook by surprise.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestLaunch` | 8 | Service starts; all six components packaged and importable; entry point exists; the double-clickable launcher exists and references the entry point; all seven secondary launchers exist; clean shutdown; all five capabilities report status; operating mode stated. |
| `TestRouting` | 12 | All nine retention phrases route with the right intent; retention beats other language; Level 3 destination preserved; Library, Operations, Research, Explain, Help language; unmatched language falls back to Answer; capitalisation and punctuation irrelevant; driver-mode detection; subject extraction. |
| `TestRetention` | 18 | Level 1 default; three-hour expiry; Save to Level 2; Level 3 to Formal with destination; artifact request not produced; **Print does not change interaction level**; Print clears expiry; Print never claims physical printing; Print from Level 2 keeps Level 2; Delete removes from view and purges content; deleted record refuses later commands; **retention creates no extra record**; **retention does not move the selection**; two commands target the same record; sweep-on-access expiry; saved records survive a sweep; **records survive a restart**. |
| `TestSelection` | 8 | New interaction becomes selected; history marks exactly one selected row; select by id; unknown id refused; retention with nothing selected refused; empty request refused; UI imports without opening a window; **UI holds no business logic**. |
| `TestLabelling` | 8 | Library results labelled by source; **sample data announced**; research fixture never called live; research status truthful; voice status matches the probe; **Dispatch never reported as connected**; Outlook status reflects configuration; status dict declares no Dispatch contact and zero operational writes. |
| `TestGovernance` | 12 | Approval claims refused; completed-action claims refused; **silence-is-consent phrasing refused**; ordinary recommendations pass; print-request wording allowed; operational claim without provenance flagged; help text exempt; **stale live data flagged**; fresh data not flagged; **authority flags forced false**; response dict always reports no authority; claim-detection helpers. |
| `TestAdapters` | 17 | **A failing capability does not stop the application**; Outlook adapter refuses a non-read script; generated scripts contain no write call; disabled Outlook returns unavailable, not sample; research never invents findings; a named-but-unimplemented provider fails loudly; Library reports missing sources; company material outranks sample at equal score; disabled voice reports its blocker; **calendar script sorts by start date**; **window configurable and never zero**; **mail and contacts not date-windowed**; **ordering reported honestly across all three fallback levels**; **provenance states ordering and window**; **the calendar script still passes the read-only guard**; **live calendar verified chronological** (runs with `ASSISTANT_TEST_OUTLOOK=1`). |
| `TestDispatchBoundary` | 8 | Port not connected; read returns unavailable, not a guess; **unpermitted read refused**; **no operational write method exists**; submission is a proposal with `accepted`/`performed`/`auto_execute` all false; unpermitted submission kind refused; nothing drains the queue; no Dispatch path in configuration. |
| `TestContainment` | 7 | Writes outside the plugin refused; runtime data and logs inside the plugin; every record file inside the plugin; **no reference to Dispatch internals**; **no Manager component anywhere**; **provider code confined to adapters**. |
| `TestDriverMode` | 4 | Spoken summary exists for every response; respects the word limit; **written response always preserved**; no voice-only record. |
| `TestCognitiveLoad` | 4 | **No record ID required to operate**; ordinary language needs no syntax; **no confirmation queue created**; the answer comes before documents. |

## Defects found by running the program, and fixed

The first two were found by operating the assembled program, not by reading it.
Neither would have been caught by inspection. The third was flagged as a
limitation in the first build and fixed on request.

### 1. Retention commands created their own records and stole the selection

`ask("Save this")` applied the save correctly, then created a **new** record for
the phrase "Save this" and selected it. A following `ask("Print this")` therefore
landed on the wrong interaction.

Observed:

```
  "Save this"   -> calendar record became SAVED        (correct)
  "Print this"  -> applied to the "Save this" record   (wrong)
```

Fixed: a retention command acts on the selected record, creates no record of
its own, and does not move the selection. Held by
`test_retention_command_creates_no_extra_record`,
`test_retention_command_does_not_move_the_selection`, and
`test_two_commands_target_the_same_record`.

### 2. "Look up the appointment policy" routed to the calendar

The Operations route matched the bare word `appointment`, so a Library request
about a policy document was sent to Outlook.

Fixed: explicit retrieval verbs (`find`, `search for`, `look up`, `pull up`,
`where is`) now outrank topical words, and the calendar patterns were narrowed
to `my appointments` and `appointments today/tomorrow/this week`. Held by
`test_library_language`.

### 3. Calendar returned folder order, not date order

Flagged as a known limitation in the first build and **fixed on request**.

An Outlook `Items` collection is in folder order by default, which is not
chronological. Observed against the real calendar:

```
  folder order (broken):  08/11 -> 12/11 -> 12/18 -> 07/15 -> 06/30
  date order (fixed):     08/25 11:00 -> 08/25 13:25 -> 08/25 16:00 -> 08/29 ...
```

Past and future were interleaved, so "what is on my calendar tomorrow" could
not be answered from the first N items.

Fixed in `adapters/outlook_com.py`: `Sort("[Start]")`, then
`IncludeRecurrences = true`, then `Restrict` to a date window. The window is
required - a recurring series with no end date would otherwise iterate forever.

**The fallbacks report themselves rather than degrading silently:**

| `ordering` | Meaning |
| --- | --- |
| `date_with_recurrences` | full fix - sorted, expanded, windowed |
| `date_no_recurrences` | sorted, but the date filter or expansion failed |
| `folder` | even sorting failed; labelled `NOT chronological` in the response |

Held by seven tests, one of which reads the live calendar and asserts the
timestamps are non-decreasing.

## Two of my own tests were wrong, and were corrected

Worth recording, because a test that fails for the wrong reason teaches nothing:

- A containment scan matched `.mdb` **inside its own regex string**, and a
  provider scan matched `System.Speech` inside the packaged Voice component's
  `NOT_IMPLEMENTED_ENGINES` list - a mention, not a call. Both now scan
  first-party code only, via `_first_party_sources()`, excluding the vendored
  component packages (which carry their own suites) and the test file itself.

## Component suites, unchanged

The six packaged components were copied in **unmodified** and their own suites
still govern them. No workstream defect required correction during this build.

| Component | Its own tests |
| --- | --- |
| Assistant UI | 39 |
| Assistant Memory | 45 |
| Assistant Library | 53 |
| Assistant Outlook | 63 |
| Assistant Research | 78 |
| Assistant Voice | 72 |
| **Component total** | **350** |
| **Assembly tests** | **259** |
| **Combined** | **609** |

## Microsoft 365 Copilot coverage

51 tests, all against a **mocked Graph transport**, so the whole contract is
proven without a tenant, a licence, or a sign-in.

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestCopilotProvider` | 13 | Conversation created with an empty body; chat posts to the conversation; **the reply is the last message, not the echo**; `locationHint` always sent; **multi-turn reuses one conversation**; reset starts a new one; `additionalContext` sent and empty entries omitted; OneDrive/SharePoint files sent as `contextualResources`; **`webContext` always explicit, never defaulted**; web search enabled per turn; research is the only path that enables web; context truncated to the limit. |
| `TestCopilotAttribution` | 4 | Citations parsed and preserved; annotations kept separate from citations; **sensitivity label and encryption flag preserved**; null sensitivity fields dropped. |
| `TestCopilotProvenanceClasses` | 8 | Citations without web are `COPILOT_WORK_GROUNDED`; with web are `COPILOT_WEB_GROUNDED`; no citations is `COPILOT_GENERAL_REASONING`; supplied files keep it work-grounded; **Copilot never claims a local or Dispatch source class**; provenance carries the class; local reads declare their own; all seven classes exist. |
| `TestCopilotContract` | 6 | The five contract methods exist; answers never carry authority; **no send/approve/decide/schedule method exists**; every boundary flag `False`; preview declared; no client secret used. |
| `TestCopilotFailure` | 5 | **Streamed turn falls back to synchronous**; API failure returns an error answer, not an exception; an empty reply is reported, not invented; **error text carries no header material**; an unsigned-in provider reports honestly and composes nothing. |
| `TestCopilotAuthentication` | 10 | Unconfigured state; **no client secret is used** (public client, no `client_credential`, no confidential-client path); **status exposes no token material**; no auth header when signed out; **MSAL is used, not hand-rolled OAuth** (no `oauth2/v2.0/token`, no `grant_type`); **the cache is DPAPI-encrypted or memory-only, never plain text**; all seven Graph scopes requested; sign-out reports what it cleared; **no token written in plain text**. |
| `TestCopilotInService` | 4 |

Contact ordering adds `TestContactOrdering` (5 tests), which hold the order
to what a person sees on screen rather than to what Outlook claims. Not selected by default in a test config; selecting it builds the backend and the app still works unsigned-in; **Dispatch stays NOT CONNECTED**. |

## Defects found in this pass, and fixed

**8. Two of my own security tests were wrong.** One scanned configuration raw
text for the word "secret" and tripped on a comment saying *"tenant_id and
client_id are not secrets"* - the very sentence written to make that point. The
other matched `client_secret` inside the honest status flag
`client_secret_used`. Both now check what matters: configuration **values** and
field **names**, and whether MSAL is built as a public client with no
credential passed. A test that fails for the wrong reason teaches nothing.

**9. Contacts were reported alphabetical over a field Outlook leaves empty.**
`Sort("[FileAs]")` is the documented way to get an alphabetical address book,
and it is what the earlier ordering fix used. On this profile `FileAs` is empty
on every synced contact - `LastName` is populated, `FileAs` is not. Sorting on
an empty key returns near-folder order, so the folder was labelled
`name_asc`, "alphabetical by name", while reading on screen as unsorted. The
label was the defect: the program was telling Mike it had fixed the exact thing
he reported. Contacts are now fetched whole, sorted in Python on the name that
is actually displayed, truncated after sorting rather than before, and reported
as `display_name_asc`. Contacts with no name at all are listed last and counted
in a note. Five tests and proof step 20 now check the order **in fact**, not
only the label.

**10. One of my own tests asserted a fact that had stopped being true.**
`test_copilot_not_selected_by_default` was written when the shipped provider was
`none`. Selecting Copilot made it fail - correctly. The assertion, not the
program, was what needed changing, and it now locks the distinction that
matters: Copilot is **selected**, is **not signed in**, and must never be
reported as connected.

**11. A timeout was being reported as a missing mailbox.** Outlook went
unresponsive during a live mailbox investigation. `accounts()` returned an empty
list, cached it, and `knows_account()` answered `False` — for the **approved**
`Ops@l1truck.com`, which had read fine an hour earlier. That is the same answer
it gives for a mailbox genuinely not in the profile, so ignorance was
indistinguishable from a finding. Worse, the failure was cached, turning a
one-minute outage into a permanent "there are no mailboxes."

`knows_account()` is now tri-state — `True` present, `False` absent, **`None`
could not be asked** — with `account_status()` returning `"present"`,
`"absent"`, or `"unknown"` for anything a person reads. `None` is falsy, so
every existing caller behaves exactly as before. Failed enumerations are no
longer cached, so recovery is automatic with no refresh flag. Seven tests in
`TestAccountDiscoveryHonesty` hold the distinction, including that a transient
failure followed by a success returns the truth.

## The two proof runners are tested before Mike ever runs them

Both remaining proofs need Mike. `PROVE_COPILOT.cmd` needs an Entra
registration, admin consent, and a sign-in first; `PROVE_VOICE_INPUT.cmd` needs
him at the microphone. In both cases he gets essentially one sitting, and the
judgment code inside each runner had never executed.

So it is exercised here instead, without a tenant and without a voice.

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestCopilotProofRunner` | 9 | A good answer passes; work- and web-grounded answers pass; **an empty reply fails** rather than passing on fluency; a provider failure fails; **every forbidden source class fails however good the answer** — `LOCAL_LIBRARY`, `LOCAL_OUTLOOK`, `ROUTE_RISK_EVENT`, `DISPATCH_FACT`; a non-Copilot class fails; absent provenance is not treated as wrong provenance; the forbidden list matches `SourceClass`; **a blocked run writes a report that claims nothing**. |
| `TestVoiceProofRunner` | 11 | Exact match scores 1.0; casing and punctuation do not penalise the speaker; nothing recognized scores 0; **extra padding words do not defeat a correct phrase**; **a repeated word is not double-counted** to satisfy two expected words; the 0.6 threshold rejects a mostly-missed phrase; a blocked run claims nothing; **a partial run is reported as NOT proven**. |

The verdict logic in `prove_copilot.py` was extracted into a pure `judge()`
function for exactly this reason. The alternative was that Mike completes five
Entra steps, signs in, and only then discovers whether the judgment code works.

## What the automated suite does NOT prove

1. **The tkinter window itself.** The suite checks the UI module imports, opens
   no window, and contains no business logic. Clicks, typing, selection, and
   rendering are exercised in the local proof and by hand, not by an automated
   UI driver.
2. **Live Outlook.** Disabled during tests by default so the suite never starts
   Outlook. Live reading is proven in the local proof instead.
3. **Audible speech and microphone input.** Proven in the local proof (speech)
   and not proven at all (microphone - it needs a person).
4. **Real three-hour expiration.** Tested on a simulated clock.
5. **Concurrency.** One operator at a time is assumed.
6. **Any Dispatch interaction**, because there is nothing to interact with.
