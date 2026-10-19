"""M5: junk lint. Deterministic text patterns that are never intended content.

Independent of the C2 gate and at least as broad: it reads the sealed README text only (no facts,
no validation module). Each rule has an id so the corpus can label a case with the rule that must
fire. A hit is a ``(rule, line, excerpt)``; M5 is the number of hits over a README.

Rules (Q_claims classes F and G):

* ``DANGLING_COLON``: a line ending in a colon that is followed, after blank lines, by a heading
  or the end of the file (the lead-in whose block is missing);
* ``SPLIT_SPEC``: a list item or table cell that begins with a comparison operator and a version
  (``<145``, ``>=87.0``): a requirement spec cut at its comma;
* ``XML_DOC_FRAGMENT``: scraped documentation markup or its residue (``<summary>``, ``<param``,
  ``The  contains`` with a missing identifier, ``Defined as `: number```);
* ``BADGE_SYNTAX``: a badge or image whose URL is malformed (an unescaped comma, ``<``,
  ``>`` or space, or an encoded comma ``%2C`` where a version range was cut) or whose brackets do
  not close.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DANGLING_COLON = "DANGLING_COLON"
SPLIT_SPEC = "SPLIT_SPEC"
XML_DOC_FRAGMENT = "XML_DOC_FRAGMENT"
BADGE_SYNTAX = "BADGE_SYNTAX"
RULES: tuple[str, ...] = (DANGLING_COLON, SPLIT_SPEC, XML_DOC_FRAGMENT, BADGE_SYNTAX)

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SPEC_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.|\|)\s*`?\s*(?:<=|>=|==|!=|~=|<|>)\s*\d")
_XML_TAG = re.compile(r"</?(?:param|returns|remarks|typeparam|see|seealso|paramref|inheritdoc)\b")
_CODE_SPAN = re.compile(r"`[^`]*`")
_MISSING_NAME = re.compile(r"\b(?:The|A|An|This) {2,}[a-z]")
_SCRAPED_TYPE = re.compile(r"Defined as\s*`\s*:")
_IMAGE_URL = re.compile(r"!\[[^\]]*\]\(([^)]*)\)")
_BAD_URL_CHARS = re.compile(r"[<>\s,]|%2[Cc]")


@dataclass(frozen=True)
class Hit:
    rule: str
    line: int  # 1-based
    excerpt: str


def _body_lines(text: str) -> list[tuple[int, str, bool]]:
    """(1-based line number, line, inside a fenced block) for every line; a fence line itself
    counts as outside, so a lead-in followed by a fence is followed by content."""
    kept: list[tuple[int, str, bool]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            kept.append((number, line, False))
            fenced = not fenced
        else:
            kept.append((number, line, fenced))
    return kept


def _dangling(lines: list[tuple[int, str, bool]]) -> list[Hit]:
    hits: list[Hit] = []
    for index, (number, line, fenced) in enumerate(lines):
        stripped = line.rstrip()
        if fenced or not stripped.endswith(":") or _HEADING.match(line):
            continue
        if line.lstrip().startswith("|") or _FENCE.match(line):
            continue
        following = next((later for _, later, _ in lines[index + 1 :] if later.strip()), None)
        if following is None or _HEADING.match(following):
            hits.append(Hit(DANGLING_COLON, number, line.strip()[:80]))
    return hits


def _badges(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in _IMAGE_URL.finditer(line):
            target = match.group(1).strip()
            if not target.startswith("data:") and _BAD_URL_CHARS.search(target):
                hits.append(Hit(BADGE_SYNTAX, number, match.group(0)[:100]))
        if "![" in line and line.count("[") != line.count("]"):
            hits.append(Hit(BADGE_SYNTAX, number, line.strip()[:100]))
    return hits


def lint(text: str) -> list[Hit]:
    """Every junk hit in a README text, ordered by line then rule."""
    body = _body_lines(text)
    hits = _dangling(body) + _badges(text)
    for number, line, fenced in body:
        if fenced:
            continue
        if _SPEC_ITEM.match(line):
            hits.append(Hit(SPLIT_SPEC, number, line.strip()[:80]))
        if (
            _XML_TAG.search(_CODE_SPAN.sub("", line))
            or _MISSING_NAME.search(line)
            or _SCRAPED_TYPE.search(line)
        ):
            hits.append(Hit(XML_DOC_FRAGMENT, number, line.strip()[:80]))
    return sorted(hits, key=lambda hit: (hit.line, hit.rule))
