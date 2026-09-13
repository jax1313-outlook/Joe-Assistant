"""The assembly point: a bus with real, read-only views onto Dispatch.

Until this module existed, `WorkerBus` was constructed in exactly one place --
`Workers/tests/test_worker_bus.py` -- and every worker was instantiated only
there. Thirty-nine tests passed and nothing in Dispatch or the Assistant Plugin
ever built one. Intelligence, Publisher and Joe could not perform a single
constitutional duty against a real load, not because their logic was wrong but
because nothing called them.

That is the third time this exact shape has turned up in this programme: the
capacity engine (1,861 lines, no caller), the proof-path commands (documented,
non-existent), and now the worker bus. Passing tests are what make it
convincing.

Three rules this module exists to keep, and each is enforced rather than
described.

**Read-only, structurally.** `CLAUDE.md` §5.4: "No direct Dispatch write
authority may be granted to Assistant." `DispatchReader` exposes nine read
methods and holds no reference to anything that writes. It is not a wrapper
around `store` that promises to behave -- it names the functions it may call, so
granting a write would mean editing this file, in public, on purpose.

**Degrades, never fails to start.** §5.4 again: "Degradation is permitted.
Incapacity is not." On a machine with no Dispatch importable, `build_bus()`
still returns a working bus whose workers report `UNCONFIGURED` and say why. It
does not raise, because a plug-in that cannot start is worse than one that can
say it has nothing to read.

**One place to audit.** Everything the Assistant can see about Dispatch passes
through `READ_METHODS` below. A reviewer asking "what can Joe see?" reads one
tuple.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from worker_bus.audit import AuditLog
from worker_bus.bus import WorkerBus
from worker_bus.workers.intelligence import IntelligenceWorker
from worker_bus.workers.joe import JoeWorker
from worker_bus.workers.library import LibraryWorker
from worker_bus.workers.publisher import PublisherWorker

#: Every Dispatch function the Assistant may call, and the reader method that
#: calls it. Adding a row is the only way to widen what a worker can see, and
#: `test_worker_host.py` asserts that none of them is a write.
READ_METHODS: tuple[tuple[str, str], ...] = (
    ("get_load", "store.get_load"),
    ("get_rate_confirmation", "store.get_rate_confirmation"),
    ("list_pods", "store.list_pods"),
    ("list_evidence", "store.list_evidence"),
    ("list_milestones", "store.list_milestones"),
    ("list_exceptions", "store.list_exceptions"),
    ("get_driver", "store.get_driver"),
    ("lane_history", "store.get_lane_history"),
    ("broker_record", "store.get_broker_scorecards"),
)


#: Where the Assistant Plugin lives, relative to this file.
#: Workers/worker_bus/host.py -> Workers/ -> repo root -> Assistant_Plugin/
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent / "Assistant_Plugin"


def ensure_plugin_importable() -> bool:
    """Put the Assistant Plugin on the import path, if it is here.

    Joe imports `conversation.readback` as a top-level package, which only
    resolves when `Assistant_Plugin/` is on `sys.path`. Under pytest the repo's
    `conftest.py` arranges that. Nothing arranged it anywhere else, so Joe
    worked in the test suite and raised `ModuleNotFoundError` the first time he
    was asked to read a load from a real host -- which is precisely the failure
    this whole module exists to stop being invisible.

    Doing it here rather than inside Joe keeps the coupling in one declared
    place: a reader asking "why is Assistant_Plugin on the path" finds this
    docstring, not a bare sys.path line halfway down a worker.

    Returns whether the plug-in is present. Absent is not an error -- Dispatch
    runs without its plug-ins by §5.4 -- and the caller reports it as status.
    """
    if not _PLUGIN_ROOT.is_dir():
        return False
    if str(_PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(_PLUGIN_ROOT))
    return True


#: Where the Library repository's `src/` is. `DISPATCH_LIBRARY_SRC` names it; without that, a
#: checkout beside this one: Joe-Assistant/Workers/worker_bus/host.py -> ... -> work/ -> Library/src/
_LIBRARY_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "Library" / "src"

#: The persistent Library catalog. When set, the bus holds the catalog-backed Library and
#: everything placed in it survives the process. Unset, the Library is the in-memory shelf.
LIBRARY_CATALOG_ENV = "DISPATCH_LIBRARY_CATALOG"


def _library_root() -> Path:
    named = os.environ.get("DISPATCH_LIBRARY_SRC", "").strip()
    return Path(named) if named else _LIBRARY_ROOT


def ensure_library_importable() -> bool:
    """Put `dispatch_library` on the import path, if the Library repo is here.

    The Library is its own repository with its own remote -- THE MIKE RULE keeps
    it liftable -- so this is a path, not a dependency. Its absence is not an
    error: `build_bus()` falls back to the in-memory shelf and LIBRARY reports
    UNCONFIGURED, which is the true answer on a machine with no Library.

    Returns whether it is present.
    """
    root = _library_root()
    if not root.is_dir():
        return False
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return True


#: One Library per process. See library_service().
_LIBRARY_SERVICE = None


def library_service():
    """The process's `LibraryService`, or None if the Library is not here.

    **One service per process, not one per bus.** Two services in one process
    must never be two shelves: a template ingested through one would be
    invisible to the other, which is the defect Phase A found on its first run.

    **Persistent when configured.** With `DISPATCH_LIBRARY_CATALOG` set, this is
    the catalog-backed Library (`dispatch_library.catalog`, schema version 2) bound
    to `DISPATCH_MEMORY_ROOT`, and a template accepted in one command is there for
    the next one -- the limit KNOWN_LIMITATIONS.md section 14 recorded is closed
    for that configuration. Without it, the Library is the in-memory shelf and
    still empties when the process exits, which is reported, not hidden:
    `library_persistent()` says which one this process holds.
    """
    global _LIBRARY_SERVICE
    if _LIBRARY_SERVICE is not None:
        return _LIBRARY_SERVICE
    if not ensure_library_importable():
        return None
    try:
        if os.environ.get(LIBRARY_CATALOG_ENV, "").strip():
            from dispatch_library.catalog import open_configured_library

            _LIBRARY_SERVICE = open_configured_library(consumer_role="WORKER_BUS")
        else:
            from dispatch_library.service import LibraryService

            _LIBRARY_SERVICE = LibraryService()
    except ImportError:  # absence is a status, never a crash
        return None
    return _LIBRARY_SERVICE


def library_persistent() -> bool:
    """Whether this process's Library remembers across processes."""
    service = library_service()
    return service is not None and hasattr(service, "catalog")


class DispatchUnavailable(RuntimeError):
    """Dispatch could not be imported. Reported, never raised at a worker."""


@dataclass(frozen=True)
class DispatchReader:
    """A read-only view of Dispatch for the workers.

    Frozen, and every method is a query. There is deliberately no `create_`,
    `update_`, `save_` or `delete_` anything: a worker that wanted to write
    would have to add a method here, which is a visible act in a reviewed file
    rather than an accident inside a worker.
    """

    def _store(self):
        try:
            from dispatch import store
        except Exception as exc:  # noqa: BLE001 - reported as a status, not raised
            raise DispatchUnavailable(str(exc)) from exc
        return store

    # -- the nine the workers actually call -------------------------------

    def get_load(self, load_id):
        return self._store().get_load(load_id)

    def get_rate_confirmation(self, load_id):
        return self._store().get_rate_confirmation(load_id)

    def list_pods(self, load_id):
        return self._store().list_pods(load_id)

    def list_evidence(self, load_id):
        return self._store().list_evidence(load_id)

    def list_milestones(self, load_id):
        return self._store().list_milestones(load_id)

    def list_exceptions(self, load_id):
        return self._store().list_exceptions(load_id=load_id)

    def get_driver(self, driver_id):
        return self._store().get_driver(driver_id)

    def lane_history(self, origin, destination, *, exclude_load_id: str = ""):
        return self._store().get_lane_history(
            origin, destination, exclude_load_id=exclude_load_id
        )

    def broker_record(self, broker):
        """The scorecard row for one broker, or None.

        A row and not a verdict: `assess_broker` reports what the record says
        and the constitution forbids it from scoring. Returning the raw row
        keeps that judgement where it belongs -- with whoever reads it.
        """
        wanted = (broker or "").strip().casefold()
        if not wanted:
            return None
        for row in self._store().get_broker_scorecards():
            if str(row.get("broker_shipper", "")).strip().casefold() == wanted:
                return row
        return None


def dispatch_available() -> bool:
    """Whether Dispatch can be read from this process at all."""
    try:
        DispatchReader()._store()
    except DispatchUnavailable:
        return False
    return True


def build_bus(*, reader=None, reasoner=None, assets=None, audit=None) -> WorkerBus:
    """The bus a host runs: four workers, real reads, no write path.

    `reader` is injectable so a test, a rehearsal, or a second profile can hand
    in its own view. Left out, it is a real `DispatchReader` when Dispatch is
    importable and `None` when it is not -- and `None` is not a failure, it is
    what makes each worker report `UNCONFIGURED` and say it cannot see Dispatch
    on this machine.

    `reasoner` stays `None` by default. Joe reads back facts without one; he
    answers open questions only with one, and reports `CONFIGURED` rather than
    `LIVE` until it is supplied. Defaulting one in would be claiming a
    capability nobody configured.
    """
    ensure_plugin_importable()

    if reader is None and dispatch_available():
        reader = DispatchReader()

    bus = WorkerBus(audit=audit if audit is not None else AuditLog())
    bus.register(IntelligenceWorker(reader=reader))
    bus.register(PublisherWorker(reader=reader))
    bus.register(JoeWorker(reader=reader, reasoner=reasoner))
    # A real Library when one is reachable; the in-memory shelf otherwise. An
    # explicit `assets` argument still wins, so a test can pin the shelf without
    # depending on whether a sibling repository happens to be checked out.
    bus.register(
        LibraryWorker(assets=assets or {}, service=None if assets else library_service())
    )
    return bus


def describe() -> dict:
    """What a host can honestly say about the workers before running any.

    Status words are the eight in `CLAUDE.md` §6 and mean what they say: with no
    Dispatch on this machine every worker reads `UNCONFIGURED`, and that is the
    truth rather than a failure.
    """
    bus = build_bus()
    return {
        "dispatch_readable": dispatch_available(),
        "plugin_present": ensure_plugin_importable(),
        "library_present": ensure_library_importable(),
        "library_persistent": library_persistent(),
        # bus.roster() is the bus's own public answer to "who is registered and
        # what can they do". Reaching into its private dict to build a second
        # version of that would be two answers to one question.
        "workers": bus.roster(),
    }
