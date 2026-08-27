# Copilot Activation — the steps only Mike can take

**Purpose:** to unblock the Microsoft 365 Copilot live proof.
**Provider:** MICROSOFT 365 COPILOT — **PILOT / PREVIEW**. Microsoft states the
Copilot Chat API is a `/beta` endpoint and is not supported for production use.

JOE does not create the app registration, does not grant consent, and
does not sign in on your behalf. Everything below is yours to do. Nothing here
was assumed about your administrative role.

---

## Before you start — one thing that will stop you cold

**`jax1313@outlook.com` cannot be used.** The Copilot Chat API does not support
personal Microsoft accounts. You need a **work or school account** on the
`l1truck.com` tenant **with a Microsoft 365 Copilot licence assigned**.

If no account has a Copilot licence, nothing below will work, and that is worth
checking first rather than at step 6.

---

## Step 1 — Create the app registration

Entra admin centre → **Applications** → **App registrations** → **New
registration**.

| Field | Value |
| --- | --- |
| Name | `Level 1 Assistant` |
| Supported account types | **Accounts in this organizational directory only** (single tenant) |
| Redirect URI | **leave empty** |

Register.

## Step 2 — Turn on the public client flow

In the new registration → **Authentication** → scroll to **Advanced settings** →
**Allow public client flows** → set to **Yes** → Save.

This is what enables device-code sign-in. Without it, step 6 fails with a
message about the client not being public.

**Do not create a client secret.** A public desktop client never uses one, and
JOE will not accept one.

## Step 3 — Add the delegated permissions

→ **API permissions** → **Add a permission** → **Microsoft Graph** →
**Delegated permissions**. Add these seven:

```
Sites.Read.All
Mail.Read
People.Read.All
OnlineMeetingTranscript.Read.All
Chat.Read
ChannelMessage.Read.All
ExternalItem.Read.All
```

All seven are read-only. None grants the ability to send, modify, or delete
anything. They are what Microsoft requires for the Chat API to ground answers in
your own tenant's content.

## Step 4 — Grant admin consent

→ **API permissions** → **Grant admin consent for l1truck.com**.

Several of these permissions cannot be consented to by a normal user. If that
button is greyed out, you are not a Global Administrator or Privileged Role
Administrator on the tenant, and whoever is will need to do this step.

**Review the seven before consenting.** They are listed above in full, and this
document is the only place they are asked for.

## Step 5 — Put the two ids in the configuration

From the registration's **Overview** page, copy:

- **Directory (tenant) ID**
- **Application (client) ID**

Open:

```
D:\SANDBOX\Assistan_Building\Assistant_Plugin\configuration\joe.config.json
```

Find `reasoning` → `copilot` and fill in:

```json
"tenant_id": "<Directory (tenant) ID>",
"client_id": "<Application (client) ID>"
```

**Neither is a secret.** They identify the app, not you. They are safe in a
configuration file. Nothing else goes here — no password, no secret, no token.

## Step 6 — Run the proof

```bash
launchers\PROVE_COPILOT.cmd
```

It will:

1. Check the configuration and stop with a plain reason if anything is missing.
2. Show you a Microsoft URL and a device code. Open the URL, enter the code,
   sign in with the **work account that has the Copilot licence**.
3. Send **one real prompt** and record exactly what comes back.
4. Write the evidence to `proof\COPILOT_LIVE_PROOF.md`.

Your sign-in is held by MSAL in a **Windows-encrypted** token cache. No token,
secret, password, or authentication code is written to the evidence file, the
logs, the reports, or the screen.

---

## What the proof checks, beyond "did it answer"

An answer is not enough. The proof also fails if Copilot claims a source class
it may never claim — `LOCAL_LIBRARY`, `LOCAL_OUTLOOK`, `ROUTE_RISK_EVENT`, or
`DISPATCH_FACT`. Copilot grounding must never masquerade as a Company Library,
Outlook, Route Risk, or Dispatch result, and a fluent answer that lies about
where it came from is worse than no answer.

## If it fails

The exit codes mean different things:

| Code | Meaning |
| --- | --- |
| 0 | Reasoning is live and proven. |
| 1 | It answered, but the answer or its provenance failed a check. Reasoning is **not** proven. |
| 2 | Blocked — a step above is incomplete. Not a program failure. |

Until it exits 0, reasoning stays `NOT CONNECTED` everywhere in the program,
and a mocked test is never described as a live answer.

## Undoing it

In JOE window → **Settings** → **Disconnect and clear
authentication**. The encrypted token cache is deleted and reasoning returns to
`NOT CONFIGURED`. Every local capability — Library, Outlook, voice, memory,
retention — keeps working exactly as before, because none of them ever depended
on Copilot.

To undo it completely, delete the app registration in Entra.

---

Mike Zachary remains final authority.
