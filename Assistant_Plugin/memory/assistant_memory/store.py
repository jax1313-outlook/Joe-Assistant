r"""Filesystem store for retention records.

One JSON file per record. Active records live in Data\active. Expired and
deleted tombstones move out of active so they cannot appear in an active query.

Every write is checked against the folder root. The store refuses to write
anywhere outside ASST\2, which is how this workstream proves it stays inside
its assigned folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .record import MemoryRecord, RetentionState

ENV_ROOT = "ASSISTANT_MEMORY_ROOT"

ACTIVE_DIR = "active"
EXPIRED_DIR = "expired"
DELETED_DIR = "deleted"

_BUCKET_FOR_STATE = {
    RetentionState.TEMPORARY: ACTIVE_DIR,
    RetentionState.SAVED: ACTIVE_DIR,
    RetentionState.FORMAL: ACTIVE_DIR,
    RetentionState.PRINT_READY: ACTIVE_DIR,
    RetentionState.EXPIRED: EXPIRED_DIR,
    RetentionState.DELETED: DELETED_DIR,
}


class StoreError(RuntimeError):
    pass


def default_folder_root() -> Path:
    """Folder 2 root: env override, else three levels above this file."""
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    # ...\2\Source\assistant_memory\store.py -> ...\2
    return Path(__file__).resolve().parent.parent.parent


class MemoryStore:
    def __init__(self, folder_root: str | Path | None = None) -> None:
        self.folder_root = (
            Path(folder_root).resolve() if folder_root else default_folder_root()
        )
        self.data_root = self.folder_root / "Data"
        self._ensure_dirs()

    # ---- containment --------------------------------------------------

    def assert_within_folder(self, path: str | Path) -> Path:
        """Refuse any path outside this workstream's folder."""
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(self.folder_root)
        except ValueError:
            raise StoreError(
                "refused write outside folder root: "
                + str(resolved)
                + " (root=" + str(self.folder_root) + ")"
            ) from None
        return resolved

    def _ensure_dirs(self) -> None:
        for bucket in (ACTIVE_DIR, EXPIRED_DIR, DELETED_DIR):
            path = self.data_root / bucket
            self.assert_within_folder(path)
            path.mkdir(parents=True, exist_ok=True)

    # ---- paths --------------------------------------------------------

    def bucket_for(self, state: str) -> str:
        try:
            return _BUCKET_FOR_STATE[state]
        except KeyError:
            raise StoreError("unknown record state: " + str(state)) from None

    def path_for(self, record_id: str, state: str) -> Path:
        return self.data_root / self.bucket_for(state) / (record_id + ".json")

    def _find_existing(self, record_id: str) -> Path | None:
        for bucket in (ACTIVE_DIR, EXPIRED_DIR, DELETED_DIR):
            candidate = self.data_root / bucket / (record_id + ".json")
            if candidate.exists():
                return candidate
        return None

    # ---- read / write -------------------------------------------------

    def save(self, record: MemoryRecord) -> Path:
        target = self.assert_within_folder(self.path_for(record.record_id, record.state))
        existing = self._find_existing(record.record_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(record.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if existing is not None and existing.resolve() != target.resolve():
            existing.unlink()
        return target

    def load(self, record_id: str) -> MemoryRecord:
        path = self._find_existing(record_id)
        if path is None:
            raise StoreError("no record found: " + str(record_id))
        return MemoryRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def exists(self, record_id: str) -> bool:
        return self._find_existing(record_id) is not None

    def _list_bucket(self, bucket: str) -> list[MemoryRecord]:
        directory = self.data_root / bucket
        if not directory.exists():
            return []
        records = []
        for path in sorted(directory.glob("*.json")):
            records.append(
                MemoryRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            )
        return records

    def list_active(self, state: str | None = None) -> list[MemoryRecord]:
        """Active retention set. Never includes EXPIRED or DELETED."""
        records = [
            record
            for record in self._list_bucket(ACTIVE_DIR)
            if record.state not in RetentionState.TERMINAL
        ]
        if state:
            records = [record for record in records if record.state == state]
        return sorted(records, key=lambda r: r.created_at)

    def list_expired(self) -> list[MemoryRecord]:
        return sorted(self._list_bucket(EXPIRED_DIR), key=lambda r: r.created_at)

    def list_deleted(self) -> list[MemoryRecord]:
        return sorted(self._list_bucket(DELETED_DIR), key=lambda r: r.created_at)

    def list_all(self) -> list[MemoryRecord]:
        return sorted(
            self._list_bucket(ACTIVE_DIR)
            + self._list_bucket(EXPIRED_DIR)
            + self._list_bucket(DELETED_DIR),
            key=lambda r: r.created_at,
        )
