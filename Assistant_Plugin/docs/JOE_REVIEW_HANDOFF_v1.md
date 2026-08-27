# JOE - Review Handoff

**For:** Mike Zachary
**Program:** JOE, the Level 1 Assistant v1.0.0
**Location:** `D:\SANDBOX\Assistan_Building\Assistant_Plugin`

---

## Read this first — what changed since v1

JOE now has a **reasoning backend**: Microsoft 365 Copilot, behind the
existing provider contract. It is **selected and not signed in**, and the whole
program is built so those two words can never blur together. If you check one
thing in this handoff, check that: the status line, the settings panel, and
every report must say `NOT CONNECTED` until someone signs in.

Full detail: [JOE_BUILD_REPORT_v2.md](JOE_BUILD_REPORT_v2.md).

**Two ordering defects were found by running it against Mike's real Outlook,
not by reading code.**

1. The calendar filter was being handed a **.NET** format string through
   Python's `strftime`. Outlook accepted it, matched nothing, and raised no
   error — an empty calendar that looked like an empty day.
2. Contacts were reported "alphabetical by name" because they were sorted on
   Outlook's `[FileAs]` field, which is **empty on every synced contact in this
   profile**. The list was labelled sorted and read as unsorted. The label was
   the defect: it told Mike the thing he complained about had been fixed.

Both are fixed, and both are now checked **in fact** — the order is verified
item by item — rather than by trusting what Outlook reports.

## Try it first, read second

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\START_JOE.cmd
```

Double-click. Then type these, in order:

```
help
Find the rate floor policy
Save this
Print this
What is on my calendar?
Research the northbound lane
```

Then press **Speak answer** to hear it out loud, and **Listen** to talk to it.

That is the whole program. If it does not earn its place in ten minutes of
that, the documents will not change your mind.

## Then run the two checks

```
launchers\RUN_TESTS.cmd      106 automated tests
launchers\RUN_PROOF.cmd      18 operational proof steps, regenerates its report
```

`RUN_PROOF.cmd` briefly opens the window and briefly starts Outlook. Add
`--no-outlook` to skip that, `--speak` to also make it talk.

## What is genuinely live

| | |
| --- | --- |
| **Library** | Your real Company Library. 28 documents indexed, plus 6 labelled samples. |
| **Outlook** | Your real calendar, mail, and contacts. **Read-only.** 601 calendar items, 273 inbox, 145 contacts. |
| **Voice out** | Windows speech. It spoke aloud during the proof. |

## What is not

| | |
| --- | --- |
| **Reasoning** | **Nothing is connected.** It cannot compose an answer. This is the big one. |
| **Research** | Sample briefs only, labelled SAMPLE DATA everywhere. |
| **Voice in** | The engine binds and the button works, but no automated run can prove recognition. You have to try it. |
| **Dispatch** | Contract only. Never contacted. |
| **Printing** | Records a request. Nothing prints. |

## The honest summary

This program is **good at finding, reading, watching, and keeping**. It is
**not able to think**. Ask it something it has no source for and it tells you
there is no source, rather than producing something that sounds like an answer.

Whether that is worth having is your call. My view: the Library search over
your own Company Library and the read-only Outlook awareness are the two parts
that remove real work today. The rest is scaffolding waiting on decisions only
you can make.

## Three things I would want you to check

**1. Does it actually reduce your load, or move it?**
Mission section 17. My belief is that Library search and calendar awareness
remove work. But you are the only person who can tell whether opening another
window to ask a question is cheaper than the thing you do now.

**2. Is the calendar window the right length?**
The folder-order defect is **fixed** - the calendar now comes back in date
order, recurring events expanded, covering the next 14 days from midnight
today. Raise `outlook.calendar_window_days` if you want to see further ahead.
Worth checking that 14 days is the right default for how you actually work.

**3. Should the Company Library path ship enabled?**
Right now the working copy has it enabled and pointed at your OneDrive folder.
The deployment candidate ships it **disabled** with a placeholder. I made that
call so a copied folder never reaches into someone's files by default. Tell me
if you want it the other way.

## Decisions waiting on you

**Email Connection Layer v1 is approved, recorded, and deliberately not
started.** Mike sequenced it behind Copilot proof and Voice proof, both of which
are behind the human authority gate. The requirement and an honest gap
assessment are in
[EMAIL_CONNECTION_LAYER_v1_REQUIREMENT.md](EMAIL_CONNECTION_LAYER_v1_REQUIREMENT.md).
Four of its fourteen requirements are already met — and all four are
constraints, not capabilities. One requirement names an account
(`Admin@l1truck.com`) that does not exist in the Outlook profile.


| # | Decision | Consequence |
| --- | --- | --- |
| 1 | **Bind a reasoning provider?** | The single change that would make this able to answer. Needs a provider and a credential you approve. |
| 2 | **Bind a research provider?** | Turns SAMPLE DATA into live research. |
| 3 | **Publish a Dispatch read interface?** | Dispatch's decision, on Dispatch's terms. JOE waits and does not specify it. |
| 4 | **Change the calendar window from 14 days?** | One value in `configurationssistant.config.json`. |
| 4b | **Sort mail by received time too?** | Same one-line mechanism as the calendar fix. Not done - you asked for the calendar. |
| 5 | **Create a repository?** | Not done. Mission forbade it without your explicit direction after local proof. Local proof now exists, so this is live for you to decide. |
| 6 | **Deploy the candidate somewhere permanent?** | It currently lives in `Deployment\Assistant_Plugin_v1.0.0\`. |

## What was not done, deliberately

- **Nothing merged into Dispatch.** No file copied, no reference added.
- **No GitHub repository, no pull request.**
- **Nothing installed into Windows.** No registry entry, service, or task.
- **The six workstream folders were not modified.** Zero files changed. No
  workstream defect required correction.
- **No Manager component** created, referenced, or implied.

## Three defects I found by running it

Recorded because they say something about how this was built:

1. **Retention commands hit the wrong record.** "Save this" then "Print this"
   landed on two different interactions. Reading the code would not have caught
   it.
2. **"Look up the appointment policy" went to your calendar** instead of the
   Library, because the router matched the word "appointment".
3. **The deployment template shipped your OneDrive path**, and my own check
   passed because the placeholder appeared in a comment it had just written.

All three are fixed, tested, and documented in the build and test reports.

## Where everything is

```
Assistant_Plugin\
  START_JOE.cmd            open it
  launchers\                     stop, restart, status, tests, proof, logs, data
  docs\                          the 11 required documents
  Deployment\                    the deployment candidate
  runtime_data\memory\           your records, plain JSON
  logs\                          event log
  app\ adapters\ contracts\ governance\   the assembly
  ui\ memory\ library\ outlook\ research\ voice\   the six components, unchanged
```

Read in this order if you want the detail:

1. `JOE_CONTEXT_v1.md` - what it is and what is connected
2. `JOE_OPERATOR_GUIDE_v1.md` - how to use it
3. `JOE_KNOWN_LIMITATIONS_v1.md` - what it cannot do
4. `JOE_LOCAL_PROOF_REPORT_v1.md` - what was proven, with evidence
5. `JOE_BUILD_REPORT_v1.md` - the full account

## Removing it

Delete the `Assistant_Plugin` folder. Dispatch is unaffected. Nothing else to
undo.

That is what "plugin" means here, and it is the one claim in this whole build I
would stake the most on.

**Mike Zachary remains final authority.**
