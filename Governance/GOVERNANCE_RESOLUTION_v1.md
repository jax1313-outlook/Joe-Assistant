# Governance Resolution v1 — the fork, and how it is closed

**Recorded:** 2026-09-12 · **Repository:** `jax1313-outlook/Joe-Assistant` (the
proving ground) · **Status of this document:** a resolution *proposal* with a
working implementation. It changes no production repository. Two of its four
outputs are files that must be placed by hand in repositories this work is not
permitted to write to, and they are shipped here as `Governance/pointers/`.

---

## 1. The finding, restated from evidence

Five repositories carry a constitution. They are not the same constitution.

| Constitution | Repositories | SHA-256 (first 12) |
|---|---|---|
| `DISPATCH_CONSTITUTION_v2.md` | Claude, Joe-Assistant, Publisher | `16708d4cfa7b` (identical in all three) |
| `DISPATCH_CONSTITUTION_v3.md` | Claude-3, Library | `acabb4c1c0f9` (identical in both) |
| *neither* | **Dispatch — the repository that actually runs** | — |

Across the seven repositories there are **87 governance-shaped documents** and
**18 clusters of byte-identical duplicates**.

Both constitutions mandate a **Manager**:

- v2 §6 lists "Manager / Control" as a core department; §14 and §18 forbid
  "bypassing Manager".
- v3 §7.1: "Manager is the Run Office function."

`Dispatch/CLAUDE.md` §5.6 says the opposite, in terms:

> **There is no Manager component in the current architecture. Do not create,
> restore, reference, or infer a Manager component, Manager agent, or Manager
> authority.**

And it is not merely written down. `Dispatch/tests/test_repository_doctrine.py`
enforces it with an allowlist of every permissible occurrence of the word
("task manager" — the Windows application; "context manager" — the Python
construct; and so on). A build that introduces a Manager fails.

**So an agent cold-starting in `Claude/`, `Joe-Assistant/` or `Publisher/` reads
its constitution and builds toward a component the production repository
rejects.** That is the defect. It is an authority defect, not a documentation
defect.

## 2. What was NOT done

**The constitutions were not merged.** Merging two documents that disagree
produces a third document that governs nothing and that nobody ratified.

**No document was deleted or rewritten.** `Dispatch/CLAUDE.md` §7 is explicit:
*"Do not edit old decisions to hide their history. Mark them SUPERSEDED and cite
the ruling that replaced them."* Every superseded document stays exactly where it
is, byte for byte.

**Manager was neither built nor removed.** See §4.

## 3. Determining the current authority from repository evidence

The question is not "which document is newest". It is "which document does the
repository actually obey". Three facts answer it:

1. **`Dispatch/CLAUDE.md` declares itself the entry point** — "the first file to
   read in this repository... so that a builder arriving with no conversation
   history can be useful within one reading".
2. **Its clauses are executable.** `tests/test_repository_doctrine.py` asserts
   them against the source tree, and its docstring states the standing: *"any
   failure blocks a readiness claim"*. No constitution in any other repository is
   enforced by anything.
3. **`Dispatch/` is the only repository containing the running program** —
   ~34,000 lines of freight code plus `cin_lite`. The other repositories hold
   documents, a worker library each, and the proving ground.

Authority therefore rests with `Dispatch/CLAUDE.md`, supported by
`DECISION_LOG.md` (the ordered record) and `tests/test_repository_doctrine.py`
(the enforcement). This is recorded as `authority` in the registry, not asserted
in prose.

## 4. The Manager adjudication

**Ruling: Manager remains a named, unbuilt capability. Nothing is created.
Nothing is removed. The contradiction is a category error, and the category is
now recorded.**

The reasoning, entirely from repository evidence:

- `Dispatch/docs/MANAGER.md` is the only document in any repository that states
  Manager's *implementation* status, and it is unambiguous: **"a capability named
  in planning and never built... This document authorizes no code, no route, no
  data model, and no runtime behavior."**
- The constitutions describe an intended **organisational shape** — departments,
  functions, who routes attention to whom. v3 §7.1 even says Manager "is not a
  direct chat interface for Mike", which is a statement about a role, not an
  instruction to instantiate a service.
- `CLAUDE.md` §5.6 governs what the **running program may contain**.

These answer different questions. A constitution naming a Run Office function is
not a licence to add a module, and a doctrine forbidding the module is not a
repudiation of the organisational idea. The fork existed because nothing said
which question each document answers — so the registry now says it, per
document, and `dispatch_governance answer "may a Manager component be built into
Dispatch"` returns `Dispatch/docs/MANAGER.md`.

Had the evidence genuinely conflicted — a constitution ruling directly on code —
this would have been escalated rather than decided. It is recorded as **U-01** in
the registry with that residual risk stated.

## 5. What was built

| Output | Where | What it does |
|---|---|---|
| **Registry** | `Governance/GOVERNANCE_REGISTRY.json` | 23 documents, each with repository, path, SHA-256, status, scope, successor, and a note. Plus nine `answers` mapping a question to the one document that decides it, and four `unresolved` items. |
| **Library + CLI** | `Governance/dispatch_governance/` | `show <repo>`, `answer "<question>"`, `check <workspace>`. Exit code 1 on a blocking finding, so CI can read it. |
| **Drift detector** | `dispatch_governance/drift.py` | Compares every registered document against local checkouts. No network, no credentials — a governance check that needs an API token is a governance check that does not run. |
| **Pointer generator** | `Governance/tools/write_pointers.py` | Writes the `GOVERNANCE.md` that marks a repository's superseded documents as superseded, without touching them. |
| **Recorder** | `Governance/tools/record_registry.py` | Re-records the registry deliberately. Never automatic: a tool that regenerated on every commit would silently re-bless whatever a document currently says, which is the drift the detector exists to catch. |

### The four statuses

- **CURRENT** — binding now.
- **SUPERSEDED** — was binding; something replaced it, and the registry names
  what. Kept and readable.
- **HISTORICAL** — never governed, or governs nothing now, retained as a record.
  `docs/MANAGER.md` lives here.
- **ADVISORY** — describes intent, authorises no code. Both constitutions live
  here (v2 additionally superseded by v3 *as intent*).

An **answer may never point at a SUPERSEDED document**, and the registry refuses
to validate if one does.

## 6. The drift finding this produces today

```
$ python -m dispatch_governance check <workspace>
  BLOCKING (2)
    [STALE_AUTHORITY_UNMARKED] Claude/GOVERNANCE.md
      Claude carries 2 superseded governing document(s) and no GOVERNANCE.md
      saying what actually governs. An agent starting there reads the
      superseded one and follows it.
    [STALE_AUTHORITY_UNMARKED] Publisher/GOVERNANCE.md
      ...
```

`Joe-Assistant` no longer appears: its `GOVERNANCE.md` is written, and its
`DISPATCH_CONSTITUTION_v2.md` is untouched beside it.

The two remaining findings are **correct and outstanding**. This work is
restricted to the sandbox repository and may not write to `Claude/` or
`Publisher/`. The exact files are generated and shipped at
`Governance/pointers/Claude-GOVERNANCE.md` and
`Governance/pointers/Publisher-GOVERNANCE.md`; placing them is a human action
listed in the final review points.

## 7. Conflicts that repository evidence cannot resolve

| id | Question | Settled by evidence? | Disposition |
|---|---|---|---|
| **U-01** | Does `CLAUDE.md` supersede v3, or are they different kinds of document? | Yes | Different kinds. Neither supersedes the other; the registry records which question each answers. Risk: a future v4 ruling directly on code would be a genuine conflict. |
| **U-02** | Who is authoritative for a worker's own charter? | Yes | Its own repository. No production document contradicts any worker README. |
| **U-03** | **Is v3 approved, or a draft?** | **No** | Its header reads *"Current Controlled Constitution - v3 Replacement Draft"* — contradictory — and no repository holds an approval record. Registered **ADVISORY**, which is true under either reading, and no code decision rests on it. **Requires Mike.** Inferring ratification is precisely the manufactured approval `CLAUDE.md` §4 forbids. |
| **U-04** | `Hold/` carries `MANAGER_CONSTITUTION_v1` twice | No | Left in place, unregistered: `Hold` is staging and its `library_seed/` is data, not governance of Dispatch. Flagged for review **before** any promotion of that seed corpus into Library. |

## 8. Running it in CI

```yaml
- name: Governance drift
  run: |
    python -m dispatch_governance check "$GITHUB_WORKSPACE/.."
```

Exit 1 on any blocking finding. It needs the sibling repositories checked out;
where they are not, it reports `REPO_NOT_CHECKED_OUT` as information rather than
silently passing — a check that cannot see a repository must not report it clean.

## 9. What this does not claim

It does not claim any repository other than this one has been changed. It does
not claim v3 is ratified. It does not claim the registry is complete: 23 of the
87 governance-shaped documents are registered, chosen because they are the ones
that *assert authority*. The remaining 64 are context, matrices and reports, and
registering them without reading each one would be exactly the unverified claim
this programme's vocabulary exists to prevent.
