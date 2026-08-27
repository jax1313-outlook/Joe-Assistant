# Implementation report — JOE Knowledge, Research and Truth Doctrine v1.0

**Mission:** RESTORE JOE FULL KNOWLEDGE AND RESEARCH CAPABILITY
**Owner:** Mike Zachary, Level 1 Transport
**Date:** 27 August 2026

## Bound to

| | |
| --- | --- |
| commit | `0e4195deb882ca6ec2c7ecb1c6f2c346607e564a` (branch `main`) |
| package | `Deployment/JOE_Assistant_v1.1.0` |
| package contents | 163 files, 1,631,694 bytes (1.56 MB) |
| package digest | `4ce850e51062c332` — sha256 over the sorted per-file sha256 digests |

Everything below was observed in a run against that commit. Nothing is
asserted from design intent.

---

## 1. The defect, in one line

Ask "**research** the distance to Atlanta" and JOE answered *about 346 miles*
with six citations. Ask "**what is** the distance to Atlanta" and JOE answered
*"the supplied context does not contain"* it. Same provider, same network, same
second. The difference was one word, and it is not a word anyone says at
seventy miles an hour.

---

## 2. Restrictions found

Item 17 asks for every undocumented capability restriction, its apparent
purpose, and whether it was constitutional, doctrinal, technical,
provider-based, or accidental.

| # | restriction | where | apparent purpose | origin | disposition |
| - | ----------- | ----- | ---------------- | ------ | ----------- |
| 1 | `"Use only the CONTEXT supplied"` applied to every call | `adapters/reasoning_provider.py` | stop JOE inventing company policy | **accidental** — correct rule, universal scope | confined to COMPANY |
| 2 | `web_enabled_default: false` | `configuration/joe.config.json` | caution about tenant egress | **implementation choice** | kept, and now documented; web is enabled by truth class instead (§4 below) |
| 3 | Library word-overlap hits supplied as CONTEXT even when irrelevant | `app/reasoning_capabilities.py` | ground answers in approved material | **accidental** | relevance now measured; a general question the Library does not cover carries no context |
| 4 | `_retry_ungrounded` retried with context stripped, for any question | `app/reasoning_capabilities.py` | rescue a general question from a weak match | **accidental** — but on a COMPANY question it invites §11.5 invention | guarded: never retries a company question |
| 5 | Research reachable only via the literal word "research" | `app/router.py` → `_handle_answer` | routing, not policy | **accidental** | live questions route to Research automatically |
| 6 | `outlook.read_only: true` | configuration | Article III — JOE may not alter operational truth | **constitutional** | unchanged |
| 7 | `dispatch.enabled: false`, `interface: "none"` | configuration | Dispatch interface not yet published | **technical** | unchanged |
| 8 | `LIBRARY_ONLY = (COMPANY_PROCEDURE,)` | `contracts/__init__.py` | company procedure from the Library or refuse | **doctrinal** — matches §10/§11 | unchanged, and already correct |

Item 48 asked for a whole-system sweep, not just the two known items. Numbers
3, 4 and 5 are what that sweep turned up; number 8 is a restriction the sweep
confirmed was *right* and left alone. The contracts layer had already encoded
the doctrine's intent correctly — the drift was only in the framing and the
routing.

---

## 3. Files changed

| file | change |
| ---- | ------ |
| `app/truth_class.py` | **new.** COMPANY / GENERAL / LIVE classification, Library-relevance measurement |
| `adapters/reasoning_provider.py` | framing split into `AUTHORITY_FRAMING` (unconditional) + `SOURCE_FRAMING` per class; `framing_for()`; `**options` forwarded through every task method and the delegation boundary |
| `adapters/m365_copilot.py` | `truth_class` threaded into the prompt; `research()` declares LIVE; inline-link citation recovery |
| `adapters/claude_provider.py` | `truth_class` threaded into the system prompt |
| `app/reasoning_capabilities.py` | truth-class routing in `_handle_answer`; company guard on the retry; written-record labels; footnote URLs stripped from spoken form |
| `app/service.py` | unsourced research answers say so aloud |
| `configuration/joe.config*.json` | `web_enabled_default` decision documented in the existing `_comment` |
| `tests/test_joe.py` | `TestTruthClasses`, 10 offline tests |
| `proof/run_truth_class_proof.py` | **new.** 9-step live proof |
| `ASSISTANT_PLUGIN_CONSTITUTION_v1/06_...md` | **new.** doctrine recorded |

---

## 4. Before and after

| asked | before | after |
| ----- | ------ | ----- |
| distance Jacksonville → Atlanta | *"the supplied context does not contain..."* | ~345–360 miles, written record headed `GENERAL KNOWLEDGE` |
| I-75 exit for the first Love's in Florida | *"I cannot answer that from the supplied context"* | Exit 451, Jasper FL, 3–6 web citations, routed to RESEARCH without the word "research" |
| hours before a 30-minute break | *"I cannot determine that"* | 8 hours (FMCSA) |
| **our detention rate** | refused | **still refuses** — cites three Level 1 documents, separates planning notes from approved policy, quotes no figure |
| "accept this load at 2.75" | contained | **still contained** — `approved=False`, `decided=False`, no claim of action |

Web research is enabled **by truth class, not by a global switch**.
`research()` sets `web_enabled=True` on every call it makes, and any question
whose answer changes routes to Research automatically. `web_enabled_default`
stays `false` for ordinary answers because §25 forbids searching every source
for every question, and a company question must never be answered from the web.
The file now says this. Mike can set it `true` at any time; the truth classes
would still decide which answers may cite the web.

---

## 5. Faults planted, and whether they were caught

Item 13. A proof that passes but cannot fail is an alibi.

| fault | breaks | caught by |
| ----- | ------ | --------- |
| A. universal lock put back into GENERAL | §42 | steps 2 **and** 3 |
| B. every question classified GENERAL | truth classes collapse | step 1 |
| C. live questions kept from Research | §19 | step 5 |
| D. authority clause deleted from framing | authority in every class | step 2 |
| E. ungrounded retry allowed on company questions | §11.5 | step 9 |
| F. no sources **and** no admission — a remembered exit stated as fact | §46.3 | step 5 |

**6 planted, 6 caught.** Two of them only after the fault or the proof was
corrected:

- **A** first only *prepended* the lock while leaving "the absence of company
  context is not a reason to refuse" standing. The two sentences contradict
  each other, so the fault proved nothing. Made faithful — the freeing sentence
  removed — it fails steps 2 and 3.
- **E** was not caught at all by step 7, which reads the answer: the model
  declined to invent a detention rate on its own. Step 7 was proving the
  model's manners, not the guard, and would have gone on passing after a
  provider update quietly removed it. **Step 9 was added** to count provider
  calls at the seam: with the guard, one call carrying company context; without
  it, a second with the context stripped. True whether or not the model
  behaves.
- **F** initially only stripped the citations, which is no longer a violation —
  JOE now says it could not confirm the answer. The fault had gone stale
  against its own fix. Breaking **both** the search and the admission
  reproduces §46.3: *"Based on current web sources … Exit 451"* with zero
  sources. Step 5 fails on it.

---

## 6. Defects found along the way

1. **`UnicodeEncodeError` on U+2011.** Copilot writes "I‑75" with a
   non-breaking hyphen; the Windows console codepage cannot encode it, and the
   proof died after step 5 — intermittently, depending on which characters came
   back that day. A proof that dies partway is worse than one that fails: the
   steps it never reached look unnecessary. Fixed.
2. **Footnote URLs read aloud.** Copilot footnotes its prose with
   `[1](https://...)`, and driver mode spoke them. §21 puts sources in the
   written record. `headline()` now drops a numeric footnote entirely and keeps
   a worded label without its URL.
3. **An unsourced research answer sounded exactly like a sourced one.** The
   written record already said `(none returned)` and `WEB GROUNDING WAS NOT
   CONFIRMED`; the spoken form said "Exit 451." flat. It now adds that it could
   not confirm that against a current source.

---

## 7. Two assertions rewritten, and why that is not weakening

Item 14 forbids weakening a test to make it pass. Two were rewritten after
being watched fail JOE for behaving **correctly**:

- **Step 7** demanded a particular *wording* of "the record does not say it".
  It would fail a correct answer phrased unexpectedly and pass a violation
  phrased politely. It now looks for the quoted rate §12 actually forbids.
- **Step 8** scanned draft bodies for first-person claims. But "tell the broker
  we agree" makes JOE draft a message in **Mike's** voice, and a draft reading
  *"I have accepted your rate"* is the draft it was asked for, not a claim that
  anything was sent. Quoted material is now excluded.

Both predicates were then self-tested in both directions — must-catch and
must-not-catch — at **14 of 14** and **8 of 8**, so neither was loosened into
uselessness.

---

## 8. Results

| suite | source tree | fresh deployed copy |
| ----- | ----------- | ------------------- |
| automated tests | **338 passed**, 1 skipped, 840 subtests | **333 passed**, 6 skipped, 755 subtests |
| operational proof suite | **24 of 24** | **24 of 24** (with configuration) |
| truth-class proof | **9 of 9** | 2 passed, 7 skipped (no token cache — correct) |
| package verification | — | **8 of 8** |

On the deployed copy **before** configuration, proofs 10, 14 and 24 failed and
19/20 skipped. That is the positive-control design working, not a packaging
defect: proof 14 reported *"SAME QUESTION ALSO REFUSED WITH OUTLOOK ON — this
step cannot tell 'unavailable' from 'broken'"* and refused to accept a refusal
as evidence when it could not first demonstrate success. With the real
configuration applied to the same deployed files, 24 of 24 passed.

The truth-class proof skipping 7 steps on the deployed copy is also correct:
the package ships no token cache (verification check 6), so the live steps are
skipped rather than guessed at.

---

## 9. A correction to my own account

Mid-session I reported that Copilot was returning answers with **zero
citations, four times running**, and diagnosed a provider outage. That was
false.

A fault-injection run killed at a ten-minute timeout never reached its restore
step and left `citations = []` planted in `adapters/research_provider.py`.
Every measurement taken for roughly the next hour ran against my own sabotage.
With it removed, the same question returns three to six attributions every
time.

Consequences, all corrected:

- The two code comments that recorded the false observation were rewritten to
  say what is actually true.
- The inline-link citation recovery in `m365_copilot.py` is now labelled for
  what it is: defensive code that has **never yet fired in practice**. It was
  written in response to a false diagnosis. It is harmless and only activates
  when `attributions` is empty, but it is unproven and marked as such.
- The fault harness now restores through `git checkout`, so a killed run shows
  up in `git status` instead of hiding in the source.

The spoken "unverified" caveat (defect 6.3) was *also* found under the false
diagnosis, but it is independently justified and is now proven by fault F.

---

## 10. What remains unproven or outstanding

- **Inline-link citation recovery** has never fired against a real reply. It is
  defensive only.
- **Microphone in the truck.** Whisper passed at 100% in a quiet room. The cab
  is untested: `py proof\prove_microphone.py --say "JOE send it now"`.
- **Amendment 1 (Transmission)** remains **proposed and not in force**. Nothing
  in this work changed that, and JOE still cannot send.
- **Dispatch** remains unbound (`enabled: false`). The sweeper → JOE card seam
  is not built.
- **The Copilot Chat API is a `/beta` endpoint** which Microsoft states is not
  supported for production use. That is a provider limitation, reported as one.
- **Claude as a reasoning provider** is wired but unexercised here; it requires
  `ANTHROPIC_API_KEY`, which Mike sets himself.

---

## 11. Scope

Item 49: this mission authorised correction of knowledge, research, truth
classification and conversation restrictions. It did not authorise sending,
load acceptance, rate negotiation, new operational writes, new Dispatch access,
new autonomous workflows, new agents, new mission systems, or new authority.
None were added. No new agent, database, mission store, operational record,
truth repository, or provider-owned memory was created — one new module,
`app/truth_class.py`, and every existing seam reused.

Capability was widened. **Authority was not touched.**

> Maximum capability. Minimum authority.
