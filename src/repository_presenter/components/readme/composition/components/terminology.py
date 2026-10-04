"""The governed technical-terminology registry and heading-case grammar: one owner.

``plans/idea.md`` (Portfolio README Presentation Contract): "Every Markdown heading uses title
case. Visitor-facing technical abbreviations use their canonical uppercase forms throughout,
including PS, EPS, PDF, XPS, XLSX, HTML, and equivalent discovered formats or protocols. ... The
renderer derives terminology from accepted facts plus the governed technical registry; validation
rejects noncanonical public casing."

``docs/README_CONTRACT.md`` section 2: "Technical abbreviations use their canonical forms, uppercase
where the standard is uppercase (PDF, XLSX, HTML, PS, EPS, XPS) and mixed where the standard is
mixed (glTF, npm) - never "Gltf" or "GLTF" in a heading."

This module is the single place those two sentences are data. The renderer normalises prose to the
forms returned by :func:`canonical_forms`, and BC-07 judges the rendered document against the same
function, so the two cannot drift (docs/RESEARCH_AND_GUIDELINES.md section 27.10). Adding a
standard, or a word that must never be mistaken for one, is an edit to a table below - never a
change to a check.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Terms whose standard is spelled in capitals (README_CONTRACT.md section 2). "PS" (PostScript) is
# named in plans/idea.md at the top of its list; it is two letters, which the old minimum-length
# gate of three could never admit, so it was unspellable in either the fixed set or the discovered
# one (verification V2 item 8).
UPPERCASE_TERMS: frozenset[str] = frozenset(
    {
        "PDF",
        "XLSX",
        "HTML",
        "PS",
        "EPS",
        "XPS",
        "API",
        "JSON",
        "XML",
        "CSV",
        "SVG",
        "URL",
        "HTTP",
        "SDK",
        "CLI",
    }
)
# Terms whose standard is mixed-case (README_CONTRACT.md section 2: "glTF, npm"). Their canonical
# spelling is kept exactly; "GLTF", "Gltf" and "NPM" are the non-canonical forms.
MIXED_CASE_TERMS: frozenset[str] = frozenset({"glTF", "npm"})
# Format extensions that are also ordinary words are never judged as abbreviations. G4-W17 arrival
# item 104: "one" (Microsoft OneNote's own format extension) was mapped to a spurious "ONE" and
# BC-07 flagged the pronoun in unrelated prose, so each such word is listed here.
WORD_EXTENSIONS: frozenset[str] = frozenset(
    {"max", "ply", "dat", "raw", "bin", "log", "map", "mat", "tag", "ini", "one"}
)
# Two-letter ordinary English words. A discovered two-letter format extension ("ps") qualifies as an
# abbreviation, which is what lets a short standard be canonical at all, unless it spells one of
# these ("go", "is", "to"): the lowercase scan would otherwise raise a pronoun or a verb.
ORDINARY_TWO_LETTER_WORDS: frozenset[str] = frozenset(
    {
        "am",
        "an",
        "as",
        "at",
        "be",
        "by",
        "do",
        "go",
        "he",
        "hi",
        "if",
        "in",
        "is",
        "it",
        "me",
        "my",
        "no",
        "of",
        "oh",
        "ok",
        "on",
        "or",
        "so",
        "to",
        "up",
        "us",
        "we",
    }
)
ORDINARY_WORDS: frozenset[str] = WORD_EXTENSIONS | ORDINARY_TWO_LETTER_WORDS
MIN_EXTENSION_LENGTH = 2

# A word standing alone in prose: not an extension (.dae), not part of a path or package
# coordinate (aspose-html-foss, a:b), not a longer identifier. One pattern for the renderer and the
# validator, so the two match exactly (G4-W17 arrival items 103 and 112).
LOWER_WORD = re.compile(r"(?<![.\w:-])[a-z]{2,}(?![\w:-])")
ANY_CASE_WORD = re.compile(r"(?<![.\w:-])[A-Za-z]{2,}(?![\w:-])")
_CODE_SPAN = re.compile(r"`[^`]*`")


def canonical_forms(extensions: Iterable[str] = ()) -> dict[str, str]:
    """Lowercase spelling to canonical form for every term this document owns.

    The registry tables above, plus every format extension the facts record that is not an
    ordinary word, upper-cased: a repository whose formats are OBJ and GLB gets those too. A
    registry term always wins over the derived upper-case form, so ``gltf`` is ``glTF`` even when
    a format fact records ``.gltf``.
    """
    forms = {term.lower(): term for term in UPPERCASE_TERMS | MIXED_CASE_TERMS}
    for raw in extensions:
        extension = raw.lstrip(".").lower()
        if (
            len(extension) >= MIN_EXTENSION_LENGTH
            and extension.isalpha()
            and extension not in ORDINARY_WORDS
        ):
            forms.setdefault(extension, extension.upper())
    return forms


def noncanonical_terms(text: str, forms: dict[str, str]) -> list[tuple[str, str]]:
    """(found, canonical) for each standalone word in ``text`` spelled other than canonically.

    Case-insensitive, so ``Gltf``, ``GLTF`` and ``Pdf`` are found as readily as ``pdf``. Code
    spans keep their source spelling and are not read.
    """
    found: list[tuple[str, str]] = []
    for match in ANY_CASE_WORD.finditer(_CODE_SPAN.sub(" ", text)):
        word = match.group(0)
        canonical = forms.get(word.lower())
        if canonical is not None and word != canonical and (word, canonical) not in found:
            found.append((word, canonical))
    return found


# Words a title leaves lowercase mid-heading (articles, coordinating conjunctions, and
# prepositions). Either case is accepted for these between the first and last word, because the
# common style guides disagree about the longer prepositions ("With", "From"); the words that do
# the heading's work are never optional.
MINOR_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "nor",
        "for",
        "so",
        "yet",
        "as",
        "at",
        "by",
        "in",
        "of",
        "on",
        "to",
        "up",
        "via",
        "vs",
        "per",
        "from",
        "with",
        "into",
        "onto",
        "over",
    }
)
_EDGE_PUNCTUATION = ".,:;!?\"'()[]{}<>*"


def _identifier_like(word: str) -> bool:
    """A token whose spelling is its own: it carries a digit, a path or call separator, or a capital
    after its first letter (CamelCase, an acronym, ``iOS``)."""
    return any(char.isdigit() or char in "._/\\()@#=+" for char in word) or any(
        char.isupper() for char in word[1:]
    )


def title_case_violations(text: str, forms: dict[str, str] | None = None) -> list[str]:
    """The words of a heading that title case forbids; empty when the heading is in title case.

    The grammar: the first and last word begin with a capital, and so does every word between
    except the articles, conjunctions and prepositions of :data:`MINOR_WORDS`. A hyphenated
    compound is judged on its first segment. Not judged, because their spelling is their own: a
    code span, a token with a digit or a path/call separator, a token with a capital after its
    first letter, a symbol-only token ("&"), and a canonical term of ``forms`` spelled exactly
    ("npm").
    """
    forms = forms or {}
    words = []
    for raw in _CODE_SPAN.sub(" ", text).split():
        word = raw.strip(_EDGE_PUNCTUATION)
        if any(char.isalpha() for char in word):
            words.append(word)
    violations: list[str] = []
    for index, word in enumerate(words):
        if _identifier_like(word) or forms.get(word.lower()) == word:
            continue
        edge = index in (0, len(words) - 1)
        if word[:1].isupper() or (not edge and word.lower() in MINOR_WORDS):
            continue
        violations.append(word)
    return violations


def _capitalised(word: str) -> str:
    """``word`` with the first letter of each hyphen-joined segment raised ("read-only" to
    "Read-Only"), every other character untouched."""
    return "-".join(part[:1].upper() + part[1:] for part in word.split("-"))


def to_title_case(text: str, forms: dict[str, str] | None = None) -> str:
    """``text`` in title case: the deterministic repair of what :func:`title_case_violations` finds.

    Exactly the words that function would reject are capitalised and nothing else is touched - a
    code span, an identifier-like token, a canonical term and a mid-heading minor word keep their
    spelling - so ``title_case_violations(to_title_case(text, forms), forms)`` is always empty. The
    renderer applies it to a heading an LLM unit supplies (an additional example's task name):
    capitalisation is a repeatable transformation, so deterministic code owns it (plans/idea.md,
    Deterministic and Agentic Approach) and a sentence-case task name never reaches the document.
    """
    forms = forms or {}
    pieces = re.split(r"(`[^`]*`|\s+)", text)
    word_pieces = [
        index
        for index, piece in enumerate(pieces)
        if piece
        and not piece.isspace()
        and not piece.startswith("`")
        and any(char.isalpha() for char in piece.strip(_EDGE_PUNCTUATION))
    ]
    for position, index in enumerate(word_pieces):
        piece = pieces[index]
        core = piece.strip(_EDGE_PUNCTUATION)
        if _identifier_like(core) or forms.get(core.lower()) == core:
            continue
        edge = position in (0, len(word_pieces) - 1)
        if core[:1].isupper() or (not edge and core.lower() in MINOR_WORDS):
            continue
        start = piece.index(core)
        pieces[index] = piece[:start] + _capitalised(core) + piece[start + len(core) :]
    return "".join(pieces)
