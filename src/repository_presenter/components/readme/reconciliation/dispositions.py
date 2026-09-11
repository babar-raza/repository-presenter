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
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    placeable_section_ids,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.planning import section_conditions
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
)
from repository_presenter.components.readme.evidence.facts.product_pages import (
    BANNER_FACT_ID,
    ENTERPRISE_FACT_ID,
    HOMEPAGE_FACT_ID,
    banner_target,
    enterprise_target,
)
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


_RECONCILIATION_BATCH = 40
# PHASE0/G: units per source_reconciliation call - the same "too big for one call, split by
# natural unit, never reorder" shape section_authoring's own _type_batches() already proves
# (composition/authoring.py's own _TYPE_BATCH, same value). Calibrated against the real,
# currently-failing case: aspose-cells-foss/Aspose.Cells-FOSS-for-Rust genuinely truncates its
# single-call reconciliation output at max_output_tokens=32000 once RC-06 grows it to 91 units
# (measured ~351 tokens/unit of output - the fix is output-side, not input-side: the packet
# itself was never close to a size limit, its own required *reply* was). 40 units/batch keeps a
# batch's own worst-case output (40 x 351 =~ 14,040 tokens) comfortably under budget with real
# headroom, not a guess (docs/DECISION_LOG.md records the full measurement this rests on).


def reconciliation_batches(facts: FactsDocument) -> list[tuple[str, list[Fact]]]:
    """Every inherited unit, split into fixed-size batches in document (ordinal) order - one
    ``(batch_id, units)`` pair per ``source_reconciliation`` call this round makes.

    Ordinal order, not grouped by ``.section``: a batch boundary may occasionally fall inside one
    heading's own units, but preserves the document's own unit ordering exactly, which
    ``merge_dispositions()`` and every downstream reader already assume - grouping by section
    first would need to interleave document order back in afterward for no real benefit, since
    ``reconcile_checks`` (below) judges each disposition independently of its neighbours anyway.
    """
    units = list(facts.by_kind("inherited_unit"))
    return [
        (
            f"reconciliation#{index // _RECONCILIATION_BATCH + 1}",
            units[index : index + _RECONCILIATION_BATCH],
        )
        for index in range(0, len(units), _RECONCILIATION_BATCH)
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
    """Every ID a disposition in this batch may cite, sorted: the packet's own fact records, the
    facts the accepted investigation cites (the prompt lets the job copy those one by one, and
    the investigation travels in the packet, so each is an ID the job can actually see), and this
    batch's own inherited units. Nothing the packet never showed is in it (section 27.2 RC1), so
    an UNRESOLVED fact is absent - ``normalize`` adds one by code where a rule calls for it."""
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
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    dispositions = schema["properties"]["dispositions"]
    citable = citable_fact_ids(facts, manifest.manifest, batch_units, investigation)
    if citable:
        dispositions["items"]["properties"]["fact_ids"]["items"] = {
            "type": "string",
            "enum": citable,
        }
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
    unresolved = code_units_by_polarity(facts, "UNRESOLVED")
    contradicted = code_units_by_polarity(facts, "CONTRADICTED")
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
        if disposition == "OMIT_UNSUPPORTED" and unit in commands and (install_ids or build_ids):
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
        if disposition in PLACING and (
            destination == "banner" or (unit.endswith(".badge_row") and BANNER_FACT_ID in cited)
        ):
            # Row 3 is shell-rendered from the verified illustration and homepage facts: a
            # placed banner row is superseded by it, or deferred while either is unresolved.
            if banner_target(facts.facts) is None:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "banner"
                entry["fact_ids"] = sorted(cited | {BANNER_FACT_ID, HOMEPAGE_FACT_ID})
            continue
        if disposition in PLACING and destination == "enterprise_relationship":
            # Row 18 is the shell's closing paragraph of Scope and Limitations, rendered from
            # the live target; inherited Enterprise prose is superseded by it, and anything
            # else placed there (a banner row, an image) has no row yet and is deferred.
            if enterprise_target(facts.facts) is None or unit.rsplit(".", 1)[-1] not in {
                "paragraph",
                "heading",
            }:
                entry["disposition"] = "DEFER_UNRESOLVED"
                entry["destination_section"] = None
            else:
                entry["disposition"] = "SUPERSEDE_REDUNDANT"
                entry["destination_section"] = "scope_limitations"
                entry["fact_ids"] = sorted(cited | {ENTERPRISE_FACT_ID})
            continue
        if (
            disposition in PLACING
            and destination == "opening"
            and unit.rsplit(".", 1)[-1] not in _SHELL_OWNED
        ):
            # README_CONTRACT.md row 4: the opening is the one authored paragraph the plan and
            # investigation own, so an inherited paragraph placed there can only repeat it
            # (the re-asked reconciler preserved the old opening beside the new one); the
            # rewrite covers it.
            entry["disposition"] = "SUPERSEDE_REDUNDANT"
            entry["destination_section"] = "opening"
            continue
        if disposition in PLACING and destination == "api_reference" and unit.endswith(".table"):
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
            # else, so a unit placed there is covered by the diagram when it cites facts and
            # deferred when it cites none.
            entry["disposition"] = "SUPERSEDE_REDUNDANT" if cited else "DEFER_UNRESOLVED"
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
        entry["disposition"] = "SUPERSEDE_REDUNDANT"
        entry["fact_ids"] = sorted(cited | set(ids))
    return errors


def placement_errors(output: dict[str, Any], facts: FactsDocument) -> list[str]:
    """Why the dispositions may not be used, beyond schema and binding; empty when they hold."""
    placeable = placeable_section_ids()
    contradicted = contradicted_code_units(facts)
    commands = command_block_units(facts)
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
    return errors


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
