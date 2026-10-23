"""``propose-ops``: write the live-anchored operations list for a repository, deterministically.

``correct-readme --ops`` applies a list of operations (``live_ops.py``) to the live README; this
module writes that list from the README, the verified facts and the pinned tree, so no bundle needs
a hand-written file. No model, no prompt, no new fact kind: every rule below is a function of the
three inputs, and every proposed operation has already passed ``live_ops.check_ops`` (the check is
the proposer's last step and its only authority; nothing here loosens it).

Six rules, each proposing nothing for a section the README already has:

1. ``RETITLE``   an H2 or H3 whose words map to a standard heading through the closed vocabulary
                 (``data/readme_standard/live_anchored_vocabulary.yaml`` and ``load_standard()``),
                 or which differs from title case only;
2. ``REFLOW``    consecutive badge lines at the top of the README, joined onto one line;
3. ``DELETE_LINE`` a single list item whose every link is relative and absent from the tree;
4. ``INSERT_BEFORE`` a Navigation section (at least four H2 sections in the corrected README);
5. ``INSERT_BEFORE`` a Dependencies section from SUPPORTED ``dependency`` facts, bucketed by
   fact id;
6. ``INSERT_BEFORE`` an At a Glance diagram built with ``components/readme_diagram`` from the
   README's own capabilities list (each bullet cut to a few of its own words) and from SUPPORTED
   ``format`` facts (or, for a side with none, the README's own formats table).

A candidate operation that cannot be proposed is reported with a typed reason, never dropped
silently; ``GLANCE_UNDERIVABLE`` is the reason for a diagram the README and facts cannot fill
without inventing a word. The report is the contract between this module and the reviewer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from markdown_it import MarkdownIt

from repository_presenter.components.readme.acceptance.judge import heading_key, load_standard
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import CorrectionError
from repository_presenter.components.readme_correction.live_ops import (
    DELETE_LINE,
    INSERT_BEFORE,
    REFLOW,
    RETITLE,
    SECTION_DEPENDENCIES,
    SECTION_GLANCE,
    SECTION_NAVIGATION,
    Heading,
    Op,
    Refusal,
    _absent,
    _bucket_of,
    _relative_target,
    apply_ops,
    check_ops,
    github_slug,
    ops_to_json,
    parse_headings,
    slug_map,
    unsupported_words,
    vocabulary,
)
from repository_presenter.components.readme_correction.model import Context, CorrectionResult
from repository_presenter.components.readme_diagram import Glance, balanced_columns, build_block
from repository_presenter.components.readme_diagram.build import build_body
from repository_presenter.components.readme_diagram.contract import (
    MIN_CAPABILITIES,
    title_failure,
    topology_failures,
)
from repository_presenter.components.readme_diagram.lint import lint_source
from repository_presenter.core.facts import Fact, read_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths

REPORT_KIND = "propose_ops_report"
README_PATH = "README.md"

# Outcomes of a proposal.
PROPOSED = "PROPOSED"
NO_CHANGE = "NO_CHANGE"
NO_LIVE_README = "NO_LIVE_README"

# The six rules (the report names each operation and each skipped candidate by one of these).
RULE_RETITLE = "RETITLE"
RULE_REFLOW = "REFLOW"
RULE_DELETE = "DELETE_LINE"
RULE_NAVIGATION = "NAVIGATION"
RULE_DEPENDENCIES = "DEPENDENCIES"
RULE_GLANCE = "AT_A_GLANCE"
RULE_ALL = "ALL"

# Typed reasons a candidate operation is not proposed.
SECTION_PRESENT = "SECTION_PRESENT"
TARGET_EXISTS = "TARGET_EXISTS"
HEADING_NOT_PLAIN = "HEADING_NOT_PLAIN"
ANCHOR_NOT_UNIQUE = "ANCHOR_NOT_UNIQUE"
CRLF_README = "CRLF_README"
NOT_AFTER_BLANK = "NOT_AFTER_BLANK"
MIXED_LINKS = "MIXED_LINKS"
CONTINUATION_LINE = "CONTINUATION_LINE"
WOULD_EMPTY_LIST = "WOULD_EMPTY_LIST"
TARGET_UNRESOLVABLE = "TARGET_UNRESOLVABLE"
TOO_FEW_SECTIONS = "TOO_FEW_SECTIONS"
NO_PLACE = "NO_PLACE"
NO_SUPPORTED_DEPENDENCIES = "NO_SUPPORTED_DEPENDENCIES"
GLANCE_UNDERIVABLE = "GLANCE_UNDERIVABLE"
REFUSED_BY_CHECK = "REFUSED_BY_CHECK"
INTRODUCES_FAILURE = "INTRODUCES_FAILURE"
#: The closed set of reasons; a report carries no other code.
REASONS: frozenset[str] = frozenset(
    {
        SECTION_PRESENT,
        TARGET_EXISTS,
        HEADING_NOT_PLAIN,
        ANCHOR_NOT_UNIQUE,
        CRLF_README,
        NOT_AFTER_BLANK,
        MIXED_LINKS,
        CONTINUATION_LINE,
        WOULD_EMPTY_LIST,
        TARGET_UNRESOLVABLE,
        TOO_FEW_SECTIONS,
        NO_PLACE,
        NO_SUPPORTED_DEPENDENCIES,
        GLANCE_UNDERIVABLE,
        REFUSED_BY_CHECK,
        INTRODUCES_FAILURE,
    }
)

#: What a Glance cannot be derived from (``detail`` of a ``GLANCE_UNDERIVABLE`` skip).
NO_PRODUCT = "NO_PRODUCT"
NO_CAPABILITIES_LIST = "NO_CAPABILITIES_LIST"
FEWER_THAN_THREE_CAPABILITIES = "FEWER_THAN_THREE_CAPABILITIES"
NO_STARTING_POINT = "NO_STARTING_POINT"
NO_OUTPUT = "NO_OUTPUT"
DIAGRAM_CONTRACT = "DIAGRAM_CONTRACT"

# Limits.
MAX_GLANCE_CAPABILITIES = 6
MAX_LABEL_WORDS = 5
MAX_FORMATS = 5
NAVIGATION_MIN_SECTIONS = 4
MAX_OMITTED_ENTRIES = 3
#: Words a title-case heading keeps in lower case (articles, coordinating conjunctions and
#: prepositions of up to three letters), except as the first or last word.
SMALL_WORDS: frozenset[str] = frozenset(
    {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by", "in"}
    | {"of", "on", "to", "up", "via", "vs", "per", "off"}
)
#: Headings that already name a navigation / dependencies section under another word.
NAVIGATION_NAMES: frozenset[str] = frozenset({"navigation", "table of contents", "contents"})
DEPENDENCY_NAMES: frozenset[str] = frozenset(
    {
        "dependencies",
        "requirements",
        "prerequisites",
        "system requirements",
        "dependencies and requirements",
        "requirements and dependencies",
    }
)
GLANCE_NAMES: frozenset[str] = frozenset({"at a glance"})

_MARKDOWN = MarkdownIt("commonmark").enable("table")
_HEADING_LINE = re.compile(r"^( {0,3}#{2,3}[ \t]+)(.*?)([ \t]*)$")
_ANY_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_CLOSING_HASHES = re.compile(r"[ \t]#+[ \t]*$")
_PLAIN_HEADING = re.compile(r"^[\w &/'\".,:;?!()+#-]+$")
_BADGE_ITEM = r"(?:\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|!\[[^\]]*\]\([^)]*\))"
_BADGE_LINE = re.compile(rf"^\s*{_BADGE_ITEM}(?:\s+{_BADGE_ITEM})*\s*$")
_LIST_ITEM_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LABEL_OK = re.compile(r"^[\w ,.'+#/:()-]+$")
_DASHES = chr(0x2013) + chr(0x2014)  # en and em dash
_CUTS = re.compile(
    r",| and | using | with | from | in | - |" + f" [{_DASHES}] " + r"|:| \(",
    flags=re.IGNORECASE,
)
_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
_IN_VERBS = frozenset({"read", "reads", "load", "loads", "open", "opens", "import", "parse"})
_OUT_VERBS = frozenset({"write", "writes", "save", "saves", "export", "exports", "render"})
_DOT_EXTENSION = re.compile(r"`(\.[A-Za-z0-9]{2,5})`")
_YES = ("yes", "✓", "✔", "✅", "supported", "true", "x")


# ------------------------------------------------------------------------------------- records
@dataclass(frozen=True)
class Skip:
    """One candidate operation that is not proposed, with its typed reason."""

    rule: str
    code: str
    line: int
    detail: str
    check_code: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "code": self.code,
            "line": self.line,
            "detail": self.detail,
            **({"check_code": self.check_code} if self.check_code else {}),
        }


@dataclass(frozen=True)
class Proposed:
    """One operation of the list, with the rule that wrote it."""

    op: Op
    rule: str
    line: int
    sections: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "id": self.op.id,
            "kind": self.op.kind,
            "rule": self.rule,
            "line": self.line,
            "sections": list(self.sections),
            "evidence": list(self.op.evidence),
            "anchor": self.op.anchor,
            "replacement": self.op.replacement,
        }


@dataclass
class Proposal:
    """The operations list and the candidates that were not proposed."""

    repository: str
    revision: str
    proposed: list[Proposed] = field(default_factory=list)
    skipped: list[Skip] = field(default_factory=list)
    outcome: str = NO_CHANGE
    reason: str = ""

    @property
    def ops(self) -> tuple[Op, ...]:
        return tuple(item.op for item in self.proposed)

    def counts(self) -> dict[str, int]:
        found: dict[str, int] = {}
        for item in self.proposed:
            found[item.op.kind] = found.get(item.op.kind, 0) + 1
        return dict(sorted(found.items()))

    def report(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "kind": REPORT_KIND,
            "repository": self.repository,
            "revision": self.revision,
            "outcome": self.outcome,
            "reason": self.reason,
            "counts": self.counts(),
            "proposed": [item.as_json() for item in self.proposed],
            "not_proposed": [skip.as_json() for skip in self.skipped],
        }


@dataclass(frozen=True)
class Cand:
    """A single-line or paragraph operation under consideration (RETITLE, REFLOW, DELETE_LINE)."""

    key: str
    rule: str
    op: Op
    line: int
    #: What replaces this candidate when the check refuses it: a vocabulary rename that would
    #: break an anchor link falls back to the title-case spelling of the same heading.
    fallback: Cand | None = None


@dataclass(frozen=True)
class Section:
    """One inserted H2 section: its text, where it goes (the 1-based line of the heading it goes
    before) and the evidence it cites."""

    rule: str
    title: str
    text: str
    anchor_line: int
    evidence: tuple[str, ...]


# ----------------------------------------------------------------------------------- the README
class Readme:
    """The live README read once: raw lines with their endings, headings, helpers for anchors."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.text = ctx.readme
        self.raw = ctx.readme.splitlines(keepends=True)
        self.crlf = "\r" in ctx.readme
        self.headings = parse_headings(ctx.readme)

    def ending(self, line: int) -> str:
        raw = self.raw[line - 1]
        return raw[len(raw.rstrip("\r\n")) :]

    def body(self, line: int) -> str:
        return self.raw[line - 1].rstrip("\r\n")

    def in_fence(self, line: int) -> bool:
        return self.ctx.lines[line - 1].in_fence

    def anchor(self, first: int, last: int | None = None) -> str | None:
        """The text of lines ``first..last`` when it occurs exactly once in the README."""
        text = "".join(self.raw[first - 1 : last or first])
        return text if text and _count(self.text, text) == 1 else None

    def unique_anchor(self, line: int, extra: int = 3) -> str | None:
        """The heading line at ``line``, with up to ``extra`` following lines until it is unique."""
        for last in range(line, min(len(self.raw), line + extra) + 1):
            anchor = self.anchor(line, last)
            if anchor is not None:
                return anchor
        return None

    def h2(self) -> list[Heading]:
        return [h for h in self.headings if h.level == 2]


def _count(text: str, needle: str) -> int:
    found, index = 0, text.find(needle)
    while index != -1:
        found += 1
        index = text.find(needle, index + 1)
    return found


# ------------------------------------------------------------------------------------ rule 1
def title_case(text: str) -> str:
    """``text`` with the first letter of each word that title case capitalises raised; it only ever
    raises a lower-case first letter and never touches a word that has a capital or a digit
    inside, a code span, a link or punctuation other than a trailing mark (so ``glTF``, ``PDF``
    and ``3D`` stay as written, and a heading that is already in title case is returned as is)."""
    parts = re.split(r"(\s+)", text)
    words = [index for index, part in enumerate(parts) if part and not part.isspace()]
    out = list(parts)
    for position, index in enumerate(words):
        word = parts[index]
        match = re.fullmatch(r"([(\"']?)([a-z][a-z'-]*)([.,:;!?)\"']*)", word)
        if match is None:
            continue
        lead, core, tail = match.groups()
        edge = position == 0 or position == len(words) - 1
        if core in SMALL_WORDS and not edge:
            continue
        out[index] = lead + core[0].upper() + core[1:] + tail
    return "".join(out)


def _standard_names() -> dict[str, str]:
    return {
        heading_key(str(name)): str(name)
        for name in load_standard().headings.values()
        if name is not None
    }


def _element_order() -> dict[str, int]:
    """heading key -> position of the standard element in the common schema's order."""
    order: dict[str, int] = {}
    for index, name in enumerate(load_standard().headings.values()):
        if name is not None:
            order[heading_key(str(name))] = index
    return order


def retitles(rd: Readme) -> tuple[list[Cand], list[Skip]]:
    vocab = vocabulary()
    standard = _standard_names()
    synonym_of = {key: name for name, keys in vocab.synonyms.items() for key in keys}
    h2_keys = {heading_key(h.text) for h in rd.h2()}
    claimed: set[str] = set()
    cands: list[Cand] = []
    skips: list[Skip] = []
    for heading in rd.headings:
        if heading.level not in (2, 3):
            continue
        key = heading_key(heading.text)
        target = heading.text
        if heading.level == 2 and key in standard:
            target = standard[key]
        elif heading.level == 2 and key in synonym_of:
            target = synonym_of[key]
        else:
            target = title_case(heading.text)
        if target == heading.text:
            continue
        if heading.level == 2 and heading_key(target) != key:
            # a vocabulary rename: one live heading per standard section, and none already there
            if heading_key(target) in h2_keys or heading_key(target) in claimed:
                skips.append(
                    Skip(
                        RULE_RETITLE,
                        TARGET_EXISTS,
                        heading.line,
                        f"{heading.text!r} would become {target!r}, which the README already has",
                    )
                )
                continue
            claimed.add(heading_key(target))
        made = _retitle(rd, heading, target)
        if isinstance(made, Skip):
            skips.append(made)
            continue
        case = title_case(heading.text)
        if heading_key(target) != key and case != heading.text:
            fallback = _retitle(rd, heading, case)
            if isinstance(fallback, Cand):
                made = Cand(made.key, made.rule, made.op, made.line, fallback)
        cands.append(made)
    return cands, skips


def _retitle(rd: Readme, heading: Heading, target: str) -> Cand | Skip:
    """The RETITLE of ``heading`` to ``target``, or the typed reason it cannot be one."""
    line = rd.body(heading.line)
    match = _HEADING_LINE.match(line)
    if (
        match is None
        or match.group(2).strip() != heading.text
        or _CLOSING_HASHES.search(line)
        or not _PLAIN_HEADING.match(heading.text)
        or not _PLAIN_HEADING.match(target)
    ):
        return Skip(
            RULE_RETITLE,
            HEADING_NOT_PLAIN,
            heading.line,
            f"{heading.text!r} is not a plain ATX heading of words",
        )
    anchor = rd.anchor(heading.line)
    if anchor is None:
        return Skip(
            RULE_RETITLE,
            ANCHOR_NOT_UNIQUE,
            heading.line,
            f"the line {line!r} occurs more than once in the README",
        )
    replacement = match.group(1) + target + match.group(3) + rd.ending(heading.line)
    op_id = f"retitle-L{heading.line}"
    op = Op(op_id, RETITLE, anchor, replacement, (f"readme:{heading.line}",))
    return Cand(op_id, RULE_RETITLE, op, heading.line)


# ------------------------------------------------------------------------------------ rule 2
def reflows(rd: Readme) -> tuple[list[Cand], list[Skip]]:
    """Badge lines at the top (before the first H2) joined onto one line per paragraph."""
    limit = rd.h2()[0].line if rd.h2() else len(rd.raw) + 1
    cands: list[Cand] = []
    skips: list[Skip] = []
    line = 1
    while line < limit:
        if not rd.body(line).strip() or rd.in_fence(line) or _ANY_HEADING.match(rd.body(line)):
            line += 1
            continue
        end = line
        while (
            end + 1 < limit
            and rd.body(end + 1).strip()
            and not _ANY_HEADING.match(rd.body(end + 1))
        ):
            end += 1
        block = range(line, end + 1)
        if len(block) >= 2 and all(_BADGE_LINE.match(rd.body(n)) for n in block):
            joined = " ".join(rd.body(n).strip() for n in block) + rd.ending(end)
            anchor = rd.anchor(line, end)
            if line > 1 and rd.body(line - 1).strip():
                skips.append(
                    Skip(
                        RULE_REFLOW,
                        NOT_AFTER_BLANK,
                        line,
                        "the badge lines directly follow another line, so they are not a paragraph",
                    )
                )
            elif anchor is None:
                skips.append(
                    Skip(RULE_REFLOW, ANCHOR_NOT_UNIQUE, line, "the badge lines occur twice")
                )
            elif joined != anchor:
                cands.append(
                    Cand(
                        f"reflow-L{line}",
                        RULE_REFLOW,
                        Op(f"reflow-L{line}", REFLOW, anchor, joined, (f"readme:{line}",)),
                        line,
                    )
                )
        line = end + 1
    return cands, skips


# ------------------------------------------------------------------------------------ rule 3
def _link_targets(text: str) -> list[str]:
    """The link and image targets markdown reads in ``text`` (a code span holds none)."""
    found: list[str] = []
    for token in _MARKDOWN.parse(text):
        for child in token.children or []:
            if child.type == "link_open":
                found.append(str(child.attrGet("href")))
            elif child.type == "image":
                found.append(str(child.attrGet("src")))
    return found


def deletes(rd: Readme) -> tuple[list[Cand], list[Skip]]:
    ctx = rd.ctx
    contradicted = {
        f.value: f.id
        for f in ctx.facts.facts
        if f.kind == "link_target" and f.polarity == "CONTRADICTED"
    }
    cands: list[Cand] = []
    skips: list[Skip] = []
    for number in range(1, len(rd.raw) + 1):
        text = rd.body(number)
        if rd.in_fence(number) or not _LIST_ITEM_LINE.match(text):
            continue
        links = _MD_LINK.findall(text)
        targets = [(raw, _relative_target(raw)) for _label, raw in links]
        broken = [t for _raw, t in targets if t is not None and t and _absent(ctx, t)]
        if not broken:
            continue
        if sorted(unquote(raw) for _label, raw in links) != sorted(
            unquote(href) for href in _link_targets(text)
        ):
            skips.append(
                Skip(
                    RULE_DELETE,
                    TARGET_UNRESOLVABLE,
                    number,
                    "link-like text that markdown does not read as a link (a code span)",
                )
            )
            continue
        if any(t is None or not t or not _absent(ctx, t) for _raw, t in targets):
            skips.append(
                Skip(
                    RULE_DELETE,
                    MIXED_LINKS,
                    number,
                    "the item also holds a link that is external or present in the tree",
                )
            )
            continue
        if any(t.startswith("..") for t in broken):
            skips.append(
                Skip(
                    RULE_DELETE,
                    TARGET_UNRESOLVABLE,
                    number,
                    "a link climbs out of the repository root; its target cannot be judged",
                )
            )
            continue
        following = rd.body(number + 1) if number < len(rd.raw) else ""
        if following[:1] in {" ", "\t"} or (
            following.strip()
            and not _LIST_ITEM_LINE.match(following)
            and not following.lstrip().startswith(("#", "```", "~~~", "|", ">"))
        ):
            skips.append(
                Skip(RULE_DELETE, CONTINUATION_LINE, number, "a following line continues the item")
            )
            continue
        previous = rd.body(number - 1) if number > 1 else ""
        if not (_LIST_ITEM_LINE.match(previous) or _LIST_ITEM_LINE.match(following)):
            skips.append(
                Skip(
                    RULE_DELETE,
                    WOULD_EMPTY_LIST,
                    number,
                    "the item is the only one of its list, so deleting it would leave a bare "
                    "section",
                )
            )
            continue
        anchor = rd.anchor(number)
        if anchor is None:
            skips.append(Skip(RULE_DELETE, ANCHOR_NOT_UNIQUE, number, "the list item occurs twice"))
            continue
        evidence: list[str] = []
        for target in broken:
            ref = contradicted.get(target) or f"tree-absent:{target}"
            if ref not in evidence:
                evidence.append(ref)
        evidence.append(f"readme:{number}")
        cands.append(
            Cand(
                f"delete-L{number}",
                RULE_DELETE,
                Op(f"delete-L{number}", DELETE_LINE, anchor, "", tuple(evidence)),
                number,
            )
        )
    return cands, skips


# ------------------------------------------------------------------------------------ rule 5
def dependencies(rd: Readme, anchor_line: int) -> tuple[Section | None, list[Skip]]:
    deps: list[Fact] = [
        f
        for f in rd.ctx.facts.facts
        if f.kind == "dependency"
        and f.polarity == "SUPPORTED"
        and f.value.strip().lower() != "none"
        and not f.id.endswith(":none")
        and "`" not in f.value
    ]
    if not deps:
        return None, [
            Skip(
                RULE_DEPENDENCIES,
                NO_SUPPORTED_DEPENDENCIES,
                0,
                "the facts hold no SUPPORTED dependency (a declared 'none' is not a bullet)",
            )
        ]
    buckets: dict[str, dict[str, list[str]]] = {
        "Required Package Dependencies": {},
        "Optional Dependencies": {},
        "Development Dependencies": {},
    }
    for fact in deps:
        buckets[_bucket_of(fact.id)].setdefault(fact.value, []).append(fact.id)
    lines = ["## Dependencies", ""]
    evidence: list[str] = []
    for title, values in buckets.items():
        if not values:
            continue
        lines += [f"### {title}", ""]
        lines += [f"- `{value}`" for value in values]
        lines.append("")
        for ids in values.values():
            evidence += [i for i in ids if i not in evidence]
    evidence.append(f"readme:{anchor_line}")
    text = "\n".join(lines) + "\n"
    return Section(RULE_DEPENDENCIES, SECTION_DEPENDENCIES, text, anchor_line, tuple(evidence)), []


# ------------------------------------------------------------------------------------ rule 6
@dataclass(frozen=True)
class BulletList:
    first: int  # 1-based line of the first item
    items: tuple[tuple[int, str], ...]  # (line, item text)


def bullet_lists(text: str) -> list[BulletList]:
    """The top-level bullet lists of ``text`` outside fenced code, each item's first paragraph."""
    tokens = _MARKDOWN.parse(text)
    lists: list[BulletList] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type == "bullet_list_open" and token.level == 0 and token.map:
            items: list[tuple[int, str]] = []
            depth_index = index + 1
            while depth_index < len(tokens) and not (
                tokens[depth_index].type == "bullet_list_close" and tokens[depth_index].level == 0
            ):
                inner = tokens[depth_index]
                if inner.type == "list_item_open" and inner.level == 1 and inner.map:
                    for follow in tokens[depth_index + 1 : depth_index + 4]:
                        if follow.type == "inline":
                            items.append((inner.map[0] + 1, follow.content))
                            break
                depth_index += 1
            lists.append(BulletList(token.map[0] + 1, tuple(items)))
            index = depth_index
        index += 1
    return lists


def plain_text(text: str) -> str:
    """Item text without images, link syntax, code ticks and emphasis marks: the words stay."""
    text = _IMAGE.sub("", text)
    text = _MD_LINK.sub(lambda m: m.group(1), text)
    text = text.replace("`", "").replace("**", "").replace("__", "")
    return " ".join(text.split())


def shorten(item: str) -> str | None:
    """A bullet cut to a few of its own words: the whole bullet when it has at most five words,
    otherwise the longest prefix, cut at a delimiter (a comma, 'and', 'using', 'with', 'from',
    'in', a dash, a colon or a bracket), of two to five words. A leading article is dropped. The
    result is always a contiguous substring of the bullet."""
    text = plain_text(item).strip().rstrip(".;:,")
    if not text:
        return None
    candidates = [text] if len(text.split()) <= MAX_LABEL_WORDS else []
    for match in _CUTS.finditer(text):
        prefix = text[: match.start()].rstrip(" ,;:-" + _DASHES)
        if prefix.count("(") == prefix.count(")"):
            candidates.append(prefix)
    fitting = [c for c in candidates if 2 <= len(c.split()) <= MAX_LABEL_WORDS]
    if not fitting:
        fitting = [c for c in candidates if len(c.split()) == 1 and len(text.split()) == 1]
    if not fitting:
        return None
    label = max(fitting, key=lambda c: len(c.split()))
    stripped = _ARTICLE.sub("", label)
    if stripped and len(stripped.split()) >= 2:
        label = stripped
    label = label.strip()
    return label if label in text and _LABEL_OK.match(label) else None


_IN_COLUMN = frozenset({"load", "read", "open", "import", "input", "parse", "reading", "loading"})
_OUT_COLUMN = frozenset(
    {"save", "write", "export", "output", "writing", "saving", "convert", "render"}
)


def _h2_spans(rd: Readme, titles: dict[int, str]) -> dict[str, tuple[int, int]]:
    """final title key -> (heading line, last line before the next H2) of each live H2."""
    h2 = rd.h2()
    out: dict[str, tuple[int, int]] = {}
    for index, heading in enumerate(h2):
        end = h2[index + 1].line - 1 if index + 1 < len(h2) else len(rd.raw)
        out.setdefault(heading_key(titles.get(heading.line, heading.text)), (heading.line, end))
    return out


def capabilities(rd: Readme, titles: dict[int, str]) -> tuple[list[tuple[int, str]], str]:
    """``([(line, label)], problem)``: the capability labels of the README's own bullet list, the
    first list of at least three items under the Key Capabilities heading or, failing that, the
    first one before the Installation section."""
    order = _element_order()
    install = order[heading_key("Installation")]
    spans = _h2_spans(rd, titles)
    lists = [
        lst
        for lst in bullet_lists(rd.text)
        if len(lst.items) >= MIN_CAPABILITIES
        and not all(_MD_LINK.fullmatch(text.strip()) for _line, text in lst.items)
    ]
    chosen: BulletList | None = None
    capabilities_key = heading_key("Key Capabilities")
    if capabilities_key in spans:
        start, end = spans[capabilities_key]
        chosen = next((lst for lst in lists if start < lst.first <= end), None)
    if chosen is None:
        limit = len(rd.raw) + 1
        for heading in rd.h2():
            key = heading_key(titles.get(heading.line, heading.text))
            if order.get(key, -1) >= install:
                limit = heading.line
                break
        chosen = next((lst for lst in lists if lst.first < limit), None)
    if chosen is None:
        return [], NO_CAPABILITIES_LIST
    labels: list[tuple[int, str]] = []
    seen: set[str] = set()
    for line, text in chosen.items:
        label = shorten(text)
        if label is None or label.casefold() in seen:
            continue
        seen.add(label.casefold())
        labels.append((line, label))
        if len(labels) == MAX_GLANCE_CAPABILITIES:
            break
    return labels, ""


def _support(rd: Readme) -> str:
    """What a diagram word may be drawn from: the README and the values of SUPPORTED facts."""
    values = "\n".join(f.value for f in rd.ctx.facts.facts if f.polarity == "SUPPORTED")
    return rd.text + "\n" + values


def _format_label(extension: str, rd: Readme) -> str | None:
    word = extension.lstrip(".").upper()
    if not re.fullmatch(r"[A-Z0-9]{1,8}", word):
        return None
    with_file = f"{word} file"
    return word if unsupported_words(with_file, _support(rd)) else with_file


def formats_from_facts(rd: Readme) -> tuple[list[str], list[str], list[str]]:
    """``(inputs, outputs, fact ids)`` from SUPPORTED ``format:input.*`` / ``format:output.*``
    facts: the fact id says the direction (the extractors record it there), the value the
    extension."""
    inputs: list[str] = []
    outputs: list[str] = []
    ids: list[str] = []
    for fact in rd.ctx.facts.facts:
        if fact.kind != "format" or fact.polarity != "SUPPORTED":
            continue
        direction = fact.id.split(":", 1)[1].split(".", 1)[0]
        label = _format_label(fact.value, rd)
        if label is None or direction not in {"input", "output"}:
            continue
        target = inputs if direction == "input" else outputs
        if label not in target:
            target.append(label)
            ids.append(fact.id)
    return inputs, outputs, ids


def _tables(rd: Readme) -> list[tuple[int, list[list[str]]]]:
    """``(line, rows)`` of each table under a heading that names formats; row 0 is the header."""
    tokens = _MARKDOWN.parse(rd.text)
    found: list[tuple[int, list[list[str]]]] = []
    for index, token in enumerate(tokens):
        if token.type != "table_open" or not token.map:
            continue
        above = [h for h in rd.headings if h.line <= token.map[0] + 1]
        if not above or "format" not in heading_key(above[-1].text):
            continue
        rows: list[list[str]] = []
        for follow in tokens[index:]:
            if follow.type == "table_close":
                break
            if follow.type == "tr_open":
                rows.append([])
            elif follow.type == "inline" and rows:
                rows[-1].append(plain_text(follow.content))
        if len(rows) >= 2:
            found.append((token.map[0] + 1, rows))
    return found


def formats_from_readme(
    rd: Readme, bullets: Sequence[tuple[int, str]]
) -> tuple[list[str], list[str], list[str]]:
    """``(inputs, outputs, evidence)`` from the README's own formats table (under a heading with
    'format' in it, with load/save style columns) or, failing that, from the capability bullets
    that name a file extension in backticks and say read/write."""
    inputs: list[str] = []
    outputs: list[str] = []
    for line, rows in _tables(rd):
        head = [cell.casefold().split()[:1] for cell in rows[0]]
        in_columns = [i for i, c in enumerate(head) if c and c[0] in _IN_COLUMN]
        out_columns = [i for i, c in enumerate(head) if c and c[0] in _OUT_COLUMN]
        for row in rows[1:]:
            name = row[0] if row else ""
            if not name or not _LABEL_OK.match(name) or len(name.split()) > 3:
                continue
            shown = name if len(name.split()) > 1 else (_format_label(name, rd) or name)
            if _affirmative(row, in_columns) and shown not in inputs:
                inputs.append(shown)
            if _affirmative(row, out_columns) and shown not in outputs:
                outputs.append(shown)
        if inputs or outputs:
            return inputs, outputs, [f"readme:{line}"]
    evidence: list[str] = []
    for line, text in bullets:
        words = {w.strip(",.").casefold() for w in text.split()}
        for extension in _DOT_EXTENSION.findall(text):
            label = _format_label(extension, rd)
            if label is None:
                continue
            if words & _IN_VERBS and label not in inputs:
                inputs.append(label)
            if words & _OUT_VERBS and label not in outputs:
                outputs.append(label)
            if f"readme:{line}" not in evidence:
                evidence.append(f"readme:{line}")
    return inputs, outputs, evidence


def _affirmative(row: Sequence[str], columns: Sequence[int]) -> bool:
    return any(i < len(row) and row[i].casefold().startswith(_YES) for i in columns)


def product_name(rd: Readme) -> tuple[str, int]:
    for heading in rd.headings:
        if heading.level == 1:
            name = plain_text(heading.text)
            return (name if _LABEL_OK.match(name) else ""), heading.line
    return "", 0


def _safe(labels: Sequence[str], count: int) -> list[str]:
    return [label for label in labels if title_failure(label, count) is None]


def glance(
    rd: Readme, titles: dict[int, str], anchor_line: int
) -> tuple[Section | None, Skip | None]:
    """The At a Glance section for ``rd`` going before line ``anchor_line``, or why not."""

    def underivable(reason: str, detail: str) -> tuple[None, Skip]:
        return None, Skip(RULE_GLANCE, GLANCE_UNDERIVABLE, 0, f"{reason}: {detail}")

    name, h1_line = product_name(rd)
    if not name:
        return underivable(NO_PRODUCT, "the README has no usable H1")
    bullets, problem = capabilities(rd, titles)
    if problem:
        return underivable(
            problem,
            "no bullet list of three or more items under Key Capabilities or before Installation",
        )
    inputs, outputs, ids = formats_from_facts(rd)
    evidence = [f"readme:{bullets[0][0]}", f"readme:{h1_line}", *ids]
    if not inputs or not outputs:
        read_in, read_out, more = formats_from_readme(rd, bullets)
        inputs, outputs = inputs or read_in, outputs or read_out
        evidence += more
    labels = [label for _line, label in bullets]
    # a label the contract cannot draw geometry-safe is dropped, never rewritten
    for _ in range(MAX_GLANCE_CAPABILITIES):
        kept = _safe(labels, len(labels))
        if kept == labels:
            break
        labels = kept
    if len(labels) < MIN_CAPABILITIES:
        return underivable(FEWER_THAN_THREE_CAPABILITIES, f"{len(labels)} drawable label(s)")
    if title_failure(name, len(labels)) is not None:
        return underivable(DIAGRAM_CONTRACT, f"the product name {name!r} cannot be drawn")
    inputs = _safe(inputs, len(labels))[:MAX_FORMATS]
    outputs = _safe(outputs, len(labels))[:MAX_FORMATS]
    if not inputs:
        return underivable(NO_STARTING_POINT, "no SUPPORTED input format and no README table")
    if not outputs:
        return underivable(NO_OUTPUT, "no SUPPORTED output format and no README table")
    shape = Glance(name, tuple(inputs), balanced_columns(tuple(labels)), tuple(outputs))
    body = build_body(shape)
    problems = [d.code for d in lint_source(body).defects]
    problems += [f.message for f in topology_failures(body, True)]
    problems += unsupported_words(" ".join(shape.labels), _support(rd))
    if problems:
        return underivable(DIAGRAM_CONTRACT, "; ".join(problems)[:200])
    text = "## At a Glance\n\n" + "\n".join(build_block(shape)) + "\n\n"
    section = Section(
        RULE_GLANCE, SECTION_GLANCE, text, anchor_line, tuple(dict.fromkeys(evidence))
    )
    return section, None


# ------------------------------------------------------------------------------------ rule 4
def navigation(
    headings: Sequence[Heading], anchor_line: int, omit: Sequence[str] = ()
) -> Section | None:
    """A Navigation section listing the H2 sections of ``headings`` (those of the corrected
    README), each linked by the slug GitHub gives it; ``omit`` names entries left out."""
    by_heading = {id(heading): slug for slug, heading in slug_map(list(headings)).items()}
    items = [
        f"- [{heading.text}](#{by_heading[id(heading)]})"
        for heading in headings
        if heading_key(heading.text) not in NAVIGATION_NAMES
        and heading.text not in omit
        and not re.search(r"[\[\]|]", heading.text)
    ]
    if len(items) < 2:
        return None
    text = "## Navigation\n\n" + "\n".join(items) + "\n\n"
    return Section(
        RULE_NAVIGATION, SECTION_NAVIGATION, text, anchor_line, (f"readme:{anchor_line}",)
    )


# --------------------------------------------------------------------------------- the proposer
class _Builder:
    """Collects the candidates and validates them against ``check_ops`` until none is refused."""

    def __init__(self, ctx: Context) -> None:
        self.ctx = ctx
        self.rd = Readme(ctx)
        self.skips: list[Skip] = []
        self.original = ctx.readme.encode("utf-8")

    def introduced(self, ops: Sequence[Op]) -> list[dict[str, Any]]:
        """The checks of the acceptance judge that ``ops`` would make fail more often than the live
        README does (what ``correct-readme --ops`` refuses a bundle for), empty when none."""
        if not ops:
            return []
        result = CorrectionResult(self.ctx.readme, apply_ops(self.ctx.readme, ops))
        delta = validation_delta(self.ctx, result, self.original)
        return list(delta["introduced"])

    def introduced_count(self, ops: Sequence[Op]) -> int:
        return sum(int(item["extra"]) for item in self.introduced(ops))

    # ---- rules 1 to 3
    def _drop(self, cands: list[Cand], refusals: Sequence[Refusal]) -> tuple[list[Cand], bool]:
        """``cands`` without the ones the refusals name (by op id, or, for a refusal about a
        heading link, the retitle that changed that heading's slug)."""
        dropped: dict[str, Refusal] = {}
        by_id = {c.op.id: c for c in cands}
        for refusal in refusals:
            if refusal.op in by_id:
                dropped.setdefault(refusal.op, refusal)
                continue
            slug = re.search(r"#(\S+)", refusal.message)
            for cand in cands:
                if cand.rule != RULE_RETITLE or not slug:
                    continue
                old = github_slug(cand.op.anchor.lstrip("# ").strip())
                new = github_slug(cand.op.replacement.lstrip("# ").strip())
                if slug.group(1) in {old, new}:
                    dropped.setdefault(cand.op.id, refusal)
        for op_id, refusal in dropped.items():
            cand = by_id[op_id]
            self.skips.append(
                Skip(cand.rule, REFUSED_BY_CHECK, cand.line, refusal.message[:200], refusal.code)
            )
        kept = [c for c in cands if c.op.id not in dropped]
        kept += [f for op_id in dropped if (f := by_id[op_id].fallback) is not None]
        return kept, bool(dropped)

    def validated(self, cands: list[Cand]) -> list[Cand]:
        """``cands`` with every candidate ``check_ops`` refuses removed, until none is refused."""
        for _ in range(len(cands) + 2):
            if not cands:
                return []
            refusals = check_ops(self.ctx, [c.op for c in cands])
            if not refusals:
                return self._without_failures(cands)
            cands, progress = self._drop(cands, refusals)
            if not progress:
                break
        self.skips.append(
            Skip(RULE_ALL, REFUSED_BY_CHECK, 0, "the list is refused as a whole; nothing proposed")
        )
        return []

    def _without_failures(self, cands: list[Cand]) -> list[Cand]:
        """``cands`` less the candidates whose removal stops the acceptance judge failing more."""
        for _ in range(len(cands) + 1):
            introduced = self.introduced([c.op for c in cands])
            if not introduced:
                return cands
            total = sum(int(item["extra"]) for item in introduced)
            detail = "; ".join(f"{i['check']}: {', '.join(i['details'])}"[:120] for i in introduced)
            for cand in cands:
                rest = [c for c in cands if c is not cand]
                if self.introduced_count([c.op for c in rest]) < total:
                    self.skips.append(Skip(cand.rule, INTRODUCES_FAILURE, cand.line, detail[:200]))
                    cands = rest
                    break
            else:
                break
        self._skip(RULE_ALL, INTRODUCES_FAILURE, "no single operation accounts for the new failure")
        return []

    # ---- rules 4 to 6
    def merged(self, sections: Sequence[Section]) -> list[Op]:
        """One INSERT_BEFORE per anchor heading, its sections in the standard's order."""
        order = {SECTION_NAVIGATION: 0, SECTION_GLANCE: 1, SECTION_DEPENDENCIES: 2}
        by_line: dict[int, list[Section]] = {}
        for section in sections:
            by_line.setdefault(section.anchor_line, []).append(section)
        ops: list[Op] = []
        for line, group in sorted(by_line.items()):
            anchor = self.rd.unique_anchor(line)
            if anchor is None:
                self.skips += [
                    Skip(
                        s.rule,
                        ANCHOR_NOT_UNIQUE,
                        line,
                        "the heading the section goes before occurs more than once",
                    )
                    for s in group
                ]
                continue
            group.sort(key=lambda s: order[s.title])
            evidence = tuple(dict.fromkeys(e for s in group for e in s.evidence))
            text = "".join(s.text for s in group) + anchor
            ops.append(Op(f"insert-L{line}", INSERT_BEFORE, anchor, text, evidence))
        return ops

    def keep_valid(self, base: Sequence[Cand], sections: Sequence[Section]) -> list[Section]:
        """The sections that pass ``check_ops`` one at a time beside ``base``."""
        kept: list[Section] = []
        base_ops = [c.op for c in base]
        floor = self.introduced_count(base_ops)
        for section in sections:
            ops = self.merged([section])
            if not ops:
                continue
            refusals = check_ops(self.ctx, [*base_ops, *ops])
            mine = [r for r in refusals if r.op == ops[0].id]
            if not mine:
                introduced = self.introduced([*base_ops, *ops])
                if sum(int(item["extra"]) for item in introduced) <= floor:
                    kept.append(section)
                    continue
                detail = "; ".join(f"{i['check']}: {', '.join(i['details'])}" for i in introduced)
                self._skip(section.rule, INTRODUCES_FAILURE, detail[:200], section.anchor_line)
                continue
            self.skips.append(
                Skip(
                    section.rule,
                    REFUSED_BY_CHECK,
                    section.anchor_line,
                    "; ".join(r.message for r in mine)[:200],
                    mine[0].code,
                )
            )
        return kept

    def sections(self, base: Sequence[Cand], titles: dict[int, str]) -> list[Section]:
        rd, ctx = self.rd, self.ctx
        h2 = rd.h2()
        if not h2:
            self.skips.append(
                Skip(RULE_NAVIGATION, NO_PLACE, 0, "the README has no H2 heading to insert before")
            )
            return []
        keys = [heading_key(titles.get(h.line, h.text)) for h in h2]
        every = {heading_key(titles.get(h.line, h.text)) for h in rd.headings if h.level >= 2}
        order = _element_order()
        first = h2[0].line
        chosen: list[Section] = []
        # -- Dependencies: after the last section the standard orders before it, before the next
        # one it orders after it
        deps_at = order[heading_key("Dependencies")]
        before = [i for i, k in enumerate(keys) if order.get(k, 99) < deps_at]
        deps_line = next(
            (
                h2[i].line
                for i in range(before[-1] + 1 if before else 0, len(h2))
                if order.get(keys[i], -1) > deps_at
            ),
            0,
        )
        if every & DEPENDENCY_NAMES:
            self._skip(RULE_DEPENDENCIES, SECTION_PRESENT, "the README has a dependencies section")
        elif not deps_line:
            self._skip(RULE_DEPENDENCIES, NO_PLACE, "no section ordered after Dependencies")
        else:
            section, skipped = dependencies(rd, deps_line)
            self.skips += skipped
            if section is not None:
                chosen.append(section)
        # -- At a Glance: directly after Navigation, whether the README has one or gets one
        nav_exists = any(k in NAVIGATION_NAMES for k in keys)
        glance_line = first
        if nav_exists:
            position = next(i for i, k in enumerate(keys) if k in NAVIGATION_NAMES)
            glance_line = h2[position + 1].line if position + 1 < len(h2) else 0
        if every & GLANCE_NAMES:
            self._skip(RULE_GLANCE, SECTION_PRESENT, "the README has an At a Glance section")
        elif not glance_line:
            self._skip(RULE_GLANCE, NO_PLACE, "no section follows the Navigation section")
        else:
            drawn, skip = glance(rd, titles, glance_line)
            if skip is not None:
                self.skips.append(skip)
            if drawn is not None:
                chosen.append(drawn)
        chosen = self.keep_valid(base, chosen)
        # -- Navigation, from the H2 headings of the README as corrected so far
        if nav_exists:
            self._skip(RULE_NAVIGATION, SECTION_PRESENT, "the README has a navigation section")
            return chosen
        interim = apply_ops(ctx.readme, [c.op for c in base] + self.merged(chosen))
        headings = [h for h in parse_headings(interim) if h.level == 2]
        if len(headings) < NAVIGATION_MIN_SECTIONS:
            self._skip(
                RULE_NAVIGATION,
                TOO_FEW_SECTIONS,
                f"the corrected README has {len(headings)} H2 section(s); at least "
                f"{NAVIGATION_MIN_SECTIONS} are needed",
            )
            return chosen
        nav = self._navigation(base, chosen, headings, first)
        return [*chosen, nav] if nav is not None else chosen

    def _navigation(
        self, base: Sequence[Cand], chosen: Sequence[Section], headings: list[Heading], first: int
    ) -> Section | None:
        """The Navigation section for ``headings`` that ``check_ops`` accepts and the acceptance
        judge does not fail on; an entry whose text makes the judge fail is left out of the list
        (up to three), and the section is dropped when that does not help."""
        base_ops = [c.op for c in base]
        floor = self.introduced_count([*base_ops, *self.merged(chosen)])
        omitted: list[str] = []
        for _ in range(MAX_OMITTED_ENTRIES + 1):
            nav = navigation(headings, first, omitted)
            if nav is None:
                self._skip(RULE_NAVIGATION, TOO_FEW_SECTIONS, "fewer than two linkable sections")
                return None
            ops = [*base_ops, *self.merged([*chosen, nav])]
            refusals = check_ops(self.ctx, ops)
            if refusals:
                self.skips.append(
                    Skip(
                        RULE_NAVIGATION,
                        REFUSED_BY_CHECK,
                        first,
                        refusals[0].message[:200],
                        refusals[0].code,
                    )
                )
                return None
            total = self.introduced_count(ops)
            if total <= floor:
                for title in omitted:
                    self._skip(
                        RULE_NAVIGATION,
                        INTRODUCES_FAILURE,
                        f"the entry {title!r} is left out of the navigation: listing it makes "
                        "the acceptance judge fail",
                    )
                return nav
            for heading in headings:
                if heading.text in omitted or heading_key(heading.text) in NAVIGATION_NAMES:
                    continue
                trial = navigation(headings, first, [*omitted, heading.text])
                if trial is None:
                    continue
                trial_ops = [*base_ops, *self.merged([*chosen, trial])]
                if not check_ops(self.ctx, trial_ops) and self.introduced_count(trial_ops) < total:
                    omitted.append(heading.text)
                    break
            else:
                break
        self._skip(RULE_NAVIGATION, INTRODUCES_FAILURE, "the navigation fails the acceptance judge")
        return None

    def _skip(self, rule: str, code: str, detail: str, line: int = 0) -> None:
        self.skips.append(Skip(rule, code, line, detail))


def _new_heading(cand: Cand) -> str:
    match = _HEADING_LINE.match(cand.op.replacement.rstrip("\r\n"))
    return match.group(2).strip() if match else ""


def propose(ctx: Context) -> Proposal:
    """The operations list for ``ctx`` and the reasons the other candidates are not in it."""
    builder = _Builder(ctx)
    rd = builder.rd
    base: list[Cand] = []
    for rule in (retitles, reflows, deletes):
        found, skipped = rule(rd)
        base += found
        builder.skips += skipped
    base = builder.validated(base)
    titles = {c.line: _new_heading(c) for c in base if c.rule == RULE_RETITLE}
    sections: list[Section] = []
    if rd.crlf:
        builder._skip(RULE_NAVIGATION, CRLF_README, "the README uses CRLF; no section is inserted")
    else:
        sections = builder.sections(base, titles)
    inserts = builder.merged(sections)
    ops = [c.op for c in base] + inserts
    if ops and check_ops(ctx, ops):  # every part passed beside the base; never ship a refused list
        builder._skip(RULE_ALL, REFUSED_BY_CHECK, "the whole list is refused; nothing proposed")
        ops, base, inserts = [], [], []
    by_id = {c.op.id: c for c in base}
    placed: list[Proposed] = []
    for op in ops:
        cand = by_id.get(op.id)
        if cand is not None:
            placed.append(Proposed(op, cand.rule, cand.line))
            continue
        line = int(op.id.rsplit("L", 1)[1])
        names = tuple(s.title for s in sections if s.anchor_line == line)
        placed.append(Proposed(op, "INSERT", line, names))
    placed.sort(key=lambda p: (p.line, p.op.kind != INSERT_BEFORE, p.op.id))
    proposal = Proposal(ctx.facts.repository, ctx.facts.source_revision, placed)
    proposal.skipped = sorted(builder.skips, key=lambda s: (s.line, s.rule, s.code))
    proposal.outcome = PROPOSED if placed else NO_CHANGE
    return proposal


# ---------------------------------------------------------------------------------- the driver
def write_proposal(proposal: Proposal, ops_path: Path, report_path: Path) -> None:
    """Write the operations file (only when there is an operation) and the report."""
    report = proposal.report()
    report["ops_file"] = ops_path.name if proposal.ops else None
    if proposal.ops:
        ops_path.parent.mkdir(parents=True, exist_ok=True)
        ops_path.write_text(
            json.dumps(ops_to_json(proposal.ops), indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def produce_proposal(
    entry: RegistryEntry,
    *,
    clone_directory: Path,
    facts_path: Path,
    token: str | None = None,
) -> Proposal:
    """The same read as ``correct-readme --ops`` (a pinned read-only clone, the snapshot, facts for
    exactly that revision), then ``propose``; nothing is written."""
    clone = pinned_read_only_clone(entry.clone_url, clone_directory, token=token)
    snapshot = capture_snapshot(entry.repository, clone)
    if snapshot.readme_path != README_PATH:
        reason = (
            "the repository has no README"
            if snapshot.readme_path is None
            else f"the README is {snapshot.readme_path!r}; a correction patches {README_PATH} only"
        )
        return Proposal(entry.repository, clone.revision, outcome=NO_LIVE_README, reason=reason)
    original = (clone.path / snapshot.readme_path).read_bytes()
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorrectionError(f"{entry.repository}'s README is not UTF-8: {exc}") from exc
    facts = read_facts(facts_path)
    if facts.repository != entry.repository or facts.source_revision != clone.revision:
        raise CorrectionError(
            f"facts are for {facts.repository} @ {facts.source_revision}, but the registry head "
            f"is {entry.repository} @ {clone.revision}; extract facts at the head and retry"
        )
    tree = tuple(list_tree_paths(clone.path))
    return propose(Context(entry, facts, text, tree, snapshot.readme_path))
