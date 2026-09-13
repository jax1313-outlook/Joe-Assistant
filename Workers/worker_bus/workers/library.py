"""Library: holds approved assets, and hands out copies. Approves nothing itself.

Thin adapter over `dispatch_library` (its own repository). Present here because
the Publisher pulls templates from it, and the pull has to go through the bus so
that the dependency is visible in one audit trail rather than buried in an
import.

The rule this worker exists to keep: an asset is either approved and in the
Library, or it is not in the Library. Nothing here promotes a draft.
"""

from __future__ import annotations

from dataclasses import dataclass

from worker_bus.contracts import Capability, Finding, WorkerRequest, WorkerResponse, refuse


def _library_available() -> bool:
    try:
        import dispatch_library  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class LibraryWorker:
    worker_id: str = "LIBRARY"
    #: In-memory asset shelf. Used when no real Library is reachable, and by the
    #: tests, which must not depend on a sibling repository being checked out.
    assets: dict = None
    #: A real `dispatch_library.LibraryService`, when one is present. It answers
    #: in the same shape as the shelf -- that equivalence is the whole point of
    #: the contract -- but it is versioned, it enforces the collection taxonomy,
    #: and it refuses a system identity as an accepting authority.
    service: object | None = None

    def __post_init__(self) -> None:
        if self.assets is None:
            self.assets = {}

    # ------------------------------------------------------------- the shelf
    #
    # One pair of accessors, so every capability below reads the same way
    # whether the answer came from the real Library or the in-memory shelf.

    def _asset(self, asset_id: str) -> dict | None:
        """One CURRENT object that may be used, as a plain dict, or None.

        The real Library answers with a `LibraryObject` carrying its version,
        status, accepting authority and collection. Those are not decoration:
        Publisher's refusal to use an unapproved template rests on them, so they
        travel rather than being flattened away.
        """
        return self._lookup(asset_id)[0]

    def _lookup(self, asset_id: str, requested_by: str = "LIBRARY_WORKER") -> tuple[dict | None, str]:
        """(asset, outcome) with outcome RETURNED, MISSING or BLOCKED_REVIEW_DUE.

        A persistent Library can hold an asset that is current and still must
        not be used outside the building: a credential past its review date.
        That is BLOCKED_REVIEW_DUE, and the asset is withheld. Answering ABSENT
        would be a lie about the shelf; answering with the asset would put an
        expired credential in a broker packet.
        """
        if self.service is not None and hasattr(self.service, "availability"):
            answer = self.service.availability(asset_id, purpose="worker bus fetch_asset",
                                               consumer_role=requested_by or "LIBRARY_WORKER")
            obj = answer["object"]
            return (obj.to_dict() if obj is not None else None), answer["outcome"]
        if self.service is not None:
            obj = self.service.current(asset_id)
            return (obj.to_dict(), "RETURNED") if obj is not None else (None, "MISSING")
        asset = self.assets.get(asset_id)
        return asset, ("RETURNED" if asset is not None else "MISSING")

    def _shelf(self, kind: str) -> dict:
        """Everything currently on the shelf, optionally one collection of it."""
        if self.service is not None:
            objects = self.service.list_current(kind or None)
            return {o.object_code: o.to_dict() for o in objects}
        return {
            asset_id: asset for asset_id, asset in self.assets.items()
            if not kind or asset.get("kind") == kind
        }

    def capabilities(self) -> tuple[Capability, ...]:
        return (
            Capability(
                "fetch_asset",
                "Return an approved asset by id.",
                produces="the asset, or ABSENT",
                reads=("library objects",),
            ),
            Capability(
                "list_assets",
                "What is on the shelf, by kind.",
                produces="asset references",
            ),
        )

    def status(self) -> str:
        # A real service is LIVE whether or not anything is on the shelf yet: an
        # empty Library is a Library with nothing in it, not an absent one.
        if self.service is not None:
            return "LIVE"
        if self.assets:
            return "SIMULATED" if not _library_available() else "LIVE"
        return "UNCONFIGURED"

    def handle(self, request: WorkerRequest, deps) -> WorkerResponse:
        if request.capability == "fetch_asset":
            asset_id = request.payload.get("asset_id", "")
            asset, outcome = self._lookup(asset_id, request.requested_by)
            if outcome == "BLOCKED_REVIEW_DUE":
                return WorkerResponse(
                    worker=self.worker_id, capability=request.capability,
                    status="UNAVAILABLE", correlation_id=request.correlation_id,
                    findings=(Finding(
                        "ASSET_REVIEW_DUE",
                        f"{asset_id!r} is in the Library and is due for review.",
                        "A current asset past its review date is blocked from external use "
                        "until a person renews or replaces it.",
                        confidence="UNAVAILABLE", requires_human_review=True,
                        source_ref=f"library:{asset_id}",
                    ),),
                )
            if asset is None:
                return WorkerResponse(
                    worker=self.worker_id, capability=request.capability,
                    status="ABSENT", correlation_id=request.correlation_id,
                    findings=(Finding(
                        "ASSET_NOT_IN_LIBRARY",
                        f"No approved asset {asset_id!r}.",
                        "An asset is either approved and here, or it is not here. "
                        "Nothing in this worker promotes a draft.",
                        confidence="ABSENT",
                    ),),
                )
            return WorkerResponse(
                worker=self.worker_id, capability=request.capability,
                status=self.status(), correlation_id=request.correlation_id,
                artifacts={"asset": dict(asset)},
            )

        kind = request.payload.get("kind", "")
        matching = self._shelf(kind)
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status=self.status() if matching else "ABSENT",
            correlation_id=request.correlation_id,
            artifacts={"assets": sorted(matching)},
        )
