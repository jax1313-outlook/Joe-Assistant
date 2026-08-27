"""Deterministic search over library documents.

No model, no ranking heuristics that cannot be explained. The score is a
stated formula, so a reviewer can predict the ordering by reading it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .document import LibraryDocument

TITLE_WEIGHT = 5
BODY_WEIGHT = 1
SNIPPET_RADIUS = 90
MAX_SNIPPETS = 3

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")

# Words too common to narrow anything down. Kept short and visible on purpose.
STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in into is it its of on
    or that the this to was what when where which who why with""".split()
)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text or "")]


def query_terms(query: str) -> list[str]:
    """Query tokens, stopwords removed - unless that would empty the query."""
    tokens = tokenize(query)
    meaningful = [token for token in tokens if token not in STOPWORDS]
    return meaningful or tokens


@dataclass
class SearchHit:
    doc_id: str
    title: str
    relative_path: str
    score: int
    matched_terms: list[str] = field(default_factory=list)
    missing_terms: list[str] = field(default_factory=list)
    title_matches: int = 0
    body_matches: int = 0
    snippets: list[str] = field(default_factory=list)
    reference: str = ""

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "relative_path": self.relative_path,
            "score": self.score,
            "matched_terms": list(self.matched_terms),
            "missing_terms": list(self.missing_terms),
            "title_matches": self.title_matches,
            "body_matches": self.body_matches,
            "snippets": list(self.snippets),
            "reference": self.reference,
        }


def _count(tokens: list[str], term: str) -> int:
    return sum(1 for token in tokens if token == term)


def _snippets(text: str, terms: list[str]) -> list[str]:
    """Short windows of the document around the first few matches."""
    found: list[str] = []
    lowered = text.lower()
    for term in terms:
        start = lowered.find(term)
        if start < 0:
            continue
        left = max(0, start - SNIPPET_RADIUS)
        right = min(len(text), start + len(term) + SNIPPET_RADIUS)
        window = " ".join(text[left:right].split())
        if left > 0:
            window = "..." + window
        if right < len(text):
            window = window + "..."
        if window not in found:
            found.append(window)
        if len(found) >= MAX_SNIPPETS:
            break
    return found


def score_document(document: LibraryDocument, terms: list[str]) -> SearchHit | None:
    """Score one document against the query terms.

    Formula, in full:
        score = 5 * (title term occurrences) + 1 * (body term occurrences)

    A document matching none of the terms scores nothing and is dropped.
    """
    title_tokens = tokenize(document.title)
    body_tokens = tokenize(document.text)

    title_matches = 0
    body_matches = 0
    matched: list[str] = []
    missing: list[str] = []

    for term in terms:
        in_title = _count(title_tokens, term)
        in_body = _count(body_tokens, term)
        if in_title or in_body:
            matched.append(term)
        else:
            missing.append(term)
        title_matches += in_title
        body_matches += in_body

    if not matched:
        return None

    return SearchHit(
        doc_id=document.doc_id,
        title=document.title,
        relative_path=document.relative_path,
        score=TITLE_WEIGHT * title_matches + BODY_WEIGHT * body_matches,
        matched_terms=matched,
        missing_terms=missing,
        title_matches=title_matches,
        body_matches=body_matches,
        snippets=_snippets(document.text, matched),
        reference=document.reference(),
    )


def search_documents(
    documents: list[LibraryDocument],
    query: str,
    require_all: bool = False,
    limit: int = 10,
) -> list[SearchHit]:
    """Rank documents against a query.

    require_all=True drops any document missing one of the query terms.
    Ties break on document id, so ordering is stable across runs.
    """
    terms = query_terms(query)
    if not terms:
        return []
    hits: list[SearchHit] = []
    for document in documents:
        hit = score_document(document, terms)
        if hit is None:
            continue
        if require_all and hit.missing_terms:
            continue
        hits.append(hit)
    hits.sort(key=lambda h: (-h.score, h.doc_id))
    return hits[:limit] if limit and limit > 0 else hits
