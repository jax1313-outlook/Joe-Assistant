# TRANSFER TO `D:\Claude-Build`

**This package is intended for transfer into `D:\Claude-Build` and nowhere
else.** It is the Claude build. Do not copy it into another platform's build
folder, and do not merge another platform's findings into it — the point of
separate folders is that each line of work evolves independently and can be
compared afterwards.

---

## Why it is not already there

This build runs on Linux, in a container with no `D:` drive and no access to
Mike's machine. `D:\Claude-Build` cannot be written to from here, so the work is
complete in the repository and packaged for you to move.

Stating that plainly rather than reporting a copy that did not happen is the
same rule as everything else in this build: `CLAUDE.md` §6 — never represent a
requested action as a completed action.

---

## What to copy

Everything in this repository. The package is the whole thing, not a subset.

    Joe-Assistant/                ->   D:\Claude-Build\

If you prefer the archive: `claude-build-phase3.zip` in the repository root
expands to a single top-level folder named `Claude-Build`, so extracting it at
the root of `D:` puts everything in `D:\Claude-Build` with nothing to rename.
It excludes `.git/` and the caches; the manifest covers exactly what is in it.

---

## Verifying it arrived intact

From `D:\Claude-Build`, with Python 3.11+:

    python -m pytest -q

Expected: **681 passed, 12 skipped**. The twelve skips are Tk display tests,
which have no display in a container and will run on the laptop.

`ROOT_MANIFEST.md` lists every file with its SHA-256. To check nothing was lost
or altered in transit:

    python Dispatch_Corrections/verify_manifest.py

It prints one line per mismatch and exits non-zero if there is any.

---

## What is in here that belongs to Dispatch rather than to this repository

`Dispatch_Corrections/patches/` holds fourteen patches against production
Dispatch. They are **not applied** to any Dispatch clone by this package.

- `0001`–`0012` are Phase 2, already open as pull requests #130–#142 against
  `jax1313-outlook/Dispatch`, in that order.
- `0013`–`0014` are Phase 3 and are **not** open as pull requests. They are held
  here awaiting your decision.

Applying them is a separate act, and it is yours:

    git checkout -b <branch> origin/main
    git am /path/to/Dispatch_Corrections/patches/00*.patch

`Dispatch_Corrections/docs/MERGE_PLAN.md` gives the order and the rollback.

---

## What this package must not do

- It must not be written into another platform's build folder.
- It must not have another platform's findings merged into it.
- It carries no credentials. Every Microsoft capability reads `UNCONFIGURED`
  because none has been configured, and no token, secret or connection string is
  in this tree. `Dispatch_Corrections/docs/` records the scan.

---

## After it lands

Nothing in this build has run on your machine. The first genuinely new
information will come from `DISPATCH_START_HERE.cmd` on the laptop, and from
walking the twenty-step proof path — which now runs, and has never been walked.

Mike remains final authority. Two items are waiting on you specifically; they
are §5 of `BUILD_SUMMARY.md`.
