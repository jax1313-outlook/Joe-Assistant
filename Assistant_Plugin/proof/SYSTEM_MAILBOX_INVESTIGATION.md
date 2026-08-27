# System@l1truck.com — Discovery Investigation

**Status: CLOSED — IGNORE.** Mike's final ruling, 2026-08-25.

Not an approved mailbox. Not used, not planned against, not investigated
further. The two unretrieved facts noted below — `ExchangeServer` and the
newest Inbox message date — **will not be pursued.** This document is kept as a
record of what was measured, not as open work.

**Method:** live read-only COM enumeration of Outlook Desktop 16.0.0.20326,
MAPI profile `Outlook`, plus filesystem inspection of the offline store files.
Nothing was written, renamed, mapped, or simulated.

**Facts only.** Where a property could not be retrieved it is marked NOT
OBTAINED with the reason, not filled in. No ownership is inferred.

---

## 1. Exact Outlook object type

`System@l1truck.com` is present as **all three** of the following, simultaneously:

| MAPI collection | Present | Identifier returned |
| --- | --- | --- |
| `Namespace.Accounts` | **yes** | SmtpAddress `System@l1truck.com` |
| `Namespace.Stores` | **yes** | DisplayName `System@l1truck.com` |
| `Namespace.Folders` (top-level roots) | **yes** | `System@l1truck.com` |

### What it is not

- **Not a PST.** Its store file is `system@l1truck.com.ost`.
- **Not a shared / additional mailbox.** Shared mailboxes and "open these
  additional mailboxes" entries appear in `Stores` and `Folders` but **not** in
  `Accounts`. This object appears in `Accounts`, with its own SMTP address and
  its own dedicated offline store file.

### A property that does not discriminate, reported so it is not misread

`Store.IsDataFileStore` returned **`True` for all three stores**, including
`jax1313@outlook.com`. On this Outlook build that property does not distinguish
a PST from an OST, so it is not evidence of anything here. The `.ost` file
extension is the discriminating fact.

### Object type, stated plainly

**A separately configured account with its own cached offline store (OST).**

---

## 2. Properties Outlook can and cannot return

| Requested | Returned | Value |
| --- | --- | --- |
| **EntryID** | **yes** | 528 hex chars, prefix `0000000038A1BB1005E5101AA1BB08002B2A56C20000454D534D44422E444C4C` |
| **ExchangeServer** | **NOT OBTAINED** | see below |
| **StoreType** | **yes** | `ExchangeStoreType = 4` |
| **DeliveryStore flag** | **yes** | it **is** the delivery store of the `system@l1truck.com` account |
| **Root Folder Name** | **yes** | `System@l1truck.com` |

### Additional properties returned

| Property | Value |
| --- | --- |
| `Store.IsOpen` | `True` |
| `Store.IsCachedExchange` | `True` |
| `Store.FilePath` | `C:\Users\jax13\AppData\Local\Microsoft\Outlook\system@l1truck.com.ost` |
| Root subfolder count | 18 |
| `Account.SmtpAddress` | `System@l1truck.com` |
| `Account.DisplayName` | `system@l1truck.com` *(lowercase — see §3)* |
| `Account.AccountType` | `0` |
| `Account.UserName` | `CAFC7B77CA55456993CE8FAFE7A7A212-CD7A9BFB-C7…` *(truncated by the timeout below)* |
| Inbox item count | 53 |

`Account.UserName` is reported exactly as returned. **No meaning is assigned to
it.** The equivalent value for `Ops@l1truck.com` was not obtained, so there is
no basis for calling this string unusual — `jax1313@outlook.com` returned
`jax1313`, but one comparison is not a pattern.

### Why ExchangeServer was not obtained

`Account.ExchangeMailboxServerName` and `Account.AutoDiscoverXml` trigger
network round-trips. Repeated concurrent COM sessions — **mine, not a fault of
this mailbox** — left Outlook unresponsive part-way through the enumeration.

**This affected every account equally.** A subsequent read of the approved
`Ops@l1truck.com` mailbox returned `Outlook did not respond within 90 seconds`,
exactly as `System@l1truck.com` did. That is a state of the tooling, and it is
reported here so it is not mistaken for a finding about this mailbox.

To retrieve it once Outlook settles, with Outlook closed and no other session
attached:

```powershell
$ns = (New-Object -ComObject Outlook.Application).GetNamespace("MAPI")
foreach ($a in $ns.Accounts) { "{0} => {1}" -f $a.SmtpAddress, $a.ExchangeMailboxServerName }
```

---

## 3. Active / cached / orphaned / renamed / legacy

| Classification | Verdict | Evidence |
| --- | --- | --- |
| **Cached** | **YES — established** | `IsCachedExchange = True`; a dedicated `.ost` exists at 16.0 MB |
| **Orphaned** | **NO evidence of it** | it has a live `Accounts` entry, a delivery-store binding, `IsOpen = True`, and an OST that Windows recorded as written **today at 12:35**, one minute after the approved Ops@ mailbox's OST at 12:34 |
| **Renamed** | **NO evidence of it** | the only inconsistency is letter casing: `Account.DisplayName` is `system@…` while SMTP, Store, and Root are `System@…`. A casing difference is not a rename |
| **Active** | **PARTIALLY established** | the *store* is open and being written to by Outlook. Whether the *mailbox on the service* is active cannot be determined from the desktop |
| **Legacy** | **CANNOT BE DETERMINED** | this needs the newest message date in its Inbox, which was not obtained — see the timeout above |

### The one measurement that would resolve it

The date of the newest message in the Inbox. A mailbox still receiving mail is
not legacy; one whose newest item is old is. Run with Outlook idle:

```powershell
$ns = (New-Object -ComObject Outlook.Application).GetNamespace("MAPI")
foreach ($s in $ns.Stores) { if ($s.DisplayName -eq 'System@l1truck.com') {
  $i = $s.GetDefaultFolder(6).Items; $i.Sort("[ReceivedTime]", $true)
  "newest: " + $i.Item(1).ReceivedTime } }
```

---

## Observed comparison — reported, not interpreted

The three stores side by side, as measured:

| Property | jax1313@outlook.com | **System@l1truck.com** | Ops@l1truck.com *(approved)* |
| --- | --- | --- | --- |
| ExchangeStoreType | 0 | **4** | 4 |
| IsCachedExchange | True | **True** | True |
| Store file | `.ost` | **`.ost`** | `.ost` |
| OST size | 286.4 MB | **16.0 MB** | 63.8 MB |
| OST last written | 2026-08-25 12:34 | **2026-08-25 12:35** | 2026-08-25 12:34 |
| Root subfolder count | 68 | **18** | 18 |
| EntryID length | 488 | **528** | 510 |
| Inbox items | 223 | **53** | 127 |
| In `Accounts` | yes | **yes** | yes |
| In `Stores` | yes | **yes** | yes |

On every structural property measured, `System@l1truck.com` matches the
approved `Ops@l1truck.com` and differs from the personal account.

**That is a statement about structure, not about validity, authorisation, or
ownership.** Two mailboxes can be configured identically and only one of them
be a mailbox the business actually has. Which mailboxes Level 1 Transport owns
is not a question Outlook can answer, and nothing here answers it.

---

## Standing status

| | |
| --- | --- |
| `Ops@l1truck.com` | **APPROVED** — mounted and readable |
| `Admin@l1truck.com` | **APPROVED** — active in Outlook Web, **not mounted** in Outlook Desktop |
| `System@l1truck.com` | **IGNORE** — closed |

**Not used, not approved, not planned against.** It is excluded from
EMAIL_CONNECTION_LAYER_v1 candidate lists. It was not removed, disabled,
renamed, or altered — it is untouched in the Outlook profile.

Nothing in this program reads it except when explicitly asked to, and no
default points at it.

---

Mike Zachary remains final authority.
