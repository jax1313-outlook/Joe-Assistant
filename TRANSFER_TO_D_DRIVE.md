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
It excludes `.git/`, the caches, and everything `.gitignore` names — which is
where the runtime token cache and the memory records live. It is built *from*
the manifest, so the archive and the checksums cannot describe different sets of
files, and `ROOT_MANIFEST.md` travels inside it so an unpacked copy can check
itself.

---

## Verifying it arrived intact

From `D:\Claude-Build`, with Python 3.11+:

    python -m pytest -q

Expected: **738 passed, 12 skipped**. The twelve skips are environment
conditional and each says which thing it needs: six want a signed-in token
cache, five want `tkinter`, and one wants `ASSISTANT_TEST_OUTLOOK=1`. They will
run on the laptop once it is set up.

`ROOT_MANIFEST.md` lists every file with its SHA-256. To check nothing was lost
or altered in transit:

    python Dispatch_Corrections/verify_manifest.py

It prints one line per mismatch and exits non-zero if there is any.

---

## What is in here that belongs to Dispatch rather than to this repository

`Dispatch_Corrections/patches/` holds seventeen patches against production
Dispatch. They are **not applied** to any Dispatch clone by this package.

- `0001`–`0012` are Phase 2, already open as pull requests #130–#142 against
  `jax1313-outlook/Dispatch`, in that order.
- `0013`–`0017` are Phase 3 and the mission review, and are **not** open as pull
  requests. They are held here awaiting your decision. Merging the pull requests
  does not bring them — `0013` in particular is the one that makes PR #140's
  capacity wiring reach anything.

Applying them is a separate act, and it is yours:

    git checkout -b <branch> origin/main
    git am /path/to/Dispatch_Corrections/patches/00*.patch

`MERGE_PLAN.md` gives the order and the rollback.

---

## What this package must not do

- It must not be written into another platform's build folder.
- It must not have another platform's findings merged into it.
- It carries no credentials. Every Microsoft capability reads `UNCONFIGURED`
  because none has been configured, and no token, secret or connection string is
  in the package. `Dispatch_Corrections/docs/` records the scan.
- Running the suite leaves runtime files in the tree — a token cache directory
  and memory records under `Assistant_Plugin/runtime_data/`. The packager
  excludes them and a test pins that it does, so they cannot reach `D:`. An
  earlier archive did carry 129 of them; see `KNOWN_LIMITATIONS.md` §13.

---

## After it lands

Nothing in this build has run on your machine. The first genuinely new
information will come from `DISPATCH_START_HERE.cmd` on the laptop, and from
walking the twenty-step proof path — which now runs, and has never been walked.

Mike remains final authority. Three items are waiting on you specifically; they
are §5 of `BUILD_SUMMARY.md`.
