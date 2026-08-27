# Workstream 3 - Assistant Library - Build Report

**Component:** Assistant Library
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\3`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## MISSION

Build Company Library access: search, retrieve, reference. Read only.

No Outlook. No Voice. No Memory. No Integration.

## FILES CREATED

```
ASST\3\
  README.md                                     reviewer entry point
  BUILD_REPORT_v1.md                            this file
  TEST_REPORT_v1.md                             full test results
  Context\CONTEXT_v1.md                         what this is and why read only
  Constitution\CONSTITUTION_v1.md               binding rules and prohibitions
  Architecture\ARCHITECTURE_v1.md               modules, indexing, the score formula
  Operator_Guide\OPERATOR_GUIDE_v1.md           how Mike runs it
  Source\library.cmd                            launcher
  Source\assistant_library\__init__.py          package exports
  Source\assistant_library\__main__.py          py -m assistant_library entry
  Source\assistant_library\document.py          document model, text extraction
  Source\assistant_library\search.py            tokenizing, scoring, snippets
  Source\assistant_library\library.py           facade: index, get, search, reference
  Source\assistant_library\cli.py               operator interface
  Corpus\README_CORPUS.md                       what the sample corpus is and is not
  Corpus\Doctrine\MISSION_VISIBILITY.md         sample document
  Corpus\Doctrine\DRIVER_FIRST.md               sample document
  Corpus\Operations\RATE_FLOOR_POLICY.md        sample document
  Corpus\Operations\APPOINTMENT_WINDOWS.md      sample document
  Corpus\Operations\NOTES.txt                   sample document
  Tests\run_tests.cmd                           test launcher
  Tests\test_assistant_library.py               53 tests
  Tests\_last_test_run.txt                      raw output of the last run
```

## COMMANDS EXECUTED

```
py -m unittest discover -s Tests -v
D:\SANDBOX\Assistan_Building\ASST\3\Tests\run_tests.cmd
py -m assistant_library index
py -m assistant_library search "mission visibility"
py -m assistant_library doctor
```

## TEST RESULTS

**53 tests. 53 passed. 0 failed. 0 errors. 0 skipped.**

| Group | Tests |
| --- | --- |
| `TestCorpusIndexing` | 9 |
| `TestDocumentReading` | 10 |
| `TestSearch` | 18 |
| `TestRetrieveAndReference` | 7 |
| `TestBoundaries` | 9 |

Live operator run:

```
index    -> 6 documents indexed, 0 skipped unsupported, 0 unreadable
search   -> "mission visibility": 1 match, score 20,
            Doctrine/MISSION_VISIBILITY.md, matched: mission, visibility
doctor   -> access mode READ ONLY, write calls in package: none,
            network modules: none, 6 documents indexed
```

Detail in `TEST_REPORT_v1.md`.

## PROVEN CAPABILITIES

1. Indexes a configurable document root recursively.
2. Reads Markdown, Markdown-extension, and plain-text documents.
3. Reads `.docx` with no Word, Office, COM, or third-party library.
4. Derives titles from Markdown H1, falling back to the file name.
5. Derives stable document ids from paths, identical across runs.
6. Reports skipped-unsupported and skipped-unreadable counts, naming the
   unreadable files.
7. Reports a truncated index as truncated.
8. Skips noise directories such as `__pycache__` and `.git`.
9. Searches by title and body terms, case-insensitively.
10. Ranks by the stated formula: `5 x title matches + 1 x body matches`.
11. Produces stable ordering for the same query on every run.
12. Reports which query terms matched and which did not.
13. Drops partial matches when every term is required.
14. Returns nothing for a no-match query, without guessing.
15. Produces context snippets around matches.
16. Retrieves a document in full by id or by path.
17. Produces a citable reference naming title, path, and modification date.
18. Handles a corrupt `.docx` by reporting it rather than crashing.
19. Raises clearly on a missing root, a file used as a root, and unknown ids.
20. Changes nothing on disk, proven by filesystem observation.
21. Contains no write call anywhere in the package.
22. Imports nothing from any other workstream.

## IMPLEMENTED BUT NOT PROVEN

1. The CLI. Exercised by hand, not by the automated suite.
2. The `ASSISTANT_LIBRARY_ROOT` environment override.
3. Reading a real Company Library. Verified only against the sample corpus.
4. The 5000-document truncation limit.
5. The 5 MB document size limit.
6. Performance at scale. Largest test corpus is six documents.
7. Documents in encodings other than UTF-8.
8. `.docx` files with tables, footnotes, headers, tracked changes, or text
   boxes. Only simple paragraph text is tested.

## NOT IMPLEMENTED

1. Any write, edit, move, rename, or delete capability. Deliberately absent.
2. PDF support.
3. `.xlsx`, `.pptx`, `.doc`, `.rtf`, or HTML support.
4. Stemming, synonyms, fuzzy matching, or spelling correction.
5. Phrase search, boolean operators, or field-scoped queries.
6. A stored or incremental index.
7. Any retention, memory, or state between runs.
8. Any Outlook, email, calendar, or contact capability.
9. Any voice capability.
10. Any network or web capability.
11. Any approval, currency, or authority judgement about a document.
12. Access control, permissions, or redaction.
13. Any user interface. Command line only.

## KNOWN LIMITATIONS

1. Whole-word matching only. `policies` will not find `policy`.
2. The index is rebuilt every run. Fine at this size, unmeasured at scale.
3. The score formula favours short documents with the term in the title. Usually
   right for a policy library; can be wrong for a long document that discusses
   the term throughout.
4. Snippets show the first match per term, not the best match.
5. The sample corpus is sample material, not approved company content.
6. Documents over 5 MB and libraries over 5000 documents are cut off. Both are
   reported, neither is silent.
7. Verified on Windows 11, Python 3.14.5 only.
8. The component cannot judge whether a document is current or approved. That
   stays with Mike Zachary.

## REVIEW NOTES

**Reviewable alone.** Start at `README.md`. The component ships with its own
sample corpus, so a reviewer can run every command and every test without
locating, configuring, or being granted access to anything else.

**The read-only claim is proven by observation, not asserted.**
`test_indexing_the_corpus_changes_nothing_on_disk` snapshots every file
modification time in the corpus, runs a full index, search, and retrieval, then
asserts nothing changed. Two more tests scan the source for any write call and
check `ZipFile` is never opened for writing. Read-only here is structural: there
is no write code path to disable.

**No third-party dependency, including for Word.** `.docx` is read by treating
it as what it is - a zip archive holding `word/document.xml` - using `zipfile`
and `re`. That avoids `python-docx`, Office automation, and COM entirely, and it
is tested against both a valid and a deliberately corrupted file.

**The ranking is arithmetic, on purpose.** `5 x title + 1 x body`, ties broken by
document id. A reviewer can predict any result by reading the formula, and a
test asserts the code matches it. A relevance model would be more flexible and
much harder to review or to trust.

**No match means no match.** Search returns nothing rather than a near miss.
For a library of approved company material, a plausible wrong document is worse
than no document.

**Reading outside the folder is allowed; writing is not.** Rule 1 forbids
*writing* outside the assigned folder. The library root is deliberately
configurable so this can be pointed at the real Company Library - and it still
cannot alter it, because the component has no write capability at all.

**The sample corpus is labelled.** Every sample document carries a notice saying
it is sample material and not approved doctrine or policy, so it cannot drift
into being treated as company truth.

**Deliberately left out and declared, not half-built:** PDF support (needs a
dependency), stemming and fuzzy matching (make results unpredictable), and a
stored index (would require write capability).
