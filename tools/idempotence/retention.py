"""How much of the live README a candidate keeps, and exactly what it loses (metric a).

Two views of the same question.

* **Atom retention.** Every live sentence, list item, table row, code block, heading, link target
  and image target is looked up in the candidate and given one outcome: ``verbatim`` (the same text
  once presentation is folded), ``reworded`` (most of its content words sit in one candidate atom),
  ``scattered`` (they sit in the candidate but spread over several atoms) or ``lost``. Lost atoms
  are listed with their position, so a review can open the live README at the line.
* **Line retention.** The strict view the correction lane is held to: every non-blank live line
  outside the Mermaid diagram must still be a line of the candidate, in order, unless an enumerated
  edit (a character span the lane reports) covers it. 100% is the only passing value.

The thresholds are those of the second first-principles analysis (0.6 and 0.85), kept so the
numbers in ``plans/reseal-and-refresh/PLAN.md`` section 11A and this module's table agree. They make
"kept" generous: ``verbatim`` is a ceiling for byte retention and ``lost`` may include a
semantically equivalent restatement.

Pure functions of the two texts: no network, no model, no clock.
"""

from __future__ import annotations

import difflib
from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

from tools.idempotence.atoms import PROSE_KINDS, Atom, Atoms, atomise, mermaid_line_numbers, toks

VERBATIM = "verbatim"
REWORDED = "reworded"
SCATTERED = "scattered"
LOST = "lost"
OUTCOMES = (VERBATIM, REWORDED, SCATTERED, LOST)

REWORD_THRESHOLD = 0.6
SCATTER_THRESHOLD = 0.85
#: A code block that is this similar to a candidate block was modified, not rewritten.
CODE_MODIFIED = 0.8
CODE_REWORKED = 0.5
#: Past this size the similarity ratio of two blocks is not worth its cost; only equality counts.
CODE_RATIO_LIMIT = 6000


@dataclass
class Category:
    """The outcomes for one kind of atom."""

    kind: str
    total: int = 0
    counts: Counter[str] = field(default_factory=Counter)
    lost: list[Atom] = field(default_factory=list)

    @property
    def verbatim(self) -> int:
        return self.counts[VERBATIM]

    @property
    def kept(self) -> int:
        """Atoms that survive in any form."""
        return self.total - self.counts[LOST]

    @property
    def verbatim_share(self) -> float:
        return self.verbatim / self.total if self.total else 1.0

    @property
    def kept_share(self) -> float:
        return self.kept / self.total if self.total else 1.0


@dataclass(frozen=True)
class LostLine:
    number: int  # 1-based, in the live README
    text: str


@dataclass
class LineRetention:
    """The strict, line-level view (see the module docstring)."""

    eligible: int = 0  # non-blank live lines outside the diagram and outside enumerated edits
    kept: int = 0  # eligible lines found in the candidate, in order
    present: int = 0  # eligible lines found anywhere in the candidate
    diagram: int = 0  # non-blank live lines inside a Mermaid fence, excluded
    allowed: int = 0  # non-blank live lines an enumerated edit covers, excluded
    live_lines: int = 0  # non-blank live lines in all
    lost: list[LostLine] = field(default_factory=list)  # eligible lines not kept in order

    @property
    def share(self) -> float:
        return self.kept / self.eligible if self.eligible else 1.0

    @property
    def present_share(self) -> float:
        return self.present / self.eligible if self.eligible else 1.0

    @property
    def total_share(self) -> float:
        """Every non-blank live line still a candidate line in order, edits and diagram included."""
        covered = self.kept + self.allowed + self.diagram
        return covered / self.live_lines if self.live_lines else 1.0


@dataclass
class RetentionReport:
    categories: dict[str, Category]
    prose: Category  # sentences and list items pooled: the headline "text kept" figure
    lines: LineRetention

    def lost_items(self) -> list[Atom]:
        """Every lost atom of every kind, in document order."""
        merged = [atom for category in self.categories.values() for atom in category.lost]
        return sorted(merged, key=lambda atom: (atom.line, atom.kind, atom.text))


def _classify_text(live: Sequence[Atom], pool: Sequence[Atom]) -> list[str]:
    """One outcome per live atom against a pool of candidate atoms (prose, rows, headings)."""
    keys = {atom.key for atom in pool}
    token_sets = [toks(atom.text) for atom in pool]
    vocabulary: set[str] = set().union(*token_sets) if token_sets else set()
    index: dict[str, list[int]] = defaultdict(list)
    for position, tokens in enumerate(token_sets):
        for token in tokens:
            index[token].append(position)
    flat = " ".join(sorted(keys))
    outcomes: list[str] = []
    for atom in live:
        if atom.key in keys:
            outcomes.append(VERBATIM)
            continue
        tokens = toks(atom.text)
        if len(tokens) < 2:
            # a label: equality, or being a substring of the candidate's text, is all it has
            outcomes.append(REWORDED if atom.key and atom.key in flat else LOST)
            continue
        hits: Counter[int] = Counter()
        for token in tokens:
            hits.update(index.get(token, ()))
        best = hits.most_common(1)[0][1] / len(tokens) if hits else 0.0
        if best >= REWORD_THRESHOLD:
            outcomes.append(REWORDED)
        elif len(tokens & vocabulary) / len(tokens) >= SCATTER_THRESHOLD:
            outcomes.append(SCATTERED)
        else:
            outcomes.append(LOST)
    return outcomes


def _classify_exact(live: Sequence[Atom], pool: Sequence[Atom]) -> list[str]:
    keys = {atom.key for atom in pool}
    return [VERBATIM if atom.key in keys else LOST for atom in live]


def _classify_code(live: Sequence[Atom], pool: Sequence[Atom]) -> list[str]:
    keys = {atom.key for atom in pool}
    outcomes: list[str] = []
    for atom in live:
        if atom.key in keys:
            outcomes.append(VERBATIM)
            continue
        best = 0.0
        if len(atom.key) <= CODE_RATIO_LIMIT:
            for other in pool:
                if len(other.key) > CODE_RATIO_LIMIT:
                    continue
                matcher = difflib.SequenceMatcher(None, atom.key, other.key, autojunk=False)
                if (
                    matcher.real_quick_ratio() < CODE_REWORKED
                    or matcher.quick_ratio() < CODE_REWORKED
                ):
                    continue
                best = max(best, matcher.ratio())
        outcomes.append(REWORDED if best >= CODE_REWORKED else LOST)
    return outcomes


def _classify_headings(live: Sequence[Atom], pool: Sequence[Atom]) -> list[str]:
    exact = {(atom.key, atom.info) for atom in pool}
    keys = {atom.key for atom in pool}
    fuzzy = _classify_text(live, pool)
    outcomes: list[str] = []
    for atom, loose in zip(live, fuzzy, strict=True):
        if (atom.key, atom.info) in exact:
            outcomes.append(VERBATIM)
        elif atom.key in keys:
            outcomes.append(REWORDED)  # the same words at another level
        else:
            outcomes.append(REWORDED if loose in (VERBATIM, REWORDED) else LOST)
    return outcomes


def _category(kind: str, live: Sequence[Atom], outcomes: Sequence[str]) -> Category:
    result = Category(kind, total=len(live))
    for atom, outcome in zip(live, outcomes, strict=True):
        result.counts[outcome] += 1
        if outcome == LOST:
            result.lost.append(atom)
    return result


def atom_retention(live: Atoms, candidate: Atoms) -> tuple[dict[str, Category], Category]:
    prose_pool = candidate.prose()
    categories: dict[str, Category] = {}
    prose = Category("prose")
    for kind in PROSE_KINDS:
        atoms = live.of(kind)
        categories[kind] = _category(kind, atoms, _classify_text(atoms, prose_pool))
        prose.total += categories[kind].total
        prose.counts.update(categories[kind].counts)
        prose.lost.extend(categories[kind].lost)
    categories["row"] = _category("row", live.rows, _classify_text(live.rows, candidate.rows))
    categories["code"] = _category("code", live.code, _classify_code(live.code, candidate.code))
    categories["heading"] = _category(
        "heading", live.headings, _classify_headings(live.headings, candidate.headings)
    )
    categories["link"] = _category("link", live.links, _classify_exact(live.links, candidate.links))
    categories["image"] = _category(
        "image", live.images, _classify_exact(live.images, candidate.images)
    )
    prose.lost.sort(key=lambda atom: (atom.line, atom.text))
    return categories, prose


def covered_lines(text: str, spans: Sequence[tuple[int, int]]) -> set[int]:
    """The 1-based lines of ``text`` that the character spans replace, delete or split.

    A span with ``start < end`` covers every line it overlaps. A pure insertion (``start == end``)
    removes nothing: at a line boundary it covers no line, and inside a line it covers that one,
    because the line is no longer whole afterwards."""
    starts = [0]
    for chunk in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(chunk))
    covered: set[int] = set()
    for start, end in spans:
        if start < end:
            covered.update(range(bisect_right(starts, start), bisect_right(starts, end - 1) + 1))
        elif 0 < start < len(text) and text[start - 1] != "\n":
            covered.add(bisect_right(starts, start))
    return covered


def line_retention(
    live: str, candidate: str, allowed: Sequence[tuple[int, int]] = ()
) -> LineRetention:
    """Strict line retention; ``allowed`` are the enumerated edits' character spans in ``live``."""
    live_lines = [line.rstrip() for line in live.splitlines()]
    cand_lines = [line.rstrip() for line in candidate.splitlines()]
    matcher = difflib.SequenceMatcher(None, live_lines, cand_lines, autojunk=False)
    in_order: set[int] = set()
    for block in matcher.get_matching_blocks():
        in_order.update(range(block.a, block.a + block.size))
    anywhere = set(cand_lines)
    diagram = mermaid_line_numbers(live)
    edited = covered_lines(live, allowed)
    result = LineRetention()
    for index, line in enumerate(live_lines):
        number = index + 1
        if not line.strip():
            continue
        result.live_lines += 1
        if number in diagram:
            result.diagram += 1
        elif number in edited:
            result.allowed += 1
        else:
            result.eligible += 1
            if line in anywhere:
                result.present += 1
            if index in in_order:
                result.kept += 1
            else:
                result.lost.append(LostLine(number, line))
    return result


def retention(
    live: str, candidate: str, allowed: Sequence[tuple[int, int]] = ()
) -> RetentionReport:
    categories, prose = atom_retention(atomise(live), atomise(candidate))
    return RetentionReport(categories, prose, line_retention(live, candidate, allowed))
