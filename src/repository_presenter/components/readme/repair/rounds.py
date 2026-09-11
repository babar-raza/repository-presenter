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
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    CONTENT_UNITS_FILENAME,
    SectionTask,
    authoring_schema,
    authoring_tasks,
    merge_units,
    reconstructed_task_output,
    unit_checks,
    write_content_units,
)
from repository_presenter.components.readme.composition.coherence import (
    apply_coherence,
    coherence_checks,
    coherence_packet,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.components.readme.composition.placement import placed_texts, placements
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
    renderer_sentences,
    write_text,
)
from repository_presenter.components.readme.investigation.dossier import (
    INVESTIGATION_FILENAME,
    investigation_packet,
    write_investigation,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    DISPOSITIONS_FILENAME,
    merge_dispositions,
    reconcile_checks,
    reconciliation_batch_facts,
    reconciliation_batches,
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
    SlotSetProbe,
    defect_fingerprint,
    merge_equivalent,
    repair_checks,
    repair_packet,
    review_defects,
    validation_defects,
)
from repository_presenter.components.readme.review.independent.review import (
    REVIEW_FILENAME,
    prose_judgment,
    review_checks,
    review_document,
    review_packet,
    second_reader,
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
from repository_presenter.core.errors import JobError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import (
    CallStore,
    JobContext,
    JobResult,
    request_hash,
    run_job,
)
from repository_presenter.core.llm.ledger import Ledger, canonical_hash
from repository_presenter.core.llm.prompts import LoadedManifest, PromptRegistry
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
    # G5-W02 (27.2 RC4): a sealed bundle for this exact revision, when one exists, so an
    # authoring task whose accepted output is reconstructable from it seeds the store before
    # its own run_job call rather than making a call the bundle already answers.
    sealed_bundle: Path | None = None


@dataclass
class Round:
    """The accepted outputs of one composition round and the judgement over them."""

    investigation: JobResult
    # PHASE0/G: one JobResult per source_reconciliation batch, keyed like `authored` (batch_id ->
    # its own call) - `dispositions` below is the merged, flat document every downstream reader
    # already expects, the same authored/units split this dataclass already uses.
    reconciled: dict[str, JobResult]
    dispositions: dict[str, Any]
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


def _second_opinion(
    loaded: LoadedManifest, packet: Mapping[str, Any], checks: Any, common: Mapping[str, Any]
) -> dict[str, Any] | None:
    """The second reader's output, or ``None`` when the job raised ``JobError`` - never ``{}``,
    which ``review_document`` reads as a completed reading that corroborated nothing (TB-04)."""
    try:
        return run_job(second_reader(loaded), packet, checks=checks, **common).output
    except JobError:
        return None


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
    # PHASE0/G: one run_job() call per batch, the same shape section_authoring's own loop below
    # already proves (composition/authoring.py's _type_batches()) - a repository whose inherited
    # units exceed one call's own output budget (measured, not hypothetical: Cells-Rust genuinely
    # truncates at 91 units, docs/DECISION_LOG.md) gets several bounded calls instead of one
    # unbounded one. reconcile_checks judges each batch's own dispositions independently (per-
    # entry, no cross-entry logic - checked directly, not assumed), so a per-batch check is exactly
    # as strict as the old whole-document check was.
    reconciled: dict[str, JobResult] = {}
    for batch_id, batch_units in reconciliation_batches(facts):
        # Real bug, found live against Cells-Rust (docs/DECISION_LOG.md): core/llm/binding.py's
        # binding_errors recomputes "every inherited unit expected" from whatever FactsDocument
        # is passed as the job's own facts= - the whole repository's, unless narrowed here - so
        # every batch's own call needs its own batch-scoped view, not just a batch-scoped
        # packet/schema, or every batch but the last is rejected for "missing" units it was never
        # asked to cover.
        batch_facts = reconciliation_batch_facts(facts, batch_units)
        reconciled[batch_id] = run_job(
            loaded,
            reconciliation_packet(
                entry, batch_facts, investigation.output, loaded.manifest, batch_units
            ),
            checks=functools.partial(reconcile_checks, facts=batch_facts),
            call_schema=reconciliation_schema(loaded, batch_units),
            **{**common, "facts": batch_facts},
        )
    dispositions = merge_dispositions([result.output for result in reconciled.values()])
    digests["dispositions"] = write_dispositions(dispositions, tx.directory / DISPOSITIONS_FILENAME)
    loaded = prompts["presentation_planning"]
    planned = run_job(
        loaded,
        planning_packet(entry, facts, investigation.output, dispositions, loaded.manifest),
        checks=functools.partial(
            plan_checks,
            facts=facts,
            dispositions=dispositions,
            ecosystem=entry.ecosystem,
        ),
        call_schema=planning_schema(loaded, facts),
        **common,
    )
    digests["plan"] = write_plan(planned.output, tx.directory / PLAN_FILENAME)
    loaded = prompts["section_authoring"]
    name = product_name(entry)
    tasks = authoring_tasks(entry, facts, investigation.output, dispositions, planned.output)
    authored: dict[str, JobResult] = {}
    for task in tasks:
        call_schema = authoring_schema(loaded, task)
        # G5-W02 (27.2 RC4): a fresh clone of an already-sealed revision has nothing in its own
        # runs/ to reuse, but the sealed bundle's own content_units.json may already answer this
        # exact task - seed the store at the hash this call would use before making it.
        if tx.sealed_bundle is not None:
            task_hash = request_hash(loaded, task.packet, call_schema)
            if tx.store.get(task_hash) is None:
                reconstructed = reconstructed_task_output(
                    tx.sealed_bundle, task, facts, loaded.sha256
                )
                if reconstructed is not None:
                    tx.store.put(task_hash, loaded.manifest.prompt_id, None, reconstructed)
        authored[task.label] = run_job(
            loaded,
            task.packet,
            checks=functools.partial(unit_checks, task=task, facts=facts, name=name),
            call_schema=call_schema,
            **common,
        )
    units = merge_units([(task.section_id, authored[task.label].output) for task in tasks])
    readme = render_readme(entry, facts, planned.output, units, dispositions)
    coherent = run_job(
        loaded,
        coherence_packet(entry, readme, units, tasks, facts),
        checks=functools.partial(coherence_checks, tasks=tasks, facts=facts, name=name),
        **common,
    )
    units, revised = apply_coherence(units, coherent.output)
    if revised:
        readme = render_readme(entry, facts, planned.output, units, dispositions)
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
            dispositions,
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
        dispositions,
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
    packet = review_packet(
        entry, facts, tx.original, readme, planned.output, dispositions, validation
    )
    checks = functools.partial(review_checks, candidate_readme=readme, facts=facts)
    reviewed = run_job(loaded, packet, checks=checks, **common)
    document = functools.partial(
        review_document,
        reviewed.output,
        loaded,
        prompts["section_authoring"],
        digests["readme"],
        candidate_readme=readme,
        facts=facts,
        original_readme=tx.original,
        rendered=renderer_sentences(entry, facts, planned.output, current.units, dispositions),
    )
    review = document()
    # A prose judgment on a required row is read a second time under a different seed before it
    # holds the candidate unsealed (the owner's two-reader rule, section 27.8). The second read
    # only ever removes a finding from the blocking set, so a read that cannot produce usable
    # output corroborates nothing and must leave `review` exactly as the first reader alone
    # produced it (never `document(second={})` - TB-04, external review D4, 2026-09-08: an empty
    # dict is not `None`, and review_document reads it as a *completed* reading that raised no
    # findings, silently demoting the first reader's finding and flipping REJECT_PRESENTATION to
    # ACCEPT while recording `second_reader.read` true for a reading that never happened). Losing
    # verification must never increase assurance.
    if any(prose_judgment(finding) for finding in review["findings"]):
        second = _second_opinion(loaded, packet, checks, common)
        if second is not None:
            review = document(second=second)
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
        # A finding's causal_stage is a model guess with no cross-check; a mechanical one is
        # cheap and available here - whether its quote is a placed, preserved/moved unit's own
        # text, which authoring never wrote and cannot revise regardless of the guess (RC-04,
        # RESEARCH_AND_GUIDELINES.md 27.2 RC4/SW4, 2026-09-08).
        placed = placed_texts(
            placements(
                current.planned.output,
                current.dispositions,
                tx.facts,
                tx.entry.ecosystem,
            )
        )
        defects.extend(
            review_defects(current.review, tx.facts, current.llm_sections, repairer, placed)
        )
    return defects


def _stage_target(
    current: Round, defect: Defect, facts: FactsDocument, name: str, ecosystem: str
) -> tuple[
    JobResult, Any, frozenset[str] | None, Mapping[str, frozenset[str]] | None, FactsDocument
]:
    """The causal stage's accepted result, its own checks, the fact set it is judged against, and
    the fact set its own binding check (``core/llm/binding.py``) must be judged against.

    Only an authored section has a fact set narrower than the corpus; the upstream stages are
    judged against all of it, so they carry None. The two fact-set values agree everywhere except
    S4 (see below) - a real, found-live divergence, not a hypothetical one.
    """
    if defect.stage == "S3":
        return current.investigation, None, None, None, facts
    if defect.stage == "S4":
        # PHASE0/G: an S4 defect names no batch - `_check_dispositions` (validation/registry.py)
        # constructs every RECONCILING-stage Failure with no structured section/unit identifier,
        # the same real, pre-existing gap `_stage_target`'s own S6 branch below already has for a
        # batched section_authoring task (its `next(... section_id == defect.section_id)` can
        # only ever resolve to a section's *main* task, never one of its batches either) -
        # checked directly against the shipped code, not assumed. Not a new regression this
        # taskcard introduces: the first batch, sorted by key, matching the same
        # first-match-only imprecision section_authoring's own precedent already ships with.
        # Repair's own repeated-failure discipline (round_defects, run_transaction) still catches
        # and reports a repair that targeted the wrong batch - it is never silently accepted.
        # dict insertion order, not sorted(keys) - "reconciliation#10" would sort before
        # "reconciliation#2" lexicographically; current.reconciled is built in batch order.
        first_batch_id = next(iter(current.reconciled))
        batch_units = dict(reconciliation_batches(facts))[first_batch_id]
        batch_facts = reconciliation_batch_facts(facts, batch_units)
        # Real bug, found live against Cells-Rust: repair_checks's own binding_errors call
        # (repair/targeted.py) needs the SAME batch-scoped facts reconciliation_batch_facts()
        # already fixed this for at the original call site (rounds.py's run_round loop) - a
        # repair revising one batch's ~40 units must not be judged against all 91 units' worth
        # of "expected" coverage either, the identical shape of the same underlying gap.
        return (
            current.reconciled[first_batch_id],
            functools.partial(reconcile_checks, facts=batch_facts),
            None,
            None,
            batch_facts,
        )
    if defect.stage == "S5":
        return (
            current.planned,
            functools.partial(
                plan_checks,
                facts=facts,
                dispositions=current.dispositions,
                ecosystem=ecosystem,
            ),
            None,
            None,
            facts,
        )
    task = next(task for task in current.tasks if task.section_id == defect.section_id)
    return (
        current.authored[task.label],
        functools.partial(unit_checks, task=task, facts=facts, name=name),
        task.accepted_ids,
        task.slot_facts,
        facts,
    )


def repair_defect(
    tx: TransactionInputs, current: Round, defect: Defect, repairs: RepairLedger
) -> None:
    """One targeted_repair call; the revised output supersedes the causal stage's stored output.

    The stage a finding names is not always the stage that can satisfy its repair. S6's per-task
    schema requires exactly the plan's slots, so a fix that would add, drop, or re-choose one is a
    planning decision by construction - proven here by the repair's own reply, a comparison of two
    slot sets, never inferred from the finding's prose. Such a repair escalates once to a
    plan-level repair at S5 carrying the finding's context, and the revised plan re-enters S6
    through S8 through the next round like any other planning change (section 27.2, the 2026-09-05
    decision). Any other exhausted repair - and one still unable to produce a schema-valid
    revision after the escalation - is recorded unrepairable at this attempt and reported, exactly
    like a defect no stage could ever reach (section 27.5 D5).
    """
    assert defect.stage is not None
    job = STAGE_JOBS[defect.stage]
    causal = tx.prompts[job]
    target, stage_checks, allowed, slot_facts, stage_facts = _stage_target(
        current, defect, tx.facts, product_name(tx.entry), tx.entry.ecosystem
    )
    contract = causal.manifest.output.schema_
    probe = _slot_set_probe(current, defect)
    try:
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
                # PHASE0/G: the causal stage's OWN binding check (unit_ids for S4) must be judged
                # against the same fact set that stage's own call was - stage_facts, not tx.facts
                # unconditionally; they agree everywhere except S4's batch scoping.
                facts=stage_facts,
                stage_checks=stage_checks,
                slots=probe,
            ),
        )
    except JobError as exc:
        if probe is not None and probe.conflicts:
            escalate_to_plan(tx, current, defect, repairs, probe)
            return
        repairs.record(replace(defect, reason=str(exc)), "unrepairable")
        return
    tx.store.put(target.request_sha256, job, result.model_served, result.output["revised_output"])
    repairs.record(defect, "repaired", result.request_sha256, result.output.get("changes", []))


def _slot_set_probe(current: Round, defect: Defect) -> SlotSetProbe | None:
    """The plan's own slot set for an authored section's repair; None for every other stage."""
    if defect.stage != "S6":
        return None
    task = next(
        (task for task in current.tasks if task.section_id == defect.section_id),
        None,
    )
    return None if task is None else SlotSetProbe(frozenset(task.slots))


def escalate_to_plan(
    tx: TransactionInputs,
    current: Round,
    defect: Defect,
    repairs: RepairLedger,
    probe: SlotSetProbe,
) -> None:
    """Route a slot-set change to the stage that owns it, once, carrying the finding's context.

    The escalated defect keeps the finding's record and takes its own fingerprint, derived from
    the attempt that proved the need, so run_transaction's one-attempt-per-fingerprint rule allows
    exactly one escalation and no more.
    """
    returned = ", ".join(sorted(probe.returned or ())) or "no slot"
    reason = (
        f"the revision would leave {returned} where the plan assigned "
        f"{', '.join(sorted(probe.required))}; escalated once to a plan-level repair at S5"
    )
    repairs.record(replace(defect, reason=reason), "escalated")
    escalated = replace(
        defect,
        fingerprint=defect_fingerprint(defect.source, None, "S5", defect.label, defect.fingerprint),
        section_id=None,
        stage="S5",
        reason=None,
    )
    repair_defect(tx, current, escalated, repairs)


def composition_id(tx: TransactionInputs) -> str:
    """What this composition is built from: the revision, the facts, and the prompt set.

    The repair ledger is scoped to it. Every round of one composition sees the same value, and a
    replay sees it again, because a repair rewrites a stored response and never these inputs; a
    composition rebuilt on new facts or a changed prompt sees a different one, which is the
    changed evidence the contract's one-attempt rule asks for (docs/README_CONTRACT.md section 6).
    """
    return canonical_hash(
        {
            "revision": tx.source_revision,
            "facts": tx.facts.to_json(),
            "prompts": dict(sorted(tx.prompts.hashes().items())),
        }
    )


def run_transaction(tx: TransactionInputs) -> tuple[Round, RepairLedger, int]:
    """Rounds until the candidate is accepted, a defect cannot be repaired, or a fingerprint
    would be attempted twice; returns the last round, the attempts, and the round count."""
    repairs = RepairLedger(tx.directory / REPAIRS_FILENAME, composition=composition_id(tx))
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
        if repeated:
            # A defect re-raised after its one repair attempt never demotes, whatever its
            # source: acceptance is decided by content, never by directory history
            # (RESEARCH_AND_GUIDELINES.md section 27.2 RC5, section 27.5 D5). It is code-caused
            # - add the check, per section 26 - or it blocks; either way it is reported here,
            # never retried a third time from a different mechanism. A validation check and a
            # review finding are held to the one rule, so neither gets a demotion path the
            # other lacks.
            for defect in repeated:
                repairs.note_re_raised(defect)
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
