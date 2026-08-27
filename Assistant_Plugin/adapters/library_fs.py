"""Library adapter - approved local filesystem sources.

Only the locations listed in configuration are read. Nothing is scanned
automatically, and nothing outside a configured source is ever touched.

READ ONLY: this adapter opens files for reading and does nothing else. The
underlying Library capability has no write capability at all.

Sources are labelled by kind. A `company` source is approved Company Library
material. A `sample` source is fixture data and is reported as SAMPLE DATA,
never as a live Company Library result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from contracts import Provenance, SourceClass, SourceMode, stamp


@dataclass
class LibrarySourceStatus:
    name: str
    path: str
    kind: str
    exists: bool
    indexed: int = 0
    skipped_unsupported: int = 0
    skipped_unreadable: int = 0
    error: str = ""

    @property
    def is_company(self) -> bool:
        return self.kind == "company"

    @property
    def mode(self) -> str:
        if not self.exists or self.error:
            return SourceMode.UNAVAILABLE
        return SourceMode.LIVE if self.is_company else SourceMode.SAMPLE

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "kind": self.kind,
            "exists": self.exists,
            "indexed": self.indexed,
            "skipped_unsupported": self.skipped_unsupported,
            "skipped_unreadable": self.skipped_unreadable,
            "error": self.error,
            "mode": self.mode,
            "is_company": self.is_company,
        }


class LibraryFsAdapter:
    """Opens each configured source with the packaged Library capability."""

    name = "library-fs"

    def __init__(self, sources: list[dict], max_documents: int = 2000) -> None:
        self.configured = list(sources or [])
        self.max_documents = max_documents
        self.statuses: list[LibrarySourceStatus] = []
        self._libraries: list[tuple[LibrarySourceStatus, object]] = []
        self.loaded = False

    # ---- loading ------------------------------------------------------

    def load(self) -> list[LibrarySourceStatus]:
        """Index every configured source. Reads only."""
        from assistant_library.library import Library, LibraryError

        self.statuses = []
        self._libraries = []

        for entry in self.configured:
            path = Path(entry.get("path", ""))
            status = LibrarySourceStatus(
                name=str(entry.get("name", path.name)),
                path=str(path),
                kind=str(entry.get("kind", "unknown")),
                exists=path.exists(),
            )
            if not status.exists:
                status.error = "configured path does not exist"
                self.statuses.append(status)
                continue
            try:
                library = Library(path)
            except LibraryError as error:
                status.error = str(error)
                self.statuses.append(status)
                continue
            report = library.report
            status.indexed = report.indexed
            status.skipped_unsupported = report.skipped_unsupported
            status.skipped_unreadable = report.skipped_unreadable
            self.statuses.append(status)
            self._libraries.append((status, library))

        self.loaded = True
        return self.statuses

    def _ensure(self) -> None:
        if not self.loaded:
            self.load()

    # ---- reading ------------------------------------------------------

    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Search every loaded source. Results carry their source and kind."""
        self._ensure()
        hits: list[dict] = []
        for status, library in self._libraries:
            for hit in library.search(query, limit=limit):
                hits.append(
                    {
                        "source_name": status.name,
                        "source_kind": status.kind,
                        "is_company": status.is_company,
                        "mode": status.mode,
                        "doc_id": hit.doc_id,
                        "title": hit.title,
                        "relative_path": hit.relative_path,
                        "score": hit.score,
                        "matched_terms": list(hit.matched_terms),
                        "missing_terms": list(hit.missing_terms),
                        "snippets": list(hit.snippets),
                        "reference": hit.reference,
                    }
                )
        # Company material sorts above sample material at equal score, so a
        # fixture never outranks approved company content.
        hits.sort(key=lambda h: (-h["score"], not h["is_company"], h["doc_id"]))
        return hits[:limit] if limit and limit > 0 else hits

    def get(self, doc_id: str) -> dict | None:
        self._ensure()
        from assistant_library.library import LibraryError

        for status, library in self._libraries:
            try:
                document = library.get(doc_id)
            except LibraryError:
                continue
            return {
                "source_name": status.name,
                "source_kind": status.kind,
                "is_company": status.is_company,
                "mode": status.mode,
                **document.to_dict(include_text=True),
            }
        return None

    # ---- reporting ----------------------------------------------------

    @property
    def total_indexed(self) -> int:
        self._ensure()
        return sum(status.indexed for status in self.statuses)

    @property
    def has_company_source(self) -> bool:
        self._ensure()
        return any(
            status.is_company and status.exists and status.indexed > 0
            for status in self.statuses
        )

    @property
    def has_any_source(self) -> bool:
        self._ensure()
        return self.total_indexed > 0

    def provenance_for(self, hit: dict) -> Provenance:
        return Provenance(
            source="Library / " + str(hit.get("source_name", "unknown")),
            mode=str(hit.get("mode", SourceMode.UNAVAILABLE)),
            as_of=stamp(),
            detail=str(hit.get("relative_path", "")),
            source_class=SourceClass.LOCAL_LIBRARY,
        )

    def probe(self) -> dict:
        self._ensure()
        return {
            "available": self.has_any_source,
            "live_connection": self.has_company_source,
            "mode": (
                SourceMode.LIVE
                if self.has_company_source
                else (SourceMode.SAMPLE if self.has_any_source else SourceMode.UNAVAILABLE)
            ),
            "indexed": self.total_indexed,
            "sources": [status.to_dict() for status in self.statuses],
            "blocker": (
                ""
                if self.has_any_source
                else "no approved Library location is configured or reachable"
            ),
        }
