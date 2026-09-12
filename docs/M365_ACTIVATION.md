# Microsoft 365 — what has to be true before any of this is `LIVE`

**Status of every Microsoft capability in this repository: `UNCONFIGURED`.**
No Graph call has been made from here. The adapters are implemented to
Microsoft's published protocols and the suite drives them through injected
openers against recorded response shapes — that is evidence of software
behaviour, not of connectivity, and this page does not present it as more.

Run `python -m dispatch_launcher transports` (Dispatch) or the suite report
below to see what this machine will actually do.

---

## 1. Microsoft is a replaceable wheel

`Dispatch/CLAUDE.md` records the General Contractor Doctrine: *"Dispatch
coordinates core operational work and uses external wheels... Use the provider;
own the interface."*

So nothing in `Assistant_Plugin/` imports a Microsoft SDK. Six ports
(`m365/ports.py`) say what Dispatch needs; `m365/adapters/graph.py` is one
implementation and `m365/adapters/local.py` is another. Replacing Microsoft
means writing a third file, not editing the program.

| Port | What Dispatch needs | What it must never do |
|---|---|---|
| `CalendarPort` | read the schedule | write a second schedule |
| `MailPort` | send what a person approved | send what nobody approved |
| `FilePort` | keep evidence durably | become the system of record |
| `SitePort` | read shared documents | publish without review |
| `ChatPort` | post a notice a person wrote | hold a conversation |
| `DocumentPort` | produce a document from approved facts | invent a fact |

## 2. Sign-in: delegated device code, and no client secret

`dispatch/connectors/outlook_connector.py` declares
`auth_method = "oauth_client_credentials"`. That is **app-only** Graph: it needs
an Entra ID tenant and an administrator's consent, it **cannot authenticate a
personal Microsoft account at all**, and the permissions it grants are
tenant-wide — a grant that can read every mailbox in an organisation, in order
to read one operator's calendar.

Delegated **device code** is what fits: Dispatch prints a short code, the
operator signs in on any browser as themselves, and the token carries exactly
their own permissions. It works on `outlook.com` accounts and on work accounts,
and no client secret sits on the laptop.

One sign-in serves both programs. Joe borrows Dispatch's token provider when
Dispatch is installed beside it (`m365/registry.py::token_provider`), and
refuses rather than holding a second credential when it is not.

### Registering the application (once)

1. <https://portal.azure.com> → **Microsoft Entra ID** → **App registrations** →
   **New registration**.
2. **Supported account types**: *Accounts in any organizational directory and
   personal Microsoft accounts*. The last part is what makes an `outlook.com`
   account work.
3. Leave **Redirect URI** empty. Register.
4. **Authentication** → **Allow public client flows** → **Yes**. Device code
   requires it; without it the sign-in fails with `unauthorized_client`.
5. Copy the **Application (client) ID**. **Do not create a client secret** —
   nothing here uses one, and there is deliberately no setting to put one in.

### Delegated permissions

| Permission | Why |
|---|---|
| `offline_access` | so a refresh token exists; otherwise every send needs a fresh sign-in |
| `Mail.Send` | to send as the operator |
| `Calendars.Read` | the calendar port reads and never writes (CLAUDE.md §5.5) |
| `Files.ReadWrite` | evidence copies in OneDrive |
| `User.Read` | to show which account is connected |
| `Sites.Read.All` | **only** if a SharePoint site is configured |
| `ChannelMessage.Send` | **only** if Teams notices are wanted |

`Mail.Read` is deliberately **not** requested. Neither program reads the
operator's mailbox and the scope should say so.

## 3. Settings

| Variable | Default | Meaning |
|---|---|---|
| `DISPATCH_MS_CLIENT_ID` | — | Application (client) ID. Absent = `UNCONFIGURED`, and every Microsoft path refuses rather than making an anonymous call. |
| `DISPATCH_MS_TENANT` | `common` | `common` accepts personal and work accounts. |
| `JOE_MS_TOKEN_CACHE` | `$DISPATCH_MEMORY_ROOT/auth/microsoft-token.json` | Where the refresh token lives. |
| `JOE_SHAREPOINT_SITE_ID` | — | Absent = the site port reports `UNCONFIGURED`. |
| `JOE_TEAMS_TEAM_ID` | — | Absent = the chat port reports `UNCONFIGURED`. |
| `JOE_LOCAL_M365_ROOT` | `LocalM365` | Where the local substitutes write. |
| `JOE_LOCAL_CALENDAR` | — | A JSON file the local calendar reads. |
| `JOE_AZURE_SPEECH_KEY` / `_REGION` | — | Speech. A key makes it `CONFIGURED`, never `LIVE`. |

**Token storage.** `dispatch/msauth.TokenCache` takes injected
`protect`/`unprotect` functions. On Windows the host supplies DPAPI, which ties
the file to the user account so a copied cache is useless elsewhere. On
platforms with no standard-library equivalent the file is written unprotected
under the operating system's own permissions, and this page says so rather than
implying more.

## 4. Turning it on

```
setx DISPATCH_MS_CLIENT_ID <the Application (client) ID>
python -m dispatch_launcher connect-microsoft      # prints a code; sign in
python -m dispatch_launcher transports             # should show LIVE -- Graph
```

### What "connected" proves, and what it does not

A successful sign-in proves the token exchange worked. It does **not** prove a
message was delivered, an event was read, or a file was stored. Send one, read
one, store one — and look. Until then the honest state of every capability is
`UNVERIFIED`, and the twenty-step operational proof treats it that way.

## 5. What the client handles, so six adapters do not each handle it badly

`m365/graph_client.py` is the only thing that speaks HTTP:

- **Throttling** — 429 carries `Retry-After`, and it is honoured exactly. Backing
  off on a schedule of your own while Microsoft tells you the number is how a
  client gets throttled harder.
- **Retry** — 429 and 5xx are "not yet". A 401 refreshes the token once and
  retries once; a second 401 is a permissions problem no retry fixes. Every other
  4xx is an answer, and retrying an answer produces a longer log and no change.
- **Paging** — `@odata.nextLink` is walked. A caller that stops at the first page
  believes it has everything, and nothing in the result says otherwise.
- **Delta** — `@odata.deltaLink` is returned to the caller to store. The client
  keeps no token: one cached inside a client outlives the collection it describes
  and produces a silent gap.

## 6. What is deliberately not built

- **A calendar mirror.** CLAUDE.md §5.5 forbids a second scheduling system.
  There is no `sync`, no local calendar table, and `propose_event` returns a
  proposal unless a recorded human decision is passed with it.
- **A Teams bot.** `post_notice` posts text a person approved. A bot that
  answers in a channel is a second interface to Dispatch with its own authority
  story, and there is no doctrine for one.
- **`.docx` authoring.** Graph converts an uploaded document to PDF; it does not
  author one. Writing OOXML is a dependency and a body of work this package does
  not take, so a `.docx` request is **refused by name** rather than quietly
  producing something else.
- **Resumable uploads.** Files over 4 MB are refused with the reason. Graph's
  simple upload stops there and an upload session is a different flow.
- **Azure Speech adapters.** The status reporting is written and the adapters are
  not; `voice/providers.py` reports `UNCONFIGURED` or `UNAVAILABLE` accordingly
  and falls back to the text engines, which report `SIMULATED`.
