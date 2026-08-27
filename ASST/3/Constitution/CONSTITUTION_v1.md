# Workstream 3 - Assistant Library - Constitution

**Component:** Assistant Library
**Version:** 1.0.0
**Final authority:** Mike Zachary

Binding rules for everything in `ASST\3`.

---

## 1. Authority

Mike Zachary remains final authority. This component finds and returns
documents. It approves nothing, decides nothing, and confers no authority on
anything it retrieves.

**Retrieving a document does not make its contents true, current, or approved
for the use at hand.** The component reports what a document says and where it
came from. The judgement stays with Mike.

## 2. Read only - structurally, not by policy

This is the central rule of the workstream.

1. No call in this package opens a file for writing.
2. No call creates, deletes, renames, moves, or replaces anything.
3. `zipfile.ZipFile` is only ever opened for reading.
4. The `Library` object exposes no `save`, `write`, `delete`, `remove`,
   `update`, `create`, `edit`, `rename`, `move`, `upload`, or `sync` method.

Enforced by three tests:

- `test_no_write_call_exists_anywhere_in_the_package` scans every source file
  for `write_text`, `write_bytes`, `.write(`, `.writestr(`, `mkdir`, `unlink`,
  `rmdir`, `.rename(`, `os.replace`, `shutil.`, `os.remove`, `os.makedirs`, and
  `open(..., "w"/"a"/"x")`.
- `test_zipfile_is_opened_read_only` checks every `ZipFile(...)` call.
- `test_indexing_the_corpus_changes_nothing_on_disk` records every file
  modification time in the corpus, runs an index, a search, and a retrieval,
  then asserts nothing changed.

The last one is the important one: it proves the read-only claim by observing
the filesystem, not by reading the code.

## 3. Isolation - absolute

1. This folder writes no file outside `ASST\3`. In fact it writes no file at
   all - see section 2.
2. This folder imports nothing from workstreams 1, 2, 4, 5, or 6.
3. This folder assumes no other workstream exists.
4. There is no integration code here, and none may be added.

Enforced by `test_imports_nothing_from_another_workstream` and
`test_uses_only_the_standard_library`, which fail on any import outside
`__future__`, `argparse`, `dataclasses`, `datetime`, `html`, `json`, `os`,
`pathlib`, `re`, `sys`, `zipfile`.

**Reading outside the folder is permitted and is the point.** The library root
is configurable so the component can be pointed at a real library. Writing
outside the folder is not permitted, and is impossible here because the
component does not write anywhere.

## 4. Hard prohibitions

There is no code path in this component that could do any of the following, and
tests assert the absence of every import that would be required:

1. Modify, create, or delete any document.
2. Reach the network. No networking module is imported at all.
3. Send or read email.
4. Read a calendar or contact list.
5. Record or play audio.
6. Retain, expire, or remember anything between runs. The index is rebuilt on
   each run and held in memory.
7. Approve a document, mark it current, or declare it doctrine.
8. Commit money, accept a load, or decide anything operational.

`test_no_memory_outlook_or_voice_capability` fails if the package ever defines a
function or class whose name suggests mail, calendar, contact, voice, or
retention capability.

## 5. Honesty rules

- **No match means no match.** An unmatched query returns nothing and says
  "No document matched. Nothing was inferred or invented." The component never
  substitutes a near miss for an answer.
- **Skips are reported, never hidden.** Every index pass reports how many files
  were skipped as unsupported, how many were unreadable, and names the
  unreadable ones. A truncated index says it was truncated.
- **Every hit carries its source.** Search results include the document id, the
  relative path, which terms matched, which terms did **not** match, and a
  citable reference.
- **The ranking is stated, not hidden.** The score formula is written in the
  code, the architecture, and the context, and a test asserts the code matches
  the stated formula.
- **The sample corpus says it is a sample.** Every corpus document carries a
  notice that it is sample material and not approved company doctrine.

## 6. What must not happen without a new decision

- Do not add any write capability, for any reason, including "fixing" a
  document or caching an index to disk.
- Do not connect this component to retention, email, research, or voice. That is
  integration, forbidden by the build matrix.
- Do not make search return a best guess when nothing matched.
- Do not let the ranking formula become unstateable.
- Do not let the sample corpus be mistaken for the real Company Library, and do
  not remove the sample notices from those documents.
