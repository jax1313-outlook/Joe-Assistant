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
    #: In-memory asset shelf for the sandbox. The real adapter replaces this
    #: with dispatch_library.LibraryService; the shape it answers in does not
    #: change, which is the point of having a contract.
    assets: dict = None

    def __post_init__(self) -> None:
        if self.assets is None:
            self.assets = {}

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
        if self.assets:
            return "SIMULATED" if not _library_available() else "LIVE"
        return "UNCONFIGURED"

    def handle(self, request: WorkerRequest, deps) -> WorkerResponse:
        if request.capability == "fetch_asset":
            asset_id = request.payload.get("asset_id", "")
            asset = self.assets.get(asset_id)
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
        matching = {
            asset_id: asset for asset_id, asset in self.assets.items()
            if not kind or asset.get("kind") == kind
        }
        return WorkerResponse(
            worker=self.worker_id, capability=request.capability,
            status=self.status() if matching else "ABSENT",
            correlation_id=request.correlation_id,
            artifacts={"assets": sorted(matching)},
        )
