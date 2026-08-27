# Workstream 2 - Assistant Memory - Context

**Component:** Assistant Memory
**Folder:** `D:\SANDBOX\Assistan_Building\ASST\2`
**Version:** 1.0.0
**Final authority:** Mike Zachary

---

## What this component is

The Sandbox retention system. It holds Assistant interaction records and
governs what happens to them over time: Level 1, Level 2, Level 3, Print Ready,
Delete, and Expiration.

## The problem it solves

Without a retention layer, every Assistant interaction is either lost the
instant it happens or kept forever. Neither is right.

Most interactions are worth nothing an hour later - a question about the next
scale, a rate that was never going to work. A few are worth keeping. A smaller
few are worth marking formal. The driver knows which is which, but only after
the answer exists.

So the default is temporary, an explicit operation changes that default, and
nothing becomes permanent by accident.

## Sandbox doctrine, as this component implements it

Restated here in full so folder 2 can be reviewed without opening anything else:

- Every interaction begins **TEMPORARY** at **Level 1**.
- Default retention is **three hours**.
- If untouched at expiration, the record is marked **EXPIRED**, its content is
  purged, and it leaves the active set. It is **never promoted** anywhere.
- **Level 2** preserves it as `SAVED` for parked review and stops expiration.
- **Level 3** preserves it as `FORMAL` and stops expiration.
- **Print Ready** preserves it as `PRINT_READY` and stops expiration. Print is a
  **state, not a level** - it does not change `interaction_level`.
- **Delete** purges the content, records a reason, and removes the record from
  the active set without promoting it.

## What "held" means here, exactly

A preserved record is a plain JSON file on this disk, inside `ASST\2\Data`.

It is **not** backed up, **not** synchronized, **not** filed in any library, and
**not** routed to any operational system. Nothing in this component describes a
record as permanently saved, because from this component's point of view it
is not.

## What it deliberately is not

This workstream holds records. That is the whole job. It has:

- no user interface
- no natural-language command recognition
- no library, research, email, calendar, or contact access
- no voice
- no routing, filing, or promotion into any other system
- no artifact production and no printing
- no network code of any kind

## Who operates it

Mike Zachary, through a command line. Operations are explicit and named -
`level-2`, `level-3`, `print-ready`, `delete` - rather than phrases to be
interpreted. Interpreting ordinary driver language is a different job and does
not belong in a retention store.

## Runtime

Python 3.10 or newer through the `py` launcher. Verified on this machine:
Python 3.14.5. Standard library only. Nothing is installed.

## Relationship to other workstreams

None. This folder does not know any other workstream exists. It imports nothing
from folders 1 or 3 through 6, and nothing from any earlier project - including
the existing Sandbox Engine, whose doctrine it follows and whose code it does
not touch.
