# Security findings

Found during Phase 2, in the order they matter. Each says what an attacker or an
accident actually gets, because "a race condition in a counter" and "the lockout
can be defeated by sending the guesses at once" are the same fact described at
two different levels of usefulness.

---

## S-1 · The PIN lockout was defeatable — **fixed**

**Severity: high.** **Status: fixed** (commit 5).

Both PIN registries kept `failed_attempt_count` in a JSON store, and every store
in `portal/models/` does read-modify-write on the whole file.
`portal/models/__init__.py` says so in its own words: *"Two processes doing
read-modify-write against the same store still lose one update; the last
os.replace wins."*

That trade was made deliberately, for durability, and was never re-examined when
a lockout counter moved into one of those files.

**Measured, with the original read-modify-write shape:**

```
OLD  12 concurrent failed attempts recorded as  1   -> lockout at 5 never trips
NEW  12 concurrent failed attempts recorded as 12   -> locked
```

The variable that defeats it is the one an attacker fully controls: how many
requests to send at once. Nothing in the registry, the audit log or any screen
would have shown it — the counter simply stayed low.

**Fix:** `dispatch/authcounters.py`. `INSERT ... ON CONFLICT DO UPDATE SET count
= count + 1` in one statement inside one transaction, with the lockout decided in
the same transaction rather than against a re-read count. Only the contended
field moved; PIN hashes, recovery words and every flow around them are untouched.

**Proof:** `tests/test_auth_lockout_concurrency.py` — twelve threads on a
barrier, through the registry function the login route actually calls.

## S-2 · `assert_within_plugin` accepted a Windows absolute path on POSIX — **fixed**

**Severity: medium.** **Status: fixed** (sandbox).

`Path("C:/Windows/Temp/x").is_absolute()` is **False** on POSIX, so such a path
resolved *under* the plugin root and the containment check passed it. The program
runs on Windows, so a config value or argument carrying one is a real escape — and
on Linux it was silently allowed, which is the condition under which a containment
test passes on a developer's machine and means nothing.

The repository's own test asserted this and had been failing.

**Fix:** `looks_absolute_anywhere()` rejects drive-letter and UNC paths on every
platform.

## S-3 · The transport is built on auth Microsoft is switching off — **mitigated**

**Severity: medium (availability, not confidentiality).** **Status: replacement built.**

`cin_lite/email_delivery.py` sends with `smtplib.login(user, password)` on port
587 — SMTP AUTH basic authentication, disabled by default on every Microsoft 365
tenant and being retired. The one path that reaches brokers.

Separately, `dispatch/connectors/outlook_connector.py` declares
`oauth_client_credentials`: **app-only** Graph, which needs an Entra tenant,
cannot authenticate a personal Microsoft account at all, and grants **tenant-wide
mailbox access** in order to read one operator's calendar.

**Fix:** delegated device code (`dispatch/msauth.py`) with least-privilege
scopes — `offline_access`, `Mail.Send`, `Calendars.Read`, `User.Read`, and
deliberately **not** `Mail.Read`. No client secret anywhere: there is no
`DISPATCH_MS_CLIENT_SECRET` setting in the repository. XOAUTH2 and Graph
transports are implemented behind the port; basic auth is kept for non-Microsoft
relays and now names the cause when a `535` comes back.

**Not proven:** no Microsoft call has been made.

## S-4 · Refresh-token protection is delegated, not assumed — **by design**

**Severity: informational.**

`dispatch/msauth.TokenCache` takes injected `protect`/`unprotect` functions. On
Windows the host supplies DPAPI, tying the file to the user account so a copied
cache is useless elsewhere. On platforms with no standard-library equivalent the
file is written unprotected under the OS's own permissions.

Written down rather than papered over: this module choosing to store a refresh
token in plain text because that is easy on Linux would be a decision it has no
business making on somebody's laptop.

## S-5 · Published development secrets — **pre-existing, correctly handled**

**Severity: informational.**

`portal/config.py` publishes `dev-portal-key-change-in-production` and
`dispatch-dev-secret`, and **refuses to start an operational deployment on
either** (`check_secrets()` raises `InsecureConfigurationError`). That is the
right shape: the value is known to everyone and cannot be used.

The secret scan excludes them **by name** rather than by pattern, so the
exclusion is auditable.

## S-6 · Five credential-shaped strings in `tests/` — **reviewed, all fixtures**

**Severity: none.** The scan reports them rather than excluding the directory.

| Match | File | What it is |
|---|---|---|
| `password = "relay-password-abcdef"` | `tests/test_connectors.py:371` | A test asserting the password is **redacted** from an SMTP error. |
| `AKIAQ7HXH2PL4TZ0RVKM` | `tests/test_sandbox_survey.py:54` | `FAKE_AWS_KEY`, proving the survey's detector fires. |
| `-----BEGIN RSA PRIVATE KEY-----` | `tests/test_sandbox_survey.py:899` | The header alone. No key material. |
| `token="not-the-real-token"` | two stakeholder tests | Asserting a bad token gets **403**. |

`tests/` is not excluded wholesale — a real credential hidden there would still
be printed. Findings outside `tests/` fail the scan.

## S-7 · The audit records shape, never values — **by design**

`Workers/worker_bus/audit.py` records `{driver_phone, load_id}`, never
`555-0100`. An audit that copies the payload is a second place the payload has to
be protected, and it is usually the place nobody remembers to protect.

## S-8 · Reasoning context is narrowed before it leaves — **by design**

`MissionRecord.context_for_reasoning()` sends six named fields. A provider handed
the whole record answers from anything in it, and one of the fields is a driver's
phone number. Asserted by `tests/test_conversation.py`.

## S-9 · No worker can approve anything — **by design, enforced**

The response contract **raises** on `approved_by`, `approved`, `decision` or
`authorized_by` in a worker's artifacts. The bus refuses an authorisation from
any reserved system identity, and refuses a named human authoriser with no
reference to a recorded decision — because an assertion that somebody approved is
not a record that they did.

## S-10 · Speech cannot become a write — **by design**

Joe produces a proposal and the words that would confirm it. There is no field
by which a proposal applies itself, and below a confidence floor he says nothing.
`CLAUDE.md` §5.4: no direct Dispatch write authority may be granted to Assistant.

---

## Not fixed, and why

**Eleven JSON stores still lose a concurrent update.** Conflict notices, the
publisher queue, library records, the sandbox, the archive index. A lost update
there costs a record, not a lockout. Fixing it properly means moving those stores
into SQLite, which is a larger change than these findings support. Stated in
`KNOWN_LIMITATIONS.md` §5.

**No rate limiting on the login route itself.** The lockout is per-identity and
now works. There is no per-IP throttle, and on a single-operator application
bound to `127.0.0.1` by default there is no meaningful attacker population for
one. It would matter the day the portal is exposed to a network.
