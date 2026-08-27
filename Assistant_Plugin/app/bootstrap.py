"""Bootstrap: make the packaged components importable.

Each of the six components was built in isolation and is packaged here
unchanged. This module puts each package directory on the import path so the
components keep their original module names and their original code.

Nothing here modifies a component. If a component ever needs changing, that is
a documented defect correction, not a bootstrap concern.
"""

from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# Directories that must be importable. Each holds one packaged component.
COMPONENT_PATHS = (
    PLUGIN_ROOT,               # contracts, governance, app, adapters
    PLUGIN_ROOT / "ui",        # assistant_ui
    PLUGIN_ROOT / "memory",    # assistant_memory, retention_language
    PLUGIN_ROOT / "library",   # assistant_library
    PLUGIN_ROOT / "outlook",   # assistant_outlook
    PLUGIN_ROOT / "research",  # assistant_research
    PLUGIN_ROOT / "voice",     # assistant_voice
)

_done = False


def install() -> list[str]:
    """Put every component directory on sys.path. Idempotent."""
    global _done
    added = []
    for path in COMPONENT_PATHS:
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
            added.append(text)
    _done = True
    return added


def installed() -> bool:
    return _done


def component_report() -> list[dict]:
    """What is packaged, and whether it is present."""
    expected = {
        "ui": "assistant_ui",
        "memory": "assistant_memory",
        "library": "assistant_library",
        "outlook": "assistant_outlook",
        "research": "assistant_research",
        "voice": "assistant_voice",
    }
    report = []
    for folder, package in expected.items():
        directory = PLUGIN_ROOT / folder / package
        report.append(
            {
                "component": folder,
                "package": package,
                "path": str(directory),
                "present": directory.is_dir(),
                "modules": (
                    sorted(p.name for p in directory.glob("*.py"))
                    if directory.is_dir()
                    else []
                ),
            }
        )
    return report


install()
