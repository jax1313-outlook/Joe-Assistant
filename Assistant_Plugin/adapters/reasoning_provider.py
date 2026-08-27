"""Reasoning provider adapter.

JOE needs something that can compose an answer. This is the one
place that talks to such a provider. The rest of the application asks this
adapter and never learns a vendor's name.

**No reasoning provider is configured on this machine.** That is a fact about
the environment, reported as `REASONING NOT CONFIGURED`, not hidden.

Backends implemented and ready to be bound:

  ollama            a local model server, no credential, nothing to buy
  openai_compatible any endpoint speaking the OpenAI chat-completions shape
                    (LM Studio, LocalAI, vLLM, llama.cpp server, and others)

Both are real HTTP clients. Neither is reachable today because no such server
is installed or running here.

CREDENTIALS: read from the environment only. Never from a config file, never
from source, never logged, never printed, never put in a report. The adapter
reports whether a credential is *present*; it never reveals a character of it.

AUTHORITY: the provider may reason. It may not approve, decide, execute, or
widen its own permissions. Every answer is returned as an `Answer` carrying
`approved=False` and `decided=False`, and the governance gate reviews it like
any other response.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from contracts import Provenance, SourceMode, stamp


class ReasoningStatus:
    LIVE = "REASONING LIVE"
    NOT_CONFIGURED = "REASONING NOT CONFIGURED"
    UNAVAILABLE = "REASONING UNAVAILABLE"
    ERROR = "REASONING ERROR"

    ALL = (LIVE, NOT_CONFIGURED, UNAVAILABLE, ERROR)


class ReasoningProviderError(RuntimeError):
    pass


# Environment variable names the adapter will look in. Presence only is ever
# reported; the value is used to build a request header and nothing else.
CREDENTIAL_ENV = {
    "openai_compatible": "ASSISTANT_REASONING_KEY",
    "ollama": "",  # a local model server needs no credential
    # Microsoft 365 Copilot holds no credential here at all - MSAL owns the
    # token and its encrypted cache. See m365_copilot_auth.py.
    "m365_copilot": "",
}

DEFAULT_ENDPOINT = {
    "ollama": "http://127.0.0.1:11434",
    "openai_compatible": "http://127.0.0.1:1234/v1",
}

# What JOE asks a provider to do. The system framing travels with
# every call so the boundary does not depend on the caller remembering it.
SYSTEM_FRAMING = (
    "You assist a truck owner-operator. Answer the immediate question first, in "
    "one or two sentences, then any detail. Be direct and operational. "
    "Use only the CONTEXT supplied; if the context does not contain the answer, "
    "say so plainly rather than guessing. Never claim to have read a system you "
    "were not given context from. Separate fact from inference, and state "
    "uncertainty when it exists. You may recommend. You may not approve, decide, "
    "or state that any action has been taken."
)

TASK_FRAMING = {
    "answer": "Answer the question.",
    "summarize": (
        "Summarize the supplied material. Keep every date, amount, location, "
        "deadline, warning, and required decision. Do not simplify away an "
        "operational consequence."
    ),
    "explain": (
        "Explain the supplied material in plain language a driver can use. "
        "Explain what it says; do not decide what it should mean."
    ),
    "draft": (
        "Write a draft for the person to review. It will not be sent by you. "
        "Do not state that anything has been sent, agreed, or approved."
    ),
    "recommend": (
        "Say what appears worth doing and why, with the uncertainty stated. "
        "This is a recommendation only; the person decides."
    ),
    "procedure": (
        "Explain the procedure using only the supplied governing document. "
        "Identify the document. If it does not cover the question, say so."
    ),
}


@dataclass
class Answer:
    """What the provider returned. Never an action, never an approval."""

    text: str
    ok: bool = True
    task: str = "answer"
    provider: str = ""
    model: str = ""
    grounded: bool = False
    sources: list[str] = field(default_factory=list)
    error: str = ""
    status: str = ReasoningStatus.LIVE
    at: str = field(default_factory=stamp)

    # Set by providers that classify their own grounding (Copilot does).
    source_class: str = "NONE"
    sensitivity_label: str = ""
    is_encrypted: bool = False
    conversation_id: str = ""
    turn_count: int = 0

    # Fixed. Emitted as literals; no code path sets them true.
    approved: bool = False
    decided: bool = False
    acted_on: bool = False

    def provenance(self) -> Provenance:
        return Provenance(
            source="Reasoning provider (" + (self.provider or "none") + ")",
            mode=SourceMode.LIVE if self.ok else SourceMode.UNAVAILABLE,
            as_of=self.at,
            detail=(
                (self.model + ", grounded in " + str(len(self.sources)) + " source(s)")
                if self.ok and self.grounded
                else (self.model or self.error or "general reasoning, no source")
            ),
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "ok": self.ok,
            "task": self.task,
            "provider": self.provider,
            "model": self.model,
            "grounded": self.grounded,
            "sources": list(self.sources),
            "error": self.error,
            "status": self.status,
            "at": self.at,
            "source_class": self.source_class,
            "sensitivity_label": self.sensitivity_label,
            "is_encrypted": self.is_encrypted,
            "conversation_id": self.conversation_id,
            "turn_count": self.turn_count,
            "approved": False,
            "decided": False,
            "acted_on": False,
        }


class ReasoningProvider:
    """The contract. status / answer / summarize / draft / recommend."""

    name = "abstract"

    def status(self) -> dict:  # pragma: no cover - interface
        raise NotImplementedError

    def answer(self, question: str, context: str = "", sources=None) -> Answer:  # pragma: no cover
        raise NotImplementedError

    def summarize(self, material: str, sources=None) -> Answer:  # pragma: no cover
        raise NotImplementedError

    def draft(self, instruction: str, context: str = "", sources=None) -> Answer:  # pragma: no cover
        raise NotImplementedError

    def recommend(self, question: str, context: str = "", sources=None) -> Answer:  # pragma: no cover
        raise NotImplementedError


class ReasoningProviderAdapter(ReasoningProvider):
    """Selects and drives a reasoning backend.

    `provider="none"` is the honest default here: nothing is bound, every call
    returns `REASONING NOT CONFIGURED`, and the rest of JOE keeps
    working.
    """

    name = "reasoning-adapter"

    SUPPORTED = ("none", "m365_copilot", "ollama", "openai_compatible")

    def __init__(
        self,
        provider: str = "none",
        model: str = "",
        endpoint: str = "",
        timeout_seconds: int = 60,
        max_context_chars: int = 12000,
        backend=None,
    ) -> None:
        # A provider that owns its own transport and auth (Copilot does) is
        # held here and everything is delegated to it.
        self.backend = backend
        self.provider = (provider or "none").strip().lower()
        self.model = (model or "").strip()
        self.endpoint = (endpoint or DEFAULT_ENDPOINT.get(self.provider, "")).rstrip("/")
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.max_context_chars = max(500, int(max_context_chars))
        self.last_error = ""
        self.calls = 0
        self._reachable: bool | None = None

    # ---- credentials --------------------------------------------------

    @property
    def credential_env(self) -> str:
        return CREDENTIAL_ENV.get(self.provider, "")

    @property
    def credential_present(self) -> bool:
        """Whether a credential exists. Never reveals the value."""
        name = self.credential_env
        return bool(name) and bool(os.environ.get(name))

    def _credential(self) -> str:
        name = self.credential_env
        return os.environ.get(name, "") if name else ""

    # ---- availability -------------------------------------------------

    @property
    def configured(self) -> bool:
        if self.provider in ("none", ""):
            return False
        if self.provider not in self.SUPPORTED:
            return False
        if self.credential_env and not self.credential_present:
            return False
        return bool(self.endpoint)

    def reachable(self, refresh: bool = False) -> bool:
        """Is the configured backend actually answering?"""
        if not self.configured:
            return False
        if self._reachable is not None and not refresh:
            return self._reachable
        url = (
            self.endpoint + "/api/tags"
            if self.provider == "ollama"
            else self.endpoint + "/models"
        )
        try:
            request = urllib.request.Request(url, method="GET")
            token = self._credential()
            if token:
                request.add_header("Authorization", "Bearer " + token)
            with urllib.request.urlopen(request, timeout=min(8, self.timeout_seconds)):
                self._reachable = True
        except (urllib.error.URLError, OSError, ValueError) as error:
            self.last_error = self._safe_error(error)
            self._reachable = False
        return self._reachable

    def status(self) -> dict:
        if self.backend is not None:
            return self.backend.status()
        if self.provider in ("none", ""):
            return {
                "status": ReasoningStatus.NOT_CONFIGURED,
                "available": False,
                "live": False,
                "provider": "none",
                "model": "",
                "credential_required": False,
                "credential_present": False,
                "blocker": (
                    "no reasoning provider is configured; set reasoning.provider "
                    "in configuration and, if the provider needs one, supply a "
                    "credential in the environment"
                ),
            }
        if self.provider not in self.SUPPORTED:
            return {
                "status": ReasoningStatus.ERROR,
                "available": False,
                "live": False,
                "provider": self.provider,
                "model": self.model,
                "credential_required": bool(self.credential_env),
                "credential_present": self.credential_present,
                "blocker": (
                    "provider '" + self.provider + "' has no adapter in this build; "
                    "supported: " + ", ".join(self.SUPPORTED)
                ),
            }
        if self.credential_env and not self.credential_present:
            return {
                "status": ReasoningStatus.NOT_CONFIGURED,
                "available": False,
                "live": False,
                "provider": self.provider,
                "model": self.model,
                "credential_required": True,
                "credential_present": False,
                "blocker": (
                    "provider '" + self.provider + "' needs a credential in the "
                    "environment variable " + self.credential_env
                    + "; none is set"
                ),
            }
        if not self.reachable():
            return {
                "status": ReasoningStatus.UNAVAILABLE,
                "available": False,
                "live": False,
                "provider": self.provider,
                "model": self.model,
                "endpoint": self.endpoint,
                "credential_required": bool(self.credential_env),
                "credential_present": self.credential_present,
                "blocker": (
                    "provider '" + self.provider + "' is configured but did not "
                    "answer at " + self.endpoint + ": " + self.last_error
                ),
            }
        return {
            "status": ReasoningStatus.LIVE,
            "available": True,
            "live": True,
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "credential_required": bool(self.credential_env),
            "credential_present": self.credential_present,
            "blocker": "",
        }

    # ---- errors -------------------------------------------------------

    @staticmethod
    def _safe_error(error: Exception) -> str:
        """An error message with no credential in it.

        Provider errors can echo a request header. Anything that looks like a
        key is removed before the message goes anywhere near a log or the UI.
        """
        text = str(error)
        for name in CREDENTIAL_ENV.values():
            if not name:
                continue
            value = os.environ.get(name)
            if value and value in text:
                text = text.replace(value, "[redacted]")
        if "Bearer " in text:
            text = text.split("Bearer ")[0] + "Bearer [redacted]"
        return text[:300]

    def _unavailable(self, task: str) -> Answer:
        state = self.status()
        return Answer(
            text="",
            ok=False,
            task=task,
            provider=self.provider,
            model=self.model,
            error=state["blocker"],
            status=state["status"],
        )

    # ---- the call -----------------------------------------------------

    def _post(self, prompt: str, task: str) -> Answer:
        state = self.status()
        if state["status"] != ReasoningStatus.LIVE:
            return self._unavailable(task)

        if self.provider == "ollama":
            url = self.endpoint + "/api/chat"
            payload = {
                "model": self.model or "llama3.1",
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_FRAMING},
                    {"role": "user", "content": prompt},
                ],
            }
        else:
            url = self.endpoint + "/chat/completions"
            payload = {
                "model": self.model or "local-model",
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_FRAMING},
                    {"role": "user", "content": prompt},
                ],
            }

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        token = self._credential()
        if token:
            request.add_header("Authorization", "Bearer " + token)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as handle:
                raw = handle.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError, ValueError) as error:
            self.last_error = self._safe_error(error)
            self._reachable = None
            return Answer(
                text="", ok=False, task=task, provider=self.provider,
                model=self.model, error=self.last_error,
                status=ReasoningStatus.ERROR,
            )

        self.calls += 1
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return Answer(
                text="", ok=False, task=task, provider=self.provider,
                model=self.model, error="provider returned unreadable output",
                status=ReasoningStatus.ERROR,
            )

        if self.provider == "ollama":
            text = str(((data.get("message") or {}).get("content")) or "")
        else:
            choices = data.get("choices") or []
            text = str(
                ((choices[0].get("message") or {}).get("content")) if choices else ""
            )

        if not text.strip():
            return Answer(
                text="", ok=False, task=task, provider=self.provider,
                model=self.model, error="provider returned an empty answer",
                status=ReasoningStatus.ERROR,
            )
        return Answer(
            text=text.strip(), ok=True, task=task,
            provider=self.provider, model=self.model,
            status=ReasoningStatus.LIVE,
        )

    # ---- prompt assembly ----------------------------------------------

    def _prompt(self, task: str, instruction: str, context: str) -> str:
        parts = [TASK_FRAMING.get(task, TASK_FRAMING["answer"]), ""]
        if context:
            parts += [
                "CONTEXT (the only material you may treat as retrieved):",
                context[: self.max_context_chars],
                "",
            ]
        else:
            parts += [
                "CONTEXT: none was retrieved. Answer from general knowledge and "
                "say plainly that you had no source.",
                "",
            ]
        parts += ["REQUEST:", instruction]
        return "\n".join(parts)

    def _run(self, task, instruction, context, sources) -> Answer:
        answer = self._post(self._prompt(task, instruction, context), task)
        answer.grounded = bool(context)
        answer.sources = list(sources or [])
        return answer

    # ---- the contract -------------------------------------------------

    def answer(self, question: str, context: str = "", sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.answer(question, context, sources)
        return self._run("answer", question, context, sources)

    def summarize(self, material: str, sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.summarize(material, sources)
        return self._run("summarize", "Summarize this.", material, sources)

    def explain(self, material: str, question: str = "", sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.explain(material, question, sources)
        return self._run(
            "explain", question or "Explain this in plain language.", material, sources
        )

    def draft(self, instruction: str, context: str = "", sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.draft(instruction, context, sources)
        return self._run("draft", instruction, context, sources)

    def recommend(self, question: str, context: str = "", sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.recommend(question, context, sources)
        return self._run("recommend", question, context, sources)

    def procedure(self, question: str, context: str = "", sources=None) -> Answer:
        if self.backend is not None:
            return self.backend.procedure(question, context, sources)
        return self._run("procedure", question, context, sources)

    def research(self, question: str, context: str = "", sources=None) -> Answer:
        """Web-grounded research, where the provider supports it."""
        if self.backend is not None and hasattr(self.backend, "research"):
            return self.backend.research(question, context, sources)
        return Answer(
            text="", ok=False, task="research", provider=self.provider,
            error="the configured reasoning provider cannot perform sourced web research",
            status=ReasoningStatus.NOT_CONFIGURED,
        )

    def provenance_for(self, answer: Answer):
        if self.backend is not None and hasattr(self.backend, "provenance_for"):
            return self.backend.provenance_for(answer)
        return answer.provenance()

    def sign_out(self) -> str:
        if self.backend is not None and hasattr(self.backend, "auth"):
            return self.backend.auth.sign_out()
        return "This provider has no sign-in to clear."

