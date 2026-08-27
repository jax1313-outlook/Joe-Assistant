"""Assistant Library - Workstream 3.

Read-only Company Library access: search, retrieve, reference.

This package imports nothing outside itself and nothing outside folder 3.
It contains no call that writes, creates, deletes, or renames a file.
"""

__version__ = "1.0.0"

from .document import (
    SUPPORTED_EXTENSIONS,
    DocumentError,
    LibraryDocument,
    load_document,
)
from .search import SearchHit, search_documents, query_terms, tokenize
from .library import IndexReport, Library, LibraryError, resolve_root

__all__ = [
    "__version__",
    "SUPPORTED_EXTENSIONS", "DocumentError", "LibraryDocument", "load_document",
    "SearchHit", "search_documents", "query_terms", "tokenize",
    "IndexReport", "Library", "LibraryError", "resolve_root",
]
