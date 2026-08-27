# Workstream 3 - Assistant Library - Test Report

**Component:** Assistant Library
**Version:** 1.0.0
**Runtime:** Python 3.14.5 via `py`, standard library only

---

## Result

**53 tests. 53 passed. 0 failed. 0 errors. 0 skipped.**

```bash
D:\SANDBOX\Assistan_Building\ASST\3\Tests\run_tests.cmd
```

Underneath: `py -m unittest discover -s Tests -v`.
Raw output: `Tests\_last_test_run.txt`. Source: `Tests\test_assistant_library.py`.

## Coverage

| Group | Tests | Establishes |
| --- | --- | --- |
| `TestCorpusIndexing` | 9 | The corpus indexes, the report matches reality, Markdown titles come from the H1, paths use forward slashes, size and modified time are captured, word and line counts work, doc ids are unique and stable across runs, a missing root and a file-as-root both raise. |
| `TestDocumentReading` | 10 | Plain text and `.docx` both read, `.docx` needs no Office, unsupported types are refused, a corrupt `.docx` is reported rather than crashing, unreadable files are skipped **and named**, unsupported files are counted, titles fall back to the file name, doc ids derive from the path, noise directories are skipped, all four extensions are covered. |
| `TestSearch` | 18 | Title and body matching, case insensitivity, no-match returns nothing, title matches outrank body matches, matched **and missing** terms reported, `--all` drops partial matches, limits respected, snippets produced, references attached, ordering stable across runs, the score matches the stated formula, stopword handling both ways, empty queries, tokenizer keeps hyphens and apostrophes, the stopword list stays small, and an empty library searches cleanly. |
| `TestRetrieveAndReference` | 7 | Full retrieval, unknown ids and paths raise, membership checks, references name title/path/date, list references, and text is excluded from `to_dict` unless asked. |
| `TestBoundaries` | 9 | No workstream import, no network/email/vendor import, standard library only, **no write call anywhere in the package**, no mutating method on `Library`, `ZipFile` only opened read-only, **indexing changes nothing on disk**, the default root is this folder's corpus, and no mail/calendar/voice/retention capability is defined. |

## The read-only proof

`test_indexing_the_corpus_changes_nothing_on_disk` is the one that matters. It:

1. records the modification time of every file in `ASST\3\Corpus`
2. builds a `Library`, runs a search, and retrieves a document
3. records every modification time again
4. asserts the two snapshots are identical

This proves the read-only claim by observing the filesystem rather than by
reading the code. Two further tests scan the source for any write call and check
that `ZipFile` is never opened in write or append mode.

## Operator verification

```
library.cmd index    -> 6 documents indexed, 0 skipped unsupported, 0 unreadable
library.cmd search "mission visibility"
                     -> 1 match, score 20, Doctrine/MISSION_VISIBILITY.md
                        matched: mission, visibility, with two context snippets
library.cmd doctor   -> access mode READ ONLY, write calls in package: none,
                        network modules: none, 6 documents indexed
```

## Test data containment

Tests that need to create files create them inside
`Tests\_workspace\<random>\` and remove them in `tearDown`. The corpus is only
ever read. No test writes outside `ASST\3`.

## Boundary verification

Imports across the whole package: `__future__`, `argparse`, `dataclasses`,
`datetime`, `html`, `json`, `os`, `pathlib`, `re`, `sys`, `zipfile`. Nothing
else. No third party - notably no `python-docx`; Word files are read with
`zipfile` and `re`. No networking module. No workstream 1, 2, or 4-6 import.

---

## PROVEN CAPABILITIES

1. Indexes a configurable document root recursively.
2. Reads Markdown, Markdown-extension, and plain-text documents.
3. Reads `.docx` documents with no Word, Office, COM, or third-party library.
4. Derives titles from Markdown H1 headings, falling back to the file name.
5. Derives stable document ids from paths, identical across separate runs.
6. Reports skipped-unsupported and skipped-unreadable counts, and names the
   unreadable files.
7. Reports a truncated index as truncated.
8. Skips noise directories such as `__pycache__` and `.git`.
9. Searches by title and body terms, case-insensitively.
10. Ranks by the stated formula: `5 x title matches + 1 x body matches`.
11. Produces the same ordering for the same query on every run.
12. Reports which query terms matched and which did not.
13. Drops partial matches when every term is required.
14. Returns nothing for a no-match query, without guessing.
15. Produces context snippets around matches.
16. Retrieves a document in full by id or by path.
17. Produces a citable reference naming title, path, and modification date.
18. Handles a corrupt `.docx` by reporting it, not crashing.
19. Raises clearly on a missing root, a file used as a root, and unknown ids.
20. **Changes nothing on disk** - proven by filesystem observation.
21. Contains no write call anywhere in the package.
22. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. **The CLI.** Exercised by hand as recorded above; no automated test drives
   `cli.py`. Its rendering and argument parsing are unproven by the suite.
2. **The `ASSISTANT_LIBRARY_ROOT` environment override.** Implemented in
   `resolve_root()`; tests pass an explicit root instead.
3. **Reading a real Company Library.** Verified only against the six-document
   sample corpus and small generated fixtures. Never pointed at the real
   library.
4. **The 5000-document truncation limit.** The flag and the code path exist;
   no test builds a corpus large enough to trigger it.
5. **The 5 MB document size limit.** Implemented; no test creates a file that
   large.
6. **Performance at scale.** The largest test corpus is six documents. Index
   and search time on thousands of documents is unmeasured.
7. **Documents in encodings other than UTF-8.** Read with `errors="replace"`, so
   they will not crash, but the resulting text quality is untested.
8. **`.docx` files with complex structure** - tables, footnotes, headers,
   tracked changes, text boxes. Only simple paragraph text is tested.

## NOT IMPLEMENTED

1. **Any write, edit, move, rename, or delete capability.** Deliberately absent.
2. **PDF support.** Would require a third-party dependency.
3. **`.xlsx`, `.pptx`, `.doc`, `.rtf`, or HTML support.**
4. **Stemming, synonyms, fuzzy matching, or spelling correction.**
5. **Phrase search, boolean operators, or field-scoped queries.**
6. **A stored or incremental index.** Rebuilt in memory every run.
7. **Any retention, memory, or state between runs.**
8. **Any Outlook, email, calendar, or contact capability.**
9. **Any voice capability.**
10. **Any network or web capability.**
11. **Any approval, currency, or authority judgement about a document.**
12. **Access control, permissions, or redaction.**
13. **Any user interface.** Command line only.

## KNOWN LIMITATIONS

1. **Whole-word matching only.** `policies` will not find `policy`. No stemming
   is deliberate - a library search that quietly matches something adjacent is
   worse than one that returns nothing.
2. The index is rebuilt on every run. Fine at this size; unmeasured at scale.
3. The score formula favours short documents with the term in the title. That is
   usually right for a policy library and can be wrong for a long document that
   discusses the term throughout.
4. Snippets are the first match per term, not the best match.
5. The sample corpus is sample material, not approved company content, and must
   not be mistaken for the real Company Library.
6. Documents over 5 MB and libraries over 5000 documents are cut off. Both are
   reported, neither is silent.
7. Verified on Windows 11 with Python 3.14.5 only.
8. The component cannot tell you whether a document is current or approved. That
   judgement stays with Mike Zachary.
