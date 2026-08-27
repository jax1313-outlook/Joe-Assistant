# Voice Live — Research Findings

**Requested:** Mike Zachary, 2026-08-26. **RESEARCH ONLY. No coding. No implementation.**
**Assumed architecture:** `Mike ↕ Voice Live ↕ Joe ↕ Dispatch`
**Retrieved:** 2026-08-26, live web sources. Prices move; these are dated.

---

## 0. The finding that changes the cost answer

**"One operator" is not the unit that gets billed. Audio seconds are.**

Every realtime voice provider bills for the audio you send and receive, not for
seats. So the cost of JOE listening for eight hours depends almost entirely on
one design decision:

| Design | What is billed |
| --- | --- |
| **Continuous open session** — microphone streams to the cloud all day | every second, including silence and road noise |
| **Gated session** — local wake-word or voice-activity detection opens the session only when Mike is actually talking | only the seconds of real conversation |

An owner/operator talking to JOE perhaps 30–60 minutes across an 8-hour day is
paying for 8 hours in the first design and 45 minutes in the second. **That is
roughly a 10× difference and it dwarfs the choice of provider.**

The gating happens on the laptop, costs nothing per minute, and is where the
money is saved.

---

## 1. Cost for one operator

There is no per-operator or per-seat price at any of the providers reviewed.
Billing is usage-based. A single owner/operator therefore costs whatever his
own talk time costs, with **no minimum, no seat fee, and no floor** on the raw
APIs.

Bundled "voice agent platforms" do add monthly platform fees — one source cites
$350–$1,200/month baseline for moderate deployments *plus* per-minute variable
cost. **Those are priced for contact centres, not for one truck.** For a single
operator the raw API route is materially cheaper and is the only one considered
in the tables below.

---

## 2. Cost at 2, 4, and 8 hours per day

**Basis for the numbers.** Audio tokenises at roughly 600 tokens per minute of
speech in, 1,200 per minute out for the OpenAI-family models — Microsoft
documents the same shape as ~10 tokens/second input and ~20 output. Rates used:

| Model | Audio in | Audio out | Cached in |
| --- | --- | --- | --- |
| `gpt-realtime-2.1` (flagship) | $32/M | $64/M | $0.40/M |
| `gpt-realtime-2.1-mini` | $10/M | $20/M | $0.30/M |
| Gemini 3.1 Flash Live | $3/M | $12/M | — |

Published effective rates on mixed conversation: **~$0.05/min flagship**,
**~$0.016/min mini**, **~$0.005 in / $0.018 out per minute** for Gemini Live.

### Scenario A — continuous open session (worst case)

Hours below are hours of **open microphone**, not hours of talking. Month = 22
working days.

| Hours/day | Flagship @ $3.00/hr | Mini @ $0.96/hr | Gemini Live ~$0.69/hr | Deepgram STT + TTS ~$0.46/hr + speech |
| --- | --- | --- | --- | --- |
| **2** | $6.00/day → **$132/mo** | $1.92/day → **$42/mo** | $1.38/day → **$30/mo** | ~$0.92/day → **~$20/mo** |
| **4** | $12.00/day → **$264/mo** | $3.84/day → **$84/mo** | $2.76/day → **$61/mo** | ~$1.84/day → **~$40/mo** |
| **8** | $24.00/day → **$528/mo** | $7.68/day → **$169/mo** | $5.52/day → **$121/mo** | ~$3.68/day → **~$81/mo** |

**These are floors, not ceilings.** Every turn re-processes the growing
conversation context, so input tokens compound. One source measuring real
sessions reports long calls commonly costing **2–5× the base estimate** without
aggressive caching. An 8-hour continuous flagship session could realistically
land between **$528 and $2,600/month**.

### Scenario B — gated session (realistic)

Assume the microphone opens only for actual exchanges. An owner/operator asking
JOE things through a working day might accumulate 30–60 minutes of real talk.

| Talk time/day | Flagship | Mini | Gemini Live |
| --- | --- | --- | --- |
| **30 min** | $1.50/day → **$33/mo** | $0.48/day → **$11/mo** | $0.35/day → **$8/mo** |
| **60 min** | $3.00/day → **$66/mo** | $0.96/day → **$21/mo** | $0.69/day → **$15/mo** |

**This is the honest answer to "what does it cost for one operator": somewhere
between $8 and $66 a month**, if the session is gated. The 2/4/8-hour framing
only produces the large numbers when the microphone is streaming to the cloud
the whole time.

### One cost I could not retrieve

**Azure Voice Live's exact dollar rates.** Microsoft's pricing page renders its
figures dynamically and returned placeholder dashes; the announcement blog was
not retrievable. Confirmed from Microsoft's own documentation: the tiers are
**Pro / Basic / Lite**, the tier follows the model chosen rather than being
selected, and Voice Live Pro uses `gpt-realtime`, `gpt-4o`, `gpt-4.1`, `gpt-5`.
Voice Live BYO audio processing was cited elsewhere at **$12.50/M input and
$30/M output**.

Because Voice Live Pro runs the same `gpt-realtime` family on the same token
math, the flagship column above is the right order of magnitude for it — but
**it is an inference, not a retrieved Azure price.** Anyone budgeting on it
should read the figure off the Azure calculator with the region selected.

---

## 3. Continuous conversation support

**All four options support it. The differences are in what they handle for you.**

| Capability | Azure Voice Live | OpenAI Realtime | Gemini Live | Composable stack |
| --- | --- | --- | --- | --- |
| Full-duplex streaming | yes | yes | yes | you build it |
| Interruption / barge-in | **yes, built in** | yes | yes | you build it |
| End-of-turn detection | **yes, "allows natural pauses without prematurely concluding"** | yes | yes | you build it |
| Noise suppression | **yes, built in** | no | no | you add it |
| **Echo cancellation** | **yes — explicitly "prevents the agent from picking up its own responses"** | not built in | not built in | you build it |

**Azure Voice Live is the only one that ships echo cancellation as a stated
feature.** That matters directly: JOE already has a hand-built microphone
suppression that mutes input while speaking, tested but never proven against a
real speaker in a real cab. Echo cancellation at the provider replaces that
guard with something engineered for the job.

Noise suppression is not a minor line item for a truck cab either.

---

## 4. Bluetooth headset support

**This is the most important finding, and it is not what the question implies.**

**No provider "supports Bluetooth."** All four accept a raw audio stream over a
WebSocket. Audio capture happens on the laptop. Bluetooth is therefore entirely
a **local Windows audio problem**, and switching providers does not by itself
fix a headset that Windows is not routing.

**But it changes what JOE is able to do about it**, and this is decisive:

| | Today (System.Speech) | With a stream-based provider |
| --- | --- | --- |
| How audio is captured | `SetInputToDefaultAudioDevice()` — the only option | JOE captures the stream itself |
| Can JOE choose the device? | **No.** There is no "record from this device" method | **Yes.** JOE can open any capture endpoint and send it |
| If the Windows default is wrong | JOE hears the wrong microphone and can only report it | JOE selects the headset regardless of the Windows default |

The device-selection limitation already documented in JOE — a preference that
can only be *remembered and reported*, never enforced — **exists because of
System.Speech, not because of Windows.** A stream-based provider removes it.

Two further Bluetooth realities, independent of provider:

- A Bluetooth headset microphone runs over **Hands-Free Profile**, which is
  narrowband mono. Recognition accuracy is materially worse than a wired or
  built-in microphone, and Windows drops audio playback quality to match while
  the microphone is open.
- Windows routes HFP as a **separate endpoint** from the A2DP playback device.
  A headset can be connected for listening while its microphone is not the
  default recording device — which is exactly the state JOE observed on this
  machine.

---

## 5. Ability to call Dispatch functions

**Supported by all four. This is the mechanism the `Mike ↕ Voice Live ↕ Joe ↕
Dispatch` architecture depends on, and it exists.**

| Provider | Function / tool calling |
| --- | --- |
| Azure Voice Live | **yes** — "enables external actions, use of tools, and grounded responses" |
| OpenAI Realtime | yes |
| Gemini Live | yes, with native-audio tool calling |
| Composable stack | whatever the chosen LLM supports |

**What this does and does not mean for JOE.** Function calling lets the voice
layer *emit a request to call something*. It does not decide whether the call is
allowed. The authority gate — Inform / Review / Draft / Execute, and the rule
that a draft command never carries send authority — stays in JOE, exactly where
the governing mission puts it.

The correct shape is: the voice provider recognises intent and proposes a tool
call; **JOE validates authority and calls the deterministic Dispatch service**;
Dispatch performs the business action. The voice provider must never hold a
credential for Dispatch or call it directly.

---

## 6. Ability to maintain mission context

**All four maintain conversation context within a session. None of them should
hold mission context, and this is a design conclusion rather than a limitation.**

Session context is what makes "which one creates more uncertainty?" resolvable
without repeating the subject. Every option does this.

**Mission context is different, and belongs to Dispatch.** Under the locked
architecture, cards represent operational truth. If the voice provider held its
own copy of mission state, that copy would be a second source of operational
truth — the specific thing the governing mission prohibits, and the thing that
drifts silently once a card changes underneath it.

The sound shape: the provider holds **conversation** context; JOE holds the
**current card reference**; Dispatch holds the **card**. JOE re-reads card state
per turn rather than remembering it.

One practical consequence for cost: context accumulation is what makes long
sessions expensive. Keeping mission state *out* of the conversation and passing
only the current card facts per turn is both architecturally correct and the
main lever on the 2–5× context-growth multiplier in §2.

---

## 7. Ability to remain provider-replaceable

**Good news, and better than expected.**

**Azure Voice Live is deliberately wire-compatible with the Azure OpenAI
Realtime API** — Microsoft states its "supported real-time events mostly match"
and that Voice Live's unique features are "optional and additive." A client
written against one can move to the other with limited change, and Voice Live's
extras (echo cancellation, noise suppression, end-of-turn detection) can be
added "without changing your existing architecture."

Practical implications:

- **Azure Voice Live and OpenAI Realtime are near-drop-in for each other.**
- **Gemini Live is a different protocol** — replaceable, but a genuine port.
- **A composable stack is the most replaceable of all** (swap STT or TTS
  independently) and the least managed — you build interruption, echo
  cancellation, and end-of-turn yourself.
- **Bring Your Own Model** is supported on Voice Live, so the reasoning model
  can change without changing the voice layer.

All four are WebSocket streaming interfaces taking audio in and audio out. That
is a narrow enough contract to sit behind a replaceable interface, which is what
the governing mission's Section 11 requires: *voice is a replaceable service
dock; do not hardwire Dispatch business logic into the voice provider.*

---

## 8. What I would look at first, if asked

Not a recommendation to implement — the mission stopped at Step 1 and nothing
here changes that.

**Azure Voice Live is the strongest fit on the evidence**, for reasons that have
little to do with price:

1. **Echo cancellation and noise suppression are built in.** JOE's hand-built
   suppression is unproven against a real cab, and a truck is a noisy room.
2. **Same tenant, same identity.** Mike is already signed in on
   `Ops@l1truck.com` with MSAL and a DPAPI-protected token cache. No second
   vendor, no second credential, no second bill.
3. **Wire-compatible with OpenAI Realtime**, so choosing it does not close the
   door.
4. **It would remove the device-selection limitation**, which is currently the
   thing standing between Mike and his headset.

**The cost question is answered by the gating decision, not the provider
choice.** Gate the session and any of these costs tens of dollars a month.
Stream continuously and the flagship models cost hundreds.

**The number I could not retrieve is Azure's actual rate**, and I would want it
read off the calculator before anyone commits.

---

## Sources

- [Azure AI Voice Live API overview — Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live)
- [Azure AI Voice Live API: what's new and the pricing announcement — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/azure-ai-voice-live-api-what%E2%80%99s-new-and-the-pricing-announcement/4428687)
- [Pricing — Azure Speech in Foundry Tools](https://azure.microsoft.com/en-us/pricing/details/speech/)
- [OpenAI Realtime API Pricing 2026: Cost Per Minute Math — Layer3Labs](https://www.layer3labs.io/guides/openai-realtime-api-pricing)
- [OpenAI Realtime API Pricing in 2026: Real-World Data From 4,000 Measured Sessions — HackerNoon](https://hackernoon.com/openai-realtime-api-pricing-in-2026-real-world-data-from-4000-measured-sessions)
- [Gemini API Pricing: Full Breakdown of Costs (Aug 2026)](https://developer.puter.com/tutorials/gemini-api-pricing/)
- [Gemini Live API — Ry Walker Research](https://rywalker.com/research/gemini-live-api)
- [Deepgram Pricing 2026: Nova-3 at $0.46/hr Breakdown](https://brasstranscripts.com/blog/deepgram-pricing-per-minute-2025-real-time-vs-batch)
- [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- [AI Voice Agent Pricing 2026 — Famulor](https://www.famulor.io/blog/ai-voice-agent-pricing-2026-what-10-platforms-actually-cost-per-minute)

---

Mike Zachary remains final authority.
