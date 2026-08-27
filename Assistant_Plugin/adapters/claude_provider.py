"""Claude as JOE's reasoning provider - built for a driver's clock.

WHY THIS EXISTS. Microsoft 365 Copilot answered in 6.6 and 9.9 seconds on this
machine. Ten seconds of silence with both hands on a wheel is not a slow
answer, it is a second thing to hold: Mike has to keep the question in his head
and decide whether JOE heard him. Speed here is not a preference, it is the
premise of the program.

CREDENTIAL. JOE never reads the API key. The Anthropic SDK reads
ANTHROPIC_API_KEY from the environment itself; this module only ever asks
whether the environment has one, and reports that as a boolean. No key is
stored in configuration, logged, or returned to a caller - the same rule the
Copilot provider follows for its token.

THE BOUNDARY TRAVELS WITH THE CALL. SYSTEM_FRAMING and TASK_FRAMING are
imported from reasoning_provider rather than restated here. A second copy of
the rule that JOE may not approve or decide is a second copy that can drift,
and the one that drifts is always the one nobody is reading.

FAST MODE. Enabled by default, because latency is the point. It runs the same
model at up to 2.5x the output speed for double the token price. When the fast
tier is rate limited the request is retried at standard speed rather than
failing - a slower answer is worth having; no answer at seventy miles an hour
is not.

NOTHING IS INVENTED. Every failure path returns an Answer with ok=False and a
plain reason. This provider never substitutes a guess for a connection it did
not get.
"""

from __future__ import annotations

import os

from .reasoning_provider import (Answer, ReasoningProvider, ReasoningStatus,
                                 SYSTEM_FRAMING, TASK_FRAMING)

CREDENTIAL_ENV = "ANTHROPIC_API_KEY"

DEFAULT_MODEL = "claude-opus-5"

# Fast mode is a research preview on Opus 5 and Opus 4.8, on the Anthropic API
# only. The beta flag is required on every request that uses it.
FAST_MODE_BETA = "fast-mode-2026-02-01"

# Safety classifiers can decline a request. The server-side fallback routes it
# to another model by refusal category instead of handing Mike an error he can
# do nothing about.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Room for a full written answer. JOE speaks one sentence of it and keeps the
# rest for "explain more", so the answer must arrive whole.
MAX_TOKENS = 2000


def credential_present() -> bool:
    """Whether the environment holds a key. The value is never read here."""
    return bool((os.environ.get(CREDENTIAL_ENV) or "").strip())


class ClaudeProvider(ReasoningProvider):
    """Anthropic's Claude, through the official SDK."""

    name = "claude"

    def __init__(
        self,
        model: str = "",
        fast: bool = True,
        effort: str = "low",
        timeout_seconds: int = 30,
        max_context_chars: int = 12000,
    ) -> None:
        self.model = (model or DEFAULT_MODEL).strip()
        self.fast = bool(fast)
        # Low effort suits a question asked at the wheel: fewer, shorter turns.
        # A capability that needs deeper reasoning can raise it per call.
        self.effort = (effort or "low").strip()
        self.timeout_seconds = int(timeout_seconds)
        self.max_context_chars = int(max_context_chars)
        self.last_error = ""
        self.last_speed = ""
        self._client = None

    # ---- connection ----------------------------------------------------

    @property
    def configured(self) -> bool:
        return credential_present()

    def _sdk(self):
        """The SDK, imported late so JOE runs without it installed."""
        if self._client is not None:
            return self._client
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "the anthropic package is not installed - "
                "run: py -m pip install --user anthropic")
        # No api_key argument: the SDK reads the environment itself, so the
        # key never passes through JOE.
        self._client = anthropic.Anthropic(timeout=float(self.timeout_seconds))
        return self._client

    def status(self) -> dict:
        present = self.configured
        try:
            import anthropic  # noqa: F401
            installed = True
        except ImportError:
            installed = False

        if not installed:
            state, blocker = (
                ReasoningStatus.NOT_CONFIGURED,
                "the anthropic package is not installed on this machine")
        elif not present:
            state, blocker = (
                ReasoningStatus.UNAVAILABLE,
                "configured, but no API key is set in " + CREDENTIAL_ENV)
        elif self.last_error:
            state, blocker = ReasoningStatus.ERROR, self.last_error
        else:
            state, blocker = ReasoningStatus.LIVE, ""

        return {
            "status": state,
            "available": state == ReasoningStatus.LIVE,
            "live": state == ReasoningStatus.LIVE,
            "provider": self.name,
            # "claude-opus-5" reads as "CLAUDE OPUS 5" on the status panel.
            # Prefixing "CLAUDE " would say it twice.
            "label": self.model.replace("-", " ").upper(),
            "model": self.model,
            "preview": False,
            "preview_notice": "",
            "credential_required": True,
            "credential_present": present,
            "credential_env": CREDENTIAL_ENV,
            "client_secret_used": False,
            "package_installed": installed,
            "fast_mode": self.fast,
            "effort": self.effort,
            "last_speed": self.last_speed,
            "blocker": blocker,
            # Stated as literals. No code path in this module sets them true.
            "can_approve": False,
            "can_decide": False,
            "can_send": False,
            "can_schedule": False,
            "can_modify_outlook": False,
            "can_modify_dispatch": False,
        }

    def sign_out(self) -> str:
        """There is no session to end. The key belongs to the environment."""
        return ("Nothing to sign out of - Claude is reached with a key held in "
                "the environment, not a session JOE owns.")

    # ---- the contract --------------------------------------------------

    def answer(self, question, context="", sources=None) -> Answer:
        return self._run("answer", question, context, sources)

    def summarize(self, material, sources=None) -> Answer:
        return self._run("summarize", "Summarize this.", material, sources)

    def explain(self, material, question="", sources=None) -> Answer:
        return self._run(
            "explain", question or "Explain this in plain language.",
            material, sources)

    def draft(self, instruction, context="", sources=None) -> Answer:
        return self._run("draft", instruction, context, sources)

    def recommend(self, question, context="", sources=None) -> Answer:
        return self._run("recommend", question, context, sources)

    def procedure(self, question, context="", sources=None) -> Answer:
        return self._run("procedure", question, context, sources)

    # ---- the call ------------------------------------------------------

    def _unavailable(self, task: str, reason: str) -> Answer:
        return Answer(
            text="", ok=False, task=task, provider=self.name,
            model=self.model, error=reason,
            status=ReasoningStatus.UNAVAILABLE,
        )

    def _prompt(self, instruction: str, context: str, sources) -> str:
        """The question, the context it must be answered from, and nothing else.

        Context is truncated rather than dropped, and the system framing tells
        Claude to say so when the context does not hold the answer - which is
        the behaviour that keeps a truncated context from becoming a guess."""
        body = [instruction.strip()]
        trimmed = (context or "").strip()[:self.max_context_chars]
        if trimmed:
            body += ["", "CONTEXT", trimmed]
        named = [str(s) for s in (sources or []) if str(s).strip()]
        if named:
            body += ["", "SOURCES", "\n".join("- " + s for s in named)]
        return "\n".join(body)

    def _run(self, task, instruction, context, sources) -> Answer:
        if not self.configured:
            return self._unavailable(
                task, "no API key is set in " + CREDENTIAL_ENV)
        try:
            client = self._sdk()
        except RuntimeError as error:
            return self._unavailable(task, str(error))

        system = SYSTEM_FRAMING
        framing = TASK_FRAMING.get(task, "")
        if framing:
            system = system + " " + framing

        request = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user",
                          "content": self._prompt(instruction, context, sources)}],
            "output_config": {"effort": self.effort},
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }

        reply = self._call(client, request, use_fast=self.fast)
        if isinstance(reply, Answer):
            return reply

        # A safety classifier declined. Say so; do not present it as an answer.
        if getattr(reply, "stop_reason", "") == "refusal":
            detail = getattr(reply, "stop_details", None)
            category = getattr(detail, "category", "") or "unspecified"
            self.last_error = "the request was declined (" + str(category) + ")"
            return Answer(
                text="", ok=False, task=task, provider=self.name,
                model=self.model, status=ReasoningStatus.ERROR,
                error=self.last_error,
            )

        text = "".join(
            getattr(block, "text", "") for block in (reply.content or [])
            if getattr(block, "type", "") == "text").strip()
        if not text:
            return self._unavailable(task, "the provider returned no text")

        self.last_error = ""
        self.last_speed = str(getattr(getattr(reply, "usage", None), "speed", "")
                              or ("fast" if self.fast else "standard"))
        named = [str(s) for s in (sources or []) if str(s).strip()]
        return Answer(
            text=text, ok=True, task=task, provider=self.name,
            model=self.model, grounded=bool(named), sources=named,
            status=ReasoningStatus.LIVE,
        )

    def _call(self, client, request, use_fast: bool):
        """One request, with fast mode dropped rather than allowed to fail."""
        import anthropic

        body = dict(request)
        if use_fast:
            body["speed"] = "fast"
            body["betas"] = list(body["betas"]) + [FAST_MODE_BETA]
        try:
            return client.beta.messages.create(**body)
        except anthropic.RateLimitError as error:
            if use_fast:
                # Fast mode has its own rate limit. A standard-speed answer
                # beats no answer.
                return self._call(client, request, use_fast=False)
            self.last_error = "rate limited: " + _brief(error)
            return self._unavailable(request.get("_task", "answer"),
                                     self.last_error)
        except anthropic.APIConnectionError as error:
            self.last_error = "could not reach Claude: " + _brief(error)
            return self._unavailable("answer", self.last_error)
        except anthropic.APIStatusError as error:
            if use_fast and getattr(error, "status_code", 0) in (400, 403, 404):
                # Fast mode unavailable for this model or account.
                return self._call(client, request, use_fast=False)
            self.last_error = "Claude returned an error: " + _brief(error)
            return self._unavailable("answer", self.last_error)
        except Exception as error:  # noqa: BLE001 - a failure must not close JOE
            self.last_error = _brief(error)
            return self._unavailable("answer", self.last_error)


def _brief(error) -> str:
    """A short reason. Never a key, never a token, never a full payload."""
    text = str(error).strip().replace("\n", " ")
    return (text[:160] + "...") if len(text) > 160 else (text or
                                                         type(error).__name__)
