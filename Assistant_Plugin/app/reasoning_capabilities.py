"""Reasoning-backed capabilities: summarize, draft, procedure, explain, answer.

Kept out of service.py so the core stays about routing and lifecycle. Mixed
into AssistantService, which supplies `self.library`, `self.reasoning`, and
`self.outlook`.

Every capability here follows the same shape:

  1. retrieve grounding material, if any exists
  2. if no provider is bound, say so - or hand back the material unsummarized
  3. otherwise ask the provider, with the retrieved material as its only context
  4. return the answer with its sources attached, or with a plain statement
     that it was general reasoning and not read from anywhere

The provider never sees a request without the framing in
`adapters/reasoning_provider.py`, and its answer still passes the governance
gate like any other response.
"""

from __future__ import annotations

from contracts import (
    AssistantResponse,
    Capability,
    Provenance,
    SourceClass,
    SourceMode,
    ReasoningMode,
)

NO_REASONING_PROVIDER = (
    "No reasoning provider is connected to JOE, so I cannot compose "
    "an original answer. What I can do is search approved Library material, "
    "read Outlook read-only, report research from supplied briefs, and hold "
    "this interaction under the retention rules."
)

UNGROUNDED_NOTICE = (
    "General reasoning - not sourced live research, and not read from the "
    "Company Library, Outlook, or Dispatch."
)

# A hit only grounds an answer if it matched a term with some substance in it.
#
# Without this, "How do I zzzqqqxyz" matches documents on the words "do" and
# "i" alone, and JOE would cite an unrelated document as governing
# procedure. Requiring one matched term of at least this length is a rule that
# can be read and predicted.
MIN_GROUNDING_TERM = 4

# Words that carry no subject. Matching on these says nothing about whether a
# document is ABOUT the question.
_STOPWORDS = frozenset("""
a an and are as at be been between but by can could did do does explain for
from had has have how i if in into is it its me my of on or should show
tell that the their them then there these they this to under up us was were
what when where which who why will with would you your about difference
differences mean means matter matters
""".split())

# What share of a question's distinctive words a document must match before it
# counts as being about that question.
MIN_SUBJECT_COVERAGE = 0.5


def headline(text: str, limit: int = 300) -> str:
    """The first line that actually says something.

    Copilot formats replies with a label line - "**Immediate answer:**" - and
    puts the answer underneath. Taking line one made that label the headline,
    so every reasoned answer opened with "**Immediate answer:**" and driver
    mode SPOKE it: "Immediate answer. No decision needed right now." A label
    is not an answer, and read aloud it is worse than silence.

    Skips markdown headings, bare labels, rules, and empty lines, then strips
    inline emphasis so what remains reads aloud cleanly."""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if set(line) <= set("-=*_ "):                  # a horizontal rule
            continue
        stripped = line.strip("*_` ").strip()
        # A short line ending in a colon labels what follows; it is not it.
        if stripped.endswith(":") and len(stripped) <= 40:
            continue
        stripped = stripped.lstrip("-*0123456789. ").strip()
        stripped = stripped.replace("**", "").replace("__", "").replace("`", "")
        if stripped:
            return stripped[:limit]
    return (text or "").strip()[:limit]


def _subject_terms(subject: str) -> set:
    """The distinctive words of a question, stopwords removed."""
    cleaned = "".join(c.lower() if (c.isalnum() or c.isspace()) else " " for c in subject)
    return {
        word for word in cleaned.split()
        if len(word) >= MIN_GROUNDING_TERM and word not in _STOPWORDS
    }


def _is_real_match(hit: dict, subject: str = "") -> bool:
    """Is this document actually ABOUT the question, or did it just share words?

    Term length alone is not enough. "Explain the difference between a live
    unload and a drop-and-hook" matched documents on `between`, `live`, and
    `unload` - all long enough to pass a length test, none of them evidence the
    Library covers drop-and-hook. Copilot was then handed that material and
    dutifully replied that the supplied context did not define the terms, which
    read as JOE being unable to answer a basic industry question.

    Coverage of the question's distinctive words is the test instead."""
    matched = {str(t).lower() for t in hit.get("matched_terms", [])}
    strong = {t for t in matched if len(t) >= MIN_GROUNDING_TERM and t not in _STOPWORDS}
    if not strong:
        return False
    wanted = _subject_terms(subject)
    if not wanted:
        return True          # nothing distinctive to cover; length test stands
    return len(strong & wanted) / len(wanted) >= MIN_SUBJECT_COVERAGE


class ReasoningCapabilities:
    """Mixin. Requires self.library, self.reasoning, self.outlook."""

    # ---- grounding ----------------------------------------------------

    def _library_context(self, subject: str, limit: int = 3):
        """Retrieve grounding material. Returns (context, sources, hits)."""
        probe = self.library.probe()
        if not probe["available"]:
            return "", [], []
        hits = [
            h for h in self.library.search(subject, limit=limit)
            if _is_real_match(h, subject)
        ]
        if not hits:
            return "", [], []
        chunks: list[str] = []
        sources: list[str] = []
        for hit in hits:
            document = self.library.get(hit["doc_id"])
            if not document:
                continue
            label = "COMPANY LIBRARY" if hit["is_company"] else "SAMPLE DATA"
            chunks.append(
                "--- "
                + hit["title"]
                + "  ["
                + label
                + "]  ("
                + hit["source_name"]
                + "/"
                + hit["relative_path"]
                + ") ---\n"
                + str(document.get("text", ""))[:4000]
            )
            sources.append(hit["reference"])
        return "\n\n".join(chunks), sources, hits

    def _reasoning_live(self) -> bool:
        return bool(self.reasoning.status().get("live"))

    # ---- honest failure -----------------------------------------------

    def _no_reasoning(self, capability: str, what: str) -> AssistantResponse:
        state = self.reasoning.status()
        return AssistantResponse(
            capability=capability,
            answer="I cannot " + what + " - no reasoning provider is connected.",
            written=(
                state["status"]
                + "\n\n"
                + state["blocker"]
                + "\n\n"
                + NO_REASONING_PROVIDER
                + "\n\nI have not produced anything that would read like an "
                "answer without one."
            ),
            ok=False,
            failure="reasoning not available",
            uncertainty="Nothing was composed. No provider answered.",
            provenance=[
                Provenance(
                    source="Reasoning provider",
                    mode=SourceMode.UNAVAILABLE,
                    detail=state["blocker"],
                )
            ],
        )

    # ---- wrapping a provider answer -----------------------------------

    def _reasoned(
        self,
        capability: str,
        answer,
        sources: list,
        hits: list,
        header: str = "",
        extra_notices: list | None = None,
    ) -> AssistantResponse:
        if not answer.ok:
            return AssistantResponse(
                capability=capability,
                answer="The reasoning provider did not answer.",
                written=answer.status + "\n\n" + answer.error,
                ok=False,
                failure="reasoning failed",
                provenance=[answer.provenance()],
            )

        body = ([header, ""] if header else []) + [answer.text]
        if sources:
            body += ["", "GROUNDED IN", ""] + ["  - " + s for s in sources]
        else:
            body += ["", UNGROUNDED_NOTICE]

        # The provider classifies its own grounding; local reads keep theirs.
        if hasattr(self.reasoning, "provenance_for"):
            provenance = [self.reasoning.provenance_for(answer)]
        else:
            provenance = [answer.provenance()]
        for hit in hits[:3]:
            provenance.append(self.library.provenance_for(hit))

        response = AssistantResponse(
            capability=capability,
            answer=headline(answer.text),
            written="\n".join(body),
            citations=list(sources),
            provenance=provenance,
            uncertainty=(
                ""
                if sources
                else "No source was retrieved; treat this as general reasoning."
            ),
        )
        for notice in extra_notices or []:
            response.add_notice(notice)
        if not sources:
            response.add_notice(UNGROUNDED_NOTICE)

        # Copilot grounding is never a local read. Say which is which.
        if response.has_copilot_source and not response.has_local_source:
            response.add_notice(
                "Grounded by Microsoft 365 Copilot, not read directly from the "
                "Company Library, Outlook, or Dispatch."
            )
        if getattr(answer, "sensitivity_label", ""):
            response.add_notice(
                "Sensitivity label carried from the source: "
                + answer.sensitivity_label
            )
        return response

    # ---- capabilities -------------------------------------------------

    # Phrases a provider uses when the material it was handed did not cover
    # the question. Not failures - it is being honest about its context.
    _CONTEXT_MISS = (
        "does not contain", "does not define", "does not discuss",
        "does not explain", "not contain a definition", "no internal results",
        "cannot answer from the sup", "supplied context does not",
        "supplied material does not", "found no matching enterprise content",
    )

    @classmethod
    def _context_missed(cls, text: str) -> bool:
        lowered = (text or "").lower()
        return any(phrase in lowered for phrase in cls._CONTEXT_MISS)

    def _retry_ungrounded(self, capability, request, answer, header):
        """Ask again with no context when the material handed over missed.

        A weak keyword match should not starve a question that general industry
        knowledge answers easily. "Explain what a drop-and-hook is" matched a
        document on the word "drop", and the reply came back "the supplied
        context does not contain a definition of drop-and-hook" - which reads
        as JOE being unable to answer a basic industry question.

        The retry also covers context carried by the CONVERSATION rather than
        passed on this call, which is why it does not test whether context was
        supplied - only whether the reply says the context missed.

        Returns a response, or None to leave the original answer alone. The
        retry is labelled GENERAL_REASONING and never as company material."""
        if not self._context_missed(getattr(answer, "text", "")):
            return None
        try:
            retry = self.reasoning.answer(request.text, "", [])
        except Exception:  # noqa: BLE001 - a failed retry is not a failed answer
            return None
        if not getattr(retry, "ok", False):
            return None
        if self._context_missed(getattr(retry, "text", "")):
            return None
        response = self._reasoned(capability, retry, [], [], header)
        response.reasoning_mode = self._mode_from_response(response)
        response.add_notice(
            "The Company Library had nothing covering this, so this is general "
            "industry knowledge - not Level 1 Transport doctrine."
        )
        return response

    @staticmethod
    def _mode_from_response(response) -> str:
        """Report the mode JOE ACTUALLY reasoned in, read off the provenance.

        Predicting the mode before the call does not work. Copilot chooses its
        own grounding per turn - the same question can come back general one
        minute and work-grounded the next - so a predicted mode collides with
        reality and the governance gate refuses a perfectly good answer.

        For open questions the mode is a description, not a constraint. The one
        genuine constraint is COMPANY_PROCEDURE, and that is enforced where it
        belongs: in _handle_procedure, by discarding an answer that came from
        the wrong place rather than by mislabelling it."""
        classes = {p.source_class for p in response.provenance if p.source_class}
        if SourceClass.COPILOT_WEB_GROUNDED in classes:
            return ReasoningMode.WEB_GROUNDED_RESEARCH
        if SourceClass.COPILOT_WORK_GROUNDED in classes:
            return ReasoningMode.WORK_GROUNDED
        if SourceClass.COPILOT_GENERAL_REASONING in classes:
            return ReasoningMode.GENERAL_REASONING
        if SourceClass.LOCAL_LIBRARY in classes:
            return ReasoningMode.SELECTED_DOCUMENT
        return ReasoningMode.GENERAL_REASONING

    def _provider_call(self, preferred: str, *args):
        """Use the provider's specialised method when it has one, else answer().

        ReasoningProvider declares answer, draft, summarize, and recommend.
        `explain` and `procedure` are Copilot extensions. Calling one
        unconditionally would break any provider implementing only the
        contract - which is the whole point of having a contract."""
        method = getattr(self.reasoning, preferred, None)
        if callable(method):
            return method(*args)
        return self.reasoning.answer(*args)

    def _handle_explain(self, request, chosen) -> AssistantResponse:
        """Explain approved material. With no provider, show the material.

        This handler predated the reasoning provider and never called one. It
        returned Library text verbatim and asserted "no reasoning provider is
        connected" - which stopped being true the moment Copilot signed in, and
        was the reason the first live Copilot proof answered from the Library
        without Copilot ever being asked."""
        subject = chosen.subject or request.text
        context, sources, hits = self._library_context(subject)

        if not self._reasoning_live():
            if hits:
                fallback = self._handle_library(request, chosen)
                fallback.capability = Capability.EXPLAIN
                fallback.add_notice(
                    "No reasoning provider is connected, so this is the matching "
                    "material rather than an explanation of it."
                )
                return fallback
            return self._no_reasoning(Capability.EXPLAIN, "explain that")

        answer = self._provider_call("explain", context or subject, request.text, sources)

        retried = self._retry_ungrounded(Capability.EXPLAIN, request, answer,
                                         "EXPLANATION")
        if retried is not None:
            return retried

        response = self._reasoned(Capability.EXPLAIN, answer, sources, hits, "EXPLANATION")
        response.reasoning_mode = self._mode_from_response(response)
        return response

    def _handle_answer(self, request, chosen) -> AssistantResponse:
        """No route matched. Ask the provider, or search the Library.

        Like _handle_explain, this asserted there was no provider in its own
        answer text. That text shipped unchanged into a signed-in session."""
        subject = chosen.subject or request.text
        context, sources, hits = self._library_context(subject)

        if not self._reasoning_live():
            if hits:
                fallback = self._handle_library(request, chosen)
                fallback.capability = Capability.ANSWER
                fallback.add_notice(
                    "No reasoning provider is connected, so this is approved "
                    "Library material rather than an answer to what you asked."
                )
                return fallback
            return self._no_reasoning(Capability.ANSWER, "answer that")

        answer = self.reasoning.answer(request.text, context, sources)
        retried = self._retry_ungrounded(Capability.ANSWER, request, answer, "")
        if retried is not None:
            return retried
        response = self._reasoned(Capability.ANSWER, answer, sources, hits)
        response.reasoning_mode = self._mode_from_response(response)
        return response

    def _handle_summarize(self, request, chosen) -> AssistantResponse:
        subject = chosen.subject or request.text
        context, sources, hits = self._library_context(subject)
        if not self._reasoning_live():
            if hits:
                fallback = self._handle_library(request, chosen)
                fallback.capability = Capability.SUMMARIZE
                fallback.add_notice(
                    "No reasoning provider is connected, so this is the matching "
                    "material rather than a summary of it."
                )
                return fallback
            return self._no_reasoning(Capability.SUMMARIZE, "summarize that")
        answer = self.reasoning.summarize(context or subject, sources)
        response = self._reasoned(Capability.SUMMARIZE, answer, sources, hits, "SUMMARY")
        # Summarising material JOE selected and read. If Copilot reached wider
        # than that, say so rather than calling it a document summary.
        response.reasoning_mode = (
            ReasoningMode.SELECTED_DOCUMENT if sources
            else self._mode_from_response(response)
        )
        return response

    def _handle_draft(self, request, chosen) -> AssistantResponse:
        subject = chosen.subject or request.text
        context, sources, hits = self._library_context(subject, limit=2)
        if not self._reasoning_live():
            return self._no_reasoning(Capability.DRAFT, "write that draft")
        answer = self.reasoning.draft(request.text, context, sources)
        response = self._reasoned(
            Capability.DRAFT,
            answer,
            sources,
            hits,
            "DRAFT ONLY - NOT SENT",
            ["DRAFT ONLY. NOT SENT. Nothing was transmitted to anyone."],
        )
        if response.ok:
            response.written = (
                "DRAFT ONLY\nNOT SENT\n\n"
                + response.written
                + "\n\nJOE cannot send anything. Sending requires your "
                "approval and a separately authorized transport system."
            )
        return response

    def _handle_procedure(self, request, chosen) -> AssistantResponse:
        subject = chosen.subject or request.text
        context, sources, hits = self._library_context(subject)
        if not sources:
            return AssistantResponse(
                capability=Capability.PROCEDURE,
                answer=("No approved Level 1 Transport procedure was found for "
                        "this question."),
                written=(
                    "I searched the configured Library for a governing document "
                    'covering "' + subject + '" and found none.\n\n'
                    "I will not invent company procedure. If a governing document "
                    "exists, add its location under library.sources in "
                    "configuration/joe.config.json."
                ),
                ok=False,
                failure="no governing document",
                reasoning_mode=ReasoningMode.COMPANY_PROCEDURE,
                uncertainty="No governing document was found.",
                provenance=[Provenance(source="Library", mode=SourceMode.SAMPLE)],
            )
        if not self._reasoning_live():
            fallback = self._handle_library(request, chosen)
            fallback.capability = Capability.PROCEDURE
            fallback.add_notice(
                "No reasoning provider is connected, so this is the governing "
                "material rather than a step-by-step explanation of it."
            )
            return fallback
        answer = self._provider_call("procedure", request.text, context, sources)
        response = self._reasoned(
            Capability.PROCEDURE,
            answer,
            sources,
            hits,
            "PROCEDURE - from the governing document(s) named below",
        )
        # Company procedure comes from approved Library material. Copilot may
        # EXPLAIN that material; it may not supply the procedure.
        #
        # Copilot chooses its own grounding, and for a procedure question it
        # will sometimes reach into tenant data and return WORK_GROUNDED. That
        # is not Level 1 Transport procedure - it could be anyone's email. The
        # answer is discarded and the governing document shown instead.
        #
        # Discarded, not refused: a blanket refusal told Mike his response
        # "claimed authority I do not have", which was both useless and untrue.
        offending = sorted({
            p.source_class for p in response.provenance
            if p.source_class in (SourceClass.COPILOT_WORK_GROUNDED,
                                  SourceClass.COPILOT_WEB_GROUNDED)
        })
        if offending:
            fallback = self._handle_library(request, chosen)
            fallback.capability = Capability.PROCEDURE
            fallback.reasoning_mode = ReasoningMode.COMPANY_PROCEDURE
            fallback.add_notice(
                "Company procedure comes from approved Library material only. "
                "The reasoning provider answered from " + ", ".join(offending)
                + " instead, so that answer was discarded and the governing "
                "material is shown as it stands."
            )
            return fallback

        response.reasoning_mode = ReasoningMode.COMPANY_PROCEDURE
        return response
