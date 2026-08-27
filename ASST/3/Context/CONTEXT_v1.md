# Workstream 3 - Assistant Library - Context

**Component:** Assistant Library
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\3`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

Read-only access to a document library. Three capabilities and nothing else:

- **Search** - find documents by their words
- **Retrieve** - read one document in full
- **Reference** - produce a citable reference to a document

## Why read only matters here

Company Library holds approved company facts and reusable assets. Approved
material is approved because a person approved it. A component that can search
the library can also be a component that quietly edits it, and then nobody knows
what is approved any more.

So this component is read only **structurally**, not by policy. There is no code
in it that opens a file for writing, creates a directory, deletes, or renames.
A test fails the build if such a call ever appears. The guarantee does not depend
on anyone remembering the rule.

## What "the library" means here

A folder of documents. The root is configurable three ways, in order:

1. an explicit `--root` on the command line
2. the `ASSISTANT_LIBRARY_ROOT` environment variable
3. the sample corpus inside this folder, `ASST\3\Corpus`

The default exists so the component runs and is testable with no setup. Pointed
at the real Company Library, it still only reads.

## The sample corpus

`ASST\3\Corpus` holds six short documents written for this workstream. Each one
carries a notice saying it is sample material, not approved company doctrine or
policy. They exist so search and retrieval have something real to work on and so
the tests are not fictional.

They are not a copy of the real Company Library and must not be treated as
authoritative.

## What it reads

| Type | How |
| --- | --- |
| `.md`, `.markdown`, `.txt` | read as text |
| `.docx` | text pulled out of the archive with the standard library - no Word, no Office automation, no COM |

Anything else is counted as skipped and reported. Unreadable files are counted
and named rather than silently dropped.

## Search that can be predicted

The ranking is a stated formula, not a heuristic:

```
score = 5 x (query term occurrences in the title)
      + 1 x (query term occurrences in the body)
```

Ties break on document id, so the same query gives the same order every time.
A reviewer can read the formula and predict the result. No model is involved.

When nothing matches, the component returns nothing and says so. It does not
guess, infer, or substitute a near miss.

## What it deliberately is not

- no writing, editing, moving, renaming, or deleting
- no retention or memory
- no Outlook, email, calendar, or contacts
- no voice
- no research and no network access
- no approval authority - retrieving a document does not make its contents true,
  current, or approved for a given use

Research is not doctrine, and a document is not a decision. This component hands
back what a document says and where it came from. Everything after that stays
with Mike Zachary.

## Runtime

Python 3.10 or newer through the `py` launcher. Verified on this machine:
Python 3.14.5. Standard library only. Nothing is installed.

## Relationship to other workstreams

None. This folder does not know any other workstream exists. It imports nothing
from folders 1, 2, or 4 through 6.
