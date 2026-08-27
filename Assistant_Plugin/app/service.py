"""AssistantService - the application core.

Owns: routing, capability dispatch, record lifecycle, status, and the
governance gate every response passes through.

Does not own: business logic of any capability. Each bounded component keeps
its own responsibility and is reached through an adapter or its own package.

The UI holds no logic. It renders what this service returns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import bootstrap  # noqa: F401  - installs component import paths
from .config import Config, ConfigError, assert_within_plugin
from .logbook import Logbook
from .reasoning_capabilities import ReasoningCapabilities
from .router import Route, route as route_request

from contracts import (
    ActionRequest,
    AssistantRequest,
    AssistantResponse,
    Capability,
    CapabilityStatus,
    Provenance,
    SourceMode,
    stamp,
    ReasoningMode,
    SourceClass,
)
from governance import AUTHORITY_STATEMENT, Governor

from adapters import (
    DispatchPort,
    LibraryFsAdapter,
    OutlookComAdapter,
    ReasoningProviderAdapter,
    ReasoningStatus,
    ResearchProviderAdapter,
    SapiVoiceAdapter,
)

NO_REASONING_PROVIDER = (
    "No reasoning provider is connected to JOE, so I cannot compose "
    "an original answer. What I can do is search approved Library material, "
    "read Outlook read-only, report research from supplied briefs, and hold "
    "this interaction under the retention rules."
)


@dataclass
class Interaction:
    """One exchange, as the UI sees it. Backed by a Memory record."""

    record_id: str
    request: str
    response: AssistantResponse
    created_at: str = field(default_factory=stamp)

    @property
    def summary(self) -> str:
        return (self.request or "")[:60]


def _one_line(item: dict) -> str:
    """One Outlook item, as a person would read it."""
    when = item.get("start") or item.get("received") or ""
    what = item.get("subject") or item.get("display_name") or item.get("name") or ""
    who = item.get("sender") or item.get("email") or ""
    parts = [str(when)[:20], str(what)[:56], str(who)[:32]]
    return "  ".join(p for p in parts if p)


class AssistantService(ReasoningCapabilities):
    """Everything JOE can do, behind one object.

    Reasoning-backed capabilities (summarize, draft, procedure) live in
    ReasoningCapabilities so this file stays about routing and lifecycle.
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self.config.ensure_runtime_dirs()
        self.log = Logbook(self.config.logs)
        self.governor = Governor(
            stale_after_minutes=int(
                self.config.get("governance", "stale_after_minutes", 15)
            )
        )
        self.started_at = stamp()

        # ---- packaged components ------------------------------------
        from assistant_memory.retention import RetentionEngine
        from assistant_memory.store import MemoryStore

        memory_root = assert_within_plugin(self.config.runtime_data / "memory")
        memory_root.mkdir(parents=True, exist_ok=True)
        self.memory = RetentionEngine(
            store=MemoryStore(memory_root),
            retention_hours=float(self.config.get("memory", "retention_hours", 3)),
        )

        # ---- adapters ------------------------------------------------
        library_cfg = self.config.section("library")
        self.library = LibraryFsAdapter(
            sources=[
                {
                    "name": s["name"],
                    "path": str(s["path"]),
                    "kind": s["kind"],
                }
                for s in self.config.library_sources()
            ],
            max_documents=int(library_cfg.get("max_documents", 2000)),
        )

        outlook_cfg = self.config.section("outlook")
        self.outlook = OutlookComAdapter(
            enabled=bool(outlook_cfg.get("enabled", True)),
            max_items=int(outlook_cfg.get("max_items", 60)),
            timeout_seconds=int(outlook_cfg.get("timeout_seconds", 90)),
            calendar_window_days=int(outlook_cfg.get("calendar_window_days", 14)),
            account=str(outlook_cfg.get("account", "")),
        )

        # Email Connection Layer v1. Replaces the single account string:
        # mail, calendar, and contacts are chosen separately, because no
        # mailbox is assumed to hold all three.
        from adapters.mailbox_registry import from_config as mailboxes_from_config

        self.mailboxes = mailboxes_from_config(
            outlook_cfg,
            logger=lambda event, detail: self.log.write(event, "-", detail),
            timeout_seconds=int(outlook_cfg.get("timeout_seconds", 90)),
        )

        research_cfg = self.config.section("research")
        self.research = ResearchProviderAdapter(
            provider=str(research_cfg.get("provider", "none")),
            fixtures_path=self.config.resolve_path(
                str(research_cfg.get("fixtures_path", "research/fixtures"))
            ),
            allow_fixture_mode=bool(research_cfg.get("allow_fixture_mode", True)),
        )

        voice_cfg = self.config.section("voice")
        # Microphone enumeration and diagnostics. Read-only: JOE never changes
        # the Windows default device.
        from adapters.microphones import MicrophoneAdapter

        self.microphones = MicrophoneAdapter(
            preferred=str(voice_cfg.get("preferred_microphone", "")),
            logger=lambda event, detail: self.log.write(event, "-", detail),
        )
        self.voice = SapiVoiceAdapter(
            enabled=bool(voice_cfg.get("enabled", True)),
            voice_name=str(voice_cfg.get("voice_name", "")),
            rate=int(voice_cfg.get("rate", 0)),
        )
        self.speak_replies = bool(voice_cfg.get("speak_replies", False))
        self.driver_mode = bool(voice_cfg.get("driver_mode", False))
        self.max_spoken_words = int(voice_cfg.get("max_spoken_words", 60))

        reasoning_cfg = self.config.section("reasoning")
        provider_name = str(reasoning_cfg.get("provider", "none")).strip().lower()
        backend = None
        self.copilot_auth = None
        if provider_name == "m365_copilot":
            from adapters import CopilotAuth, M365CopilotProvider

            copilot_cfg = reasoning_cfg.get("copilot") or {}
            # The token cache lives inside the plugin, encrypted by Windows
            # DPAPI. Nothing readable is ever written.
            cache_dir = assert_within_plugin(self.config.runtime_data / "auth")
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.copilot_auth = CopilotAuth(
                tenant_id=str(copilot_cfg.get("tenant_id", "")),
                client_id=str(copilot_cfg.get("client_id", "")),
                cache_dir=cache_dir,
            )
            backend = M365CopilotProvider(
                auth=self.copilot_auth,
                time_zone=str(copilot_cfg.get("time_zone", "America/New_York")),
                timeout_seconds=int(copilot_cfg.get("timeout_seconds", 120)),
                web_enabled=bool(copilot_cfg.get("web_enabled_default", False)),
                max_context_chars=int(reasoning_cfg.get("max_context_chars", 12000)),
            )
        self.reasoning = ReasoningProviderAdapter(
            provider=provider_name,
            model=str(reasoning_cfg.get("model", "")),
            endpoint=str(reasoning_cfg.get("endpoint", "")),
            timeout_seconds=int(reasoning_cfg.get("timeout_seconds", 60)),
            max_context_chars=int(reasoning_cfg.get("max_context_chars", 12000)),
            backend=backend,
        )

        # Research borrows the reasoning provider's connection rather than
        # holding a second credential. There is one sign-in on this machine and
        # one token cache; a separate research credential would be a second
        # thing to keep secure for no gain. Bound after the backend exists.
        if backend is not None:
            self.research.copilot = backend

        dispatch_cfg = self.config.section("dispatch")
        self.dispatch = DispatchPort(
            interface=str(dispatch_cfg.get("interface", "none")),
            endpoint=str(dispatch_cfg.get("endpoint", "")),
            enabled=bool(dispatch_cfg.get("enabled", False)),
        )

        self.interactions: list[Interaction] = []
        self.selected_id: str | None = None
        self.log.event("service_started", "Assistant service started")

    # ================================================================
    # Asking
    # ================================================================

    def ask(self, text: str, channel: str = "text") -> Interaction:
        """The whole interaction path: route, answer, record, govern."""
        request = AssistantRequest(text=(text or "").strip(), channel=channel)
        if not request.text:
            raise ValueError("nothing was asked")

        chosen = route_request(request.text)
        request.driver_mode = chosen.driver_mode or self.driver_mode

        try:
            response = self._dispatch_capability(request, chosen)
        except Exception as error:  # a failing capability must not close the app
            self.log.error("capability_failed", chosen.capability, str(error))
            response = AssistantResponse(
                capability=chosen.capability,
                answer=(
                    "That capability failed. Everything else is still working."
                ),
                written=(
                    "The " + chosen.capability + " capability raised an error and "
                    "was isolated. No operational fact was invented, and nothing "
                    "was changed.\n\nDetail has been written to the log."
                ),
                ok=False,
                failure=type(error).__name__,
                notices=["A capability failed. The rest of JOE is unaffected."],
            )

        response = self.governor.enforce(response)
        response = self._shape_for_driver(response, request.driver_mode)

        # A retention command acts on the interaction Mike already has
        # selected. It is not itself a new interaction, and it must not move
        # the selection - otherwise "Save this. Print this." would put the two
        # commands on two different records.
        if chosen.capability == Capability.RETENTION:
            target = self.selected_id or ""
            self.log.event(
                "retention_command",
                chosen.retention_intent + " | " + request.text[:80],
                target,
            )
            return Interaction(
                record_id=target, request=request.text, response=response
            )

        record = self.memory.create(
            driver_request=request.text,
            assistant_response=response.written,
            source_channel=channel,
        )
        interaction = Interaction(
            record_id=record.record_id, request=request.text, response=response
        )
        self.interactions.append(interaction)
        self.selected_id = record.record_id
        self.log.event(
            "interaction",
            chosen.capability + " | " + request.text[:120],
            record.record_id,
        )
        return interaction

    def _dispatch_capability(
        self, request: AssistantRequest, chosen: Route
    ) -> AssistantResponse:
        handlers = {
            Capability.RETENTION: self._handle_retention,
            Capability.LIBRARY: self._handle_library,
            Capability.RESEARCH: self._handle_research,
            Capability.OPERATIONS: self._handle_operations,
            Capability.EXPLAIN: self._handle_explain,
            Capability.HELP: self._handle_help,
            Capability.ANSWER: self._handle_answer,
            Capability.SUMMARIZE: self._handle_summarize,
            Capability.DRAFT: self._handle_draft,
            Capability.PROCEDURE: self._handle_procedure,
        }
        return handlers[chosen.capability](request, chosen)

    # ================================================================
    # Capabilities
    # ================================================================

    def _handle_help(self, request, chosen) -> AssistantResponse:
        lines = [
            "Ask in ordinary words. Some things I can do:",
            "",
            "  What matters about tomorrow's run?      read your calendar",
            "  Find the broker packet                  search approved Library",
            "  Explain that in plain language          explain from Library",
            "  Research the road restriction           research from briefs",
            "  Save this                               keep this interaction",
            "  Level 3 this under Ideas                request a formal record",
            "  Print this                              mark it print ready",
            "  Delete this                             remove it",
            "",
            AUTHORITY_STATEMENT,
        ]
        return AssistantResponse(
            capability=Capability.HELP,
            answer="Ask in ordinary words - here is what I can do.",
            written="\n".join(lines),
        )

    def _handle_library(self, request, chosen) -> AssistantResponse:
        subject = chosen.subject or request.text
        probe = self.library.probe()
        if not probe["available"]:
            return AssistantResponse(
                capability=Capability.LIBRARY,
                answer="No approved Library location is configured.",
                written=(
                    "No approved Library location is configured or reachable, so "
                    "there was nothing to search.\n\n"
                    "Add a path under library.sources in "
                    "configuration/joe.config.json."
                ),
                ok=False,
                failure="no library source",
                provenance=[Provenance(source="Library", mode=SourceMode.UNAVAILABLE)],
            )

        hits = self.library.search(subject, limit=6)
        if not hits:
            return AssistantResponse(
                capability=Capability.LIBRARY,
                answer='Nothing in the Library matches "' + subject + '".',
                written=(
                    'I searched the configured Library locations for "'
                    + subject
                    + '" and found nothing.\n\n'
                    "I have not invented a document and have not guessed at a "
                    "near match.\n\nSearched:\n"
                    + "\n".join(
                        "  - " + s["name"] + "  (" + str(s["indexed"]) + " documents)"
                        for s in probe["sources"]
                    )
                ),
                provenance=[
                    Provenance(
                        source="Library / " + s["name"],
                        mode=s["mode"],
                        detail=str(s["indexed"]) + " documents searched",
                    )
                    for s in probe["sources"]
                ],
            )

        top = hits[0]
        body = [
            "Found " + str(len(hits)) + " match(es) for \"" + subject + "\".",
            "",
        ]
        for index, hit in enumerate(hits, start=1):
            label = "COMPANY LIBRARY" if hit["is_company"] else "SAMPLE DATA"
            body.append(
                str(index) + ". " + hit["title"] + "   [" + label + "]"
            )
            body.append("     " + hit["source_name"] + " / " + hit["relative_path"])
            for snippet in hit["snippets"][:2]:
                body.append("     > " + snippet)
            body.append("")
        return AssistantResponse(
            capability=Capability.LIBRARY,
            answer=(
                top["title"]
                + " - "
                + top["source_name"]
                + "/"
                + top["relative_path"]
            ),
            written="\n".join(body),
            findings=[h["title"] for h in hits],
            citations=[h["reference"] for h in hits],
            provenance=[self.library.provenance_for(hit) for hit in hits[:4]],
        )

    def _handle_research(self, request, chosen) -> AssistantResponse:
        subject = chosen.subject or request.text
        probe = self.research.probe()
        result = self.research.research(subject)

        if not result.ok:
            return AssistantResponse(
                capability=Capability.RESEARCH,
                answer="Research provider is unavailable. No live research was performed.",
                written=(
                    "No live research was performed.\n\n"
                    + result.error
                    + "\n\nA research provider adapter exists and is ready to be "
                    "bound. Until one is approved and configured, I will not "
                    "present anything as research."
                ),
                ok=False,
                failure="no research provider",
                provenance=[result.provenance()],
                uncertainty="Nothing was researched. Nothing here is established.",
            )

        # Live Copilot research returns prose plus attributions, not the
        # fixture brief shape. Two different things, reported two different
        # ways - forcing live output through the fixture renderer would have
        # invented findings and confidences nobody returned.
        if result.brief.get("text") is not None:
            return self._live_research_response(subject, result)

        from assistant_research.record import record_from_brief

        research_record = record_from_brief(result.brief)
        data = research_record.to_dict()

        body = [
            "RESEARCH - " + ("LIVE" if result.mode == SourceMode.LIVE else "SAMPLE DATA"),
            "",
            "Question:  " + data["question"],
            "Scope:     " + (data["scope"] or "(not stated)"),
            "",
            "FINDINGS",
        ]
        for finding in data["findings"]:
            body.append("")
            body.append("  " + finding["topic"] + "   [" + finding["confidence"] + "]")
            for entry in finding["supporting"]:
                body.append("    supports:    " + entry["statement"])
                body.append("                 " + entry["citation"])
            for entry in finding["contradicting"]:
                body.append("    CONTRADICTS: " + entry["statement"])
                body.append("                 " + entry["citation"])
            body.append("    uncertainty: " + finding["uncertainty"])

        recommendation = data.get("recommendation") or {}
        body += ["", "OPERATIONAL CONSEQUENCES"]
        consequences = [
            f["topic"] + " is " + f["confidence"].lower()
            for f in data["findings"]
        ]
        body += ["  - " + c for c in consequences] or ["  (none recorded)"]
        body += ["", "RECOMMENDATION"]
        if recommendation:
            body.append("  " + recommendation["statement"])
            if recommendation.get("rationale"):
                body.append("  Because: " + recommendation["rationale"])
            for question in recommendation.get("open_questions", []):
                body.append("  Open question: " + question)
            body.append("")
            body.append(
                "  Recommendation only. approved=False decided=False acted_on=False"
            )
            body.append("  Decision required from: Mike Zachary")
        else:
            body.append("  None offered.")

        uncertainties = "; ".join(
            u["topic"] + ": " + u["confidence"] for u in data["uncertainties"]
        )
        return AssistantResponse(
            capability=Capability.RESEARCH,
            answer=(
                recommendation.get("statement")
                or (data["findings"][0]["topic"] if data["findings"] else "No findings.")
            ),
            written="\n".join(body),
            findings=[f["topic"] for f in data["findings"]],
            citations=list(data["citations"]),
            uncertainty=uncertainties,
            recommendation=recommendation.get("statement", ""),
            provenance=[result.provenance()],
        )

    # Web research is not a substitute for the official channels, and saying
    # so is part of the report rather than a footnote.
    OFFICIAL_SOURCE_NOTICE = (
        "Web research does not replace official DOT or 511 monitoring. Treat "
        "this as background, not as a road status."
    )

    def _live_research_response(self, subject, result) -> AssistantResponse:
        """The mission's research report shape, over live Copilot grounding.

        Every section is present even when empty, because a missing section
        reads as "nothing to report" while an empty one reads as "asked, and
        nothing came back". Those are different facts.
        """
        from app.reasoning_capabilities import headline

        brief = result.brief
        text = str(brief.get("text") or "").strip()
        citations = [str(c) for c in (brief.get("citations") or [])]
        annotations = [str(a) for a in (brief.get("annotations") or [])]
        web = bool(brief.get("web_grounded"))
        retrieved = str(brief.get("retrieved_at") or result.read_at)
        short = headline(text, limit=240)

        body = [
            "RESEARCH - LIVE" if web else "RESEARCH - LIVE REASONING, NOT WEB-GROUNDED",
            "",
            "QUESTION",
            "  " + subject,
            "",
            "RESEARCH SCOPE",
            "  " + str(brief.get("scope") or "(not stated)"),
            "",
            "RETRIEVAL TIME",
            "  " + retrieved,
            "",
            "SOURCES CONSULTED",
        ]
        body += ["  - " + c for c in citations] or [
            "  (none returned)",
            "  Without a returned source this is general reasoning with search "
            "enabled, not web research.",
        ]
        body += ["", "ATTRIBUTIONS"]
        body += ["  - " + a for a in annotations] or ["  (none returned)"]
        body += ["", "CONFIRMED FINDINGS", ""]
        body += ["  " + line for line in text.splitlines()] or ["  (none)"]
        body += [
            "",
            "UNCONFIRMED INFORMATION",
            "  Anything above without a source line beside it is unconfirmed.",
            "",
            "SOURCE CONFLICTS",
            "  " + ("Not separately assessed. Where sources disagree, the "
                    "disagreement is visible in the findings above."
                    if citations else "No sources were returned to conflict."),
            "",
            "OPERATIONAL CONSEQUENCES",
            "  " + self.OFFICIAL_SOURCE_NOTICE,
            "",
            "UNCERTAINTY",
            "  Retrieved at " + retrieved + ". Conditions change after retrieval.",
            "  " + ("Web grounding was used." if web
                   else "WEB GROUNDING WAS NOT CONFIRMED for this answer."),
            "",
            "RECOMMENDATION",
            "  Check the official source before acting on anything above.",
            "  Recommendation only. approved=False decided=False acted_on=False",
            "  Decision required from: Mike Zachary",
            "",
            "SHORT SPOKEN ANSWER",
            "  " + short,
        ]

        response = AssistantResponse(
            capability=Capability.RESEARCH,
            answer=short,
            written="\n".join(body),
            spoken_summary=short,
            citations=citations,
            findings=citations[:6],
            recommendation="Check the official source before acting on this.",
            uncertainty=(
                "Retrieved at " + retrieved + "; conditions change after retrieval."
            ),
            reasoning_mode=ReasoningMode.WEB_GROUNDED_RESEARCH,
            provenance=[
                Provenance(
                    source="Microsoft 365 Copilot (web-grounded research)",
                    mode=SourceMode.LIVE,
                    as_of=retrieved,
                    source_class=(
                        SourceClass.COPILOT_WEB_GROUNDED if web
                        else SourceClass.COPILOT_GENERAL_REASONING
                    ),
                    detail=str(len(citations)) + " source(s) returned",
                )
            ],
        )
        response.add_notice(self.OFFICIAL_SOURCE_NOTICE)
        if not citations:
            response.add_notice(
                "No source attributions came back, so this is not web research. "
                "It is general reasoning and is labelled as such."
            )
        if not web:
            response.add_notice(
                "Web grounding was not confirmed for this answer."
            )
        return response

    # ---- which mailbox answers -----------------------------------------

    def _requested_mailbox(self, text: str):
        """(connection, scope) for a request that may name a mailbox.

        scope is "all" when Mike asked for every account, "one" otherwise.
        Naming a mailbox that is not configured returns (None, "one") so the
        normal default applies - JOE never invents a mailbox it does not have.
        """
        lowered = (text or "").lower()
        if any(phrase in lowered for phrase in
               ("all accounts", "all mailboxes", "every account",
                "both accounts", "all my email", "across accounts")):
            return None, "all"
        for connection in self.mailboxes.connections:
            handles = [connection.friendly_name.lower(),
                       connection.address.lower(),
                       connection.address.split("@")[0].lower(),
                       connection.connection_id.lower()]
            if any(h and h in lowered for h in handles):
                return connection, "one"
        return None, "one"

    def _no_mailbox_for(self, kind: str) -> AssistantResponse:
        """Say why nothing was read, rather than reading an empty mailbox.

        Reporting an empty day from a mailbox with no calendar is true of the
        mailbox and false of Mike. This is the difference."""
        note = self.mailboxes.fallback_note(kind) or (
            "no approved mailbox is configured for " + kind)
        return AssistantResponse(
            capability=Capability.OPERATIONS,
            answer="I have no mailbox that holds your " + kind + ".",
            written=(
                "I did not read any mailbox, because none of the approved "
                "mailboxes holds " + kind + ".\n\n" + note
                + "\n\nI am not showing you an empty " + kind
                + " - that would look like an answer. Add a mailbox that holds "
                  "your " + kind + " in Settings, or name one in the request."
            ),
            ok=False,
            failure="no mailbox holds " + kind,
            uncertainty="Nothing was read. Nothing here is established.",
            provenance=[Provenance(source="Outlook", mode=SourceMode.UNAVAILABLE,
                                   detail=note)],
        )

    def _read_all_mailboxes(self, kind: str, request) -> AssistantResponse:
        """Read every enabled mailbox, keeping each result separately labelled.

        Content from two mailboxes is never merged into one undifferentiated
        list - which one a message came from is operational information."""
        sources = self.mailboxes.sources_for(kind)
        if not sources:
            return self._no_mailbox_for(kind)

        body = ["OUTLOOK - LIVE, READ ONLY", "All approved mailboxes", ""]
        provenance = []
        findings = []
        failures = []
        for connection in sources:
            try:
                if kind == "calendar":
                    result = self.outlook.calendar(account=connection.address)
                else:
                    result = getattr(self.outlook, kind)(account=connection.address)
            except Exception as error:  # noqa: BLE001
                failures.append(connection.friendly_name + ": " + str(error)[:80])
                continue

            body.append(connection.friendly_name + "   (" + connection.address + ")")
            if not result.ok:
                # One mailbox failing must not hide the others.
                failures.append(connection.friendly_name + ": "
                                + (result.error or "unreadable"))
                body.append("    could not be read: "
                            + (result.error or "unknown reason"))
                body.append("")
                continue

            body.append("    " + str(result.returned) + " of "
                        + str(result.total) + "   " + result.ordering_label)
            for item in result.items[:8]:
                body.append("      " + _one_line(item))
            body.append("")
            findings.append(connection.friendly_name + ": "
                            + str(result.returned) + " item(s)")
            provenance.append(Provenance(
                source="Outlook / " + connection.friendly_name,
                mode=SourceMode.LIVE,
                as_of=result.read_at,
                source_class=SourceClass.LOCAL_OUTLOOK,
                detail=connection.address,
            ))

        if failures:
            body += ["MAILBOXES THAT COULD NOT BE READ", ""]
            body += ["  - " + f for f in failures]
            body += ["", "The mailboxes above that DID answer are still shown. "
                         "One failing does not hide the rest."]

        response = AssistantResponse(
            capability=Capability.OPERATIONS,
            answer=("Read " + str(len(provenance)) + " of "
                    + str(len(sources)) + " approved mailbox(es) for " + kind + "."),
            written="\n".join(body),
            findings=findings,
            provenance=provenance,
            ok=bool(provenance),
            failure="" if provenance else "no mailbox could be read",
        )
        if failures:
            response.add_notice(str(len(failures))
                                + " mailbox(es) could not be read. The rest are shown.")
        return response

    def _ensure_mailboxes_discovered(self) -> None:
        """Ask Outlook what it exposes, once, before a mailbox is chosen.

        from_config() builds every connection as UNKNOWN, and UNKNOWN is not
        usable. Without this call source_for() finds no usable mailbox and
        refuses every mail, calendar and contacts question - truthfully
        worded, and wrong, because the mailboxes hold all three.

        Lazy, to honour outlook.lazy_connect: Outlook is contacted when Mike
        asks, not at startup. A failed discovery is not cached (discover()
        clears last_discovery on failure), so the next ask retries rather
        than inheriting one bad moment for the life of the process.
        """
        if self.mailboxes.last_discovery is not None:
            return
        self.mailboxes.discover()

    def _handle_operations(self, request, chosen) -> AssistantResponse:
        """Read-only operational awareness through Outlook.

        Dispatch is the system of record for operations. Outlook is scheduling
        authority and mail transport. Neither is written to.
        """
        text = request.text.lower()
        if any(w in text for w in ("mail", "email", "inbox", "unread")):
            kind = "mail"
        elif any(w in text for w in ("who is", "contact", "phone number")):
            kind = "contacts"
        else:
            kind = "calendar"

        # What Outlook actually exposes, before anything is chosen from it.
        self._ensure_mailboxes_discovered()

        # Which mailbox answers this. Chosen per capability, because no
        # mailbox is assumed to hold mail AND calendar AND contacts.
        requested, scope = self._requested_mailbox(request.text)
        if scope == "all":
            return self._read_all_mailboxes(kind, request)
        connection = requested or self.mailboxes.source_for(kind)
        if connection is None:
            return self._no_mailbox_for(kind)
        account = connection.address

        # Calendar reads honour the date words Mike used, so "tomorrow" reads
        # tomorrow rather than a generic window.
        wants_next = False
        if kind == "calendar":
            from adapters.outlook_com import range_for, range_for_date
            from .when import parse_when

            when_kind, anchor = parse_when(request.text)
            wants_next = when_kind == "next"
            if when_kind == "date" and anchor is not None:
                date_range = range_for_date(anchor)
            elif when_kind in ("today", "tomorrow", "this week", "next week"):
                date_range = range_for(when_kind)
            else:
                date_range = range_for("", self.outlook.calendar_window_days)
            result = self.outlook.calendar(date_range=date_range,
                                           account=account)
        else:
            result = getattr(self.outlook, kind)(account=account)

        if not result.ok:
            return AssistantResponse(
                capability=Capability.OPERATIONS,
                answer="Outlook is not connected. I cannot read the live " + kind + ".",
                written=(
                    "Outlook is not connected, so I did not read your "
                    + kind
                    + ".\n\nReason: "
                    + (result.error or "unknown")
                    + "\n\nI have not substituted sample data for your real "
                    + kind
                    + "."
                ),
                ok=False,
                failure="outlook unavailable",
                provenance=[result.provenance()],
            )

        items = result.items
        body = [
            "OUTLOOK - LIVE, READ ONLY",
            "Mailbox: " + connection.friendly_name
            + "  (" + connection.address + ")",
            "Folder:  " + result.folder + "   ("
            + str(result.returned) + " of " + str(result.total) + " shown)",
            "Order:   " + result.ordering_label,
            "Read at: " + result.read_at,
            "",
        ]
        if kind == "calendar":
            if result.window_start:
                body.append("Asked for: " + result.window_line())
                body.append("")
            if wants_next and items and result.is_date_ordered:
                first = items[0]
                body.append("Next scheduled item:")
                body.append(
                    "  " + str(first.get("start", ""))[:16]
                    + "   " + str(first.get("subject", ""))[:52]
                )
                if first.get("location"):
                    body.append("      " + str(first.get("location"))[:60])
                body.append("")
                body.append("After that:")
                rest = items[1:9]
            else:
                body.append(
                    "Entries, soonest first:"
                    if result.is_date_ordered
                    else "Entries in folder order - these are NOT in date order:"
                )
                rest = items[:12]
            for item in rest:
                body.append(
                    "  " + str(item.get("start", ""))[:16]
                    + "   " + str(item.get("subject", ""))[:52]
                )
                if item.get("location"):
                    body.append("      " + str(item.get("location"))[:60])
            if not items:
                body.append("  (nothing in this range)")

            if items and result.is_date_ordered:
                lead = "Next up: " if wants_next else ""
                headline = (
                    lead
                    + str(items[0].get("subject", ""))[:60]
                    + " at "
                    + str(items[0].get("start", ""))[:16]
                )
                if not wants_next and result.window_label:
                    headline = (
                        str(len(items))
                        + " item(s) "
                        + result.window_label
                        + ". First: "
                        + str(items[0].get("subject", ""))[:44]
                        + " at "
                        + str(items[0].get("start", ""))[11:16]
                    )
            elif items:
                headline = (
                    "Calendar read, but NOT in date order - the first entry "
                    "shown is not necessarily your next one."
                )
            elif result.window_label:
                headline = "Nothing on the calendar " + result.window_label + "."
            else:
                headline = "Nothing on the calendar."
        elif kind == "mail":
            unread = [i for i in items if i.get("unread")]
            body.append(str(len(unread)) + " unread of " + str(len(items)) + " shown.")
            body.append("")
            for item in items[:12]:
                mark = "UNREAD  " if item.get("unread") else "        "
                body.append(
                    "  " + mark + str(item.get("received", ""))[:16]
                    + "  " + str(item.get("subject", ""))[:48]
                )
                body.append("            from " + str(item.get("sender", ""))[:48])
            headline = str(len(unread)) + " unread message(s)."
        else:
            body.append("Contacts:")
            for item in items[:15]:
                body.append(
                    "  " + str(item.get("display_name", ""))[:32]
                    + "   " + str(item.get("email", ""))[:40]
                )
            headline = str(len(items)) + " contact(s) read."

        body += [
            "",
            "Read-only. Nothing was sent, replied to, accepted, declined, "
            "scheduled, or modified.",
            "Dispatch remains the system of record for operational truth.",
        ]
        return AssistantResponse(
            capability=Capability.OPERATIONS,
            answer=headline,
            written="\n".join(body),
            provenance=[result.provenance()],
        )

    def _handle_retention(self, request, chosen) -> AssistantResponse:
        """Retention commands act on the currently selected interaction."""
        if not self.selected_id:
            return AssistantResponse(
                capability=Capability.RETENTION,
                answer="There is no interaction selected to act on.",
                written=(
                    "Ask something first, or select an interaction in the "
                    "history, then say Save, Level 3, Print, or Delete."
                ),
                ok=False,
                failure="nothing selected",
            )
        result = self.apply_retention(
            self.selected_id, chosen.retention_intent, chosen.references
        )
        return result

    # ================================================================
    # Retention actions (buttons and language share this path)
    # ================================================================

    def apply_retention(
        self, record_id: str, intent: str, references: dict | None = None
    ) -> AssistantResponse:
        """Save / Level 3 / Print / Delete / Level 1, for one record."""
        from assistant_memory.retention import Operation, RetentionError

        references = references or {}
        options = {
            key: references[key]
            for key in ("related_load", "related_mission", "destination")
            if references.get(key)
        }
        mapping = {
            "LEVEL_1": Operation.LEVEL_1,
            "LEVEL_2": Operation.LEVEL_2,
            "LEVEL_3": Operation.LEVEL_3,
            "PRINT": Operation.PRINT_READY,
            "PRINT_READY": Operation.PRINT_READY,
            "DELETE": Operation.DELETE,
        }
        operation = mapping.get(intent)
        if operation is None:
            return AssistantResponse(
                capability=Capability.RETENTION,
                answer="I did not recognize that as a retention command.",
                written="Recognized retention commands: Save, Level 3, Print, Delete.",
                ok=False,
                failure="unknown retention intent",
            )

        try:
            outcome = self.memory.apply(record_id, operation, **options)
        except RetentionError as error:
            return AssistantResponse(
                capability=Capability.RETENTION,
                answer="That was refused: " + str(error),
                written=str(error),
                ok=False,
                failure="retention refused",
            )

        notices: list[str] = []
        artifact: ActionRequest | None = None

        if operation == Operation.LEVEL_3:
            artifact = ActionRequest(
                kind="action_request",
                detail=(
                    "Formal artifact requested for "
                    + record_id
                    + (
                        " under " + options["destination"]
                        if options.get("destination")
                        else ""
                    )
                ),
            )
            notices.append(
                "Formal artifact requested. Nothing has been produced yet."
            )
        if operation == Operation.PRINT_READY:
            notices.append(
                "Print request recorded. Nothing was physically printed."
            )
        if operation == Operation.DELETE:
            self._forget(record_id)

        written = [
            "RETENTION",
            "",
            "  record            " + outcome.record_id,
            "  state             " + outcome.previous_state + " -> " + outcome.new_state,
            "  interaction level " + outcome.previous_level + " -> " + outcome.new_level,
            "  expires           " + str(outcome.expires_at or "no expiration"),
        ]
        for change in outcome.changes:
            written.append("    - " + change)
        if artifact:
            written += [
                "",
                "  ARTIFACT REQUEST",
                "    " + artifact.detail,
                "    produced=False  accepted=False  decision required from Mike Zachary",
            ]
        written += ["", "  " + outcome.notice]

        self.log.event(
            "retention", intent + " -> " + outcome.new_state, outcome.record_id
        )
        return AssistantResponse(
            capability=Capability.RETENTION,
            answer=outcome.notice,
            written="\n".join(written),
            notices=notices,
        )

    def _forget(self, record_id: str) -> None:
        self.interactions = [
            i for i in self.interactions if i.record_id != record_id
        ]
        if self.selected_id == record_id:
            self.selected_id = (
                self.interactions[-1].record_id if self.interactions else None
            )

    # ================================================================
    # History and selection
    # ================================================================

    def select(self, record_id: str) -> bool:
        if any(i.record_id == record_id for i in self.interactions):
            self.selected_id = record_id
            return True
        return False

    def selected(self) -> Interaction | None:
        for interaction in self.interactions:
            if interaction.record_id == self.selected_id:
                return interaction
        return None

    def history(self) -> list[dict]:
        """Active interactions, expired ones swept out first."""
        self.memory.sweep()
        active = {r.record_id for r in self.memory.store.list_active()}
        rows = []
        for interaction in self.interactions:
            if interaction.record_id not in active:
                continue
            record = self.memory.get(interaction.record_id)
            rows.append(
                {
                    "record_id": record.record_id,
                    "request": interaction.request,
                    "state": record.state,
                    "level": record.interaction_level,
                    "expires_at": record.expires_at,
                    "capability": interaction.response.capability,
                    "selected": record.record_id == self.selected_id,
                }
            )
        return rows

    def reload_history(self) -> int:
        """Rebuild the visible history from records that survived a restart."""
        self.memory.sweep()
        existing = {i.record_id for i in self.interactions}
        restored = 0
        for record in self.memory.store.list_active():
            if record.record_id in existing:
                continue
            self.interactions.append(
                Interaction(
                    record_id=record.record_id,
                    request=record.driver_request or "(no request recorded)",
                    response=AssistantResponse(
                        capability=Capability.ANSWER,
                        answer="(restored from a previous session)",
                        written=record.assistant_response or "(no response recorded)",
                    ),
                    created_at=record.created_at,
                )
            )
            restored += 1
        self.interactions.sort(key=lambda i: i.created_at)
        if self.interactions and not self.selected_id:
            self.selected_id = self.interactions[-1].record_id
        return restored

    # ================================================================
    # Driver mode and voice
    # ================================================================

    def _shape_for_driver(
        self, response: AssistantResponse, driver_mode: bool
    ) -> AssistantResponse:
        from assistant_voice.driver_mode import check_length, prepare_for_speech

        try:
            brief = prepare_for_speech(response.answer, "the written response above")
        except Exception:
            return response
        fits, _ = check_length(brief)
        response.spoken_summary = brief.spoken_text() if fits else response.answer
        if driver_mode and brief.deferred:
            response.add_notice(
                "Long result. The short spoken form defers to the written "
                "response, which stays here for parked review."
            )
        return response

    def copilot_status(self) -> dict:
        """Everything the settings panel needs. No credential material."""
        if self.copilot_auth is None:
            return {
                "provider_selected": False,
                "blocker": (
                    "Microsoft 365 Copilot is not the selected provider. Set "
                    "reasoning.provider to m365_copilot in the configuration."
                ),
            }
        status = dict(self.copilot_auth.status())
        status["provider_selected"] = True
        status.update(self.reasoning.status())
        return status

    def copilot_sign_out(self) -> str:
        """Clear the Microsoft sign-in and delete the encrypted token cache."""
        message = self.reasoning.sign_out()
        self.log.event("copilot_sign_out", message)
        return message

    def speak(self, text: str) -> dict:
        """Speak out loud. Only ever on an explicit request."""
        attempt = self.voice.speak(text)
        self.log.event(
            "voice_speak",
            ("spoken" if attempt.spoken else "failed: " + attempt.error),
        )
        return attempt.to_dict()

    def listen(self, seconds: int = 6) -> dict:
        result = self.voice.listen(seconds)
        self.log.event(
            "voice_listen",
            ("recognized" if result.get("recognized") else "nothing recognized"),
        )
        return result

    # ================================================================
    # Status
    # ================================================================

    def _voice_input_detail(self, voice: dict) -> str:
        """What is actually known about hearing Mike, stage by stage."""
        if not voice.get("stt_engine_available"):
            return "no speech recognition engine on this machine"
        try:
            diagnostics = self.microphones.diagnostics()
            device = diagnostics.get("in_use") or ""
        except Exception:  # noqa: BLE001
            device = ""
        parts = ["recognizer binds"]
        parts.append("microphone: " + (device or "NONE CONNECTED"))
        parts.append("never proven with a live voice")
        return "; ".join(parts)

    def _voice_input_blocker(self, voice: dict) -> str:
        if not voice.get("stt_engine_available"):
            return voice.get("blocker", "") or "no recognition engine"
        try:
            diagnostics = self.microphones.diagnostics()
            if diagnostics.get("blocker"):
                return diagnostics["blocker"]
            if not diagnostics.get("in_use"):
                return "no recording device is connected"
        except Exception:  # noqa: BLE001
            pass
        return ("the engine binds, but no person has spoken to it. "
                "Run the microphone test to prove it.")

    def status(self) -> list[CapabilityStatus]:
        library = self.library.probe()
        research = self.research.probe()
        voice = self.voice.probe()
        outlook = self.outlook.probe()
        dispatch = self.dispatch.probe()

        reasoning = self.reasoning.status()
        reasoning_detail = (
            reasoning.get("label") or reasoning["provider"]
            if reasoning["live"]
            else reasoning["status"]
        )
        if reasoning.get("preview") and reasoning["live"]:
            reasoning_detail += "  PILOT / PREVIEW"

        return [
            CapabilityStatus(
                name="Reasoning",
                available=reasoning["available"],
                mode=SourceMode.LIVE if reasoning["live"] else SourceMode.UNAVAILABLE,
                detail=reasoning_detail,
                live_connection=reasoning["live"],
                blocker=reasoning["blocker"],
            ),
            CapabilityStatus(
                name="Library",
                available=library["available"],
                mode=library["mode"],
                detail=str(library["indexed"]) + " documents indexed",
                live_connection=library["live_connection"],
                blocker=library["blocker"],
            ),
            CapabilityStatus(
                name="Outlook",
                available=outlook["available"],
                mode=(
                    SourceMode.LIVE
                    if outlook["live_connection"]
                    else (SourceMode.READY if outlook["available"] else SourceMode.UNAVAILABLE)
                ),
                detail=(
                    "read-only, " + str(outlook.get("account", ""))
                    if outlook["live_connection"]
                    else (
                        "installed and read-only; connects when you ask"
                        if outlook["available"]
                        else ""
                    )
                ),
                live_connection=outlook["live_connection"],
                blocker=outlook.get("blocker", "") or outlook.get("last_error", ""),
            ),
            CapabilityStatus(
                name="Research",
                available=research["available"],
                mode=research["mode"],
                detail="provider: " + research["provider"],
                live_connection=research["live_connection"],
                blocker=research["blocker"],
            ),
            # Voice is reported as TWO capabilities, because it is two.
            #
            # Output is proven and audible. Input has never been exercised with
            # Mike's voice - the engine binds and a microphone exists, which is
            # not the same thing. A single "Voice LIVE" chip covered both and
            # read as though speaking to JOE were a proven path.
            CapabilityStatus(
                name="Voice out",
                available=bool(voice.get("tts_available")),
                mode=(SourceMode.LIVE if voice.get("tts_available")
                      else SourceMode.UNAVAILABLE),
                detail=(
                    "speech engine bound: " + ", ".join(voice.get("voices", []))
                    if voice.get("tts_available")
                    else ""
                ),
                live_connection=bool(voice.get("tts_available")),
                blocker=voice.get("blocker", ""),
            ),
            CapabilityStatus(
                name="Voice in",
                available=bool(voice.get("stt_engine_available")),
                # READY, never LIVE. The recognizer binding proves the engine
                # loads. It does not prove a person was ever heard, and this
                # capability must not claim LIVE until one has been.
                mode=SourceMode.UNAVAILABLE,
                detail=self._voice_input_detail(voice),
                live_connection=False,
                blocker=self._voice_input_blocker(voice),
            ),
            CapabilityStatus(
                name="Dispatch",
                available=dispatch["available"],
                mode=SourceMode.UNAVAILABLE,
                detail="interface contract only; nothing connected",
                live_connection=dispatch["live_connection"],
                blocker=dispatch["blocker"],
            ),
        ]

    def operating_mode(self) -> str:
        live = [s.name for s in self.status() if s.live_connection]
        if not live:
            return "REDUCED - no live capability connected"
        return "LIVE: " + ", ".join(live)

    def status_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "operating_mode": self.operating_mode(),
            "capabilities": [s.to_dict() for s in self.status()],
            "interactions": len(self.interactions),
            "active_records": len(self.memory.store.list_active()),
            "runtime_data": str(self.config.runtime_data),
            "logs": str(self.config.logs),
            "authority": AUTHORITY_STATEMENT,
            "reasoning": self.reasoning.status(),
            "outlook_account": self.outlook.account or "(default store)",
            "dispatch_contacted": False,
            "operational_writes": 0,
            "messages_sent": 0,
        }

    def shutdown(self) -> None:
        self.log.event("service_stopped", "Assistant service stopped")
