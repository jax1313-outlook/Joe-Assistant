# Workstream 3 - Assistant Library - Architecture

**Component:** Assistant Library
**Version:** 1.0.0

---

## 1. Shape

```
                    +---------------------------+
                    |          cli.py           |  operator surface
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |        library.py         |  the facade
                    |  index / get / search /   |  read only, no state on disk
                    |  reference                |
                    +------+-------------+------+
                           |             |
                           v             v
                 +----------------+  +----------------+
                 |  document.py   |  |   search.py    |
                 |  read a file,  |  |  score, rank,  |
                 |  extract text  |  |  snippet       |
                 +----------------+  +----------------+
```

`document.py` and `search.py` know nothing about each other beyond the
`LibraryDocument` shape, and neither knows about the CLI. Dependency direction
is one way.

## 2. Modules

| Module | Responsibility | Tests |
| --- | --- | --- |
| `document.py` | `LibraryDocument`, text extraction for `.md` / `.markdown` / `.txt` / `.docx`, title derivation, doc id derivation, references. | 10 |
| `search.py` | Tokenizing, stopwords, scoring, ranking, snippets. | 18 |
| `library.py` | `Library` facade: index a root, list, get, find by path, search, reference. `IndexReport`. | 16 |
| `cli.py` | `index`, `list`, `search`, `get`, `reference`, `doctor`. | exercised manually |

**Third-party dependencies: zero.** Imports across the package: `__future__`,
`argparse`, `dataclasses`, `datetime`, `html`, `json`, `os`, `pathlib`, `re`,
`sys`, `zipfile`. Verified by test.

Note what is *not* there: no `python-docx`. Word documents are read by treating
the `.docx` as what it is - a zip archive containing `word/document.xml` -
and pulling the text out with `zipfile` and `re`. No Office, no COM, no install.

## 3. Read only, structurally

The component holds no write capability at all:

| Operation | Available? |
| --- | --- |
| Read a file | yes |
| Walk a directory | yes |
| Write, create, delete, rename, move | **no code path exists** |
| Cache the index to disk | no - the index is rebuilt per run, held in memory |

Three tests enforce it, one of which proves it by observation: it snapshots
every modification time in the corpus, runs an index, a search, and a retrieval,
then asserts nothing on disk changed.

## 4. Indexing

```
  Library(root)
      |
      +-- root missing or not a directory?  ->  LibraryError
      |
      +-- walk root recursively, sorted for stable ordering
              |
              +-- skip .git, .svn, __pycache__, node_modules, .venv, venv, .idea
              +-- unsupported extension  ->  count as skipped_unsupported
              +-- read fails             ->  count as skipped_unreadable, name it
              +-- over 5 MB              ->  skipped as unreadable, with a reason
              +-- otherwise              ->  index it
              |
              +-- past 5000 documents    ->  stop and set truncated = True
```

Every pass returns an `IndexReport`: root, indexed, skipped_unsupported,
skipped_unreadable, the names of unreadable files, and whether the pass was
truncated. Nothing is dropped silently.

## 5. Document identity

| Field | Derivation |
| --- | --- |
| `doc_id` | `DOC-` plus the relative path uppercased with non-alphanumerics collapsed to `-`, capped at 60 characters |
| `title` | first Markdown `# ` heading in the first 40 lines, else the file stem with underscores as spaces |
| `relative_path` | path below the root, always forward slashes |
| `modified_at` | file modification time, UTC ISO-8601 with `Z` |

Ids are derived from the path, not assigned, so they are stable across runs
without any stored state. A test asserts two separate `Library` objects over the
same root produce identical ids in identical order.

## 6. Search

**The score formula, in full:**

```
score = TITLE_WEIGHT x (occurrences of query terms in the title)
      + BODY_WEIGHT  x (occurrences of query terms in the body)

TITLE_WEIGHT = 5
BODY_WEIGHT  = 1
```

A document matching none of the terms scores nothing and is dropped. Ties break
on `doc_id`, so ordering is stable. A test asserts the code matches the formula
as written above.

**Tokenizing.** `[A-Za-z0-9][A-Za-z0-9'-]*`, lowercased. Hyphens and apostrophes
are kept, so `driver's` and `non-stop` survive as single terms.

**Stopwords.** A deliberately short list of 28 common words, visible at the top
of `search.py`. If removing them would empty the query, they are kept - so
searching for `what is the` still searches rather than returning nothing.

**Matched and missing terms.** Every hit reports both. `require_all=True` drops
any document with a missing term; the default keeps partial matches but labels
what was missing, so a thin result cannot be mistaken for a strong one.

**Snippets.** Up to three windows of ~90 characters either side of the first
match for each matched term, whitespace collapsed, with ellipses where the text
was cut.

## 7. References

```
<title> (<relative path>, modified <YYYY-MM-DD>)
```

Example:

```
Rate Floor Policy (Operations/RATE_FLOOR_POLICY.md, modified 2026-08-24)
```

The reference names the document and where it was read from, and nothing more.
It makes no claim about whether the content is current or approved.

## 8. Configuration

Root resolution order:

1. explicit `--root` / constructor argument
2. `ASSISTANT_LIBRARY_ROOT` environment variable
3. `ASST\3\Corpus` - the sample corpus in this folder

## 9. Limits, chosen deliberately

| Limit | Value | Why |
| --- | --- | --- |
| Max document size | 5 MB | a library document larger than this is almost certainly not prose |
| Max documents | 5000 | keeps a mis-pointed root from walking a whole disk; reported as `truncated` |
| Max snippets per hit | 3 | enough to judge relevance, short enough to read |

## 10. What was deliberately left out

- **No stored index.** Rebuilding per run costs a fraction of a second on a
  library this size and removes a whole class of staleness bugs. It also keeps
  the component free of any write capability.
- **No stemming, synonyms, or fuzzy matching.** Each would make results harder
  to predict, and a library search that quietly matches something adjacent is
  worse than one that returns nothing.
- **No PDF support.** Would need a third-party dependency. Declared under
  NOT IMPLEMENTED rather than half-built.
- **No relevance model.** A stated arithmetic formula is reviewable; a model is
  not.
