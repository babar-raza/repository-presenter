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

Two refinements from the wave-6 acceptance reviews (cause 4, preserved-unit placement and
duplication in every sealed or would-be bundle):

* **A release number is not content.** The kept Gradle line ``implementation
  'org.aspose:aspose-pdf-foss:26.6.0'`` differed from the Installation row's own
  ``...:26.9.0`` in one
  token, counted as uncovered, and printed a second time with the stale version (PDF-Java, BC-14).
  Every comparison here reads text through :func:`unversioned`, which replaces a release number of
  three or more components with one token. A two-component number is a floor (``Python 3.10``,
  ``Java 17``) and is compared as written: a unit that says a different floor is a different claim.
* **A kept unit may be stated by more than its destination.** The Installation and Dependencies
  sections are the renderer's and cannot hold a kept unit, so the dependency list, the Python floor
  and the alternative install block under the source's own Installation heading land in whichever
  section the unit was sent to (Slides-Python, BarCode-Python, PDF-Python) and repeat what those
  two sections print. ``uncovered`` takes the extra sections to read the unit against (``also``),
  and :func:`uncovered_block` is the same whole-content test for a code block, line by line.
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

# A release number of three or more components ("26.6.0", "v1.2.3-rc1"): the one part of an install
# line that differs between two releases of the same package. Two components are a floor, not a
# release, and one is a count.
_RELEASE = re.compile(r"(?<![\w.])v?\d+(?:\.\d+){2,}(?:[-+][0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?(?!\w)")
RELEASE_TOKEN = "<release>"

_SPAN = re.compile(r"`([^`]+)`")
_URL = re.compile(r"https?://[^\s<>)\]`]+")
_BULLET = re.compile(r"^(?:[-*+]|\d{1,3}[.)])\s+")
# What a sentence boundary may not fall inside: a code span, a link destination, a bare URL, a tag.
_PROTECTED = re.compile(r"`[^`\n]*`|\]\([^)\s]*\)|https?://[^\s<>)\]]+|<[^>\n]+>")
_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\[\"'(*_<])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def unversioned(text: str) -> str:
    """``text`` with every release number of three or more components replaced by one token, so two
    texts that differ only in the release they name compare equal."""
    return _RELEASE.sub(RELEASE_TOKEN, text)


class _Indexed:
    """One destination's text, indexed once for the sentence test."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.squashed = _squash(unversioned(text))
        self.stems = stems(unversioned(text))

    def states(self, sentence: str, share: float) -> bool:
        squashed = _squash(unversioned(sentence))
        if squashed.strip() and squashed in self.squashed:
            return True
        subject = stems(_URL.sub(" ", unversioned(sentence)))
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

    @property
    def section_ids(self) -> tuple[str, ...]:
        """The sections the document includes, in document order."""
        return self._section_ids

    def text(self, section_id: str) -> str:
        if section_id not in self._texts:
            self._texts[section_id] = self._section_text(section_id)
        return self._texts[section_id]

    def index(self, section_id: str) -> _Indexed:
        if section_id not in self._indexed:
            self._indexed[section_id] = _Indexed(self.text(section_id))
        return self._indexed[section_id]

    def merged(self, section_id: str, also: Sequence[str]) -> _Indexed:
        """The index of ``section_id`` read together with the sections ``also`` (a section the
        document does not include contributes nothing). Cached under the whole set."""
        if not also:
            return self.index(section_id)
        key = "\x00".join((section_id, *also))
        if key not in self._indexed:
            texts = [self.text(section_id)]
            texts.extend(self.text(other) for other in also if other in self._section_ids)
            self._indexed[key] = _Indexed("\n\n".join(texts))
        return self._indexed[key]

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
    built when ``text`` carries one). Both are compared as written, release number and all: BC-08
    and BC-06 demand the unit's own spelling of a command or a link, so a unit that spells a
    command at another release than the document's is not covered by it."""
    tokens = hard_tokens(text)
    return not tokens or all(token in shown.document for token in tokens)


def _uncovered_items(
    text: str,
    destination: _Indexed,
    shown: Destinations,
    by_link: bool,
    elsewhere: _Indexed | None = None,
) -> str | None:
    """The items of a kept list the destination does not state, or ``None`` for text that is not a
    list. ``elsewhere`` is the text of the sections that state the list on the destination's behalf
    (the renderer's Installation and Dependencies): an item they state as a sentence (``SENTENCE_
    SHARE`` of its own word stems, not only the subject words of its lead, which an unrelated
    mention of "images" or "pytest" would satisfy and so hide what the item says about it) is
    covered too. The item must also pass BC-05's own item test against that text, so what is
    dropped here is never an item the independent check then finds unstated."""
    blocks = list_blocks(text)
    if not blocks:
        return None
    # One pass over the whole list: the item test indexes the destination's words each call. The
    # list is read as written, release numbers and all: BC-05 judges it with this same test on this
    # same text, and a number it reads as a word here must be one there.
    absent = set(
        missing_items(
            text,
            destination.text,
            by_link=by_link,
            document_text=shown.document if by_link else "",
        )
    )
    absent_elsewhere = set(missing_items(text, elsewhere.text)) if elsewhere is not None else set()

    def stated_elsewhere(item: str) -> bool:
        return (
            elsewhere is not None
            and item not in absent_elsewhere
            and elsewhere.states(item, SENTENCE_SHARE)
        )

    open_items = []
    for block in blocks:
        item = " ".join(list_items(block))
        first = next(iter(list_items(block)), "")
        if (first in absent and not stated_elsewhere(item)) or not _carries_all(block, shown):
            open_items.append(block)
    return text if len(open_items) == len(blocks) else "\n".join(open_items)


def uncovered(
    unit_id: str,
    text: str,
    shown: Destinations,
    section_id: str,
    *,
    by_link: bool = False,
    lead_in: bool = False,
    also: Sequence[str] = (),
    only_also: bool = False,
) -> str:
    """The part of the kept unit ``text`` that section ``section_id`` of ``shown`` does not state,
    as written; empty when it states all of it. A command or a link may be rendered in another
    section, so those are looked for in the whole document; ``by_link`` judges a list item by the
    link it carries (Documentation and Resources), ``lead_in`` marks a sentence that introduces a
    rendered example, and ``also`` names sections that may state the unit instead of the
    destination (the renderer's Installation and Dependencies, for a unit about installing).
    ``only_also`` leaves the destination out of the test: a unit nominated for its topic alone,
    with no fact the destination's content rests on, is dropped only for what those sections say.

    ``also`` is a second haystack, never a union with the destination: read together, the long
    authored text of a section and the two renderer sections share enough vocabulary to "state"
    an identifier-heavy sentence that says something new (3D-.NET: the console converter that is
    not published to NuGet), so a part is covered by the destination alone or by ``also`` alone.

    The remainder is the unit's own text, byte for byte, when nothing of it is stated: a part is
    only ever removed, never reworded.
    """
    destination = _Indexed("") if only_also else shown.index(section_id)
    elsewhere = shown.merged(also[0], also[1:]) if also else None
    if by_link and unit_id.rsplit(".", 1)[-1] != "list":
        # A paragraph in Documentation and Resources that only points at documents the section
        # already lists (Slides-Python: "See agents.md ... and CONTRIBUTING.md for how to
        # build") says
        # nothing the list does not, and README_CONTRACT.md row 15 never names a target twice.
        links = item_links(text)
        if links and all(link in destination.text for link in links):
            return ""
    if unit_id.rsplit(".", 1)[-1] == "list":
        remainder = _uncovered_items(text, destination, shown, by_link, elsewhere)
        if remainder is not None:
            return remainder
    parts = sentences(text)
    if not parts:
        return ""
    open_parts = [
        part
        for part in parts
        if not _carries_all(part, shown)
        or not (
            lead_in
            or destination.states(part, SENTENCE_SHARE)
            or (elsewhere is not None and elsewhere.states(part, SENTENCE_SHARE))
        )
    ]
    return text if len(open_parts) == len(parts) else " ".join(open_parts)


def states_all(kept: str, text: str, share: float = SENTENCE_SHARE) -> bool:
    """Whether ``kept`` states every sentence of ``text``, by the sentence test of this module
    (verbatim, or ``share`` of the sentence's word stems, release numbers aside).

    The authored units of a section owe the substance of each inherited unit reconciliation
    superseded into it; a kept unit printed as written in the same section that already says it
    discharges that debt, and asking the author to restate it prints it twice."""
    parts = sentences(text)
    indexed = _Indexed(kept)
    return bool(parts) and all(indexed.states(part, share) for part in parts)


def _loose(line: str) -> str:
    return " ".join(unversioned(line).split()).lower()


def _block_body(text: str) -> list[str]:
    """The lines of a fenced code block that say something: fences, blank lines and comments
    dropped."""
    return [
        raw.strip()
        for raw in text.splitlines()
        if raw.strip() and not raw.strip().startswith(("```", "~~~", "#", "//"))
    ]


def uncovered_block(text: str, shown: Destinations, sections: Sequence[str]) -> str:
    """``text`` (a kept code block) when the ``sections`` lack a line of it, else the empty string.

    A code block is content nothing else renders (``placement.py``) - until the renderer prints the
    same lines itself: the Installation row's Maven and Gradle declarations, its clone-and-build
    lines, its verify line. Each line is looked for among the lines of those renderer-owned
    ``sections`` as they render without any kept unit, so a block that repeats what they print is
    dropped and one with a single line they lack is carried whole (a block is never cut: its lines
    only mean something together). A declaration is compared release number aside (the Gradle line
    kept at ``:26.6.0``, printed at ``:26.9.0``); a shell command is compared as written, since
    BC-08 demands the unit's own spelling of it. A block with no line to compare by is carried."""
    lines = _block_body(text)
    if not lines:
        return text
    printed = [
        line
        for section in sections
        if section in shown.section_ids
        for line in _block_body(shown.text(section))
    ]
    exact = set(printed)
    loose = {_loose(line) for line in printed}
    covered = all(
        (line in exact) if COMMAND.match(line) else (_loose(line) in loose) for line in lines
    )
    return "" if covered else text
