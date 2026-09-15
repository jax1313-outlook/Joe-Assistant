"""The workers. Three of them, plus Library, which the Publisher pulls from.

Each is a thin, bounded adapter over a program that lives in its own repository.
The adapter's job is to answer in the contract's shape and to be honest about
whether the program behind it is actually there -- an adapter whose package is
not importable answers UNCONFIGURED and returns nothing else, rather than
producing a plausible result from nothing.
"""

from worker_bus.workers.intelligence import IntelligenceWorker
from worker_bus.workers.library import LibraryWorker
from worker_bus.workers.publisher import PublisherWorker
from worker_bus.workers.joe import JoeWorker

__all__ = ["IntelligenceWorker", "LibraryWorker", "PublisherWorker", "JoeWorker"]
