# Workstream 3 - Assistant Library - Operator Guide

**For:** Mike Zachary
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\3`

---

## What this is

Read-only access to a folder of documents. Search it, read one, get a reference
to cite. It cannot change anything it reads.

## The command

```bash
D:\SANDBOX\Assistan_Building\ASST\3\Source\library.cmd index
```

Everything below uses `library.cmd`.

## Search

```bash
library.cmd search "mission visibility"
```

You get ranked matches with the document id, the path, which of your terms
matched, which did **not**, and a few lines of context around each hit.

Require every term:

```bash
library.cmd search "rate floor policy" --all
```

If nothing matches, it says so. It does not guess or return something close.

## Read a document

```bash
library.cmd get DOC-DOCTRINE-MISSION-VISIBILITY-MD
```

Just the first part:

```bash
library.cmd get DOC-DOCTRINE-MISSION-VISIBILITY-MD --lines 20
```

## Get a reference to cite

```bash
library.cmd reference DOC-OPERATIONS-RATE-FLOOR-POLICY-MD
```

Gives you something like:

```
Rate Floor Policy (Operations/RATE_FLOOR_POLICY.md, modified 2026-08-24)
```

## See what is indexed

```bash
library.cmd index
```

```bash
library.cmd list
```

`index` reports how many documents were read, how many were skipped as
unsupported, and names anything it could not read. Nothing is dropped quietly.

## Point it at a real library

By default it reads the sample corpus in this folder. To read somewhere else:

```bash
library.cmd --root "C:\path\to\Company Library" search "detention"
```

Or set it once for the session:

```bash
set ASSISTANT_LIBRARY_ROOT=C:\path\to\Company Library
```

**It still only reads.** There is no write capability in this component to turn
on. Pointing it at the real Company Library cannot change the real Company
Library.

## What it can read

| Type | Supported |
| --- | --- |
| `.md`, `.markdown`, `.txt` | yes |
| `.docx` | yes - no Word or Office needed |
| `.pdf`, `.xlsx`, `.pptx`, anything else | no, counted as skipped |

## Check the boundaries yourself

```bash
library.cmd doctor
```

Prints the configured root, confirms access mode is READ ONLY, confirms no write
calls exist in the package, and confirms no network module is loaded.

## Run the tests

```bash
D:\SANDBOX\Assistan_Building\ASST\3\Tests\run_tests.cmd
```

53 tests. One of them snapshots every file in the corpus, runs a full index,
search, and retrieval, and then proves nothing on disk changed.

## About the sample documents

`ASST\3\Corpus` holds six short documents written for this workstream so it runs
and tests with no setup. Each one says, at the bottom, that it is sample
material and **not approved company doctrine or policy**.

They are not a copy of the real Company Library. Do not treat them as
authoritative.

## What this will NOT do - read this part

**It will not change anything.** No writing, editing, moving, renaming, or
deleting. Not disabled - absent.

**Finding a document does not make it true.** Retrieval tells you what a
document says and where it came from. Whether it is current, approved, or right
for what you are doing is your call.

**It will not guess.** No match means no match.

**It has no memory.** The index is rebuilt every run and held in memory. Nothing
is remembered between runs.

**It will not send email, read your calendar, listen, or reach the network.**
There is no code in it that could.

## If something goes wrong

**`py was not found`** — install Python 3.10 or newer from python.org. `python`
on this machine is the Microsoft Store stub, which is why everything uses `py`.

**`ERROR: library root does not exist`** — check the `--root` path or
`ASSISTANT_LIBRARY_ROOT`.

**`NOT FOUND: no such document`** — wrong doc id. Run `library.cmd list` to see
them.

**A document you expected is missing** — check the skipped counts from
`library.cmd index`. It is probably an unsupported type, such as a PDF.

**Search finds nothing you expected** — try fewer terms, or drop `--all`. The
match is on whole words; there is no stemming, so `policies` will not match
`policy`.
