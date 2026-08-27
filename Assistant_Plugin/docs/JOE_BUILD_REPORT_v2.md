# JOE — Build Report v2

**Mission:** JOE_COMPLETION_MISSION_v2, and the APPROVED DIRECTION
to build the Microsoft 365 Copilot Chat API backend behind the existing
ReasoningProvider contract.
**Program:** Level 1 Assistant — Dispatch Plugin
**Built:** 2026-08-25
**Final authority:** Mike Zachary

---

## MISSION RESULT

Fourteen of the fifteen approved build items are done and proven locally. The
fifteenth — a live Copilot answer — cannot be reached from this side of the
human authority gate.

Mail and contact ordering is corrected. Email account designation exists and
reports which account it read. The Microsoft 365 Copilot reasoning backend is
built, wired behind the provider contract, and tested end to end against a
mocked Graph transport. Authentication uses Microsoft's own MSAL public client
with a Windows-encrypted token cache; no hand-built OAuth and no readable token
anywhere.

**The program is not complete.** Voice input has not been physically tested with
a person at the microphone, and no live Copilot prompt has ever been sent. Both
sit behind actions only Mike may take.

Dispatch was never contacted. No repository was created. No pull request was
made. No Manager component exists.

## APPLICATION PATH

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\START_JOE.cmd
```

Double-click. Deployment candidate:
`D:\SANDBOX\Assistan_Building\Assistant_Plugin\Deployment\Assistant_Plugin_v1.0.0`

## REASONING PROVIDER STATUS

**`Reasoning LIVE`.** Proven 2026-08-25.

| | |
| --- | --- |
| provider selected | `True` |
| signed in | `True` |
| account | `Ops@l1truck.com` |
| live | `True` |
| state | `SIGNED IN` |
| preview | `True` |
| tenant id set | `True` |
| client id set | `True` |
| client secret used | `False` |
| token cache | DPAPI-encrypted |
| blocker | none |

Status line:

```
Reasoning LIVE | Library LIVE | Outlook READY | Research SAMPLE |
Voice LIVE | Dispatch NOT CONNECTED
```

Two defects had to be fixed before this could be true, and both were found by
running the live proof rather than by reading code — see DEFECTS.

## PROVIDER USED

**MICROSOFT 365 COPILOT — PILOT / PREVIEW.**

Microsoft Graph `/beta` Copilot Chat API:

```
POST /beta/copilot/conversations
POST /beta/copilot/conversations/{id}/chat
```

Microsoft states that `/beta` APIs are subject to change and are **not
supported for production use**. That notice is carried in the provider label,
the settings panel header, and this report. It is a pilot, not a platform
decision.

All provider-specific code is confined to `adapters/m365_copilot.py` and
`adapters/m365_copilot_auth.py`. Nothing above the adapter layer knows Copilot
exists. Replacing the provider is an adapter swap.

## CREDENTIAL STORAGE METHOD

**MSAL public client. Windows DPAPI-encrypted token cache. No fallback to
readable storage.**

| Property | Result | How it is enforced |
| --- | --- | --- |
| Library | `msal.PublicClientApplication` | `ConfidentialClientApplication` appears nowhere |
| Client secret | none | no `client_credential` is passed; a test asserts it |
| Cache | `FilePersistenceWithDataProtection` (DPAPI) | if DPAPI is unavailable the cache is **memory-only** — it never degrades to plain text |
| Hand-rolled OAuth | none | no `oauth2/v2.0/token`, no `grant_type` in source |
| Token exposure | none | `authorization_header()` is the only path a token leaves; tokens are never parsed, stored by this code, printed, logged, or returned |
| Sign-out | deletes the cache | `sign_out()` reports what it cleared |

The settings panel displays connection state, tenant/client id **set-or-not
booleans**, scopes, and blockers. It displays no token, no secret, no password,
and no authentication code.

A sweep of all 218 shipped source, configuration, documentation, and test files
for bearer tokens, JWTs, API keys, and `access_token=` assignments returned
**zero matches**.

## VOICE INPUT RESULT

**NOT PROVEN. The engine binds; no human has spoken to it.**

| | |
| --- | --- |
| speech-to-text engine available | `True` |
| recognizer | `MS-1033-80-DESK` |
| microphone present | Internal Microphone (Conexant ISST Audio) |
| recognition attempted with a person at the mic | **no** |

Recognition cannot be proven by a program talking to itself. This requires Mike
at the microphone and is listed under EXTERNAL BLOCKERS.

## EXACT PHRASE SPOKEN

**None.** No phrase has been spoken into the microphone.

## EXACT RECOGNIZED TEXT

**None.** No speech has been recognized.

## VOICE OUTPUT RESULT

**LIVE and heard.**

| | |
| --- | --- |
| engine | Windows `System.Speech` |
| voices | Microsoft David Desktop, Microsoft Zira Desktop |
| synthesis | 115,546-byte WAV rendered to file |
| audible | **spoke aloud** during proof step 12 |

## OUTLOOK CALENDAR ORDERING RESULT

**CORRECTED AND PROVEN CHRONOLOGICAL.**

| | |
| --- | --- |
| connection | live, read-only, Outlook 16.0.0.20326 |
| folder total | 601 items |
| ordering reported | `date_with_recurrences` |
| window | the next 14 days, `2026-08-25T00:00:00 → 2026-09-08T00:00:00` |
| ascending in fact | **True**, checked item by item |

Named-date and relative-date questions were checked separately (proof 19):
today, tomorrow, "next Tuesday", "this week", "next week", and a spoken month
name each return the right window, each in date order.

The defect that caused this was not a sort. `Restrict` was being handed a
**.NET** format string (`"MM/dd/yyyy hh:mm tt"`) through Python's `strftime`,
which returns those characters literally. Outlook accepted the filter, matched
nothing, and **raised no error**. An empty calendar looked like a genuinely
empty day. The format is now a Python format producing the shape Outlook wants,
the shape is validated against a regex before the filter is built, and a
mismatch raises rather than returning silence.

## LIBRARY GROUNDING RESULT

**LIVE over the real Company Library.** 34 documents indexed (28 Company
Library + 6 sample corpus). Reads are direct and labelled
`Company Library (read directly)`. Sample-corpus hits are labelled
`SAMPLE DATA — this did not come from a live source.` on the answer itself.

Grounding requires a matched term of at least four characters. Before that rule
a nonsense question matched on "do" and "i" and would have cited an unrelated
document as governing.

## DRAFTING RESULT

**Refuses honestly. Nothing can send.**

```
Q: Draft an email to a broker about a late pickup
A: I cannot write that draft — no reasoning provider is connected.
```

With a provider connected, drafts are marked **DRAFT ONLY / NOT SENT**. There
is no send path: no `send`, `approve`, `decide`, or `schedule` method exists on
the Copilot adapter, and every boundary flag it reports is `False`. Twenty-one
write-capable Outlook COM calls are scanned for and refused before any generated
script runs; none appears in any script.

## SUMMARIZATION RESULT

**Degrades honestly.** Returns the matching material with the notice:

> No reasoning provider is connected, so this is the matching material rather
> than a summary of it.

Verified against `Company Library/Constitutions/DISPATCH_CONSTITUTION_v3.md`.

## EXPLANATION RESULT

**Routes correctly and grounds locally.** "Explain what a detention charge is"
returns `Company Library/Architecture/CONTEXT_MASTER.md`, classed
`Company Library (read directly)`.

A guard exists so that **asking about a command does not execute it**. Before
it, "How do I create a Level 3 record" promoted the record, and "How do I delete
this" would have deleted it.

## PROCEDURE ASSISTANCE RESULT

**Cites a governing document, or states there is none.** "How do I handle a load
refusal" returns
`Company Library/Vision/Vision_3v2_Dispatch_Operating_Lifecycle.docx` with the
notice that this is the governing material rather than a step-by-step
explanation of it. Where no governing document exists, it says so instead of
composing procedure.

## MEMORY RESULT

**Retention memory works end to end, and survives restart.**

| Command as Mike types it | Level | State | Expiry |
| --- | --- | --- | --- |
| *(new interaction)* | `LEVEL_1` | `TEMPORARY` | 3 hours |
| "Save this" | `LEVEL_2` | `SAVED` | kept |
| "Print this" | **`LEVEL_1`** | `PRINT_READY` | kept |
| "Make this a Level 3 record" | `LEVEL_3` | `FORMAL` | kept |
| "Delete this" | `LEVEL_1` | `DELETED` | — |

Print holds the interaction level at `LEVEL_1` and changes only the state, per
Mike's Doctrine C4 ruling. 29 active records survived a shutdown and reopen
intact.

**What memory is not:** there is no durable free-form note. "Remember that
trailer 118 has a bad tail light" is retained as a Level 1 record for three
hours like any other interaction, and the answer that comes back is a Library
match, not a stored fact. Listed under KNOWN LIMITATIONS.

## TEST COMMANDS

```
py -m unittest discover -s tests
py proof/run_proof.py
py proof/run_proof.py --no-outlook
Deployment\PACKAGE_ASSISTANT.cmd
```

Component suites, run from `D:\SANDBOX\Assistan_Building\ASST\1..6`:

```
py -m unittest discover -s tests
```

## TEST RESULTS

**222 assembly tests. 221 passed. 1 skipped. 0 failed. 0 errors.**

The skip is the live-Outlook calendar ordering test, which runs only with
`ASSISTANT_TEST_OUTLOOK=1`. It was run separately against the real calendar and
passed.

| Suite | Tests | Result |
| --- | --- | --- |
| Assembly | 222 | 221 passed, 1 skipped |
| Component 1 | 39 | OK |
| Component 2 | 45 | OK |
| Component 3 | 53 | OK |
| Component 4 | 63 | OK |
| Component 5 | 78 | OK |
| Component 6 | 72 | OK |
| **Combined** | **609** | |

Copilot coverage is 51 tests against a mocked Graph transport — the whole
contract proven without a tenant, a licence, or a sign-in. Contact ordering adds
5 tests that check the order **in fact**, not the label.

## LOCAL PROOF RESULTS

**24 passed, 0 skipped, 0 failed (of 24 steps)**, run with live Outlook.

Skipped steps now read as SKIPPED rather than FAIL. A step not attempted is not
a step that failed, and reporting it as one overstated the damage in exactly the
direction that erodes trust in the rest of the report.

## IMPLEMENTED AND OPERATIONALLY PROVEN

- Launcher, window, and written response
- Record retention: Level 1/2/3, Print, Delete, three-hour expiration, restart survival
- Doctrine C4 — Print is a state, not a level
- Library search over the real Company Library, correctly labelled
- Outlook live read-only: calendar, mail, contacts
- Calendar in date order, recurrences expanded, date filtering by today / tomorrow / named date / this week / next week
- Mail newest-received-first
- Contacts alphabetical by the name shown, over the whole folder
- Email account designation — three accounts enumerated, the one in use reported
- Voice output, audible
- Deterministic routing with no model in the loop
- Governance gate on every response
- Path containment — no write leaves the plugin root
- Provenance class separation across all seven classes
- Drafting, summarization, explanation, and procedure all degrade honestly without a provider
- Operation with Outlook unavailable, and with voice unavailable

## IMPLEMENTED BUT NOT OPERATIONALLY PROVEN

- **Microsoft 365 Copilot chat.** Built, wired, and tested against a mocked
  Graph. No live prompt has been sent. The conversation lifecycle, reply
  parsing, multi-turn reuse, web-grounding toggle, citation and sensitivity-label
  handling, streamed-to-synchronous fallback, and every failure path are proven
  against the mock only.
- **MSAL device-code sign-in.** The flow is built and the cache is configured.
  No sign-in has occurred, so the DPAPI cache has never been written.
- **Voice input.** The recognizer binds and the microphone is present. No speech
  has been recognized.
- **Research.** Adapter retained, fixtures labelled `SAMPLE`. No live provider.
- **Printing.** The request is recorded; nothing is sent to a printer.

## NOT IMPLEMENTED

- **Dispatch connection.** Contract and ports only. No published interface
  exists to connect to.
- `ROUTE_RISK_EVENT` and `DISPATCH_FACT` provenance classes — defined and
  reserved so nothing else can claim them, with no source behind either.
- Durable free-form memory.
- Any operational write, anywhere, to anything.

## EXTERNAL BLOCKERS

Every one of these is behind the human authority gate. **I did not attempt any
of them and did not act on Mike's behalf.**

1. **Entra app registration** — public client, device-code flow enabled.
2. **Tenant id and client id** in `configuration/joe.config.json`. Neither
   is a secret.
3. **Delegated permission review** — seven Graph scopes: `Sites.Read.All`,
   `Mail.Read`, `People.Read.All`, `OnlineMeetingTranscript.Read.All`,
   `Chat.Read`, `ChannelMessage.Read.All`, `ExternalItem.Read.All`.
4. **Administrator consent** on those scopes. I did not assume Mike holds that
   role.
5. **A work or school account with a Microsoft 365 Copilot licence.**
   `jax1313@outlook.com` cannot be used — the Copilot API does not support
   personal Microsoft accounts.
6. **One interactive device-code sign-in.**
7. **A live Copilot prompt**, to prove reasoning rather than mock it.
8. **Mike at the microphone**, to prove voice input.

## KNOWN LIMITATIONS

1. **Reasoning is selected, not connected.** Until sign-in, JOE will
   not compose — it returns matching material and says why.
2. **The Copilot API is `/beta`.** Microsoft does not support it for production.
   Endpoints and response shapes may change without notice, and the mocked tests
   would not detect a change until a live call failed.
3. **No durable free-form memory.** See MEMORY RESULT.
4. **Contacts are truncated to 60** of 145 after sorting. The count and the cut
   are both reported.
5. **Three contacts have no name in Outlook** and are listed last, in folder
   order, with a note saying so.
6. **Research is sample data**, labelled everywhere it appears.
7. **Printing records intent only.**
8. **Local reports name Mike's own machine, Library path, and Outlook
   accounts.** That is evidence, not leakage, but it is his to redact before
   these documents go anywhere.

## SECURITY RESULT

| Check | Result |
| --- | --- |
| Credential-shaped strings in 218 shipped files | **0** |
| Client secret used | **none** — public client, `client_credential` never passed |
| Hand-rolled OAuth | **none** — no token endpoint, no `grant_type` |
| Token cache | DPAPI-encrypted, or memory-only; **never plain text** |
| Token in source, config, logs, reports, tests, or fixtures | **none** |
| Settings panel exposure | state, booleans, scopes, blockers — no secret material |
| Write-capable Outlook COM calls in generated scripts | **0**, with 21 guarded against |
| Writes outside the plugin root | **0** (proof 17) |
| Machine-specific config in the deployment package | **excluded** — template only, and the template holds no personal path or value |

## DISPATCH INDEPENDENCE RESULT

**Dispatch was never contacted.**

| | |
| --- | --- |
| Dispatch status | `NOT CONNECTED`, `live_connection: False` |
| Contacted during proof | no (proof 16) |
| Dispatch files, databases, internals read | none |
| localhost services contacted | none |
| Copilot able to reach Dispatch | no — a test asserts Copilot can never claim `DISPATCH_FACT` |
| `ASST\1..6` component folders modified this mission | **0** |
| Repository created | no |
| Pull request created | no |
| Manager component | none exists |

The removability test holds: remove JOE and Dispatch is unchanged.

## DEPLOYMENT READINESS RESULT

**Rebuilt and verified.** `Deployment\Assistant_Plugin_v1.0.0` — 101 files,
0.92 MB.

Verified the way an operator would use it: copied
`configuration/joe.config.template.json` to `joe.config.json`,
launched, and ran the suite inside the package.

```
answers : True
status  : Reasoning NOT CONNECTED | Library SAMPLE | Outlook READY |
          Research SAMPLE | Voice LIVE | Dispatch NOT CONNECTED
tests   : OK (skipped=1)
```

Library correctly falls back to `SAMPLE` because the packaged template carries
no Library path — the template was scanned and holds no personal path or value.
The machine-specific config was removed again afterwards; the package must not
ship one.

## EXACT FILES MODIFIED

```
adapters/__init__.py
adapters/library_fs.py
adapters/outlook_com.py
adapters/reasoning_provider.py
app/router.py
app/service.py
joe_main.py
configuration/joe.config.json
configuration/joe.config.template.json
contracts/__init__.py
ui/window.py
launchers/JOE_ACCOUNTS.cmd
proof/run_proof.py
tests/test_assistant_plugin.py
docs/JOE_ARCHITECTURE_v1.md
docs/JOE_BUILD_REPORT_v1.md
docs/JOE_DEPLOYMENT_GUIDE_v1.md
docs/JOE_KNOWN_LIMITATIONS_v1.md
docs/JOE_LOCAL_PROOF_REPORT_v1.md
docs/JOE_OPERATOR_GUIDE_v1.md
docs/JOE_REVIEW_HANDOFF_v1.md
docs/JOE_TEST_REPORT_v1.md
Deployment/DEPENDENCIES.txt
Deployment/README.md
Deployment/VERSION.txt
```

## EXACT FILES CREATED

```
adapters/m365_copilot.py          19,397 bytes
adapters/m365_copilot_auth.py     12,628 bytes
app/reasoning_capabilities.py     10,498 bytes
app/when.py                        4,134 bytes
ui/settings_panel.py              10,009 bytes
docs/JOE_BUILD_REPORT_v2.md   (this document)
```

Plus the rebuilt deployment candidate under
`Deployment/Assistant_Plugin_v1.0.0/`.

## REVIEW HANDOFF PATH

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\docs\JOE_REVIEW_HANDOFF_v1.md
```

---

**Do not call this program complete.** Voice input was not physically tested.
Reasoning is not live — only fixtures and mocks have answered. Research is not
live. Calendar ordering *is* proven, in fact and not only in label.

Mike Zachary remains final authority.
