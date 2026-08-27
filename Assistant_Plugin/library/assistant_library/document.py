"""Library document model and text extraction.

Read only. Nothing in this module opens a file for writing. Text extraction
covers plain text, Markdown, and Word documents, using the standard library
only - no Word, no Office automation, no COM.
"""

from __future__ import annotations

import html
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED_EXTENSIONS = (".md", ".txt", ".markdown", ".docx")

MAX_BYTES = 5 * 1024 * 1024  # a library document larger than this is skipped


class DocumentError(RuntimeError):
    pass


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_docx(path: Path) -> str:
    """Pull the visible text out of a .docx without any Office dependency.

    A .docx is a zip archive; word/document.xml holds the body. Paragraph
    ends become newlines so extracted text keeps its shape.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError) as error:
        raise DocumentError("unreadable .docx: " + path.name) from error
    raw = re.sub(r"</w:p>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    return html.unescape(raw)


_READERS = {
    ".md": _read_plain,
    ".markdown": _read_plain,
    ".txt": _read_plain,
    ".docx": _read_docx,
}


@dataclass
class LibraryDocument:
    """One document in the library. Immutable in practice."""

    doc_id: str
    title: str
    relative_path: str
    absolute_path: str
    extension: str
    size_bytes: int
    modified_at: str
    text: str

    @property
    def line_count(self) -> int:
        return len(self.text.splitlines())

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self, include_text: bool = False) -> dict:
        data = {
            "doc_id": self.doc_id,
            "title": self.title,
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "modified_at": self.modified_at,
            "line_count": self.line_count,
            "word_count": self.word_count,
        }
        if include_text:
            data["text"] = self.text
        return data

    def reference(self) -> str:
        """A citable reference to this document.

        Company Library material is approved company fact, so a reference
        names the document and where it was read from, and nothing more.
        """
        return "{title} ({path}, modified {modified})".format(
            title=self.title,
            path=self.relative_path,
            modified=self.modified_at[:10],
        )


def title_from(path: Path, text: str) -> str:
    """First Markdown H1 if there is one, else the file name."""
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem.replace("_", " ").strip()


def doc_id_from(relative_path: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", relative_path).strip("-").upper()
    return "DOC-" + (slug[:60] if slug else "UNTITLED")


def load_document(path: Path, root: Path) -> LibraryDocument:
    """Read one document. Opens for reading only."""
    resolved = Path(path).resolve()
    extension = resolved.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentError("unsupported document type: " + extension)
    stat = resolved.stat()
    if stat.st_size > MAX_BYTES:
        raise DocumentError("document too large: " + resolved.name)
    text = _READERS[extension](resolved)
    try:
        relative = str(resolved.relative_to(Path(root).resolve()))
    except ValueError:
        relative = resolved.name
    return LibraryDocument(
        doc_id=doc_id_from(relative),
        title=title_from(resolved, text),
        relative_path=relative.replace("\\", "/"),
        absolute_path=str(resolved),
        extension=extension,
        size_bytes=stat.st_size,
        modified_at=_stamp(datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)),
        text=text,
    )
