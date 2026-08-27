r"""Filesystem store for Sandbox records.

One JSON file per record. Active records live in Sandbox/active.
Expired and deleted tombstones move out of active so they cannot appear
in an active Sandbox query.

Every write is checked against the project root. The store refuses to
write anywhere outside the project, which is how the build proves no
record escaped D:\Sandbox\Assistan_Building.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .records import SandboxRecord, RecordState

ENV_ROOT = "SANDBOX_ENGINE_ROOT"

ACTIVE_DIR = "active"
EXPIRED_DIR = "expired"
DELETED_DIR = "deleted"

_BUCKET_FOR_STATE = {
    RecordState.TEMPORARY: ACTIVE_DIR,
    RecordState.SAVED: ACTIVE_DIR,
    RecordState.FORMAL: ACTIVE_DIR,
    RecordState.PRINT_READY: ACTIVE_DIR,
    RecordState.EXPIRED: EXPIRED_DIR,
    RecordState.DELETED: DELETED_DIR,
}


class StoreError(RuntimeError):
    pass


def default_project_root() -> Path:
    """Project root: env override, else two levels above this package."""
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    # .../Build/sandbox_engine/store.py -> .../Build -> project root
    return Path(__file__).resolve().parent.parent.parent


class SandboxStore:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root).resolve() if project_root else default_project_root()
        self.sandbox_root = self.project_root / "Sandbox"
        self.artifacts_root = self.project_root / "Artifacts"
        self.artifact_requests_root = self.artifacts_root / "requests"
        self._ensure_dirs()

    # ---- containment ---------------------------------------------------

    def assert_within_project(self, path: str | Path) -> Path:
        """Refuse any path outside the project root."""
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(self.project_root)
        except ValueError:
            raise StoreError(
                f"refused write outside project root: {resolved} (root={self.project_root})"
            ) from None
        return resolved

    def _ensure_dirs(self) -> None:
        for path in (
            self.sandbox_root / ACTIVE_DIR,
            self.sandbox_root / EXPIRED_DIR,
            self.sandbox_root / DELETED_DIR,
            self.artifact_requests_root,
        ):
            self.assert_within_project(path)
            path.mkdir(parents=True, exist_ok=True)

    # ---- paths -----------------------------------------------------------

    def bucket_for(self, state: str) -> str:
        try:
            return _BUCKET_FOR_STATE[state]
        except KeyError:
            raise StoreError(f"unknown record state: {state}") from None

    def path_for(self, sandbox_id: str, state: str) -> Path:
        bucket = self.bucket_for(state)
        return self.sandbox_root / bucket / f"{sandbox_id}.json"

    def _find_existing(self, sandbox_id: str) -> Path | None:
        for bucket in (ACTIVE_DIR, EXPIRED_DIR, DELETED_DIR):
            candidate = self.sandbox_root / bucket / f"{sandbox_id}.json"
            if candidate.exists():
                return candidate
        return None

    # ---- read / write ----------------------------------------------------

    def save(self, record: SandboxRecord) -> Path:
        target = self.assert_within_project(self.path_for(record.sandbox_id, record.state))
        existing = self._find_existing(record.sandbox_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(record.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if existing is not None and existing.resolve() != target.resolve():
            existing.unlink()
        return target

    def load(self, sandbox_id: str) -> SandboxRecord:
        path = self._find_existing(sandbox_id)
        if path is None:
            raise StoreError(f"no sandbox record found: {sandbox_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return SandboxRecord.from_dict(data)

    def exists(self, sandbox_id: str) -> bool:
        return self._find_existing(sandbox_id) is not None

    def _list_bucket(self, bucket: str) -> list[SandboxRecord]:
        directory = self.sandbox_root / bucket
        records: list[SandboxRecord] = []
        if not directory.exists():
            return records
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(SandboxRecord.from_dict(data))
        return records

    def list_active(self, state: str | None = None) -> list[SandboxRecord]:
        """Active Sandbox contents. Never includes EXPIRED or DELETED."""
        records = [
            record
            for record in self._list_bucket(ACTIVE_DIR)
            if record.state not in RecordState.TERMINAL
        ]
        if state:
            records = [record for record in records if record.state == state]
        return sorted(records, key=lambda r: r.created_at)

    def list_expired(self) -> list[SandboxRecord]:
        return sorted(self._list_bucket(EXPIRED_DIR), key=lambda r: r.created_at)

    def list_deleted(self) -> list[SandboxRecord]:
        return sorted(self._list_bucket(DELETED_DIR), key=lambda r: r.created_at)

    def list_all(self) -> list[SandboxRecord]:
        return sorted(
            self._list_bucket(ACTIVE_DIR)
            + self._list_bucket(EXPIRED_DIR)
            + self._list_bucket(DELETED_DIR),
            key=lambda r: r.created_at,
        )

    # ---- artifact requests ----------------------------------------------

    def write_artifact_request(self, request: dict, body: str) -> tuple[Path, Path]:
        """Write a request for an artifact. Never produces the artifact
        itself and never contacts a printer or any external system."""
        request_id = request["artifact_request_id"]
        json_path = self.assert_within_project(
            self.artifact_requests_root / f"{request_id}.json"
        )
        md_path = self.assert_within_project(
            self.artifact_requests_root / f"{request_id}.md"
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        md_path.write_text(body, encoding="utf-8")
        return json_path, md_path

    def list_artifact_requests(self) -> list[dict]:
        if not self.artifact_requests_root.exists():
            return []
        out = []
        for path in sorted(self.artifact_requests_root.glob("*.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return out
