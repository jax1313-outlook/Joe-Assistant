# Deployment Candidate

**JOE, the Level 1 Assistant — v1.1.0**

## What is here

```
Deployment\
  JOE_Assistant_v1.1.0\    the deployment candidate - 149 files, 1.4 MB
  PACKAGE_JOE.cmd          rebuilds the candidate from the working copy
  verify_package.ps1       checks a candidate before it can be deployed
  DEPENDENCIES.txt         what must be installed (very little)
  VERSION.txt              version, what changed, verification results
  README.md                this file
```

The candidate is a **clean copy** of the working program with runtime data,
logs, the token cache, and the machine-specific configuration removed. It ships
the configuration **template**, not anyone's real paths.

## Install

1. Copy `JOE_Assistant_v1.1.0` wherever you want it.
2. Copy `configuration\joe.config.template.json` to
   `configuration\joe.config.json`.
3. Edit the Company Library path, or leave that source disabled.
4. Double-click `START_JOE.cmd`.

Full instructions, uninstall, backup, reset, and security notes:
`docs\JOE_DEPLOYMENT_GUIDE_v1.md` inside the candidate.

## Rebuild

Double-click `PACKAGE_JOE.cmd`. It clears the previous candidate, copies the
working program, and then **verifies the result before letting you deploy it**.
A build that fails verification is rejected rather than left in this folder
looking finished.

The eight checks compare the candidate against the source it was built from,
file by file, rather than against a written-down list — because a written list
is what went stale last time. They also refuse a candidate carrying machine
configuration, runtime state, logs, or a token cache.

## Why 1.1.0 and not 1.0.0

The 1.0.0 candidate was built **before the program was renamed to JOE**. It
shipped `assistant_main.py` and `START_ASSISTANT.cmd`, and it kept that name
while the source moved on without it. Deploying from it gave you a build where
mail, calendar and contacts all refused — and its own bundled proof suite
reported 24 of 24 while doing so.

The packaging script excluded `assistant.config.json`. After the rename the real
file was `joe.config.json`, so the exclusion matched nothing and the machine's
own configuration would have shipped. A stale name in an exclusion list does not
error; it quietly stops protecting anything.

That is why the script now verifies, and why the package carries the program's
actual name.

## Verified

Not by reading it. The built candidate was copied to a fresh location on
another drive, given a configuration the way an operator would, and run:

```
24 proofs passed, 0 skipped, 0 failed
329 automated tests pass
Reasoning: SIGNED OUT   (correct - a fresh deployment has no token cache,
                         and it says so rather than inheriting one)
```

## Not done, deliberately

- **Not installed into Dispatch.** Nothing was copied there.
- **Not installed into Windows.** No registry entry, service, or scheduled task.
- **Cannot send.** Amendment 1 is drafted and not in force. Article II has
  eight permitted functions, and transmission is not one of them.

## Uninstall

Delete the folder. That is all there is to it, and it is the point.
