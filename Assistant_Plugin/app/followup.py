"""One sentence, and the rest only when Mike asks for it.

JOE answers in a single sentence. Everything else waits. The premise of this
program is less for Mike to carry, and an answer delivered in full when one
line would do is more to carry, not less - he has to hold the whole thing while
deciding which part mattered.

"Explain more" is not a new question. It acts on the answer Mike just heard,
the way a retention command acts on the record he already has selected. So it
creates no memory record, does not move the selection, and never re-reads the
sentence he has already been told.

MATCHING IS WHOLE-UTTERANCE, NEVER SUBSTRING. "Please find the rate floor
policy" is a question that happens to be polite. "Please" on its own is Mike
asking for the rest. Matching a substring would turn every courteous request
into a repeat of the previous answer, which is the exact failure this module
exists to avoid.

NUMBERS ARE NOT SENTENCE ENDINGS. A rate of 2.75 contains a full stop and is
not two sentences. Getting that wrong would speak half a rate to a driver, so
the sentence finder is careful about decimals and abbreviations rather than
splitting on punctuation.
"""

from __future__ import annotations

import re

# A sentence Mike cannot hold in his head is not a short answer. Past this,
# the sentence is reported as too long rather than chopped - half a sentence
# about a rate is worse than a deferral.
MAX_SENTENCE_WORDS = 45

# Whole utterances that mean "give me the rest". Bare "explain" is deliberately
# absent: JOE has an EXPLAIN capability, and one word should not mean two
# different things depending on what came before it.
_EXPANSION_PHRASES = frozenset({
    "explain more",
    "please",
    "more",
    "more please",
    "explain more please",
    "tell me more",
    "say more",
    "go on",
    "continue",
    "elaborate",
    "expand",
    "expand on that",
    "the rest",
    "read the rest",
    "full answer",
    "the full answer",
    "more detail",
    "more details",
    "details",
    "what else",
    "and",
})

# Stripped before matching so "JOE, explain more" is the same request as
# "explain more".
_ADDRESS = re.compile(r"^\s*(hey\s+|ok\s+|okay\s+)?joe[\s,]+", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")

# Trailing full stops that belong to the word, not to the sentence.
_ABBREVIATIONS = (
    "a.m.", "p.m.", "mr.", "mrs.", "ms.", "dr.", "st.", "no.", "vs.",
    "etc.", "approx.", "dept.", "inc.", "ltd.", "co.", "u.s.", "i.e.",
    "e.g.", "jr.", "sr.", "rd.", "ave.", "blvd.", "hwy.", "mi.", "ft.",
)


def normalize(text: str) -> str:
    """Lowercase, unpunctuated, single-spaced - for matching only."""
    stripped = _ADDRESS.sub("", text or "")
    stripped = _PUNCT.sub(" ", stripped)
    return _SPACE.sub(" ", stripped).strip().lower()


def is_expansion_request(text: str) -> bool:
    """Is this whole utterance Mike asking for the rest of the last answer?"""
    return normalize(text) in _EXPANSION_PHRASES


def first_sentence(text: str) -> str:
    """The first real sentence, with decimals and abbreviations left intact.

    Returns the whole text when it contains no sentence break - a short answer
    with no full stop is already one sentence."""
    line = _SPACE.sub(" ", (text or "").strip())
    if not line:
        return ""

    index = 0
    length = len(line)
    while index < length:
        character = line[index]
        if character in ".!?":
            # 2.75 is a rate, not two sentences.
            if (character == "."
                    and index > 0 and line[index - 1].isdigit()
                    and index + 1 < length and line[index + 1].isdigit()):
                index += 1
                continue
            # "9 a.m." ends a phrase, not a sentence.
            head = line[:index + 1].lower()
            if any(head.endswith(abbrev) for abbrev in _ABBREVIATIONS):
                index += 1
                continue
            if index + 1 >= length or line[index + 1].isspace():
                return line[:index + 1]
        index += 1
    return line


def is_too_long(sentence: str) -> bool:
    return len(sentence.split()) > MAX_SENTENCE_WORDS


def speakable_finding(title: str, snippets) -> str:
    """What a document search is worth saying out loud.

    Mike asked what the policy says, not where the file lives. Naming the file
    answers a question he did not ask, in the least speakable form there is -
    "Sample Corpus slash Operations slash RATE underscore FLOOR underscore
    POLICY dot M D" is a path being read as though it were an answer. The path
    is genuinely useful on the screen he reads when parked, which is where it
    stays.

    Returns the title alone when there is no usable excerpt: a title is a poor
    answer, but it is still an answer, and inventing one is not an option."""
    name = str(title or "").strip()
    lines = [str(s).strip() for s in (snippets or []) if str(s).strip()]
    if not lines:
        return name

    lead = re.sub(r"^#+\s*", "", lines[0])           # markdown heading marks
    lead = lead.replace("…", "...")

    # A search excerpt is cut to a fixed width, so it usually ends mid-word:
    # "after fue...". Spoken, that becomes "after fyoo", which sounds like JOE
    # malfunctioning rather than like an answer. Note that it was cut, so the
    # fragment can be dropped below instead of being punctuated into a lie.
    elided = False
    while lead.rstrip().endswith("..."):
        lead = lead.rstrip()[:-3].rstrip()
        elided = True

    # Excerpts often repeat the document title before the text.
    if name and lead.lower().startswith(name.lower()):
        lead = lead[len(name):].lstrip(" :–—-")
    lead = _SPACE.sub(" ", lead).strip()

    if not lead:
        return name
    sentence = first_sentence(lead)
    if not sentence or is_too_long(sentence):
        return name

    if not sentence.endswith((".", "!", "?")):
        if elided:
            # No sentence ended inside the excerpt, so what is left runs into
            # the cut. Fall back to the last clause boundary - a clause that
            # stops cleanly is worth hearing; a severed word is not.
            boundary = max(sentence.rfind(","), sentence.rfind(";"))
            if boundary > 20:
                sentence = sentence[:boundary]
            else:
                sentence = sentence.rsplit(" ", 1)[0]
            if not sentence.strip():
                return name
        sentence = sentence.rstrip(" ,;:-–—") + "."
    return (name + ": " + sentence) if name else sentence


def rest_of(full_text: str, already_said: str) -> str:
    """The full answer with the sentence Mike already heard removed.

    Repeating it would spend his attention on something he has already been
    told, which is the cost this module exists to avoid."""
    full = (full_text or "").strip()
    said = (already_said or "").strip()
    if not full:
        return ""
    if said and full.lower().startswith(said.lower()):
        remainder = full[len(said):].lstrip(" \n\t")
        if remainder:
            return remainder
    return full
