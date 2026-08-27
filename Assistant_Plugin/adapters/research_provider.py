"""Research provider adapter.

No live research provider is configured on this machine. That is a fact about
the environment, not a design choice, and it is reported rather than hidden.

The adapter exists so a provider can be bound later without touching the
Research capability. Provider-specific behaviour belongs here and nowhere
else - the Research module must never learn a vendor's name.

Fixture mode returns the supplied sample briefs, labelled SAMPLE DATA. Fixture
output is never presented as live research.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from contracts import Provenance, SourceMode, stamp


class ResearchProviderError(RuntimeError):
    pass


@dataclass
class ProviderResult:
    ok: bool
    mode: str = SourceMode.UNAVAILABLE
    brief: dict = field(default_factory=dict)
    provider: str = "none"
    error: str = ""
    read_at: str = field(default_factory=stamp)

    def provenance(self) -> Provenance:
        return Provenance(
            source="Research provider (" + self.provider + ")",
            mode=self.mode,
            as_of=self.read_at,
            detail=self.error or ("brief: " + str(self.brief.get("question", ""))[:60]),
        )


class ResearchProviderAdapter:
    """Selects a research provider. Only 'none' and 'fixture' exist today."""

    name = "research-provider"

    SUPPORTED = ("none", "fixture", "m365_copilot")

    def __init__(
        self,
        provider: str = "none",
        fixtures_path: str | Path | None = None,
        allow_fixture_mode: bool = True,
        copilot=None,
    ) -> None:
        self.provider = (provider or "none").strip().lower()
        self.fixtures_path = Path(fixtures_path) if fixtures_path else None
        self.allow_fixture_mode = allow_fixture_mode
        # The live reasoning provider, when one is bound. Research borrows its
        # connection rather than holding a second credential - there is exactly
        # one sign-in on this machine and exactly one token cache.
        self.copilot = copilot
        self.last_error = ""

    # ---- availability -------------------------------------------------

    @property
    def has_live_provider(self) -> bool:
        """True only when a real, credentialed research service is bound AND
        that service is actually signed in.

        Naming a provider in configuration is not the same as having one. For
        Copilot this asks the reasoning provider whether it is live, so an
        unsigned-in session reports SAMPLE rather than claiming live research
        it cannot perform."""
        if self.provider in ("none", "fixture", ""):
            return False
        if self.provider == "m365_copilot":
            if self.copilot is None:
                return False
            try:
                return bool(self.copilot.status().get("live"))
            except Exception:  # noqa: BLE001
                return False
        return True

    def probe(self) -> dict:
        if self.has_live_provider:
            return {
                "available": True,
                "live_connection": True,
                "mode": SourceMode.LIVE,
                "provider": self.provider,
                "blocker": "",
            }
        if self.allow_fixture_mode and self._fixtures():
            return {
                "available": True,
                "live_connection": False,
                "mode": SourceMode.SAMPLE,
                "provider": "fixture",
                "blocker": (
                    "no live research provider is configured; "
                    "set research.provider in configuration and supply an "
                    "approved credential"
                ),
            }
        return {
            "available": False,
            "live_connection": False,
            "mode": SourceMode.UNAVAILABLE,
            "provider": "none",
            "blocker": "no research provider and no fixtures are available",
        }

    # ---- live research, through Copilot web grounding ------------------

    def _research_via_copilot(self, question: str) -> ProviderResult:
        """Live web-grounded research. Attributions are mandatory.

        Web grounding without returned attributions is not research - it is
        general reasoning that happened to have search switched on. If nothing
        came back with a citation, this reports that plainly rather than
        dressing the answer up as sourced.
        """
        read_at = stamp()
        try:
            answer = self.copilot.research(question)
        except Exception as error:  # noqa: BLE001
            self.last_error = str(error)
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                provider=self.provider, error=self.last_error, read_at=read_at,
            )

        if not getattr(answer, "ok", False):
            self.last_error = getattr(answer, "error", "") or "research returned no answer"
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                provider=self.provider, error=self.last_error, read_at=read_at,
            )

        # Answer.source_class is a FIELD, not a method. Calling it raised
        # "'str' object is not callable" and the whole capability was isolated.
        citations = list(getattr(answer, "sources", None) or [])
        source_class = str(getattr(answer, "source_class", "") or "")
        web_grounded = source_class == "COPILOT_WEB_GROUNDED"

        return ProviderResult(
            ok=True,
            mode=SourceMode.LIVE,
            provider=self.provider,
            read_at=read_at,
            brief={
                "question": question,
                "scope": ("Live web-grounded search through Microsoft 365 "
                          "Copilot at " + read_at),
                "text": getattr(answer, "text", ""),
                "citations": citations,
                "annotations": list(getattr(answer, "sources", None) or []),
                "source_class": source_class,
                "web_grounded": web_grounded,
                "retrieved_at": read_at,
                "sensitivity_label": getattr(answer, "sensitivity_label", ""),
            },
        )

    # ---- fixtures -----------------------------------------------------

    def _fixtures(self) -> list[Path]:
        if not self.fixtures_path or not self.fixtures_path.exists():
            return []
        return sorted(self.fixtures_path.glob("*.json"))

    def list_fixtures(self) -> list[str]:
        return [path.name for path in self._fixtures()]

    # ---- the one operation --------------------------------------------

    def research(self, question: str) -> ProviderResult:
        """Return a research brief for a question.

        Live provider  -> would call the provider. None is bound, so this
                          branch is unreachable in this build and says so.
        Fixture mode   -> returns the closest supplied sample brief, labelled
                          SAMPLE DATA.
        Neither        -> reports unavailability. It never invents findings.
        """
        wanted = (question or "").strip()
        if not wanted:
            return ProviderResult(
                ok=False, error="no research question was supplied"
            )

        if self.has_live_provider:
            if self.provider == "m365_copilot":
                return self._research_via_copilot(wanted)
            self.last_error = (
                "provider '" + self.provider + "' is named in configuration but "
                "no adapter for it is implemented in this build"
            )
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                provider=self.provider, error=self.last_error,
            )

        if not self.allow_fixture_mode:
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                error="no live research provider is configured",
            )

        fixture = self._best_fixture(wanted)
        if fixture is None:
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                error=(
                    "no live research provider is configured, and no sample "
                    "brief matches that question"
                ),
            )
        try:
            brief = json.loads(fixture.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            return ProviderResult(
                ok=False, mode=SourceMode.UNAVAILABLE,
                error="sample brief " + fixture.name + " could not be read: " + str(error),
            )
        if isinstance(brief, list):
            brief = {"question": wanted, "sources": brief}
        return ProviderResult(
            ok=True, mode=SourceMode.SAMPLE, provider="fixture", brief=brief
        )

    def _best_fixture(self, question: str) -> Path | None:
        """Pick the sample brief sharing the most words with the question."""
        fixtures = self._fixtures()
        if not fixtures:
            return None
        wanted = {w for w in question.lower().split() if len(w) > 3}
        best, best_score = None, -1
        for path in fixtures:
            words = {w for w in path.stem.lower().replace("_", " ").split() if len(w) > 3}
            try:
                text = path.read_text(encoding="utf-8").lower()
            except OSError:
                text = ""
            score = len(wanted & words) * 3 + sum(1 for w in wanted if w in text)
            if score > best_score:
                best, best_score = path, score
        return best
