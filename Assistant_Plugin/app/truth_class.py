"""What KIND of truth a question asks for. Doctrine v1.0, Part V.

Not how hard the question is. Who owns the answer.

  COMPANY   Level 1 Transport's own facts - our rates, our policy, our
            procedures, our records, our operations. Only an approved company
            source can settle these. If the Library has nothing, the honest
            answer is "there is no approved document on that", NOT a plausible
            industry figure. This is the rule "use only the CONTEXT supplied"
            was written to protect, and here it is kept exactly as strict as it
            has always been.

  GENERAL   Stable knowledge nobody owns. What a rate floor is, what deadhead
            means, how a fuel surcharge works, roughly how far Atlanta is.
            Answered from the model's own knowledge. No company context is
            required, and its absence is not a reason to refuse.

  LIVE      Facts that change: current weather, traffic, prices, hours, whether
            a place is open, which exit a truck stop sits at. These need a
            current source. Model memory alone is not one.

WHY THIS FILE EXISTS. Ask "research the distance to Atlanta" and JOE answered
"about 346 miles" with six citations. Ask "what is the distance to Atlanta" and
JOE answered "the supplied context does not contain" it. Same provider, same
network, same second. The difference was one word - and it is not a word a
driver says at seventy miles an hour.

That was never a safety boundary. It was a routing accident wearing one's
clothes. "Use only the CONTEXT supplied" was written to stop JOE inventing
company policy. It was applied to every question, including the ones where
there is no company policy to invent.

Guardrails belong on the sides of the road, not across it.

WHAT THIS DOES NOT TOUCH. Authority. Classifying a question as GENERAL or LIVE
lets JOE go and find out; it does not let JOE approve, accept, commit,
negotiate, transmit, or alter an operational record. Article III restricts what
JOE may DECIDE, not what JOE may KNOW.

Maximum capability. Minimum authority.
"""

from __future__ import annotations

import re

COMPANY = "COMPANY"
GENERAL = "GENERAL"
LIVE = "LIVE"

# Written-record labels. Doctrine sections 16 and 21.
LABELS = {
    COMPANY: "COMPANY TRUTH",
    GENERAL: "GENERAL KNOWLEDGE",
    LIVE: "LIVE RESEARCH",
}

# ---- COMPANY -----------------------------------------------------------
# Naming the firm, the system, or the people in it.
_OURS = r"level\s*1|l1\s+transport|dispatch|\bjoe\b|our\s+company|the\s+company"

# First person plural is the reliable tell: "our rate floor" is a company fact,
# "a rate floor" is a definition anyone can look up.
_POSSESSIVE = r"\b(our|ours|we|us)\b"

# First person singular counts only next to something we actually own. "my
# truck" is ours; "how long would it take me" is not.
_MINE = (
    r"\bmy\s+("
    r"load|loads|truck|trailer|rate|rates|broker|brokers|customer|customers|"
    r"appointment|appointments|schedule|calendar|inbox|mail|email|emails|"
    r"policy|policies|procedure|procedures|record|records|document|documents|"
    r"invoice|invoices|settlement|settlements|log|logs|hours|company|"
    r"authority|insurance|contract|contracts|lane|lanes|driver|drivers|"
    r"card|cards"
    r")\b"
)

# Things only Dispatch holds.
_ARTEFACTS = (
    r"opportunity card|mission card|\bthe card\b|current card|"
    r"\bopportunity\b|\bopportunities\b|"
    r"rate confirmation|\bpod\b|\bpou\b|bill of lading|"
    r"work calendar|pop procedure"
)

# Asking whether a counterparty DID something is asking about our records, not
# about brokers in general. "What is a broker" is a definition anyone can look
# up; "did a broker reply" can only be answered from Outlook. The verb is the
# tell, so the bare noun is deliberately left out of this pattern.
_COUNTERPARTY_EVENT = (
    r"\b(broker|brokers|shipper|shippers|receiver|receivers|consignee|"
    r"customer|customers|dispatcher)\b[^.?!]{0,40}?\b("
    r"repl(y|ied|ies)|respond(ed|s)?|answer(ed|s)?|call(ed|s)?|"
    r"email(ed|s)?|contact(ed|s)?|confirm(ed|s)?|sen[dt]|got back"
    r")\b"
)

_COMPANY_PATTERN = re.compile(
    "(" + _OURS + ")|" + _POSSESSIVE + "|" + _MINE
    + "|(" + _ARTEFACTS + ")|(" + _COUNTERPARTY_EVENT + ")",
    re.IGNORECASE,
)

# ---- LIVE --------------------------------------------------------------
# A fact is LIVE when its truth depends on when you ask. Doctrine section 18.
_LIVE_PATTERNS = (
    # time-dependence, stated outright
    r"\b(current|currently|right now|at the moment|as of now|today|todays|"
    r"tonight|tomorrow|this week|this morning|this afternoon|latest|newest|"
    r"up to date|nowadays|these days)\b",
    # conditions on the road
    r"\b(weather|forecast|temperature|storm|hurricane|"
    r"traffic|congestion|accident|construction|detour|road closure|closure|"
    r"closed|shut down|delay|delays|backup)\b",
    # money that moves
    r"\b(price|prices|pricing|cost|costs|fuel price|"
    r"diesel price|gas price|toll|tolls|going rate|market rate)\b",
    # finding a physical place
    r"\b(where is|where.s|nearest|closest|next exit|exit number|what exit|"
    r"which exit|exit for|located at|location of|address of|phone number|"
    r"directions to|open now|still open|hours of operation)\b",
    # named facilities a driver stops at - their exits and hours change
    r"(\btruck ?stop|\brest area|\bweigh station|\bscale house|"
    r"love.s travel|\bloves\b|\blove.s\b|\bpilot\b|flying j|ta petro|"
    r"petro stopping|buc-ee|quiktrip|\bwawa\b|parking availability)",
    # status of a changeable thing
    r"\b(is .{0,30} open|has .{0,30} changed|status of|still in effect|"
    r"still valid|been updated|any news)\b",
    # shipper/receiver operating hours
    r"\b(shipper|receiver|consignee) hours\b",
)

_LIVE_PATTERN = re.compile("|".join(_LIVE_PATTERNS), re.IGNORECASE)


def classify(question: str) -> str:
    """COMPANY, LIVE or GENERAL.

    Order matters. COMPANY is asked first because "what is the current rate on
    my load" is a company question about a company record, not a web lookup -
    the web cannot know it and must not be asked.

    Biased toward answering. A GENERAL question misread as LIVE costs a web
    search. A LIVE question misread as GENERAL is contained downstream, because
    a GENERAL answer is labelled GENERAL KNOWLEDGE and never claims to be
    current.
    """
    text = (question or "").strip()
    if not text:
        return GENERAL
    if _COMPANY_PATTERN.search(text):
        return COMPANY
    if _LIVE_PATTERN.search(text):
        return LIVE
    return GENERAL


def is_company_question(question: str) -> bool:
    return classify(question) == COMPANY


def label_for(truth_class: str) -> str:
    """The written-record heading for a class. Sections 16 and 21."""
    return LABELS.get(truth_class, LABELS[GENERAL])


# ---- Library relevance -------------------------------------------------
# A Library search is word overlap, so it nearly always returns something. The
# question "driving distance between Jacksonville and Atlanta" matched two
# Level 1 Vision documents on the words "driving", "jacksonville" and
# "florida", while missing "distance", "atlanta" and "georgia" entirely. Those
# documents were then handed over as CONTEXT, and the model answered -
# correctly - that the context did not contain the distance.
#
# So "did the Library return hits" is the wrong question. It always does. The
# right question is whether a hit actually covers what was asked.
MINIMUM_TERM_COVERAGE = 0.6


def hit_coverage(hit) -> float:
    """How much of the question this hit actually matched, 0.0 to 1.0."""
    if not isinstance(hit, dict):
        return 1.0  # unknown shape: assume retrieval knew what it was doing
    matched = len(hit.get("matched_terms") or [])
    missing = len(hit.get("missing_terms") or [])
    total = matched + missing
    if total == 0:
        return 0.0
    return matched / total


def library_answers_this(hits) -> bool:
    """True when at least one hit covers enough of the question to be an answer.

    Deliberately generous to the Library: one good hit is enough, and a hit
    whose shape is unrecognised counts as good. This exists to catch the
    "matched on the word driving" case, not to second-guess retrieval.
    """
    return any(hit_coverage(h) >= MINIMUM_TERM_COVERAGE for h in (hits or []))
