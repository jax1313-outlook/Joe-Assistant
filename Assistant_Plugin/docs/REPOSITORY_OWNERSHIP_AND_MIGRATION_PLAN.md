# Repository Ownership and Migration Plan

**Mission:** BOOTSTRAP THE DISPATCH COPILOT AGENT, §10.E
**Type:** Plan only. **Nothing was moved, branched, or created.**
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

---

## 1. Repository roles

| Role | Path | Status |
| --- | --- | --- |
| **Authoritative Dispatch repository** | **not established** | **BLOCKED — Mike must name it.** Not available to this workspace |
| **Joe salvage source** | `D:\SANDBOX\Assistan_Building\Assistant_Plugin` | exists, current, 74 Python files |
| **Component workstreams** | `D:\SANDBOX\Assistan_Building\ASST\1..6` | exist, 350 tests, **untouched throughout** |
| **Sandbox** | `D:\SANDBOX\Assistan_Building` | the external-drive isolation Joe was built in |
| **Preservation location for legacy code** | **not created** | recommended below |
| **Distribution repository** | **does not exist** | **and must not be created** — see §6 |

**A fact that shapes everything below: none of these is a git repository.**
Verified — zero `.git` directories anywhere in the Joe tree. Every mission to
date forbade creating one. So there is currently **no version history, no
branches, and no ability to diff or revert** anything in Joe.

---

## 2. The consequence, stated plainly

**A migration of this size without version control is the largest avoidable risk
in the plan.**

The build plan's WP-2 splits an 1,128-line file that 154 tests and 140 proof
references depend on. Doing that with no ability to diff, branch, or revert
means the only rollback is a manual file copy that someone has to remember to
take.

**This is worth raising even though creating a repository is prohibited**,
because the prohibition was written for a different reason — Mike's operational
acceptance gates the *distribution* repository, not local version control.

**Three options, and they are genuinely different:**

| Option | What it gives | What it costs |
| --- | --- | --- |
| **A. Local git, never pushed** | full history, branches, instant revert. Stays on the external drive; no remote, no GitHub | requires Mike to lift the "no repository" rule for *local* use only |
| **B. Dated folder snapshots** | crude rollback, no history, no diffs. Needs discipline to take before every package | no rule change; large duplication; easy to forget exactly when it matters |
| **C. Neither** | nothing | WP-2 becomes materially more dangerous |

**Recommendation: Option A, as a narrowly scoped decision.** A local git
repository with no remote is not "creating the repository" in the sense the
acceptance gate means — that gate is about distribution and about Mike's
approval of Joe as an operational tool. **But it is Mike's call, and I have not
run `git init`.**

---

## 3. Migration strategy — if version control is available

| Branch | Purpose |
| --- | --- |
| `main` | the current working Joe, untouched, always launchable |
| `voice-dock` | WP-1 |
| `agent-lifecycle` | WP-2 |
| `dispatch-integration` | WP-3 onward, **not started until Dispatch is available** |

**Rules:** one work package per branch; `main` must always pass 329 tests and
24/24 proof steps; nothing merges without its own proof.

## 3b. If version control is not available

Before each work package: copy the whole tree to
`D:\SANDBOX\Assistan_Building\_snapshots\<date>_<package>_before\`.

Crude, and better than nothing. Every snapshot is kept.

---

## 4. Preservation of rejected and legacy code

**Nothing is deleted. Ever.** The salvage matrix classifies three components
RETAIN AS LEGACY and zero DO NOT USE.

Recommended location:

```
D:\SANDBOX\Assistan_Building\_legacy\
    library_fs\            superseded when Dispatch's Library interface exists
    research_provider\     pending the Research ownership ruling (conflict C-4)
    standalone_proofs\     8 proof scripts + 13 launchers + evidence files
    standalone_ui\         the tkinter window shell
```

**Move only when a replacement is proven working.** Retiring a capability before
its replacement exists removes something that works for no gain — the same
reasoning that keeps Joe's Library index alive until Dispatch's is reachable.

**The `ASST\1..6` workstreams are not migrated at all.** They stay where they
are, unrenamed and untouched, as the component-isolation record.

---

## 5. Merge and proof gates

No work package merges without all of:

| Gate | Standard |
| --- | --- |
| Tests | all pass, and the package adds its own |
| Local proof | 24/24 steps still pass |
| Control audit | 20/20 still pass |
| Drift guards | 0 Manager classes; Dispatch not contacted unless the package authorises it; no writes outside the root; no credential in any file |
| **Card discipline** | **0 card structures inside Joe**; no durable copy of card state |
| Operational proof | the thing the package claims to fix actually works, demonstrated |
| Rollback | a documented way back |

**Two gates only Mike can pass:** voice input with his voice, and operational
acceptance. Neither can be automated, and neither should be claimed.

---

## 6. Distribution repository — still gated

**Do not create it.** The condition is unchanged and explicit: only when Mike
states that Joe has passed operational acceptance and directs its creation.

Passing tests is insufficient. A working Copilot connection is insufficient. A
deployment package is insufficient. **Mike's real use is the gate.**

Local version control under §2 Option A is a **different question** and should
not be treated as satisfying or violating this gate.

---

## 7. Local deployment path

Current: `D:\SANDBOX\Assistan_Building\Assistant_Plugin\Deployment\`, with a
`JOE` desktop shortcut plus three utility shortcuts, all verified.

**Inside Dispatch this changes fundamentally.** Joe starts when Dispatch starts,
so a separate Joe launcher stops being the delivery mechanism. The existing
launchers move to legacy — **but not until Joe actually runs inside Dispatch**,
because until then they are the only way Mike can run it at all.

## 8. Ownership backup

The external drive is currently the only copy of Joe. **There is no backup and
no version history.** For a body of work this size that is a real exposure, and
it is worth a decision independently of everything else in this plan.

---

## 9. Unresolved, requiring Mike

1. **Which repository is authoritative Dispatch** — blocks WP-3 onward
2. **Local version control: yes or no** — materially changes WP-2's risk
3. **Backup of the sandbox** — currently a single copy on one drive

---

Mike Zachary remains final authority.
