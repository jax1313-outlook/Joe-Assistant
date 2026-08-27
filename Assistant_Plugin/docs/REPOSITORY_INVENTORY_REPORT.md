# Repository Inventory Report — Working Repository

**Mission:** JOE REPOSITORY PRESERVATION AND CERTIFICATION, Step 1
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

**No files were modified.**

---

## 1. The finding that changes this step

### `D:\Joe Assistant` exists and is EMPTY

| | |
| --- | --- |
| Path | `D:\Joe Assistant` |
| Folders | 1 (the root itself) |
| Files | **0** |
| Size | 0 bytes |

The folder has been created. **Nothing has been moved into it.**

### Joe's working code is still in the sandbox

The mission names `D:\Joe Assistant` as the working repository. Joe is not
there. Every file remains at:

```
D:\SANDBOX\Assistan_Building\
```

Inventorying the empty folder and stopping would have satisfied the letter of
Step 1 and reported nothing useful, so this document inventories **where Joe
actually is**, and says plainly that it is not where the mission expects.

---

## 2. Inventory of the actual working tree

`D:\SANDBOX\Assistan_Building`

| | |
| --- | --- |
| Folders | **144** |
| Files | **612** |
| Total size | **3,597,703 bytes (3.43 MB)** |

### A size discrepancy worth explaining

`du` reported **181 MB** for this tree. The true content is **3.43 MB**. The
gap is cluster-allocation overhead: 612 mostly-small files on an external drive
with large allocation units, plus regenerable `__pycache__` bytecode.

**3.43 MB is the figure that matters** — it is the number of bytes that must
survive for recovery to be possible, and it is what was verified.

---

## 3. Top-level structure

```
D:\SANDBOX\Assistan_Building\
    ASSISTANT_PLUGIN_CONSTITUTION_v1\   governing doctrine
    ASST\                               the six component workstreams (1..6)
    Architecture\
    Artifacts\
    Assistant_Plugin\                   ← the running program
    Build\
    Constitution\
    Context\
    Governing_Inputs\
    Sandbox\
    Testing\
```

### `Assistant_Plugin\` — the program itself

```
    adapters\        10 provider adapters
    app\             service, router, reasoning, driver voice, config, logbook
    configuration\   joe.config.json + template
    contracts\       response, provenance, source classes, reasoning modes
    docs\            67 documents
    governance\      the governance gate
    launchers\       26 launcher scripts
    library\         sample corpus
    logs\
    memory\          retention engine and store
    outlook\
    proof\           8 proof scripts + evidence
    research\
    runtime_data\    live interaction records
    tests\
    ui\              window and settings panel
    voice\
    Deployment\      the standalone deployment candidate
```

---

## 4. Significant assets

| Class | Count |
| --- | --- |
| Python source | **140** |
| Documentation (`.md`) | **67** |
| Launchers (`.cmd`) | **26** |
| Configuration (`.json`) | **202** |
| PowerShell scripts | 1 |
| Images (proof screenshots) | 6 |
| **Test suite** | 1 file, **329 tests** |
| **Proof artifacts** | **23** files in `proof\` |
| Runtime data | **190** files |
| Deployment candidate | **116** files |

### Configuration files

| File | Contains |
| --- | --- |
| `configuration/joe.config.json` | live machine config — tenant id, client id, mailbox registry, library paths |
| `configuration/joe.config.template.json` | ships disconnected: empty tenant/client id, no mailboxes |

Most of the 202 JSON files are **runtime interaction records**, not
configuration.

### Tests and proof

| | |
| --- | --- |
| Assembly tests | `tests/test_joe.py` — 329 tests |
| Component tests | `ASST\1..6` — 350 tests, untouched throughout |
| Proof scripts | 8 — `run_proof.py`, `prove_copilot`, `prove_research`, `prove_reasoning`, `prove_voice_input`, `prove_microphone`, `prove_email_layer`, `audit_controls` |
| Proof evidence | 23 files including live-run reports and 3 window screenshots |

---

## 5. Locked files, active processes, and artifacts

**Checked, not assumed.**

| Check | Result |
| --- | --- |
| Files that could not be opened for reading | **0** |
| JOE window running (`pythonw`) | **0** |
| Outlook running | 0 |
| Python processes | 1 (this session's own tooling) |
| `.claude` directories inside the tree | **0** |
| Claude Desktop artifacts | **0 found** |
| `__pycache__` directories | 28 — regenerable bytecode |
| `_workspace` directories | 6 — test scratch, recreated per run |

**No locked files. No blocked handles. A clean, complete copy was possible.**

---

## 6. What was not modified

Nothing. No file was created, renamed, deleted, or edited in the working tree
during this inventory.

---

Mike Zachary remains final authority.
