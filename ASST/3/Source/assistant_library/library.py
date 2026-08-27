r"""The Library facade: open a root, index it, search it, retrieve from it.

READ ONLY, structurally. This package contains no call that opens a file for
writing, creates a directory, deletes anything, or renames anything. A test
fails the build if one appears.

The library root is configurable. It defaults to the sample corpus inside
ASST\3 so the component runs with no setup. Pointed at the real Company
Library, it still only reads.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .document import (
    SUPPORTED_EXTENSIONS,
    DocumentError,
    LibraryDocument,
    load_document,
)
from .search import SearchHit, search_documents

ENV_ROOT = "ASSISTANT_LIBRARY_ROOT"

# Directories never worth indexing.
SKIP_DIRECTORIES = frozenset(
    {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea"}
)

MAX_DOCUMENTS = 5000


class LibraryError(RuntimeError):
    pass


@dataclass
class IndexReport:
    """What happened during an index pass. Skips are reported, never hidden."""

    root: str
    indexed: int = 0
    skipped_unsupported: int = 0
    skipped_unreadable: int = 0
    unreadable: list[str] = None  # type: ignore[assignment]
    truncated: bool = False

    def __post_init__(self) -> None:
        if self.unreadable is None:
            self.unreadable = []

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "indexed": self.indexed,
            "skipped_unsupported": self.skipped_unsupported,
            "skipped_unreadable": self.skipped_unreadable,
            "unreadable": list(self.unreadable),
            "truncated": self.truncated,
        }


def default_corpus_root() -> Path:
    """Sample corpus inside folder 3, used when no root is configured."""
    # ...\3\Source\assistant_library\library.py -> ...\3\Corpus
    return Path(__file__).resolve().parent.parent.parent / "Corpus"


def resolve_root(root: str | Path | None = None) -> Path:
    if root:
        return Path(root).resolve()
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).resolve()
    return default_corpus_root()


class Library:
    """Read-only access to a document library."""

    def __init__(self, root: str | Path | None = None, auto_index: bool = True) -> None:
        self.root = resolve_root(root)
        self._documents: dict[str, LibraryDocument] = {}
        self.report = IndexReport(root=str(self.root))
        if auto_index:
            self.index()

    # ---- indexing -----------------------------------------------------

    def index(self) -> IndexReport:
        """Walk the root and read every supported document.

        Opens files for reading only. Creates nothing, writes nothing.
        """
        if not self.root.exists():
            raise LibraryError("library root does not exist: " + str(self.root))
        if not self.root.is_dir():
            raise LibraryError("library root is not a directory: " + str(self.root))

        self._documents = {}
        report = IndexReport(root=str(self.root))

        for path in sorted(self.root.rglob("*")):
            if len(self._documents) >= MAX_DOCUMENTS:
                report.truncated = True
                break
            if path.is_dir():
                continue
            if any(part in SKIP_DIRECTORIES for part in path.parts):
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                report.skipped_unsupported += 1
                continue
            try:
                document = load_document(path, self.root)
            except (DocumentError, OSError) as error:
                report.skipped_unreadable += 1
                report.unreadable.append(path.name + ": " + str(error))
                continue
            self._documents[document.doc_id] = document
            report.indexed += 1

        self.report = report
        return report

    # ---- reading ------------------------------------------------------

    @property
    def documents(self) -> list[LibraryDocument]:
        return sorted(self._documents.values(), key=lambda d: d.relative_path)

    def __len__(self) -> int:
        return len(self._documents)

    @property
    def is_empty(self) -> bool:
        return not self._documents

    def has(self, doc_id: str) -> bool:
        return doc_id in self._documents

    def get(self, doc_id: str) -> LibraryDocument:
        """Retrieve one document in full."""
        try:
            return self._documents[doc_id]
        except KeyError:
            raise LibraryError("no such document: " + str(doc_id)) from None

    def find_by_path(self, relative_path: str) -> LibraryDocument:
        wanted = str(relative_path).replace("\\", "/").lower()
        for document in self._documents.values():
            if document.relative_path.lower() == wanted:
                return document
        raise LibraryError("no document at path: " + str(relative_path))

    # ---- search -------------------------------------------------------

    def search(
        self, query: str, require_all: bool = False, limit: int = 10
    ) -> list[SearchHit]:
        return search_documents(
            self.documents, query, require_all=require_all, limit=limit
        )

    # ---- reference ----------------------------------------------------

    def reference(self, doc_id: str) -> str:
        """A citable reference to one document."""
        return self.get(doc_id).reference()

    def references(self, doc_ids: list[str]) -> list[str]:
        return [self.reference(doc_id) for doc_id in doc_ids]
