"""What a kept inherited unit is about, read from the heading path it sat under in the source.

Two stages need the same answer. Reconciliation (``reconciliation/destinations.py``) uses it to say
which section can hold a unit its destination cannot, and to move a unit the model filed under a
section that has nothing to do with its topic. Placement (``composition/placement.py``) uses it to
decide which of the renderer's own sections already state a unit before it is printed a second time.
It lives under ``composition`` because placement may not import reconciliation (reconciliation
imports planning, which imports placement), and it is a registry of patterns, not a branch: a new
topic is a row in ``_TOPICS``.

A heading path starts with the product's H1, which names the product and not a topic. The deepest
heading of a path is read first, then its parents; the first topic whose pattern matches wins.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from repository_presenter.core.facts import Fact

# (topic, heading pattern), in the order they are tried against one heading.
_TOPICS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Sections the shell prints itself from facts: the licence statement, the notices link, the
    # Navigation list, the badge and banner rows. A unit under one of these headings is that
    # section's own text, not content to keep somewhere else, so it has no home.
    (
        "furniture",
        re.compile(
            r"\b(?:licen[cs]\w*|copyright|notices?|third party|navigation|table of contents|"
            r"contents|badges?|banner)\b"
        ),
    ),
    (
        "build",
        re.compile(r"\b(?:tests?|testing|build|building|develop\w*|contribut\w*|compil\w*|ci)\b"),
    ),
    (
        "example",
        re.compile(
            r"\b(?:examples?|usage|samples?|tutorials?|recipes?|demos?|quick start|how to)\b"
        ),
    ),
    # A heading that gets the reader going. Its prose is often the first example's explanation, so
    # a unit under it stays where the model put it; only the fallback home is chosen from here.
    ("setup", re.compile(r"\b(?:setup|set up|getting started)\b")),
    # What the Installation and Dependencies sections print from facts: how the package is
    # obtained, what it needs. A kept unit under such a heading is the renderer's subject too.
    (
        "install",
        re.compile(r"\b(?:install\w*|requirements?|prerequisites?|depend\w*|extras?|packages?)\b"),
    ),
    ("api", re.compile(r"\b(?:api|reference|classes|methods?|namespaces?|modules?)\b")),
    (
        "limits",
        re.compile(
            r"\b(?:limit\w*|supported|compatib\w*|known|restrictions?|caveats?|status|roadmap|notes?)\b"
        ),
    ),
    (
        "capabilities",
        re.compile(r"\b(?:features?|capabilit\w*|overview|about|highlights?|why|what)\b"),
    ),
    (
        "resources",
        re.compile(
            r"\b(?:docs?|documentation|links?|resources?|community|contact|help|learn\w*|"
            r"changelog|releases?|acknowledg\w*|credits?)\b"
        ),
    ),
)
_SPACE = re.compile(r"[^a-z0-9]+")


def source_heading(unit: Fact | None) -> str | None:
    """The heading path the extractor recorded for an inherited unit, or ``None``."""
    if unit is None:
        return None
    section = (unit.attributes or {}).get("section")
    return section or None


def heading_parts(section: str) -> list[str]:
    """A heading path ("Product > Installation > Requirements") as lower-case parts."""
    return [
        part for part in (_SPACE.sub(" ", p.lower()).strip() for p in section.split(">")) if part
    ]


def root_heading(units: Sequence[Fact]) -> str | None:
    """The README's title as the first part of its units' heading paths: the part more than half of
    them share. A path starts with the product's own H1, which names the product and not a topic
    ("Aspose.Note FOSS" is not a note); a README with no H1 has no such part."""
    firsts = Counter(
        path[0]
        for unit in units
        if (section := source_heading(unit)) and (path := heading_parts(section))
    )
    if not firsts:
        return None
    root, count = firsts.most_common(1)[0]
    return root if count * 2 > sum(firsts.values()) else None


def topic_of(parts: Sequence[str]) -> str | None:
    """The topic of a heading path's parts: the first, deepest part that names one."""
    for part in reversed(parts):
        for topic, pattern in _TOPICS:
            if pattern.search(part):
                return topic
    return None


def path_topic(heading_path: str | None, root: str | None = None) -> str | None:
    """The topic of a heading path, with the README's title (``root``) taken off the front.
    ``None`` for a path under no known topic or directly under the title, which is the product
    introduction the opening is written from."""
    parts = heading_parts(heading_path) if heading_path else []
    if parts and root is not None and parts[0] == root:
        parts = parts[1:]
    return topic_of(parts) if parts else None


def unit_topic(unit: Fact | None, root: str | None = None) -> str | None:
    """The topic of one inherited unit from its own heading path (:func:`path_topic`)."""
    return path_topic(source_heading(unit), root)
