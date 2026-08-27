# JOE - Deployment Guide

**Program:** JOE, the Level 1 Assistant
**Version:** 1.0.0
**Deployment candidate:** `Assistant_Plugin\Deployment\`

**This is a local deployment candidate. Nothing is installed into Dispatch.
No repository was created. No pull request was made.**

---

## 1. What this is

A folder you copy. There is no installer, no service, no registry entry, no
scheduled task, and no package to download.

## 2. Requirements

See `Deployment\DEPENDENCIES.txt`. In short:

- Python 3.10 or newer with the `py` launcher (verified: 3.14.5)
- Windows 10 or 11 (verified: Windows 11 Pro 26200)
- **No third-party Python package.** Standard library only.

Optional, for live capabilities: desktop Outlook with a profile, Windows
System.Speech, a microphone. Each is optional; JOE runs and reports
honestly without any of them.

## 3. Install

1. Copy the whole `Assistant_Plugin` folder wherever you want it.
2. Copy `configuration\joe.config.template.json` to
   `configuration\joe.config.json`.
3. Open it and set your Library path:

```json
"sources": [
  {
    "name": "Company Library",
    "path": "C:\\path\\to\\your\\Company Library",
    "kind": "company",
    "enabled": true
  }
]
```

   Set `"enabled": false` on that source if you do not want a Library
   connected yet.

4. Double-click `START_JOE.cmd`.

That is the whole installation.

**Optional:** right-click `START_JOE.cmd` → Send to → Desktop (create
shortcut), so it is one click from the desktop.

## 4. Verify

```
launchers\JOE_STATUS.cmd     what is connected
launchers\RUN_TESTS.cmd            259 automated tests
launchers\RUN_PROOF.cmd            24 operational proof steps
```

`RUN_PROOF.cmd` regenerates `docs\JOE_LOCAL_PROOF_REPORT_v1.md`
from what actually happened on that machine. It briefly opens JOE
window and briefly starts Outlook. Use `RUN_PROOF.cmd --no-outlook` to skip
the Outlook step, or `--speak` to also make it speak aloud.

## 5. Uninstall

**Delete the `Assistant_Plugin` folder.**

That is all. There is nothing else to remove:

- nothing was installed into Windows
- no registry key was created
- no service or scheduled task was registered
- nothing was written outside the folder
- **nothing was installed into Dispatch**

**Dispatch is unaffected by removal.** It never knew JOE existed.
This is the removability requirement, and deleting the folder is the proof.

## 6. Your data

```
Assistant_Plugin\runtime_data\memory\active\     kept records
Assistant_Plugin\runtime_data\memory\expired\    tombstones, content purged
Assistant_Plugin\runtime_data\memory\deleted\    tombstones, content purged
```

Plain JSON, one file per record. `launchers\OPEN_DATA.cmd` opens the folder.

Nothing operational lives here. These are Assistant interaction records, not
Dispatch records. Losing them loses convenience, not operational truth.

## 7. Logs

```
Assistant_Plugin\logs\joe.log        event log
Assistant_Plugin\logs\last_test_run.txt    last test output
```

`launchers\OPEN_LOGS.cmd` opens the folder.

The log records event kinds, capability names, and record IDs. **It does not
record the body of a document, an email, or a calendar entry.**

## 8. Backup

Copy these two folders:

```
Assistant_Plugin\runtime_data\
Assistant_Plugin\configuration\
```

That is your records and your settings. Everything else is program files you
can re-copy.

To restore: put them back and start JOE.

## 9. Reset

**Clear records, keep settings:** delete everything inside
`runtime_data\memory\active`, `\expired`, and `\deleted`.

**Clear logs:** delete `logs\joe.log`.

**Full reset:** delete `runtime_data\` and `logs\`, then start JOE.
It recreates both.

**Back to defaults:** copy `configuration\joe.config.template.json` over
`configuration\joe.config.json` and re-enter your Library path.

## 10. Security notes

**What this program can reach**

- Files under the Library paths **you configure**. Read-only. Nothing is
  scanned automatically and nothing outside those paths is opened.
- Your Outlook calendar, mail, and contacts, **read-only**, and only when you
  ask. It does not connect on startup.
- The Windows speech engines, when you press Speak or Listen.

**What it cannot reach**

- The network. No networking module is imported at all.
- Dispatch. No interface is configured and no write method exists.
- Anything outside its own folder, for writing. Every write path is checked and
  refused if it falls outside.

**Credentials:** none are used, stored, or required. The Outlook connection
uses the Windows session you are already signed into. There is no API key, no
token, and no password anywhere in this program or its configuration.

**Outlook is read-only structurally.** The adapter generates PowerShell from a
fixed template and scans it for twenty non-read calls (`Send`, `Save`, `Delete`,
`Move`, `Reply`, `Forward`, `CreateItem`, `Accept`, `Decline`, and others). If
one ever appeared it refuses to run.

**Your data stays local.** Nothing is uploaded, synchronized, or transmitted.

**File permissions:** records are plain readable JSON with no access control
beyond Windows file permissions. Anyone who can read the folder can read them.
Do not put the folder somewhere shared.

## 11. Provider connection status

| Provider | State on the build machine | Blocker |
| --- | --- | --- |
| Library (filesystem) | **LIVE** - Company Library, 28 docs + 6 sample | none |
| Outlook (Windows COM) | **LIVE** - read-only, Outlook 16.0 | none |
| Voice output (System.Speech) | **LIVE** - 2 voices, speaks aloud | none |
| Voice input (recognition) | engine binds, recognition unproven | needs a person at the microphone |
| Research | **SAMPLE DATA** | no approved provider or credential |
| Dispatch | **NOT CONNECTED** | no published interface exists |
| Printing | **NOT IMPLEMENTED** | no printing service bound |
| Reasoning provider | **NOT CONNECTED** | none approved or configured |

## 12. Plugin boundary

Restated so it is in the deployment package too:

- Dispatch is the General Contractor, System of Record, and Operational
  Authority.
- JOE is a specialized staff plugin.
- JOE may recommend. It may not approve, decide, own Dispatch
  records, or alter operational truth.
- JOE never writes to Dispatch. It submits proposals that nothing
  drains.
- Silence is never consent.
- **Mike Zachary remains final authority.**

Full contract: `docs\JOE_INTERFACE_CONTRACT_v1.md`.

## 13. Dispatch independence

Proven, not asserted:

- JOE was built, tested, and proven with Dispatch entirely absent.
- `dispatch_contacted` is a literal `False`; `operational_writes` is `0`.
- No Dispatch path, endpoint, credential, or handle exists anywhere in the
  program.
- No Assistant file was copied into Dispatch.
- Removing JOE is a folder deletion.

See local proof steps 14, 16, and 18.

## 14. Version

```
Program            JOE, the Level 1 Assistant
Version            1.0.0
Built              2026-08-25
Runtime            Python 3.14.5, tkinter 8.6
Governing doctrine JOE_CONSTITUTION_v1 (v1.0)
Components         Assistant UI, Memory, Library, Outlook, Research, Voice
                   packaged unchanged from ASST\1..6
Automated tests   259 assembly + 350 component = 609
Local proof        18 of 18 steps
```
