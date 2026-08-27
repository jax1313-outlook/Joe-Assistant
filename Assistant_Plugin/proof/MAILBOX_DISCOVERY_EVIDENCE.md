# Mailbox Discovery Evidence

**Standing approvals, Mike 2026-08-25 (final):** `Ops@l1truck.com` APPROVED,
`Admin@l1truck.com` APPROVED, `System@l1truck.com` **IGNORE**.

`System@l1truck.com` appears in the enumerations below only because it is
genuinely present in the Outlook profile. Omitting it would make these tables
false. It is ignored, not used, and not planned against.

**Run:** 2026-08-25
**Source:** Outlook Desktop 16.0.0.20326, MAPI profile `Outlook`, read-only.
**Method:** live COM enumeration. Nothing renamed, mapped, inferred, or
simulated.

---

## Answers to the four questions

### 1. Is the adapter enumerating desktop Outlook stores only?

**No — it is narrower than that.** The adapter enumerates
`Namespace.Accounts` only. It does not read `Namespace.Stores` and does not
read `Namespace.Folders`.

That is a real limitation and it is already recorded as one: a shared mailbox
appears in `Stores` and `Folders` but **not** in `Accounts`, so a shared mailbox
would be invisible to discovery on any profile where those views diverge.

**On this profile they do not diverge.** All three views return the same three
mailboxes. So the adapter's narrowness is not what is hiding
`Admin@l1truck.com`.

### 2. Is Admin@l1truck.com mounted in desktop Outlook?

**No.**

Checked four ways, all agreeing:

| Check | Result |
| --- | --- |
| `Namespace.Accounts` | not present |
| `Namespace.Stores` | not present |
| `Namespace.Folders` | not present |
| Direct name probe for `*Admin*` across all three | **NOT PRESENT** |

### Re-checked after a full Outlook restart — 2026-08-25

Outlook Desktop was stopped and started fresh, and discovery re-run against a
clean MAPI session:

| Mailbox | `account_status()` |
| --- | --- |
| `Ops@l1truck.com` | **present** |
| `Admin@l1truck.com` | **absent** |
| `System@l1truck.com` | present *(ignored by ruling)* |

`accounts_known = True`, so **`absent` here is a finding, not ignorance.** The
earlier working theory — that Outlook simply had not picked the mailbox up
since it was added — **did not hold.** A restart did not mount it.

`Admin@l1truck.com` needs adding to this machine's Outlook Desktop profile.
That is Mike's action; the paths are at the end of this document.

### 3. Not mounted — reported clearly

**`Admin@l1truck.com` is not mounted in Outlook Desktop on this machine.**

This is not a claim that the mailbox does not exist. The screenshot shows it
live in Outlook Web with its own Inbox, Drafts, Sent Items, Deleted Items,
Junk Email, Notes, Archive, Conversation History, and Search Folders. It exists
on the service.

Outlook Web and Outlook Desktop are separate surfaces with separate mailbox
lists. A mailbox added in Web does not appear in Desktop until Desktop is told
about it. JOE reads Desktop via COM and has no view of Web at all.

**Both statements are true at once: the mailbox is active, and this machine's
Outlook Desktop does not have it.**

### 4. Mounted — why discovery would miss it

Not applicable. It is not mounted.

---

## Every mailbox Outlook Desktop exposes

Exactly as reported, nothing added or interpreted.

| Display Name | SMTP Address | Store Name | Inbox Count |
| --- | --- | --- | --- |
| jax1313@outlook.com | jax1313@outlook.com | jax1313@outlook.com | 223 |
| system@l1truck.com | System@l1truck.com | System@l1truck.com | 53 |
| Ops@l1truck.com | Ops@l1truck.com | Ops@l1truck.com | 127 |
| **Admin@l1truck.com** | **— not exposed —** | **— not exposed —** | **— not exposed —** |

`Display Name` is Outlook's own casing and differs from `SMTP Address` for
`system@l1truck.com`. Reported as-is; not normalised.

Inbox Count is the total item count of each store's default Inbox folder. The
`1` beside Admin@'s Inbox in the Outlook Web screenshot is an **unread** count,
which is a different number from the totals above.

### Store detail

| Store | ExchangeStoreType | Top-level root present |
| --- | --- | --- |
| Ops@l1truck.com | 4 | yes |
| jax1313@outlook.com | 0 | yes |
| System@l1truck.com | 4 | yes |

---

## What was not done

- No mailbox was added, mounted, renamed, or mapped.
- No SMTP address was inferred from a display name, or the reverse.
- No mailbox was simulated, stubbed, or assumed present.
- `Admin@l1truck.com` is **not** hard-coded anywhere. Discovery will find it the
  moment Outlook Desktop exposes it, with no code change.
- Nothing was written to any mailbox. Read-only throughout.

## Mounting it is Mike's action

Outlook Desktop is currently running. If `Admin@l1truck.com` is added while it
is open, the profile change may not appear until Outlook is restarted — which
is the most likely explanation if it was already added.

Two paths, depending on what the mailbox is:

- **A full account:** Outlook → File → Add Account.
- **A shared mailbox:** it auto-maps if permissions grant that, but the mount
  usually only appears after an Outlook restart. It can also be added manually
  under Account Settings → Change → More Settings → Advanced → Open these
  additional mailboxes.

Either way, re-run:

```bash
launchers\JOE_ACCOUNTS.cmd
```

If it appears in `Stores` but **not** in `Accounts`, that is the shared-mailbox
case, and the adapter will still not see it — because it reads `Accounts` only.
Fixing that is EMAIL_CONNECTION_LAYER_v1, which is approved and not being built
yet.

---

Mike Zachary remains final authority.
