"""Canonical governance: what currently governs, what used to, and drift between them.

Phase 1 found that five repositories carry a constitution and they are not the
same constitution:

    DISPATCH_CONSTITUTION_v2   Claude, Joe-Assistant, Publisher   (identical bytes)
    DISPATCH_CONSTITUTION_v3   Claude-3, Library                  (identical bytes)
    neither                    Dispatch  (the production repository)

All five mandate a Manager component. `Dispatch/CLAUDE.md` section 5.6 forbids
one, and `Dispatch/tests/test_repository_doctrine.py` enforces that ban in CI
with an allowlist of every permissible use of the word. So an agent cold-starting
in Claude/, Joe-Assistant/ or Publisher/ reads its constitution and builds toward
a component the production repository will reject.

That is not a documentation problem. It is an authority problem, and the fix is
not to merge the documents -- merging two constitutions that disagree produces a
third document that governs nothing. The fix is to say, in one machine-readable
place, which document is current for which question, and to make the answer
checkable.
"""

from dispatch_governance.registry import (
    CURRENT,
    HISTORICAL,
    SUPERSEDED,
    GovernanceRegistry,
    load_registry,
)
from dispatch_governance.drift import DriftFinding, check_drift, render_drift

__all__ = [
    "CURRENT",
    "SUPERSEDED",
    "HISTORICAL",
    "GovernanceRegistry",
    "load_registry",
    "DriftFinding",
    "check_drift",
    "render_drift",
]
