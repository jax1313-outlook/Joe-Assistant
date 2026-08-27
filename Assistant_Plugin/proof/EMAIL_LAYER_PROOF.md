# JOE - Email Connection Layer v1 Proof

**Run:** 2026-08-26T23:31:55+00:00
**Source:** the live Outlook Desktop profile. Not fixtures.

## Result

**PASS - Email Connection Layer v1 proven.**

| Check | Result | Detail |
| --- | --- | --- |
| Outlook answered discovery | **PASS** | - |
| all three Outlook views were read | **PASS** | accounts=3 stores=3 folders=3 |
| at least one mailbox is configured | **PASS** | 2 configured |
| each mailbox is identified separately | **PASS** | - |
| every mailbox reports an object type | **PASS** | - |
| every mailbox reports a truth state | **PASS** | - |
| a failed discovery is unknown, not absent | **PASS** | unknown |
| a failed discovery is not cached | **PASS** | - |
| the mail source actually holds mail | **PASS** | Operations |
| no calendar source is explained, not silent | **PASS** | no approved mailbox holds any calendar |
| no contacts source is explained, not silent | **PASS** | no approved mailbox holds any contacts |
| zero is empty and minus one is unknown | **PASS** | - |
| a single-mailbox read names the mailbox | **PASS** | Operations |
| a single-mailbox read returned enough to be meaningful | **PASS** | - |
| an all-mailbox read labels every mailbox separately | **PASS** | 2 mailboxes |
| mailbox contents are not merged unlabelled | **PASS** | - |
| one mailbox failing does not disable the others | **PASS** | - |
| no send, delete, or move path exists in the layer | **PASS** | - |
| every mailbox reports write authority none | **PASS** | - |
| the retired mailbox is absent from configuration | **PASS** | - |
| the retired mailbox is absent from the layer | **PASS** | - |
| the retired mailbox is not a configured connection | **PASS** | - |

## Configured mailboxes

| Name | Address | Status | Type | Found in | Mail | Calendar | Contacts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Operations | Ops@l1truck.com | LIVE | full account | Accounts, Stores, Folders | 127 | 0 | 0 |
| Administration | Admin@l1truck.com | LIVE | full account | Accounts, Stores, Folders | 3 | 0 | 0 |

## Which mailbox answers what

| Capability | Source |
| --- | --- |
| mail | Operations |
| calendar | **none** |
| contacts | **none** |

### Why a capability has no source

- **calendar** - no approved mailbox holds any calendar. JOE is not reading an empty one - there is nothing configured that has any.
- **contacts** - no approved mailbox holds any contacts. JOE is not reading an empty one - there is nothing configured that has any.
