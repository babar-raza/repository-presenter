"""The repair of a disposition as a per-unit patch.

Wave 4: of nine BC-05 failures, eight reached ``targeted_repair`` with a disposition defect and
none was repaired by it. The repair asked for the whole causal artifact (a 155-unit
``revised_output``, whose schema was the manifest's unbounded one), and that failed three ways:

* it truncated: Email-Python's reply hit ``max_output_tokens`` (8,000) while re-listing every unit
  it was not asked about, and a truncated reply is the one class ``run_job`` can never retry;
* it was refused for its own bookkeeping: the model listed ``changes`` with the path of the unit
  in *its* partial list (``dispositions.0``), the check resolved that path in the stored batch
  (where the unit is ``dispositions.15``) and called the ledger untruthful (3D-Java, Words-.NET,
  Font-Python), a defect of asking a model to do arithmetic the code can do;
* it could name any destination: ``destination_section`` was a free string in the repair's
  contract, so the unit went to ``installation`` again, twice (3D-Java, Note-Python,
  BarCode-Python, Words-.NET).

A patch asks for what is wrong and nothing else. :func:`patch_scope` reads the units at fault from
the failure records' ``unit_id`` field (``validation/registry.py``; never from the sentence that
describes them), takes the batch that holds them (the first batch was always assumed), adds the
sentence that introduces a unit that is a block, and cuts the reply contract down to those units:
``reconciliation_schema`` over just them, so the reply cannot name another unit, cannot cite a
fact outside the packet, cannot place a unit in a section that cannot hold it, and is bounded by
construction to the number of units asked about. The reply is merged into the stored batch by unit
(``binding.merge_partial_units``), judged by the batch's own contract and checks, and its
``changes`` are derived from the difference (``jobs.repair_changes``) - what shipped, not what the
model says it did.

A unit whose defect is that it was deferred must leave the deferral (:func:`patch_checks`): handing
back the same disposition is the one reply that cannot repair it.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from repository_presenter.components.readme.reconciliation.destinations import (
    holdable_sections,
    nearest_for_units,
    source_heading,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    lead_in_of,
    reconciliation_batch_facts,
    reconciliation_schema,
    units_per_reply,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.facts import Fact, FactsDocument
from repository_presenter.core.llm.prompts import LoadedManifest

# The most units one patch asks about: the manifest's own ``changes`` ceiling, and a bound on the
# reply the repair prompt's budget is checked against (``units_per_reply``).
PATCH_UNITS = 12
# Tokens of the reply that are not dispositions: the fingerprint, the stage and the ledger.
_RESERVED_TOKENS = 600
_ENUM_SHOWN_LIMIT = 50


def failing_units(record: Mapping[str, Any]) -> list[str]:
    """The inherited units a defect's failure records name in their ``unit_id`` field (and those of
    the equivalent findings merged into it), in the order named, without repeats."""
    failures: list[Any] = list(record.get("failures") or [])
    for equivalent in record.get("equivalent_findings") or []:
        failures.extend(equivalent.get("failures") or [])
    named: list[str] = []
    for failure in failures:
        unit = failure.get("unit_id") if isinstance(failure, Mapping) else None
        if unit and unit not in named:
            named.append(str(unit))
    return named


def target_batch(
    record: Mapping[str, Any], batches: Mapping[str, Sequence[Fact]], available: Collection[str]
) -> str | None:
    """The first batch (of those with an accepted reply) holding a unit the defect names, or
    ``None`` when it names none: the repair then keeps its earlier target, the first batch."""
    named = set(failing_units(record))
    for batch_id, units in batches.items():
        if batch_id in available and named & {unit.id for unit in units}:
            return batch_id
    return None


@dataclass(frozen=True)
class PatchScope:
    """What a repair of a disposition defect is asked, and the contract its reply must meet."""

    batch_id: str
    unit_ids: tuple[str, ...]
    # The stored dispositions of those units, with what the model needs to place each: the text,
    # the heading it sat under and the nearest section that can hold it. The packet's stage output.
    shown: dict[str, Any]
    # The bounded schema of the reply's ``revised_output`` (the call's constraint, not the
    # contract of the stored batch, which the merged reply is judged by).
    contract: dict[str, Any]
    # Units whose stored disposition is a deferral: the defect is that the deferral loses content.
    deferred: frozenset[str]
    holdable: tuple[str, ...]


def patch_scope(
    record: Mapping[str, Any],
    reconciled: Mapping[str, Mapping[str, Any]],
    batches: Mapping[str, Sequence[Fact]],
    facts: FactsDocument,
    manifest: LoadedManifest,
    investigation: Mapping[str, Any],
    repair_budget_tokens: int,
) -> PatchScope | None:
    """The patch a disposition defect is repaired by, or ``None`` when the defect names no unit
    this repair can address (a review finding routed here, a failure about the batch as a whole):
    the earlier whole-batch repair then runs unchanged.

    ``reconciled`` is each batch's stored output by batch ID; ``repair_budget_tokens`` is the repair
    prompt's ``max_output_tokens``, which bounds how many units one patch asks about."""
    batch_id = target_batch(record, batches, reconciled)
    if batch_id is None:
        return None
    batch_units = list(batches[batch_id])
    by_id = {unit.id: unit for unit in batch_units}
    stored = {
        str(entry.get("unit_id")): entry
        for entry in reconciled[batch_id].get("dispositions", [])
        if isinstance(entry, Mapping)
    }
    wanted = [unit for unit in failing_units(record) if unit in by_id and unit in stored]
    if not wanted:
        return None
    # A block moves with the sentence that introduces it, whatever that sentence is now doing (kept
    # elsewhere, superseded by a section that prints the block's twin, or withheld): the model
    # decides both or the label is left behind.
    for named in list(wanted):
        lead = lead_in_of(named, by_id)
        if lead is not None and lead not in wanted and lead in stored:
            wanted.append(lead)
    batch_facts = reconciliation_batch_facts(facts, batch_units)
    try:
        fits = units_per_reply(batch_facts, repair_budget_tokens - _RESERVED_TOKENS)
    except ConfigError:
        return None  # not even one disposition fits the repair budget: revise the batch as before
    cap = min(PATCH_UNITS, fits)
    order = {unit.id: index for index, unit in enumerate(batch_units)}
    chosen = sorted(wanted, key=order.__getitem__)[:cap]
    units = [by_id[unit] for unit in chosen]
    scoped = reconciliation_batch_facts(batch_facts, units)
    holdable = holdable_sections(batch_facts)
    near = nearest_for_units(units, holdable)
    shown = []
    for unit in units:
        entry = copy.deepcopy(dict(stored[unit.id]))
        entry["unit_text"] = unit.value
        heading = source_heading(unit)
        if heading:
            entry["source_heading"] = heading
        if near[unit.id] is not None:
            entry["nearest_section_that_can_hold_it"] = near[unit.id]
        shown.append(entry)
    return PatchScope(
        batch_id=batch_id,
        unit_ids=tuple(chosen),
        shown={"dispositions": shown},
        contract=reconciliation_schema(manifest, units, scoped, investigation),
        deferred=frozenset(
            unit for unit in chosen if stored[unit].get("disposition") == "DEFER_UNRESOLVED"
        ),
        holdable=holdable,
    )


def patch_checks(
    scope: PatchScope, checks: Callable[[dict[str, Any]], list[str]] | None
) -> Callable[[dict[str, Any]], list[str]]:
    """``checks`` with the rule that a deferred unit the defect names must stop being deferred.

    The defect is that deferring the unit takes its content out of the README ("keep it where a
    reader will find it, restate it, or omit it citing the fact that contradicts it"); the second
    wave-4 reply of 3D-Java handed the same deferral back with a longer rationale and the repair was
    spent. Run on the merged reply, before the batch's own checks."""

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        by_unit = {
            str(entry.get("unit_id")): entry
            for entry in revised.get("dispositions", [])
            if isinstance(entry, Mapping)
        }
        for unit in sorted(scope.deferred):
            if by_unit.get(unit, {}).get("disposition") == "DEFER_UNRESOLVED":
                errors.append(
                    f"{unit}: still DEFER_UNRESOLVED, which is the defect: deferring it loses its "
                    f"content. Keep it as written in a section that can hold it "
                    f"({', '.join(scope.holdable)}), or omit it citing the fact that contradicts it"
                )
        errors.extend(checks(revised) if checks is not None else [])
        return errors

    return guarded


_CHANGE_TEXT = 2000  # the repair manifest's own ``before``/``after`` ceiling
_CHANGE_FACTS = 24  # ... and its ``fact_ids`` ceiling


def unit_changes(original: Mapping[str, Any], revised: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The ledger of a patch, derived from the difference: one entry per unit whose disposition
    changed, at its position in the stored batch, with the entry before and after as JSON.

    It satisfies the repair manifest's ``changes`` contract (at most 12 entries, text ceilings, a
    ``fact_ids`` list) because a stored repair is re-judged by that contract on reuse; per unit and
    not per field because a unit's fields change together and the manifest allows only twelve."""
    before = [entry for entry in original.get("dispositions", []) if isinstance(entry, Mapping)]
    after = {
        str(entry.get("unit_id")): entry
        for entry in revised.get("dispositions", [])
        if isinstance(entry, Mapping)
    }
    changes: list[dict[str, Any]] = []
    for index, was in enumerate(before):
        now = after.get(str(was.get("unit_id")))
        if now is None or now == was:
            continue
        changes.append(
            {
                "id": f"R{len(changes) + 1:02d}",
                "path": f"dispositions.{index}",
                "before": _shown(was),
                "after": _shown(now),
                "fact_ids": [str(i) for i in (now.get("fact_ids") or [])][:_CHANGE_FACTS],
            }
        )
    return changes[:PATCH_UNITS]


def _shown(entry: Mapping[str, Any]) -> str:
    text = json.dumps(entry, sort_keys=True, ensure_ascii=False)
    return text if len(text) <= _CHANGE_TEXT else text[: _CHANGE_TEXT - 3] + "..."


def condensed(node: Any) -> Any:
    """``node`` (a schema shown in a prompt) with every long ``enum`` replaced by its size: the
    contract of a patch lists hundreds of citable fact IDs, which the decoder enforces and the
    reader of the prompt does not need spelled out."""
    if isinstance(node, dict):
        return {
            key: (
                f"<{len(value)} allowed values, enforced when the reply is decoded>"
                if key == "enum" and isinstance(value, list) and len(value) > _ENUM_SHOWN_LIMIT
                else condensed(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [condensed(item) for item in node]
    return node
