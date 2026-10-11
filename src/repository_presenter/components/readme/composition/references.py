"""Dangling references: a sentence that points at a table, list, example or section not there.

Wave-3 acceptance review (reseal f69f75c7): preserved inherited sentences kept their pointer and
lost what they pointed at. Cells-.NET printed a raw member dump under "see the table below" with
no table in the section; Slides-.NET kept "Every example below" after its last example and an
opening that sent the reader to a "What it cannot do" section the candidate does not have;
Slides-Python kept a chart note after an unrelated example. The sentence is true in the upstream
README, whose layout the candidate replaced, and false in the candidate. A reader meets a promise
nothing keeps.

The check is mechanical and reads only the finished README:

* a directional reference (``below``, ``the following``, ``as follows``) needs a block of the kind
  it names after it in the same scope (``table`` -> a table, ``list`` -> a list, ``example`` /
  ``snippet`` / ``code`` / ``command`` -> a fenced block, ``diagram`` -> a Mermaid block; no kind
  -> any block). The scope runs from the sentence to the next heading of the same or a higher
  level, so a section's lead-in reaches the subsections it introduces;
* ``above`` / ``preceding`` needs such a block between the scope's heading and the sentence;
* a paragraph that ends on a colon needs something after it before the next heading (Cells-Java,
  HTML-Python, Page-Python and PDF-Python each end "Run the test suite:" and move on to a heading);
* a reference to a named section ("the Scope and Limitations section", "see the 'What it cannot
  do' section") needs a heading of that name somewhere in the README.

Run over the 46 distinct sealed READMEs it reports the defects above and no well-formed sentence.
It is called from BC-07, which locates the sentence in a placed inherited unit (the reconciliation
kept a sentence and dropped its referent) or in an authored one (composition).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```+|~~~+)\s*([\w+#.-]*)")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[(])")
_MARKUP = re.compile(r"[*_`]+|\[([^\]]*)\]\([^)]*\)")
_SPACE = re.compile(r"\s+")

_KIND_WORDS = {
    "table": "table",
    "list": "list",
    "bullets": "list",
    "diagram": "diagram",
    "example": "code",
    "examples": "code",
    "sample": "code",
    "samples": "code",
    "snippet": "code",
    "snippets": "code",
    "code": "code",
    "command": "code",
    "commands": "code",
    "block": "code",
}
_KIND = "|".join(sorted(_KIND_WORDS, key=len, reverse=True))
# "the table below", "every example below", "the examples listed below", "the list above".
_DIRECT = re.compile(
    rf"\b(?P<kind>{_KIND})\b(?:\s+(?:shown|listed|given|described|collected|printed|included))?"
    rf"\s+(?P<way>below|above)\b",
    re.IGNORECASE,
)
# "the following table", "the following examples", "as follows".
_FOLLOWING = re.compile(rf"\b(?:the\s+)?following\s+(?P<kind>{_KIND})\b", re.IGNORECASE)
# "see below", "described below", "listed below" with no noun in front.
_BARE_BELOW = re.compile(
    r"\b(?:see|are|is|as|listed|described|shown|given|follows?)\s+below\b", re.I
)
_BARE_ABOVE = re.compile(r"\b(?:see|listed|described|shown|given|as|mentioned)\s+above\b", re.I)
# "the Scope and Limitations section", "see the 'What it cannot do' section".
_SECTION = re.compile(
    r"\b(?:the|in|under|see)\s+[\"\u201c'\u2018]?"
    r"(?P<name>[A-Z][A-Za-z0-9&/' -]{2,48}?)[\"\u201d'\u2019]?\s+section\b"
)
# "listed in full under What it cannot do." - the heading named by a sentence that ends on it.
_UNDER = re.compile(
    r"\b(?:listed|described|documented|covered|explained|detailed|found)\s+(?:in full\s+)?"
    r"(?:under|in)\s+(?:the\s+)?[\"\u201c'\u2018]?"
    r"(?P<name>[A-Z][A-Za-z0-9&/' -]{2,48}?)[\"\u201d'\u2019]?\s*[.;,]?\s*$"
)
_GENERIC_SECTION_NAMES = frozenset(
    {"this", "that", "next", "previous", "following", "above", "below"}
)


@dataclass(frozen=True)
class DanglingReference:
    """A sentence whose pointer has no referent, the section it sits in, and what is missing."""

    sentence: str
    section: str
    reason: str


@dataclass
class _Block:
    kind: str  # paragraph | list | table | code | diagram | html
    text: str
    scope_end: int  # index of the first block after this block's heading scope


def _plain(text: str) -> str:
    return _SPACE.sub(" ", _MARKUP.sub(lambda m: m.group(1) or "", text)).strip().lower()


def _normal(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def _parse(readme: str) -> tuple[list[_Block], list[tuple[int, int, str]]]:
    """The README as blocks in order, and its headings as ``(block index, level, title)``."""
    blocks: list[_Block] = []
    headings: list[tuple[int, int, str]] = []
    lines = readme.splitlines()
    index = 0
    pending: list[str] = []

    def flush() -> None:
        if not pending:
            return
        text = "\n".join(pending)
        first = pending[0]
        if _TABLE_ROW.match(first):
            kind = "table"
        elif _BULLET.match(first):
            kind = "list"
        elif first.lstrip().startswith("<"):
            kind = "html"
        else:
            kind = "paragraph"
        blocks.append(_Block(kind, text, 0))
        pending.clear()

    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line)
        if fence:
            flush()
            marker, language = fence.group(1), fence.group(2).lower()
            body = [line]
            index += 1
            while index < len(lines) and not lines[index].strip().startswith(marker[:3]):
                body.append(lines[index])
                index += 1
            body.append(lines[index] if index < len(lines) else marker)
            blocks.append(
                _Block("diagram" if language == "mermaid" else "code", "\n".join(body), 0)
            )
            index += 1
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            headings.append((len(blocks), len(heading.group(1)), heading.group(2)))
            blocks.append(_Block("heading", heading.group(2), 0))
            index += 1
            continue
        if not line.strip():
            flush()
        elif pending and (
            (_BULLET.match(line) and not _BULLET.match(pending[0]) and not line.startswith(" "))
            or (_TABLE_ROW.match(line) != _TABLE_ROW.match(pending[0]))
        ):
            flush()
            pending.append(line)
        else:
            pending.append(line)
        index += 1
    flush()
    return blocks, headings


def _scope(position: int, headings: list[tuple[int, int, str]], total: int) -> tuple[int, int, str]:
    """``(start, end, title)`` of the heading scope holding block ``position``: from its heading to
    the next heading of the same or a higher level."""
    start, level, title = 0, 0, ""
    for at, depth, name in headings:
        if at <= position:
            start, level, title = at, depth, name
    end = total
    for at, depth, _ in headings:
        if at > position and depth <= level:
            end = at
            break
    return start, end, title


def _has(blocks: list[_Block], lo: int, hi: int, wanted: str | None) -> bool:
    content = [b for b in blocks[lo:hi] if b.kind not in {"heading", "html"}]
    if wanted is None:
        return bool(content)
    if wanted == "code":
        return any(b.kind == "code" for b in content)
    return any(b.kind == wanted for b in content)


def _nothing_follows(blocks: list[_Block], position: int) -> bool:
    """The next content block after ``position`` is a heading, or there is none (a paragraph that
    ends on a colon promises a command, list or table; prose may also continue into a paragraph,
    which is why only a heading or the end of the document proves the promise unkept)."""
    following = next((b for b in blocks[position + 1 :] if b.kind != "html"), None)
    return following is None or following.kind == "heading"


def dangling_references(readme: str) -> list[DanglingReference]:
    """Every prose sentence of ``readme`` that points at something the README does not have."""
    blocks, headings = _parse(readme)
    titles = {_normal(title) for _, _, title in headings}
    found: list[DanglingReference] = []
    for position, block in enumerate(blocks):
        if block.kind not in {"paragraph", "list"}:
            continue
        start, end, title = _scope(position, headings, len(blocks))
        pieces = _SENTENCE_END.split(_SPACE.sub(" ", block.text))
        for index, raw in enumerate(pieces):
            sentence = _plain(raw)
            if not sentence:
                continue
            reasons: list[str] = []
            for match in _DIRECT.finditer(sentence):
                wanted = _KIND_WORDS[match.group("kind").lower()]
                below = match.group("way").lower() == "below"
                lo, hi = (position + 1, end) if below else (start, position)
                if not _has(blocks, lo, hi, wanted):
                    direction = "follows" if below else "precedes"
                    reasons.append(
                        f"says '{match.group(0)}' but no {wanted} {direction} it in this section"
                    )
            for match in _FOLLOWING.finditer(sentence):
                wanted = _KIND_WORDS[match.group("kind").lower()]
                if not _has(blocks, position + 1, end, wanted):
                    reasons.append(f"says '{match.group(0)}' but no {wanted} follows it")
            if (
                not reasons
                and _BARE_BELOW.search(sentence)
                and not _has(blocks, position + 1, end, None)
            ):
                reasons.append("points 'below' but nothing follows it in this section")
            if (
                not reasons
                and _BARE_ABOVE.search(sentence)
                and not _has(blocks, start, position, None)
            ):
                reasons.append("points 'above' but nothing precedes it in this section")
            if (
                not reasons
                and block.kind == "paragraph"
                and index == len(pieces) - 1
                and raw.rstrip().endswith(":")
                and _nothing_follows(blocks, position)
            ):
                reasons.append("ends with a colon but nothing follows it before the next heading")
            spaced = _SPACE.sub(" ", raw)
            for match in (*_SECTION.finditer(spaced), *_UNDER.finditer(spaced.strip())):
                name = match.group("name").strip()
                if name.lower() in _GENERIC_SECTION_NAMES or _normal(name) in titles:
                    continue
                if not any(_normal(name) in known for known in titles):
                    reasons.append(f"refers to a '{name}' section this README does not have")
            if reasons:
                found.append(DanglingReference(raw.strip(), title, "; ".join(reasons)))
    return found
