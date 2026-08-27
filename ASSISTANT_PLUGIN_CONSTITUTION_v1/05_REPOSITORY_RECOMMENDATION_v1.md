# ASSISTANT PLUGIN CONSTITUTION v1
## Document 5 of 5 — Repository Recommendation

**Subject:** Where Assistant code should live, and why
**Version:** 1.0
**Final authority:** Mike Zachary
**Status:** Recommendation. Doctrine only — no repository is created, moved, or
configured by this document.

---

## 1. The recommendation

**Keep the Assistant in its own repository, entirely separate from Dispatch.**

```
    dispatch/                          <-- Dispatch Core. Untouched by this.
      ...
      interfaces/                      <-- published by Dispatch, owned by Dispatch
                                           consumed by anyone; knows no consumers

    assistant-plugin/                  <-- everything Assistant
      doctrine/                        <-- this document set
      components/
        ui/
        memory/
        library/
        outlook/
        research/
        voice/
      contracts/                       <-- the Dispatch interface version consumed
```

Two repositories. One dependency, running one way. Nothing shared.

## 2. Why — the argument that decides it

**The removability test must be demonstrable, not argued.**

Constitution Article V says Dispatch must remain fully functional if the
Assistant plugin is removed. The question is how anyone would ever *show* that.

| Repository shape | "Remove the plugin" means | Is removability provable? |
| --- | --- | --- |
| Assistant inside Dispatch's repo | a refactor — find every Assistant file, untangle every reference, hope nothing was missed | **No.** It is an opinion held by whoever did the untangling. |
| Assistant in its own repo | **delete the repository** | **Yes.** Dispatch still builds, still runs, still works — or it does not, and you have found a breach. |

That is the whole case. Separation turns the central doctrinal claim of this
Constitution from something asserted into something **demonstrated in one
step**.

## 3. What separation also buys

**3.1 Encapsulation becomes physical.**
Dispatch's boundary is a repository boundary. Reaching around it requires
deliberate effort that shows up in a diff, rather than being one convenient
import away.

**3.2 The dependency direction is visible at a glance.**
The Assistant repo references Dispatch's published interface. The Dispatch repo
contains **zero** references to the Assistant. Anyone can verify that in seconds
— which makes Architecture 2.2 auditable rather than aspirational.

**3.3 Dispatch is not held back.**
Separate repositories mean separate release cadence. Dispatch changes when
Dispatch needs to, and the plugin adapts on its own schedule. This is
Architecture 2.3 made structural.

**3.4 Dispatch stays reviewable alone.**
Someone auditing Dispatch reads Dispatch. They do not wade through Assistant
code to find out what the system of record actually does.

**3.5 Blast radius is bounded and obvious.**
A mistake in the Assistant repo cannot reach operational truth, because
operational truth is not in that repository.

**3.6 The plugin assumption is enforced by daily friction.**
In a shared repo, "just call into Dispatch directly" is easy and invisible.
Across a repository boundary it is neither. The right thing becomes the path of
least resistance, which is the only durable form of enforcement.

## 4. Options considered

| Option | Assessment |
| --- | --- |
| **A. Monorepo — Assistant inside Dispatch** | **Rejected.** Removability becomes unprovable (§2). Encapsulation depends on discipline alone. Reverse dependency is one import away and will eventually happen. Convenient today, and the exact mechanism by which a plugin becomes core. |
| **B. Two repositories — Dispatch, Assistant** | **Recommended.** Removability provable. Dependency direction visible. Dispatch reviewable alone. Simple enough to actually hold. |
| **C. One repository per Assistant component (seven repos)** | **Rejected.** Component isolation is a design property, already achieved with folder boundaries and enforced by tests. Seven repositories buys nothing extra and costs coordination on every change. Isolation that is already proven does not need more ceremony. |
| **D. Assistant components inside Dispatch as "plugins" folders** | **Rejected.** Same failure as A wearing plugin vocabulary. Sitting inside the Core's repository makes it part of the Core in every way that matters. |

## 5. Inside the Assistant repository

**5.1 Doctrine at the root.** This document set lives in `doctrine/`, at the top
of the Assistant repo, where nobody can build a component without walking past
it.

**5.2 Components as bounded modules**, one directory each, matching what is
already built: UI, Memory, Library, Outlook, Research, Voice.

**5.3 Each component keeps what it already has** — its own context,
constitution, architecture, source, tests, operator guide, and reports. That
structure was built to be independently reviewable and it should not be
flattened.

**5.4 A component may not import another component.** The rule already holds and
is already enforced by tests. Nothing about a shared repository relaxes it.

**5.5 `contracts/` records which version of Dispatch's published interface the
plugin was built against.** It is a **record of what was consumed**, not a
definition of what is available. The Assistant does not define the terms of its
own access (Architecture 3.8).

## 6. What must never appear in the Assistant repository

| Never | Why |
| --- | --- |
| **Dispatch source code** | It would make the plugin a fork of the Core, and the boundary meaningless |
| **Operational records** | Dispatch owns them. A copy in a repository is a second system of record with a version history. |
| **Credentials, tokens, keys, connection strings** | Not decided here, and never committed anywhere |
| **Real customer, broker, load, or rate data** | Sample and fixture data only, labelled as such |
| **Anything Dispatch depends on** | The dependency runs one way. If Dispatch needs it, it is not plugin material. |

**6.1** The sixth row is the one to watch. The day something in the Assistant
repository becomes load-bearing for Dispatch, the Assistant has stopped being a
plugin — and the repository boundary is what makes that visible instead of
gradual.

## 7. Where the interface itself lives

**Published from Dispatch's side.** The interface is Dispatch's to define, own,
version, and publish (Architecture 3.8).

This does not break encapsulation. **Publishing an interface is not knowing
about a consumer.** Dispatch offers a surface; who reads it is not Dispatch's
concern, and Dispatch's code contains no reference to the Assistant.

The Assistant repository records which version it consumes. It does not
negotiate, extend, or define that surface.

## 8. Current work, and what this means for it

Stated for clarity. **This document creates no obligation to move anything.**

| What exists now | Standing under this doctrine |
| --- | --- |
| `ASST\1..6` — the six Assistant components | **Plugin components.** Correctly built: isolated, no integration, no cross-dependency. They are ready for a plugin repository as they stand. |
| `Build\sandbox_engine` — Sandbox Engine v1 | **Plugin component.** Its doctrine — records expire, nothing is promoted, nothing routed to Dispatch, Company Library, or Archive — is this Constitution applied before it was written. |
| This document set | **Doctrine.** Belongs at the root of the Assistant repository when one is created. |

**8.1** Nothing already built violates this doctrine. That is not luck — it is
the result of having built each piece with hard boundaries, structural
prohibitions, and honest reports of what was not proven. The doctrine could be
written afterwards because the work was done as though it already existed.

**8.2** No migration is proposed, scheduled, or begun by this document.

## 9. Sequencing, if and when Mike chooses to proceed

Offered as a recommendation only. Nothing here is authorized, scheduled, or
started.

1. Mike accepts or amends this document set.
2. An Assistant repository is created, with `doctrine/` at its root.
3. Existing components move in unchanged.
4. Dispatch publishes an interface — **when Dispatch is ready, on Dispatch's
   terms**, and not before.
5. The plugin consumes it, recording the version.
6. The removability test is run for real: remove the plugin, confirm Dispatch is
   whole.

**9.1** Step 4 is Dispatch's, and it is the gate. The Assistant does not
initiate it, does not specify it, and waits.

**9.2** Step 6 is not a formality. It is the moment the central claim of this
Constitution is either verified or found false, and it should be run before
anyone relies on the plugin for anything.

## 10. Summary

**Recommendation: two repositories.** Dispatch as it is; the Assistant separate,
depending one way on a published interface it does not own.

The reason is a single sentence: **it makes "Dispatch works without the
Assistant" something you can prove by deleting a folder, instead of something
you have to take on trust.**

Mike Zachary remains final authority over this recommendation and over whether
any of it happens.
