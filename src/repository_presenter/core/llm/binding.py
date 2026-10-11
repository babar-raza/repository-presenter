"""Bind a job's output to the facts it cites: an unknown or contradicted ID rejects the output.

The guard is structural. It walks the output for every key that carries fact or unit IDs and
checks each against the facts document; it never reads prose. What each binding class requires:
``fact_ids`` and ``selection_ids`` cite only SUPPORTED facts; ``revision_ids`` cite only SUPPORTED
facts in the repair's own changes, while its ``revised_output`` is bound by the causal stage's own
binding (a reconciliation repair may cite a contradicted fact for an omission exactly as a fresh
reply may); ``finding_ids`` cite facts that exist (a finding may point at a contradicted fact as
its evidence); ``unit_ids`` name every inherited unit exactly once.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from typing import Any

from repository_presenter.core.facts import FactsDocument

Binding = str
_FACT_KEY_SUFFIXES = ("_fact_id", "_fact_ids", "_example_id", "_example_ids", "_format_ids")


@dataclass(frozen=True)
class CitedIds:
    fact_ids: tuple[str, ...]
    unit_ids: tuple[str, ...]


def _walk(payload: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk(item)


def _is_fact_key(key: str) -> bool:
    return key == "fact_ids" or key.endswith(_FACT_KEY_SUFFIXES)


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def collect_ids(payload: Any) -> CitedIds:
    """Every fact ID and unit ID the output cites, in document order, duplicates kept."""
    fact_ids: list[str] = []
    unit_ids: list[str] = []
    for key, value in _walk(payload):
        if _is_fact_key(key):
            fact_ids.extend(_strings(value))
        elif key in {"unit_id", "unit_ids"}:
            unit_ids.extend(_strings(value))
    return CitedIds(tuple(fact_ids), tuple(unit_ids))


def resolve_symbol_ids(payload: Any, facts: FactsDocument) -> list[tuple[str, str]]:
    """Rewrite, in place, a cited public_symbol ID the facts do not carry to the shortest
    SUPPORTED public_symbol ID with the same final name segment, and return the rewrites.

    A job names a symbol by the path it reads (``aspose.threed.LambertMaterial``) while the
    facts record it where it is defined (``aspose.threed.shading.LambertMaterial``) and again
    at each re-export; the shortest ID is the package-level export. The final name segment is
    matched without regard to case, because a job names the class as the source spells it
    (``Scene``) while a fact ID is lowercased (``scene``) - a fact-ID spelling the model is
    asked to reproduce and is rejected for missing, which is cause RC1 in
    docs/RESEARCH_AND_GUIDELINES.md section 27.2, measured there as "investigation: unknown
    fact ID 9". Fact IDs are lowercased when they are minted, so folding case adds no
    ambiguity. A name no fact carries stays as cited and rejects the output as before.
    """
    known = {fact.id for fact in facts.facts}
    by_name: dict[str, list[str]] = {}
    for fact in facts.by_kind("public_symbol"):
        if fact.polarity == "SUPPORTED":
            by_name.setdefault(fact.id.rsplit(".", 1)[-1].lower(), []).append(fact.id)
    rewrites: dict[str, str] = {}

    def resolve(value: str) -> str:
        if value in known or not value.startswith("public_symbol:"):
            return value
        candidates = by_name.get(value.rsplit(".", 1)[-1].lower(), [])
        if not candidates:
            return value
        target = min(candidates, key=lambda i: (len(i), i))
        rewrites[value] = target
        return target

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if _is_fact_key(key) and isinstance(value, str):
                    node[key] = resolve(value)
                elif _is_fact_key(key) and isinstance(value, list):
                    node[key] = [resolve(v) if isinstance(v, str) else v for v in value]
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return sorted(rewrites.items())


def drop_unknown_finding_ids(payload: Any, facts: FactsDocument) -> list[str]:
    """Remove, in place, every cited ID the facts do not carry from a review finding's own
    ``fact_ids``; returns the IDs dropped.

    A finding's ``fact_ids`` is the reviewer's pointer at evidence, and every consumer reads it
    through the facts (``cited = [by_id[i] ... if i in by_id]``): an ID that names no fact was
    already invisible to the rulings, so removing it changes no judgement - it only stops one
    invented pointer (Aspose.Page-FOSS-for-Python, 2026-10-11: ``scope:pdf_import_absent`` beside
    two real format IDs, refused twice) from discarding a whole review of otherwise-bound findings.
    A finding left naming nothing is judged as the finding that names no fact, which is what it
    now is; the verdict and every other field are untouched, and nothing is added. Applies to
    ``findings[*].fact_ids`` only: an omission claim's own ``missing_ids`` stay bound as before.
    """
    known = {fact.id for fact in facts.facts}
    dropped: list[str] = []
    findings = payload.get("findings") if isinstance(payload, dict) else None
    for finding in findings if isinstance(findings, list) else []:
        cited = finding.get("fact_ids") if isinstance(finding, dict) else None
        if not isinstance(cited, list):
            continue
        kept = [item for item in cited if not isinstance(item, str) or item in known]
        dropped.extend(item for item in cited if isinstance(item, str) and item not in known)
        if len(kept) != len(cited):
            finding["fact_ids"] = kept
    return dropped


def fold_duplicate_units(payload: Any) -> None:
    """A repeated ``unit_id`` disposition is dropped in place, keeping the first.

    The ``unit_ids`` binding requires every inherited unit exactly once; a second disposition
    for the same unit answers nothing the first did not, so it is folded away rather than
    rejecting a whole reply that got 83 of 85 units right for repeating one
    (RESEARCH_AND_GUIDELINES.md section 28.12 G4-W17 arrival item 17, measured on
    `aspose-slides-foss/Aspose.Slides-FOSS-for-Java`: 85 units, two with more than one
    disposition, two with none). Structural, like every check in this module: any list of
    records each carrying its own ``unit_id`` is folded, never a name specific to one job's
    schema, so this has no effect on a payload with no such list - every binding but
    ``unit_ids`` today.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if (
                isinstance(value, list)
                and value
                and all(isinstance(item, dict) and "unit_id" in item for item in value)
            ):
                seen: set[Any] = set()
                kept = []
                for item in value:
                    unit_id = item.get("unit_id")
                    if unit_id in seen:
                        continue
                    seen.add(unit_id)
                    kept.append(item)
                if len(kept) != len(value):
                    payload[key] = kept
            else:
                fold_duplicate_units(value)
    elif isinstance(payload, list):
        for item in payload:
            fold_duplicate_units(item)


def merge_partial_units(revised: Any, original: Any) -> Any:
    """A copy of ``revised`` with each unit-keyed list filled in from ``original`` for any unit
    the reply left silent, so a reply may declare only the units it actually revised instead of
    re-stating a whole batch just to satisfy the ``unit_ids`` binding's completeness check.

    G4-W17 arrival item 94, measured on PDF-Cpp: an S4 repair reply that correctly identified and
    fixed exactly two of a forty-unit reconciliation batch was rejected outright, twice, for not
    re-declaring the other thirty-eight - the completeness check below (``binding_errors``,
    ``binding == "unit_ids"``) has no way to distinguish "every unit accounted for" from "every
    unit re-typed", and demanding the second spends the one repair attempt a defect's fingerprint
    ever gets on pure transcription of content nothing asked to change. A unit ``revised`` does
    name overrides ``original``'s own record for it; a unit ``revised`` is silent on carries over
    ``original``'s record unchanged, in ``original``'s own order - the repair reply's own
    ``changes[]`` already names which units it touched, so this never has to guess which of
    ``revised``'s declared units are the real edits.

    Only a top-level list of records each keyed by its own ``unit_id`` is merged this way - the
    identical shape ``fold_duplicate_units`` already folds duplicates within - so a payload with
    no such list at any key returns ``revised`` unchanged at that key, and a non-dict payload (a
    schema violation some other check will already reject) is returned as given.
    """
    if not (isinstance(revised, dict) and isinstance(original, dict)):
        return revised
    merged = dict(revised)
    for key, original_value in original.items():
        if not (
            isinstance(original_value, list)
            and original_value
            and all(isinstance(item, dict) and "unit_id" in item for item in original_value)
        ):
            continue
        declared = merged.get(key)
        if not isinstance(declared, list):
            declared = []
        declared_by_unit = {
            item["unit_id"]: item
            for item in declared
            if isinstance(item, dict) and "unit_id" in item
        }
        merged[key] = [declared_by_unit.get(item["unit_id"], item) for item in original_value]
    return merged


def fill_silent_units(revised: Any, original: Any) -> Any:
    """``revised`` with each unit-keyed list completed from ``original`` for the units it left out.

    The re-ask of a ``unit_ids`` job quotes only the units that were wrong, and a model answers
    what it was shown: Aspose.PDF for TypeScript's second reply declared the 4 units the first
    rejection named and nothing for the other 36, so it was refused as "no disposition for
    inherited units: ..." although the first reply had already answered all 36 validly (cut-2
    wave, 2026-10-11, two batches). A unit the reply is silent on keeps the disposition it had
    the first time; a unit the reply does state is the reply's own, and the rejected ones are
    judged again by the same checks, so nothing is accepted that was not judged. A list is only
    completed when it is a strict subset of the original's units; a full reply is returned as
    given (unlike :func:`merge_partial_units`, order and extra entries are never rewritten).
    """
    if not (isinstance(revised, dict) and isinstance(original, dict)):
        return revised
    completed = dict(revised)
    for key, original_value in original.items():
        revised_value = completed.get(key)
        if not (
            isinstance(original_value, list)
            and isinstance(revised_value, list)
            and original_value
            and all(isinstance(item, dict) and "unit_id" in item for item in original_value)
            and all(isinstance(item, dict) and "unit_id" in item for item in revised_value)
        ):
            continue
        stated = {item["unit_id"] for item in revised_value}
        silent = [item for item in original_value if item["unit_id"] not in stated]
        if silent:
            completed[key] = [*revised_value, *silent]
    return completed


def silent_unit_ids(output: Any, facts: FactsDocument) -> list[str]:
    """The inherited units ``facts`` holds that ``output`` cites nowhere, in the facts' order.

    Exactly the units :func:`binding_errors` reports as "no disposition for inherited units";
    empty when ``output`` is not a JSON object (a shape failure has nothing safe to narrow).
    """
    if not isinstance(output, dict):
        return []
    cited = set(collect_ids(output).unit_ids)
    return [fact.id for fact in facts.by_kind("inherited_unit") if fact.id not in cited]


def add_silent_units(base: Any, narrowed: Any, silent: Collection[str]) -> Any:
    """``base`` with each unit-keyed list extended by the ``silent`` units ``narrowed`` answers.

    The one further ask a ``unit_ids`` job makes shows the model only the units both earlier
    replies left without a disposition (cut-2 wave, 2026-10-11, BarCode-Python: units 057-059,
    silent twice in a batch of 19). Its reply is merged here and the merged whole is judged by
    the job's ordinary schema, binding and checks, so a unit is accepted only on the same terms as
    any other. Only entries for units in ``silent`` are taken, appended after ``base``'s own: a
    unit ``base`` already answers keeps that answer, whatever the narrowed reply says about it.
    """
    if not (isinstance(base, dict) and isinstance(narrowed, dict)):
        return base
    merged = dict(base)
    for key, value in narrowed.items():
        if not (
            isinstance(value, list)
            and all(isinstance(item, dict) and "unit_id" in item for item in value)
        ):
            continue
        wanted = [item for item in value if item["unit_id"] in silent]
        if wanted:
            current = merged.get(key)
            merged[key] = [*(current if isinstance(current, list) else []), *wanted]
    return merged


def binding_errors(payload: Any, facts: FactsDocument, binding: Binding) -> list[str]:
    """Why the output may not be used, or an empty list when every citation holds."""
    known = {fact.id: fact for fact in facts.facts}
    if binding == "revision_ids" and isinstance(payload, dict):
        # The revised output is the causal stage's object and is bound by that stage's
        # binding in the repair checks; here only the repair's own citations are judged.
        payload = {key: value for key, value in payload.items() if key != "revised_output"}
    cited = collect_ids(payload)
    errors: list[str] = []
    require_supported = binding in {"fact_ids", "selection_ids", "revision_ids"}
    for fact_id in dict.fromkeys(cited.fact_ids):
        fact = known.get(fact_id)
        if fact is None:
            errors.append(f"unknown fact ID {fact_id}")
        elif require_supported and fact.polarity != "SUPPORTED":
            errors.append(f"fact {fact_id} is {fact.polarity}, not SUPPORTED")
    for unit_id in dict.fromkeys(cited.unit_ids):
        unit = known.get(unit_id)
        if unit is None:
            errors.append(f"unknown inherited unit {unit_id}")
        elif unit.kind != "inherited_unit":
            # A real fact written into a unit field (a plan's unit_ids filled with the same
            # identity or package IDs as its fact_ids, measured on Slides-Java 2026-10-05): the
            # bare "unknown inherited unit" gave the one re-ask no way to see that the ID is
            # fine and the field is wrong, and the identical reply came back.
            errors.append(
                f"unknown inherited unit {unit_id}: it is a fact of kind {unit.kind}, not an "
                "inherited_unit; unit_ids take only inherited_unit:... IDs, so cite this one in "
                "fact_ids and leave unit_ids empty when no inherited unit applies"
            )
    if binding == "unit_ids":
        expected = [fact.id for fact in facts.by_kind("inherited_unit")]
        counts = {unit_id: cited.unit_ids.count(unit_id) for unit_id in expected}
        missing = [unit_id for unit_id, count in counts.items() if count == 0]
        duplicated = [unit_id for unit_id, count in counts.items() if count > 1]
        if missing:
            errors.append(f"no disposition for inherited units: {', '.join(missing)}")
        if duplicated:
            errors.append(f"more than one disposition for: {', '.join(duplicated)}")
    return errors
