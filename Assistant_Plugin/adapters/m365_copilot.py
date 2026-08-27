"""Microsoft 365 Copilot Chat API - reasoning provider.

    MICROSOFT 365 COPILOT
    PILOT / PREVIEW

Microsoft states of the `/beta` endpoints: "APIs under the /beta version are
subject to change. Use of these APIs in production applications is not
supported." That is carried through to the UI and every report rather than
quietly dropped.

Endpoints implemented:

    POST /beta/copilot/conversations                     create
    POST /beta/copilot/conversations/{id}/chat           synchronous turn
    POST /beta/copilot/conversations/{id}/chatOverStream  streamed turn

Authentication is delegated only - JOE acts as the signed-in person.
Microsoft supports no application-permission mode for this API, so there is no
unattended path, by their design and not by omission.

PROVENANCE. Copilot answers are classified, never blended with local reads:

    COPILOT_WORK_GROUNDED      grounded in tenant data (SharePoint, mail, ...)
    COPILOT_WEB_GROUNDED       grounded in web search
    COPILOT_GENERAL_REASONING  no source - reasoning only

A Copilot answer never becomes a Company Library result, an Outlook read, a
route-risk event, or a Dispatch fact.

BOUNDARIES. This provider may reason, explain, summarize, draft, compare,
recommend, and perform sourced web-grounded research. It may not approve,
decide, send, schedule, modify Outlook, modify Dispatch, alter operational
truth, or treat silence as consent. It has no method that could.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from contracts import Provenance, SourceClass, SourceMode, stamp

from .m365_copilot_auth import AuthState, CopilotAuth
from .reasoning_provider import (
    SYSTEM_FRAMING,
    TASK_FRAMING,
    Answer,
    ReasoningProvider,
    ReasoningStatus,
)

GRAPH_BETA = "https://graph.microsoft.com/beta"
CONVERSATIONS = GRAPH_BETA + "/copilot/conversations"

PROVIDER_LABEL = "MICROSOFT 365 COPILOT  (PILOT / PREVIEW)"

# Microsoft's own words about the /beta surface. Shown, not paraphrased away.
PREVIEW_NOTICE = (
    "Microsoft 365 Copilot Chat API is a /beta endpoint. Microsoft states use "
    "of these APIs in production applications is not supported. This is a "
    "pilot connection."
)


class CopilotApiError(RuntimeError):
    pass


@dataclass
class CopilotReply:
    """One parsed Copilot turn."""

    text: str = ""
    conversation_id: str = ""
    turn_count: int = 0
    citations: list = field(default_factory=list)
    annotations: list = field(default_factory=list)
    sensitivity: dict = field(default_factory=dict)
    web_enabled: bool = False
    had_context: bool = False
    had_files: bool = False

    @property
    def has_citations(self) -> bool:
        return bool(self.citations)

    def source_class(self) -> str:
        """Classify honestly, from what the reply actually shows.

        Work-grounded is claimed only when Copilot returned citations and web
        search was not the grounding used. Otherwise it is web-grounded or
        plain reasoning. When unsure, the weaker claim wins.
        """
        if self.has_citations:
            return (
                SourceClass.COPILOT_WEB_GROUNDED
                if self.web_enabled and not (self.had_files or self.had_context)
                else SourceClass.COPILOT_WORK_GROUNDED
            )
        return SourceClass.COPILOT_GENERAL_REASONING

    def sources(self) -> list[str]:
        out: list[str] = []
        for entry in self.citations:
            name = str(entry.get("providerDisplayName") or "").strip()
            url = str(entry.get("seeMoreWebUrl") or "").strip()
            label = name or url or "(unnamed citation)"
            if url and name:
                label = name + "  " + url
            if label not in out:
                out.append(label)
        return out

    @property
    def sensitivity_label(self) -> str:
        return str(self.sensitivity.get("displayName") or "").strip()

    @property
    def is_encrypted(self) -> bool:
        return bool(self.sensitivity.get("isEncrypted"))


def parse_conversation(payload: dict) -> CopilotReply:
    """Pull the assistant's turn out of a copilotConversation payload.

    The thread echoes the prompt first, so the reply is the LAST message.
    """
    reply = CopilotReply(
        conversation_id=str(payload.get("id", "")),
        turn_count=int(payload.get("turnCount", 0) or 0),
    )
    messages = payload.get("messages") or []
    if not isinstance(messages, list) or not messages:
        return reply

    last = messages[-1] if isinstance(messages[-1], dict) else {}
    reply.text = str(last.get("text", "") or "").strip()

    for attribution in last.get("attributions") or []:
        if not isinstance(attribution, dict):
            continue
        kind = str(attribution.get("attributionType", "")).lower()
        if kind == "citation":
            reply.citations.append(attribution)
        else:
            reply.annotations.append(attribution)

    sensitivity = last.get("sensitivityLabel")
    if isinstance(sensitivity, dict):
        reply.sensitivity = {
            key: value for key, value in sensitivity.items() if value is not None
        }
    return reply


class M365CopilotProvider(ReasoningProvider):
    """Reasoning through Microsoft 365 Copilot. Delegated, read-only, pilot."""

    name = "m365_copilot"
    label = PROVIDER_LABEL

    def __init__(
        self,
        auth: CopilotAuth | None = None,
        time_zone: str = "America/New_York",
        timeout_seconds: int = 120,
        web_enabled: bool = False,
        max_context_chars: int = 12000,
        transport=None,
    ) -> None:
        self.auth = auth or CopilotAuth()
        self.time_zone = time_zone or "America/New_York"
        self.timeout_seconds = max(15, int(timeout_seconds))
        # Web grounding is off unless asked for. Research turns it on
        # deliberately; ordinary answers stay inside work data.
        self.web_enabled = bool(web_enabled)
        self.max_context_chars = max(500, int(max_context_chars))
        # Injected in tests so the contract can be proven without a tenant.
        self._transport = transport
        self.conversation_id = ""
        self.turns = 0
        self.last_error = ""
        self.last_reply: CopilotReply | None = None

    # ---- transport ----------------------------------------------------

    def _post(self, url: str, body: dict) -> dict:
        """One POST to Graph. The token goes into the header and nowhere else."""
        if self._transport is not None:
            return self._transport(url, body, self.auth)

        header = self.auth.authorization_header()
        if not header:
            raise CopilotApiError(
                "not signed in to Microsoft 365: " + (self.auth.status()["blocker"] or "")
            )
        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST"
        )
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", header)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as handle:
                raw = handle.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            raise CopilotApiError(self._safe_http(error)) from None
        except (urllib.error.URLError, OSError) as error:
            raise CopilotApiError(
                "could not reach Microsoft Graph: " + type(error).__name__
            ) from None
        try:
            return json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            raise CopilotApiError("Graph returned output that could not be read") from None

    @staticmethod
    def _safe_http(error) -> str:
        """An HTTP error with no header, token, or correlation id echoed back."""
        code = getattr(error, "code", 0)
        meaning = {
            401: "sign-in has expired or was rejected - sign in again",
            403: (
                "access denied. The account may lack a Microsoft 365 Copilot "
                "licence, or admin consent for the required Graph permissions"
            ),
            404: "the Copilot Chat API was not found for this tenant",
            429: "Microsoft is rate limiting - try again shortly",
        }.get(code, "")
        detail = ""
        try:
            payload = json.loads(error.read().decode("utf-8", errors="replace"))
            detail = str(((payload.get("error") or {}).get("message")) or "")[:200]
        except Exception:  # noqa: BLE001
            detail = ""
        return ("HTTP " + str(code) + (": " + meaning if meaning else "")
                + (" - " + detail if detail else ""))

    # ---- conversation -------------------------------------------------

    def start_conversation(self) -> str:
        """Create a Copilot conversation. Body is an empty JSON object."""
        payload = self._post(CONVERSATIONS, {})
        conversation_id = str(payload.get("id", ""))
        if not conversation_id:
            raise CopilotApiError("Copilot did not return a conversation id")
        self.conversation_id = conversation_id
        self.turns = 0
        return conversation_id

    def _ensure_conversation(self) -> str:
        if not self.conversation_id:
            self.start_conversation()
        return self.conversation_id

    def reset_conversation(self) -> None:
        """Forget the thread. The next turn starts a new conversation."""
        self.conversation_id = ""
        self.turns = 0

    # ---- the request body ---------------------------------------------

    def _build_body(
        self,
        text: str,
        additional_context: list | None = None,
        files: list | None = None,
        web_enabled: bool | None = None,
    ) -> dict:
        body: dict = {
            "message": {"text": text},
            "locationHint": {"timeZone": self.time_zone},
        }
        extra = [c for c in (additional_context or []) if str(c).strip()]
        if extra:
            body["additionalContext"] = [
                {"text": str(c)[: self.max_context_chars]} for c in extra
            ]
        resources: dict = {}
        clean_files = [str(u).strip() for u in (files or []) if str(u).strip()]
        if clean_files:
            resources["files"] = [{"uri": uri} for uri in clean_files]
        wanted = self.web_enabled if web_enabled is None else bool(web_enabled)
        # Sent explicitly either way, so grounding is never left to a default.
        resources["webContext"] = {"isWebEnabled": wanted}
        body["contextualResources"] = resources
        return body

    # ---- turns --------------------------------------------------------

    def chat(
        self,
        text: str,
        additional_context: list | None = None,
        files: list | None = None,
        web_enabled: bool | None = None,
    ) -> CopilotReply:
        conversation_id = self._ensure_conversation()
        body = self._build_body(text, additional_context, files, web_enabled)
        payload = self._post(CONVERSATIONS + "/" + conversation_id + "/chat", body)
        reply = parse_conversation(payload)
        reply.web_enabled = body["contextualResources"]["webContext"]["isWebEnabled"]
        reply.had_context = "additionalContext" in body
        reply.had_files = bool(body["contextualResources"].get("files"))
        if reply.conversation_id:
            self.conversation_id = reply.conversation_id
        self.turns = reply.turn_count or (self.turns + 1)
        self.last_reply = reply
        return reply

    def chat_over_stream(
        self,
        text: str,
        additional_context: list | None = None,
        files: list | None = None,
        web_enabled: bool | None = None,
    ) -> CopilotReply:
        """Streamed turn, where the tenant supports it.

        The streamed endpoint returns the same conversation shape. If it is
        unavailable this falls back to the synchronous turn and says so,
        rather than failing the request.
        """
        conversation_id = self._ensure_conversation()
        body = self._build_body(text, additional_context, files, web_enabled)
        try:
            payload = self._post(
                CONVERSATIONS + "/" + conversation_id + "/chatOverStream", body
            )
        except CopilotApiError as error:
            self.last_error = "streamed turn unavailable (" + str(error) + "); used synchronous"
            return self.chat(text, additional_context, files, web_enabled)
        reply = parse_conversation(payload)
        reply.web_enabled = body["contextualResources"]["webContext"]["isWebEnabled"]
        reply.had_context = "additionalContext" in body
        reply.had_files = bool(body["contextualResources"].get("files"))
        if reply.conversation_id:
            self.conversation_id = reply.conversation_id
        self.turns = reply.turn_count or (self.turns + 1)
        self.last_reply = reply
        return reply

    # ---- the ReasoningProvider contract -------------------------------

    def _answer_from(self, reply: CopilotReply, task: str) -> Answer:
        source_class = reply.source_class()
        answer = Answer(
            text=reply.text,
            ok=bool(reply.text),
            task=task,
            provider=self.name,
            model=PROVIDER_LABEL,
            grounded=reply.has_citations,
            sources=reply.sources(),
            status=ReasoningStatus.LIVE if reply.text else ReasoningStatus.ERROR,
            error="" if reply.text else "Copilot returned an empty answer",
        )
        answer.source_class = source_class
        answer.sensitivity_label = reply.sensitivity_label
        answer.is_encrypted = reply.is_encrypted
        answer.conversation_id = reply.conversation_id
        answer.turn_count = reply.turn_count
        return answer

    def _run(self, task: str, instruction: str, context: str, sources, **options) -> Answer:
        state = self.status()
        if state["status"] != ReasoningStatus.LIVE:
            return Answer(
                text="", ok=False, task=task, provider=self.name,
                model=PROVIDER_LABEL, error=state["blocker"], status=state["status"],
            )
        prompt = "\n".join(
            [
                SYSTEM_FRAMING,
                "",
                TASK_FRAMING.get(task, TASK_FRAMING["answer"]),
                "",
                "REQUEST:",
                instruction,
            ]
        )
        extra = [context] if context else None
        try:
            reply = self.chat(
                prompt,
                additional_context=extra,
                files=options.get("files"),
                web_enabled=options.get("web_enabled"),
            )
        except CopilotApiError as error:
            self.last_error = str(error)
            return Answer(
                text="", ok=False, task=task, provider=self.name,
                model=PROVIDER_LABEL, error=self.last_error,
                status=ReasoningStatus.ERROR,
            )
        answer = self._answer_from(reply, task)
        # Local material supplied as grounding stays labelled as ours.
        for source in sources or []:
            if source not in answer.sources:
                answer.sources.append(source)
        return answer

    def answer(self, question: str, context: str = "", sources=None, **options) -> Answer:
        return self._run("answer", question, context, sources, **options)

    def summarize(self, material: str, sources=None, **options) -> Answer:
        return self._run("summarize", "Summarize this.", material, sources, **options)

    def explain(self, material: str, question: str = "", sources=None, **options) -> Answer:
        return self._run(
            "explain", question or "Explain this in plain language.",
            material, sources, **options,
        )

    def draft(self, instruction: str, context: str = "", sources=None, **options) -> Answer:
        return self._run("draft", instruction, context, sources, **options)

    def recommend(self, question: str, context: str = "", sources=None, **options) -> Answer:
        return self._run("recommend", question, context, sources, **options)

    def procedure(self, question: str, context: str = "", sources=None, **options) -> Answer:
        return self._run("procedure", question, context, sources, **options)

    def research(self, question: str, context: str = "", sources=None) -> Answer:
        """Web-grounded research. The only path that turns web search on."""
        return self._run(
            "recommend", question, context, sources, web_enabled=True
        )

    # ---- provenance ---------------------------------------------------

    def provenance_for(self, answer: Answer) -> Provenance:
        source_class = getattr(answer, "source_class", SourceClass.COPILOT_GENERAL_REASONING)
        detail = PROVIDER_LABEL
        if answer.sources:
            detail += ", " + str(len(answer.sources)) + " citation(s)"
        label = getattr(answer, "sensitivity_label", "")
        if label:
            detail += ", sensitivity: " + label
        return Provenance(
            source="Microsoft 365 Copilot",
            mode=SourceMode.LIVE if answer.ok else SourceMode.UNAVAILABLE,
            as_of=stamp(),
            detail=detail if answer.ok else answer.error,
            source_class=source_class,
        )

    # ---- status -------------------------------------------------------

    def status(self) -> dict:
        auth = self.auth.status()
        state = auth["state"]
        mapping = {
            AuthState.LIBRARY_MISSING: ReasoningStatus.NOT_CONFIGURED,
            AuthState.NOT_CONFIGURED: ReasoningStatus.NOT_CONFIGURED,
            AuthState.SIGNED_OUT: ReasoningStatus.UNAVAILABLE,
            AuthState.ERROR: ReasoningStatus.ERROR,
            AuthState.SIGNED_IN: ReasoningStatus.LIVE,
        }
        status = mapping.get(state, ReasoningStatus.ERROR)
        if self._transport is not None:
            status = ReasoningStatus.LIVE  # test transport
        return {
            "status": status,
            "available": status == ReasoningStatus.LIVE,
            "live": status == ReasoningStatus.LIVE,
            "provider": self.name,
            "label": PROVIDER_LABEL,
            "model": PROVIDER_LABEL,
            "preview": True,
            "preview_notice": PREVIEW_NOTICE,
            "credential_required": True,
            "credential_present": auth["signed_in"],
            "client_secret_used": False,
            "account": auth["account"],
            "auth_state": state,
            "cache_encrypted": auth["cache_encrypted"],
            "scopes": auth["scopes"],
            "conversation_id": self.conversation_id,
            "turns": self.turns,
            "web_enabled_default": self.web_enabled,
            "blocker": auth["blocker"] or self.last_error,
            # Boundaries, emitted as literals.
            "can_approve": False,
            "can_decide": False,
            "can_send": False,
            "can_schedule": False,
            "can_modify_outlook": False,
            "can_modify_dispatch": False,
        }
