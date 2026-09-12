"""Make the whole sandbox suite runnable with one command from the repository root.

Before this, `pytest` at the root collected nothing but errors: the plugin's
tests import `app`, `adapters`, `conversation` as top-level packages, which only
resolve when the working directory is `Assistant_Plugin/`. The Workers and
Governance suites each had their own required directory too. So there were three
places to stand and three commands to remember, and a suite that is awkward to
run is a suite that gets run less often than it should.

Adding the three roots to `sys.path` here is deliberate rather than turning each
tree into an installable package. They are separate programs in separate
directories on purpose -- THE MIKE RULE: a subsystem that can be lifted out and
run on its own is worth more than one sharing a clever abstraction -- and each
still runs standalone from its own directory exactly as before. This only adds a
way to run all of them at once.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

#: Each is a self-contained program. Order matters only in that the plugin's own
#: modules should win any name collision, since its tests are the largest set.
SUITE_ROOTS = (
    ROOT / "Assistant_Plugin",
    ROOT / "Workers",
    ROOT / "Governance",
)

for path in SUITE_ROOTS:
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
