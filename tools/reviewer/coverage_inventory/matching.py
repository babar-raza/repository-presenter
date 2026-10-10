# Part of TC-COV-01 (plans: reseal-and-refresh). Owner/reviewer measurement tooling (tools/README.md):
# read-only, no provider call, writes only the files it is told to. Not imported by src/.
"""Matching helpers: does a clone information unit appear in a body of text (a sealed README, the
extracted facts, the live upstream README)?

Matching is deliberately approximate and always reports *how* it matched, so a reader can discount
weak methods. Methods, strongest first:

  pattern          a regular expression the unit supplied (target frameworks, versions)
  path             the unit's repository path appears verbatim
  basename         the unit's file name appears
  name             the unit's identifier (CLI name, command) appears as a whole word
  command          the tool and verb of a build/test command appear in order on one line
  values           every value of a matrix axis appears
  heading          a heading with a normalised, known name exists (community files, changelog)
  heading+overlap  a README section whose normalised heading matches AND whose words overlap
  content_overlap  >= OVERLAP_PRESENT of the unit's distinctive words appear in the target
  dir_pointer      only the containing directory (docs/, examples/) is pointed at; weakest
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

OVERLAP_PRESENT = 0.6  # distinctive-word containment that counts as "carried"
OVERLAP_WITH_HEADING = 0.4  # lower bar when the section heading also matches
MIN_BODY_TOKENS = 3  # fewer distinctive words than this and a unit has no content to carry

_STOP = frozenset(
    """a an and are as at be but by can for from has have if in into is it its not of on or our so
    that the their then there these this to was we were will with you your use used using also may
    more most such than when which who why how any all each other some new""".split()
)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}|\d+(?:\.\d+)+")
_MD_NOISE = re.compile(r"[`*_~>#|\[\]()!]+")
_BADGE_LINE = re.compile(r"^\s*(\[!\[|!\[)")


def norm_path(p: str) -> str:
    return p.replace("\\", "/").strip().lstrip("./").lower()


def norm_heading(h: str) -> str:
    """Heading text reduced to its comparable core: no #, no markdown, no emoji, lower case."""
    h = unicodedata.normalize("NFKC", h).strip().strip("#").strip()
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)  # [text](url) -> text
    h = _MD_NOISE.sub(" ", h)
    h = "".join(c for c in h if c.isalnum() or c in " '&+.-")  # drops emoji and symbols
    return re.sub(r"\s+", " ", h).strip().lower()


def tokens(text: str) -> frozenset[str]:
    """Distinctive lower-case words (identifiers, words >= 3 chars, version numbers)."""
    out = set()
    for w in _WORD.findall(unicodedata.normalize("NFKC", text)):
        w = w.lower()
        if w not in _STOP:
            out.add(w)
    return frozenset(out)


def overlap(unit_tokens: frozenset[str], target_tokens: frozenset[str]) -> float:
    """Fraction of the unit's distinctive words found in the target (containment, not Jaccard:
    a section reorganised into a larger document still counts as carried)."""
    if len(unit_tokens) < MIN_BODY_TOKENS:
        return 0.0
    return len(unit_tokens & target_tokens) / len(unit_tokens)


@dataclass
class Corpus:
    """One body of text to search: a sealed README, the extracted facts, or the live README."""

    name: str
    raw: str
    chunked: bool = False  # score overlap against the best section (or pair of adjacent sections), not the whole text
    lower: str = field(init=False)
    toks: frozenset[str] = field(init=False)
    headings: frozenset[str] = field(init=False)
    code: str = field(init=False)  # fenced blocks and inline code spans only, lower case
    chunks: list = field(init=False)

    def __post_init__(self) -> None:
        self.lower = unicodedata.normalize("NFKC", self.raw).replace("\\", "/").lower()
        self.toks = tokens(self.raw)
        spans = re.findall(r"(?:```|~~~)[^\n]*\n(.*?)(?:```|~~~)", self.lower, re.S)
        spans += re.findall(r"`([^`\n]+)`", self.lower)
        self.code = "\n".join(spans)
        self.headings = frozenset(
            norm_heading(m.group(0)) for m in re.finditer(r"^#{1,6}\s+.+$", self.raw, re.M)
        )
        secs = [tokens(h + " " + b) for h, b in split_sections(self.raw)]
        self.chunks = secs + [a | b for a, b in zip(secs, secs[1:])]

    def best_overlap(self, unit_tokens: frozenset[str]) -> float:
        if not self.chunked or not self.chunks:
            return overlap(unit_tokens, self.toks)
        return max(overlap(unit_tokens, c) for c in self.chunks)

    def has_text(self, needle: str) -> bool:
        return bool(needle) and needle.lower() in self.lower

    def has_word(self, word: str) -> bool:
        if not word:
            return False
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(word.lower())}(?![A-Za-z0-9_])", self.lower) is not None

    def has_path(self, path: str) -> bool:
        p = norm_path(path)
        return bool(p) and re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(p)}(?![A-Za-z0-9_])", self.lower) is not None

    def has_regex(self, pattern: str) -> bool:
        return re.search(pattern, self.lower, re.I) is not None

    def has_cli(self, name: str) -> bool:
        """``name`` is used as a command inside code: it starts a code line (after a ``$`` prompt) or
        a code span. A package of the same name (``pip install aspose-font``) is not a CLI."""
        if not name:
            return False
        n = re.escape(name.lower())
        for m in re.finditer(rf"(?<![A-Za-z0-9_./-]){n}(?![A-Za-z0-9_.-])", self.code):
            start = self.code.rfind(chr(10), 0, m.start()) + 1
            before = self.code[start : m.start()]
            if re.search(r"\b(install|add|require|pip|npm|import|from|package)\b", before):
                continue
            if re.fullmatch(r"\s*(?:[$>]\s*)?(?:\./)?", before):
                return True
        return False

    def has_command(self, words: list[str]) -> bool:
        """The words appear in order on one line (``mvn -B -q verify`` carries ``mvn verify``)."""
        if not words:
            return False
        pat = r"(?<![A-Za-z0-9_])" + r"[^\n]*?(?<![A-Za-z0-9_-])".join(re.escape(w.lower()) for w in words)
        return re.search(pat + r"(?![A-Za-z0-9_])", self.lower) is not None


@dataclass
class Unit:
    """One piece of clone information. ``unit_type`` is the gap-table column; the rest drives matching."""

    unit_type: str
    name: str  # stable identifier shown in the missing list
    path: str = ""  # repository path, when the unit is a file or directory
    detail: str = ""  # human note: size, headings, values
    size: int = 0
    patterns: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)  # whole-word identifiers
    command: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)  # every one must appear (matrix axes)
    heading_keys: list[str] = field(default_factory=list)  # normalised headings that carry this unit
    body_tokens: frozenset[str] = frozenset()
    pointer_dirs: list[str] = field(default_factory=list)
    heading: str = ""  # readme_unit: this section's own normalised heading
    use_basename: bool = True


# Unit types that are a file in the repository, so its path or file name is a valid way to find it.
FILE_TYPES = frozenset({"doc_page", "root_doc", "changelog", "contributing", "security_policy", "code_of_conduct",
                        "license_notice", "example_file"})


def find_hit(unit: Unit, corpus: Corpus) -> tuple[str, float] | None:
    """The strongest way ``unit`` appears in ``corpus``: ``(method, score)`` or None."""
    for pat in unit.patterns:
        if corpus.has_regex(pat):
            return "pattern", 1.0
    if unit.path and unit.unit_type in FILE_TYPES and "." in unit.path.rsplit("/", 1)[-1]:
        if corpus.has_path(unit.path):
            return "path", 1.0
        base = unit.path.replace("\\", "/").rsplit("/", 1)[-1]
        if unit.use_basename and corpus.has_path(base):
            return "basename", 1.0
    for n in unit.names:
        if (corpus.has_cli(n) if unit.unit_type == "cli_entry" else corpus.has_word(n)):
            return "name", 1.0
    if unit.command and corpus.has_command(unit.command):
        return "command", 1.0
    if unit.values:
        present = [any(corpus.has_word(alt) or corpus.has_text(alt) for alt in v.split("|")) for v in unit.values]
        if all(present):
            return "values", 1.0
        numeric = all(re.fullmatch(r"[0-9][0-9.]*", v) for v in unit.values)
        if numeric and len(unit.values) > 2 and present[0] and present[-1]:
            return "values_range", 1.0  # first and last stated: a range such as 3.10-3.13
    score = corpus.best_overlap(unit.body_tokens)
    heading_match = bool(unit.heading) and unit.heading in corpus.headings
    if unit.heading_keys and any(k in corpus.headings for k in unit.heading_keys):
        return "heading", score
    if heading_match and score >= OVERLAP_WITH_HEADING:
        return "heading+overlap", score
    if score >= OVERLAP_PRESENT:
        return "content_overlap", score
    for d in unit.pointer_dirs:
        if corpus.has_path(d.rstrip("/") + "/"):  # 'docs/' not the word 'docs'
            return "dir_pointer", 0.0
    return None


PRESENT_IN_README = "PRESENT_IN_README"
PRESENT_IN_FACTS = "PRESENT_IN_FACTS"
MISSING = "MISSING"
NO_BUNDLE = "NO_BUNDLE"


def status_of(readme_hit, facts_hit) -> str:
    """The unit's delivery status: carried by the sealed README, only ingested into facts, or neither."""
    if readme_hit:
        return PRESENT_IN_README
    if facts_hit:
        return PRESENT_IN_FACTS
    return MISSING


# --- section splitting -----------------------------------------------------------------------

def split_sections(markdown: str) -> list[tuple[str, str]]:
    """``[(heading_text, body)]`` flat sections of a markdown document; fences are respected so a
    ``# comment`` in a code block is not a heading. Text before the first heading is dropped."""
    out: list[tuple[str, list[str]]] = []
    fence = None
    for line in markdown.splitlines():
        m = re.match(r"^\s*(`{3,}|~{3,})", line)
        if m:
            marker = m.group(1)[0]
            fence = None if fence == marker else (fence or marker)
        h = re.match(r"^(#{1,6})\s+(.*)$", line) if fence is None else None
        if h:
            out.append((h.group(2).strip(), []))
        elif out:
            out[-1][1].append(line)
    return [(h, "\n".join(b)) for h, b in out]


def body_is_material(body: str) -> bool:
    """A section has content worth carrying: not only badges, link lists of bare URLs, or nothing."""
    lines = [l for l in body.splitlines() if l.strip() and not _BADGE_LINE.match(l)]
    text = re.sub(r"https?://\S+", " ", "\n".join(lines))
    return len(tokens(text)) >= MIN_BODY_TOKENS


def version_pattern(kind: str, value: str) -> list[str]:
    """Regexes that recognise a platform/runtime floor in prose ('net8.0' as '.NET 8', 'java 21')."""
    v = re.escape(value.lower())
    pats = [rf"(?<![a-z0-9]){v}(?![a-z0-9])"]
    if kind == "dotnet":
        m = re.match(r"net(\d+)\.(\d+)", value.lower())
        if m and int(m.group(1)) >= 5:
            pats.append(rf"\.net\s*{m.group(1)}(\.{m.group(2)})?(?![0-9])")
    elif kind == "java":
        pats = [rf"(?:java|jdk|jre|release)[\s-]*(?:version\s*)?{v}(?![0-9])", rf"(?<![0-9.]){v}\+", rf"java-version[^\n]*{v}"]
    elif kind == "python":
        pats = [rf"python\s*(?:>=?\s*|version\s*)?{v}(?![0-9])", rf"(?<![0-9.]){v}\+", rf">=\s*{v}(?![0-9])", rf"python_requires[^\n]*{v}"]
    elif kind == "go":
        pats = [rf"(?<![a-z])go\s*(?:>=?\s*|version\s*)?{v}(?![0-9])", rf"(?<![0-9.]){v}\+"]
    elif kind == "node":
        pats = [rf"node(?:\.js)?\s*(?:>=?\s*|version\s*)?v?{v}(?![0-9])", rf">=\s*{v}(?![0-9])"]
    elif kind == "cxx":
        pats = [rf"c\+\+\s*{v}(?![0-9])", rf"cxx_std_{v}", rf"std=c\+\+{v}", rf"cxx_standard\s*{v}"]
    elif kind == "rust":
        pats = [rf"edition\s*=?\s*\"?{v}", rf"rust\s*(?:version\s*)?{v}(?![0-9])", rf"(?<![0-9.]){v}\+"]
    return pats
