"""Cut a README into the atoms the idempotence metrics compare, each with its position.

An atom is the smallest unit a maintainer can recognise as "still there" or "gone": a prose
sentence, a list item, a table row, a fenced code block, a heading, a link target, an image
target. The cut is made with markdown-it-py, the parser ``components/readme/reconciliation``
already uses, so a fenced block, a table cell and an HTML block are never mistaken for prose.

Two comparison keys exist, on purpose. ``norm`` folds case, emphasis, backticks, link syntax and
whitespace, so "verbatim" ignores presentation and is a generous ceiling for byte retention.
``toks`` keeps the content words, so "reworded" asks whether most of the words survive in one
candidate atom. The thresholds live in ``retention.py``; the cut lives here and is shared by the
retention, introduced-text and edit-script measures so they cannot disagree about what an atom is.

Pure functions of the text: no network, no model, no clock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from markdown_it import MarkdownIt

PROSE_KINDS = ("sentence", "item")
ALL_KINDS = ("sentence", "item", "row", "code", "heading", "link", "image")

_MD = MarkdownIt("commonmark").enable("table")
_STOP_WORDS = (
    "the and for with that this from into are not but its can has have will your you our their "
    "was were any all use uses used than yet via also each other such when where which while "
    "only more most some then them they there these those able over under both just like"
)
_STOP = frozenset(_STOP_WORDS.split())
#: Typographic quotes folded to the plain ones (U+2018, U+2019, U+201C, U+201D).
_QUOTES = {0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[\"(])")
_WORD = re.compile(r"[a-z0-9][a-z0-9_.+#-]{1,}")
_HTML_URL = re.compile(r"""(?:href|src)=["']([^"']+)["']""")
_TAG = re.compile(r"<[^>]+>")
_FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*([^\s`]*)")

#: A prose sentence of fewer words than this is a fragment, not a claim.
MIN_SENTENCE_WORDS = 4
#: A list item shorter than this is a label, not a claim. It is the sentence floor, so the figures
#: compare with the second first-principles analysis, whose prose atoms were all 4 words or more.
MIN_ITEM_WORDS = 4


@dataclass(frozen=True)
class Atom:
    kind: str
    text: str  # as written (inline markup folded to its words), for display
    key: str  # ``norm(text)``, for equality
    line: int  # 1-based line of the block that holds it
    section: str  # nearest H2 (else H1) heading above it, "" before any
    info: str = ""  # code: language; heading: level; link and image: the target as written


@dataclass
class Atoms:
    """Every atom of one README, by kind, in document order."""

    sentences: list[Atom] = field(default_factory=list)
    items: list[Atom] = field(default_factory=list)
    rows: list[Atom] = field(default_factory=list)
    code: list[Atom] = field(default_factory=list)
    headings: list[Atom] = field(default_factory=list)
    links: list[Atom] = field(default_factory=list)  # distinct targets, first position
    images: list[Atom] = field(default_factory=list)  # distinct targets, first position

    def of(self, kind: str) -> list[Atom]:
        return {
            "sentence": self.sentences,
            "item": self.items,
            "row": self.rows,
            "code": self.code,
            "heading": self.headings,
            "link": self.links,
            "image": self.images,
        }[kind]

    def prose(self) -> list[Atom]:
        return [*self.sentences, *self.items]


def norm(text: str) -> str:
    """The comparison form: case, emphasis, backticks, link syntax, tags and spacing folded."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r" \1 ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = _TAG.sub(" ", text)
    text = text.replace("`", "").replace("*", "").replace("_", " ")
    text = text.translate(_QUOTES)
    return re.sub(r"\s+", " ", text).strip().lower().rstrip(".:;")


def toks(text: str) -> frozenset[str]:
    """The content words of ``text`` (stop words and one-letter tokens dropped)."""
    return frozenset(t for t in _WORD.findall(norm(text)) if t not in _STOP)


def norm_url(url: str) -> str:
    url = re.sub(r"^https?://(www\.)?", "", url.strip()).rstrip("/")
    return re.sub(r"^\./", "", url).lower()


def sentences(text: str) -> list[str]:
    return [part for part in _SENTENCE_SPLIT.split(text.strip()) if part.strip()]


def _inline_text(token: object) -> str:
    out: list[str] = []
    for child in getattr(token, "children", None) or []:
        if child.type in ("text", "code_inline"):
            out.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            out.append(" ")
        elif child.type == "image":
            out.append(child.content or "")
    return "".join(out)


def _line_of(lines: list[str], start: int, end: int, needle: str) -> int:
    """The 1-based line in ``[start, end)`` that holds ``needle``, else ``start + 1``."""
    for number in range(max(start, 0), min(end, len(lines))):
        if needle in lines[number]:
            return number + 1
    return start + 1


def atomise(text: str) -> Atoms:
    """One walk over the markdown-it tokens; the order of the walk is the order of the document."""
    atoms = Atoms()
    lines = text.splitlines()
    tokens = _MD.parse(text)
    section = ""
    in_item = 0
    row: list[str] = []
    row_line = 0
    seen_links: set[str] = set()
    seen_images: set[str] = set()

    def add_link(url: str, line: int, image: bool) -> None:
        if not url or url.startswith("#"):
            return
        key = norm_url(url)
        seen, bucket = (seen_images, atoms.images) if image else (seen_links, atoms.links)
        if key not in seen:
            seen.add(key)
            bucket.append(Atom("image" if image else "link", url, key, line, section, url))

    for index, token in enumerate(tokens):
        start, end = (token.map[0], token.map[1]) if token.map else (0, 0)
        if token.type == "list_item_open":
            in_item += 1
        elif token.type == "list_item_close":
            in_item = max(0, in_item - 1)
        elif token.type == "heading_open":
            level = int(token.tag[1])
            heading = _inline_text(tokens[index + 1])
            atoms.headings.append(
                Atom("heading", heading, norm(heading), start + 1, section, str(level))
            )
            if level <= 2:
                section = heading.strip()
        elif token.type == "inline":
            previous = tokens[index - 1].type if index else ""
            for child in token.children or []:
                if child.type == "link_open":
                    href = str(dict(child.attrs).get("href", ""))
                    add_link(href, _line_of(lines, start, end, href), False)
                elif child.type == "image":
                    src = str(dict(child.attrs).get("src", ""))
                    add_link(src, _line_of(lines, start, end, src), True)
            if previous == "heading_open":
                continue
            body = _inline_text(token)
            if previous in ("th_open", "td_open"):
                if not row:
                    row_line = start + 1
                row.append(body)
                continue
            if in_item:
                if len(body.split()) >= MIN_ITEM_WORDS:
                    atoms.items.append(Atom("item", body, norm(body), start + 1, section))
                continue
            for sentence in sentences(body):
                if len(sentence.split()) >= MIN_SENTENCE_WORDS:
                    atoms.sentences.append(
                        Atom("sentence", sentence, norm(sentence), start + 1, section)
                    )
        elif token.type == "tr_close":
            joined = " | ".join(row)
            if norm(joined).replace("|", "").strip():
                atoms.rows.append(Atom("row", joined, norm(joined), row_line, section))
            row = []
        elif token.type in ("fence", "code_block"):
            info = (token.info or "").strip().split(" ")[0].lower()
            body = token.content.rstrip("\n")
            atoms.code.append(
                Atom("code", body, re.sub(r"\s+", " ", body).strip(), start + 1, section, info)
            )
        elif token.type == "html_block":
            for match in _HTML_URL.finditer(token.content):
                url = match.group(1)
                add_link(
                    url, _line_of(lines, start, end, url), bool(re.search(r"src=", match.group(0)))
                )
            plain = re.sub(r"\s+", " ", _TAG.sub(" ", token.content)).strip()
            for sentence in sentences(plain):
                if len(sentence.split()) >= MIN_SENTENCE_WORDS:
                    atoms.sentences.append(
                        Atom("sentence", sentence, norm(sentence), start + 1, section)
                    )
    return atoms


def mermaid_line_numbers(text: str) -> set[int]:
    """The 1-based lines inside a ```mermaid fence (the diagram body; the fence markers are not)."""
    inside = False
    marker = ""
    out: set[int] = set()
    for number, line in enumerate(text.splitlines(), start=1):
        match = _FENCE_OPEN.match(line)
        if not inside:
            if match and match.group(2).lower() == "mermaid":
                inside, marker = True, match.group(1)[0] * len(match.group(1))
            continue
        if match and match.group(1).startswith(marker) and not match.group(2):
            inside = False
            continue
        out.add(number)
    return out
