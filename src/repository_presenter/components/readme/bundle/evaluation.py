"""Dependency evaluation: which sealed inputs changed, and the earliest stage that reopens.

A sealed bundle's dependencies.json names exactly the inputs its candidate consumed. Before a run
asks for anything, the inputs it would consume now are compared with that record, class by
class, and each change names the state it reopens (docs/STATE_MACHINE.md section 9): the source
revision or tree and the fact records reopen EXTRACTING; a prompt reopens its own stage; a
template component reopens COMPOSING; the contract version or a validator reopens VALIDATING;
the acceptance profile reopens REVIEWING; the policy reopens PLANNING. The earliest affected
state is the answer, or NONE when nothing changed. The protected-content fingerprint is derived
from the accepted dispositions rather than consumed, so the seal compares it, not this record.

The evaluation derives only from the candidate's own dependencies.json: no global control-plane
hash exists, and none may. It is written to the transaction as evaluation.json.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EVALUATION_FILENAME = "evaluation.json"
NONE = "NONE"
STATE_ORDER: tuple[str, ...] = (
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
    "VALIDATING",
    "REVIEWING",
)
PROMPT_STATES: dict[str, str] = {
    "repository_investigation": "INVESTIGATING",
    "source_reconciliation": "RECONCILING",
    "presentation_planning": "PLANNING",
    "section_authoring": "COMPOSING",
    "independent_review": "REVIEWING",
    "targeted_repair": "REVIEWING",
}


@dataclass(frozen=True)
class Change:
    dependency: str
    detail: str
    reopens: str


@dataclass(frozen=True)
class Evaluation:
    changes: tuple[Change, ...]

    @property
    def earliest(self) -> str:
        states = [change.reopens for change in self.changes]
        return min(states, key=STATE_ORDER.index) if states else NONE


def _differs(sealed: Any, current: Any) -> bool:
    return bool(sealed != current)


def evaluate(sealed: dict[str, Any], current: dict[str, Any]) -> Evaluation:
    """Every changed dependency class with the state it reopens, in state order then name."""
    changes: list[Change] = []
    if _differs(sealed.get("source"), current.get("source")):
        changes.append(Change("source", "revision or tree fingerprint changed", "EXTRACTING"))
    sealed_facts = dict(sealed.get("facts", {}))
    current_facts = dict(current.get("facts", {}))
    if sealed_facts != current_facts:
        added = sorted(set(current_facts) - set(sealed_facts))
        removed = sorted(set(sealed_facts) - set(current_facts))
        altered = sorted(
            fact_id
            for fact_id in set(sealed_facts) & set(current_facts)
            if sealed_facts[fact_id] != current_facts[fact_id]
        )
        detail = f"{len(added)} fact records added, {len(removed)} removed, {len(altered)} altered"
        changes.append(Change("facts", detail, "EXTRACTING"))
    sealed_prompts = dict(sealed.get("prompts", {}))
    current_prompts = dict(current.get("prompts", {}))
    for name in sorted(set(sealed_prompts) | set(current_prompts)):
        if sealed_prompts.get(name) == current_prompts.get(name):
            continue
        if name not in sealed_prompts:
            detail = "prompt added"
        elif name not in current_prompts:
            detail = "prompt removed"
        else:
            fields = sorted(
                field
                for field in ("sha256", "version", "model_route")
                if sealed_prompts[name].get(field) != current_prompts[name].get(field)
            )
            detail = f"prompt {', '.join(fields)} changed"
        changes.append(Change(f"prompts.{name}", detail, PROMPT_STATES.get(name, "INVESTIGATING")))
    if _differs(sealed.get("contract_version"), current.get("contract_version")):
        changes.append(
            Change(
                "contract_version",
                f"{sealed.get('contract_version')} -> {current.get('contract_version')}",
                "VALIDATING",
            )
        )
    sealed_components = dict(sealed.get("components", {}))
    current_components = dict(current.get("components", {}))
    for name in sorted(set(sealed_components) | set(current_components)):
        if sealed_components.get(name) != current_components.get(name):
            changes.append(
                Change(
                    f"components.{name}",
                    f"{sealed_components.get(name)} -> {current_components.get(name)}",
                    "COMPOSING",
                )
            )
    if _differs(sealed.get("validators"), current.get("validators")) or _differs(
        sealed.get("validator_version"), current.get("validator_version")
    ):
        changes.append(
            Change("validators", "a check or the validator version changed", "VALIDATING")
        )
    if _differs(
        sealed.get("acceptance_profile_version"), current.get("acceptance_profile_version")
    ):
        changes.append(
            Change(
                "acceptance_profile_version",
                f"{sealed.get('acceptance_profile_version')} -> "
                f"{current.get('acceptance_profile_version')}",
                "REVIEWING",
            )
        )
    if _differs(sealed.get("policy"), current.get("policy")):
        changes.append(Change("policy", "policy version or hash changed", "PLANNING"))
    ordered = sorted(
        changes, key=lambda change: (STATE_ORDER.index(change.reopens), change.dependency)
    )
    return Evaluation(tuple(ordered))


def evaluation_document(
    bundle_revision: str | None, evaluation: Evaluation | None
) -> dict[str, Any]:
    """evaluation.json: the sealed basis, every change, and the earliest affected stage."""
    if evaluation is None:
        return {
            "schema_version": 1,
            "sealed_bundle": None,
            "changes": [],
            "earliest_affected_stage": "EXTRACTING",
            "note": "no sealed bundle for this revision; every stage runs",
        }
    return {
        "schema_version": 1,
        "sealed_bundle": bundle_revision,
        "changes": [asdict(change) for change in evaluation.changes],
        "earliest_affected_stage": evaluation.earliest,
        "note": (
            "nothing consumed changed; every stage reuses its accepted output"
            if not evaluation.changes
            else "the earliest affected stage and everything downstream are asked again"
        ),
    }


def summarize_evaluation(document: dict[str, Any]) -> str:
    if document.get("sealed_bundle") is None:
        return "no sealed bundle for this revision; every stage runs"
    changes = document.get("changes", [])
    names = ", ".join(f"{c['dependency']} -> {c['reopens']}" for c in changes)
    return (
        f"earliest affected stage {document.get('earliest_affected_stage')}; "
        f"{len(changes)} changes" + (f" ({names})" if names else "")
    )


def write_evaluation(document: dict[str, Any], path: Path) -> str:
    data = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
