# Dispatch Copilot Agent — Build Plan

**Mission:** BOOTSTRAP THE DISPATCH COPILOT AGENT, §10.D
**Type:** Plan only. **No coding under this mission.** No automatic progression.
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

The smallest ordered sequence. Reuse before creation, interfaces before
coupling, preserve before modifying.

**Work packages are grouped by what blocks them.** WP-1 and WP-2 can start
without the Dispatch repository. Everything from WP-3 onward cannot.

---

## Ordering principle

The prior mission's dependency order started with card discovery. **That order
cannot begin**, because the Dispatch repository is unavailable. So the sequence
below front-loads the two packages that are genuinely independent — the Voice
Dock and the agent lifecycle split — and both happen to be the two things Mike
has already flagged as broken or unproven.

That is not a coincidence. **Voice input is the capability Mike cannot yet use,
and the lifecycle split is the highest-risk refactor in the repository.** Doing
them while Dispatch is unavailable costs nothing in waiting time.

---

## WP-1 — Voice Dock, provider-neutral, with device selection

**Mission:** make Joe able to hear Mike through the headset he already wears,
behind a replaceable provider interface.

**Why first:** it is the only capability Mike has never been able to use, it is
completely independent of Dispatch, and the root cause is already known.

| | |
| --- | --- |
| **Inputs** | `app/driver_voice.py` (212 loc, 18 tests), `adapters/microphones.py` (212 loc, 43 tests), `adapters/voice_sapi.py` (243 loc), `VOICE_LIVE_RESEARCH_FINDINGS.md` |
| **Files affected** | new `voice_dock/` package; `adapters/voice_sapi.py` becomes one provider plugin |
| **Reused code** | the loop, the command grammar, microphone suppression, device enumeration, present/absent/unknown — **all of it, unchanged in behaviour** |
| **New code** | provider interface; stream-based capture that can bind a **chosen** device; audio-activity detection; idle-session closure; stage-level diagnostics |
| **Tests** | existing 18 + 43 must still pass. New: device selection honoured; session gating opens and closes; activity detection distinguishes silence from a dead microphone; provider swap changes nothing above the dock |
| **Operational proof** | **Mike speaks through the LEVN headset and Joe answers.** The existing `MIC_TEST` harness already runs this and currently blocks on him |
| **Rollback** | keep `voice_sapi` as the default provider; the dock falls back to it |
| **Drift test** | Does this recreate Manager? No. Does it turn Joe into a voice provider? **No — the opposite.** Does it hold Dispatch logic? No |
| **Definition of done** | Mike converses hands-free through his headset; the failing stage is named when any stage fails; swapping the provider requires no change above the dock |
| **Dependencies** | none. **Can start now** |

**The specific defect it fixes:** `System.Speech` exposes only
`SetInputToDefaultAudioDevice()`. Joe cannot bind a chosen capture device, which
is why a headset preference can only be *remembered and reported*, never
enforced. A stream-based provider removes that.

---

## WP-2 — Agent lifecycle split

**Mission:** turn `AssistantService` from an application into a component that
starts and stops with a host.

**Why second:** it is the highest-risk refactor in the repository and the one
most likely to break the 329-test safety net. Doing it against a *known* host
(the current window) before adding an *unknown* host (Dispatch) halves the
number of things that can go wrong at once.

| | |
| --- | --- |
| **Inputs** | `app/service.py` — 1,128 loc, 154 test references, 140 proof references |
| **Files affected** | `app/service.py` split; `joe_main.py`; `ui/window.py` |
| **Reused code** | every capability handler, the governance gate, retention, contracts, all adapters — **the internals do not change** |
| **New code** | an agent façade with explicit `start()` / `stop()`; adapter construction moved out of the constructor |
| **Tests** | all 329 must still pass. New: start/stop is idempotent; stop releases the voice loop and all adapters; the agent survives a host restart |
| **Operational proof** | Joe still launches, answers, and passes 24/24 proof steps with the split in place |
| **Rollback** | the split is additive — the old entry point keeps working until the new one is proven |
| **Drift test** | No Manager. No new source of truth. No screen work |
| **Definition of done** | Joe runs identically, and its lifecycle is externally controlled |
| **Dependencies** | none technically. **But see the warning** |

> **Warning worth acting on.** How this split should land depends on Dispatch's
> plugin lifecycle, which is unknown. Doing it now risks splitting it the wrong
> way and splitting it twice. **My recommendation is to do WP-1 first and hold
> WP-2 until the Dispatch lifecycle is visible**, unless Mike wants the
> refactoring risk retired early.

---

## WP-3 — Card read, through a Dispatch interface

**BLOCKED — requires the Dispatch repository.**

| | |
| --- | --- |
| **Mission** | Joe reads card state and answers card-grounded questions |
| **Inputs** | Dispatch card interface; `contracts::SourceClass.DISPATCH_FACT` (already reserved, produced by nothing) |
| **Reused code** | `Provenance`, the governance gate, the status vocabulary, `dispatch_port.py` |
| **New code** | a card read adapter; card-grounded reasoning mode |
| **Tests** | a card read is labelled `DISPATCH_FACT`; Copilot may never wear that class (**the guard already exists**); an unreachable Dispatch reports UNKNOWN, never "no cards" |
| **Operational proof** | Mike asks about a real card; Joe answers from Dispatch and names the card and retrieval time |
| **Drift test** | Does Joe store the card? **It must not** |
| **Definition of done** | Joe answers a card question with no durable copy of card state anywhere in Joe |
| **Dependencies** | Dispatch repository; card interface |

---

## WP-4 — Card resolution

**BLOCKED.** Resolve "XPO Load 123" to exactly one card. Zero matches → say so.
Many → ask which. **Never guess.** Depends on WP-3.

---

## WP-5 — Command classification: Inform / Review / Draft / Execute

**BLOCKED on a decision, not on code.**

**This work package cannot be specified until conflict C-1 is ruled on.** Joe's
entire authority model is proposal-only and is enforced in five places. §7 of the
mission requires EXECUTE. Those are not reconcilable by adjusting a flag.

**Do not start this package before Mike rules.** Building it either way first
means building it twice.

---

## WP-6 — Monitoring surface

**PARTIALLY BLOCKED.** Joe's `CapabilityStatus` vocabulary — LIVE / READY /
UNKNOWN, a timeout never cached as absence — is directly reusable for Job 2 and
is already tested. The *subjects* being monitored are Dispatch-side and unknown.

---

## WP-7 onward — deferred

Publisher requests, Outlook transport, Alert Card announcement, Transaction
Log, Config Review triggering. **All blocked, all Dispatch-owned.** None should
be built inside Joe.

---

## The first work package, if one starts

**WP-1, the Voice Dock.**

It is the only package that is genuinely unblocked, it fixes the capability Mike
has never been able to use, it reuses 400+ lines of already-tested code
unchanged, and its proof is a thing Mike can do in five minutes with a headset.

It also has the cleanest rollback in the plan: the existing SAPI provider stays
as the default until the new one is proven.

---

## What must NOT be built, in any package

- Any card structure inside Joe
- Config Review, scoring, or capacity calculation
- A Transaction Log inside Joe — Dispatch owns event history, and §10 of the
  prior mission warns against asserting a log exists before confirming it
- A second operational database or durable card copy
- A Manager, or anything that routes between Dispatch modules
- Dispatch business logic inside the voice adapter
- Unrestricted Dispatch credentials held by any voice provider

---

Mike Zachary remains final authority.
