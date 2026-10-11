"""Whether the rendered README states what a deferred unit said: the decidable test behind an
advisory deferral that claims "nothing is lost".

Wave-3 acceptance review (reseal f69f75c7; Note-Python 013, Slides-Python 018 and 117, Slides-.NET
033): an ADVISORY deferral class told the reviewer a unit was "not published, nothing lost" while
the README did not state the unit's content anywhere. The `[pdf]` install extra the first Quick
Start example needs, the warning that a shared ``aspose`` namespace makes the library unimportable,
and the Enterprise Edition paragraph were all true losses that BC-05 reported as advisories and
every later check passed. An advisory is honest only when the content is carried, so
``validation/deferrals.py`` asks this module, with the finished README, before it believes one.

The test is deliberately mechanical and deliberately lenient about wording, because the composer
restates content rather than quoting it:

* every anchor the unit spells must appear in the README: a code span, a link destination, a
  dotted version or number. These are the claim-bearing tokens; a paraphrase keeps them or has
  dropped the claim;
* every prose sentence of at least ``_CLAIM_STEMS`` distinct content words that spells no anchor
  of its own must have at least half of those words in one README block (a paragraph, list item
  or table row), so a restated sentence passes and an absent one does not;
* a fenced block is compared line by line (comment lines and blank lines aside), the way
  ``dispositions._command_lines`` compares a command block.

A unit with no anchor and no long sentence ("Install the library from PyPI:") states nothing a
reader could lose, so it is stated. The function returns the pieces that are not carried, so a
failure can name them and the repair has something to act on.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme.composition.list_coverage import list_items, stems

_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_LINK_DESTINATION = re.compile(r"\]\(\s*<?([^)\s>]+)")
_BARE_URL = re.compile(r"https?://[^\s)>\]`]+")
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)+(?![\w.])")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[(])")
_FENCE = re.compile(r"^\s*```")
_COMMENT = re.compile(r"^\s*(?:#|//|--)")
_EMPHASIS = re.compile(r"[*]+")
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)[^)]*\)")
_SPACE = re.compile(r"\s+")
# A sentence with fewer content words than this cannot be tested by word share; it is judged by
# its anchors alone (a lead-in such as "Install the library from PyPI:" carries no claim).
_CLAIM_STEMS = 5
_PRESENT_SHARE = 0.5
_QUOTE_LIMIT = 120
_MIN_ANCHOR = 2


def _plain(text: str) -> str:
    """``text`` as it is compared: links flattened to ``label destination``, emphasis and
    backticks removed, whitespace collapsed, lower case."""
    flattened = _MARKDOWN_LINK.sub(r"\1 \2", text)
    return _SPACE.sub(" ", _EMPHASIS.sub("", flattened).replace("`", "")).strip().lower()


def _destination(target: str) -> str:
    return target.strip().rstrip("/").lower()


def _anchors(text: str) -> list[tuple[str, str]]:
    """The tokens of ``text`` a rewrite cannot drop and still state it: ``(kind, comparable)``."""
    found: list[tuple[str, str]] = []
    for span in _CODE_SPAN.findall(text):
        plain = _plain(span)
        if len(plain) >= _MIN_ANCHOR:
            found.append(("span", plain))
    for target in (*_LINK_DESTINATION.findall(text), *_BARE_URL.findall(text)):
        if not target.startswith("#"):
            found.append(("link", _destination(target)))
    found.extend(("number", number) for number in _NUMBER.findall(_CODE_SPAN.sub(" ", text)))
    return list(dict.fromkeys(found))


def _blocks(readme: str) -> list[str]:
    """The README's paragraphs, list items and table rows, each as the stems it states."""
    blocks: list[str] = []
    for paragraph in re.split(r"\n\s*\n", readme):
        blocks.append(paragraph)
        blocks.extend(line for line in paragraph.splitlines() if line.strip())
    return blocks


def _code_lines(text: str) -> list[str]:
    """The comparable lines of a fenced block: fences, comments and blank lines removed."""
    return [
        _plain(line)
        for line in text.splitlines()
        if line.strip() and not _FENCE.match(line) and not _COMMENT.match(line)
    ]


def _sentences(text: str, kind: str) -> list[str]:
    if kind in {"list", "table"}:
        items = list_items(text) if kind == "list" else []
        return items or [
            re.sub(r"^[\s|:-]+|[\s|:-]+$", "", line)
            for line in text.splitlines()
            if line.strip() and not re.fullmatch(r"[\s|:-]+", line)
        ]
    return [part for part in _SENTENCE_END.split(_SPACE.sub(" ", text).strip()) if part]


def unstated(unit_text: str, readme: str, *, kind: str = "paragraph") -> list[str]:
    """The pieces of ``unit_text`` the README does not state: empty when it carries them all.

    ``kind`` is the inherited unit's kind (``paragraph``, ``list``, ``table``, ``code_block``,
    ``heading``). Each piece is a short quotation, ready for a failure message."""
    document = _plain(readme)
    if kind == "code_block":
        return [line for line in _code_lines(unit_text) if line not in document][:6]
    missing: list[str] = []
    for anchor_kind, anchor in _anchors(unit_text):
        if anchor not in document:
            missing.append(f"{anchor_kind} {anchor!r}")
    block_stems: list[set[str]] | None = None
    for sentence in _sentences(unit_text, kind):
        if _anchors(sentence):
            continue  # judged by its anchors above
        wanted = stems(sentence)
        if len(wanted) < _CLAIM_STEMS:
            continue
        if block_stems is None:
            block_stems = [stems(block) for block in _blocks(readme)]
        best = max((len(wanted & have) for have in block_stems), default=0)
        if best < max(1, round(len(wanted) * _PRESENT_SHARE)):
            plain = _SPACE.sub(" ", _EMPHASIS.sub("", sentence)).strip()
            missing.append(
                repr(plain if len(plain) <= _QUOTE_LIMIT else plain[:_QUOTE_LIMIT].rstrip() + "...")
            )
    return missing
