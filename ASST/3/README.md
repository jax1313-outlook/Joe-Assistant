# ASST\3 - Assistant Library

**Read-only** access to a document library: search, retrieve, reference.
No writing, no memory, no email, no voice, no network.

## Use it

```bash
Source\library.cmd search "mission visibility"
```

```bash
Source\library.cmd index
```

Reads the sample corpus in this folder by default. Point it elsewhere with
`--root` or `ASSISTANT_LIBRARY_ROOT`.

## Test it

```bash
Tests\run_tests.cmd
```

53 tests.

## Read it in this order

1. `Context\CONTEXT_v1.md` - what this is and why read only
2. `Constitution\CONSTITUTION_v1.md` - the rules it is built under
3. `Architecture\ARCHITECTURE_v1.md` - modules, indexing, the score formula
4. `Operator_Guide\OPERATOR_GUIDE_v1.md` - how to use it
5. `TEST_REPORT_v1.md` - what is proven, and what is not
6. `BUILD_REPORT_v1.md` - the build summary

## The three things to know

**It cannot change anything.** Read-only is structural, not policy. There is no
write code path to disable, and a test proves it by checking that a full index,
search, and retrieval leaves every file on disk untouched.

**No match means no match.** Search returns nothing rather than a near miss.

**Finding a document does not make it true.** The component reports what a
document says and where it came from. Whether it is current or approved is
Mike's call.

## The sample corpus

`Corpus\` holds six short documents written for this workstream so it runs and
tests with no setup. Each says it is **sample material, not approved company
doctrine**. It is not a copy of the real Company Library.

## Isolation

This folder imports nothing from workstreams 1, 2, and 4-6, and writes nothing
anywhere - inside `ASST\3` or out.
