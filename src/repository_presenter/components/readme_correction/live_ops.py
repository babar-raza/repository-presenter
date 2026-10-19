"""Live-anchored operations: bring a live README to the family standard, byte for byte elsewhere.

The correction path's edits (``model.Edit``) are deliberately tiny: a line fragment, a short pure
insertion, no heading introduced, no delete. That keeps it safe and also keeps it from doing the
structural work a live README needs (retitling a heading to the family's name, joining the badge
lines, adding Navigation, Dependencies and At a Glance, dropping a bullet whose link target does
not exist). This module is the second, separately typed family for that work. It never replaces a
correction; a bundle holds one family or the other (``live_bundle.py``).

An ``Op`` names an ``anchor``: an exact string that occurs exactly once in the live README and
starts and ends on a line boundary. Four closed kinds:

* ``RETITLE``      one heading line becomes one heading line (same level, same words, or the
                   standard name of the section: ``data/readme_standard``);
* ``REFLOW``       whitespace only, outside code, in a paragraph (badge lines joined onto one);
* ``DELETE_LINE``  one list item whose every relative link target the repository does not hold;
* ``INSERT_BEFORE`` text inserted before a heading, which may open Navigation, Dependencies or
                   At a Glance sections, each verified against the README, the facts and the
                   corrected headings (and nothing else).

``apply_ops`` is pure and strict; ``confinement_proof`` shows that removing exactly the operations'
spans from the live and the corrected text leaves identical bytes, so a maintainer byte no operation
names is unchanged. ``check_ops`` returns typed refusals; every rule has a negative control.

An ``INSERT_BEFORE`` is a zero-width insertion at the start of its anchor (the anchor is where, and
the proof that the text is inserted *before* it: the replacement ends with the anchor byte for
byte). So a ``RETITLE`` of the very heading an insertion goes before does not overlap it.

Nothing here calls a model or the network; the same inputs give the same bytes.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from typing import Any
from urllib.parse import unquote

import yaml
from markdown_it import MarkdownIt

from repository_presenter.components.readme.acceptance.judge import (
    DATA_DIR,
    heading_key,
    load_standard,
)
from repository_presenter.components.readme.review.acceptance.text_checks import (
    FAIL,
    assurance_narration,
    scan,
)
from repository_presenter.components.readme_correction.model import Context
from repository_presenter.components.readme_correction.text_gate import narration
from repository_presenter.components.readme_diagram import contract
from repository_presenter.components.readme_diagram.lint import lint_source
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.components.readme_diagram.rebuild import mermaid_fences
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.facts import Fact

RETITLE = "RETITLE"
REFLOW = "REFLOW"
INSERT_BEFORE = "INSERT_BEFORE"
DELETE_LINE = "DELETE_LINE"
#: The closed set of operation kinds; nothing outside it can be applied or proposed.
OP_KINDS: frozenset[str] = frozenset({RETITLE, REFLOW, INSERT_BEFORE, DELETE_LINE})
#: The text one INSERT_BEFORE adds is a few sections, never a rewrite of the README.
MAX_INSERT = 6000
VOCABULARY_FILE = "live_anchored_vocabulary.yaml"

# Typed refusal codes (also the codes of ``LiveOpError``).
BAD_OPERATIONS = "BAD_OPERATIONS"
UNKNOWN_KIND = "UNKNOWN_KIND"
NO_OPERATIONS = "NO_OPERATIONS"
DUPLICATE_ID = "DUPLICATE_ID"
ANCHOR_NOT_FOUND = "ANCHOR_NOT_FOUND"
ANCHOR_NOT_UNIQUE = "ANCHOR_NOT_UNIQUE"
ANCHOR_NOT_LINE_ALIGNED = "ANCHOR_NOT_LINE_ALIGNED"
ANCHOR_IN_CODE = "ANCHOR_IN_CODE"
OVERLAPPING_OPERATIONS = "OVERLAPPING_OPERATIONS"
INSERT_NOT_BEFORE_ANCHOR = "INSERT_NOT_BEFORE_ANCHOR"
MISSING_EVIDENCE = "MISSING_EVIDENCE"
EVIDENCE_UNKNOWN = "EVIDENCE_UNKNOWN"
EVIDENCE_WRONG_POLARITY = "EVIDENCE_WRONG_POLARITY"
EVIDENCE_NOT_THE_ANCHOR = "EVIDENCE_NOT_THE_ANCHOR"
RETITLE_NOT_A_HEADING = "RETITLE_NOT_A_HEADING"
RETITLE_NOT_COSMETIC = "RETITLE_NOT_COSMETIC"
REFLOW_CHANGES_CHARACTERS = "REFLOW_CHANGES_CHARACTERS"
REFLOW_NOT_A_PARAGRAPH = "REFLOW_NOT_A_PARAGRAPH"
REFLOW_CHANGES_LINKS = "REFLOW_CHANGES_LINKS"
DELETE_NOT_A_LIST_ITEM = "DELETE_NOT_A_LIST_ITEM"
DELETE_LINK_NOT_BROKEN = "DELETE_LINK_NOT_BROKEN"
DELETE_EVIDENCE_MISSING = "DELETE_EVIDENCE_MISSING"
DELETE_ORPHANS_TEXT = "DELETE_ORPHANS_TEXT"
INSERT_SHAPE = "INSERT_SHAPE"
INSERT_TOO_LONG = "INSERT_TOO_LONG"
INSERT_SECTION_NOT_ALLOWED = "INSERT_SECTION_NOT_ALLOWED"
INSERT_DUPLICATE_SECTION = "INSERT_DUPLICATE_SECTION"
INSERT_URL_UNSUPPORTED = "INSERT_URL_UNSUPPORTED"
INSERT_NARRATION = "INSERT_NARRATION"
NAVIGATION_MISMATCH = "NAVIGATION_MISMATCH"
DEPENDENCIES_UNSUPPORTED = "DEPENDENCIES_UNSUPPORTED"
GLANCE_NOT_A_DIAGRAM = "GLANCE_NOT_A_DIAGRAM"
GLANCE_LINT = "GLANCE_LINT"
GLANCE_UNSUPPORTED_WORDS = "GLANCE_UNSUPPORTED_WORDS"
DUPLICATE_HEADING = "DUPLICATE_HEADING"
BROKEN_ANCHOR_LINK = "BROKEN_ANCHOR_LINK"
STALE_REVISION = "STALE_REVISION"

#: Lint defects of a drawn At a Glance diagram that are about ordering and canonical form, not
#: about a reader seeing clipped, stacked or lost text; they are recorded, never silently passed.
GLANCE_TOLERATED_DEFECTS: frozenset[str] = frozenset()
#: The H2 sections an INSERT_BEFORE may open, each with its own verification.
SECTION_NAVIGATION = "Navigation"
SECTION_DEPENDENCIES = "Dependencies"
SECTION_GLANCE = "At a Glance"
SECTIONS: tuple[str, ...] = (SECTION_NAVIGATION, SECTION_DEPENDENCIES, SECTION_GLANCE)


class LiveOpError(PresenterError, ValueError):
    """An operation (or the file holding them) that violates the closed shape; never applied."""

    def __init__(self, code: str, message: str, op: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.op = op


@dataclass(frozen=True)
class Refusal:
    """One typed reason the operations may not be applied."""

    code: str
    op: str
    message: str

    def __str__(self) -> str:
        where = f" [{self.op}]" if self.op else ""
        return f"{self.code}{where}: {self.message}"


@dataclass(frozen=True)
class Op:
    """One live-anchored operation.

    ``evidence`` entries are fact ids, ``readme:<line>`` (the README's own text, 1-based line of
    the live README) or ``tree-absent:<path>`` (a path the pinned tree does not hold)."""

    id: str
    kind: str
    anchor: str
    replacement: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in OP_KINDS:
            raise LiveOpError(
                UNKNOWN_KIND, f"operation kind {self.kind!r} is outside the closed set"
            )
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", self.id):
            raise LiveOpError(BAD_OPERATIONS, f"operation id {self.id!r} is not a short token")
        if not self.anchor:
            raise LiveOpError(BAD_OPERATIONS, "an operation names a non-empty anchor", self.id)
        if self.kind == DELETE_LINE:
            if self.replacement != "":
                raise LiveOpError(BAD_OPERATIONS, "a DELETE_LINE replaces with nothing", self.id)
        elif self.replacement == "" or self.replacement == self.anchor:
            raise LiveOpError(
                BAD_OPERATIONS, "the replacement is empty or equals the anchor", self.id
            )


_OP_KEYS = frozenset({"id", "kind", "anchor", "replacement", "evidence"})


def ops_to_json(ops: Sequence[Op]) -> list[dict[str, Any]]:
    """The list of dicts ``operations.json`` holds (dumped with sorted keys)."""
    return [
        {
            "id": op.id,
            "kind": op.kind,
            "anchor": op.anchor,
            "replacement": op.replacement,
            "evidence": list(op.evidence),
        }
        for op in ops
    ]


def ops_from_json(data: Any) -> tuple[Op, ...]:
    """The operations of a parsed ``operations.json``; any other shape is a typed refusal."""
    if not isinstance(data, list):
        raise LiveOpError(BAD_OPERATIONS, "operations.json is not a list of operations")
    ops: list[Op] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict) or set(item) != _OP_KEYS:
            raise LiveOpError(
                BAD_OPERATIONS,
                f"operation {index} does not have exactly the keys {sorted(_OP_KEYS)}",
            )
        evidence = item["evidence"]
        if not isinstance(evidence, list) or not all(isinstance(e, str) for e in evidence):
            raise LiveOpError(
                BAD_OPERATIONS, f"operation {index}: evidence is not a list of strings"
            )
        for key in ("id", "kind", "anchor", "replacement"):
            if not isinstance(item[key], str):
                raise LiveOpError(BAD_OPERATIONS, f"operation {index}: {key} is not a string")
        ops.append(
            Op(
                id=item["id"],
                kind=item["kind"],
                anchor=item["anchor"],
                replacement=item["replacement"],
                evidence=tuple(evidence),
            )
        )
    return tuple(ops)


# ---------------------------------------------------------------------------------- placement
@dataclass(frozen=True)
class Placed:
    """An operation at its place in the original: ``original[start:end]`` becomes ``text`` (an
    INSERT_BEFORE has ``start == end``: the text before its anchor)."""

    op: Op
    start: int
    end: int
    text: str


def _occurrences(text: str, needle: str) -> list[int]:
    found: list[int] = []
    index = text.find(needle)
    while index != -1:
        found.append(index)
        index = text.find(needle, index + 1)
    return found


def _line_aligned(text: str, start: int, end: int, anchor: str) -> bool:
    if start != 0 and text[start - 1] != "\n":
        return False
    return (
        anchor.endswith("\n")
        or end == len(text)
        or text[end] == "\n"
        or text[end : end + 2] == "\r\n"
    )


def place(original: str, ops: Sequence[Op]) -> list[Placed]:
    """Every operation at its unique, line-aligned anchor in document order; strict."""
    placed: list[Placed] = []
    ids: set[str] = set()
    for op in ops:
        if op.id in ids:
            raise LiveOpError(DUPLICATE_ID, f"operation id {op.id!r} is used twice", op.id)
        ids.add(op.id)
        starts = _occurrences(original, op.anchor)
        if not starts:
            raise LiveOpError(ANCHOR_NOT_FOUND, "the anchor does not occur in the README", op.id)
        if len(starts) > 1:
            raise LiveOpError(
                ANCHOR_NOT_UNIQUE, f"the anchor occurs {len(starts)} times in the README", op.id
            )
        start = starts[0]
        end = start + len(op.anchor)
        if not _line_aligned(original, start, end, op.anchor):
            raise LiveOpError(ANCHOR_NOT_LINE_ALIGNED, "the anchor is not whole lines", op.id)
        if op.kind == INSERT_BEFORE:
            if not op.replacement.endswith(op.anchor) or len(op.replacement) == len(op.anchor):
                raise LiveOpError(
                    INSERT_NOT_BEFORE_ANCHOR,
                    "an INSERT_BEFORE replacement is new text followed by the anchor, unchanged",
                    op.id,
                )
            placed.append(Placed(op, start, start, op.replacement[: -len(op.anchor)]))
        else:
            placed.append(Placed(op, start, end, op.replacement))
    placed.sort(key=lambda p: (p.start, p.end))
    frontier = 0
    insert_at: set[int] = set()
    for item in placed:
        if item.start < frontier:
            raise LiveOpError(
                OVERLAPPING_OPERATIONS, "the operation overlaps another operation", item.op.id
            )
        if item.start == item.end:
            if item.start in insert_at:
                raise LiveOpError(
                    OVERLAPPING_OPERATIONS,
                    "two insertions at one place have no defined order",
                    item.op.id,
                )
            insert_at.add(item.start)
        frontier = max(frontier, item.end)
    return placed


def apply_placed(original: str, placed: Sequence[Placed]) -> tuple[str, list[tuple[int, int]]]:
    """``(corrected, output spans)`` for operations already placed."""
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    cursor = 0
    produced = 0
    for item in placed:
        before = original[cursor : item.start]
        pieces.append(before)
        produced += len(before)
        pieces.append(item.text)
        spans.append((produced, produced + len(item.text)))
        produced += len(item.text)
        cursor = item.end
    pieces.append(original[cursor:])
    return "".join(pieces), spans


def apply_ops(original: str, ops: Sequence[Op]) -> str:
    """``original`` with every operation applied once; anchors unique and non-overlapping."""
    return apply_placed(original, place(original, ops))[0]


def _without(text: str, spans: Sequence[tuple[int, int]]) -> str:
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def confinement_proof(original: str, corrected: str, ops: Sequence[Op]) -> bool:
    """Whether ``corrected`` is ``original`` changed only inside the operations' spans: each output
    span holds exactly its operation's text, and with the spans removed from both texts the
    remaining bytes are identical."""
    try:
        placed = place(original, ops)
    except LiveOpError:
        return False
    out_spans: list[tuple[int, int]] = []
    shift = 0
    for item in placed:
        out_start = item.start + shift
        out_spans.append((out_start, out_start + len(item.text)))
        shift += len(item.text) - (item.end - item.start)
    if out_spans and out_spans[-1][1] > len(corrected):
        return False
    if any(corrected[a:b] != item.text for (a, b), item in zip(out_spans, placed, strict=True)):
        return False
    return _without(original, [(p.start, p.end) for p in placed]) == _without(corrected, out_spans)


# -------------------------------------------------------------------------------- vocabulary
@dataclass(frozen=True)
class Vocabulary:
    synonyms: dict[str, frozenset[str]]  # standard heading -> accepted live heading keys
    buckets: tuple[str, ...]
    glue: frozenset[str]


@cache
def vocabulary() -> Vocabulary:
    document = yaml.safe_load((DATA_DIR / VOCABULARY_FILE).read_text(encoding="utf-8"))
    headings = load_standard().headings
    synonyms: dict[str, frozenset[str]] = {}
    for element, names in document["heading_synonyms"].items():
        standard = headings.get(element)
        if standard:
            synonyms[str(standard)] = frozenset(heading_key(str(name)) for name in names)
    return Vocabulary(
        synonyms,
        tuple(str(b) for b in document["dependency_buckets"]),
        frozenset(str(w).lower() for w in document["glue_words"]),
    )


# ------------------------------------------------------------------------------- markdown aids
_ATX = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
_ANCHOR_LINK = re.compile(r"\]\(#([^)\s]+)\)")
_WORD = re.compile(r"[^\W\d_]+")
_URL = re.compile(r"(?:https?://|www\.)[^\s<>)\]\"'`]+")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
_MARKDOWN = MarkdownIt("commonmark")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int  # 1-based


def parse_headings(text: str) -> list[Heading]:
    """The ATX headings of ``text`` outside fenced blocks, in order."""
    found: list[Heading] = []
    for line in scan(text):
        if line.code:
            continue
        match = _ATX.match(line.text)
        if match and match.group(2).strip():
            found.append(Heading(len(match.group(1)), match.group(2).strip(), line.number))
    return found


def github_slug(heading: str) -> str:
    """GitHub's anchor for a heading (before the ``-1`` suffix a repeated heading gets)."""
    text = _MD_LINK.sub(lambda m: m.group(1), heading).replace("`", "")
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def slug_map(headings: Sequence[Heading]) -> dict[str, Heading]:
    """slug -> heading for ``headings`` in document order, repeats numbered the way GitHub does."""
    seen: dict[str, int] = {}
    out: dict[str, Heading] = {}
    for heading in headings:
        base = github_slug(heading.text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        out[base if count == 0 else f"{base}-{count}"] = heading
    return out


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _stems(word: str) -> set[str]:
    w = word.lower()
    out = {w}
    for suffix in ("ing", "ion", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            out.add(w[: -len(suffix)])
    return out


def unsupported_words(text: str, support: str) -> list[str]:
    """The words of ``text`` (split on non-letters) no word of ``support`` matches, ignoring case
    and a plural or a verb or noun ending; the glue words of the vocabulary need no support."""
    known: set[str] = set()
    for word in _WORD.findall(support):
        known |= _stems(word)
    glue = vocabulary().glue
    missing: list[str] = []
    for word in _WORD.findall(text):
        if word.lower() in glue or not _stems(word).isdisjoint(known):
            continue
        if word not in missing:
            missing.append(word)
    return missing


# ------------------------------------------------------------------------------------ evidence
@dataclass(frozen=True)
class Ref:
    """One resolved evidence entry."""

    entry: str
    kind: str  # "fact" | "readme" | "tree-absent"
    fact: Fact | None = None
    line: int | None = None
    path: str = ""


def _ctx_lines(ctx: Context) -> int:
    return len(ctx.readme.splitlines())


def resolve_evidence(ctx: Context, op: Op, refusals: list[Refusal]) -> list[Ref]:
    """The op's evidence entries as references, refusing the ones that are not real."""
    refs: list[Ref] = []
    if not op.evidence:
        refusals.append(Refusal(MISSING_EVIDENCE, op.id, "the operation cites no evidence"))
    tree = set(ctx.tree_paths)
    for entry in op.evidence:
        if entry.startswith("readme:"):
            number = entry[7:]
            if not number.isdigit() or not 1 <= int(number) <= _ctx_lines(ctx):
                refusals.append(
                    Refusal(EVIDENCE_UNKNOWN, op.id, f"{entry!r} is not a line of the live README")
                )
            else:
                refs.append(Ref(entry, "readme", line=int(number)))
        elif entry.startswith("tree-absent:"):
            path = entry[12:]
            if not path or path in tree or any(t.startswith(path.rstrip("/") + "/") for t in tree):
                refusals.append(
                    Refusal(EVIDENCE_UNKNOWN, op.id, f"{path!r} is not absent from the pinned tree")
                )
            else:
                refs.append(Ref(entry, "tree-absent", path=path))
        else:
            fact = ctx.fact(entry)
            if fact is None:
                refusals.append(
                    Refusal(EVIDENCE_UNKNOWN, op.id, f"{entry!r} is not a fact of this revision")
                )
                continue
            contradicting = (
                op.kind == DELETE_LINE
                and fact.kind == "link_target"
                and fact.polarity == "CONTRADICTED"
            )
            if fact.polarity != "SUPPORTED" and not contradicting:
                refusals.append(
                    Refusal(
                        EVIDENCE_WRONG_POLARITY,
                        op.id,
                        f"{entry} is {fact.polarity}; an operation rests on SUPPORTED facts",
                    )
                )
                continue
            refs.append(Ref(entry, "fact", fact=fact))
    return refs


def evidence_record(ref: Ref) -> dict[str, Any]:
    """The bundle's statement of one resolved entry (``corrections.json``)."""
    if ref.kind == "fact" and ref.fact is not None:
        return {
            "ref": ref.entry,
            "status": ref.fact.polarity,
            "kind": ref.fact.kind,
            "value": ref.fact.value[:160],
        }
    if ref.kind == "readme":
        return {
            "ref": ref.entry,
            "status": "README_TEXT",
            "kind": "readme_line",
            "value": ref.entry,
        }
    return {"ref": ref.entry, "status": "TREE_ABSENT", "kind": "tree_path", "value": ref.path}


# ------------------------------------------------------------------------------------ the rules
def _single_line(text: str) -> str | None:
    body = text[:-1] if text.endswith("\n") else text
    return None if "\n" in body or "\r" in body.rstrip("\r") else body.rstrip("\r")


def _heading_of(line: str) -> tuple[int, str] | None:
    match = _ATX.match(line)
    return (
        (len(match.group(1)), match.group(2).strip()) if match and match.group(2).strip() else None
    )


def _in_code(ctx: Context, start: int, end: int) -> bool:
    first = _line_of(ctx.readme, start)
    last = _line_of(ctx.readme, max(start, end - 1))
    return any(ctx.lines[n - 1].in_fence for n in range(first, last + 1) if n <= len(ctx.lines))


def _words_key(text: str) -> list[str]:
    return [w for w in heading_key(text).split() if w != "and"]


def _check_retitle(ctx: Context, p: Placed, refs: list[Ref], out: list[Refusal]) -> None:
    op = p.op
    old, new = _single_line(op.anchor), _single_line(op.replacement)
    if old is None or new is None or op.anchor.endswith("\n") != op.replacement.endswith("\n"):
        out.append(
            Refusal(RETITLE_NOT_A_HEADING, op.id, "a RETITLE is one heading line to one line")
        )
        return
    a, b = _heading_of(old), _heading_of(new)
    if a is None or b is None or _in_code(ctx, p.start, p.end):
        out.append(
            Refusal(
                RETITLE_NOT_A_HEADING,
                op.id,
                "the anchor and the replacement are each one heading line",
            )
        )
        return
    if a[0] != b[0]:
        out.append(
            Refusal(RETITLE_NOT_COSMETIC, op.id, f"the heading level changes (H{a[0]} to H{b[0]})")
        )
        return
    if a[0] == 1:
        out.append(
            Refusal(RETITLE_NOT_COSMETIC, op.id, "the H1 names the product; it is not retitled")
        )
        return
    wanted = f"readme:{_line_of(ctx.readme, p.start)}"
    if wanted not in op.evidence:
        out.append(Refusal(EVIDENCE_NOT_THE_ANCHOR, op.id, f"the evidence must include {wanted}"))
    if _words_key(a[1]) == _words_key(b[1]):
        return
    vocab = vocabulary()
    if a[0] == 2 and b[1] in vocab.synonyms and heading_key(a[1]) in vocab.synonyms[b[1]]:
        return
    out.append(
        Refusal(
            RETITLE_NOT_COSMETIC,
            op.id,
            f"{a[1]!r} to {b[1]!r} neither keeps the words (ignoring case, '&' and 'and', "
            "punctuation) nor is the standard name of that section",
        )
    )


def _check_reflow(ctx: Context, p: Placed, refs: list[Ref], out: list[Refusal]) -> None:
    op = p.op
    # Identical non-whitespace characters, and stronger: the same whitespace-separated tokens in
    # the same order, so no space is added inside a word or removed between two.
    if op.anchor.split() != op.replacement.split():
        out.append(Refusal(REFLOW_CHANGES_CHARACTERS, op.id, "a REFLOW changes whitespace only"))
        return
    before = ctx.readme[: p.start]
    after = ctx.readme[p.end :]
    blank_before = p.start == 0 or before.endswith("\n\n")
    blank_after = not after or after.startswith("\n") or after.startswith("\r\n")
    if (
        _in_code(ctx, p.start, p.end)
        or not blank_before
        or not blank_after
        or not _paragraphs_only(op.anchor)
        or not _paragraphs_only(op.replacement)
    ):
        out.append(
            Refusal(REFLOW_NOT_A_PARAGRAPH, op.id, "a REFLOW is whole paragraphs outside code")
        )
        return
    if len(_blocks(op.anchor)) != len(_blocks(op.replacement)) or _targets(op.anchor) != _targets(
        op.replacement
    ):
        out.append(
            Refusal(REFLOW_CHANGES_LINKS, op.id, "the links or images differ after the reflow")
        )


def _blocks(text: str) -> list[str]:
    return [t.type for t in _MARKDOWN.parse(text) if t.type.endswith("_open") and t.level == 0]


def _paragraphs_only(text: str) -> bool:
    kinds = _blocks(text)
    return bool(kinds) and all(kind == "paragraph_open" for kind in kinds)


def _targets(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for token in _MARKDOWN.parse(text):
        for child in token.children or []:
            if child.type == "link_open":
                found.append(("link", str(child.attrGet("href"))))
            elif child.type == "image":
                found.append(("image", str(child.attrGet("src"))))
    return found


_EXTERNAL = ("http://", "https://", "mailto:", "ftp://", "//", "#", "tel:", "data:")


def _relative_target(raw: str) -> str | None:
    target = raw.strip()
    if (
        not target
        or target.lower().startswith(_EXTERNAL)
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)
    ):
        return None
    return unquote(target.split("#", 1)[0].split("?", 1)[0])


def _absent(ctx: Context, target: str) -> bool:
    if not target:
        return False
    wanted = target.lstrip("./").rstrip("/")
    tree = set(ctx.tree_paths)
    return wanted not in tree and not any(path.startswith(wanted + "/") for path in tree)


def _check_delete(ctx: Context, p: Placed, refs: list[Ref], out: list[Refusal]) -> None:
    op = p.op
    line = _single_line(op.anchor)
    if line is None or not _LIST_ITEM.match(line) or _in_code(ctx, p.start, p.end):
        out.append(
            Refusal(DELETE_NOT_A_LIST_ITEM, op.id, "the anchor is exactly one list-item line")
        )
        return
    links = _MD_LINK.findall(line)
    if not links:
        out.append(Refusal(DELETE_NOT_A_LIST_ITEM, op.id, "the list item holds no markdown link"))
        return
    contradicted = {
        f.value: f.id
        for f in ctx.facts.facts
        if f.kind == "link_target" and f.polarity == "CONTRADICTED"
    }
    cited = {r.entry for r in refs}
    for _text, raw in links:
        target = _relative_target(raw)
        if target is None:
            out.append(Refusal(DELETE_LINK_NOT_BROKEN, op.id, f"{raw!r} is not a relative link"))
            continue
        fact_id = contradicted.get(target)
        absent = _absent(ctx, target)
        if not absent and fact_id is None:
            out.append(
                Refusal(DELETE_LINK_NOT_BROKEN, op.id, f"{target!r} is in the repository tree")
            )
        elif fact_id is not None and fact_id not in cited:
            out.append(Refusal(DELETE_EVIDENCE_MISSING, op.id, f"the evidence must name {fact_id}"))
        elif fact_id is None and f"tree-absent:{target}" not in cited:
            out.append(
                Refusal(
                    DELETE_EVIDENCE_MISSING, op.id, f"the evidence must name tree-absent:{target}"
                )
            )
    follow = ctx.readme[p.end :]
    if follow[:1] in {" ", "\t"}:
        out.append(Refusal(DELETE_ORPHANS_TEXT, op.id, "an indented line continues the item"))


def _urls_allowed(ctx: Context) -> set[str]:
    allowed = {u.rstrip(".,;:") for u in _URL.findall(ctx.readme)}
    allowed |= {
        f.value for f in ctx.facts.facts if f.kind == "link_target" and f.polarity == "SUPPORTED"
    }
    return allowed


@dataclass(frozen=True)
class Section:
    title: str
    heading_line: int  # 1-based in the inserted text
    body: tuple[str, ...]  # lines after the heading


def split_sections(inserted: str) -> tuple[list[Section], str]:
    """``(sections, problem)``: the H2 sections of inserted text, or why it is not only sections."""
    lines = inserted.splitlines()
    heads = parse_headings(inserted)
    if not heads or heads[0].line != 1 or heads[0].level != 2:
        return [], "the inserted text starts with an H2 heading"
    if any(h.level == 1 for h in heads):
        return [], "the inserted text has an H1"
    twos = [h for h in heads if h.level == 2]
    sections: list[Section] = []
    for index, head in enumerate(twos):
        end = twos[index + 1].line - 1 if index + 1 < len(twos) else len(lines)
        sections.append(Section(head.text, head.line, tuple(lines[head.line : end])))
    return sections, ""


def _check_insert(
    ctx: Context, p: Placed, refs: list[Ref], corrected: str, out: list[Refusal]
) -> None:
    op, inserted = p.op, p.text
    if len(inserted) > MAX_INSERT:
        out.append(
            Refusal(INSERT_TOO_LONG, op.id, f"{len(inserted)} characters; at most {MAX_INSERT}")
        )
        return
    first = op.anchor.splitlines()[0] if op.anchor.splitlines() else ""
    if _heading_of(first) is None or _in_code(ctx, p.start, p.start + 1):
        out.append(Refusal(INSERT_SHAPE, op.id, "an insertion goes before a heading line"))
        return
    if not (p.start == 0 or ctx.readme[: p.start].endswith("\n\n")) or not inserted.endswith(
        "\n\n"
    ):
        out.append(
            Refusal(INSERT_SHAPE, op.id, "the inserted text is whole blocks, blank-line separated")
        )
        return
    sections, problem = split_sections(inserted)
    if problem:
        out.append(Refusal(INSERT_SHAPE, op.id, problem))
        return
    existing = {heading_key(h.text) for h in parse_headings(ctx.readme) if h.level == 2}
    urls = _urls_allowed(ctx)
    for url in _URL.findall(inserted):
        if url.rstrip(".,;:") not in urls:
            out.append(
                Refusal(
                    INSERT_URL_UNSUPPORTED,
                    op.id,
                    f"{url} is neither in the README nor a SUPPORTED link",
                )
            )
    hits = narration(inserted)
    if hits or assurance_narration(scan(inserted)).outcome == FAIL:
        out.append(Refusal(INSERT_NARRATION, op.id, f"the inserted text carries narration {hits}"))
    titles: set[str] = set()
    for section in sections:
        if section.title not in SECTIONS:
            out.append(
                Refusal(
                    INSERT_SECTION_NOT_ALLOWED,
                    op.id,
                    f"{section.title!r} is not one of {', '.join(SECTIONS)}",
                )
            )
            continue
        if heading_key(section.title) in existing or section.title in titles:
            out.append(
                Refusal(INSERT_DUPLICATE_SECTION, op.id, f"the README already has {section.title}")
            )
            continue
        titles.add(section.title)
        if section.title == SECTION_NAVIGATION:
            _check_navigation(ctx, p, section, refs, corrected, out)
        elif section.title == SECTION_DEPENDENCIES:
            _check_dependencies(ctx, p, section, refs, corrected, out)
        else:
            _check_glance(ctx, p, section, refs, out)


def _need_readme_ref(p: Placed, refs: list[Ref], what: str, out: list[Refusal]) -> None:
    if not any(r.kind == "readme" for r in refs):
        out.append(
            Refusal(
                MISSING_EVIDENCE,
                p.op.id,
                f"{what} cites the README text it summarises (readme:<line>)",
            )
        )


_NAV_ITEM = re.compile(r"^- \[([^\]]+)\]\(#([^)\s]+)\)$")


def _check_navigation(
    ctx: Context, p: Placed, section: Section, refs: list[Ref], corrected: str, out: list[Refusal]
) -> None:
    _need_readme_ref(p, refs, "Navigation", out)
    slugs = slug_map([h for h in parse_headings(corrected) if h.level == 2])
    items = [line for line in section.body if line.strip()]
    seen: set[str] = set()
    bad: list[str] = []
    for line in items:
        match = _NAV_ITEM.match(line)
        if match is None:
            bad.append(f"{line!r} is not '- [Heading](#slug)'")
            continue
        text, slug = match.group(1), match.group(2)
        heading = slugs.get(slug)
        if heading is None:
            bad.append(f"#{slug} is not the slug of an H2 of the corrected README")
        elif heading.text != text:
            bad.append(f"link text {text!r} is not the heading {heading.text!r}")
        elif slug in seen:
            bad.append(f"#{slug} is listed twice")
        seen.add(slug)
    if len(items) < 2:
        bad.append("a navigation lists at least two sections")
    if bad:
        out.append(Refusal(NAVIGATION_MISMATCH, p.op.id, "; ".join(bad[:4])))


_BULLET = re.compile(r"^- `([^`]+)`(.*)$")


def _bucket_of(fact_id: str) -> str:
    if fact_id.startswith("dependency:development."):
        return "Development Dependencies"
    if fact_id.startswith("dependency:optional."):
        return "Optional Dependencies"
    return "Required Package Dependencies"


def _check_dependencies(
    ctx: Context, p: Placed, section: Section, refs: list[Ref], corrected: str, out: list[Refusal]
) -> None:
    vocab = vocabulary()
    deps: dict[str, list[Fact]] = {}
    for fact in ctx.facts.facts:
        if fact.kind == "dependency" and fact.polarity == "SUPPORTED":
            deps.setdefault(fact.value, []).append(fact)
    cited = {r.entry for r in refs}
    cited_lines = [r.line for r in refs if r.kind == "readme" and r.line is not None]
    live_lines = ctx.readme.splitlines()
    corrected_slugs = slug_map(parse_headings(corrected))
    bucket = ""
    bullets = 0
    bad: list[str] = []
    support_parts = [ctx.readme]
    for line in section.body:
        if not line.strip():
            continue
        head = _ATX.match(line)
        if head is not None:
            if len(head.group(1)) != 3 or head.group(2).strip() not in vocab.buckets:
                bad.append(f"heading {line!r} is not one of the dependency buckets")
            bucket = head.group(2).strip()
            continue
        match = _BULLET.match(line)
        if match is None:
            bad.append(f"{line!r} is not a bullet that starts with a code span")
            continue
        bullets += 1
        code, rest = match.group(1), match.group(2)
        backing = deps.get(code)
        if backing is not None:
            ids = {f.id for f in backing}
            if not ids & cited:
                bad.append(f"`{code}` needs its fact ({', '.join(sorted(ids))}) in the evidence")
            elif bucket and bucket not in {_bucket_of(i) for i in ids}:
                bad.append(f"`{code}` is not a {bucket} fact")
            for fact in backing:
                if fact.id in cited:
                    support_parts += [fact.value, *(e.detail or "" for e in fact.evidence)]
        else:
            lines_with = [n for n in cited_lines if code in live_lines[n - 1]]
            if not lines_with or code not in ctx.readme:
                bad.append(
                    f"`{code}` is neither a SUPPORTED dependency nor a cited line of the README"
                )
            elif bucket != "Optional Dependencies" and bucket != "Native and System Requirements":
                bad.append(f"`{code}` rests on README text, so it belongs under an optional bucket")
        remainder = _MD_LINK.sub(lambda m: m.group(1), rest)
        for _text, target in _MD_LINK.findall(rest):
            slug = target[1:] if target.startswith("#") else ""
            matched = corrected_slugs.get(slug)
            if matched is None or matched.text != _text:
                bad.append(
                    f"the link {target!r} is not the heading it names in the corrected README"
                )
        missing = unsupported_words(remainder, "\n".join(support_parts))
        if missing:
            bad.append(f"words of `{code}`'s bullet no source states: {', '.join(missing)}")
    if bullets == 0:
        bad.append("an empty Dependencies section")
    if bad:
        out.append(Refusal(DEPENDENCIES_UNSUPPORTED, p.op.id, "; ".join(bad[:4])))


def glance_bodies(inserted: str) -> list[str]:
    """The Mermaid sources of the At a Glance section(s) of inserted text."""
    sections, _problem = split_sections(inserted)
    bodies: list[str] = []
    for section in sections:
        if section.title == SECTION_GLANCE:
            lines = [line + "\n" for line in section.body]
            bodies += [fence.body for fence in mermaid_fences(lines)]
    return bodies


def glance_notes(body: str) -> list[dict[str, str]]:
    """What a diagram is allowed to differ in from the canonical drawing, for the record:
    ``[{"code", "detail"}]`` of the tolerated lint defects and of the drawing-form (COMPOSING)
    failures of the contract."""
    notes = [
        {"code": d.code, "detail": d.detail}
        for d in lint_source(body).defects
        if d.code in GLANCE_TOLERATED_DEFECTS
    ]
    try:
        has_inputs = bool(parse(body).glance.starting_points)
    except NotAGlanceError:
        return notes
    notes += [
        {"code": "CONTRACT_COMPOSING", "detail": f.message}
        for f in contract.topology_failures(body, has_inputs)
        if f.stage == contract.COMPOSING
    ]
    return notes


def _check_glance(
    ctx: Context, p: Placed, section: Section, refs: list[Ref], out: list[Refusal]
) -> None:
    _need_readme_ref(p, refs, "At a Glance", out)
    lines = [line + "\n" for line in section.body]
    fences = mermaid_fences(lines)
    fenced = {n for f in fences for n in range(f.first, f.last + 2)}  # opener .. closer
    stray = [
        line for n, line in enumerate(section.body, start=1) if line.strip() and n not in fenced
    ]
    if len(fences) != 1 or stray:
        out.append(
            Refusal(
                GLANCE_NOT_A_DIAGRAM, p.op.id, "At a Glance is one mermaid block and nothing else"
            )
        )
        return
    body = fences[0].body
    try:
        glance = parse(body).glance
    except NotAGlanceError as error:
        out.append(Refusal(GLANCE_NOT_A_DIAGRAM, p.op.id, f"not the At a Glance chain: {error}"))
        return
    report = lint_source(body)
    serious = sorted(c for c in report.codes if c not in GLANCE_TOLERATED_DEFECTS)
    content = [
        f.message
        for f in contract.topology_failures(body, bool(glance.starting_points))
        if f.stage == contract.PLANNING
    ]
    if serious:
        out.append(Refusal(GLANCE_LINT, p.op.id, f"the diagram lint finds {', '.join(serious)}"))
    elif content:
        out.append(Refusal(GLANCE_LINT, p.op.id, content[0][:160]))
    support = (
        ctx.readme + "\n" + "\n".join(f.value for f in ctx.facts.facts if f.polarity == "SUPPORTED")
    )
    missing = unsupported_words(" ".join(glance.labels), support)
    if missing:
        out.append(
            Refusal(
                GLANCE_UNSUPPORTED_WORDS,
                p.op.id,
                "label words in neither the README nor a SUPPORTED fact: " + ", ".join(missing),
            )
        )


def check_ops(ctx: Context, ops: Sequence[Op]) -> list[Refusal]:
    """Every typed reason ``ops`` may not be applied to ``ctx.readme``; empty when they may."""
    if not ops:
        return [Refusal(NO_OPERATIONS, "", "there are no operations to apply")]
    try:
        placed = place(ctx.readme, ops)
    except LiveOpError as exc:
        return [Refusal(exc.code, exc.op, str(exc))]
    corrected = apply_placed(ctx.readme, placed)[0]
    out: list[Refusal] = []
    allowed = _urls_allowed(ctx)
    for item in placed:
        refs = resolve_evidence(ctx, item.op, out)
        if item.op.kind == RETITLE:
            _check_retitle(ctx, item, refs, out)
        elif item.op.kind == REFLOW:
            _check_reflow(ctx, item, refs, out)
        elif item.op.kind == DELETE_LINE:
            _check_delete(ctx, item, refs, out)
        else:
            _check_insert(ctx, item, refs, corrected, out)
        if item.op.kind != INSERT_BEFORE:
            for url in _URL.findall(item.text):
                if url.rstrip(".,;:") not in allowed:
                    out.append(Refusal(INSERT_URL_UNSUPPORTED, item.op.id, f"{url} is new"))
    out += _heading_refusals(ctx, corrected)
    return out


def _heading_refusals(ctx: Context, corrected: str) -> list[Refusal]:
    before = slug_map(parse_headings(ctx.readme))
    after = slug_map(parse_headings(corrected))
    out: list[Refusal] = []
    plain_before = [github_slug(h.text) for h in parse_headings(ctx.readme)]
    plain_after = [github_slug(h.text) for h in parse_headings(corrected)]
    for slug in sorted(set(plain_after)):
        if plain_after.count(slug) > 1 and plain_before.count(slug) <= 1:
            out.append(Refusal(DUPLICATE_HEADING, "", f"two headings would share #{slug}"))
    for slug in sorted(set(_ANCHOR_LINK.findall(ctx.readme))):
        if slug in before and slug not in after:
            out.append(
                Refusal(BROKEN_ANCHOR_LINK, "", f"a link to #{slug} would point at no heading")
            )
    return out


def line_of(original: str, placed: Placed) -> int:
    """The 1-based line of the live README an operation starts on."""
    return _line_of(original, placed.start)


def retitle_reason(anchor: str, replacement: str) -> str:
    """``same_words`` when a retitle keeps the heading's words (ignoring case, '&'/'and',
    punctuation), else ``standard_name``: the family's name for the section."""
    old, new = _heading_of(anchor.strip()), _heading_of(replacement.strip())
    if old is not None and new is not None and _words_key(old[1]) == _words_key(new[1]):
        return "same_words"
    return "standard_name"


def inserted_titles(placed: Placed) -> list[str]:
    """The H2 titles an INSERT_BEFORE opens (empty for the other kinds)."""
    if placed.op.kind != INSERT_BEFORE:
        return []
    return [s.title for s in split_sections(placed.text)[0]]
