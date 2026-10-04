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

import copy
import functools
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    CONTENT_UNITS_FILENAME,
    RAW_CALLS_FILENAME,
    SectionTask,
    authoring_schema,
    authoring_tasks,
    merge_units,
    reconstructed_task_output,
    recover_carried_units,
    recover_section_authoring_output,
    recover_title_verbatim_opening,
    repair_title_verbatim_opening_errors,
    unit_checks,
    write_content_units,
    write_raw_calls,
)
from repository_presenter.components.readme.composition.coherence import (
    apply_coherence,
    coherence_batch_units,
    coherence_batches,
    coherence_checks,
    coherence_packet,
    coherence_schema,
    recover_coherence_content_loss,
)
from repository_presenter.components.readme.composition.components.identity import product_name
from repository_presenter.components.readme.composition.placement import placed_texts, placements
from repository_presenter.components.readme.composition.planning import (
    PLAN_FILENAME,
    bound_visible_line_overage,
    plan_checks,
    planning_packet,
    planning_schema,
    recover_uncited_capability_titles,
    recover_visible_line_overage,
    write_plan,
)
from repository_presenter.components.readme.composition.policy import DEFAULT_POLICY
from repository_presenter.components.readme.composition.renderer import (
    PATCH_FILENAME,
    README_FILENAME,
    line_counts,
    render_patch,
    render_readme,
    renderer_sentences,
    write_text,
)
from repository_presenter.components.readme.investigation.dossier import (
    INVESTIGATION_FILENAME,
    investigation_packet,
    investigation_schema,
    write_investigation,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    DISPOSITIONS_FILENAME,
    coordinate_neighbor_promises,
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
    repair_schema,
    review_defects,
    validation_defects,
    visible_line_budget_hint,
)
from repository_presenter.components.readme.review.acceptance.scorer import score_candidate
from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    MAJORITY_VOTE_REPOSITORIES,
    REVIEW_FILENAME,
    prose_judgment,
    review_checks,
    review_document,
    review_packet,
    second_reader,
    third_reader,
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
    effective_model,
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
    # PDFPY-03: one JobResult per coherence batch now, keyed like `reconciled`/`authored` above
    # (batch_id -> its own call) - the loop above may make several calls where there used to be
    # exactly one.
    coherent: dict[str, JobResult]
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
) -> JobResult | None:
    """The second reader's own ``JobResult``, or ``None`` when the job raised ``JobError`` - never
    an empty output, which ``review_document`` reads as a completed reading that corroborated
    nothing (TB-04). Returns the whole ``JobResult``, not just ``.output`` (G5-W02): the caller
    needs ``.request_sha256`` too, to seal this read's own raw output under its own call's own key
    in ``raw_calls.json`` - ``review.json`` alone cannot always answer for it on a later replay
    (a rejected first read never carries the second reader's own non-blocking findings forward)."""
    try:
        return run_job(second_reader(loaded), packet, checks=checks, **common)
    except JobError:
        return None


def _third_opinion(
    loaded: LoadedManifest, packet: Mapping[str, Any], checks: Any, common: Mapping[str, Any]
) -> JobResult | None:
    """The third reader's own ``JobResult`` for a 2-of-3 majority-vote escalation (section 5.6),
    or ``None`` when the job raised ``JobError`` - mirrors ``_second_opinion`` exactly, including
    returning the whole ``JobResult`` rather than just ``.output`` (G5-W02)."""
    try:
        return run_job(third_reader(loaded), packet, checks=checks, **common)
    except JobError:
        return None


def _raw_call_entry(result: JobResult) -> dict[str, Any]:
    """One ``raw_calls.json`` entry for ``result`` (G5-W02): the shape
    ``composition/authoring.py::write_raw_calls`` and ``bundle/seal.py::seed_additional_calls``
    both already document and agree on.

    Deliberately excludes ``result.model_served``: ``core/llm/jobs.py::run_job`` hardcodes it to
    ``None`` on its own cache-reuse path (never the originally-served model name), so a round that
    reuses a prior call - exactly the no-op-proof rerun this item's own acceptance bar names -
    would otherwise write a ``raw_calls.json`` that differs from the one the original, live call
    wrote, falsely tripping the byte-identical no-op comparison (measured live: hosted CI's own
    canary no-op proof, `AssertionError: assert 'ACCEPTED' == 'READY_FOR_PROPOSAL'`, `raw_calls.
    json changed since the last seal`). Neither `investigation.json`/`dispositions.json`/`plan.
    json` ever carry `model_served` in their own sealed content for the identical reason - only
    `calls.jsonl` does, and that file is `bundle/seal.py::REPLAY_EXEMPT` precisely because it
    carries exactly this kind of per-run-only metadata."""
    return {"job": result.job, "output": result.output}


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
    # G4-W17 arrival item 105 (E22): the one fact-citing job with no call_schema of its own,
    # unlike the reconciliation/planning/authoring calls below - pinned to the packet's own
    # fact_dossier so a hallucinated fact ID is refused at decode, not after a spent call.
    investigation = run_job(
        loaded,
        investigation_packet(entry, facts, loaded.manifest),
        call_schema=investigation_schema(loaded, facts),
        **common,
    )
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
    for batch_id, batch_units in reconciliation_batches(
        facts, loaded.manifest.sampling.max_output_tokens
    ):
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
            call_schema=reconciliation_schema(
                loaded, batch_units, batch_facts, investigation.output
            ),
            **{**common, "facts": batch_facts},
        )
    dispositions = merge_dispositions([result.output for result in reconciled.values()])
    # BC-10 coherence-gap (docs/DECISION_LOG.md 2026-09-17 14:14 UTC / 2026-09-24 10:14 UTC): each
    # batch above is checked independently of every other batch (reconcile_checks has no
    # cross-entry logic, by design), so a unit's own dependency on a *different* unit - possibly
    # reconciled in a different batch - was never re-examined once every batch's own output is
    # known. Runs once here, after every batch is merged into one flat document.
    coordinate_neighbor_promises(dispositions, facts)
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
        call_schema=planning_schema(loaded, facts, investigation.output, dispositions),
        recover=functools.partial(recover_uncited_capability_titles, facts=facts),
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
            task_hash = request_hash(
                loaded,
                task.packet,
                call_schema,
                model=effective_model(loaded, tx.context),
            )
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
            # G4-W17, docs/DECISION_LOG.md 2026-09-24 14:25 UTC (PROPOSAL, Page-Python's
            # first-ever seal attempt) and 2026-09-27 (docs/DEFECT_INDEX.md
            # section_authoring.rejection_no_recover, 4th sighting, aspose-slides-foss/
            # Aspose.Slides-FOSS-for-Java): symmetric to presentation_planning's own recover=
            # above (item 111/PGPY-04) - a final rejection whose re-ask reproduced a
            # _FORBIDDEN command marker byte-for-byte, OR whose own correction of an unrelated
            # rejection incidentally stripped the detail item 106's title-restatement carve-out
            # needed, gets one deterministic last-resort correction (composed - either, both,
            # or neither may apply), re-validated through the real unit_checks before ever
            # being accepted.
            recover=functools.partial(
                recover_section_authoring_output,
                slot_titles=task.slot_titles,
                must_carry=task.must_carry,
            ),
            **common,
        )
    units = merge_units([(task.section_id, authored[task.label].output) for task in tasks])
    readme = render_readme(entry, facts, planned.output, units, dispositions)
    # PDFPY-03 (docs/DECISION_LOG.md 2026-09-17 09:18 UTC, corroborated 2026-09-24 14:20 UTC): one
    # call asking for every LLM-owned unit back at once truncates at the shared
    # max_output_tokens=8000 cap once the document grows large enough (measured on PDF-Python and
    # Font-Python, both aborting the whole transaction with no README produced). One run_job() call
    # per coherence batch now, the same shape source_reconciliation's own loop above and
    # section_authoring's own _type_batches() already prove for the identical class of problem.
    # Each batch's own call still receives the *current* full rendered document and every current
    # unit for context (coherence_packet's own existing_units/rendered_document fields are
    # unscoped) - only the reply itself is narrowed to the batch's own units. The document is
    # re-rendered after any batch that actually revised something, so a later batch judges its own
    # section against a document that already reflects every earlier batch's revisions - cross-
    # batch consistency stays genuinely checked, not silently dropped.
    coherent: dict[str, JobResult] = {}
    revised: list[str] = []
    for batch_id, batch_tasks in coherence_batches(tasks):
        batch_packet = coherence_packet(entry, readme, units, batch_tasks, facts)
        return_units = coherence_batch_units(batch_packet["existing_units"], batch_tasks)
        coherent[batch_id] = run_job(
            loaded,
            batch_packet,
            checks=functools.partial(
                coherence_checks,
                tasks=batch_tasks,
                facts=facts,
                name=name,
                # G3-W05 (docs/DEFECT_INDEX.md composition.coherence.inherited_diagram_content_
                # loss): this batch's own pre-coherence units, so a revision that silently drops a
                # previously-cited fact's content is rejected here rather than left to whichever
                # draw's independent-review sample happens to notice it.
                existing_units=return_units,
            ),
            call_schema=coherence_schema(loaded, return_units, batch_tasks),
            # G3-W05: this call site had no recover= at all before this item - a final rejection
            # always raised JobError outright. The one deterministic last resort available for the
            # content-loss shape above: revert exactly the unit(s) that dropped untraced content
            # to their own pre-coherence text/fact_ids, never the whole batch.
            recover=functools.partial(
                recover_coherence_content_loss, existing_units=return_units, facts=facts
            ),
            **common,
        )
        units, batch_revised = apply_coherence(units, coherent[batch_id].output)
        if batch_revised:
            readme = render_readme(entry, facts, planned.output, units, dispositions)
        revised.extend(batch_revised)
    digests["units"] = write_content_units(units, tx.directory / CONTENT_UNITS_FILENAME)
    digests["readme"] = write_text(readme, tx.directory / README_FILENAME)
    digests["patch"] = write_text(render_patch(tx.original, readme), tx.directory / PATCH_FILENAME)
    # G5-W02 (27.2 RC4's own remaining gap): raw_calls.json seals every accepted call above that
    # no other sealed artifact already answers for verbatim - every coherence batch, plus a batch
    # section_authoring task (a non-batch one is already reconstructed from content_units.json
    # alone by reconstructed_task_output, seeded before its own run_job call further up). Written
    # now so a round that stops at blocking_failures below (never reaching review) still seals
    # whatever it made; the review block further down adds its own reads and rewrites this same
    # file, exactly like digests["validation"] is written once here and again after review.
    raw_calls: dict[str, dict[str, Any]] = {
        result.request_sha256: _raw_call_entry(result) for result in coherent.values()
    }
    raw_calls.update(
        {
            authored[task.label].request_sha256: _raw_call_entry(authored[task.label])
            for task in tasks
            if task.is_batch
        }
    )
    digests["raw_calls"] = write_raw_calls(raw_calls, tx.directory / RAW_CALLS_FILENAME)
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
        # G4-W17 arrival item 62: the fold stack reads which quoted text a unit actually wrote.
        units=current.units,
        # G4-W17 arrival item 86: the fold stack also learns which inherited_unit reconciliation
        # itself marked OMIT_UNSUPPORTED, so a finding demanding it back is the reviewer's own
        # defect rather than a doomed block - review.py's own excluded_disposition_defect was
        # already landed inert (c37791f) pending exactly this one line.
        dispositions=dispositions,
    )
    review = document()
    # Two triggers share the one corroborating read under a different seed. A prose judgment on
    # a required row is read a second time before it holds the candidate unsealed (the owner's
    # two-reader rule, section 27.8). And an ACCEPT - returned, or a rejection whose every
    # finding folded to advisory, the class 8 of the 9 pre-sprint seals belong to - is read a
    # second time before it seals the candidate (PHASE1/F6): check 10 now passes only a
    # corroborated accept (second_reader.read >= 2), and on this path the second read's findings
    # pass the same fold stack as the first read's, so a disagreement blocks and repairs through
    # the normal rounds. A read that cannot produce usable output corroborates nothing and must
    # leave `review` exactly as the first reader alone produced it (never `document(second={})` -
    # TB-04, external review D4, 2026-09-08: an empty dict is not `None`, and review_document
    # reads it as a *completed* reading that raised no findings, silently demoting the first
    # reader's finding and flipping REJECT_PRESENTATION to ACCEPT while recording a reading that
    # never happened). Losing verification must never increase assurance - which on the accept
    # path now means the uncorroborated ACCEPT fails check 10 rather than sealing. A repository
    # named in MAJORITY_VOTE_REPOSITORIES (section 5.6) escalates this to a 2-of-3 vote among
    # three independent reads instead of one confirming read - see the branch just below.
    second_result: JobResult | None = None
    third_result: JobResult | None = None
    if review["verdict"] == ACCEPT or any(
        prose_judgment(finding) for finding in review["findings"]
    ):
        second_result = _second_opinion(loaded, packet, checks, common)
        if second_result is not None:
            if tx.entry.repository in MAJORITY_VOTE_REPOSITORIES:
                # Section 5.6 escalation: this repository's own documented rerun history
                # (docs/DECISION_LOG.md) already shows two or more distinct S10 findings across
                # independent draws, so promoting to ACCEPT needs a 2-of-3 majority among three
                # independent reads rather than one confirming read alone. A failed third read
                # (JobError) falls back to the unescalated single-confirming-read rule below,
                # never to a looser one - losing verification must never increase assurance.
                third_result = _third_opinion(loaded, packet, checks, common)
                third_output = third_result.output if third_result is not None else None
                review = document(second=second_result.output, third=third_output)
            else:
                review = document(second=second_result.output)
    validation = record_review_verdict(validation, review)
    # G3-W02 ADVISORY: the acceptance score is recorded with the review. No blocking check reads
    # it, and it is computed after check 10 so the record sees the same verdicts the bundle does.
    review["acceptance_profile"] = score_candidate(readme, validation, review)
    digests["review"] = write_review(review, tx.directory / REVIEW_FILENAME)
    digests["validation"] = write_validation(validation, tx.directory / VALIDATION_FILENAME)
    # G5-W02: the review reads above are not covered by anything else that seals verbatim output
    # (review.json folds first/second/third into findings/advisory, losing a corroborating read's
    # own non-blocking findings whenever the first read already rejected - see write_raw_calls's
    # own docstring), so they join the raw_calls.json this round already wrote after coherence.
    raw_calls[reviewed.request_sha256] = _raw_call_entry(reviewed)
    if second_result is not None:
        raw_calls[second_result.request_sha256] = _raw_call_entry(second_result)
    if third_result is not None:
        raw_calls[third_result.request_sha256] = _raw_call_entry(third_result)
    digests["raw_calls"] = write_raw_calls(raw_calls, tx.directory / RAW_CALLS_FILENAME)
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


def _refuse_noop(
    original: dict[str, Any], checks: Callable[[dict[str, Any]], list[str]] | None
) -> Callable[[dict[str, Any]], list[str]]:
    """Wrap a causal stage's own checks so a revision proven identical to the stage's own output
    is refused before those checks even run.

    Measured live (RESEARCH_LANE_E.md E16, arrival item 84: Font for Python's S9 BC-07 blocker).
    A repair asked to shrink an already schema-maximal plan can satisfy schema, binding, slot-set,
    and the causal stage's own checks by returning the SAME output it was given - nothing compared
    the reply to its input, so the no-op cleared every check, was recorded "repaired", and only
    the next round's re-validation discovered nothing had changed, by when the
    one-attempt-per-fingerprint rule had already spent its only try. `repair_checks`
    (`repair/targeted.py`) is not this work item's file to edit, so the refusal lives here, at the
    one seam `_stage_target` already owns for every causal stage - S3, S4, S5, and S6 alike, not
    just the S5 case this was measured on, since nothing about the mechanism is S5-specific.
    """

    def guarded(revised: dict[str, Any]) -> list[str]:
        if revised == original:
            return [
                "matches the causal stage's own output unchanged; a no-op cannot repair a "
                "defect this stage's content did not change"
            ]
        return list(checks(revised)) if checks is not None else []

    return guarded


def _reject_title_verbatim_opening(
    checks: Callable[[dict[str, Any]], list[str]] | None, task: SectionTask
) -> Callable[[dict[str, Any]], list[str]]:
    """Layer independent review's own stricter title-restatement standard onto an S6 repair's own
    stage_checks - never onto ``unit_checks`` itself, which stays exactly as permissive as before
    for a fresh ``section_authoring`` draft (docs/DECISION_LOG.md 2026-09-25 08:04 UTC,
    aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python BC-10 F03).

    ``unit_checks``'s own item-106 carve-out exempts a unit whose text opens with its own title
    restated verbatim once real member-level detail follows it - correct for a genuinely
    single-purpose capability with no compliant paraphrase at all (item 106, PDF-Cpp), which a
    fresh draft has no narrower context to fix. A *repair*, reacting to review's own finding that
    the literal opening clause itself is generic regardless of what trails it, has a narrower job:
    revise the flagged clause, not merely add detail after it. Scoped to the repair path only, so
    a first-draft unit this exact shape (PDF-Cpp's own case) is still accepted exactly as before.
    """

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors = list(checks(revised)) if checks is not None else []
        errors.extend(repair_title_verbatim_opening_errors(revised, task))
        return errors

    return guarded


def _reject_insufficient_visible_line_overage(
    checks: Callable[[dict[str, Any]], list[str]] | None, hint: Mapping[str, Any]
) -> Callable[[dict[str, Any]], list[str]]:
    """Layer a deterministic visible-line-budget check onto a BC-07 repair's own S5
    ``stage_checks`` - never onto ``plan_checks`` itself, which has no visible-line notion at all
    (rendering the whole document only happens downstream, at S9).

    G4-W17 (docs/DECISION_LOG.md 2026-09-17 10:24 UTC, 2026-09-27 05:14 UTC): measured live on
    aspose-font-foss/Aspose.Font-FOSS-for-Python, the repair packet's own ``visible_line_budget``
    hint (naming the exact, measured cost of clearing an optional example-selection field) was not
    enough on its own - the model's one repair attempt still made an unrelated, self-reported
    no-op prose edit instead, twice, across two independent live draws. Without a check that can
    actually see whether a lever was used, the job's one universal re-ask has nothing informed to
    react to (the same class item 111/PGPY-04 already fixed for an uncited capability title).
    Rejects only when every named lever field is still set exactly as the causal stage's own
    output had it - a reply that clears even one has done everything this check asks and is never
    rejected for guessing which lever, or how many, to use.
    """
    levers = hint.get("optional_plan_fields_and_their_visible_line_cost_if_cleared") or {}

    def guarded(revised: dict[str, Any]) -> list[str]:
        errors = list(checks(revised)) if checks is not None else []
        if levers and all(revised.get(field) is not None for field in levers):
            named = ", ".join(sorted(levers))
            errors.append(
                f"revised_output: the plan is {hint['visible_lines_over_budget']} visible lines "
                f"over budget and none of the named optional fields ({named}) was cleared; set "
                "at least one to null - the same verified example stays fully present in its "
                "section's own collapsed block, this only stops duplicating it visibly"
            )
        return errors

    return guarded


def _stage_target(
    current: Round,
    defect: Defect,
    facts: FactsDocument,
    name: str,
    ecosystem: str,
    prompts: PromptRegistry,
) -> tuple[
    JobResult, Any, frozenset[str] | None, Mapping[str, frozenset[str]] | None, FactsDocument
]:
    """The causal stage's accepted result, its own checks, the fact set it is judged against, and
    the fact set its own binding check (``core/llm/binding.py``) must be judged against.

    Only an authored section has a fact set narrower than the corpus; the upstream stages are
    judged against all of it, so they carry None. The two fact-set values agree everywhere except
    S4 (see below) - a real, found-live divergence, not a hypothetical one. Every branch's checks
    are wrapped in ``_refuse_noop`` against that stage's own accepted output, so a repair reply
    proven identical to what it was meant to revise is refused, never recorded "repaired".
    """
    if defect.stage == "S3":
        return (
            current.investigation,
            _refuse_noop(current.investigation.output, None),
            None,
            None,
            facts,
        )
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
        # The budget is read here, where batching happens, from the same manifest run_round splits
        # with. Read eagerly by the caller it would require source_reconciliation for every repair,
        # including stages that never batch.
        reconciliation_budget = prompts["source_reconciliation"].manifest.sampling.max_output_tokens
        batch_units = dict(reconciliation_batches(facts, reconciliation_budget))[first_batch_id]
        batch_facts = reconciliation_batch_facts(facts, batch_units)
        # Real bug, found live against Cells-Rust: repair_checks's own binding_errors call
        # (repair/targeted.py) needs the SAME batch-scoped facts reconciliation_batch_facts()
        # already fixed this for at the original call site (rounds.py's run_round loop) - a
        # repair revising one batch's ~40 units must not be judged against all 91 units' worth
        # of "expected" coverage either, the identical shape of the same underlying gap.
        return (
            current.reconciled[first_batch_id],
            _refuse_noop(
                current.reconciled[first_batch_id].output,
                functools.partial(reconcile_checks, facts=batch_facts),
            ),
            None,
            None,
            batch_facts,
        )
    if defect.stage == "S5":
        return (
            current.planned,
            _refuse_noop(
                current.planned.output,
                functools.partial(
                    plan_checks,
                    facts=facts,
                    dispositions=current.dispositions,
                    ecosystem=ecosystem,
                ),
            ),
            None,
            None,
            facts,
        )
    task = next(task for task in current.tasks if task.section_id == defect.section_id)
    return (
        current.authored[task.label],
        _refuse_noop(
            current.authored[task.label].output,
            functools.partial(unit_checks, task=task, facts=facts, name=name),
        ),
        task.accepted_ids,
        task.slot_facts,
        facts,
    )


def _with_carried_units(
    recover: Callable[[dict[str, Any]], dict[str, Any] | None], must_carry: frozenset[str]
) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    """A repair's own last-resort recovery, extended with the must-carry omission record.

    A ``targeted_repair`` reply wraps its units in ``revised_output``, so the carry recovery runs
    on that shape, after the title recovery; with nothing to carry the recovery is returned
    unchanged. Each step is re-validated by the repair's real checks (unit_checks included)."""
    if not must_carry:
        return recover

    def recovered(output: dict[str, Any]) -> dict[str, Any] | None:
        first = recover(output)
        base = first if first is not None else output
        revised = base.get("revised_output")
        if isinstance(revised, dict) and recover_carried_units(revised, must_carry):
            return base
        return first

    return recovered


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
        current,
        defect,
        tx.facts,
        product_name(tx.entry),
        tx.entry.ecosystem,
        tx.prompts,
    )
    contract = causal.manifest.output.schema_
    probe = _slot_set_probe(current, defect, tx.facts)
    # G4-W17, docs/DECISION_LOG.md 2026-09-25 08:04 UTC (BarCode-Python BC-10 F03): an S6 repair
    # gets review's own stricter title-restatement standard layered onto its stage_checks (never
    # onto unit_checks itself) and a matching recover= last resort, so a reply that still opens a
    # unit with its own title restated verbatim is rejected here - even though unit_checks' item-
    # 106 carve-out would pass it - and given one deterministic chance to be corrected before the
    # job's retry budget is spent.
    section_task = None
    if defect.stage == "S6":
        section_task = next(
            (task for task in current.tasks if task.section_id == defect.section_id), None
        )
    if section_task is not None:
        stage_checks = _reject_title_verbatim_opening(stage_checks, section_task)
    # G4-W17 (docs/DECISION_LOG.md 2026-09-17 10:24 UTC, 2026-09-27 05:14 UTC): a BC-07
    # visible-line-budget defect always names causal stage S5 (the only Failure `_check_structure`
    # ever raises with `stage="PLANNING"` - validation/registry.py), so this is a structured,
    # non-prose signal, not a guess. The exact current overage is measured directly from this
    # round's own rendered README and the same policy the check itself judged against - never
    # parsed from the check's own `detail` text (this module is also routing-held). A packet hint
    # alone was measured live to not be enough (two independent draws, aspose-font-foss/Aspose.
    # Font-FOSS-for-Python, each made an unrelated self-reported no-op edit instead), so a reply
    # that still leaves every named lever untouched is rejected here and given one deterministic
    # last-resort correction (recover=) before the job's retry budget is spent - mirroring the S6
    # title-verbatim-opening pair immediately above.
    visible_line_hint: dict[str, Any] | None = None
    if defect.stage == "S5" and defect.label == "BC-07":
        visible, _total = line_counts(current.readme)
        visible_line_hint = visible_line_budget_hint(
            target.output, tx.facts, visible, DEFAULT_POLICY.visible_lines_budget
        )
        if visible_line_hint is not None:
            stage_checks = _reject_insufficient_visible_line_overage(
                stage_checks, visible_line_hint
            )
            # Code first, where the arithmetic already proves the clear closes the overage: the
            # model's own repair attempts cleared no lever on any recorded draw. The bound's reply
            # must pass the causal stage's own checks, exactly as a model reply would, or it is not
            # used and the targeted repair below runs as before.
            bounded = bound_visible_line_overage(
                target.output,
                overage=visible_line_hint["visible_lines_over_budget"],
                levers=visible_line_hint[
                    "optional_plan_fields_and_their_visible_line_cost_if_cleared"
                ],
            )
            if (
                bounded is not None
                and stage_checks is not None
                and not stage_checks(copy.deepcopy(bounded["revised_output"]))
            ):
                tx.store.put(
                    target.request_sha256, job, target.model_served, bounded["revised_output"]
                )
                repairs.record(defect, "repaired", None, bounded["changes"])
                return
    recover_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    if section_task is not None:
        recover_fn = _with_carried_units(
            functools.partial(recover_title_verbatim_opening, slot_titles=section_task.slot_titles),
            section_task.must_carry,
        )
    elif visible_line_hint is not None:
        recover_fn = functools.partial(
            recover_visible_line_overage,
            levers=visible_line_hint["optional_plan_fields_and_their_visible_line_cost_if_cleared"],
        )
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
                visible_line_hint,
                # The superseded inherited units an S6 section must carry: a repair that cannot
                # see them can repair the wording but never the missing content.
                carried=section_task.must_carry if section_task is not None else (),
            ),
            config=tx.config,
            facts=tx.facts,
            ledger=tx.ledger,
            store=tx.store,
            context=tx.context,
            call_schema=repair_schema(tx.prompts["targeted_repair"], contract),
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
                # G4-W17 arrival item 94: the causal stage's own stored output, so a unit_ids-
                # bound (S4) reply may declare only the units it actually revised - the rest
                # merges in from here instead of demanding a token-costly full re-declaration.
                original=target.output,
            ),
            recover=recover_fn,
        )
    except JobError as exc:
        if probe is not None and probe.conflicts:
            escalate_to_plan(tx, current, defect, repairs, probe)
            return
        repairs.record(replace(defect, reason=str(exc)), "unrepairable")
        return
    tx.store.put(target.request_sha256, job, result.model_served, result.output["revised_output"])
    repairs.record(defect, "repaired", result.request_sha256, result.output.get("changes", []))


def _slot_set_probe(current: Round, defect: Defect, facts: FactsDocument) -> SlotSetProbe | None:
    """The plan's own slot set and per-slot fact binding for an authored section's repair; None
    for every other stage. The fact binding is what lets a reply citing a SUPPORTED fact outside
    its slot's plan be routed to planning (SlotSetProbe.observe_facts) instead of re-asked."""
    if defect.stage != "S6":
        return None
    task = next(
        (task for task in current.tasks if task.section_id == defect.section_id),
        None,
    )
    if task is None:
        return None
    return SlotSetProbe(
        frozenset(task.slots),
        fact_sets=dict(task.slot_facts),
        fact_universe=frozenset(fact.id for fact in facts.facts),
        neutral_facts=frozenset(
            fact.id for fact in facts.facts if fact.kind in {"identity", "package"}
        ),
    )


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
    parts: list[str] = []
    if probe.returned is not None and probe.returned != probe.required:
        returned = ", ".join(sorted(probe.returned)) or "no slot"
        parts.append(
            f"the revision would leave {returned} where the plan assigned "
            f"{', '.join(sorted(probe.required))}"
        )
    if probe.fact_conflicts:
        parts.append(
            "the revision cites "
            f"{', '.join(sorted(probe.fact_conflicts))} outside the slot's planned facts"
        )
    reason = "; ".join(parts) + "; escalated once to a plan-level repair at S5"
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
