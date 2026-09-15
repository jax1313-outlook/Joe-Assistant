"""The one machine-discoverable answer to "what governs this?".

A registry entry is a claim about *authority*, not about content. It says which
document answers a question, where that document lives, what its bytes were when
the claim was recorded, and -- for anything not current -- what replaced it and
when.

Four states, and the distinction between the last three is the whole point:

``CURRENT``
    Binding now. A builder must follow it.

``SUPERSEDED``
    Was binding; something else replaced it. Kept, readable, and named as
    superseded, because `Dispatch/CLAUDE.md` section 7 is explicit: "Do not edit
    old decisions to hide their history. Mark them SUPERSEDED and cite the
    ruling that replaced them."

``HISTORICAL``
    Never governed, or governs nothing now, and is retained as a record. This is
    where a document like `docs/MANAGER.md` sits: a permanent architectural
    record of a capability that was named and never built.

``ADVISORY``
    Describes intent -- an organisational shape, a direction -- and authorises
    no code. The constitutions are largely this, and saying so is what resolves
    the Manager conflict without deleting anybody's document.

The registry does not rank documents by recency. A v3 that is newer than a v2 is
not automatically the authority: `Dispatch/CLAUDE.md` is older than both and is
the authority for the repository that actually runs, because it is the one whose
clauses are enforced by tests that fail a build.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

CURRENT = "CURRENT"
SUPERSEDED = "SUPERSEDED"
HISTORICAL = "HISTORICAL"
ADVISORY = "ADVISORY"

STATUSES = (CURRENT, SUPERSEDED, HISTORICAL, ADVISORY)

DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "GOVERNANCE_REGISTRY.json"


def sha256_text(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class GovernanceDocument:
    doc_id: str
    repo: str
    path: str
    status: str
    scope: str
    sha256: str = ""
    #: What replaced it. Required when status is SUPERSEDED -- a supersession
    #: with no successor is an assertion that something stopped being true
    #: without saying what became true instead.
    superseded_by: str = ""
    recorded_at: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown governance status: {self.status!r}")
        if self.status == SUPERSEDED and not self.superseded_by:
            raise ValueError(
                f"{self.doc_id} is SUPERSEDED but names nothing that replaced it"
            )

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "repo": self.repo,
            "path": self.path,
            "status": self.status,
            "scope": self.scope,
            "sha256": self.sha256,
            "superseded_by": self.superseded_by,
            "recorded_at": self.recorded_at,
            "note": self.note,
        }


@dataclass
class GovernanceRegistry:
    version: str = "1"
    authority: str = ""
    generated_at: str = ""
    documents: list[GovernanceDocument] = field(default_factory=list)
    #: question -> doc_id. The index a builder actually uses: "who decides
    #: whether a Manager may exist" has one answer, and it is a document.
    answers: dict = field(default_factory=dict)
    unresolved: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------------ lookup

    def get(self, doc_id: str) -> GovernanceDocument | None:
        for doc in self.documents:
            if doc.doc_id == doc_id:
                return doc
        return None

    def current(self) -> list[GovernanceDocument]:
        return [d for d in self.documents if d.status == CURRENT]

    def for_repo(self, repo: str) -> list[GovernanceDocument]:
        lowered = repo.lower()
        return [d for d in self.documents if d.repo.lower() == lowered]

    def answer(self, question: str) -> GovernanceDocument | None:
        doc_id = self.answers.get(question)
        return self.get(doc_id) if doc_id else None

    def binding_for(self, repo: str) -> list[GovernanceDocument]:
        """Everything CURRENT that a builder in this repository must follow.

        Repository-scoped CURRENT documents plus every programme-wide one. A
        worker repository carrying its own copy of a superseded constitution
        gets nothing from this call, which is the point.
        """
        lowered = repo.lower()
        return [
            d for d in self.documents
            if d.status == CURRENT and d.repo.lower() in (lowered, "*")
        ]

    # ------------------------------------------------------------------- io

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "authority": self.authority,
            "generated_at": self.generated_at,
            "answers": self.answers,
            "unresolved": self.unresolved,
            "documents": [d.to_dict() for d in self.documents],
        }

    def save(self, path: Path | str = DEFAULT_REGISTRY) -> Path:
        target = Path(path)
        target.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def from_dict(cls, data: dict) -> "GovernanceRegistry":
        return cls(
            version=str(data.get("version", "1")),
            authority=data.get("authority", ""),
            generated_at=data.get("generated_at", ""),
            answers=dict(data.get("answers", {})),
            unresolved=list(data.get("unresolved", [])),
            documents=[GovernanceDocument(**d) for d in data.get("documents", [])],
        )

    # -------------------------------------------------------------- validation

    def validate(self) -> list[str]:
        """Problems with the registry itself. Empty list means it is coherent."""
        problems: list[str] = []
        seen: set[str] = set()
        for doc in self.documents:
            if doc.doc_id in seen:
                problems.append(f"duplicate doc_id: {doc.doc_id}")
            seen.add(doc.doc_id)
        for doc in self.documents:
            if doc.superseded_by and not self.get(doc.superseded_by):
                problems.append(
                    f"{doc.doc_id} is superseded by {doc.superseded_by}, which is not registered"
                )
            if doc.status == SUPERSEDED:
                successor = self.get(doc.superseded_by)
                if successor and successor.status == SUPERSEDED:
                    problems.append(
                        f"{doc.doc_id} points at {successor.doc_id}, which is itself superseded"
                    )
        for question, doc_id in self.answers.items():
            target = self.get(doc_id)
            if target is None:
                problems.append(f"answer {question!r} names unregistered {doc_id}")
            elif target.status == SUPERSEDED:
                # The only status that cannot answer a question. CURRENT binds,
                # HISTORICAL settles a question about what exists ("was Manager
                # built?"), and ADVISORY settles a question about intent -- but
                # a superseded document answers nothing, because something
                # replaced it and the registry knows what.
                problems.append(
                    f"answer {question!r} points at {doc_id}, which is SUPERSEDED by "
                    f"{target.superseded_by}"
                )
        return problems


def load_registry(path: Path | str = DEFAULT_REGISTRY) -> GovernanceRegistry:
    return GovernanceRegistry.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )
