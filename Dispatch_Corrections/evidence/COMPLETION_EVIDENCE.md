# Completion evidence

Collected 2026-09-12T21:15:55Z by `Dispatch_Corrections/collect_evidence.py`.

Every command below was run. Output is verbatim and truncated only at the
tail. A step that could not be performed says so rather than being omitted.

| # | Step | Outcome |
|---|---|---|
| 5 | Monetary calculation and migration | **PASSED** |
| 3 | Execute proof step 18 against a real load | **PASSED** |
| 3 | Proof step 18 fails when the evidence bytes change | **PASSED** |
| 6 | Create a backup | **PASSED** |
| 6 | Verify every hash in the archive | **PASSED** |
| 7 | Restore into an isolated destination | **PASSED** |
| 7 | Backup status after a machine-performed restore | **PASSED** |
| 8 | Injected failures across atomic operations | **PASSED** |
| 9 | Concurrent PIN attempts and SQLite contention | **PASSED** |
| 10 | Notification failure visibility and retry | **PASSED** |
| 13 | Microsoft stays behind provider-neutral adapters | **PASSED** |
| 14 | Remove generated caches and runtime debris | **PASSED** |
| 15 | Scan for secrets and credentials | **PASSED** |
| 16 | Merge plan against the actual diff | **PASSED** |

## 5. Monetary calculation and migration

```
$ /tmp/claude-0/venv/bin/python -m pytest -o addopts= -q tests/test_money.py
61 passed in 3.47s
(exit 0)
```

Exactness, ROUND_HALF_UP, the generated cents columns, and the two reports that used to disagree by pennies.

## 3. Execute proof step 18 against a real load

```
$ python scripts/dispatch_proof.py verify --load-id LOAD-20260912-FC5D0CB2
[snapshot (before the restart)] exit 0
snapshot written: proof/load/proof_snapshot_LOAD-20260912-FC5D0CB2.json
  drivers        0
  equipment      0
  evidence       1
  exceptions     0
  loads          1
  milestones     0
  pod_packages   0

[step 18 · verify] exit 0
    exceptions     0  —
    loads          1  LOAD-20260912-FC5D0CB2
    milestones     0  —
    pod_packages   0  —
  Compared against snapshot taken 2026-09-12T21:15:47Z
    drivers        ok
    equipment      ok
    evidence       ok
    exceptions     ok
    loads          ok
    milestones     ok
    pod_packages   ok
    evidence EV-20260912-9AE51407  ok
  RESULT: PASSED
(exit 0)
```

Before this work: `invalid choice: 'verify'`.

## 3. Proof step 18 fails when the evidence bytes change

```
$ verify (after tampering)
  Compared against snapshot taken 2026-09-12T21:15:47Z
    drivers        ok
    equipment      ok
    evidence       ok
    exceptions     ok
    loads          ok
    milestones     ok
    pod_packages   ok
    evidence EV-20260912-9AE51407  DRIFT
  RESULT: FAILED
(exit 1)
```

Exit 1 is the correct result. The evidence row is untouched and only a recomputed hash says otherwise.

## 6. Create a backup

```
$ python -m dispatch_launcher backup
  Backup written to /tmp/dispatch-evidence-2l3beu1c/Backups/dispatch-backup-20260912T211547Z
      2 files, 606,232 bytes
      This backup has not been restored, so it is not yet known to be usable.
      Prove it with:  python -m dispatch_launcher prove-restore
(exit 0)
```

Nothing in the product could take one before this work.

## 6. Verify every hash in the archive

```
$ python scripts/dispatch_backup.py verify dispatch-backup-20260912T211547Z
/tmp/dispatch-evidence-2l3beu1c/Backups/dispatch-backup-20260912T211547Z: 2 files verified, all hashes match
(exit 0)
```

## 7. Restore into an isolated destination

```
$ python -m dispatch_launcher prove-restore
  Restore proven in an isolated destination.
      restored 2 files to /tmp/dispatch-restore-proof-y7vzj8j2
      verification record: /tmp/dispatch-evidence-2l3beu1c/Backups/dispatch-backup-20260912T211547Z.restore-verification.json
      repointed 1 stored file paths
      Recorded as Code-automated. The archive restores and every hash matches;
      that the restored Dispatch actually works is still for a person to confirm.
(exit 0)
```

Recorded as Code-automated, so the status stays UNVERIFIED. A person confirming the restored copy works is what reaches VERIFIED.

## 7. Backup status after a machine-performed restore

```
$ backup_status()
UNVERIFIED
This backup was restored into an isolated destination by the program on 2026-09-12T21:15:48Z and every hash matched. Nobody has opened the restored Dispatch and confirmed it works, so it is not VERIFIED. Do that and record it with:  python -m dispatch_launcher prove-restore --confirmed-by "Mike"
(exit 0)
```

UNVERIFIED is the correct answer and the point of the step.

## 8. Injected failures across atomic operations

```
$ /tmp/claude-0/venv/bin/python -m pytest -o addopts= -q tests/test_atomic_service_operations.py
14 passed in 0.84s
(exit 0)
```

Each test breaks a store call after the first successful write and asserts the first write is gone too.

## 9. Concurrent PIN attempts and SQLite contention

```
$ /tmp/claude-0/venv/bin/python -m pytest -o addopts= -q tests/test_auth_lockout_concurrency.py
14 passed in 3.18s
(exit 0)
```

12 concurrent failures were recorded as 1 before; the lockout never tripped.

## 10. Notification failure visibility and retry

```
$ /tmp/claude-0/venv/bin/python -m pytest -o addopts= -q tests/test_delivery_visibility.py
21 passed in 1.46s
(exit 0)
```

## 13. Microsoft stays behind provider-neutral adapters

```
$ /tmp/claude-0/venv/bin/python -m pytest -o addopts= -q tests/test_transport.py tests/test_msauth.py
48 passed in 0.16s
(exit 0)
```

No Microsoft call has been made from this repository.

## 14. Remove generated caches and runtime debris

```
$ find ... -name __pycache__ -exec rm -rf
(working tree clean of untracked debris)
(exit 0)
```

## 15. Scan for secrets and credentials

```
$ python _evidence_secrets.py
scanned 489 tracked text files against 8 patterns:
  - private key block
  - aws access key id
  - slack token
  - github token
  - azure/entra secret
  - bearer literal
  - assigned credential
  - connection string
4 known published development default(s) excluded by name; portal/config.py
refuses to start an operational deployment on any of them.
5 match(es) inside tests/ -- listed, not excused:
  FIXTURE  assigned credential  tests/test_connectors.py:371  password = "relay-password-abcdef"
  FIXTURE  private key block    tests/test_sandbox_survey.py:899  -----BEGIN RSA PRIVATE KEY-----
  FIXTURE  aws access key id    tests/test_sandbox_survey.py:54  AKIAQ7HXH2PL4TZ0RVKM
  FIXTURE  assigned credential  tests/test_stakeholder_evidence_download.py:104  token="not-the-real-token"
  FIXTURE  assigned credential  tests/test_stakeholder_portal.py:65  token="not-the-real-token"
No credential matches outside tests/.
(exit 0)
```

## 16. Merge plan against the actual diff

```
$ git log --oneline 3c03ab2..HEAD; git diff --stat
fdeac1d Measure branch coverage, and measure the launcher
3b1ea1b Wire the capacity engine into production, and make appointment times readable
0764bc4 Record every outbound attempt, log it, and give the log a size
869605b Put a provider-neutral transport behind the mail path, with Microsoft-compatible auth
39bed43 Give the operator a way to take a backup, and to prove one
593de61 Money becomes whole cents, exactly, everywhere it is added up
470af3d Move the PIN lockout counters where a transaction protects them
59c1534 Make multi-step service operations atomic, and defer sends past the commit
5e5f34d Replace the dashboard's per-load queries with two rollups
42902ba Build the schema once per process, wait for a write lock, and allow a unit of work
07bfdb1 Repair the operational proof path and make it executable

 tests/test_proof_command_contract.py          | 158 ++++++++++
 tests/test_proof_persistence_verify.py        | 198 ++++++++++++
 tests/test_rate_confirmation_print.py         |   8 +-
 tests/test_timestamps.py                      | 175 +++++++++++
 tests/test_transport.py                       | 289 +++++++++++++++++
 65 files changed, 7858 insertions(+), 208 deletions(-)
(exit 0)
```
