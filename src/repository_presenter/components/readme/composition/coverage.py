"""How much of a kept unit its destination section already states: the whole-content test behind
the drop rule in ``placement.py``.

Wave-3 acceptance review (reseal ``f69f75c7``, LST-01) and the wave-3 triage (U9): placement
dropped a whole ``VERIFIED_PRESERVE``/``VERIFIED_MOVE`` unit as soon as ONE fact it cites was also
cited by the destination's own content. Measured on the 36 wave-3 transactions it dropped 266 of
the 665 kept units that render as written (40%); of the 209 with a rendered README, 95 (45%) were
not wholly stated by their destination, so their substance (a limitation, a format table, a
second paragraph of the Development section) reached the document nowhere. Nothing downstream
saw the loss: BC-05 skipped an ``overlap`` unit and BC-08 reads commands only - until a unit
carried a command. ``go run main.go`` (Cells-Go), ``make test`` (Page-Python), ``go run
./_examples/feature_showcase`` (PDF-Go) and ``dotnet add reference`` (PDF-.NET) were dropped by
the overlap rule and BC-08 then demanded the very command the rule had removed, a contradiction
no stage could resolve.

A fact id is a citation, not a statement: two pieces of content resting on the same fact can say
different things. So the rule asks the question it means. A kept unit is dropped only when the
destination, as it renders without the unit, STATES everything the unit says; otherwise the unit is
carried, or only the part the destination does not state is (the unit's uncovered remainder):

* a list is judged item by item, with the item test BC-05 already uses for a dropped list
  (``list_coverage.missing_items``: the subject words of the item's lead, or its link in
  Documentation and Resources), so what placement drops BC-05 accepts;
* any other unit is judged sentence by sentence: a sentence is stated when the destination holds
  it verbatim or holds at least ``SENTENCE_SHARE`` of its word stems;
* a command or a link a sentence or item carries must itself appear in the document. This is the
  part that cannot be a judgment: BC-08 demands the command and BC-06 the link, whatever else the
  destination says;
* a lead-in (a sentence beside a rendered example, or opening the example section) is the section's
  own lead-in's duplicate by construction, so it is stated whenever it adds no command or link the
  document lacks.

A shared fact id only nominates a unit for dropping (``placement.py``); this test decides it, from
text alone - no plan, no fact id, no model - and every input is the document the renderer produces
without any kept unit placed (``Destinations``), so the renderer and the validator reach the same
answer.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence

from repository_presenter.components.readme.composition.list_coverage import (
    item_links,
    list_items,
    missing_items,
    stems,
)

# The shape BC-08 calls a command (``validation/registry.py::_COMMAND``); a test pins the two equal.
COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:pip3?|python3?(?:\s+-m)?|npm|npx|yarn|pnpm|dotnet|mvn|gradle|go|"
    r"cargo|cmake|make|git)\b(?!-)",
    re.IGNORECASE,
)
# The share of a sentence's word stems the destination must hold for the sentence to count as
# stated in other words. Measured on the 209 dropped units of the wave-3 transactions that have a
# rendered README: 122 are stated in full at 0.6, 114 at 0.7, 108 at 0.8, so the rule is not
# knife-edge; 0.7 sits where a paraphrase of a sentence is still stated and a sentence the
# destination merely shares a topic with is not.
SENTENCE_SHARE = 0.7

_SPAN = re.compile(r"`([^`]+)`")
_URL = re.compile(r"https?://[^\s<>)\]`]+")
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+")
# What a sentence boundary may not fall inside: a code span, a link destination, a bare URL, a tag.
_PROTECTED = re.compile(r"`[^`\n]*`|\]\([^)\s]*\)|https?://[^\s<>)\]]+|<[^>\n]+>")
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\[\"'(*_<])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


class _Indexed:
    """One destination's text, indexed once for the sentence test."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.squashed = _squash(text)
        self.stems = stems(text)

    def states(self, sentence: str, share: float) -> bool:
        squashed = _squash(sentence)
        if squashed.strip() and squashed in self.squashed:
            return True
        subject = stems(_URL.sub(" ", sentence))
        if not subject:
            return False  # nothing to compare by: it is not decidable, so it is not covered
        return len(subject & self.stems) >= math.ceil(len(subject) * share)


class Destinations:
    """The document as it renders with no kept unit placed, section by section.

    ``section_text`` renders one included section's body on demand (a candidate with a very large
    API reference pays for that section only when a kept unit is judged against it), and
    ``document`` is every included section together, built only when a command or a link needs
    looking for. ``Destinations.of`` wraps texts already in hand.
    """

    def __init__(self, section_text: Callable[[str], str], section_ids: Sequence[str]) -> None:
        self._section_text = section_text
        self._section_ids = tuple(section_ids)
        self._texts: dict[str, str] = {}
        self._indexed: dict[str, _Indexed] = {}
        self._document: str | None = None

    @classmethod
    def of(cls, sections: Mapping[str, str]) -> Destinations:
        return cls(lambda section_id: sections.get(section_id, ""), tuple(sections))

    def text(self, section_id: str) -> str:
        if section_id not in self._texts:
            self._texts[section_id] = self._section_text(section_id)
        return self._texts[section_id]

    def index(self, section_id: str) -> _Indexed:
        if section_id not in self._indexed:
            self._indexed[section_id] = _Indexed(self.text(section_id))
        return self._indexed[section_id]

    @property
    def document(self) -> str:
        if self._document is None:
            self._document = "\n\n".join(self.text(section_id) for section_id in self._section_ids)
        return self._document


def sentences(text: str) -> list[str]:
    """``text`` split into its sentences, each a substring of ``text`` (inner line breaks kept).
    A boundary never falls inside a code span, a link destination, or a URL."""
    masked = _PROTECTED.sub(lambda match: "\x00" * len(match.group(0)), text)
    parts: list[str] = []
    start = 0
    for boundary in _BOUNDARY.finditer(masked):
        parts.append(text[start : boundary.start()])
        start = boundary.end()
    parts.append(text[start:])
    return [part for part in parts if part.strip()]


def list_blocks(text: str) -> list[str]:
    """The top-level items of a Markdown list, each as written (marker, wrapped and nested
    lines), in the order ``list_coverage.list_items`` reads them."""
    blocks: list[list[str]] = []
    for line in text.splitlines():
        if _BULLET.match(line):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    return ["\n".join(block).rstrip() for block in blocks]


def hard_tokens(text: str) -> list[str]:
    """The commands and links ``text`` carries: what BC-08 and BC-06 hold the document to whatever
    else it says. An in-page anchor names a heading, not a document, and is not one."""
    found = [span.strip() for span in _SPAN.findall(text) if COMMAND.match(span)]
    found.extend(item_links(text))
    found.extend(url.rstrip(".,;:") for url in _URL.findall(text))
    return list(dict.fromkeys(token for token in found if token))


def _squash(text: str) -> str:
    return f" {_NON_WORD.sub(' ', text.lower()).strip()} "


def _carries_all(text: str, shown: Destinations) -> bool:
    """Whether the document holds every command and link ``text`` carries (the document is only
    built when ``text`` carries one)."""
    tokens = hard_tokens(text)
    return not tokens or all(token in shown.document for token in tokens)


def _uncovered_items(
    text: str, destination: _Indexed, shown: Destinations, by_link: bool
) -> str | None:
    blocks = list_blocks(text)
    if not blocks:
        return None
    # One pass over the whole list: the item test indexes the destination's words each call.
    absent = set(
        missing_items(
            text,
            destination.text,
            by_link=by_link,
            document_text=shown.document if by_link else "",
        )
    )
    open_items = [
        block
        for block in blocks
        if next(iter(list_items(block)), "") in absent or not _carries_all(block, shown)
    ]
    return text if len(open_items) == len(blocks) else "\n".join(open_items)


def uncovered(
    unit_id: str,
    text: str,
    shown: Destinations,
    section_id: str,
    *,
    by_link: bool = False,
    lead_in: bool = False,
) -> str:
    """The part of the kept unit ``text`` that section ``section_id`` of ``shown`` does not state,
    as written; empty when it states all of it. A command or a link may be rendered in another
    section, so those are looked for in the whole document; ``by_link`` judges a list item by the
    link it carries (Documentation and Resources), ``lead_in`` marks a sentence that introduces a
    rendered example.

    The remainder is the unit's own text, byte for byte, when nothing of it is stated: a part is
    only ever removed, never reworded.
    """
    destination = shown.index(section_id)
    if unit_id.rsplit(".", 1)[-1] == "list":
        remainder = _uncovered_items(text, destination, shown, by_link)
        if remainder is not None:
            return remainder
    parts = sentences(text)
    if not parts:
        return ""
    open_parts = [
        part
        for part in parts
        if not _carries_all(part, shown)
        or not (lead_in or destination.states(part, SENTENCE_SHARE))
    ]
    return text if len(open_parts) == len(parts) else " ".join(open_parts)
