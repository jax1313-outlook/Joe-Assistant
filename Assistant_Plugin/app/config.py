"""Configuration loading and path containment.

Every path the application uses is resolved here, and every write path is
checked against the plugin root before anything is written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PLUGIN_ROOT / "configuration"
CONFIG_FILE = CONFIG_DIR / "joe.config.json"
TEMPLATE_FILE = CONFIG_DIR / "joe.config.template.json"

ENV_ROOT = "JOE_ROOT"
ENV_CONFIG = "JOE_CONFIG"


class ConfigError(RuntimeError):
    pass


class ContainmentError(RuntimeError):
    """Raised on any attempt to write outside the plugin root."""


def plugin_root() -> Path:
    override = os.environ.get(ENV_ROOT)
    return Path(override).resolve() if override else PLUGIN_ROOT


def assert_within_plugin(path: str | Path) -> Path:
    """Refuse any write path outside the plugin root.

    This is how the build proves it writes nothing outside its own folder.
    """
    root = plugin_root()
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ContainmentError(
            "refused write outside the plugin root: "
            + str(resolved)
            + "  (root=" + str(root) + ")"
        ) from None
    return resolved


def _strip_comments(value):
    if isinstance(value, dict):
        return {k: _strip_comments(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, list):
        return [_strip_comments(v) for v in value]
    return value


class Config:
    """Loaded configuration, with resolved paths."""

    def __init__(self, data: dict, source: Path) -> None:
        self.data = data
        self.source = source
        self.root = plugin_root()

    # ---- loading ------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        target = Path(path) if path else Path(
            os.environ.get(ENV_CONFIG) or CONFIG_FILE
        )
        if not target.exists():
            raise ConfigError("configuration not found: " + str(target))
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ConfigError(
                "configuration is not valid JSON (" + target.name + "): " + str(error)
            ) from None
        return cls(_strip_comments(raw), target.resolve())

    # ---- access -------------------------------------------------------

    def section(self, name: str) -> dict:
        value = self.data.get(name)
        return dict(value) if isinstance(value, dict) else {}

    def get(self, section: str, key: str, default=None):
        return self.section(section).get(key, default)

    # ---- paths --------------------------------------------------------

    def resolve_path(self, value: str) -> Path:
        """Absolute paths stay absolute; relative paths hang off the root."""
        candidate = Path(value)
        return candidate if candidate.is_absolute() else (self.root / candidate)

    @property
    def runtime_data(self) -> Path:
        return assert_within_plugin(
            self.resolve_path(self.get("paths", "runtime_data", "runtime_data"))
        )

    @property
    def logs(self) -> Path:
        return assert_within_plugin(
            self.resolve_path(self.get("paths", "logs", "logs"))
        )

    def library_sources(self) -> list[dict]:
        """Approved Library locations only. Reading outside the plugin is
        permitted; writing is not, and the Library capability cannot write."""
        out = []
        for entry in self.section("library").get("sources", []):
            if not entry.get("enabled", True):
                continue
            resolved = self.resolve_path(entry.get("path", ""))
            out.append(
                {
                    "name": entry.get("name", resolved.name),
                    "path": resolved,
                    "kind": entry.get("kind", "unknown"),
                    "exists": resolved.exists(),
                }
            )
        return out

    def ensure_runtime_dirs(self) -> None:
        for path in (self.runtime_data, self.logs):
            assert_within_plugin(path).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        return {
            "source": str(self.source),
            "root": str(self.root),
            "runtime_data": str(self.runtime_data),
            "logs": str(self.logs),
            "sections": sorted(self.data.keys()),
        }
