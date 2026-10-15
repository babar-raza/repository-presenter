"""Whether a tracked ``docs/`` directory holds documentation, read from the pinned clone.

``add_doc_links`` was report-only because it treated any ``docs/`` directory as documentation
(Slides for .NET and Slides for C++: ``docs/`` held a banner, a NuGet icon and a NuGet README). Its
re-enable condition (``additions.DOCS_RE_ENABLE``) asks for a SUPPORTED fact
``build_test_asset:documentation`` recording a docs directory with at least one markdown or
reStructuredText file of prose, outside the asset directories. This module makes that fact: a file
counts only when, with its code blocks, tables, headings, link lists and markup taken out, it still
holds a few sentences of running text.

The fact is made by the correction run from the clone (it is not an extractor's), and travels in
the bundle's ``facts.json`` so the typed gate re-derives the same edit.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.facts import Evidence, Fact

DOCS_FACT_ID = "build_test_asset:documentation"
ASSET_DIRS = frozenset(
    {"media", "assets", "images", "img", "nuget", "static", "public", "icons", "banner", "logo"}
)
#: Running text a documentation file must hold: words in lines of at least ``_LINE_WORDS`` words.
MIN_PROSE_WORDS = 40
_LINE_WORDS = 6
_MAX_BYTES = 400_000
_MAX_EVIDENCE = 3
_FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")
_TAGS = re.compile(r"<[^>\n]+>")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")


def documentation_paths(tree_paths: Sequence[str]) -> list[str]:
    """The markdown and reStructuredText files under ``docs/`` outside the asset directories."""
    found = []
    for path in tree_paths:
        parts = path.lower().split("/")
        is_text = parts[-1].endswith((".md", ".rst"))
        if parts[0] == "docs" and len(parts) > 1 and is_text and not ASSET_DIRS & set(parts[1:-1]):
            found.append(path)
    return sorted(found)


def prose_words(text: str) -> int:
    """The words of running text in ``text``: lines of at least six words that are not code,
    tables, headings, list items of bare links or markup."""
    total = 0
    fenced = False
    for raw in text.splitlines():
        if _FENCE.match(raw):
            fenced = not fenced
            continue
        line = raw.strip()
        if fenced or not line or line.startswith(("#", "|", ">", "=", "-" * 3, ":::", "..")):
            continue
        line = _LINK.sub(r"\1", _TAGS.sub(" ", line)).lstrip("-*+ 0123456789.)")
        words = _WORD.findall(line)
        if len(words) >= _LINE_WORDS:
            total += len(words)
    return total


def documentation_fact(clone_path: Path, tree_paths: Sequence[str]) -> Fact | None:
    """The SUPPORTED fact for a ``docs/`` directory holding prose documentation, or ``None``."""
    evidence: list[Evidence] = []
    count = 0
    for path in documentation_paths(tree_paths):
        try:
            file = clone_path / path
            if file.stat().st_size > _MAX_BYTES:
                continue
            words = prose_words(file.read_text("utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if words >= MIN_PROSE_WORDS:
            count += 1
            if len(evidence) < _MAX_EVIDENCE:
                evidence.append(Evidence(path, f"{words} words of prose"))
    if not evidence:
        return None
    return Fact(
        DOCS_FACT_ID,
        "build_test_asset",
        "docs/",
        tuple(evidence),
        attributes={"role": "documentation", "files": str(count)},
    )
