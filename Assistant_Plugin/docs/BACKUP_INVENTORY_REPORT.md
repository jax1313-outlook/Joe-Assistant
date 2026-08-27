# Backup Inventory Report

**Mission:** JOE REPOSITORY PRESERVATION AND CERTIFICATION, Step 2
**Produced:** 2026-08-26
**Final authority:** Mike Zachary

---

## 1. State BEFORE this mission

```
C:\Users\jax13\OneDrive - Level 1 Transport Inc (1)\Copilot WorkSpace\Joe Assistant
```

| | |
| --- | --- |
| Folders | 1 (the root itself) |
| Files | **0** |
| Size | 0 bytes |

**The backup repository was empty.**

Both named repositories — working and backup — contained nothing. Joe existed
in exactly one place, `D:\SANDBOX\Assistan_Building`, on one external drive,
with **no backup and no version history**.

That is the exposure this mission exists to close, and it was real.

---

## 2. State AFTER this mission

| | |
| --- | --- |
| Folders | **144** |
| Files | **612** |
| Total size | **3,597,703 bytes (3.43 MB)** |

The copy operation is documented in `BACKUP_ACTION_REPORT.md`.

---

## 3. Top-level structure of the backup

Mirrors the source exactly:

```
Copilot WorkSpace\Joe Assistant\
    ASSISTANT_PLUGIN_CONSTITUTION_v1\
    ASST\                               the six component workstreams
    Architecture\
    Artifacts\
    Assistant_Plugin\                   the program
    Build\
    Constitution\
    Context\
    Governing_Inputs\
    Sandbox\
    Testing\
```

---

## 4. Significant assets present in the backup

| Class | Source | Backup | Match |
| --- | --- | --- | --- |
| Python source | 140 | 140 | yes |
| Documentation | 67 | 67 | yes |
| Launchers | 26 | 26 | yes |
| Configuration | 202 | 202 | yes |
| Test suite | 329 tests | 329 tests | yes |
| Proof artifacts | 23 | 23 | yes |
| Runtime data | 190 | 190 | yes |
| Deployment candidate | 116 | 116 | yes |
| Component workstreams `ASST\1..6` | present | present | yes |

### Configuration in the backup — a security note

The backup contains `configuration/joe.config.json`, which holds Mike's
**tenant id and client id**. Neither is a secret — a public-client id is safe to
store, and this has been the documented position throughout.

**What the backup does NOT contain:**

| | |
| --- | --- |
| Token cache | **absent** — `runtime_data/auth/` was not present in the source at copy time |
| Passwords, access tokens, refresh tokens | **none anywhere** |
| Client secret | **none** — a public desktop client never uses one |

The backup does contain **runtime interaction records**, which include mail
subjects read from Mike's own mailboxes. This is Mike's own business data
inside Mike's own Microsoft 365 tenant, which is where the mission directs the
backup to live. **Flagged so it is a known fact rather than a discovery.**

---

## 5. Exclusions

Two categories were deliberately excluded. Both are documented here because
certification requires exclusions to be stated.

| Excluded | Count | Why | Recovery impact |
| --- | --- | --- | --- |
| `__pycache__` | 28 directories | Python bytecode, regenerated automatically on first run | **none** |
| `*_workspace` | 6 directories | test scratch directories, recreated by every test run | **none** |

**Neither affects recovery.** Restoring the backup and running the test suite
regenerates both.

---

## 6. Sync status

The backup lives in OneDrive and will sync to Mike's Microsoft 365 tenant. At
the time of writing the files exist on local disk at the path above; **cloud
sync completion was not verified and is not claimed.**

That is worth knowing: until OneDrive finishes uploading, the backup protects
against loss of the external drive but not against loss of the laptop.

---

Mike Zachary remains final authority.
