# Deployment Candidate

**Level 1 Assistant - Dispatch Plugin v1.0.0**

## What is here

```
Deployment\
  Assistant_Plugin_v1.0.0\      the deployment candidate - 90 files, 0.53 MB
  PACKAGE_ASSISTANT.cmd         rebuilds the candidate from the working copy
  DEPENDENCIES.txt              what must be installed (very little)
  VERSION.txt                   version, verification results, live status
  README.md                     this file
```

The candidate is a **clean copy** of the working program with runtime data,
logs, and the machine-specific configuration removed. It ships the
configuration **template**, not anyone's real paths.

## Install

1. Copy `Assistant_Plugin_v1.0.0` wherever you want it.
2. Copy `configuration\assistant.config.template.json` to
   `configuration\assistant.config.json`.
3. Edit the Company Library path, or leave that source disabled.
4. Double-click `START_ASSISTANT.cmd`.

Full instructions, uninstall, backup, reset, and security notes:
`docs\ASSISTANT_PLUGIN_DEPLOYMENT_GUIDE_v1.md` inside the candidate.

## Verified

The candidate was run from its own folder with only the shipped template, and
reported truthfully:

```
Operating mode: LIVE: Voice
  Library: SAMPLE DATA - 6 documents indexed
  Outlook: READY - installed and read-only; connects when you ask
  Research: SAMPLE DATA - provider: fixture
  Voice: LIVE - speech engine bound
  Dispatch: NOT CONNECTED
  Dispatch contacted: False    Operational writes: 0
```

Library correctly reports SAMPLE DATA with no Company Library configured. It
does not claim a live source it does not have.

## Not done, deliberately

- **Not installed into Dispatch.** Nothing was copied there.
- **No GitHub repository created.** Not authorized by this mission.
- **No pull request.** Not authorized.
- **Not installed into Windows.** No registry entry, service, or scheduled task.

## Uninstall

Delete the folder. That is all there is to it, and it is the point.
