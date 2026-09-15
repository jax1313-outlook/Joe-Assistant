# External activation — what only Mike can do

Everything in this list is blocked on something outside the repositories: an
account, a credential, a decision, or a laptop. None of it can be completed by
any amount of further work in here, and none of it is claimed as done.

---

## A · Microsoft 365 — one registration, then one sign-in

**Who:** Mike. **Time:** ~15 minutes, once.

1. <https://portal.azure.com> → Entra ID → App registrations → New registration.
2. Supported account types: **Accounts in any organizational directory and
   personal Microsoft accounts** — the last part is what makes an `outlook.com`
   account work.
3. Authentication → **Allow public client flows: Yes**.
4. Delegated permissions: `offline_access`, `Mail.Send`, `Calendars.Read`,
   `Files.ReadWrite`, `User.Read`.
5. **Do not create a client secret.** Nothing uses one and there is no setting
   for it.
6. On the laptop: `setx DISPATCH_MS_CLIENT_ID <application id>`, then
   `python -m dispatch_launcher connect-microsoft`.

**Verify:** `python -m dispatch_launcher transports` shows `LIVE -- Microsoft
Graph as <address>`. Then send one message and look in **Sent Items** — the
sign-in proves the token exchange, not delivery.

> If the mailbox is Microsoft 365 and the current SMTP settings are in use, they
> are working on borrowed time: SMTP AUTH basic authentication is disabled by
> default on every tenant and is being retired. `smtp_oauth2` is the
> smallest-change replacement; `graph` is the better one.

## B · A backup location, and a scheduled backup

**Who:** Mike. **Time:** 5 minutes.

```
setx /M DISPATCH_BACKUP_DIR "D:\Backups\Dispatch"
python -m dispatch_launcher schedule-backup      # prints the schtasks line
```

The schedule command **prints** the command rather than running it: registering a
scheduled task writes to the machine outside Dispatch's own folders, and the
program does not do that unasked. Run the line it prints, as Administrator.

## C · Prove a restore, as a person

**Who:** Mike. **Blocked on:** B.

```
python -m dispatch_launcher backup
python -m dispatch_launcher prove-restore
```

That second command restores into an isolated scratch directory and records
`performed_by: Code-automated`. **The status stays `UNVERIFIED`**, and that is
correct: the program proved the archive restores and every hash matches. It
cannot prove the restored Dispatch *works*.

Open the restored copy. If it works:

```
python -m dispatch_launcher prove-restore --confirmed-by "Mike"
```

Only that reaches `VERIFIED`.

## D · The operating timezone

**Who:** Mike. **Default:** `America/New_York`.

```
setx DISPATCH_OPERATING_TIMEZONE "America/New_York"
```

Every appointment typed without an offset is recorded in this zone. If it is
wrong, every appointment is wrong by the difference — which is why it is a
setting and not an assumption.

## E · Capacity profiles, one per truck

**Who:** Mike. **Time:** 2 minutes per truck.

Until a truck has one, its loads report `UNCONFIGURED` on the capacity panel.
That is deliberate — assuming a 53-foot dry van is how freight is accepted onto a
trailer that cannot carry it.

`source` is required (a spec sheet, a door sticker, a scale ticket) and
`verified_by` is not defaulted: a specification nobody signed for is
`CONFIGURED`, not `VERIFIED`.

## F · Place two governance pointers

**Who:** anyone with write access to `Claude` and `Publisher`.

Copy `Governance/pointers/Claude-GOVERNANCE.md` → `Claude/GOVERNANCE.md` and
`Governance/pointers/Publisher-GOVERNANCE.md` → `Publisher/GOVERNANCE.md`.

Nothing else in those repositories changes. The superseded constitutions stay
exactly where they are — the pointer is what stops them being read as current.

**Verify:** `python -m dispatch_governance check <workspace>` returns 0.

## G · Rule on `DISPATCH_CONSTITUTION_v3`

**Who:** Mike, and only Mike.

Its header says both "Current Controlled Constitution" and "v3 Replacement
Draft". No repository holds an approval record. It is registered `ADVISORY`,
which is true either way and on which no code decision rests.

If it was ratified, say so and the registry is updated. Inferring it is the
manufactured approval `CLAUDE.md` §4 forbids outright.

## H · Speech, if voice is wanted beyond text

**Who:** Mike. **Optional.**

Either an Azure Speech resource (`JOE_AZURE_SPEECH_KEY`, `JOE_AZURE_SPEECH_REGION`
— and the adapters are **not written**, only the status reporting), or a local
Whisper model (`JOE_WHISPER_MODEL`).

Without either, Joe runs on the text engines and reports `SIMULATED`: nothing was
heard and nothing was said aloud.

## I · Walk the twenty-step operational proof

**Who:** Mike. **Blocked on:** the series being merged, and B.

This is the gate. Steps 18, 19 and 20 now run — before this work all three were
rejected by their own parsers. Nothing in Dispatch is `OPERATIONALLY PROVEN`
until this is walked on his laptop and the report is written.
