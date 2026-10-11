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
  source heading and kind. It is a registry (``composition/source_topics._TOPICS`` and ``_HOMES``),
  not a branch: a heading that names a topic ("Installation", "Requirements", "Testing") maps to
  the sections that topic belongs in, a unit under no known topic falls back to its kind, and a
  unit none of the holdable sections suits gets ``None`` - the one case a deferral is still the
  honest outcome.
* :func:`rehomed` - the section a kept unit belongs in when the reply filed it in one that has no
  place for its topic (an install requirement in Scope and Limitations, a dependency list in the
  API Reference); ``dispositions.normalize`` applies it, because no stage after reconciliation
  can move a kept unit.
* :func:`disposition_variants` - the two complete object shapes the S4 schema offers: a placing
  disposition names a holdable section, every other disposition keeps the open destination (a
  supersession names whichever section renders or covers the unit, including a renderer-owned one).

A renderer-owned section stays a legal destination for ``SUPERSEDE_REDUNDANT`` only: that is the
disposition that says "this section already prints the substance", and the coverage rules of
``dispositions._supersession_gap`` decide whether it does.
"""

from __future__ import annotations

import copy
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
from repository_presenter.components.readme.composition.source_topics import (
    heading_parts,
    path_topic,
    root_heading,
    source_heading,
    topic_of,
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

# The sections a topic's units belong in, nearest first, for a code block and for anything else.
# "install" content that the Installation row does not print (a second package manager, an extra,
# a build-tool declaration, a requirement the Dependencies section does not state) lives in
# Development and Testing - README_CONTRACT.md row 17: "install or build and run the suite" - and
# nowhere else a reader would look for a limitation, a link or a first example. Scope and
# Limitations (row 16) is a bulleted list of limitations, Documentation and Resources (row 15) a
# list of links, Quick Start (row 10) one or two minimal examples; the wave-6 acceptance reviews
# found 124 install and dependency units in those three across 44 bundles (BarCode-Python,
# Slides-Python, PDF-Python, every sealed or would-be bundle). The prose and the code pools start
# with the same section so a lead-in and its block are never sent to different sections; the
# fallbacks after it are for a repository with no build or test asset.
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
        ("development_testing", "quick_start", "documentation_resources", "scope_limitations"),
    ),
    "setup": (
        ("quick_start", "development_testing", "additional_examples"),
        ("quick_start", "development_testing", "documentation_resources", "scope_limitations"),
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
# The sections a topic's units are moved out of when the reply filed them there: those whose
# contract row has no place for the topic - a bulleted list of limitations (row 16), a list of
# links (row 15), three to eight capabilities (row 7), the API surface (row 14), task-named
# examples (row 12). A model that meets "Requires Python 3.12+" under Installation files it with
# whatever section it reads next (Scope and Limitations 29 times, Documentation and Resources 21,
# Additional Examples 7, API Reference 4 and Key Capabilities 2 in the 44 wave-6 bundles), and no
# stage after reconciliation can move a kept unit. Quick Start is left alone for install content:
# it follows Installation, and an install warning there ("the PyPI release predates this source",
# Slides-Python) is read where a visitor needs it. Build and test material is the same shape
# filed under limitations (BarCode-Python's dev dependencies, 9 units), and a pointer into the API
# listing filed under capabilities is the orphan PDF-Python's Key Capabilities ends with (17).
_MISFILED: Mapping[str, frozenset[str]] = {
    "install": frozenset(
        {
            "scope_limitations",
            "documentation_resources",
            "key_capabilities",
            "api_reference",
            "additional_examples",
        }
    ),
    "build": frozenset({"scope_limitations", "key_capabilities", "api_reference"}),
    "api": frozenset({"key_capabilities", "scope_limitations"}),
}
# The unit kinds the shell owns outright; a placement of one is never a content placement.
_SHELL_KINDS = frozenset({"heading", "badge_row", "html_block"})
# A unit under no known topic is placed by its kind alone. Neither list ends in the API Reference:
# a snippet or a sentence that is not about the API is not made to read as part of it, and a unit
# none of these suits is the one a deferral is still the honest outcome for.
_KIND_HOMES: tuple[tuple[str, ...], tuple[str, ...]] = (
    ("development_testing", "additional_examples", "quick_start"),
    ("scope_limitations", "documentation_resources", "key_capabilities"),
)


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
    parts = heading_parts(heading_path) if heading_path else []
    if parts and root is not None and parts[0] == root:
        parts = parts[1:]
        if not parts:
            return None
    topic = topic_of(parts)
    if topic == "furniture":
        return None
    candidates = _HOMES[topic][0 if code else 1] if topic is not None else ()
    for pool in (candidates, _KIND_HOMES[0 if code else 1]):
        for section in pool:
            if section in holdable and section not in _NEVER_AUTOMATIC and kind in _kinds(section):
                return section
    return None


def rehomed(
    unit_id: str,
    heading_path: str | None,
    destination: str | None,
    holdable: Collection[str],
    root: str | None = None,
) -> str | None:
    """The section a kept unit belongs in when the reply filed it somewhere else, or ``None`` when
    it stays where it is.

    Only a unit of a topic with a ``_MISFILED`` entry (what the Installation and Dependencies
    sections print, build and test material, API listings) filed in a section that has no
    place for it is moved, and only to the topic's
    own home (:func:`nearest_holdable`); a unit the shell owns, a unit with no home, or one filed
    in a section that can hold it is left alone."""
    if unit_id.rsplit(".", 1)[-1] in _SHELL_KINDS or destination is None:
        return None
    topic = path_topic(heading_path, root)
    if topic is None or destination not in _MISFILED.get(topic, frozenset()):
        return None
    home = nearest_holdable(unit_id, heading_path, holdable, root)
    return home if home is not None and home != destination else None


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
