"""One composition round - stages S3 to S10 over the extracted facts - and the bounded repair loop.

A round runs the governed jobs through the store, so a stage whose request is unchanged reuses
its accepted output with zero provider calls and only a repaired stage and everything downstream
of it are asked again. The loop judges the round (validation, then review), routes each blocking
defect to its causal stage, repairs each fresh fingerprint once by writing the revised output back
to the store under the causal request's own hash, and runs the next round. A defect whose
fingerprint was already attempted, or that no stage can repair, ends the loop: it is reported,
never retried. Every artifact of the round is written, so the last round is what the bundle holds.
"""

from __future__ import annotations

import functools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    CONTENT_UNITS_FILENAME,
    SectionTask,
    authoring_schema,
    authoring_tasks,
    merge_units,
    unit_checks,
    write_content_units,
)
from repository_presenter.components.readme.composition.coherence import (
    apply_coherence,
    coherence_checks,
    coherence_packet,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.components.readme.composition.planning import (
    PLAN_FILENAME,
    plan_checks,
    planning_packet,
    planning_schema,
    write_plan,
)
from repository_presenter.components.readme.composition.renderer import (
    PATCH_FILENAME,
    README_FILENAME,
    render_patch,
    render_readme,
    write_text,
)
from repository_presenter.components.readme.investigation.dossier import (
    INVESTIGATION_FILENAME,
    investigation_packet,
    write_investigation,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    DISPOSITIONS_FILENAME,
    reconcile_checks,
    reconciliation_packet,
    reconciliation_schema,
    write_dispositions,
)
from repository_presenter.components.readme.repair.targeted import (
    MAX_ROUNDS,
    REPAIRS_FILENAME,
    STAGE_JOBS,
    Defect,
    RepairLedger,
    merge_equivalent,
    repair_checks,
    repair_packet,
    review_defects,
    validation_defects,
)
from repository_presenter.components.readme.review.independent.review import (
    REVIEW_FILENAME,
    demote_findings,
    review_checks,
    review_document,
    review_packet,
    write_review,
)
from repository_presenter.components.readme.validation.registry import (
    VALIDATION_FILENAME,
    Candidate,
    blocking_failures,
    record_review_verdict,
    validate_candidate,
    write_validation,
)
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import CallStore, JobContext, JobResult, run_job
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import PromptRegistry
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret


@dataclass(frozen=True)
class TransactionInputs:
    """Everything a round reads that does not change between rounds."""

    entry: RegistryEntry
    facts: FactsDocument
    prompts: PromptRegistry
    config: GatewayConfig
    ledger: Ledger
    store: CallStore
    context: JobContext
    original: str
    original_bytes: bytes | None
    source_revision: str
    readme_sha256: str | None
    tree_paths: Sequence[str]
    directory: Path
    secrets: Sequence[ConfiguredSecret]


@dataclass
class Round:
    """The accepted outputs of one composition round and the judgement over them."""

    investigation: JobResult
    reconciled: JobResult
    planned: JobResult
    authored: dict[str, JobResult]
    tasks: list[SectionTask]
    units: dict[str, Any]
    coherent: JobResult
    revised: list[str]
    readme: str
    validation: dict[str, Any]
    reviewed: JobResult | None = None
    review: dict[str, Any] = field(default_factory=dict)
    digests: dict[str, str] = field(default_factory=dict)

    @property
    def llm_sections(self) -> set[str]:
        return {task.section_id for task in self.tasks}


def run_round(tx: TransactionInputs) -> Round:
    """Stages S3 to S10 once, every artifact written; unchanged requests reuse the store."""
    prompts, facts, entry = tx.prompts, tx.facts, tx.entry
    common: dict[str, Any] = {
        "config": tx.config,
        "facts": facts,
        "ledger": tx.ledger,
        "store": tx.store,
        "context": tx.context,
    }
    digests: dict[str, str] = {}
    loaded = prompts["repository_investigation"]
    investigation = run_job(loaded, investigation_packet(entry, facts, loaded.manifest), **common)
    digests["investigation"] = write_investigation(
        investigation.output, tx.directory / INVESTIGATION_FILENAME
    )
    loaded = prompts["source_reconciliation"]
    reconciled = run_job(
        loaded,
        reconciliation_packet(entry, facts, investigation.output, loaded.manifest),
        checks=functools.partial(reconcile_checks, facts=facts),
        call_schema=reconciliation_schema(loaded, facts),
        **common,
    )
    digests["dispositions"] = write_dispositions(
        reconciled.output, tx.directory / DISPOSITIONS_FILENAME
    )
    loaded = prompts["presentation_planning"]
    planned = run_job(
        loaded,
        planning_packet(entry, facts, investigation.output, reconciled.output, loaded.manifest),
        checks=functools.partial(
            plan_checks,
            facts=facts,
            dispositions=reconciled.output,
            ecosystem=entry.ecosystem,
        ),
        call_schema=planning_schema(loaded, facts),
        **common,
    )
    digests["plan"] = write_plan(planned.output, tx.directory / PLAN_FILENAME)
    loaded = prompts["section_authoring"]
    name = product_name(entry)
    tasks = authoring_tasks(entry, facts, investigation.output, reconciled.output, planned.output)
    authored: dict[str, JobResult] = {}
    for task in tasks:
        authored[task.label] = run_job(
            loaded,
            task.packet,
            checks=functools.partial(unit_checks, task=task, facts=facts, name=name),
            call_schema=authoring_schema(loaded, task),
            **common,
        )
    units = merge_units([(task.section_id, authored[task.label].output) for task in tasks])
    readme = render_readme(entry, facts, planned.output, units, reconciled.output)
    coherent = run_job(
        loaded,
        coherence_packet(entry, readme, units, tasks, facts),
        checks=functools.partial(coherence_checks, tasks=tasks, facts=facts, name=name),
        **common,
    )
    units, revised = apply_coherence(units, coherent.output)
    if revised:
        readme = render_readme(entry, facts, planned.output, units, reconciled.output)
    digests["units"] = write_content_units(units, tx.directory / CONTENT_UNITS_FILENAME)
    digests["readme"] = write_text(readme, tx.directory / README_FILENAME)
    digests["patch"] = write_text(render_patch(tx.original, readme), tx.directory / PATCH_FILENAME)
    # Stage S9 runs exactly the contract's blocking checks over the written artifacts; a
    # failure names its causal stage so repair reopens the cause, never the validation.
    validation = validate_candidate(
        Candidate(
            entry,
            facts,
            planned.output,
            units,
            reconciled.output,
            readme,
            tx.original_bytes,
            tx.source_revision,
            tx.readme_sha256,
            tx.tree_paths,
            tasks,
        ),
        tx.directory,
        tx.secrets,
    )
    digests["validation"] = write_validation(validation, tx.directory / VALIDATION_FILENAME)
    current = Round(
        investigation,
        reconciled,
        planned,
        authored,
        tasks,
        units,
        coherent,
        revised,
        readme,
        validation,
        digests=digests,
    )
    if blocking_failures(validation):
        return current
    # Stage S10 runs only over a candidate every deterministic check accepted, under its own
    # prompt and identity, and writes its verdict into check 10.
    loaded = prompts["independent_review"]
    reviewed = run_job(
        loaded,
        review_packet(
            entry, facts, tx.original, readme, planned.output, reconciled.output, validation
        ),
        checks=functools.partial(review_checks, candidate_readme=readme, facts=facts),
        **common,
    )
    review = review_document(
        reviewed.output,
        loaded,
        prompts["section_authoring"],
        digests["readme"],
        candidate_readme=readme,
        facts=facts,
    )
    digests["review"] = write_review(review, tx.directory / REVIEW_FILENAME)
    validation = record_review_verdict(validation, review)
    digests["validation"] = write_validation(validation, tx.directory / VALIDATION_FILENAME)
    current.validation = validation
    current.reviewed = reviewed
    current.review = review
    return current


def round_defects(current: Round, tx: TransactionInputs) -> list[Defect]:
    """The blocking defects of a round: failing checks first, then the review's findings."""
    repairer = tx.prompts["targeted_repair"].sha256
    review_failed = any(
        check.get("id") == "BC-10" and check.get("verdict") == "FAIL"
        for check in current.validation.get("checks", [])
    )
    checks = [
        check
        for check in current.validation.get("checks", [])
        if check.get("verdict") == "FAIL" and check.get("id") != "BC-10"
    ]
    defects = validation_defects(
        {"checks": checks, "validator_version": current.validation.get("validator_version")},
        current.llm_sections,
        repairer,
    )
    if review_failed:
        defects.extend(review_defects(current.review, tx.facts, current.llm_sections, repairer))
    return defects


def _stage_target(
    current: Round, defect: Defect, facts: FactsDocument, name: str, ecosystem: str
) -> tuple[JobResult, Any, frozenset[str] | None, Mapping[str, frozenset[str]] | None]:
    """The causal stage's accepted result, its own checks, and the fact set it is judged against.

    Only an authored section has a fact set narrower than the corpus; the upstream stages are
    judged against all of it, so they carry None.
    """
    if defect.stage == "S3":
        return current.investigation, None, None, None
    if defect.stage == "S4":
        return current.reconciled, functools.partial(reconcile_checks, facts=facts), None, None
    if defect.stage == "S5":
        return (
            current.planned,
            functools.partial(
                plan_checks,
                facts=facts,
                dispositions=current.reconciled.output,
                ecosystem=ecosystem,
            ),
            None,
            None,
        )
    task = next(task for task in current.tasks if task.section_id == defect.section_id)
    return (
        current.authored[task.label],
        functools.partial(unit_checks, task=task, facts=facts, name=name),
        task.accepted_ids,
        task.slot_facts,
    )


def repair_defect(
    tx: TransactionInputs, current: Round, defect: Defect, repairs: RepairLedger
) -> None:
    """One targeted_repair call; the revised output supersedes the causal stage's stored output."""
    assert defect.stage is not None
    job = STAGE_JOBS[defect.stage]
    causal = tx.prompts[job]
    target, stage_checks, allowed, slot_facts = _stage_target(
        current, defect, tx.facts, product_name(tx.entry), tx.entry.ecosystem
    )
    contract = causal.manifest.output.schema_
    result = run_job(
        tx.prompts["targeted_repair"],
        repair_packet(
            tx.entry,
            defect,
            target.output,
            tx.facts,
            current.review.get("preserve", []),
            contract,
            allowed,
            slot_facts,
        ),
        config=tx.config,
        facts=tx.facts,
        ledger=tx.ledger,
        store=tx.store,
        context=tx.context,
        checks=functools.partial(
            repair_checks,
            defect=defect,
            output_contract=contract,
            binding=causal.manifest.output.binding,
            facts=tx.facts,
            stage_checks=stage_checks,
        ),
    )
    tx.store.put(target.request_sha256, job, result.model_served, result.output["revised_output"])
    repairs.record(defect, "repaired", result.request_sha256, result.output.get("changes", []))


def demote_re_raised(
    tx: TransactionInputs, current: Round, repeated: Sequence[Defect], repairs: RepairLedger
) -> Round:
    """Record the re-raised findings and rewrite review.json and validation.json so the
    verdict follows the blocking findings that remain."""
    for defect in repeated:
        repairs.note_re_raised(defect)
    current.review = demote_findings(current.review, [d.label for d in repeated])
    current.digests["review"] = write_review(current.review, tx.directory / REVIEW_FILENAME)
    current.validation = record_review_verdict(current.validation, current.review)
    current.digests["validation"] = write_validation(
        current.validation, tx.directory / VALIDATION_FILENAME
    )
    return current


def run_transaction(tx: TransactionInputs) -> tuple[Round, RepairLedger, int]:
    """Rounds until the candidate is accepted, a defect cannot be repaired, or a fingerprint
    would be attempted twice; returns the last round, the attempts, and the round count."""
    repairs = RepairLedger(tx.directory / REPAIRS_FILENAME)
    current = run_round(tx)
    rounds = 1
    while rounds < MAX_ROUNDS:
        defects = round_defects(current, tx)
        if not defects:
            break
        for defect in defects:
            if not defect.repairable and not repairs.attempted(defect.fingerprint):
                repairs.record(defect, "unrepairable")
        repeated = [d for d in defects if d.repairable and repairs.attempted(d.fingerprint)]
        if any(d.source == "validation" for d in repeated):
            break  # a blocking check failed again after its one repair: reported, never retried
        if repeated:
            # A review finding re-raised after its one attempt is a reviewer-scope defect:
            # recorded advisory, it never blocks a second time (README_CONTRACT.md section 6).
            current = demote_re_raised(tx, current, repeated, repairs)
            defects = round_defects(current, tx)
            if not defects:
                break
        # One attempt per fingerprint: the round's equivalent defects fold into one repair.
        fresh = merge_equivalent(
            [d for d in defects if d.repairable and not repairs.attempted(d.fingerprint)]
        )
        if not fresh:
            break
        for defect in fresh:
            repair_defect(tx, current, defect, repairs)
        current = run_round(tx)
        rounds += 1
    return current, repairs, rounds
