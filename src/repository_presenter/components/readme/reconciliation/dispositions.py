"""Reconcile the existing README with the facts: one disposition per inherited unit.

The job receives every inherited unit, the SUPPORTED and CONTRADICTED facts (bounded), the
accepted investigation, and the shell's sections. Beyond the schema and the unit-ID binding, the
rules here run before the output is used. Deterministic sections (identity, badges, navigation,
installation, dependencies, third_party_notices, license) render from facts, so a unit the job
routes to one of them is normalised into SUPERSEDE_REDUNDANT citing the facts that section
renders - the job decided the unit is verified and where its substance belongs; deterministic
code decides that deterministic content is rendered, never copied. A placing disposition
otherwise needs a placeable destination, a correction cites its evidence, a supersession names
its section or cites facts, and a code block whose example is CONTRADICTED is never placed. A
violation is quoted back once; a second one fails the transaction closed.

A disposition may claim only what this stage can prove (TC-DSP-01, G3-W08). Reconciliation runs
before planning, so SUPERSEDE_REDUNDANT - "something else carries this" - stands only where that
is decidable from the facts: a shell-owned unit, a deterministic section whose rendering inputs
hold everything the unit rests on, the Core API table for a listing of verified classes, the
opening for the lead paragraph, a section that must cite or omit the unit (authoring.carried_units)
or the diagram for a diagram. Anywhere else the unit stays a placement and placement, which holds
the plan, decides. OMIT_UNSUPPORTED - "no fact supports this" - stands only after a failed support
lookup. What cannot be folded to a truthful disposition is refused by ``placement_errors`` (typed,
quoting the unit) and, on the last attempt, deferred by ``recover_uncited_prose_omits``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    _CARRY_SECTIONS,
    inherited_unit_named_symbols,
)
from repository_presenter.components.readme.composition.components.shell import (
    placeable_section_ids,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.placement import renderer_fact_ids
from repository_presenter.components.readme.composition.planning import section_conditions
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
)
from repository_presenter.components.readme.evidence.facts.links import extract_links
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
from repository_presenter.core.ecosystems import spec_for
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import (
    DECLARED_SYMBOL_KINDS,
    Fact,
    FactsDocument,
    bounded_records,
)
from repository_presenter.core.llm.binding import collect_ids
from repository_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

DISPOSITIONS_FILENAME = "dispositions.json"
PLACING = frozenset(
    {"VERIFIED_PRESERVE", "VERIFIED_REWRITE", "VERIFIED_MOVE", "CORRECT_WITH_EVIDENCE"}
)
# The shell owns every heading and badge row; placing one anywhere renders nothing.
_SHELL_OWNED = frozenset({"heading", "badge_row"})
# item 90: these three link_target facts are the renderer's own - product_pages.py resolves each
# from a live lookup independent of any inherited unit's own embedded copy, and the banner/
# enterprise folds a few lines below already own deciding what happens when either is unresolved.
# They are never CONTRADICTED in practice (product_pages.py records only SUPPORTED or UNRESOLVED),
# so excluding them here just keeps the fold below scoped to a unit's own prose, never to a link
# the renderer decides on its own - the same exclusion planning.py's _SHELL_OWNED_LINKS applies
# before letting a VERIFIED_REWRITE citation reach its own links backstop.
_RENDERER_OWNED_LINK_IDS = frozenset({BANNER_FACT_ID, HOMEPAGE_FACT_ID, ENTERPRISE_FACT_ID})
# Fence languages that mark a block of commands the maintainers run, never a product claim.
_COMMAND_FENCES = frozenset({"bash", "sh", "shell", "console", "zsh", "powershell", "pwsh", "cmd"})
# A block that installs or fetches the package belongs to the Installation row, which renders
# the verified install itself; any other command block is the maintainers' build or test path.
_INSTALL_COMMAND = re.compile(
    r"^\s*(?:[$>]\s*)?(?:python3?\s+-m\s+)?(?:pip3?\s+install|npm\s+install|dotnet\s+add|"
    r"cargo\s+add|go\s+get|git\s+clone)",
    re.IGNORECASE | re.MULTILINE,
)


def command_block_units(facts: FactsDocument) -> set[str]:
    """Inherited code blocks fenced as shell commands (README_CONTRACT.md section 2 row 17)."""
    found: set[str] = set()
    for fact in facts.by_kind("inherited_unit"):
        first = fact.value.splitlines()[0].strip().lower() if fact.value.strip() else ""
        if fact.id.endswith(".code_block") and first[3:].strip() in _COMMAND_FENCES:
            found.add(fact.id)
    return found


RENDERING_FACT_KINDS: dict[str, tuple[str, ...]] = {
    "identity": ("identity", "package"),
    "badges": ("link_target",),
    "banner": ("link_target",),  # the verified product illustration and homepage pair only
    "navigation": ("identity",),
    "installation": ("install_command",),
    "dependencies": ("dependency",),
    "third_party_notices": ("third_party_notices",),
    "license": ("license",),
}
_UNIT_REFERENCE = re.compile(r"unit (inherited_unit:[0-9]+\.[a-z_]+)")
# G4-W17 (BC-10 coherence-gap, aspose-slides-foss/Aspose.Slides-FOSS-for-.NET): the leading
# three-digit block ordinal of an inherited_unit ID - evidence/facts/inherited.py's own
# block_ordinal numbering is dense and contiguous (one whole document, no gaps), so ordinal+1 is
# always that unit's own immediate neighbor in the original document, split-list sub-ordinals
# (the optional middle group) included.
_UNIT_ORDINAL = re.compile(r"^inherited_unit:(\d{3})(?:\.\d{3})?\.[a-z_]+$")


_RECONCILIATION_BATCH = 40
# S4 output budget. A reply is bounded by construction, not by a measured average: the schema
# caps each disposition's fact_ids at RECONCILIATION_FACT_IDS_PER_DISPOSITION, and a batch is
# only as large as the longest reply the schema admits still fits max_output_tokens, counted at
# OUTPUT_CHARS_PER_TOKEN_FLOOR characters per token. The defect this closes (PDF-TypeScript,
# 2026-10-04): one 40-unit reply reached finish_reason length at 32,000 tokens, and the same
# request then answered 4,666. A disposition's citations were bounded only by the batch's citable
# set (739 IDs there), so a repeating list could run to the whole budget. The same class ran away
# on Cells-Go (2026-09-11, 1,047 repeated IDs) and PDF-.NET (F27).
RECONCILIATION_FACT_IDS_PER_DISPOSITION = 16
# The healthy 40-unit reply measured 4.2 characters per token (19,616 characters, 4,666 tokens,
# qwen3-next). Identifier-dense JSON packs fewer, so the bound uses this floor, never that average.
OUTPUT_CHARS_PER_TOKEN_FLOOR = 2.5
# The rationale's maxLength and the disposition enum, as the manifest states them; a test holds
# both to the manifest so the bound below can never drift from the schema it is computed for.
_RATIONALE_MAX_CHARS = 160
_DISPOSITIONS = (
    "VERIFIED_PRESERVE",
    "VERIFIED_REWRITE",
    "VERIFIED_MOVE",
    "CORRECT_WITH_EVIDENCE",
    "SUPERSEDE_REDUNDANT",
    "OMIT_UNSUPPORTED",
    "DEFER_UNRESOLVED",
    "NON_CONTENT",
)


def _longest(node: Mapping[str, Any]) -> int | None:
    """The longest serialized value a schema node admits, JSON quotes included; ``None`` if open."""
    if "enum" in node:
        return max(len(json.dumps(value, ensure_ascii=False)) for value in node["enum"])
    if "oneOf" in node:
        known = [
            size for size in (_longest(option) for option in node["oneOf"]) if size is not None
        ]
        return max(known) if len(known) == len(node["oneOf"]) else None
    if node.get("type") == "null":
        return len("null")
    if node.get("type") == "string" and "maxLength" in node:
        return int(node["maxLength"]) + 2
    return None


def _reply_chars(
    records: int,
    *,
    unit_chars: int,
    disposition_chars: int,
    destination_chars: int,
    fact_id_chars: int,
    citations: int,
    rationale_chars: int,
) -> int:
    """Characters of the longest reply of ``records`` dispositions: every value at the given
    serialized length, every citation list full, pretty-printed (the wider of the two forms a
    model writes, so compact output is bounded too)."""
    record = {
        "unit_id": "u" * (unit_chars - 2),
        "disposition": "d" * (disposition_chars - 2),
        "destination_section": "s" * (destination_chars - 2),
        "fact_ids": ["f" * (fact_id_chars - 2)] * citations,
        "rationale": "r" * (rationale_chars - 2),
    }
    return len(json.dumps({"dispositions": [record] * records}, indent=2, ensure_ascii=False))


def output_chars_bound(schema: Mapping[str, Any]) -> int | None:
    """The longest reply, in characters, that ``schema`` admits; ``None`` when a field it leaves
    open makes the bound infinite. Computed from the schema the job is decoded under, so it tracks
    the schema rather than a separate estimate; it is a bound only to the extent the decoder
    enforces that schema, which the live proof checks against a real reply."""
    dispositions = schema["properties"]["dispositions"]
    props = dispositions["items"]["properties"]
    fact_ids = props["fact_ids"]
    sizes = {
        "unit_chars": _longest(props["unit_id"]),
        "disposition_chars": _longest(props["disposition"]),
        "destination_chars": _longest(props["destination_section"]),
        "rationale_chars": _longest(props["rationale"]),
        "citations": fact_ids.get("maxItems"),
    }
    if None in sizes.values() or "maxItems" not in dispositions:
        return None
    fact_chars = _longest(fact_ids["items"]) if "items" in fact_ids else 0
    if fact_chars is None:
        return None
    return _reply_chars(
        dispositions["maxItems"],
        **{k: v for k, v in sizes.items() if k != "citations"},
        fact_id_chars=fact_chars,
        citations=sizes["citations"],
    )


def _batch_size(facts: FactsDocument, max_output_tokens: int) -> int:
    """The largest batch, up to _RECONCILIATION_BATCH units, whose longest reply the schema
    admits still fits the budget. Sized from the repository's own longest identifiers, so it
    holds for any citable set the packet can show: every ID a batch could cite is in ``facts``."""
    units = list(facts.by_kind("inherited_unit"))
    if not units:
        return _RECONCILIATION_BATCH
    budget = max_output_tokens * OUTPUT_CHARS_PER_TOKEN_FLOOR
    sizes = {
        "unit_chars": max(len(json.dumps(unit.id)) for unit in units),
        "disposition_chars": max(len(json.dumps(name)) for name in _DISPOSITIONS),
        "destination_chars": max(len(json.dumps(name)) for name in section_ids()),
        "rationale_chars": _RATIONALE_MAX_CHARS + 2,
        "fact_id_chars": max(len(json.dumps(fact.id)) for fact in facts.facts),
        "citations": RECONCILIATION_FACT_IDS_PER_DISPOSITION,
    }

    def fits(size: int) -> bool:
        return _reply_chars(size, **sizes) <= budget

    size = min(_RECONCILIATION_BATCH, len(units))
    while size > 1 and not fits(size):
        size -= 1
    if not fits(size):
        raise ConfigError(
            f"one unit's longest reply ({_reply_chars(1, **sizes)} characters) exceeds the "
            f"source_reconciliation budget ({budget:.0f} characters); lower "
            "RECONCILIATION_FACT_IDS_PER_DISPOSITION or raise max_output_tokens"
        )
    return size


def reconciliation_batches(
    facts: FactsDocument, max_output_tokens: int
) -> list[tuple[str, list[Fact]]]:
    """Every inherited unit, split into batches in document (ordinal) order - one
    ``(batch_id, units)`` pair per ``source_reconciliation`` call this round makes. A batch holds
    at most _RECONCILIATION_BATCH units, and fewer when its longest reply would not fit
    ``max_output_tokens`` (see _batch_size). No unit is ever dropped.

    Ordinal order, not grouped by ``.section``: a batch boundary may occasionally fall inside one
    heading's own units, but preserves the document's own unit ordering exactly, which
    ``merge_dispositions()`` and every downstream reader already assume - grouping by section
    first would need to interleave document order back in afterward for no real benefit, since
    ``reconcile_checks`` (below) judges each disposition independently of its neighbours anyway.
    """
    units = list(facts.by_kind("inherited_unit"))
    size = _batch_size(facts, max_output_tokens)
    return [
        (f"reconciliation#{index // size + 1}", units[index : index + size])
        for index in range(0, len(units), size)
    ]


def reconciliation_batch_facts(facts: FactsDocument, batch_units: Sequence[Fact]) -> FactsDocument:
    """``facts``, with its own ``inherited_unit`` facts narrowed to exactly ``batch_units``.

    Real bug this closes, found live against Cells-Rust (not assumed): ``core/llm/binding.py``'s
    ``binding_errors`` recomputes its own "every inherited unit expected" set directly from
    ``facts.by_kind("inherited_unit")`` - the whole ``FactsDocument`` passed as the job's own
    ``facts=`` argument - independent of whatever the packet or schema for one particular call
    were scoped to. Passing the same, unscoped ``facts`` for every batch's own call made
    ``binding_errors`` demand full 91-unit coverage from each individual ~40-unit batch reply,
    rejecting every batch but the last on "no disposition for inherited units: ...". A batch's own
    call must see - and be judged against - only its own units; every other fact kind is
    untouched, so ``bounded_records()`` and every other check reading this document still see the
    real, whole repository.
    """
    keep = frozenset(fact.id for fact in batch_units)
    return FactsDocument(
        facts.repository,
        facts.source_revision,
        tuple(fact for fact in facts.facts if fact.kind != "inherited_unit" or fact.id in keep),
        facts.schema_version,
    )


def merge_dispositions(outputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Every batch's own accepted dispositions, concatenated in batch order into one flat
    document - the reconciliation sibling of ``composition/authoring.py``'s ``merge_units()``.

    Simpler than ``merge_units()``: a disposition is never rendered in shell order the way an
    authored unit is, so nothing here needs re-sorting by section - batch order already is
    document order (``reconciliation_batches()``'s own contract), and every downstream reader
    (placement, planning, validation, review) already reads ``dispositions`` as one flat list
    keyed by ``unit_id``, never by position.
    """
    dispositions: list[dict[str, Any]] = []
    for output in outputs:
        dispositions.extend(output.get("dispositions", []))
    return {"dispositions": dispositions}


def _packet_fact_records(facts: FactsDocument, manifest: PromptManifest) -> list[dict[str, str]]:
    """The fact records the reconciliation packet shows - one function, so the packet and the
    schema's citable set can never drift apart (the planning schema's own lesson, taskcard H)."""
    kinds = [kind for kind in manifest.packet.fact_kinds if kind != "inherited_unit"]
    return bounded_records(
        facts, kinds, ("SUPPORTED", "CONTRADICTED"), symbol_kinds=DECLARED_SYMBOL_KINDS
    )


def citable_fact_ids(
    facts: FactsDocument,
    manifest: PromptManifest,
    batch_units: Sequence[Fact],
    investigation: Mapping[str, Any],
) -> list[str]:
    """Every ID the job may *write* in this batch, sorted: the packet's own fact records, the
    facts the accepted investigation cites (the prompt lets the job copy those one by one, and
    the investigation travels in the packet, so each is an ID the job can actually see), and this
    batch's own inherited units. Nothing the packet never showed is in it (section 27.2 RC1), so
    an UNRESOLVED fact is absent - ``normalize`` adds one by code where a rule calls for it.

    This is a decoder constraint, not the stored output's shape: ``normalize`` writes IDs no
    packet shows (``identity:revision`` from ``rendering_fact_ids``, an UNRESOLVED example behind
    a deferred block), and the store holds the folded output, so the reuse path re-judges a
    stored reply under the manifest's base schema, the binding, and the checks - never under this
    enum (G4-W17 arrival item 60; ``core/llm/jobs.py::run_job``). Widening the enum instead would
    change every S4 request digest (the call schema is part of the payload) and reopen on the
    next fold-written ID.
    """
    known = {fact.id for fact in facts.facts}
    shown = {record["id"] for record in _packet_fact_records(facts, manifest)}
    cited = {fact_id for fact_id in collect_ids(investigation).fact_ids if fact_id in known}
    return sorted(shown | cited | {fact.id for fact in batch_units})


def reconciliation_schema(
    manifest: LoadedManifest,
    batch_units: Sequence[Fact],
    facts: FactsDocument,
    investigation: Mapping[str, Any],
) -> dict[str, Any]:
    """The reconciliation schema specialised for one batch: its units, and the IDs it may cite.

    Every inherited unit in this batch needs one disposition and no other unit is in this batch,
    which the code knows exactly, so the schema says so rather than letting the job invent a unit
    and be rejected for it (RESEARCH_AND_GUIDELINES.md section 27.5 D1; cause RC1 in 27.2). The
    canary's job paired the right ordinals with the wrong type suffixes -
    inherited_unit:037.paragraph where the unit is inherited_unit:037.code_block - and lost a
    whole transaction to it. The destination and the rationale stay the job's.

    PHASE0/G: scoped to ``batch_units`` (one ``reconciliation_batches()`` entry), not every
    inherited unit in the repository - the same per-batch shape ``authoring_schema()`` already
    uses (``minItems``/``maxItems``/enum sized to one ``SectionTask``'s own slots, not the whole
    plan). No unbounded fallback: every caller, production or test, must pass a real batch,
    mirroring ``authoring_schema()``'s own signature exactly (no "give me everything" mode).

    ``fact_ids`` gets the same treatment as ``unit_id``, for the same reason, and it has to be an
    enum. G4-W17 arrival item 40 (e2a1a83) pinned each entry by the pattern ``^(<kinds>):`` on an
    array with no ``maxItems`` - a real fix for a real defect (Aspose.PDF for Python cited the
    packet's own investigation keys, "product_summary:fact_ids", twice). Under strict json_schema
    decoding the bare kind prefix ``"public_symbol:"`` satisfies that pattern, and the decoder
    emitted it until the 32,000-token budget was gone: 1,047 times in one array on Aspose.Cells
    for Go, ``finish_reason length`` on both runs, and identically on Aspose.Cells and Slides for
    Java - S4 runs for every repository, so no candidate anywhere could seal (S4-REGRESSION,
    2026-09-11; lane D PROPOSAL P23, lane C PROPOSAL S, both measured live). The samples that did
    complete were rejected anyway, every ``fact_ids`` entry a prefix naming no fact. The IDs a
    disposition may cite are known here exactly (``citable_fact_ids``), so the schema lists them;
    lane D replayed the identical request with that one change: ``finish_reason stop``, 3,560
    tokens, 40 of 40 dispositions. A ``unit_id`` came back well-formed in every runaway reply -
    the one field that already had the enum.

    Item 40 bounded only the enum of the array's *items*; the array itself stayed unbounded, and
    G4-W17 arrival item 121 (lane F PROPOSAL F27) measured the same risk class still live on
    PDF-.NET - the identical request hash answered 32,000 tokens truncated on one attempt and a
    normal 3,016 tokens on an otherwise-identical retry, rescued only by chance. ``fact_ids`` now
    also gets a ``maxItems`` equal to this batch's own citable-set size: no single disposition can
    legitimately cite more distinct facts than exist in its own packet, and that size is already
    computed above as ``citable``, so the bound never drifts from the enum it accompanies.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    dispositions = schema["properties"]["dispositions"]
    citable = citable_fact_ids(facts, manifest.manifest, batch_units, investigation)
    # The destination is a shell section or null: an open string here is the one field a runaway
    # could fill to the budget unchecked (the same enum treatment unit_id and fact_ids get below).
    dispositions["items"]["properties"]["destination_section"] = {
        "oneOf": [{"type": "null"}, {"type": "string", "enum": list(section_ids())}]
    }
    if citable:
        dispositions["items"]["properties"]["fact_ids"]["items"] = {
            "type": "string",
            "enum": citable,
        }
        # item 121 (F27) bounded the array by the citable set, which is 739 IDs on PDF-TypeScript
        # and more elsewhere - a bound that does not bound the reply, since a repeating citation
        # list can run to the whole budget (2026-10-04: 32,000 tokens on one attempt). The cap is
        # per disposition and small: the symbols a placed unit names are added by code (see
        # ``normalize``), so the job cites the facts that carry its decision, and output_chars_bound
        # proves the whole batch's longest reply fits the budget at this cap.
        dispositions["items"]["properties"]["fact_ids"]["maxItems"] = min(
            len(citable), RECONCILIATION_FACT_IDS_PER_DISPOSITION
        )
    else:
        dispositions["items"]["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
    units = [fact.id for fact in batch_units]
    if not units:
        return schema
    dispositions["minItems"] = len(units)
    dispositions["maxItems"] = len(units)
    dispositions["items"]["properties"]["unit_id"] = {"type": "string", "enum": units}
    return schema


def reconciliation_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    manifest: PromptManifest,
    batch_units: Sequence[Fact],
) -> dict[str, Any]:
    """PHASE0/G: ``inherited_units`` is exactly ``batch_units`` - one batch's own units, not
    every inherited unit in the repository. ``facts`` (bounded, non-``inherited_unit`` kinds) is
    unchanged: shared context every batch needs, already capped by ``bounded_records()``.

    Public symbols enter by the granularity the extractor recorded, not by dotted depth (ported
    from PR #29/G4-W17 arrival item 40, stranded unmerged for 4 days - landed here 2026-09-11):
    the depth proxy is shaped by the package root, so a repository whose root is two or three
    segments has no citable type at all. Measured 2026-09-07 on Aspose.Page for Python, whose
    root is `aspose.page`: about seven namespace strings of its 570 public symbols reached this
    packet, and the job - rejected twice - cited `public_symbol:aspose.page.common`, a real
    directory of the repository, of exactly the shape of the only symbols it had been shown.
    """
    units = [
        {"id": fact.id, "type": fact.id.rsplit(".", 1)[-1], "text": fact.value}
        for fact in batch_units
    ]
    return {
        "repository": entry.repository,
        "inherited_units": units,
        "facts": _packet_fact_records(facts, manifest),
        "investigation": investigation,
        "sections": shell_packet(),
    }


def code_units_by_polarity(facts: FactsDocument, polarity: str) -> dict[str, str]:
    """Inherited code blocks whose example fact has ``polarity``, by unit ID, from the evidence."""
    units: dict[str, str] = {}
    for fact in facts.by_kind("example"):
        if fact.polarity != polarity:
            continue
        for evidence in fact.evidence:
            match = _UNIT_REFERENCE.search(evidence.detail or "")
            if match:
                units[match.group(1)] = fact.id
    return units


def contradicted_code_units(facts: FactsDocument) -> frozenset[str]:
    """Inherited code blocks whose example fact is CONTRADICTED, read from the example evidence."""
    return frozenset(code_units_by_polarity(facts, "CONTRADICTED"))


def contradicted_link_hrefs(facts: FactsDocument) -> dict[str, str]:
    """CONTRADICTED, non-renderer-owned ``link_target`` facts, by href (item 90).

    Keyed by ``fact.value`` - the href a ``link_target`` fact was extracted from - so a unit's
    own embedded links (``contradicted_embedded_links`` below) can be matched by the exact string
    a reader would click, the same identity ``extract_links`` already dedupes on. The three
    renderer-owned IDs (banner, homepage, enterprise) are excluded: they are never CONTRADICTED in
    practice, and citing one from this fold would misdirect ``composition/planning.py``'s
    ``_missing_links`` backstop, which treats any other ``link_target`` fact a ``VERIFIED_REWRITE``
    disposition cites as a real, renderable link it must add to the plan's own ``links``.
    """
    return {
        fact.value: fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "CONTRADICTED" and fact.id not in _RENDERER_OWNED_LINK_IDS
    }


def contradicted_embedded_links(unit_text: str, contradicted: Mapping[str, str]) -> set[str]:
    """Fact IDs of ``unit_text``'s own embedded links whose target is CONTRADICTED (item 90).

    A VERIFIED_PRESERVE/VERIFIED_MOVE unit renders its raw markdown verbatim, embedded links
    included, with no check of its own against what those links' own ``link_target`` facts say -
    so a link reconciliation already knows is broken reaches the sealed README unchanged, with no
    repair path. Matched by parsing the unit's own text with the same ``extract_links`` the
    evidence extractor used on the whole README, so a href only counts when it is genuinely
    embedded in this unit, never a substring coincidence.
    """
    if not contradicted:
        return set()
    return {
        contradicted[link.href] for link in extract_links(unit_text) if link.href in contradicted
    }


def rendering_fact_ids(section: str, facts: FactsDocument) -> list[str]:
    """The SUPPORTED facts a deterministic section renders for this repository, by ID."""
    if section == "banner":
        # README_CONTRACT.md row 3 renders exactly the verified illustration and homepage.
        pair = banner_target(facts.facts)
        return sorted(fact.id for fact in pair) if pair is not None else []
    kinds = RENDERING_FACT_KINDS.get(section, ())
    return sorted(
        fact.id for fact in facts.facts if fact.kind in kinds and fact.polarity == "SUPPORTED"
    )


# ---------------------------------------------------------------------------------------------
# TC-DSP-01 / G3-W08: a unit is dropped only when something true takes its place.
#
# Reconciliation runs before planning, so what it may claim is limited to what is decided before a
# plan exists. A SUPERSEDE_REDUNDANT is a claim that the destination already carries the unit; it
# stands only when that is provable here: the shell owns the unit's kind (a heading, a badge row,
# an HTML structure block), the destination is a deterministic section whose rendering inputs hold
# every fact the unit rests on, the destination is the Core API table and the unit lists only
# verified classes and enums, the unit is the lead paragraph the opening replaces, the destination
# owes an explicit disposition for it downstream (authoring.carried_units), or the destination is
# the diagram and the unit is one. Anything else - a section whose content the plan chooses - is
# not provable, so the unit stays a placing disposition and placement decides, with the plan in
# hand, whether it overlaps (placement.placements). Measured on the 30 sealed bundles
# (tests/components/readme/reconciliation/test_supersession_coverage.py): verified Quick Start,
# Installation, Dependencies and Key Capabilities units were dropped as "redundant" while no
# section carried them.
#
# OMIT_UNSUPPORTED is the other silent drop. It claims no fact supports the unit, so it fails when
# the unit's own example is verified or unresolved (unresolved is a deferral, never an omission) or
# when an uncited omission's text spells a SUPPORTED fact.
# ---------------------------------------------------------------------------------------------
# The unit kinds that carry content of their own. A heading, a badge row or an HTML structure block
# is owned by the shell (placement.renders_verbatim): it renders whatever the plan says, so
# superseding one never drops anything.
_CONTENT_KINDS = frozenset({"paragraph", "list", "table", "code_block", "blockquote"})
_NEUTRAL_FACT_KINDS = frozenset({"identity", "package", "inherited_unit"})
# The unit kinds each deterministic section can render. A kind outside the set carries content the
# section never prints, whatever facts the unit cites.
_SECTION_RENDERS: dict[str, frozenset[str]] = {
    "identity": frozenset({"heading"}),
    "badges": frozenset({"badge_row"}),
    "banner": frozenset({"badge_row"}),
    "navigation": frozenset({"heading", "list"}),
    "installation": frozenset({"heading", "paragraph", "list", "code_block", "blockquote"}),
    "dependencies": frozenset({"heading", "paragraph", "list", "table", "code_block"}),
    "third_party_notices": frozenset({"heading", "paragraph", "list"}),
    "license": frozenset({"heading", "paragraph"}),
}
_NAVIGATION_ITEM = re.compile(r"^\s*[-*+]\s*\[[^\]]+\]\(#[^)\s]*\)\s*$")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SYMBOL_SPAN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:(?:\.|::)[A-Za-z_][A-Za-z0-9_]*)*")
_VERSION_PIN = re.compile(r"(?<=\S)(?:==|>=|<=|~=|!=|>|<)[^\s]+|\s--version\s+\S+")
_PROMPT = re.compile(r"^\s*(?:[$>]\s+)")

# Gap reasons. A reason names why a disposition does not stand; the code that folds and the
# message the re-ask quotes are both keyed on it.
UNRENDERED_FACTS = "unrendered_facts"
UNRENDERED_COMMAND = "unrendered_command"
SECTION_RENDERS_OTHER_KINDS = "section_renders_other_kinds"
NOT_LEAD_PARAGRAPH = "not_lead_paragraph"
PLAN_DEPENDENT = "plan_dependent"
EXAMPLE_NOT_VERIFIED = "example_not_verified"
NO_DESTINATION = "no_destination"
API_MEMBERS = "api_members"
NOT_AN_API_LISTING = "not_an_api_listing"
NOT_A_DIAGRAM = "not_a_diagram"
NOT_NAVIGATION = "not_navigation"
OMIT_UNRESOLVED_EXAMPLE = "omit_unresolved_example"
OMIT_VERIFIED_EXAMPLE = "omit_verified_example"
OMIT_NAMES_SUPPORTED = "omit_names_supported"
UNCOVERED_SUPERSESSION = "uncovered_supersession"
SUPPORTED_OMISSION = "supported_omission"


@dataclass(frozen=True)
class CoverageGap:
    """One disposition that claims more than reconciliation can prove, and why."""

    unit_id: str
    disposition: str
    destination: str | None
    reason: str
    detail: str


def _unit_kind(unit_id: str) -> str:
    return unit_id.rsplit(".", 1)[-1]


def _is_mermaid(text: str) -> bool:
    first = text.splitlines()[0].strip().lower() if text.strip() else ""
    return first.startswith("```") and first[3:].strip() == "mermaid"


def _command_lines(text: str) -> list[str]:
    """The comparable command lines of a fenced block: prompts, comments, fences and version pins
    removed, whitespace collapsed, lower case - the form a rendered install command is held in."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = _PROMPT.sub("", raw).strip()
        if not line or line.startswith(("```", "#", "//")):
            continue
        lines.append(" ".join(_VERSION_PIN.sub("", line).split()).lower())
    return lines


@dataclass(frozen=True)
class _Coverage:
    """What reconciliation can prove a destination carries: derived from the facts alone."""

    facts: FactsDocument
    units: Mapping[str, Fact]
    kinds: Mapping[str, str]
    deterministic: frozenset[str]
    placeable: frozenset[str]
    rendered: Mapping[str, frozenset[str]]
    api_ids: frozenset[str]
    api_names: frozenset[str]
    namespaces: frozenset[str]
    api_members: frozenset[str]
    examples: Mapping[str, tuple[str, str]]
    commands: frozenset[str]
    lead: frozenset[str]
    commands_blocks: frozenset[str]

    def text(self, unit_id: str) -> str:
        unit = self.units.get(unit_id)
        return unit.value if unit is not None else ""

    def named(self, unit_id: str) -> frozenset[str]:
        return inherited_unit_named_symbols(self.facts, self.text(unit_id))


def _example_status(facts: FactsDocument) -> dict[str, tuple[str, str]]:
    """Each inherited code block's example fact: ``unit -> (polarity, example fact id)``."""
    status: dict[str, tuple[str, str]] = {}
    for fact in facts.by_kind("example"):
        for evidence in fact.evidence:
            match = _UNIT_REFERENCE.search(evidence.detail or "")
            if match:
                status[match.group(1)] = (fact.polarity, fact.id)
    return status


def _rendered_commands(facts: FactsDocument) -> frozenset[str]:
    """The command lines the Installation row can print (renderer._installation): the verified
    install command, and - when an example was executed - the ecosystem's clone-and-build lines
    and the verify line for a module an executed example imports."""
    lines: set[str] = set()
    for fact in facts.by_kind("install_command"):
        if fact.polarity == "SUPPORTED":
            lines.update(_command_lines(fact.value))
    ecosystem = next(
        (f.value for f in facts.by_kind("identity") if f.id == "identity:ecosystem"), ""
    )
    repository = next(
        (f.value for f in facts.by_kind("identity") if f.id == "identity:repository"), ""
    )
    try:
        spec = spec_for(ecosystem)
    except ConfigError:
        return frozenset(lines)
    executed = [fact for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"]
    install = next(
        (f for f in facts.by_kind("install_command") if f.id == spec.install_fact_id), None
    )
    kind = (install.attributes or {}).get("install_kind") if install is not None else None
    if executed and repository and kind not in {"source", "source_checkout"}:
        lines.update(_command_lines(spec.clone_and_build(repository, repository.split("/")[-1])))
    imported = [
        fact.value
        for fact in facts.by_kind("import_path")
        if fact.polarity == "SUPPORTED"
        and any(
            re.search(spec.import_pattern.format(module=re.escape(fact.value)), example.value)
            for example in executed
        )
    ]
    if imported and spec.verify_command:
        lines.update(_command_lines(spec.verify_command.format(module=max(imported, key=len))))
    return frozenset(lines)


def _lead_paragraphs(units: Sequence[Fact]) -> frozenset[str]:
    """The README's lead paragraph: the first paragraph directly under the H1. It is the one the
    opening replaces (README_CONTRACT.md row 4); a second paragraph carries claims of its own."""
    ordered = sorted(
        (u for u in units if _unit_kind(u.id) == "paragraph"),
        key=lambda u: (_unit_ordinal(u.id) is None, _unit_ordinal(u.id) or 0, u.id),
    )
    for unit in ordered:
        section = str((unit.attributes or {}).get("section") or "")
        if ">" not in section:
            return frozenset({unit.id})
    return frozenset()


def coverage_context(facts: FactsDocument) -> _Coverage:
    deterministic = frozenset(set(section_ids()) - placeable_section_ids())
    rendered = {section: frozenset(rendering_fact_ids(section, facts)) for section in deterministic}
    # The Installation row also prints the verify line for an imported module.
    rendered["installation"] = rendered["installation"] | frozenset(
        f.id for f in facts.by_kind("import_path") if f.polarity == "SUPPORTED"
    )
    api_ids = renderer_fact_ids("api_reference", facts)
    api_names: set[str] = set()
    for fact in facts.by_kind("public_symbol"):
        if fact.id in api_ids:
            api_names.update({fact.value, fact.value.rsplit(".", 1)[-1]})
    units = list(facts.by_kind("inherited_unit"))
    return _Coverage(
        facts=facts,
        units={u.id: u for u in units},
        kinds={f.id: f.kind for f in facts.facts},
        deterministic=deterministic,
        placeable=placeable_section_ids(),
        rendered=rendered,
        api_ids=api_ids,
        api_names=frozenset(api_names),
        namespaces=frozenset(
            f.id
            for f in facts.by_kind("public_symbol")
            if (f.attributes or {}).get("symbol_kind") == "module"
        ),
        api_members=frozenset(
            f.value.rsplit(".", 1)[-1]
            for f in facts.by_kind("public_symbol")
            if f.polarity == "SUPPORTED"
            and f.id not in api_ids
            and (f.attributes or {}).get("symbol_kind") != "module"
        ),
        examples=_example_status(facts),
        commands=_rendered_commands(facts),
        lead=_lead_paragraphs(units),
        commands_blocks=frozenset(command_block_units(facts)),
    )


def _table_first_column(text: str) -> str:
    """The first cell of each body row: what a table lists. The other cells describe it."""
    cells: list[str] = []
    for row in text.splitlines()[2:]:
        parts = row.strip().strip("|").split("|")
        if parts and parts[0].strip():
            cells.append(parts[0])
    return "\n".join(cells)


def _uncovered_members(text: str, members: frozenset[str], names: frozenset[str]) -> list[str]:
    """Verified members the unit spells in code spans that the Core API table does not print.

    A table lists classes and enums; a method, a function or a property is verified content the
    table omits, so a unit that spells one is not covered by it. A name no fact verifies is not
    here: dropping it publishes nothing unverified. A table is judged by what it lists (its first
    column), a list or a paragraph by every name it spells."""
    found: list[str] = []
    for span in _CODE_SPAN.findall(text):
        for token in _IDENTIFIER.findall(span):
            if token in members and token not in names and token not in found:
                found.append(token)
    return found


def _supersession_gap(
    unit_id: str, destination: str | None, cited: set[str], ctx: _Coverage
) -> tuple[str, str] | None:
    """Why ``destination`` cannot be shown to carry ``unit_id`` before a plan exists, or ``None``
    when it provably does."""
    kind = _unit_kind(unit_id)
    if kind not in _CONTENT_KINDS:
        return None
    text = ctx.text(unit_id)
    if kind == "code_block" and _is_mermaid(text):
        return None  # the renderer owns the one diagram
    status = ctx.examples.get(unit_id)
    if status is not None and kind == "code_block":
        polarity, example_id = status
        if polarity != "SUPPORTED":
            return (
                EXAMPLE_NOT_VERIFIED,
                f"its example {example_id} is {polarity}, so no section prints this block",
            )
        if destination in {"quick_start", "additional_examples"}:
            return None  # the plan owns every verified example (placement.renders_verbatim)
    if destination is None:
        return (NO_DESTINATION, "it names no section that carries the unit")
    if destination == "at_a_glance":
        return (NOT_A_DIAGRAM, "At a Glance holds one diagram and nothing else")
    named = ctx.named(unit_id)
    # A namespace names no member, and identity and package facts are on nearly every unit.
    content = sorted(
        fact_id
        for fact_id in cited | named
        if ctx.kinds.get(fact_id) is not None
        and ctx.kinds[fact_id] not in _NEUTRAL_FACT_KINDS
        and fact_id not in ctx.namespaces
    )
    if destination in ctx.deterministic:
        if kind not in _SECTION_RENDERS.get(destination, frozenset()):
            return (
                SECTION_RENDERS_OTHER_KINDS,
                f"{destination} renders from facts and prints no {kind.replace('_', ' ')}",
            )
        if destination == "navigation" and not all(
            _NAVIGATION_ITEM.match(line) for line in text.splitlines() if line.strip()
        ):
            return (NOT_NAVIGATION, "navigation lists the document's own sections only")
        # The navigation list is the document's own sections, whatever the reply cited for it.
        unrendered = (
            []
            if destination == "navigation"
            else [fact_id for fact_id in content if fact_id not in ctx.rendered[destination]]
        )
        if unrendered:
            return (
                UNRENDERED_FACTS,
                f"it rests on facts {destination} does not render: {', '.join(unrendered[:6])}",
            )
        if destination == "installation" and kind == "code_block":
            lines = _command_lines(text)
            missing = [line for line in lines if line not in ctx.commands]
            if not lines or missing:
                return (
                    UNRENDERED_COMMAND,
                    "installation prints the verified install command, not "
                    f"{(missing or ['this block'])[0]!r}",
                )
        return None
    if destination == "api_reference":
        if kind not in {"table", "list"}:
            # Only a listing is what the table prints. A paragraph states things (Cells-Rust
            # Project Structure: where the sources live) and a code block shows things, neither
            # of which the table carries, whatever classes they happen to cite.
            return (
                SECTION_RENDERS_OTHER_KINDS,
                f"the Core API table lists classes and enums, not a {kind.replace('_', ' ')}",
            )
        # A namespace a group of classes sits under names no member the table could omit.
        # A table is what its rows list; the facts it cites only group them.
        unrendered = (
            []
            if kind == "table"
            else [
                fact_id
                for fact_id in content
                if fact_id not in ctx.api_ids and fact_id not in ctx.namespaces
            ]
        )
        spelled = _table_first_column(text) if kind == "table" else text
        spans = [span.strip() for span in _CODE_SPAN.findall(spelled)]
        if not spans or not all(_SYMBOL_SPAN.fullmatch(span) for span in spans):
            # A listing of classes writes names. A tree of paths, a command or a signature in a
            # code span is something else (Cells-Rust Project Structure), not the table's content.
            return (NOT_AN_API_LISTING, "it lists paths or code, not the classes the table prints")
        unknown = _uncovered_members(spelled, ctx.api_members, ctx.api_names)
        if unrendered or unknown:
            what = unknown[:6] or unrendered[:6]
            return (
                API_MEMBERS,
                "the Core API table lists verified classes and enums only, not " + ", ".join(what),
            )
        return None
    if destination in _CARRY_SECTIONS and kind in {"paragraph", "list"}:
        return None  # authoring.carried_units makes the section cite or explicitly omit it
    if destination == "opening":
        if unit_id in ctx.lead:
            return None
        return (NOT_LEAD_PARAGRAPH, "the opening replaces the lead paragraph only")
    return (PLAN_DEPENDENT, f"what {destination} carries is chosen by the plan, after this stage")


def _omission_gap(unit_id: str, entry: Mapping[str, Any], ctx: _Coverage) -> tuple[str, str] | None:
    """Why an OMIT_UNSUPPORTED is not a failed support lookup, or ``None`` when it stands."""
    kind = _unit_kind(unit_id)
    if kind not in _CONTENT_KINDS or unit_id in ctx.commands_blocks:
        return None
    status = ctx.examples.get(unit_id)
    if status is not None and kind == "code_block":
        polarity, example_id = status
        if polarity == "UNRESOLVED":
            return (
                OMIT_UNRESOLVED_EXAMPLE,
                f"its example {example_id} is UNRESOLVED: facts neither support nor contradict "
                "it, which is a deferral",
            )
        if polarity == "SUPPORTED":
            return (OMIT_VERIFIED_EXAMPLE, f"its example {example_id} is verified")
        return None
    if entry.get("fact_ids") or kind in _PROSE_UNIT_KINDS:
        # A cited reason stands; an uncited prose omission is placement_errors' own rule.
        return None
    named = sorted(ctx.named(unit_id))
    if named:
        return (OMIT_NAMES_SUPPORTED, "its text spells SUPPORTED facts: " + ", ".join(named[:6]))
    return None


def _narrow_citations(entry: Mapping[str, Any], ctx: _Coverage) -> list[str]:
    """The facts a disposition cites that name something narrower than "this repository": an
    identity or package citation is on nearly every unit and shows no shared subject."""
    return sorted(
        fact_id
        for fact_id in entry.get("fact_ids") or []
        if ctx.kinds.get(fact_id) not in {"identity", "package"}
    )


_WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{2,}")
_FILLER = frozenset(
    {"the", "and", "for", "with", "this", "that", "are", "see", "from", "into", "use", "using"}
    | {"can", "you", "your", "has", "have", "was", "will", "its", "also", "all", "not", "but"}
)
# Prose a placed unit renders verbatim and placement judges by overlap. A code block is content
# nothing else renders (placement.placements never drops one as overlap), a heading is the
# shell's: neither claims a subject nor is covered by another unit's claim.
_RESTATABLE_KINDS = frozenset({"paragraph", "list", "table", "blockquote"})
_RESTATED_SHARE = 0.8
_RESTATED_MIN_WORDS = 3
Claims = dict[tuple[str, str], set[str]]


def _subject_words(text: str) -> set[str]:
    """The words a unit's prose is about: lower case, filler dropped, paths and names whole."""
    return {word.rstrip("./-").lower() for word in _WORD.findall(text)} - _FILLER


def _restates(entry: Mapping[str, Any], destination: str, claims: Claims, ctx: _Coverage) -> bool:
    """Whether the unit only repeats what placed units in ``destination`` already say.

    A shared citation alone is not a shared subject: a reply that cites the same few symbols on
    every unit of a section (Cells-Rust API Reference: five class symbols on all 28 units;
    Slides-.NET: three namespace symbols on every one) made the first unit claim them and
    superseded the rest, dropping a project-structure tree and a members list as "duplicates"
    of a heading. A unit restates earlier ones when it shares a narrow citation with them and
    at least ``_RESTATED_SHARE`` of its own prose vocabulary already appears in the units that
    made those claims."""
    unit = str(entry.get("unit_id", "?"))
    if _unit_kind(unit) not in _RESTATABLE_KINDS:
        return False
    shared = [
        claims[destination, fact_id]
        for fact_id in _narrow_citations(entry, ctx)
        if (destination, fact_id) in claims
    ]
    words = _subject_words(ctx.text(unit))
    if not shared or len(words) < _RESTATED_MIN_WORDS:
        return False
    earlier = set().union(*shared)
    return len(words - earlier) <= (1 - _RESTATED_SHARE) * len(words)


def _claim(entry: Mapping[str, Any], destination: str, claims: Claims, ctx: _Coverage) -> None:
    """Record that ``entry`` places its prose in ``destination`` for each narrow fact it cites."""
    unit = str(entry.get("unit_id", "?"))
    if _unit_kind(unit) not in _RESTATABLE_KINDS:
        return
    words = _subject_words(ctx.text(unit))
    for fact_id in _narrow_citations(entry, ctx):
        claims.setdefault((destination, fact_id), set()).update(words)


def _judge(
    output: Mapping[str, Any], ctx: _Coverage
) -> Iterator[tuple[dict[str, Any], tuple[str, str] | None]]:
    """Each disposition with why it claims more than the stage can prove, or ``None``.

    A supersession, or a placement aimed at a section that renders from facts (and so can only
    supersede), is judged by what its destination provably carries - or by an earlier placement
    in the same section that already carries every fact it rests on. An omission is judged by
    whether a support lookup failed. A consumer may rewrite the entry it was handed; the claims
    later units are measured against follow the entry as it stands afterwards."""
    claims: Claims = {}
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        disposition = entry.get("disposition")
        destination = entry.get("destination_section")
        cited = set(entry.get("fact_ids") or [])
        gap: tuple[str, str] | None = None
        if disposition == "SUPERSEDE_REDUNDANT" or (
            disposition in PLACING and destination in ctx.deterministic
        ):
            gap = _supersession_gap(unit, destination, cited, ctx)
            if (
                gap is not None
                and disposition == "SUPERSEDE_REDUNDANT"
                and destination in ctx.placeable
                and gap[0] in {PLAN_DEPENDENT, NOT_LEAD_PARAGRAPH, API_MEMBERS, UNRENDERED_FACTS}
                and _restates(entry, destination, claims, ctx)
            ):
                gap = None
        elif disposition == "OMIT_UNSUPPORTED":
            gap = _omission_gap(unit, entry, ctx)
        yield entry, gap
        destination = entry.get("destination_section")
        if entry.get("disposition") in PLACING and destination in ctx.placeable:
            _claim(entry, destination, claims, ctx)


def coverage_findings(output: Mapping[str, Any], facts: FactsDocument) -> list[CoverageGap]:
    """Every disposition in ``output`` that claims more than reconciliation can prove.

    Read-only; ``normalize`` folds what it can, ``placement_errors`` refuses the rest."""
    return [
        CoverageGap(
            str(entry.get("unit_id", "?")),
            str(entry.get("disposition")),
            entry.get("destination_section"),
            gap[0],
            gap[1],
        )
        for entry, gap in _judge(output, coverage_context(facts))
        if gap is not None
    ]


def _prune_incidental_coverage(output: dict[str, Any], ctx: _Coverage) -> None:
    """Drop the class and enum citations that would make placement discard a unit as covered.

    ``placement.placements`` drops a placed unit whose citations intersect what its section
    renders - a drop, not a placement - and the Core API table renders every verified class and
    enum. A reply that cites the same few class symbols on every API Reference unit (Cells-Rust:
    Project Structure, whose text names none of them; the Detailed Member Reference lists, which
    spell methods the table does not print) therefore loses those units while the table covers
    nothing they say. A class the unit does not state is not evidence for it, so a placed API
    Reference unit the Core API table does not cover keeps only the citations that carry it."""
    for entry in output.get("dispositions", []):
        if entry.get("disposition") not in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}:
            continue
        unit = str(entry.get("unit_id", "?"))
        if entry.get("destination_section") != "api_reference" or _unit_kind(unit) not in {
            "paragraph",
            "list",
            "table",
        }:
            continue
        cited = set(entry.get("fact_ids") or [])
        if not cited & ctx.api_ids:
            continue
        if _supersession_gap(unit, "api_reference", cited, ctx) is not None:
            entry["fact_ids"] = sorted(cited - ctx.api_ids)


def _fold_uncovered(output: dict[str, Any], facts: FactsDocument, ctx: _Coverage) -> None:
    """Fold every disposition that claims more than reconciliation can prove into the one it can.

    A supersession whose destination cannot be shown to carry the unit stays a placing
    disposition at that destination when the shell can hold the unit there (the plan decides,
    with the plan in hand, whether it overlaps what the section renders anyway). A supersession of
    a code block whose example is not verified is the placing fold's own answer: deferred while
    UNRESOLVED, omitted while CONTRADICTED. An omission of such a block while its example is
    UNRESOLVED is a deferral, not an omission: the facts neither support nor contradict it.
    Nothing here drops a unit; what cannot be folded is left for ``placement_errors``."""
    for entry, gap in _judge(output, ctx):
        if gap is None:
            continue
        unit = str(entry.get("unit_id", "?"))
        cited = set(entry.get("fact_ids") or [])
        if entry.get("disposition") == "OMIT_UNSUPPORTED":
            if gap[0] == OMIT_UNRESOLVED_EXAMPLE:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
                entry["fact_ids"] = sorted(cited | {ctx.examples[unit][1]})
        elif gap[0] == NOT_A_DIAGRAM:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
        elif gap[0] == EXAMPLE_NOT_VERIFIED:
            polarity, example_id = ctx.examples[unit]
            entry["disposition"] = (
                "OMIT_UNSUPPORTED" if polarity == "CONTRADICTED" else "DEFER_UNRESOLVED"
            )
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {example_id})
        elif entry.get("disposition") == "SUPERSEDE_REDUNDANT" and (
            entry.get("destination_section") in ctx.placeable
        ):
            entry["disposition"] = "VERIFIED_PRESERVE"


def normalize(
    output: dict[str, Any], facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> list[str]:
    """Fold placements deterministic code cannot honour into the disposition it can, in place.

    A placement into a deterministic section becomes a supersession citing the facts that
    section renders. A placed code block whose example is UNRESOLVED, or a placement into the
    Enterprise Edition section while the policy carries no verified target, is deferred: the
    candidate cannot render either at this revision, so "verified" would be false. A code block
    placed into At a Glance is superseded by the renderer's own diagram. Returns the units that
    cannot be folded because the section renders nothing here.
    """
    deterministic = set(section_ids()) - placeable_section_ids()
    coverage = coverage_context(facts)
    unresolved = code_units_by_polarity(facts, "UNRESOLVED")
    contradicted = code_units_by_polarity(facts, "CONTRADICTED")
    contradicted_links = contradicted_link_hrefs(facts)
    commands = command_block_units(facts)
    units_by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    install_ids = sorted(
        f.id for f in facts.by_kind("install_command") if f.polarity == "SUPPORTED"
    )
    build_ids = sorted(f.id for f in facts.by_kind("build_test_asset") if f.polarity == "SUPPORTED")
    absent = {
        section for section, holds in section_conditions(facts, policy).items() if holds is False
    }
    errors: list[str] = []
    # First, so a supersession the stage cannot prove becomes the placement it should have been
    # and then meets every placement rule below (a contradicted link, an absent section).
    _fold_uncovered(output, facts, coverage)
    for entry in output.get("dispositions", []):
        unit = str(entry.get("unit_id", "?"))
        destination = entry.get("destination_section")
        disposition = entry.get("disposition")
        cited = set(entry.get("fact_ids") or [])
        if disposition in PLACING and unit in unresolved:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {unresolved[unit]})
            continue
        # G7-W12 follow-up (a): an uncited DEFER_UNRESOLVED on a command block is the same
        # defect as its OMIT_UNSUPPORTED (the re-ask template sends the model to DEFER when it
        # cannot cite, and it relabels units the rejection never named: 3D-.NET 067, Page-Python
        # 015, PDF-.NET 018), so it folds by the same rule. Not a deferral that already has a
        # reason: a citation, or an example that is UNRESOLVED or CONTRADICTED (BC-03 withholds
        # an unexecuted block, and keeping it would publish it).
        restated = (
            disposition == "DEFER_UNRESOLVED"
            and not cited
            and unit not in unresolved
            and unit not in contradicted
        )
        if (
            (disposition == "OMIT_UNSUPPORTED" or restated)
            and unit in commands
            and (install_ids or build_ids)
        ):
            # A command block is the maintainers' own command, not a claim: an install command
            # is rendered by the Installation row, any other block is kept where it was - but
            # only where Development and Testing actually renders. Measured 2026-09-06: Words
            # and Cells for .NET each have install_command:dotnet SUPPORTED and zero
            # build_test_asset facts, so a non-install command (`dotnet test`) routed here by
            # install_ids alone claimed a section whose own condition is false, and the
            # candidate died on the same placement the branch below already knows to defer.
            block = units_by_id[unit]
            heading = " ".join(e.detail or "" for e in block.evidence)
            installing = "> Installation" in heading or bool(_INSTALL_COMMAND.search(block.value))
            # A block the Installation row prints may be superseded by it; any other command
            # (a build from a clone, a second package manager) is content nothing else renders.
            installing = installing and (
                _supersession_gap(unit, "installation", cited, coverage) is None
            )
            if installing and install_ids:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "installation"
                entry["fact_ids"] = sorted(cited | set(install_ids))
            elif "development_testing" in absent:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "VERIFIED_PRESERVE"
                entry["destination_section"] = "development_testing"
                entry["fact_ids"] = sorted(cited | set(build_ids or install_ids))
            continue
        if disposition in PLACING and unit in contradicted:
            # The example failed at this revision: the block is never placed (README_CONTRACT.md
            # section 3), so the placement folds into an omission citing the contradiction.
            entry["disposition"] = "OMIT_UNSUPPORTED"
            entry["destination_section"] = None
            entry["fact_ids"] = sorted(cited | {contradicted[unit]})
            continue
        if (
            disposition in {"VERIFIED_PRESERVE", "VERIFIED_MOVE"}
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            # item 90: a VERIFIED_PRESERVE/VERIFIED_MOVE unit renders its raw markdown verbatim,
            # embedded links included, with no check of its own against those links' own
            # link_target facts - so a link reconciliation already knows is CONTRADICTED reaches
            # the sealed README with no repair path. Fold to VERIFIED_REWRITE (the existing
            # fold-not-reject pattern, items 16/17): the unit's substance still stands, but S6
            # re-authors the wording from facts instead of copying the broken link through.
            # heading/badge_row units are excluded (the shell owns them entirely - the banner
            # fold just below is their own dedicated path when they cite the banner). The
            # CONTRADICTED fact itself is never added to fact_ids - composition/planning.py's
            # _missing_links backstop treats any non-renderer-owned link_target citation on a
            # VERIFIED_REWRITE disposition as a real link to surface, and this one is exactly the
            # opposite of that.
            unit_fact = units_by_id.get(unit)
            bad_links = (
                contradicted_embedded_links(unit_fact.value, contradicted_links)
                if unit_fact is not None
                else set()
            )
            if bad_links:
                entry["disposition"] = "VERIFIED_REWRITE"
                entry["fact_ids"] = sorted(cited - bad_links)
                continue
        if disposition in PLACING and (
            destination == "banner" or (unit.endswith(".badge_row") and BANNER_FACT_ID in cited)
        ):
            # Row 3 is shell-rendered from the verified illustration and homepage facts: a
            # placed banner row is superseded by it, or deferred while either is unresolved.
            if banner_target(facts.facts) is None:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            elif unit.rsplit(".", 1)[-1] not in _CONTENT_KINDS:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "banner"
                entry["fact_ids"] = sorted(cited | {BANNER_FACT_ID, HOMEPAGE_FACT_ID})
            # The banner prints the verified illustration and homepage; any other unit placed
            # there is content it never prints, so it is not called redundant (placement_errors
            # then refuses a destination the shell cannot hold).
            continue
        if disposition in PLACING and destination == "enterprise_relationship":
            # Row 18 is the shell's closing paragraph of Scope and Limitations, rendered from
            # the live target; inherited Enterprise prose is superseded by it, and anything
            # else placed there (a banner row, an image) has no row yet and is deferred. The
            # destination stays enterprise_relationship, the reconciler's own choice: the shell
            # prints "These limitations don't apply to [...]" itself, and the authored context
            # sentence of that section is the only place the paragraph's "which adds ..."
            # substance can render, so it is the section that owes the unit a citation or a
            # reasoned omission (authoring.carried_units). Rewriting it to scope_limitations
            # (the pre-G7-W15 fold) made S6 owe the unit to a section that may not name the
            # Enterprise Edition and may not cite what only the other section can state.
            if enterprise_target(facts.facts) is None or unit.rsplit(".", 1)[-1] not in {
                "paragraph",
                "heading",
            }:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "enterprise_relationship"
                entry["fact_ids"] = sorted(cited | {ENTERPRISE_FACT_ID})
            continue
        if (
            disposition in PLACING
            and destination == "opening"
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
            and unit in coverage.lead
        ):
            # README_CONTRACT.md row 4: the opening is the one authored paragraph the plan and
            # investigation own, so an inherited paragraph placed there can only repeat it
            # (the re-asked reconciler preserved the old opening beside the new one); the
            # rewrite covers it. Only the lead paragraph is that opening: a second paragraph
            # states claims of its own (Slides-.NET 004: who the library is for), so it stays
            # placed and placement overlap decides.
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "opening"
            continue
        if (
            disposition in PLACING
            and destination == "api_reference"
            and unit.endswith(".table")
            and _supersession_gap(unit, "api_reference", cited, coverage) is None
        ):
            # README_CONTRACT.md row 14: the Core API table is deterministic from the verified
            # symbol facts, so an inherited API table placed here is covered by it, never
            # rendered beside it (the re-asked reconciler placed two such tables on the canary).
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "api_reference"
            continue
        if (
            disposition in PLACING
            and destination == "at_a_glance"
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            # README_CONTRACT.md row 6: the section is exactly one Mermaid fence and nothing
            # else, so a diagram placed there is covered by the diagram when it cites facts. Any
            # other content is not carried by a diagram, and an uncited unit has nothing to say
            # it is: both are deferred for the owner.
            covered = bool(cited) and _supersession_gap(unit, destination, cited, coverage) is None
            entry["disposition"] = "SUPERSEDE_REDUNDANT" if covered else "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if (
            disposition == "SUPERSEDE_REDUNDANT"
            and destination in absent
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            # Nothing covers the unit when the section that would cannot appear at this
            # revision, so the unit is deferred for the owner rather than silently dropped.
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if (
            disposition in PLACING
            and destination in absent
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            # README_CONTRACT.md section 3: an excluded destination re-routes or fails closed
            # naming the unit. The section's condition does not hold at this revision, so no
            # plan can include it and no re-ask can place it there; the unit is deferred for the
            # owner rather than dropped, exactly as a supersession by an absent section is one
            # branch above. Measured 2026-09-06: Aspose.Cells and Aspose.Words for .NET each
            # routed build and test snippets into development_testing, whose condition is false
            # because neither repository records a build_test_asset - the re-ask failed on the
            # same units and the whole candidate died on a placement no plan could honour.
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if destination not in deterministic:
            continue
        ids = rendering_fact_ids(destination, facts)
        if not ids:
            # A required deterministic section (owner "D") is never excluded, so it is never in
            # `absent` - but "required" only means the section always appears, not that it
            # always has content. Measured 2026-09-06 on Aspose.Slides for .NET: `installation`
            # renders nothing because the package is genuinely unpublished (§31), and the same
            # placement survived one re-ask unchanged - the model cannot invent evidence a
            # section lacks any more than it can invent a section a plan excludes.
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
            continue
        if _supersession_gap(unit, destination, cited, coverage) is not None:
            # The section renders from facts and does not render this unit's content: it is not
            # redundant. Left as the reply wrote it, placement_errors names why (and the last
            # attempt's recover defers it) instead of this fold dropping it.
            continue
        entry["disposition"] = "SUPERSEDE_REDUNDANT"
        entry["fact_ids"] = sorted(cited | set(ids))
    # G4-W17 arrival item 98 (BCPY-02): a placeable section (never folded above - that branch
    # is deterministic sections only) can still receive two independent PLACING dispositions
    # for the same subject, one preserved and one moved in from elsewhere, each citing the
    # same non-trivial fact - a real, repair-unreachable duplication once composed, since
    # neither repair/rounds.py nor repair/targeted.py has any awareness of a VERIFIED_MOVE or
    # VERIFIED_PRESERVE disposition to act on. Measured on BarCode-Python: two adjacent
    # sentences both pointing at the same examples/ directory, one VERIFIED_PRESERVE'd in
    # additional_examples and one VERIFIED_MOVE'd there from a separate section, both citing
    # the same build_test_asset fact. Mirrors this file's own Core-API-table dedup precedent
    # just above (a structural shape rather than a citation, but the same "the first claim on
    # a destination stands, a later one is superseded by it" policy) - a second run over the
    # now-final destination_section of every entry (including one this loop itself just moved,
    # such as the OMIT_UNSUPPORTED-command branch's VERIFIED_PRESERVE into development_testing
    # above), in document order, so the first PLACING claim on a (section, fact) pair always
    # wins and is never itself downgraded.
    claims: Claims = {}
    for entry in output.get("dispositions", []):
        destination = entry.get("destination_section")
        if entry.get("disposition") not in PLACING or destination not in placeable_section_ids():
            continue
        # TC-DSP-01: identity/package citations are on nearly every unit (unit_checks' own
        # `neutral` set treats them the same way), and a shared narrow citation alone is not a
        # shared subject, so a later unit is superseded only when it restates what earlier placed
        # units already say (_restates).
        if _restates(entry, destination, claims, coverage):
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            continue
        _claim(entry, destination, claims, coverage)
    # G4-W17 arrival item 110 (LANE-B-W14R6-F1): a placed inherited_unit's own sentence can name
    # several symbols the S4 job's own sampled fact_ids never cited - measured on Aspose.3D for
    # TypeScript, where inherited_unit:077.list named a dozen not-implemented symbols in one
    # verbatim sentence and its disposition cited only 7, leaving the rest with no path into S6's
    # own citation set even though composition/authoring.py's split mechanism (proven by that same
    # sentence's own FileSystem bullet) can surface any of them once offered one. Every SUPPORTED
    # public_symbol/import_path fact the unit's own text spells is added here, deterministically,
    # after every fold and dedup above (so it can never influence which destination a unit landed
    # on or trigger a spurious duplicate-subject fold) - the full set a single sampled call's own
    # coverage should never have been the ceiling on.
    for entry in output.get("dispositions", []):
        if entry.get("disposition") not in PLACING:
            continue
        unit_fact = units_by_id.get(str(entry.get("unit_id", "?")))
        if unit_fact is None or unit_fact.polarity != "SUPPORTED":
            continue
        named = inherited_unit_named_symbols(facts, unit_fact.value)
        if not named:
            continue
        entry["fact_ids"] = sorted(set(entry.get("fact_ids") or []) | named)
    _prune_incidental_coverage(output, coverage)
    return errors


def _unit_ordinal(unit_id: str) -> int | None:
    """``unit_id``'s own leading block ordinal, or ``None`` if it is not an ``inherited_unit`` ID
    of that shape."""
    match = _UNIT_ORDINAL.match(unit_id)
    return int(match.group(1)) if match else None


def coordinate_neighbor_promises(
    dispositions: dict[str, Any], facts: FactsDocument
) -> dict[str, Any]:
    """Defer a placed unit whose own text promises the block immediately following it in the
    original document when that neighbor's own disposition does not survive to render anywhere.

    BC-10 coherence-gap, ``aspose-slides-foss/Aspose.Slides-FOSS-for-.NET``
    (``docs/DECISION_LOG.md`` 2026-09-17 14:14 UTC, corroborated 2026-09-24 10:14 UTC):
    ``inherited_unit:033.paragraph`` ("Three namespaces cover every sample on this page, and
    each sample below assumes all three:") was disposed ``VERIFIED_PRESERVE`` while
    ``inherited_unit:034.code_block`` (the sample the colon promises) fell to
    ``OMIT_UNSUPPORTED`` (its own ``example`` fact CONTRADICTED) - each disposition independently
    correct on its own narrow grounds, but the preserved sentence then stood alone in the
    composed document, naming content the candidate never delivers (BC-10
    ``REJECT_PRESENTATION``, "moving key factual content out of its original context").

    Root cause: every ``source_reconciliation`` batch (``reconciliation_batches()``) is checked
    by ``reconcile_checks``/``normalize()`` independently of every other batch, by design (PHASE0/G
    - a per-entry check, deliberately no cross-entry logic, so a bounded batch call is exactly as
    strict as the old whole-document one was). A unit disposed in one batch call has no way to
    see whether a *different* unit - possibly reconciled in a different batch call - that its own
    text depends on survived. This function runs once, after ``merge_dispositions()`` folds every
    batch into one flat document, the one point a neighbor's own final disposition is visible
    regardless of which batch produced it.

    Detection is syntactic, not semantic (rule 13/14: a free-text semantic-similarity check is
    unreachable for a deterministic one): a ``paragraph``/``list`` unit whose own text ends with a
    colon is a forward reference to whatever block comes immediately next in
    ``evidence/facts/inherited.py``'s own ordinal numbering - the same class of literal, syntactic
    cue ``_INSTALL_COMMAND`` and the ``"> Installation"`` heading match already use elsewhere in
    this file. Only an immediately-following *code block* is checked (the concrete, measured
    shape); a promise that names a non-adjacent unit (docs/DECISION_LOG.md's own 2026-09-24
    10:14 UTC entry names a second, harder, non-adjacent case on this same repository) needs its
    own mechanism and is out of this fix's narrow scope. A neighbor that folds to
    ``SUPERSEDE_REDUNDANT`` keeps its promise (the content it named still renders, just from a
    deterministic section or an earlier placement) and is left alone; only ``OMIT_UNSUPPORTED``
    and ``DEFER_UNRESOLVED`` - genuinely nothing rendered - break it.

    No existing check is weakened: this only narrows what a colon-ending unit's own
    ``VERIFIED_PRESERVE``/``VERIFIED_MOVE``/``VERIFIED_REWRITE``/``CORRECT_WITH_EVIDENCE`` may
    still claim once its own promise is known to be broken, mirroring every other coordination
    fold this file already applies (deferred for the owner, never silently dropped).
    """
    units_by_id = {fact.id: fact for fact in facts.by_kind("inherited_unit")}
    entries_by_id = {
        str(entry.get("unit_id", "?")): entry for entry in dispositions.get("dispositions", [])
    }
    for entry in dispositions.get("dispositions", []):
        if entry.get("disposition") not in PLACING:
            continue
        unit = str(entry.get("unit_id", "?"))
        if unit.rsplit(".", 1)[-1] not in {"paragraph", "list"}:
            continue
        unit_fact = units_by_id.get(unit)
        if unit_fact is None or not unit_fact.value.rstrip().endswith(":"):
            continue
        ordinal = _unit_ordinal(unit)
        if ordinal is None:
            continue
        neighbor = entries_by_id.get(f"inherited_unit:{ordinal + 1:03d}.code_block")
        if neighbor is None or neighbor.get("disposition") not in {
            "OMIT_UNSUPPORTED",
            "DEFER_UNRESOLVED",
        }:
            continue
        entry["disposition"] = "DEFER_UNRESOLVED"
        entry["destination_section"] = None
    return dispositions


UNCITED_PROSE_OMIT = "uncited_prose_omit"
# The unit kinds an uncited OMIT_UNSUPPORTED is refused for: prose. A heading, an HTML block, a
# code block or a table is not refused by this check (it is shell-owned, command or markup).
_PROSE_UNIT_KINDS = frozenset({"paragraph", "list"})


def uncited_omit_candidates(unit_text: str, facts: FactsDocument) -> list[str]:
    """SUPPORTED fact IDs the refused unit's own text already spells, sorted - a deterministic
    candidate list the ``uncited_prose_omit`` re-ask can name, so the model has somewhere
    concrete to look rather than only being told to "try harder" (#1008's repair round).

    Diagnosis (PDF-TypeScript, ``inherited_unit:014.list``/``016.list``): the model omitted a
    unit with no citation while real SUPPORTED facts it never cited were sitting in its own
    sentence the whole time (``parsecontentstream``, ``document.save``,
    ``saveoptions.compressed``/``encrypt``/``incremental``/``linearized``/``streamfilter``,
    ``savedocxfile``, ``parsehtml``, ``parsemarkdown``). ``placement_errors`` correctly refused
    the omission; the re-ask gave the model only the unit's text back, never pointing at its own
    unused evidence. This reuses ``inherited_unit_named_symbols`` - the same verbatim-token match
    ``coordinate_neighbor_promises``'s item-110 fold already applies to a *placed* unit's
    citations - against the refused unit's text instead, conservatively: a ``public_symbol``/
    ``import_path`` fact counts only when its own value is spelled, as a whole identifier-shaped
    token, somewhere in the unit's running prose or an inline code span (no fuzzy or partial
    matching). Returning no candidates is a true negative, not a failure: most uncited omissions
    name nothing any fact spells, and those keep the plain, candidate-free re-ask unchanged.
    """
    return sorted(inherited_unit_named_symbols(facts, unit_text))


_OMISSION_ACTION = {
    OMIT_UNRESOLVED_EXAMPLE: "Choose DEFER_UNRESOLVED: an example the facts neither support nor "
    "contradict is withheld and listed, never called unsupported",
    OMIT_VERIFIED_EXAMPLE: "Supersede it into quick_start or additional_examples (the plan "
    "renders every verified example there) or place it; do not omit a verified example",
    OMIT_NAMES_SUPPORTED: "Cite the facts that support it and place it, or choose "
    "DEFER_UNRESOLVED if no fact settles its claim",
}
_QUOTE_LIMIT = 600


def _coverage_errors(
    gaps: Sequence[CoverageGap], unit_text: Mapping[str, str], placeable: frozenset[str]
) -> list[str]:
    """One typed, repairable refusal per disposition that claims more than the stage can prove,
    quoting the unit's exact text (the one re-ask can only act on what it is shown)."""
    errors: list[str] = []
    for gap in gaps:
        kind = _unit_kind(gap.unit_id).replace("_", " ")
        text = json.dumps(unit_text.get(gap.unit_id, "(text not in the facts)"), ensure_ascii=False)
        if len(text) > _QUOTE_LIMIT:
            text = text[:_QUOTE_LIMIT] + "..."
        if gap.disposition == "OMIT_UNSUPPORTED":
            errors.append(
                f"{gap.unit_id}: {SUPPORTED_OMISSION}: OMIT_UNSUPPORTED claims no fact supports "
                f"this {kind}, but {gap.detail}. {_OMISSION_ACTION[gap.reason]}; the unit's exact "
                f"text is {text}"
            )
            continue
        errors.append(
            f"{gap.unit_id}: {UNCOVERED_SUPERSESSION}: {gap.disposition} treats "
            f"{gap.destination or 'no section'} as carrying this {kind}, but {gap.detail}. A unit "
            "is superseded only when something that renders takes its place: place it "
            "(VERIFIED_PRESERVE or VERIFIED_MOVE) into a section the shell can hold "
            f"({', '.join(sorted(placeable))}) or choose DEFER_UNRESOLVED; the unit's exact text "
            f"is {text}"
        )
    return errors


def placement_errors(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """Why the dispositions may not be used, beyond schema and binding; empty when they hold.

    An OMIT_UNSUPPORTED on a paragraph or list must cite at least one fact ID as its reason (the
    facts that show the claim unsupported), or be placed instead. A prose omission with no citation
    is the 15%-wrong omission class measured on the sealed candidates (2026-10-06): the reason is
    what lets the decision be checked at all. Each refusal is typed (``uncited_prose_omit``) and
    quotes the unit's exact text, so the one re-ask can act on it. When the unit's own text already
    spells a SUPPORTED fact's identifier, the refusal also names that fact ID as a candidate
    (``uncited_omit_candidates``) - the model still decides whether it truly supports the claim;
    this never assigns a disposition on its own.
    """
    placeable = placeable_section_ids()
    contradicted = contradicted_code_units(facts)
    commands = command_block_units(facts)
    unit_text = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    build_facts = sorted(
        fact.id
        for fact in facts.facts
        if fact.kind in {"build_test_asset", "install_command"} and fact.polarity == "SUPPORTED"
    )
    errors: list[str] = []
    for entry in output.get("dispositions", []):
        unit = entry.get("unit_id", "?")
        disposition = entry.get("disposition")
        destination = entry.get("destination_section")
        cited = entry.get("fact_ids") or []
        if (
            disposition == "OMIT_UNSUPPORTED"
            and not cited
            and unit.rsplit(".", 1)[-1] in _PROSE_UNIT_KINDS
        ):
            kind = unit.rsplit(".", 1)[-1]
            raw_text = unit_text.get(unit, "(text not in the facts)")
            text = json.dumps(raw_text, ensure_ascii=False)
            candidates = uncited_omit_candidates(raw_text, facts)
            candidate_clause = (
                " This unit's own text already spells these SUPPORTED facts: "
                f"{', '.join(candidates)}. Cite whichever of them actually support the claim "
                "(SUPERSEDE_REDUNDANT or CORRECT_WITH_EVIDENCE), or OMIT_UNSUPPORTED with a "
                "cited reason if none of them truly apply."
                if candidates
                else ""
            )
            errors.append(
                f"{unit}: {UNCITED_PROSE_OMIT}: OMIT_UNSUPPORTED on a {kind} needs at least one "
                "fact ID that shows the claim unsupported, or the unit must be placed in a section "
                f"the shell can hold; the unit's exact text is {text}.{candidate_clause} Cite the "
                "supporting fact IDs or place the unit; do not omit it without a cited reason"
            )
        if disposition == "OMIT_UNSUPPORTED" and unit in commands and build_facts:
            # A command block is the maintainers' own build, test, or install command, not a
            # claim a fact could refute; with build or install facts recorded it is kept.
            errors.append(
                f"{unit}: a command block is never OMIT_UNSUPPORTED while build or install "
                f"facts exist ({', '.join(build_facts)}); choose VERIFIED_PRESERVE into "
                "development_testing, or SUPERSEDE_REDUNDANT by installation for an install "
                "command"
            )
        if disposition in PLACING:
            if destination not in placeable:
                errors.append(
                    f"{unit}: {disposition} needs a destination the shell can hold "
                    f"({', '.join(sorted(placeable))}); got {destination!r}"
                )
            if unit in contradicted:
                errors.append(f"{unit}: its example is CONTRADICTED and cannot be placed")
        elif disposition == "SUPERSEDE_REDUNDANT":
            # Superseded by a deterministic section's rendering (cited by fact ID after the
            # fold) or by the plan's own content for a placeable section: the exclusivity of
            # README_CONTRACT.md section 3 from the reconciler's side.
            if destination is None and not cited:
                errors.append(
                    f"{unit}: SUPERSEDE_REDUNDANT names the section whose content renders or "
                    "covers the unit in destination_section, or cites at least one fact ID"
                )
        elif destination is not None:
            errors.append(f"{unit}: {disposition} takes no destination; got {destination!r}")
        if disposition == "CORRECT_WITH_EVIDENCE" and not cited:
            errors.append(f"{unit}: CORRECT_WITH_EVIDENCE needs at least one fact ID as evidence")
    # What normalize folds on its own is not refused: a supersession into a section the shell can
    # hold becomes a placement, and an omitted unresolved example a deferral. What is left is a
    # claim only a different reply, or the last attempt's deferral, can correct.
    unfolded = [
        gap
        for gap in coverage_findings(output, facts)
        if not (gap.disposition == "SUPERSEDE_REDUNDANT" and gap.destination in placeable)
        and gap.reason != OMIT_UNRESOLVED_EXAMPLE
    ]
    errors.extend(_coverage_errors(unfolded, unit_text, placeable))
    return errors


# What a recovered omission says about itself. The cause is recorded in the rationale because the
# disposition record has no other field (DispositionsV1 is closed: additionalProperties false, and
# the manifest's schema is part of every S4 request digest). deferrals.py's NO_EVIDENCE_EITHER_WAY
# reads the opening words and still checks the facts, so the statement is not taken on trust.
RECOVERED_OMIT_RATIONALE = (
    "No fact cited for this omission; held as unresolved for the owner. Reason given: "
)
_RATIONALE_LIMIT = _RATIONALE_MAX_CHARS


def _uncited_prose_omit(entry: Mapping[str, Any]) -> bool:
    """The exact shape ``placement_errors`` refuses as ``uncited_prose_omit``."""
    return (
        entry.get("disposition") == "OMIT_UNSUPPORTED"
        and not entry.get("fact_ids")
        and str(entry.get("unit_id", "?")).rsplit(".", 1)[-1] in _PROSE_UNIT_KINDS
    )


RECOVERED_COVERAGE_RATIONALE = "Not provably carried by the section named; held for the owner. "


def _recover_uncovered(output: dict[str, Any], facts: FactsDocument) -> bool:
    """Fold, in place, every disposition still claiming more than the stage can prove into the
    deferral that says so. Returns whether anything changed.

    Only reached for a reply that survived the one re-ask with such a claim (``recover=`` runs on
    the last attempt only). Deferring is the only fold that asserts nothing: the unit is listed
    for the owner and never rendered, so the claim "something else carries this" is withdrawn
    rather than repeated. A verified example the reply omitted is the one exception: the plan
    renders every verified example, so it is superseded into Additional Examples citing it."""
    ctx = coverage_context(facts)
    changed = False
    for entry, gap in _judge(output, ctx):
        if gap is None:
            continue
        unit = str(entry.get("unit_id", "?"))
        cited = set(entry.get("fact_ids") or [])
        reason = RECOVERED_COVERAGE_RATIONALE + str(entry.get("rationale") or "").strip()
        entry["rationale"] = reason[:_RATIONALE_LIMIT]
        example = {ctx.examples[unit][1]} if unit in ctx.examples else set()
        if gap[0] == OMIT_VERIFIED_EXAMPLE:
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "additional_examples"
        else:
            entry["disposition"] = "DEFER_UNRESOLVED"
            entry["destination_section"] = None
        entry["fact_ids"] = sorted(cited | example)
        changed = True
    return changed


def recover_uncited_prose_omits(
    output: dict[str, Any], facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for ``source_reconciliation``'s final rejected attempt only
    (``recover=``, ``core/llm/jobs.py``): a prose omission still uncited after the one re-ask
    becomes an explicit ``DEFER_UNRESOLVED`` instead of failing the transaction, and a
    disposition still claiming more than the stage can prove (TC-DSP-01: a supersession no
    rendering covers, an omission of a unit a fact supports) is deferred the same way.

    Diagnosis (G7-W12 follow-up, Aspose.PSD-FOSS-for-.NET ``inherited_unit:018.paragraph``, "the
    package is not published to NuGet yet", 2026-10-10): both attempts kept the unit as an
    uncited ``OMIT_UNSUPPORTED``, so the S4 job failed closed before BC-05 could judge anything.
    The re-ask had already named the unit and its exact text; a model that will not cite is not
    helped by a third ask. The one honest reading of "omitted, and no fact says why" is the
    prompt's own definition of ``DEFER_UNRESOLVED``: a claim the facts neither support nor
    contradict, listed for the owner and never rendered. Nothing is published either way; the
    deferral is the version that stays visible.

    Safe only when the deferral hides nothing the facts already cover. A unit whose own text spells
    a SUPPORTED fact (``uncited_omit_candidates``) is not unresolved: the evidence is in its
    sentence, so the omission should have cited it, and this declines. Declining is all or
    nothing - one unsafe omission returns ``None`` rather than a partial fix the checks would
    reject anyway - and so is a unit the facts do not hold (its text cannot be examined).

    Never accepted on this function's say-so: ``run_job`` re-validates the returned copy through
    the schema, the unit binding and ``reconcile_checks`` exactly as it does any reply, so a reply
    with another defect is still rejected, and the model's own reply is never edited in place.
    The model's stated reason is kept after the cause, within the rationale's length limit.
    """
    entries = output.get("dispositions")
    if not isinstance(entries, list):
        return None
    uncited = [entry for entry in entries if isinstance(entry, dict) and _uncited_prose_omit(entry)]
    unit_text = {fact.id: fact.value for fact in facts.by_kind("inherited_unit")}
    for entry in uncited:
        text = unit_text.get(str(entry.get("unit_id")))
        if text is None or uncited_omit_candidates(text, facts):
            return None
    recovered = copy.deepcopy(output)
    for entry in recovered["dispositions"]:
        if not _uncited_prose_omit(entry):
            continue
        reason = str(entry.get("rationale") or "").strip()
        room = _RATIONALE_LIMIT - len(RECOVERED_OMIT_RATIONALE)
        if len(reason) > room:
            reason = reason[: room - 3].rstrip() + "..."
        entry["disposition"] = "DEFER_UNRESOLVED"
        entry["destination_section"] = None
        entry["fact_ids"] = []
        entry["rationale"] = RECOVERED_OMIT_RATIONALE + reason
    # An entry deferred above is no longer an omission, so the coverage fold sees what is left.
    folded = _recover_uncovered(recovered, facts)
    return recovered if uncited or folded else None


def reconcile_checks(
    output: dict[str, Any], facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> list[str]:
    """The job's own checks for the runner: normalise, then judge what remains."""
    return normalize(output, facts, policy) + placement_errors(output, facts)


def summarize(output: dict[str, Any]) -> Counter[str]:
    return Counter(entry["disposition"] for entry in output.get("dispositions", []))


def write_dispositions(output: dict[str, Any], path: Path) -> str:
    """Write the accepted dispositions as deterministic JSON; returns the SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
