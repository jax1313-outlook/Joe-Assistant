"""Assistant Research - Workstream 5.

Research, analysis, findings, recommendations, uncertainties, source reporting.

Research may recommend. Research may not approve, decide, or alter doctrine.

This package imports nothing outside itself and nothing outside folder 5.
It has no network access and fetches nothing; sources are supplied to it.
"""

__version__ = "1.0.0"

from .sources import Claim, KIND_STANDING, Source, SourceError, SourceKind
from .analysis import (
    CONFIDENCE_MEANING,
    Confidence,
    Finding,
    analyze,
    analyze_topic,
    topics_in,
)
from .authority import (
    AUTHORITY_STATEMENT,
    FORBIDDEN_PHRASES,
    AuthorityError,
    Recommendation,
    assert_no_authority_claim,
    find_authority_claims,
)
from .record import (
    RecordError,
    ResearchRecord,
    load_brief,
    load_sources,
    record_from_brief,
    resolve_data_root,
)

__all__ = [
    "__version__",
    "Claim", "KIND_STANDING", "Source", "SourceError", "SourceKind",
    "CONFIDENCE_MEANING", "Confidence", "Finding", "analyze", "analyze_topic",
    "topics_in",
    "AUTHORITY_STATEMENT", "FORBIDDEN_PHRASES", "AuthorityError",
    "Recommendation", "assert_no_authority_claim", "find_authority_claims",
    "RecordError", "ResearchRecord", "load_brief", "load_sources",
    "record_from_brief", "resolve_data_root",
]
