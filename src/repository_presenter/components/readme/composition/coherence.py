"""Stage S8: the coherence pass - revise LLM-owned units only, once, then re-render.

The pass is one or more section_authoring calls in coherence mode: each call sees the rendered
document and every authored unit for context, and returns exactly one batch's own units with their
section and slot unchanged and their text possibly revised. The guard holds each returned unit to
its own section's rules (slots exactly once, citations inside the section's set, no Markdown,
identifiers that are fact values), so the pass can only change prose the LLM already owned.
Deterministic blocks are untouched by construction: the renderer is a pure function and only unit
texts change.

PDFPY-03 (docs/DECISION_LOG.md 2026-09-17 09:18 UTC, corroborated 2026-09-24 14:20 UTC on a second
repository): a single call asking for every LLM-owned unit back at once has no bound on its own
completion size - unlike authoring.py's own per-task ``section_authoring`` calls, which are always
scoped to one section's (or one type-batch's) own slots. Once a document carries enough units (47
on PDF-Python, more on Font-Python), the reply alone exceeds the shared ``max_output_tokens=8000``
cap and the whole transaction aborts with ``finish_reason: length`` before any README or validation
is produced - PDF-Python and Font-Python have both been blocked on exactly this.
``coherence_batches`` splits the pass into fixed-size batches, mirroring the precedent
``authoring.py::_type_batches`` and
``reconciliation/dispositions.py::reconciliation_batches`` already set for the identical class of
problem: several bounded calls instead of one unbounded one, never splitting one section's own
slots across two calls (a section's own internal coherence is still judged in one call).

Cross-batch consistency is not silently dropped: every batch call still receives the *entire*
current rendered document and *every* current LLM-owned unit (``coherence_packet``'s own
``existing_units``/``rendered_document`` fields are unscoped, independent of which tasks are
passed) - only the schema-forced *reply* is narrowed to the batch's own units. The caller
(``repair/rounds.py``) also re-renders the document after each batch and feeds the updated
document into the next batch's packet, so a later batch judges its own section's coherence against
a document that already reflects every earlier batch's revisions, not the stale pre-pass text.

G3-W05 (``docs/DEFECT_INDEX.md`` ``composition.coherence.inherited_diagram_content_loss``): this
call site had no ``recover=`` at all until this item, and no deterministic check for the specific
shape two independently sealed candidates' own review caught - a capability or diagram-adjacent
unit losing a specific, named, fact-backed detail during exactly this pass. ``coherence_checks``'
own new ``existing_units`` parameter lets it see each unit's pre-coherence text/fact_ids alongside
the reply's post-coherence ones (``coherence_content_loss_errors``); ``recover_coherence_content_
loss`` reverts only the specific unit(s) found to have silently dropped a cited fact's own
content, never the whole batch and never a rewrite - see both functions' own docstrings.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    section_spellings,
    slot_records,
    uncarried_units,
    unit_checks,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.core.facts import FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import LoadedManifest
from repository_presenter.core.registry.models import RegistryEntry

COHERENCE_SECTION = "all"
_SPELLING_CAP = 120
# PDFPY-03: units per coherence-batch call. The manifest's own ``text`` field comment (item 75,
# prompts/section_authoring.yaml) records the longest unit ever measured across every sealed
# bundle at 972 characters (~250 tokens with its ``fact_ids``/JSON overhead) against a maxLength
# ceiling of 2200 set well above it for headroom, not as a realistic average. Sizing the batch off
# the real measured maximum rather than the abstract schema ceiling: 16 units x ~250 tokens worst
# case =~ 4000, half the shared 8000-token completion cap, with room to spare even if every unit in
# a batch happened to hit the longest length ever recorded at once. Large enough that the project's
# own small/typical candidates (on the order of 10-20 LLM-owned units) still complete in one
# coherence call exactly as before; small enough that a document the size of the ones that actually
# truncated (47+ units, PDF-Python and Font-Python) still splits into several bounded calls.
_COHERENCE_BATCH_UNITS = 16


def coherence_packet(
    entry: RegistryEntry,
    readme: str,
    units_document: dict[str, Any],
    tasks: list[SectionTask],
    facts: FactsDocument,
) -> dict[str, Any]:
    """The packet for the one coherence call: the document, the units, and their closed facts."""
    by_id = {fact.id: fact for fact in facts.facts}
    # Batch-authored type descriptions are per-type sentences, not narrative: the coherence
    # pass neither receives nor returns them, so its output stays within the budget.
    tasks = [task for task in tasks if not task.is_batch]
    accepted_ids = coherence_citable_ids(tasks)
    slots = [f"{task.section_id}/{slot}" for task in tasks for slot in task.slots]
    spellings = section_spellings(accepted_ids, facts)[:_SPELLING_CAP]
    return {
        "repository": entry.repository,
        "product_name": product_name(entry),
        "mode": "coherence",
        "section_id": COHERENCE_SECTION,
        "objective": (
            "Revise the LLM-owned units, once, so the whole document reads as one coherent "
            "developer journey: no repetition across sections, one voice, each unit still true to "
            "its facts. Return every unit with its section and slot exactly as given, revised or "
            f"not. Units to return, each exactly once: {', '.join(slots)}. Identifiers the prose "
            f"may spell, exactly as written: {', '.join(spellings)}; any other API name, member, "
            "attribute, or parameter is rejected."
        ),
        "slots": [
            record
            for task in tasks
            for record in slot_records(task.slots, task.slot_facts, task.slot_titles)
        ],
        "accepted_facts": [
            {"id": fact_id, "kind": by_id[fact_id].kind, "value": by_id[fact_id].value}
            for fact_id in accepted_ids
            if fact_id in by_id
        ],
        "do_not_claim": bounded_records(
            facts,
            ["format", "install_command", "link_target", "example"],
            ("CONTRADICTED", "UNRESOLVED"),
        ),
        "length_budget": "each unit within its own section's budget; never longer than before",
        "rendered_document": readme,
        "existing_units": [
            unit
            for unit in units_document.get("units", [])
            if not str(unit.get("slot", "")).startswith("type:")
        ],
    }


def coherence_citable_ids(tasks: list[SectionTask]) -> list[str]:
    """Every fact ID any unit the coherence call returns may legitimately cite: the union of
    every authored section task's own accepted set - exactly the ids ``coherence_packet`` already
    shows the job as ``accepted_facts`` - batch/type tasks excluded as they carry no coherence
    unit at all.

    G4-W17 arrival item 123: this is the shared, per-call enum ``reconciliation_schema``'s own
    ``citable_fact_ids`` already builds for its per-batch ``fact_ids``, not a per-unit
    ``prefixItems`` restriction like ``authoring_schema``'s - the coherence call, like a
    reconciliation batch, returns many different units in one reply, so one decoder constraint
    covering everything any of them could legitimately cite is what bounds the runaway risk;
    each unit's own narrower, section-scoped set is still enforced post-hoc by
    ``coherence_checks``' per-section ``unit_checks`` call, exactly as it already was.
    """
    tasks = [task for task in tasks if not task.is_batch]
    ids: list[str] = []
    for task in tasks:
        ids.extend(fact_id for fact_id in sorted(task.accepted_ids))
    return list(dict.fromkeys(ids))


def coherence_batches(tasks: list[SectionTask]) -> list[tuple[str, list[SectionTask]]]:
    """Every LLM-owned section, grouped into fixed-size coherence batches in document (task) order
    - one ``(batch_id, group)`` pair per coherence call this round makes (PDFPY-03).

    Greedy accumulation, never splitting one task's own slots across two batches: a section's
    coherence is judged as a whole in one call, exactly as ``coherence_checks``' per-task
    ``unit_checks`` already expects. A single task whose own slot count alone exceeds
    ``_COHERENCE_BATCH_UNITS`` still gets its own, larger batch rather than being split - no
    section on record carries anywhere near that many slots (the portfolio's own largest,
    ``key_capabilities``, is bounded well under it), so this is a safety fallback, not the normal
    case. Batch/type tasks are excluded - they carry no coherence unit at all, same as
    ``coherence_citable_ids``.
    """
    tasks = [task for task in tasks if not task.is_batch]
    batches: list[list[SectionTask]] = []
    current: list[SectionTask] = []
    current_units = 0
    for task in tasks:
        if current and current_units + len(task.slots) > _COHERENCE_BATCH_UNITS:
            batches.append(current)
            current = []
            current_units = 0
        current.append(task)
        current_units += len(task.slots)
    if current:
        batches.append(current)
    return [(f"coherence#{index + 1}", group) for index, group in enumerate(batches)]


def coherence_batch_units(
    existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> list[dict[str, Any]]:
    """The subset of ``existing_units`` one batch's own ``tasks`` own - exactly the units that
    batch's own coherence call must return, once ``coherence_batches`` splits the pass into
    several calls. Matched by (section, slot), the same key ``apply_coherence`` already uses."""
    slots = {(task.section_id, slot) for task in tasks for slot in task.slots}
    return [unit for unit in existing_units if (unit.get("section"), unit.get("slot")) in slots]


def coherence_schema(
    manifest: LoadedManifest, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any]:
    """The section_authoring schema specialised for the one coherence call: exactly as many units
    back as were given, and each unit's own ``fact_ids`` limited to what any of them could
    legitimately cite.

    G4-W17 arrival item 75 (lane F F23, Email-.NET; lane B LANE-B-W14R2-F1, Cells-TS):
    section_authoring's per-task calls already get an exact ``units`` count from
    ``authoring_schema`` (the plan's own slot count), but the coherence call - one call returning
    every LLM-owned unit in the document at once, the largest single section_authoring reply by
    construction - used the bare manifest schema with no bound of its own beyond ``minItems: 1``.
    Nothing here changes ``text``'s or ``omitted``'s bounds; those come from the manifest schema
    this deep-copies, so the same ``maxLength`` fix covers this call too.

    G4-W17 arrival item 123: the units count bound above says nothing about any unit's own
    ``fact_ids`` - the one call site among section_authoring's five shapes (S3, S4's per-entry
    calls, S5, S6's per-task calls) that never got the per-kind bound treatment
    ``authoring_schema``/``reconciliation_schema`` already apply, and structurally the single
    largest section_authoring reply in the pipeline (every LLM-owned unit in the document, one
    call). A count bound alone still lets a runaway completion spend its whole budget on
    well-formed but wrong IDs (item 121's own reasoning), so ``fact_ids`` now carries the same
    enum-of-citable-IDs treatment the other two functions apply, via ``coherence_citable_ids``.
    """
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    units = schema["properties"]["units"]
    citable = coherence_citable_ids(tasks)
    if citable:
        units["items"]["properties"]["fact_ids"]["items"] = {"type": "string", "enum": citable}
    else:
        units["items"]["properties"]["fact_ids"] = {"type": "array", "maxItems": 0}
    count = len(existing_units)
    if count:
        units["minItems"] = count
        units["maxItems"] = count
    return schema


def coherence_checks(
    output: dict[str, Any],
    tasks: list[SectionTask],
    facts: FactsDocument,
    name: str,
    existing_units: list[dict[str, Any]] | None = None,
    prior_omitted: Sequence[Mapping[str, Any]] = (),
) -> list[str]:
    """Every section's rules, applied to the units the pass returned for that section, plus
    (when ``existing_units`` - this batch's own pre-coherence units, G3-W05) a check that the
    revision did not silently drop named content the pre-coherence unit carried
    (``coherence_content_loss_errors`` below).

    ``prior_omitted`` is the explicit omissions S6 ``section_authoring`` already accepted
    (``{"section", "fact_id", "reason"}`` each). This pass revises units only - it has no omission
    channel of its own - so a must-carry unit S6 validly omitted with a reason (README_CONTRACT.md:
    cite it or omit it with a reason) must still count as dispositioned here; judging coherence with
    an empty omission list rejected every such unit as "missing", whatever the reply said
    (aspose-slides-foss/Aspose.Slides-FOSS-for-Java, G7-W15: S6 omitted 035/081/083/085/095 with
    reasons, then both coherence attempts were refused for exactly those five)."""
    errors: list[str] = []
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in output.get("units", []):
        by_section.setdefault(str(unit.get("section", "")), []).append(unit)
    tasks = [task for task in tasks if not task.is_batch]
    known = {task.section_id for task in tasks}
    for section in sorted(set(by_section) - known):
        errors.append(f"units name a section the plan did not author: {section}")
    # This one call returns every section's units at once, so a must-carry unit's own citation is
    # visible here even when it landed in a different section than its disposition's own
    # destination_section (authoring.py::carried_unit_errors' own docstring, confirmed live on
    # aspose-psd-foss/Aspose.PSD-FOSS-for-.NET, 2026-10-08) - named by the first section found
    # citing it, so the carry check below can tell a real cross-section move from a true silent
    # drop and name exactly where the content went.
    cited_elsewhere: dict[str, str] = {}
    for section, section_units in by_section.items():
        for unit in section_units:
            for fact_id in unit.get("fact_ids", []):
                cited_elsewhere.setdefault(fact_id, section)
    for task in tasks:
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        omitted = [
            item
            for item in prior_omitted
            if isinstance(item, Mapping) and item.get("section") == task.section_id
        ]
        errors.extend(
            unit_checks(
                {"units": owned, "omitted": omitted},
                task,
                facts,
                name,
                elsewhere_cited=cited_elsewhere,
            )
        )
    if existing_units is not None:
        errors.extend(coherence_content_loss_errors(output.get("units", []), existing_units, facts))
    return errors


# docs/DEFECT_INDEX.md `composition.coherence.inherited_diagram_content_loss` (project/state.yaml
# G3-W05): two independent, corroborated sightings (both 2026-09-27) - aspose-slides-foss's Java
# and .NET candidates - each had independent review catch an inherited Mermaid diagram or
# capability list losing specific, named capability/structure/input-output detail the prior
# version carried, with no deterministic check standing in the gap at all: whether the loss was
# ever caught depended entirely on whether that draw's own review sample happened to notice it,
# and a `targeted_repair` round on the finding did not reliably restore what was lost either (both
# sightings survived one repair round with the rejection still standing).
#
# Scoped to what the coherence pass can actually change - a unit's own text and fact_ids, matched
# by its unchanged section/slot (the pass's own contract already requires both back exactly as
# given, revised or not) - never a comparison against the ORIGINAL upstream README itself, which
# would need a much weaker, free-text comparison with no fact-level precision this late in
# composition and no access to the source document at all at this stage. A citation a unit itself
# carried immediately before this pass and no longer carries immediately after it, whose own
# SUPPORTED value's distinctive content is nowhere in the revised text either, is exactly "named or
# structural content present before is missing after" - a fact-grounded signal, not a guess at
# paraphrase quality. A dropped citation whose value's own content still appears in the revised
# text (re-cited under different wording, or folded into a still-cited sibling claim with the same
# content) is not flagged - only silent, untraceable loss is.
_CONTENT_TOKEN = re.compile(r"[a-z0-9][a-z0-9+./_-]{2,}")

# docs/DECISION_LOG.md (this item's own live verification, aspose-slides-foss/Aspose.Slides-FOSS-
# for-Java, 2026-09-30/10-01): a first version of this check with no kind exclusion fired live
# against every `documentation_resources` link unit and `scope_limitations/scope` - the model had
# correctly shortened several link sentences that each repeated the full "org.aspose:aspose-
# slides-foss version 26.8.0 for Java 21" boilerplate (exactly the "no repetition across sections"
# improvement coherence's own objective asks for), dropping the `identity:*`/`package:*`
# provenance citations that boilerplate existed only to justify - never a named capability, format,
# or diagram element a reader would notice missing. ``planning.py``'s own
# ``recover_uncited_capability_titles`` already treats ``identity``/``package`` facts as "neutral"
# background the prose does not need to spell out explicitly (`_product_name`'s own `neutral` set,
# items 1010/1038) - the same exemption applies here, for the same reason: these two kinds back
# ambient context (what repository, what revision, what package coordinate), not a distinguishable
# claim a human would read as "missing" the way a dropped capability or format is.
_NEUTRAL_FACT_KINDS = frozenset({"identity", "package"})


def _content_tokens(text: str) -> frozenset[str]:
    """The lower-cased, three-or-more-character tokens ``text`` spells - a coarse but cheap
    proxy for "this text still mentions this content", good enough to tell a genuine restatement
    (in different words, same distinctive tokens) from silent removal (none of them left)."""
    return frozenset(_CONTENT_TOKEN.findall(text.lower()))


def _dropped_untraced_fact_ids(
    unit: dict[str, Any], existing: dict[str, Any], facts: FactsDocument
) -> list[str]:
    """The pre-coherence fact IDs ``unit`` no longer cites whose own SUPPORTED value has left no
    trace (none of its distinctive tokens) in ``unit``'s revised text - shared by
    ``coherence_content_loss_errors`` (what to reject) and ``recover_coherence_content_loss``
    (what to restore), so the two can never drift apart on what counts as "lost". A dropped
    ``identity``/``package`` fact (``_NEUTRAL_FACT_KINDS``) is never counted - ambient provenance,
    not named content a reader would notice missing."""
    by_id = {fact.id: fact for fact in facts.facts}
    existing_ids = {str(i) for i in existing.get("fact_ids", [])}
    revised_ids = {str(i) for i in unit.get("fact_ids", [])}
    dropped = sorted(existing_ids - revised_ids)
    if not dropped:
        return []
    revised_tokens = _content_tokens(str(unit.get("text", "")))
    untraced: list[str] = []
    for fact_id in dropped:
        fact = by_id.get(fact_id)
        if fact is None or fact.polarity != "SUPPORTED" or fact.kind in _NEUTRAL_FACT_KINDS:
            continue
        value_tokens = _content_tokens(fact.value)
        if value_tokens and value_tokens & revised_tokens:
            continue  # the dropped citation's own content still reads somewhere in the text
        untraced.append(fact_id)
    return untraced


def coherence_content_loss_errors(
    output_units: list[dict[str, Any]],
    existing_units: list[dict[str, Any]],
    facts: FactsDocument,
) -> list[str]:
    """A coherence revision that drops a previously-cited fact with none of its own content left
    in the revised text, per unit (matched by its unchanged section/slot) - see the module-level
    note above for the exact mechanism and its scope."""
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    by_id = {fact.id: fact for fact in facts.facts}
    errors: list[str] = []
    for unit in output_units:
        key = (str(unit.get("section")), str(unit.get("slot")))
        existing = existing_by_key.get(key)
        if existing is None:
            continue
        for fact_id in _dropped_untraced_fact_ids(unit, existing, facts):
            fact = by_id.get(fact_id)
            value = fact.value if fact is not None else fact_id
            kind = fact.kind if fact is not None else "fact"
            errors.append(
                f"{key[0]}/{key[1]}: coherence revision drops the previously-cited {kind} "
                f"{fact_id!r} and none of its own content ({value!r}) remains in the revised "
                "text - a named capability, format, or structural detail the prior version "
                "carried must not be silently dropped during coherence"
            )
    return errors


def recover_coherence_content_loss(
    output: dict[str, Any], *, existing_units: list[dict[str, Any]], facts: FactsDocument
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call (``recover=``,
    ``core/llm/jobs.py``) - never called on a first attempt, so the model's own one universal
    re-ask is always tried first exactly as before; a unit ``coherence_checks`` would still reject
    for an unrelated reason is unaffected, since ``run_job`` re-validates the corrected output
    through the real ``coherence_checks`` - this content-loss check included - before ever
    accepting it.

    ``docs/DEFECT_INDEX.md`` ``composition.coherence.inherited_diagram_content_loss``;
    ``project/state.yaml`` G3-W05: S8 coherence had no ``recover=`` at all before this (confirmed
    by direct code read) - a final rejection here always raised ``JobError`` outright. The one
    safe, "never invent" correction available for THIS shape: a unit whose own revision dropped a
    previously-cited fact with no trace of its value left in the text is reverted, in full, to its
    own pre-coherence text and fact_ids - restoring exactly what the pass already had and knew to
    be correct, never rewriting it into something new - while every other unit's own genuine
    revision (one that did not drop untraced content) is left exactly as the model returned it.

    Returns ``None`` when nothing needed reverting (nothing to try), never a no-op copy of
    ``output``.
    """
    units = output.get("units")
    if not isinstance(units, list):
        return None
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    changed = False
    for unit in units:
        if not isinstance(unit, dict):
            continue
        key = (str(unit.get("section")), str(unit.get("slot")))
        existing = existing_by_key.get(key)
        if existing is None:
            continue
        if _dropped_untraced_fact_ids(unit, existing, facts):
            unit["text"] = existing.get("text", unit.get("text"))
            existing_fact_ids = existing.get("fact_ids")
            unit["fact_ids"] = (
                list(existing_fact_ids)
                if isinstance(existing_fact_ids, list)
                else unit.get("fact_ids", [])
            )
            changed = True
    return output if changed else None


# docs/DEFECT_INDEX.md composition.authoring.superseded_unit_not_carried: a second, narrower
# recurrence after #298 (NORMALISATION_VERSION item 30, commit 5cffa343) - confirmed live,
# aspose-3d-foss/Aspose.3D-FOSS-for-.NET and aspose-email-foss/Aspose.Email-FOSS-for-.Net,
# 2026-10-08 (independently reproduced here by direct call against the real coherence_checks,
# never the live transcript alone): #298 made coherence_checks *name* the real section a moved
# must-carry unit landed in, but gave the S8 pass no deterministic way to *fix* it when the
# model's own one-shot re-ask still fails to - and it reliably does, for this one shape. The
# obligation moves TO scope_limitations while the model's prose keeps citing the identical
# fact_id FROM enterprise_relationship - whose own task.accepted_ids never included it in the
# first place (authoring.py's section_selections only ever grants scope_limitations/
# development_testing the carried_units() a disposition supersedes into them; no section a unit
# merely ends up quoted in gains the fact by that quoting alone). So a model that moves the
# citation this way is rejected TWICE in the same call - carried_unit_errors' own "it was instead
# cited in enterprise_relationship" (the gap #298 named) AND unit_checks' own "cites facts outside
# this section's set" on the enterprise_relationship unit itself (confirmed directly: both errors
# fire together, every time, for this exact shape - see test_coherence.py's own reproduction).
# Both are satisfiable at once (a compliant reply exists and passes cleanly: cite the fact in
# scope_limitations, drop it from enterprise_relationship's own unit) - this is not a structural
# deadlock between the carry rule and any other rule (plans/idea.md's edition-naming rule
# included: scope_limitations is free to name "Enterprise Edition" outright, and
# enterprise_relationship's own duplicate-name guard never even inspects fact_ids) - but the one
# universal re-ask does not reliably reach that compliant reply within its own budget, and S8 had
# no deterministic last resort for this specific shape at all, unlike the sibling content-loss
# gap G3-W05 already closed with recover_coherence_content_loss above.
#
# The fix is scoped to the earliest stage that can see the mistake deterministically: S8 coherence
# is the only call site that can turn an already-correct S6 carry (S6's own unit_checks enforces
# carried_unit_errors with no elsewhere_cited before coherence ever runs, so every must_carry
# fact_id is guaranteed cited-or-validly-omitted in existing_units by construction) into a broken
# one; reconciliation's own destination_section call is untouched (scope_limitations really is
# this unit's disposed home; enterprise_relationship simply also finds the same substance
# relevant, which coherence_checks' own docstring already treats as fine so long as the disposed
# section still carries it) and the carry/outside-section checks themselves are untouched (neither
# is wrong; the gap is a missing recovery, never a wrong gate).
def recover_coherence_carried_units(
    output: dict[str, Any], *, existing_units: list[dict[str, Any]], tasks: list[SectionTask]
) -> dict[str, Any] | None:
    """Last-resort correction for S8 coherence's own ``run_job`` call, alongside
    ``recover_coherence_content_loss``: a must-carry fact_id (``SectionTask.must_carry``) that the
    pre-coherence document already carried correctly in its own disposed section, but this
    revision no longer carries there - because a unit elsewhere now cites it instead, which that
    other section's own ``accepted_ids`` never granted it to begin with.

    Two deterministic, "never invent" corrections, mirroring ``recover_coherence_content_loss``'s
    own full-unit-revert precedent exactly:

    1. The disposed section's own pre-coherence unit that carried the fact_id (matched by its
       unchanged slot, the same key every coherence correction uses) is restored in full - its own
       text and fact_ids, never a rewrite - undoing whatever this revision did to that one slot.
    2. Every *other* unit that cites the same fact_id without its own task granting it (the
       stray citation that caused the move in the first place) has that one id stripped from its
       own fact_ids - never its text, which the model may still have revised legitimately; only
       the over-claimed citation id is removed, the same narrow, mechanical strip
       ``authoring.py``'s own ``_strip_echoed_fact_ids`` already applies for a different stray-
       citation shape.

    Scoped to must-carry fact ids only (never a blanket "any out-of-section citation is stripped"
    rule, which could as easily hide an unrelated defect) - a fact_id only qualifies when some
    *other* task's own ``must_carry`` names it, so a genuinely wrong citation with no must-carry
    obligation behind it is left for the model's own re-ask to fix, exactly as before.

    Returns ``None`` when nothing needed correcting.
    """
    units = output.get("units")
    if not isinstance(units, list):
        return None
    by_section: dict[str, list[dict[str, Any]]] = {}
    for unit in units:
        if isinstance(unit, dict):
            by_section.setdefault(str(unit.get("section", "")), []).append(unit)
    existing_by_key = {
        (str(unit.get("section")), str(unit.get("slot"))): unit for unit in existing_units
    }
    carry_owners: dict[str, str] = {}
    for task in tasks:
        for fact_id in task.must_carry:
            carry_owners[fact_id] = task.section_id
    changed = False
    for task in tasks:
        if not task.must_carry:
            continue
        owned = [u for u in by_section.get(task.section_id, []) if u.get("slot") in task.slots]
        missing = uncarried_units({"units": owned, "omitted": []}, task.must_carry)
        for fact_id in missing:
            for unit in owned:
                key = (task.section_id, str(unit.get("slot")))
                existing = existing_by_key.get(key)
                if existing is None or fact_id not in existing.get("fact_ids", []):
                    continue
                unit["text"] = existing.get("text", unit.get("text"))
                existing_fact_ids = existing.get("fact_ids")
                unit["fact_ids"] = (
                    list(existing_fact_ids)
                    if isinstance(existing_fact_ids, list)
                    else unit.get("fact_ids", [])
                )
                changed = True
    for task in tasks:
        for unit in by_section.get(task.section_id, []):
            if unit.get("slot") not in task.slots:
                continue
            fact_ids = unit.get("fact_ids")
            if not isinstance(fact_ids, list):
                continue
            stray = [
                fact_id
                for fact_id in fact_ids
                if fact_id not in task.accepted_ids
                and carry_owners.get(fact_id) not in (None, task.section_id)
            ]
            if not stray:
                continue
            remaining = [fact_id for fact_id in fact_ids if fact_id not in stray]
            if remaining:
                unit["fact_ids"] = remaining
                changed = True
                continue
            # Stripping every stray id would leave this unit with none at all - the schema's own
            # per-unit ``fact_ids`` bound requires at least one (G7-W17 live gap, aspose-email-foss/
            # Aspose.Email-FOSS-for-.Net, revision 59125b47...: "$.units[12].fact_ids: [] should be
            # non-empty" rejected the correction itself before coherence_checks ever saw it - this
            # unit's entire citation set was the one over-claimed must-carry id, so stripping it
            # bare is not a safe correction). Fall back to the same full-unit revert the carrying
            # section above already uses: restore this unit's own pre-coherence text and fact_ids
            # in full, never leaving an empty array. If no pre-coherence record exists for this
            # exact slot, decline the strip entirely (never invent or emit an empty fact_ids) and
            # leave it for the model's own re-ask, exactly as the no-carry-obligation scope control
            # already does above.
            key = (task.section_id, str(unit.get("slot")))
            existing = existing_by_key.get(key)
            existing_fact_ids = existing.get("fact_ids") if existing else None
            if existing is not None and isinstance(existing_fact_ids, list) and existing_fact_ids:
                unit["text"] = existing.get("text", unit.get("text"))
                unit["fact_ids"] = list(existing_fact_ids)
                changed = True
    return output if changed else None


def recover_coherence_regressions(
    output: dict[str, Any],
    *,
    existing_units: list[dict[str, Any]],
    facts: FactsDocument,
    tasks: list[SectionTask],
) -> dict[str, Any] | None:
    """The one ``recover=`` callable ``repair/rounds.py``'s S8 call site passes: both of S8
    coherence's own last-resort corrections, composed - ``recover_coherence_content_loss`` first
    (the generic dropped-fact-with-no-trace revert, G3-W05), then
    ``recover_coherence_carried_units`` (the must-carry-specific revert and stray-citation strip,
    above) against whatever the first pass left. Running the must-carry fix second means it always
    judges the live, possibly-already-corrected output rather than a stale view. ``run_job`` only
    ever accepts the result on its own re-validation against the real checks, never on either
    function's say-so, so an incomplete correction here changes nothing: the job fails exactly as
    it would have without this at all. Returns ``None`` only when neither correction found
    anything to fix."""
    changed = False
    content_fixed = recover_coherence_content_loss(
        output, existing_units=existing_units, facts=facts
    )
    if content_fixed is not None:
        output = content_fixed
        changed = True
    carry_fixed = recover_coherence_carried_units(
        output, existing_units=existing_units, tasks=tasks
    )
    if carry_fixed is not None:
        output = carry_fixed
        changed = True
    return output if changed else None


def apply_coherence(
    units_document: dict[str, Any], output: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """The units document with revised texts, and the section/slot names whose text changed."""
    revised_text = {
        (unit["section"], unit["slot"]): unit["text"] for unit in output.get("units", [])
    }
    revised: list[str] = []
    units: list[dict[str, Any]] = []
    for unit in units_document.get("units", []):
        key = (unit["section"], unit["slot"])
        text = revised_text.get(key, unit["text"])
        fact_ids = next(
            (
                item.get("fact_ids", unit["fact_ids"])
                for item in output.get("units", [])
                if (item.get("section"), item.get("slot")) == key
            ),
            unit["fact_ids"],
        )
        if text != unit["text"]:
            revised.append(f"{key[0]}/{key[1]}")
        units.append({**unit, "text": text, "fact_ids": fact_ids})
    document = {
        **units_document,
        "units": units,
        "coherence": {"applied": True, "revised": revised},
    }
    return document, revised
