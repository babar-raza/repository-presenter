"""Stage S11: targeted repair - one typed defect, its causal stage, one attempt per fingerprint.

A blocking validation failure or a rejecting review finding becomes a defect routed to the stage
that caused it (docs/STATE_MACHINE.md section 8): S3 investigation, S4 reconciliation, S5
planning, or S6 authoring. Render and coherence defects are authoring defects, because only the
units change. A finding that blames the evidence (S2) is repairable only when the evidence it
cites exists and is SUPPORTED and the section is LLM-owned - then the disagreement is in how the
section used the evidence, an S6 matter; otherwise extraction is reopened, which without a source
or extractor change yields the same facts, and the finding is recorded as advisory. A defect in a
deterministic section is advisory too: those blocks change only when their facts change.

The fingerprint names the target - source, section, stage, criterion or check - so two findings
that would be repaired the same way are equivalent. repairs.json records every attempt; a second
equivalent failure is reported, never retried, and the mechanism must change before another ask.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from repository_presenter.core.facts import FACT_KINDS, FactsDocument, bounded_records
from repository_presenter.core.llm.binding import binding_errors
from repository_presenter.core.llm.ledger import canonical_hash
from repository_presenter.core.registry.models import RegistryEntry

REPAIRS_FILENAME = "repairs.json"
MAX_ROUNDS = 3
STAGE_JOBS: dict[str, str] = {
    "S3": "repository_investigation",
    "S4": "source_reconciliation",
    "S5": "presentation_planning",
    "S6": "section_authoring",
}
STATE_STAGES: dict[str, str] = {
    "INVESTIGATING": "S3",
    "RECONCILING": "S4",
    "PLANNING": "S5",
    "COMPOSING": "S6",
}
_COMPOSITION_STAGES = frozenset({"S6", "S7", "S8"})
EVIDENCE_REASON = (
    "evidence defect: extraction reopens only when the source or the extractor changes, and "
    "neither has"
)


@dataclass(frozen=True)
class Defect:
    """One typed defect and where the loop may act on it."""

    fingerprint: str
    source: str
    label: str
    section_id: str | None
    stage: str | None
    record: dict[str, Any]
    reason: str | None = None

    @property
    def repairable(self) -> bool:
        return self.stage is not None


@dataclass
class SlotSetProbe:
    """Whether a repair's own reply would change the plan's slot set.

    The plan owns the slot set: S6's per-task schema requires exactly the slots the plan assigned,
    so a revision that adds, drops, or re-chooses one is a planning decision by construction. The
    escalation reads this comparison of two sets of slot names - the plan's, and the revision's -
    and never the rejection's prose (docs/RESEARCH_AND_GUIDELINES.md section 27.2, the 2026-09-05
    decision; RC8's rule that routing reads fields).
    """

    required: frozenset[str]
    returned: frozenset[str] | None = None

    @property
    def conflicts(self) -> bool:
        return self.returned is not None and self.returned != self.required


def defect_fingerprint(
    source: str, section: str | None, stage: str | None, criterion: str, context: str = ""
) -> str:
    """Two defects the loop would repair the same way share a fingerprint. ``context`` is the
    judge's own identity - the reviewer prompt's hash or the validator version - so a changed
    mechanism permits a new attempt, as the contract requires after a second failure."""
    return canonical_hash(
        {
            "source": source,
            "section": section,
            "stage": stage,
            "criterion": criterion,
            "context": context,
        }
    )[:24]


def review_defects(
    review: dict[str, Any], facts: FactsDocument, llm_sections: set[str], repairer: str = ""
) -> list[Defect]:
    """The review's blocking findings routed to the stage a repair may revise; ``repairer`` is
    the repair prompt's hash, part of the fingerprint like the reviewer's own."""
    context = f"{review.get('reviewer', {}).get('prompt_sha256', '')}|{repairer}"
    defects: list[Defect] = []
    for finding in review.get("findings", []):
        section = str(finding.get("section_id") or "") or None
        named = str(finding.get("causal_stage") or "")
        criterion = str(finding.get("criterion") or "")
        stage: str | None = "S6" if named in _COMPOSITION_STAGES else named
        reason: str | None = None
        if named == "S2":
            # In an LLM-authored section the claim either misused evidence that exists or
            # asserts what no fact supports; both are fixed by revising the units. Only a
            # deterministic section's content follows the facts themselves.
            if section in llm_sections:
                stage = "S6"
            else:
                stage, reason = None, EVIDENCE_REASON
        if stage == "S6" and section not in llm_sections:
            stage, reason = (
                None,
                (f"section {section} is deterministic; its blocks change only when facts change"),
            )
        if stage is not None and stage not in STAGE_JOBS:
            stage, reason = None, f"stage {named} is not repairable by revision"
        defects.append(
            Defect(
                defect_fingerprint("review", section, stage or named, criterion, context),
                "review",
                str(finding.get("id", "?")),
                section,
                stage,
                dict(finding),
                reason,
            )
        )
    return defects


def validation_defects(
    validation: dict[str, Any], llm_sections: set[str], repairer: str = ""
) -> list[Defect]:
    """The failing blocking checks routed to the stage a repair may revise."""
    defects: list[Defect] = []
    context = f"{validation.get('validator_version', '')}|{repairer}"
    for check in validation.get("checks", []):
        if check.get("verdict") != "FAIL":
            continue
        state = check.get("causal_stage")
        stage = STATE_STAGES.get(str(state))
        details = list(check.get("details", []))
        failures = list(check.get("failures", []))
        section: str | None = None
        reason: str | None = None
        if stage == "S6":
            named = [
                str(failure.get("section_id"))
                for failure in failures
                if failure.get("section_id") in llm_sections
            ]
            section = named[0] if named else None
            if section is None:
                stage, reason = None, "no failing check names an LLM-owned section"
        elif stage is None:
            reason = f"{state or 'the bundle'} is not repairable by revision"
        record = {
            "id": check.get("id"),
            "name": check.get("name"),
            "causal_stage": state,
            "details": details,
            "failures": failures,
        }
        defects.append(
            Defect(
                defect_fingerprint(
                    "validation", section, stage or str(state), str(check.get("id")), context
                ),
                "validation",
                str(check.get("id", "?")),
                section,
                stage,
                record,
                reason,
            )
        )
    return defects


def merge_equivalent(defects: Sequence[Defect]) -> list[Defect]:
    """One defect per fingerprint, carrying every equivalent finding of the round, so the one
    repair the fingerprint allows sees the whole set rather than the first alone."""
    merged: dict[str, Defect] = {}
    for defect in defects:
        first = merged.get(defect.fingerprint)
        if first is None:
            merged[defect.fingerprint] = defect
            continue
        equivalent = [*first.record.get("equivalent_findings", []), defect.record]
        merged[defect.fingerprint] = replace(
            first,
            label=f"{first.label}+{defect.label}",
            record={**first.record, "equivalent_findings": equivalent},
        )
    return list(merged.values())


@dataclass
class RepairLedger:
    """repairs.json: every attempt by fingerprint; a second equivalent failure is never retried."""

    path: Path
    attempts: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.path.is_file():
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            self.attempts = dict(stored.get("attempts", {}))

    def attempted(self, fingerprint: str) -> bool:
        return fingerprint in self.attempts

    def record(
        self,
        defect: Defect,
        outcome: str,
        request_sha256: str | None = None,
        changes: Sequence[dict[str, Any]] = (),
    ) -> None:
        self.attempts[defect.fingerprint] = {
            "source": defect.source,
            "label": defect.label,
            "section_id": defect.section_id,
            "stage": defect.stage,
            "outcome": outcome,
            "reason": defect.reason,
            "request_sha256": request_sha256,
            "changes": list(changes),
        }
        self.write()

    def note_re_raised(self, defect: Defect) -> None:
        """A defect re-raised after its fingerprint's one attempt: recorded, never retried, and
        never demoted on that account alone (docs/RESEARCH_AND_GUIDELINES.md section 27.5 D5) -
        it blocks, and the transaction reports it rather than trying a third time."""
        attempt = self.attempts[defect.fingerprint]
        re_raised = list(attempt.get("re_raised", []))
        if defect.label not in re_raised:
            re_raised.append(defect.label)
        attempt["re_raised"] = re_raised
        self.write()

    def write(self) -> None:
        document = {"schema_version": 1, "attempts": self.attempts}
        data = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(data.encode("utf-8"))

    def summary(self) -> str:
        repaired = sorted(
            f"{a['label']} {a['stage']}{' ' + a['section_id'] if a['section_id'] else ''}"
            for a in self.attempts.values()
            if a["outcome"] == "repaired"
        )
        advisory = sum(1 for a in self.attempts.values() if a["outcome"] == "unrepairable")
        escalated = sum(1 for a in self.attempts.values() if a["outcome"] == "escalated")
        re_raised = sum(len(a.get("re_raised", [])) for a in self.attempts.values())
        parts = [f"{len(repaired)} repaired" + (f" ({', '.join(repaired)})" if repaired else "")]
        if escalated:
            parts.append(f"{escalated} escalated to a plan-level repair")
        parts.append(f"{advisory} unrepairable recorded advisory")
        if re_raised:
            # Never "recorded advisory": a re-raised defect blocks and the transaction reports
            # it (section 27.5 D5), the same outcome an unrepairable one on its first attempt
            # does not get.
            parts.append(f"{re_raised} re-raised after repair; the equivalent failure stands")
        return ", ".join(parts)


def repair_packet(
    entry: RegistryEntry,
    defect: Defect,
    stage_output: dict[str, Any],
    facts: FactsDocument,
    preserve: Sequence[str],
    output_contract: dict[str, Any],
    allowed: Collection[str] | None = None,
    slot_facts: Mapping[str, Collection[str]] | None = None,
) -> dict[str, Any]:
    """The packet for one repair call: the defect, the one artifact it may revise, its contract.

    When the causal stage authored a section, ``allowed`` is that section's own fact set and the
    packet carries only those records. The repair is judged by the section's checks, so a packet
    holding the whole corpus asks the model to guess which part of it applies and rejects it for
    guessing wrong: RESEARCH_AND_GUIDELINES.md section 27.2 RC1 measured 69 of 76 repair
    rejections as citations outside the section's set, and the canary's own rejected replies
    name that family and the UNRESOLVED-fact one it shares a cause with.
    """
    kinds = [kind for kind in FACT_KINDS if kind != "inherited_unit"]
    records = bounded_records(facts, kinds, ("SUPPORTED",))
    if allowed is not None:
        permitted = set(allowed)
        records = [record for record in records if record["id"] in permitted]
    return {
        "repository": entry.repository,
        "defect": {**defect.record, "fingerprint": defect.fingerprint, "source": defect.source},
        "causal_stage": defect.stage,
        "stage_output": stage_output,
        "facts": records,
        "slot_facts": {slot: sorted(ids) for slot, ids in sorted((slot_facts or {}).items())},
        "preserve": list(preserve),
        "output_contract": output_contract,
    }


def repair_checks(
    output: dict[str, Any],
    defect: Defect,
    output_contract: dict[str, Any],
    binding: str,
    facts: FactsDocument,
    stage_checks: Callable[[dict[str, Any]], list[str]] | None = None,
    slots: SlotSetProbe | None = None,
) -> list[str]:
    """Why the repair may not be used: it must target the defect, and the revised output must
    satisfy the causal stage's own contract, binding, and checks exactly as a fresh reply would.

    ``slots``, when a content stage gave one, records the slot set this reply would leave behind
    and rejects a revision that changes it: the plan owns that set, so such a fix is a planning
    decision the escalation routes to S5 rather than a revision this stage may make.
    """
    errors: list[str] = []
    if output.get("causal_stage") != defect.stage:
        errors.append(f"causal_stage must be {defect.stage}; got {output.get('causal_stage')!r}")
    if output.get("fingerprint") != defect.fingerprint:
        errors.append(f"fingerprint must be the defect's own ({defect.fingerprint})")
    revised = output.get("revised_output")
    if not isinstance(revised, dict):
        return [*errors, "revised_output must be the causal stage's output object"]
    validator = Draft202012Validator(output_contract)
    errors.extend(
        f"revised_output{error.json_path[1:]}: {error.message}"
        for error in sorted(validator.iter_errors(revised), key=lambda error: error.json_path)
    )
    errors.extend(f"revised_output: {error}" for error in binding_errors(revised, facts, binding))
    # Read before the stage's own checks, which normalise the units they judge.
    if slots is not None:
        slots.returned = frozenset(
            str(unit.get("slot"))
            for unit in revised.get("units", [])
            if isinstance(unit, dict) and unit.get("slot") is not None
        )
        if slots.conflicts:
            errors.append(
                "revised_output: the plan owns this section's slot set "
                f"({', '.join(sorted(slots.required))}); a revision filling "
                f"{', '.join(sorted(slots.returned)) or 'none of them'} would add, drop, or "
                "re-choose a slot, which is a planning decision, not an authoring one"
            )
    if not errors and stage_checks is not None:
        errors.extend(f"revised_output: {error}" for error in stage_checks(revised))
    return errors
