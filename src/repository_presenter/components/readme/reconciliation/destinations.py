"""Where a kept inherited unit can go: the sections that can hold it, and the nearest one.

Reconciliation (S4) offered every section of the shell as a destination for a kept unit, and four of
them cannot hold one. The renderer owns Installation, Dependencies, the identity and badge rows, the
Navigation list, Third-Party Notices and License: they print from facts and have no place for an
inherited paragraph or code block (README_CONTRACT.md section 2, owner ``D``). At a Glance holds one
diagram and nothing else. A section whose condition does not hold at this revision is not in the
document at all. A model asked "where does this Gradle snippet live?" answered ``installation``
because that is where the reader met it (wave 4, nine repositories), the placement was refused as
"needs a destination the shell can hold", the re-ask answered ``installation`` again, and the
last-resort correction deferred the unit, so the content left the README (BC-05 v7 now blocks that).

This module is the one answer to "which sections can hold a unit here":

* :func:`holdable_sections` - the sections a VERIFIED_PRESERVE, VERIFIED_MOVE, VERIFIED_REWRITE or
  CORRECT_WITH_EVIDENCE disposition may name for this repository, in shell order. It is the
  decoder's enum for a placing disposition (``dispositions.reconciliation_schema``), the list a
  refusal quotes, and the set a last-resort correction picks from, so the three can never disagree.
* :func:`nearest_holdable` - the holdable section nearest to one unit, read from the unit's own
  source heading and kind. It is a registry (``_TOPICS`` and ``_HOMES``), not a branch: a heading
  that names a topic ("Installation", "Requirements", "Testing") maps to the sections that topic
  belongs in, a unit under no known topic falls back to its kind, and a unit none of the holdable
  sections suits gets ``None`` - the one case a deferral is still the honest outcome.
* :func:`disposition_variants` - the two complete object shapes the S4 schema offers: a placing
  disposition names a holdable section, every other disposition keeps the open destination (a
  supersession names whichever section renders or covers the unit, including a renderer-owned one).

A renderer-owned section stays a legal destination for ``SUPERSEDE_REDUNDANT`` only: that is the
disposition that says "this section already prints the substance", and the coverage rules of
``dispositions._supersession_gap`` decide whether it does.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    section_ids,
)
from repository_presenter.components.readme.composition.planning import section_conditions
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
)
from repository_presenter.core.facts import Fact, FactsDocument

PLACING_DISPOSITIONS = (
    "VERIFIED_PRESERVE",
    "VERIFIED_REWRITE",
    "VERIFIED_MOVE",
    "CORRECT_WITH_EVIDENCE",
)

# README_CONTRACT.md section 2.1: At a Glance is exactly one Mermaid fence. A unit placed there is
# folded to the diagram's supersession or to a deferral (dispositions.normalize), never rendered.
_DIAGRAM_ONLY = frozenset({"at_a_glance"})
# The opening is the product summary the plan and investigation own; a unit is never *moved* there
# by code, only the lead paragraph is superseded into it (dispositions.normalize).
_NEVER_AUTOMATIC = frozenset({"opening"})
# The unit kinds a section can print as written. A section absent here prints any kind.
_PRINTS = {
    "enterprise_relationship": frozenset({"paragraph", "heading"}),
    "documentation_resources": frozenset({"paragraph", "list", "blockquote"}),
    "key_capabilities": frozenset({"paragraph", "list", "blockquote"}),
    "scope_limitations": frozenset({"paragraph", "list", "table", "blockquote"}),
}

# A heading's topic, from its own words. The deepest heading of a unit's path is read first, then
# its parents; the product's H1 (the path's first part) names the product, not a topic.
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
    (
        "install",
        re.compile(
            r"\b(?:install\w*|setup|set up|getting started|requirements?|prerequisites?|"
            r"depend\w*|extras?|packages?)\b"
        ),
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
# The sections a topic's units belong in, nearest first, for a code block and for anything else.
# "install" content that the Installation row does not print (a second package manager, an extra,
# a build-tool declaration) lives with the commands a maintainer runs, or with the requirements a
# reader must meet; it is never dropped.
_HOMES: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "build": (
        ("development_testing", "additional_examples", "quick_start"),
        ("development_testing", "scope_limitations"),
    ),
    "example": (
        ("additional_examples", "quick_start", "development_testing"),
        ("additional_examples", "quick_start", "scope_limitations"),
    ),
    "install": (
        ("development_testing", "quick_start", "additional_examples"),
        ("scope_limitations", "documentation_resources", "development_testing"),
    ),
    "api": (("api_reference",), ("api_reference",)),
    "limits": (("scope_limitations",), ("scope_limitations",)),
    "capabilities": (
        ("additional_examples", "quick_start"),
        ("key_capabilities", "scope_limitations"),
    ),
    "resources": (
        ("additional_examples", "development_testing"),
        ("documentation_resources", "scope_limitations"),
    ),
}
# A unit under no known topic is placed by its kind alone. Neither list ends in the API Reference:
# a snippet or a sentence that is not about the API is not made to read as part of it, and a unit
# none of these suits is the one a deferral is still the honest outcome for.
_KIND_HOMES: tuple[tuple[str, ...], tuple[str, ...]] = (
    ("development_testing", "additional_examples", "quick_start"),
    ("scope_limitations", "documentation_resources", "key_capabilities"),
)
_SPACE = re.compile(r"[^a-z0-9]+")


def holdable_sections(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> tuple[str, ...]:
    """The sections a placing disposition may name for this repository, in shell order.

    A section holds an inherited unit when its content is the LLM's or a mix (owner ``L`` or ``M``),
    it is in the document at this revision (its condition does not fail on these facts), and it is
    not the diagram-only At a Glance. The Enterprise Edition paragraph needs a verified target,
    which ``section_conditions`` already asks for."""
    absent = {
        section for section, holds in section_conditions(facts, policy).items() if holds is False
    }
    return tuple(
        section.id
        for section in SEMANTIC_SHELL
        if section.owner != "D" and section.id not in absent and section.id not in _DIAGRAM_ONLY
    )


def source_heading(unit: Fact | None) -> str | None:
    """The heading path the extractor recorded for an inherited unit, or ``None``."""
    if unit is None:
        return None
    section = (unit.attributes or {}).get("section")
    return section or None


def _path(section: str) -> list[str]:
    """A heading path ("Product > Installation > Requirements") as lower-case parts."""
    return [
        part for part in (_SPACE.sub(" ", p.lower()).strip() for p in section.split(">")) if part
    ]


def root_heading(units: Sequence[Fact]) -> str | None:
    """The README's title as the first part of its units' heading paths: the part more than half of
    them share. A path starts with the product's own H1, which names the product and not a topic
    ("Aspose.Note FOSS" is not a note); a README with no H1 has no such part."""
    firsts = Counter(
        path[0] for unit in units if (section := source_heading(unit)) and (path := _path(section))
    )
    if not firsts:
        return None
    root, count = firsts.most_common(1)[0]
    return root if count * 2 > sum(firsts.values()) else None


def _topic(parts: Sequence[str]) -> str | None:
    """The topic of a heading path's parts: the first, deepest part that names one."""
    for part in reversed(parts):
        for topic, pattern in _TOPICS:
            if pattern.search(part):
                return topic
    return None


def nearest_holdable(
    unit_id: str, heading_path: str | None, holdable: Collection[str], root: str | None = None
) -> str | None:
    """The holdable section nearest to one unit, or ``None`` when none of them suits it.

    The unit's kind (the suffix of its ID) decides whether it is a code block; its source heading
    decides the topic; the topic's list (``_HOMES``) is walked nearest first and the first section
    that is holdable and prints this kind of unit wins. A shell command and any other snippet share
    their homes. ``root`` is the README's title (``root_heading``): a unit directly under it is the
    product introduction, which the opening is written from, and a unit under a heading the shell
    prints itself (licence, notices, navigation, badges) is that section's own text; neither has a
    home."""
    kind = unit_id.rsplit(".", 1)[-1]
    code = kind == "code_block"
    parts = _path(heading_path) if heading_path else []
    if parts and root is not None and parts[0] == root:
        parts = parts[1:]
        if not parts:
            return None
    topic = _topic(parts)
    if topic == "furniture":
        return None
    candidates = _HOMES[topic][0 if code else 1] if topic is not None else ()
    for pool in (candidates, _KIND_HOMES[0 if code else 1]):
        for section in pool:
            if section in holdable and section not in _NEVER_AUTOMATIC and kind in _kinds(section):
                return section
    return None


def _kinds(section: str) -> Collection[str]:
    """The unit kinds ``section`` prints as written (all of them for a section not listed)."""
    return _PRINTS.get(
        section, frozenset({"paragraph", "list", "table", "code_block", "blockquote"})
    )


def nearest_for_units(
    units: Sequence[Fact], holdable: Collection[str], context: Sequence[Fact] | None = None
) -> dict[str, str | None]:
    """:func:`nearest_holdable` for each of ``units``, keyed by unit ID. ``context`` is the set of
    units the README's title is read from (default: ``units``); a subset of one section's units
    must pass the whole batch, or that section would be taken for the title."""
    root = root_heading(context if context is not None else units)
    return {
        unit.id: nearest_holdable(unit.id, source_heading(unit), holdable, root) for unit in units
    }


def disposition_variants(item: Mapping[str, Any], holdable: Sequence[str]) -> list[dict[str, Any]]:
    """The S4 schema's two complete object shapes, from the manifest's one.

    ``item`` is the manifest's disposition object (unit, disposition, destination, citations,
    rationale). A placing disposition keeps its destination to ``holdable``; every other
    disposition keeps the open one (null or any section), because a supersession names the section
    that already renders the unit, renderer-owned or not. Each shape is a whole object, not a
    refinement of a shared one: a constrained decoder compiles each alternative as its own grammar
    and a sibling ``properties`` next to ``anyOf`` is not honoured by all of them. With nothing
    holdable the placing shape is dropped, so no placement can be written at all."""
    placing = copy.deepcopy(dict(item))
    placing["properties"]["disposition"] = {"enum": list(PLACING_DISPOSITIONS)}
    placing["properties"]["destination_section"] = {"type": "string", "enum": list(holdable)}
    other = copy.deepcopy(dict(item))
    other["properties"]["disposition"] = {
        "enum": [
            name
            for name in item["properties"]["disposition"]["enum"]
            if name not in PLACING_DISPOSITIONS
        ]
    }
    other["properties"]["destination_section"] = {
        "oneOf": [{"type": "null"}, {"type": "string", "enum": list(section_ids())}]
    }
    return [placing, other] if holdable else [other]
