"""An audience, benefit, or use case is stated only when an accepted fact states it.

Acceptance review of the wave-3 reseal (f69f75c7, five sealed candidates, 4 of 5 affected): the
opening named who uses the library and what for ("Developers use it to generate reports ...",
"It is used by Java developers building applications ... such as CAD viewers, simulation tools,
and 3D printing workflows", "Users include Java developers who need to generate reports, process
financial data ...") and what it spares them ("without requiring a commercial license"). No fact
and no inherited README text said any of it. Every other check passed it: BC-04 judges identifiers
and citations, and a citation is satisfied by identity and package facts that carry no audience at
all (the investigation's own ``audience`` statement cites ``identity:platform`` and
``package:target_framework``). The cause was upstream of every check: the opening's objective, and
the contract row it restated, asked for "who uses it", a thing no fact extractor records, so the
model filled the request from the platform name.

This module is the deterministic half of the fix (the objective and the prompt are the other). A
sentence of an authored unit that makes an audience, suitability, usage, or spared-cost claim
(``_PATTERNS``) is refused unless the claim, word for word in substance, is already in the text of
an accepted fact the unit may cite - a package description, or an inherited README unit
reconciliation kept (VERIFIED_PRESERVE, VERIFIED_REWRITE, VERIFIED_MOVE) into that section. "In
substance" is the content words of the claim, from the trigger phrase to the end of its sentence,
all appearing within one sentence (or two adjacent ones) of one supporting text: a paraphrase of a
kept sentence passes, and a kept sentence extended with one invented use case does not.

It sits beside ``authoring.py`` and imports nothing from it, so ``unit_checks`` can call it. The
refusal names the sentence and the rule, so the one re-ask can drop it; ``strip_audience_units``
is the last resort when the re-ask repeats it, and only ever deletes (a trailing clause, or the
whole sentence), never rewrites.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Mapping
from typing import Any

from repository_presenter.core.facts import FactsDocument

# The sections whose authored prose is a statement about the product as a whole. A capability,
# limitation, or link unit is bound to its own slot's facts by README_CONTRACT.md check 4 and
# describes what that slot does, not who the library is for.
AUDIENCE_SECTIONS = frozenset({"opening"})

_ROLE = (
    r"(?:developers?|programmers?|engineers?|coders?|teams?|users?|analysts?|scientists?|"
    r"researchers?|testers?|integrators?|professionals?|practitioners?|maintainers?|"
    r"designers?|artists?|students?|hobbyists?|beginners?|experts?|customers?|clients?|"
    r"organi[sz]ations?|businesses|companies|enterprises|people|anyone|everyone|you)"
)
# Up to two words between a preposition or verb and the role it governs ("Java developers",
# ".NET Core developers", "end users"), none of them an article, preposition, or conjunction, so
# "by passing the user or owner password" is not "by ... users".
_MODIFIERS = (
    r"(?:(?!(?:the|a|an|this|that|these|those|your|its|their|our|of|to|in|on|with|each|every|"
    r"and|or|as|at|is|are)\b)[\w.#+/-]+\s+){0,2}?"
)
_WORD = r"[\w-]+"

# Each pattern is one way of saying who the product is for, where it is useful, or what it spares
# the reader. They are phrases, not topics: "reads and writes XLSX files" and "targets net8.0"
# name no audience, and a role noun alone ("Developer Guide") is not matched.
_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # "enables developers to ...", "lets you ...", "helps teams ..."
        r"\b(?:enables?|enabling|allows?|allowing|lets?|letting|helps?|helping|empowers?|"
        r"empowering|equips?|equipping)\s+(?:(?:the|all|any)\s+)?" + _MODIFIERS + _ROLE + r"\b",
        # "Developers use it to ...", "Users include ...", "teams who need ...", "users building"
        r"\b" + _ROLE + r"\s+(?:can\s+|may\s+|typically\s+|commonly\s+|often\s+)*"
        r"(?:use|uses|using|include|includes|including|who|that|building|build|builds|"
        r"needing|need|needs|wanting|want|wants|looking|seeking|working|benefit|benefits|"
        r"rely|relies|writing|creating|developing)\b",
        # "for Java developers", "used by teams", "aimed at analysts"
        r"\b(?:for|by|among|targeting)\s+(?:(?:all|any|many|most|both)\s+)?"
        + _MODIFIERS
        + _ROLE
        + r"\b",
        # "Users across engineering domains ...", "teams in finance ..."
        r"\b" + _ROLE + r"\s+(?:in|across|within|from|at)\b",
        # "commonly used", "widely used"
        r"\b(?:widely|commonly|typically|often|frequently|primarily|mainly|mostly)\s+used\b",
        # "ideal for", "suitable for", "designed for", "making it suitable"
        r"\b(?:ideal|ideally\s+suited|well[- ]suited|best\s+suited|suitable|suited|perfect|"
        r"perfectly\s+suited|great|excellent|useful|handy|helpful|valuable|beneficial|"
        r"appropriate)\s+(?:for|to|when|if)\b",
        r"\b(?:designed|intended|aimed|geared|tailored|targeted)\s+(?:for|at|toward|towards)\b",
        r"\b(?:making|makes|made)\s+it\s+(?:\w+\s+)?(?:suitable|ideal|useful|perfect|attractive|"
        r"appealing|well[- ]suited|a\s+good\s+fit|a\s+great\s+fit)\b",
        # use-case framing
        r"\buse[- ]cases?\b",
        r"\b(?:whether|if|when)\s+you(?:'re|\s+are|\s+need|\s+want)?\b",
        r"\bfor\s+(?:those|anyone|everyone|people)\b",
        # what the product spares the reader
        r"\bwithout\s+(?:(?:requiring|needing|the\s+need\s+for|having\s+to\s+\w+(?:\s+for)?)\s+)?"
        r"(?:an?\s+|the\s+|any\s+)?(?:" + _WORD + r"\s+){0,2}?"
        r"(?:licen[cs]es?|licen[cs]ing|suites?|subscriptions?|purchases?|fees?|payments?)\b",
        r"\b(?:saves?|spares?|eliminates?|removes?|reduces?|avoids?)\s+(?:the\s+)?"
        r"(?:need|time|effort|hassle|cost|burden|complexity|boilerplate|overhead)\b",
        r"\b(?:simplif(?:y|ies|ying)|streamlin(?:e|es|ing)|accelerat(?:e|es|ing)|"
        r"speed(?:s|ing)?\s+up)\b",
    )
)

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[])")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+")
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    {"the", "and", "for", "with", "that", "this", "are", "not", "but", "its", "can", "has", "have"}
    | {"was", "were", "any", "all", "from", "into", "than", "via", "who", "which", "such", "also"}
    | {"their", "they", "them", "you", "your", "our", "out", "own", "per", "etc", "use", "uses"}
)
_STEM = 5
_QUOTE_LIMIT = 200
_TRAILING_CONNECTORS = frozenset(
    {"and", "or", "but", "so", "that", "which", "who", "to", "for", "of", "by", "in", "with"}
    | {"making", "makes", "while", "when", "where", "enabling", "allowing"}
)
_MIN_HEAD_WORDS = 5
# A clause cut off before an audience phrase is kept only when it still has a predicate; a head
# such as "Aspose.Note FOSS for Python version 26.3.2" (its verb was "enables ...") is a fragment,
# and the whole sentence goes instead. A short list of the verbs openings use, not a parser: a head
# with none of them is dropped, which only ever deletes more.
_PREDICATE = re.compile(
    r"\b(?:is|are|was|provides?|offers?|supports?|reads?|writes?|converts?|creates?|generates?|"
    r"renders?|parses?|loads?|saves?|exports?|imports?|targets?|requires?|runs?|exposes?|"
    r"includes?|handles?|models?|implements?|processes|contains?|has|have|uses?|depends?|"
    r"ships?|works?|extracts?|builds?|manipulates?|edits?|opens?|serializes?|validates?)\b",
    re.IGNORECASE,
)

UNSUPPORTED_AUDIENCE = "states an audience, benefit, or use case that no accepted fact states"


def support_texts(accepted_ids: Collection[str], facts: FactsDocument) -> list[str]:
    """The text an audience claim may rest on: the value of every SUPPORTED fact in the section's
    accepted set - package and identity facts, and the inherited README units reconciliation kept
    in the section - and nothing else (an inherited unit it dropped or superseded is not here)."""
    return [
        fact.value
        for fact in facts.facts
        if fact.id in accepted_ids and fact.polarity == "SUPPORTED"
    ]


def sentences(text: str) -> list[str]:
    """``text`` as sentences, in order, a bullet marker dropped."""
    found: list[str] = []
    for raw in text.splitlines():
        line = _BULLET.sub("", raw).strip()
        found.extend(part.strip() for part in _SENTENCE_BREAK.split(line) if part.strip())
    return found


def content_words(text: str) -> frozenset[str]:
    """The stems of ``text``'s words that carry meaning: no stopwords, none under three letters."""
    return frozenset(
        word[:_STEM]
        for word in _TOKEN.findall(text.lower())
        if len(word) > 2 and word not in _STOPWORDS
    )


def trigger_start(sentence: str) -> int | None:
    """Where the first audience, benefit, or use-case phrase of ``sentence`` begins, or ``None``."""
    starts = [match.start() for pattern in _PATTERNS if (match := pattern.search(sentence))]
    return min(starts) if starts else None


def _support_windows(support: Iterable[str]) -> list[frozenset[str]]:
    """Every sentence of every supporting text, and every pair of adjacent sentences, as the sets
    of content words a claim may be found inside."""
    windows: list[frozenset[str]] = []
    for text in support:
        parts = [content_words(sentence) for sentence in sentences(text)]
        windows.extend(parts)
        windows.extend(parts[index] | parts[index + 1] for index in range(len(parts) - 1))
    return windows


def unsupported_audience_sentences(text: str, support: Iterable[str]) -> list[str]:
    """The sentences of ``text`` that make an audience, benefit, or use-case claim no ``support``
    text makes, in order. A claim is supported when every content word from its trigger phrase to
    the end of its sentence appears inside one sentence (or two adjacent ones) of one text."""
    texts = list(support)
    windows: list[frozenset[str]] | None = None
    unsupported: list[str] = []
    for sentence in sentences(text):
        start = trigger_start(sentence)
        if start is None:
            continue
        claim = content_words(sentence[start:])
        if windows is None:
            windows = _support_windows(texts)
        if not any(claim <= window for window in windows):
            unsupported.append(sentence)
    return unsupported


def audience_errors(
    units: Iterable[Mapping[str, Any]], support: Iterable[str], section: str
) -> list[str]:
    """One refusal per unit sentence that states an unsupported audience, benefit, or use case,
    for a section in ``AUDIENCE_SECTIONS``; empty otherwise. The refusal quotes the sentence so
    the re-ask can delete or replace exactly it."""
    if section not in AUDIENCE_SECTIONS:
        return []
    texts = list(support)
    errors: list[str] = []
    for unit in units:
        for sentence in unsupported_audience_sentences(str(unit.get("text", "")), texts):
            quoted = sentence if len(sentence) <= _QUOTE_LIMIT else sentence[:_QUOTE_LIMIT] + "..."
            errors.append(
                f"unit {unit.get('slot')}: {UNSUPPORTED_AUDIENCE} ({quoted!r}); state what the "
                "product is and does from the cited facts, as its own actions (it reads, writes, "
                "converts ...), and delete the audience, use-case, suitability, or 'without "
                "requiring ...' wording without replacing it by another"
            )
    return errors


def _trimmed(sentence: str, start: int) -> str | None:
    """``sentence`` cut back to the clause before ``start`` when that clause is a sentence on its
    own, else ``None`` (the whole sentence goes)."""
    words = sentence[:start].rstrip(" ,;:-").split()
    while words and words[-1].lower().strip(",;:") in _TRAILING_CONNECTORS:
        words.pop()
    head = " ".join(words).rstrip(",;:")
    if len(words) < _MIN_HEAD_WORDS or _PREDICATE.search(head) is None:
        return None
    return head + "."


def strip_audience_claims(text: str, support: Iterable[str]) -> str | None:
    """``text`` with each unsupported audience claim deleted - a trailing clause when the part
    before it stands as a sentence, the whole sentence otherwise - or ``None`` when nothing was
    found or nothing would be left. Only ever deletes: no word is added or changed."""
    flagged = set(unsupported_audience_sentences(text, support))
    if not flagged:
        return None
    kept: list[str] = []
    for sentence in sentences(text):
        if sentence not in flagged:
            kept.append(sentence)
            continue
        start = trigger_start(sentence)
        trimmed = _trimmed(sentence, start) if start is not None else None
        if trimmed is not None:
            kept.append(trimmed)
    return " ".join(kept) if kept else None


def strip_audience_units(
    output: dict[str, Any], support: Iterable[str], section: str
) -> dict[str, Any] | None:
    """Last-resort correction for a ``section_authoring`` reply: the unsupported audience claims
    of each unit removed in place by ``strip_audience_claims``. ``None`` when the section is not
    one of ``AUDIENCE_SECTIONS`` or nothing changed - never a no-op copy of ``output``. A unit
    that would be left empty is untouched (the refusal stands and the job fails closed)."""
    if section not in AUDIENCE_SECTIONS:
        return None
    units = output.get("units")
    if not isinstance(units, list):
        return None
    texts = list(support)
    changed = False
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("text"), str):
            continue
        stripped = strip_audience_claims(unit["text"], texts)
        if stripped is not None:
            unit["text"] = stripped
            changed = True
    return output if changed else None
