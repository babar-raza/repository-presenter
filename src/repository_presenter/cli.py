"""The single command-line entry point, ``repository-presenter``."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import cast

from repository_presenter import __version__
from repository_presenter.components.issues import file as issues_file
from repository_presenter.components.issues.draft import (
    eligible_for_handoff,
    record_handoff_if_new,
)
from repository_presenter.components.issues.ledger import (
    UPSTREAM_DEFECTS_DIRNAME,
    load_ledger,
)
from repository_presenter.components.issues.model import (
    Handoff,
    HandoffError,
    load_handoff,
    write_handoff,
)
from repository_presenter.components.issues.redetect import (
    RedetectionResult,
    RedetectorNotRegisteredError,
    apply_redetection,
    redetect,
)
from repository_presenter.components.metadata.apply import (
    AUTHORIZATION_VARIABLE,
    apply_metadata_diff,
)
from repository_presenter.components.metadata.capture import (
    CAPTURE_FILENAME,
    capture_repo_metadata,
    write_capture,
)
from repository_presenter.components.metadata.proposal import (
    build_proposal,
    diff_against_observed,
)
from repository_presenter.components.monitor.drift import (
    drift_document,
    observe_drift,
    write_drift_document,
)
from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE as PROPOSE_AUTHORIZATION_VARIABLE,
)
from repository_presenter.components.propose.effect import (
    presenter_branch_name,
    propose_candidate,
)
from repository_presenter.components.propose.effect import (
    write_authorized as propose_write_authorized,
)
from repository_presenter.components.readme.bundle.evaluation import (
    EVALUATION_FILENAME,
    evaluate,
    evaluation_document,
    summarize_evaluation,
    write_evaluation,
)
from repository_presenter.components.readme.bundle.reproducibility import (
    reproducible_candidates,
)
from repository_presenter.components.readme.bundle.seal import (
    DEPENDENCIES_FILENAME,
    SealInputs,
    bundle_directory,
    invalidate_bundle,
    invalidates,
    seal_candidate,
    sealed_models,
    seed_additional_calls,
    seed_call_store,
    upstream_dependencies,
)
from repository_presenter.components.readme.composition.authoring import (
    CONTENT_UNITS_FILENAME,
    NORMALISATION_VERSION,
)
from repository_presenter.components.readme.composition.components.shell import SHELL_VERSION
from repository_presenter.components.readme.composition.planning import (
    PLAN_FILENAME,
    summarize_plan,
)
from repository_presenter.components.readme.composition.renderer import (
    PATCH_FILENAME,
    README_FILENAME,
    RENDERER_VERSION,
    line_counts,
)
from repository_presenter.components.readme.evidence.facts.extract import extract_facts
from repository_presenter.components.readme.evidence.processability import (
    DISPOSITION_FILENAME,
    assess_processability,
    write_disposition,
)
from repository_presenter.components.readme.extractors.examples.selection import select_examples
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.investigation.dossier import (
    INVESTIGATION_FILENAME,
)
from repository_presenter.components.readme.reconciliation.dispositions import (
    DISPOSITIONS_FILENAME,
    summarize,
)
from repository_presenter.components.readme.repair.rounds import (
    Round,
    TransactionInputs,
    run_transaction,
)
from repository_presenter.components.readme.review.independent.review import (
    REVIEW_FILENAME,
    REVIEWER_LOGIC_VERSION,
    summarize_review,
)
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    VALIDATION_FILENAME,
    VALIDATOR_VERSION,
    blocking_failures,
    coverage_rows,
    summarize_validation,
)
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    BundleError,
    count_current_candidates,
    examples_verification_summary,
    independently_accepted_candidates,
    integrity_valid_candidates,
    iter_sealed_bundles,
    stale_candidates,
    verify_bundle,
)
from repository_presenter.core.config import API_KEY_VARIABLE, load_gateway_config
from repository_presenter.core.errors import JobError, PresenterError
from repository_presenter.core.examples import (
    RECEIPTS_FILENAME,
    ExampleCandidate,
    ExampleReceipt,
    write_receipts,
)
from repository_presenter.core.facts import (
    FACTS_FILENAME,
    FactsDocument,
    read_facts,
    write_facts,
)
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.github.client import (
    FileContents,
    default_patch,
    default_post,
    default_put,
)
from repository_presenter.core.github.client import (
    create_pull_request as default_create_pull_request,
)
from repository_presenter.core.github.client import (
    create_ref as default_create_ref,
)
from repository_presenter.core.github.client import (
    find_open_pull_request as default_find_open_pull_request,
)
from repository_presenter.core.github.client import (
    get_contents as default_get_contents,
)
from repository_presenter.core.github.client import (
    get_ref as default_get_ref,
)
from repository_presenter.core.github.client import (
    put_contents as default_put_contents,
)
from repository_presenter.core.github.client import (
    update_pull_request as default_update_pull_request,
)
from repository_presenter.core.github.read_client import fetch_default_branch_sha
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.llm.fallback import describe, select_models
from repository_presenter.core.llm.jobs import CALLS_DIRNAME, CallStore, JobContext, JobResult
from repository_presenter.core.llm.ledger import LEDGER_FILENAME, Ledger
from repository_presenter.core.llm.prompts import PROMPTS_DIRNAME, load_manifests, validate_routes
from repository_presenter.core.preflight import (
    CATALOG_FILENAME,
    PREFLIGHT_DIRNAME,
    read_catalog_ids,
    run_gateway_preflight,
    write_catalog,
)
from repository_presenter.core.probes import PROBES_FILENAME, write_probes
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    enabled_entries,
    load_registry,
    require_listed,
)
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.retry import RetryableOperationError
from repository_presenter.core.secrets import configured_secrets, find_secret_leaks, redact
from repository_presenter.core.snapshot.capture import (
    capture_snapshot,
    list_tree_paths,
    verify_snapshot,
    write_source_artifacts,
)
from repository_presenter.core.state.git_backend import GitStateBackend
from repository_presenter.core.state.present_transaction import (
    STATE_TOKEN_VARIABLE,
    classify_present_outcome,
    run_present_transaction,
)
from repository_presenter.core.state.trigger import TriggerEventType
from repository_presenter.cursor import (
    CURSOR_RELATIVE_PATH,
    CursorError,
    find_project_root,
    load_cursor,
)

PROGRAM = "repository-presenter"
RUNS_DIRNAME = "runs"
MONITOR_DIRNAME = "monitor"
DRIFT_FILENAME = "drift.json"
EXIT_OK = 0
EXIT_INCONSISTENT = 1
EXIT_USAGE = 2
EXIT_UNSAFE = 3


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for every subcommand."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Keep the README files of authorized repositories accurate and current.",
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    root_help = (
        f"project root holding {CURSOR_RELATIVE_PATH.as_posix()}; "
        "discovered from the working directory when omitted"
    )
    status = subcommands.add_parser(
        "status",
        help="report the current gate and current reviewable no-op-proven candidates",
    )
    status.add_argument("--root", type=Path, default=None, help=root_help)
    status.add_argument(
        "--stale",
        action="store_true",
        help=(
            "also report every current candidate whose dependencies.json is behind the running "
            "code's component/check versions - a pure read, makes no provider call"
        ),
    )
    present = subcommands.add_parser(
        "present",
        help="run the README transaction for one admitted repository",
    )
    present.add_argument(
        "--repo",
        required=True,
        metavar="OWNER/NAME",
        help="repository coordinates exactly as listed in the registry",
    )
    present.add_argument("--root", type=Path, default=None, help=root_help)
    present.add_argument(
        "--facts-only",
        action="store_true",
        help=(
            "stop after the facts stage with the processability and coverage record, making no "
            "provider call; the cohort preflight (RESEARCH_AND_GUIDELINES.md section 28.12)"
        ),
    )
    present.add_argument(
        "--fresh",
        action="store_true",
        help=(
            "do not seed this run's call store from the sealed bundle's own history - every job "
            "makes a genuinely live call even where a prior seal already answered it. For "
            "periodically refreshing a call-volume-sensitive record (e.g. the canary's own "
            "first-attempt-rate floor) against a matured cache, not routine re-seals"
        ),
    )
    present.add_argument(
        "--durable-state",
        action="store_true",
        help=(
            "wire G5-W04's durable-state backend around this run (G5-W05): a recovery sweep, "
            "trigger admission/deduplication, and a committed transition receipt, each against "
            "this control repository's own git-ref state store - never the target repository. "
            "The local pipeline itself is unchanged; this only records that it ran. Used by "
            ".github/workflows/present.yml; a plain local run never needs it"
        ),
    )
    present.add_argument(
        "--trigger-event-type",
        choices=[
            "workflow_dispatch",
            "repository_dispatch",
            "workflow_call",
            "schedule",
            "manual_dispatch",
        ],
        default="workflow_dispatch",
        help="with --durable-state: the trigger vocabulary this invocation counts as (section 3.2)",
    )
    present.add_argument(
        "--workflow-run-id",
        default=None,
        help=(
            "with --durable-state: the triggering workflow run's own identity, used as the "
            "trigger's dedup key; defaults to the GITHUB_RUN_ID environment variable"
        ),
    )
    present.add_argument(
        "--holder-id",
        default=None,
        help=(
            "with --durable-state: the lease holder identity; defaults to a "
            "workflow-run-id-derived value"
        ),
    )
    present.add_argument(
        "--state-remote",
        default="origin",
        help=(
            "with --durable-state: the git remote this control repository's own state ref lives on"
        ),
    )
    preflight = subcommands.add_parser(
        "preflight",
        help="reach the LLM gateway from the process environment and record its model catalog",
    )
    preflight.add_argument("--root", type=Path, default=None, help=root_help)
    redetect_cmd = subcommands.add_parser(
        "redetect-upstream-defects",
        help=(
            "re-evaluate each evidence/upstream-defects/ handoff's own triggering_check against "
            "the target repository's current state (docs/investigations/03-issue-tracking.md "
            "section 6); read-only, no gh issue create/close call"
        ),
    )
    redetect_cmd.add_argument("--root", type=Path, default=None, help=root_help)
    redetect_cmd.add_argument(
        "--repo",
        default=None,
        metavar="OWNER/NAME",
        help="only re-evaluate handoffs for this repository; every handoff when omitted",
    )
    redetect_cmd.add_argument(
        "--apply",
        action="store_true",
        help=(
            "write back a proposed status change (only ever FILED -> RESOLVED_UPSTREAM, never a "
            "GitHub effect); a dry-run report only when omitted"
        ),
    )
    monitor_cmd = subcommands.add_parser(
        "monitor",
        help=(
            "observe each enabled registry repository's upstream default-branch head against its "
            "CURRENT sealed bundle's revision (CURRENT/DRIFTED/NO_BUNDLE/UNREACHABLE); read-only, "
            "no provider call, writes a JSON evidence file under runs/monitor/"
        ),
    )
    monitor_cmd.add_argument("--root", type=Path, default=None, help=root_help)
    monitor_cmd.add_argument(
        "--owner",
        default=None,
        metavar="OWNER",
        help=(
            "only observe enabled entries under this GitHub owner; every enabled entry when omitted"
        ),
    )
    monitor_cmd.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            f"evidence file to write; defaults to {RUNS_DIRNAME}/{MONITOR_DIRNAME}/"
            f"{DRIFT_FILENAME} (drift-<owner>.json with --owner)"
        ),
    )
    file_cmd = subcommands.add_parser(
        "file-upstream-defects",
        help=(
            "file each HANDOFF_PENDING evidence/upstream-defects/ handoff as a real GitHub "
            "issue - dry-run by default; --file attempts the gh issue create call, but only when "
            "the owner has explicitly authorized it"
        ),
    )
    file_cmd.add_argument("--root", type=Path, default=None, help=root_help)
    file_cmd.add_argument(
        "--repo",
        default=None,
        metavar="OWNER/NAME",
        help="only file handoffs for this repository; every HANDOFF_PENDING handoff when omitted",
    )
    file_cmd.add_argument(
        "--file",
        action="store_true",
        help=(
            f"attempt to file each eligible handoff as a GitHub issue; refuses and explains why "
            f"unless {issues_file.AUTHORIZATION_VARIABLE}=1 and a write-scoped "
            "GH_ISSUES_WRITE_TOKEN are both present - lists what would be filed and makes no "
            "write call when omitted"
        ),
    )
    metadata = subcommands.add_parser(
        "metadata",
        help=(
            "capture GitHub's observed description/homepage/topics for one admitted repository "
            "and diff them against a proposal derived from already-verified facts - dry-run by "
            "default (workstream 2 Phase 0/1); --apply attempts the PATCH/PUT, but only when the "
            "owner has explicitly authorized it (OWNER-04/G6-G7 still gate a real live run)"
        ),
    )
    metadata.add_argument(
        "--repo",
        required=True,
        metavar="OWNER/NAME",
        help="repository coordinates exactly as listed in the registry",
    )
    metadata.add_argument("--root", type=Path, default=None, help=root_help)
    metadata.add_argument(
        "--apply",
        action="store_true",
        help=(
            f"attempt to write the computed diff to GitHub; refuses and explains why unless "
            f"{AUTHORIZATION_VARIABLE}=1 and a write-scoped GH_METADATA_WRITE_TOKEN are both "
            "present - prints the diff and makes no write call when omitted"
        ),
    )
    propose = subcommands.add_parser(
        "propose",
        help=(
            "create or update the one stable presenter branch/PR proposing a sealed README "
            "candidate to its target repository (G6-W02) - dry-run by default; --propose attempts "
            "the branch/contents/pull-request calls, but only when the owner has explicitly "
            "authorized it"
        ),
    )
    propose.add_argument(
        "--repo",
        required=True,
        metavar="OWNER/NAME",
        help="the target repository to propose against",
    )
    propose.add_argument("--root", type=Path, default=None, help=root_help)
    propose.add_argument(
        "--readme-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "propose this file's content instead of --repo's registry-admitted sealed CURRENT "
            "candidate - for the G6-W02 disposable-target proof only (a disposable test "
            "repository is never registry-admitted and has no sealed bundle); requires "
            "--source-revision; never used for a real, registry-admitted repository"
        ),
    )
    propose.add_argument(
        "--source-revision",
        default=None,
        metavar="SHA",
        help="required with --readme-file: the exact revision --readme-file's content came from",
    )
    propose.add_argument(
        "--base-branch",
        default=None,
        help="override the target's default branch; read live from GitHub when omitted",
    )
    propose.add_argument(
        "--expires-in-minutes",
        type=int,
        default=15,
        help="how long the assembled authorization stays valid before it must be re-minted",
    )
    propose.add_argument(
        "--propose",
        dest="do_propose",
        action="store_true",
        help=(
            f"attempt to create/update the presenter branch and PR; refuses and explains why "
            f"unless {PROPOSE_AUTHORIZATION_VARIABLE}=1 and a write-scoped GH_PROPOSAL_WRITE_TOKEN "
            "are both present - prints the assembled authorization and makes no GitHub call when "
            "omitted"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return run_status(args.root, stale=args.stale)
    if args.command == "present":
        if args.durable_state:
            return run_present_hosted(
                args.repo,
                args.root,
                facts_only=args.facts_only,
                fresh=args.fresh,
                trigger_event_type=args.trigger_event_type,
                workflow_run_id=args.workflow_run_id,
                holder_id=args.holder_id,
                state_remote=args.state_remote,
            )
        return run_present(args.repo, args.root, facts_only=args.facts_only, fresh=args.fresh)
    if args.command == "preflight":
        return run_preflight(args.root)
    if args.command == "monitor":
        return run_monitor(args.root, owner=args.owner, out=args.out)
    if args.command == "redetect-upstream-defects":
        return run_redetect_upstream_defects(args.root, repository=args.repo, apply=args.apply)
    if args.command == "file-upstream-defects":
        return run_file_upstream_defects(args.root, repository=args.repo, file=args.file)
    if args.command == "metadata":
        return run_metadata(args.repo, args.root, apply=args.apply)
    if args.command == "propose":
        return run_propose(
            args.repo,
            args.root,
            readme_file=args.readme_file,
            source_revision=args.source_revision,
            base_branch=args.base_branch,
            expires_in_minutes=args.expires_in_minutes,
            propose=args.do_propose,
        )
    parser.error(f"unknown command {args.command!r}")


def run_preflight(root_argument: Path | None) -> int:
    """Read the gateway variables, list the live models, and record the catalog under runs/."""
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    live_values = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    catalog_path = root / RUNS_DIRNAME / PREFLIGHT_DIRNAME / CATALOG_FILENAME
    try:
        config = load_gateway_config(os.environ)
        result = run_gateway_preflight(config, root / PROMPTS_DIRNAME)
        digest = write_catalog(result, catalog_path)
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
    ids = result.catalog.ids
    routes = sorted(set(result.prompts.routes().values()))
    print(f"gateway: {config.host} reachable ({API_KEY_VARIABLE} read, never printed)")
    print(f"models: {', '.join(ids)} ({len(ids)})")
    if result.model_override is not None:
        print(f"override: {result.model_override} (present in the catalog)")
    print(
        f"prompts: {len(result.prompts.manifests)} manifests routed to {', '.join(routes)}; "
        "content hashes recorded"
    )
    if result.selection is not None:
        for line in describe(result.selection):
            print(line)
    print(f"catalog: {catalog_path.relative_to(root).as_posix()} (digest {digest})")
    return EXIT_OK


def run_monitor(
    root_argument: Path | None, *, owner: str | None = None, out: Path | None = None
) -> int:
    """Observe every enabled registry entry's upstream head against its CURRENT bundle (G7-W06).

    Read-only: the one credential is the read-only ``GH_TOKEN``, required here so an unattended
    run never falls back to anonymous reads. It makes no provider call and writes only the
    evidence file. Exit 1 when any repository was UNREACHABLE, because the observation is then
    incomplete and the run must say so; DRIFTED and NO_BUNDLE are findings, not failures.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    token = os.environ.get("GH_TOKEN") or None
    if token is None:
        _fail(
            "GH_TOKEN (the read-only analysis token) is required; "
            "monitor reads no repository without it"
        )
        return EXIT_USAGE
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
    except PresenterError as exc:
        _fail(str(exc))
        return exc.exit_code
    entries = [e for e in enabled_entries(registry) if owner is None or e.owner == owner]
    if not entries:
        scope = f" for owner {owner}" if owner else ""
        _fail(f"no enabled registry entries{scope}")
        return EXIT_USAGE
    observations = observe_drift(root, entries, token=token, read_head=fetch_default_branch_sha)
    observed_at = datetime.now(UTC).isoformat(timespec="seconds")
    document = drift_document(observations, observed_at=observed_at, owner=owner)
    name = DRIFT_FILENAME if owner is None else f"drift-{owner}.json"
    path = out or root / RUNS_DIRNAME / MONITOR_DIRNAME / name
    write_drift_document(document, path)
    for observation in sorted(observations, key=lambda o: o.repository):
        head = (observation.head_revision or "-")[:12]
        bundle = (observation.bundle_revision or "-")[:12]
        line = f"{observation.status:<11} {observation.repository}  head {head}  bundle {bundle}"
        if observation.detail:
            line += f"  ({observation.detail})"
        print(line)
    counts = ", ".join(f"{status} {count}" for status, count in document["summary"].items())
    print(f"monitor: {len(observations)} observed - {counts}")
    print(f"evidence: {path}")
    unreachable = [o.repository for o in observations if o.status == "UNREACHABLE"]
    if unreachable:
        _fail(
            f"{len(unreachable)} repositor(ies) unreachable, observation incomplete: "
            + ", ".join(unreachable)
        )
        return EXIT_INCONSISTENT
    return EXIT_OK


def run_redetect_upstream_defects(
    root_argument: Path | None, *, repository: str | None = None, apply: bool = False
) -> int:
    """Re-evaluate every (or one `--repo`) handoff's own `triggering_check` right now.

    Read + local-JSON only (`docs/DECISION_LOG.md`'s 2026-09-17 15:40 UTC ruling): builds the
    dedup ledger from `evidence/upstream-defects/`, then for each entry calls
    `issues.redetect.redetect` and prints whether the check still fires. `--apply`
    writes back only the one schema-valid transition `redetect.py` can ever propose (`FILED` ->
    `RESOLVED_UPSTREAM`, `issue_ref` unchanged) - never a `gh issue create`/`close` call, which
    stays out of scope until its own separate write-authorization work item.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        ledger = load_ledger(root / "evidence" / UPSTREAM_DEFECTS_DIRNAME)
    except HandoffError as exc:
        _fail(str(exc))
        return EXIT_INCONSISTENT
    entries = [
        entry
        for entry in sorted(ledger.values(), key=lambda e: (e.repository, e.defect_fingerprint))
        if repository is None or entry.repository == repository
    ]
    if not entries:
        print(
            f"redetect: no handoff found for {repository!r}"
            if repository
            else "redetect: no handoffs on record"
        )
        return EXIT_OK
    for entry in entries:
        try:
            handoff = load_handoff(entry.path)
        except HandoffError as exc:
            _fail(str(exc))
            return EXIT_INCONSISTENT
        try:
            result = redetect(handoff)
        except RedetectorNotRegisteredError as exc:
            print(f"redetect: {entry.repository} {entry.defect_fingerprint[:19]}...: {exc}")
            continue
        print(
            f"redetect: {entry.repository} {entry.triggering_check_id} "
            f"(status {handoff.status}): {result.note}"
        )
        if result.revision_drifted:
            print(
                f"  revision drifted: handoff recorded {handoff.source_revision}, "
                f"current default-branch head is {result.checked_at_revision}"
            )
        if result.proposed_status is not None:
            print(
                f"  proposed status: {handoff.status} -> {result.proposed_status} "
                f"(reason: {result.proposed_close_reason})"
            )
            if apply:
                updated = apply_redetection(handoff, result)
                write_handoff(updated, entry.path)
                print(
                    f"  applied: {entry.path.relative_to(root).as_posix()} now {updated.status} "
                    f"({updated.close_reason})"
                )
    return EXIT_OK


def _redetect_or_inconclusive(handoff: Handoff) -> RedetectionResult:
    """``redetect.redetect``, but never raises: a handoff whose ``triggering_check.id`` has no
    registered redetector (``RedetectorNotRegisteredError``) is reported as an inconclusive
    recheck rather than crashing the filer - ``file_handoff`` already fails closed on
    ``still_fires is None`` (this module's own docstring; ``AGENTS.md`` "Recheck upstream
    revision immediately before an effect")."""
    try:
        return redetect(handoff)
    except RedetectorNotRegisteredError as exc:
        return RedetectionResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            triggering_check_id=handoff.triggering_check.id,
            checked_at=datetime.now(UTC).isoformat(timespec="seconds"),
            checked_at_revision=None,
            revision_drifted=False,
            still_fires=None,
            note=str(exc),
            fresh_evidence=(),
            proposed_status=None,
        )


def run_file_upstream_defects(
    root_argument: Path | None, *, repository: str | None = None, file: bool = False
) -> int:
    """File each eligible (``HANDOFF_PENDING``) ``evidence/upstream-defects/`` handoff as a real
    GitHub issue.

    Dry-run by default: lists what would be filed and makes no network call at all. ``--file``
    attempts the write through ``components/issues/file.py``, which refuses (and explains exactly
    why, making no write call) unless ``issues_file.AUTHORIZATION_VARIABLE`` is set to a truthy
    value *and* a write-scoped ``GH_ISSUES_WRITE_TOKEN`` is present - neither is set in this
    project's own environment today, so ``--file`` prints the same refusal here that it would
    anywhere else this command runs, never a live issue creation.

    Before ever writing, this also re-runs the handoff's own ``triggering_check``
    (``components/issues/redetect.py``) against the target repository's *current* state and
    refuses to file anything the recheck cannot freshly confirm still fires (``AGENTS.md``
    "Recheck upstream revision immediately before an effect"). A handoff whose status is not
    ``HANDOFF_PENDING`` is skipped without even reaching the recheck - already-``FILED`` handoffs
    are never re-filed (the dedup guard).
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        ledger = load_ledger(root / "evidence" / UPSTREAM_DEFECTS_DIRNAME)
    except HandoffError as exc:
        _fail(str(exc))
        return EXIT_INCONSISTENT
    entries = [
        entry
        for entry in sorted(ledger.values(), key=lambda e: (e.repository, e.defect_fingerprint))
        if repository is None or entry.repository == repository
    ]
    if not entries:
        print(
            f"file: no handoff found for {repository!r}"
            if repository
            else "file: no handoffs on record"
        )
        return EXIT_OK
    write_token = os.environ.get("GH_ISSUES_WRITE_TOKEN") or None
    for entry in entries:
        try:
            handoff = load_handoff(entry.path)
        except HandoffError as exc:
            _fail(str(exc))
            return EXIT_INCONSISTENT
        if handoff.status != "HANDOFF_PENDING":
            print(
                f"file: {handoff.repository} {handoff.defect_fingerprint[:19]}...: skip - "
                f"status is {handoff.status!r}, not HANDOFF_PENDING"
            )
            continue
        if not file:
            print(
                f"file: {handoff.repository} would file {handoff.suggested_issue_title!r} "
                "(dry run; pass --file to attempt)"
            )
            continue
        result = issues_file.file_handoff(
            handoff,
            token=write_token,
            environment=os.environ,
            create=default_post,
            recheck=partial(_redetect_or_inconclusive, handoff),
        )
        print(
            f"file: {handoff.repository} authorized={result.authorized} "
            f"filed={result.filed} - {result.reason}"
        )
        if result.filed and result.issue_ref is not None:
            updated = replace(handoff, status="FILED", issue_ref=result.issue_ref)
            write_handoff(updated, entry.path)
            print(
                f"  applied: {entry.path.relative_to(root).as_posix()} now FILED "
                f"({result.issue_ref.url})"
            )
    return EXIT_OK


def run_metadata(repository: str, root_argument: Path | None, *, apply: bool = False) -> int:
    """Capture GitHub's observed description/homepage/topics for ``repository`` and diff them
    against a proposal derived only from already-verified facts (workstream 2 Phase 0/1,
    docs/investigations/02-repo-metadata-community-files.md section 5).

    Dry-run by default: the one live call this makes without ``--apply`` is
    ``GET /repos/{owner}/{repo}``, at the same repository-scoped ``GH_TOKEN`` read access
    ``present`` already uses to clone. ``--apply`` attempts to write the computed diff through
    ``components/metadata/apply.py``, which refuses (and explains exactly why, making no write
    call) unless ``AUTHORIZATION_VARIABLE`` is set to a truthy value *and* a write-scoped
    ``GH_METADATA_WRITE_TOKEN`` is present - neither is set in this project's own environment
    today, so ``--apply`` prints the same refusal here that it would anywhere else this command
    runs, never a live repository write.

    A repository with no sealed ``CURRENT`` candidate yet - or whose sealed bundle has no
    ``facts.json`` - still gets its observation captured and written; only the proposal (which
    needs verified facts to derive from) is skipped, reported plainly rather than guessed.
    ``--apply`` has nothing to apply in that case either.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    live_values = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
        entry = require_listed(registry, repository)
        print(f"admitted: {entry.repository} (mode {entry.mode})")
        token = os.environ.get("GH_TOKEN") or None
        observed = capture_repo_metadata(entry, token=token)
        metadata_dir = root / RUNS_DIRNAME / "metadata" / f"{entry.owner}__{entry.name}"
        capture_path = metadata_dir / CAPTURE_FILENAME
        digest = write_capture(observed, capture_path)
        print(
            f"observed: description={observed.description!r} homepage={observed.homepage!r} "
            f"topics={list(observed.topics)} (as of {observed.observed_at})"
        )
        print(f"capture: {capture_path.relative_to(root).as_posix()} (digest {digest})")
        current_path = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / CURRENT_FILENAME
        if not current_path.is_file():
            print("proposal: no sealed CURRENT candidate for this repository yet - capture only")
            return EXIT_OK
        revision = current_path.read_text(encoding="utf-8").strip()
        bundle = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / revision
        facts_path = bundle / FACTS_FILENAME
        if not facts_path.is_file():
            print(f"proposal: sealed bundle at {revision} has no {FACTS_FILENAME} - capture only")
            return EXIT_OK
        facts = read_facts(facts_path)
        readme_path = bundle / README_FILENAME
        readme_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None
        proposal = build_proposal(facts, readme_text)
        diff = diff_against_observed(
            entry.repository,
            proposal,
            observed_description=observed.description,
            observed_homepage=observed.homepage,
            observed_topics=observed.topics,
        )
        print(
            f"proposed: description={proposal.description!r} "
            f"(source: {proposal.description_source})"
        )
        print(
            f"proposed: topics={list(proposal.topics)} (sources: {list(proposal.topics_sources)})"
        )
        print(f"proposed: homepage={proposal.homepage!r} (source: {proposal.homepage_source})")
        if not diff.has_changes:
            print("diff: none - GitHub's observed metadata already matches the proposal")
            if apply:
                print("apply: nothing to change")
            return EXIT_OK
        print(
            f"diff: description_changed={diff.description_changed} "
            f"homepage_changed={diff.homepage_changed} topics_changed={diff.topics_changed}"
        )
        if not apply:
            print(
                "apply: dry run (pass --apply to attempt a write; still gated on "
                f"{AUTHORIZATION_VARIABLE} and a write-scoped GH_METADATA_WRITE_TOKEN, and on "
                "OWNER-04's write-capable credential - project/state.yaml)"
            )
            return EXIT_OK
        write_token = os.environ.get("GH_METADATA_WRITE_TOKEN") or None
        result = apply_metadata_diff(
            diff,
            entry.owner,
            entry.name,
            token=write_token,
            environment=os.environ,
            patch=default_patch,
            put=default_put,
            refetch=lambda: capture_repo_metadata(entry, token=write_token),
        )
        for outcome in (result.description, result.homepage, result.topics):
            if not outcome.changed:
                continue
            verb = "written" if outcome.applied else "not written"
            print(f"apply: {outcome.field} {verb} - {outcome.reason}")
        if not result.wrote_anything:
            print("apply: nothing written (see the per-field reasons above)")
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
    return EXIT_OK


def _cli_utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_propose(
    repository: str,
    root_argument: Path | None,
    *,
    readme_file: Path | None = None,
    source_revision: str | None = None,
    base_branch: str | None = None,
    expires_in_minutes: int = 15,
    propose: bool = False,
) -> int:
    """Create or update the one stable presenter branch/PR proposing ``repository``'s README
    candidate (G6-W02; ``components/propose/effect.py``).

    Two content sources, never mixed:

    - By default, ``repository`` must be registry-admitted with a sealed ``CURRENT`` candidate
      (``candidates/<owner>__<name>/CURRENT``) - the real, production shape this command exists
      for. Nothing here re-validates the bundle's own acceptance; ``status``/``present`` already
      own that.
    - ``--readme-file`` (with required ``--source-revision``) bypasses the registry and sealed
      bundle entirely, for the G6-W02 disposable-target proof only: a disposable test repository
      created purely to exercise this write path is never registry-admitted (the registry names
      only the authorized ``aspose-*-foss`` portfolio - ``AGENTS.md`` "Security and Effects"'s
      allow-list governs *analysis* of that portfolio, which this command never performs; it only
      opens or updates a pull request on whatever ``--repo`` names, using content supplied
      directly). Never pass this for a real, registry-admitted repository.

    Dry-run by default: assembles and prints the authorization payload, making no GitHub call at
    all. ``--propose`` attempts the write through ``components/propose/effect.py``, which refuses
    (and explains exactly why, making no write call beyond whatever read it needed to decide the
    refusal) unless ``PROPOSE_AUTHORIZATION_VARIABLE`` is set to a truthy value *and* a write-scoped
    ``GH_PROPOSAL_WRITE_TOKEN`` is present - neither is set in this project's own environment today,
    so ``--propose`` prints the same refusal here that it would anywhere else this command runs,
    never a live repository write.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    live_values = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    try:
        if readme_file is not None:
            if not source_revision:
                _fail("propose: --readme-file requires --source-revision")
                return EXIT_USAGE
            if not readme_file.is_file():
                _fail(f"propose: {readme_file} does not exist")
                return EXIT_USAGE
            readme_text = readme_file.read_text(encoding="utf-8")
            revision = source_revision
            print(
                f"propose: {repository} using --readme-file (disposable-target proof only, "
                "never a registered repository's own sealed candidate)"
            )
        else:
            registry = load_registry(root / REGISTRY_RELATIVE_PATH)
            entry = require_listed(registry, repository)
            repository = entry.repository
            print(f"admitted: {entry.repository} (mode {entry.mode})")
            current_path = (
                root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / CURRENT_FILENAME
            )
            if not current_path.is_file():
                print(f"propose: no sealed CURRENT candidate for {repository} - nothing to propose")
                return EXIT_OK
            revision = current_path.read_text(encoding="utf-8").strip()
            bundle = root / CANDIDATES_DIRNAME / f"{entry.owner}__{entry.name}" / revision
            readme_path = bundle / README_FILENAME
            if not readme_path.is_file():
                print(
                    f"propose: sealed bundle at {revision} has no {README_FILENAME} - nothing to "
                    "propose"
                )
                return EXIT_OK
            readme_text = readme_path.read_text(encoding="utf-8")

        candidate_hash = sha256_text(readme_text)
        branch = presenter_branch_name()
        issued_at = _cli_utc_now()
        expires_at = (datetime.now(UTC) + timedelta(minutes=expires_in_minutes)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        authorization = authorize_proposal(
            repository=repository,
            candidate_hash=candidate_hash,
            source_revision=revision,
            branch=branch,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        print(
            f"propose: {repository} candidate_hash={candidate_hash} source_revision={revision} "
            f"branch={branch} policy_version={authorization.policy_version} "
            f"expires_at={expires_at}"
        )
        if not propose:
            print(
                "propose: dry run (pass --propose to attempt a write; still gated on "
                f"{PROPOSE_AUTHORIZATION_VARIABLE} and a write-scoped GH_PROPOSAL_WRITE_TOKEN)"
            )
            return EXIT_OK

        # Past this point every GitHub call targets `repository` with the one freshly minted,
        # repository-scoped write token for this effect job - never GH_TOKEN, which this project's
        # own read-only analysis uses and which has no write scope at all (AGENTS.md "Analysis uses
        # repository-scoped read-only credentials"). That write token is also the one this command
        # reads the target's live state with (default branch, current revision, current presenter-
        # branch content): a disposable proof target is never registry-admitted, so GH_TOKEN would
        # not even have read access to it, and a GitHub App's Contents:Write permission already
        # implies read - exactly the one-token-per-effect-job shape docs/STATE_MACHINE.md section
        # 12 describes, never a second credential smuggled in for convenience.
        write_token = os.environ.get("GH_PROPOSAL_WRITE_TOKEN") or None

        def _recheck_source() -> str:
            fresh = fetch_default_branch_sha(repository, token=write_token)
            return fresh.sha or f"<unreadable: {fresh.error}>"

        def _reconcile_write() -> FileContents | None:
            # Only ever invoked from inside propose_candidate's own lost-response handling, which
            # is itself only reached past that function's own token gate - write_token is always a
            # real string by the time this runs, never None.
            assert write_token is not None
            owner, name = repository.split("/", 1)
            return default_get_contents(owner, name, README_FILENAME, ref=branch, token=write_token)

        # Mirror propose_candidate's own gate here too, before the one read this command makes
        # ahead of the effect itself (resolving the default branch when --base-branch is omitted):
        # an unauthorized or under-credentialed --propose makes no GitHub call at all, not even a
        # read, exactly like every other early refusal in this module's own docstring.
        base = base_branch
        if base is None and propose_write_authorized(os.environ) and write_token:
            default_branch_read = fetch_default_branch_sha(repository, token=write_token)
            if default_branch_read.error is not None or default_branch_read.branch is None:
                _fail(
                    f"propose: could not read {repository}'s default branch: "
                    f"{default_branch_read.error}"
                )
                return EXIT_INCONSISTENT
            base = default_branch_read.branch
        base = base or ""  # unused by propose_candidate before its own authorization gate

        pr_title = "Update README via repository-presenter"
        pr_body = (
            "Automated README proposal from repository-presenter.\n\n"
            f"- candidate_hash: {candidate_hash}\n"
            f"- source_revision: {revision}\n"
            f"- policy_version: {authorization.policy_version}\n"
        )
        result = propose_candidate(
            repository=repository,
            readme_text=readme_text,
            source_revision=revision,
            authorization=authorization,
            base_branch=base,
            pr_title=pr_title,
            pr_body=pr_body,
            token=write_token,
            environment=os.environ,
            branch=branch,
            recheck_source=_recheck_source,
            reconcile_write=_reconcile_write,
            get_ref=default_get_ref,
            create_ref=default_create_ref,
            get_contents=default_get_contents,
            put_contents=default_put_contents,
            find_open_pull_request=default_find_open_pull_request,
            create_pull_request=default_create_pull_request,
            update_pull_request=default_update_pull_request,
        )
        print(
            f"propose: {repository} authorized={result.authorized} effected={result.effected} - "
            f"{result.reason}"
        )
        if result.pr_url is not None:
            print(
                f"  pr: {result.pr_url} (commit_written={result.commit_written} "
                f"pr_created={result.pr_created} pr_updated={result.pr_updated})"
            )
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
    return EXIT_OK


def run_status(root_argument: Path | None, *, stale: bool = False) -> int:
    """Print version, gate, work item, and N/34 progress from sealed bundles on disk.

    ``--stale`` additionally reports every current candidate whose sealed ``dependencies.json``
    is behind the running code's component/check versions (``core.candidates.stale_candidates``,
    2026-09-09, ``docs/CI_AND_STALENESS_ASSESSMENT.md``) - a pure read, makes no provider call,
    and does not affect the exit status: a stale candidate is not itself an inconsistency, only
    something due for a re-seal.

    The ``progress:`` line (PHASE0/PA-03) reports four distinct counts the single "N/34" headline
    used to conflate: how many repositories have ever sealed anything at all, how many of those
    sealed bundles pass integrity verification, how many still render byte-identical to their own
    stored README under the code running right now, and how many are independently accepted under
    the current contract with known-stale ones excluded. ``candidates:`` above and the consistency
    check below are both left pointed at ``count_current_candidates`` exactly as before - that is
    the number ``cursor.recorded_candidates`` has always meant, and this new line reports
    alongside it rather than replacing it.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        cursor = load_cursor(root)
        leaks = find_secret_leaks(root, configured_secrets(os.environ))
        on_disk = count_current_candidates(root)
        current_components = {
            "shell": SHELL_VERSION,
            "renderer": RENDERER_VERSION,
            "normalisation": NORMALISATION_VERSION,
            "reviewer_logic": REVIEWER_LOGIC_VERSION,
        }
        current_validators = {check.id: check.version for check in BLOCKING_CHECKS}
        found = stale_candidates(root, current_components, current_validators, VALIDATOR_VERSION)
    except (CursorError, BundleError, OSError) as exc:
        _fail(str(exc))
        return EXIT_INCONSISTENT
    if leaks:
        for leak in leaks:
            relative = leak.path.relative_to(root).as_posix()
            _fail(f"secret canary: value of {leak.variable} found in {relative}")
        return EXIT_UNSAFE
    print(f"{PROGRAM} {__version__}")
    print(f"gate: {cursor.current_gate_id} ({cursor.current_gate_status})")
    print(f"work item: {cursor.active_work_item_id} ({cursor.active_work_item_status})")
    print(f"candidates: {on_disk}/{cursor.denominator} current reviewable no-op-proven")
    historical = len({bundle.repository_dir for bundle in iter_sealed_bundles(root)})
    integrity_valid = integrity_valid_candidates(root)
    reproducible = reproducible_candidates(root)
    accepted = independently_accepted_candidates(root, found)
    print(
        f"progress: {historical} ever sealed, {integrity_valid} integrity-valid, "
        f"{reproducible} current-code reproducible, {accepted} independently accepted "
        "(stale-excluded)"
    )
    executed, example_total = examples_verification_summary(root)
    print(f"examples: {executed}/{example_total} verified across counted candidates")
    print(f"canary: {cursor.canary}")
    if stale:
        if found:
            print(f"stale: {len(found)} current candidate(s) behind the running code -")
            for candidate in found:
                print(f"  {candidate.repository_dir} @ {candidate.revision}:")
                for reason in candidate.reasons:
                    print(f"    {reason}")
        else:
            print("stale: none")
    if on_disk != cursor.recorded_candidates:
        _fail(
            f"cursor records {cursor.recorded_candidates} current candidates "
            f"but {on_disk} sealed on disk"
        )
        return EXIT_INCONSISTENT
    return EXIT_OK


PREFLIGHT_FILENAME = "preflight.json"


def _report_facts_only(
    root: Path,
    entry: RegistryEntry,
    revision: str,
    document: FactsDocument,
    transaction: Path,
) -> int:
    """Write and print what the facts alone say about this repository's readiness.

    Per fact kind, how many resolved; per required contract row, whether the kinds it rests on
    produced anything. A row with no supported fact of any kind it needs is the coverage gap the
    cohort must see before it spends a composition on the repository.
    """
    polarity = Counter(fact.polarity for fact in document.facts)
    kinds = {
        kind: {
            "supported": sum(
                1 for f in document.facts if f.kind == kind and f.polarity == "SUPPORTED"
            ),
            "extracted": sum(1 for f in document.facts if f.kind == kind),
        }
        for kind in sorted({fact.kind for fact in document.facts})
    }
    rows = coverage_rows(document, set())
    starved = [
        row["section_id"]
        for row in rows
        if row["required"] and row["kinds"] and not any(kind["supported"] for kind in row["kinds"])
    ]
    record = {
        "schema_version": 1,
        "repository": entry.repository,
        "source_revision": revision,
        "processable": True,
        "facts": {"total": len(document.facts), "by_polarity": dict(polarity), "by_kind": kinds},
        "required_rows_without_evidence": starved,
        "coverage": rows,
    }
    path = transaction / PREFLIGHT_FILENAME
    path.write_bytes((json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(
        f"preflight: {path.relative_to(root).as_posix()} ({len(document.facts)} facts, "
        f"{polarity.get('SUPPORTED', 0)} supported, {polarity.get('UNRESOLVED', 0)} unresolved, "
        f"{polarity.get('CONTRADICTED', 0)} contradicted; required rows without evidence: "
        f"{', '.join(starved) or 'none'})"
    )
    return EXIT_OK


def run_present(
    repository: str, root_argument: Path | None, *, facts_only: bool = False, fresh: bool = False
) -> int:
    """Admit ``repository`` from the registry, then run the transaction stages.

    ``facts_only`` stops after S2 with the processability and coverage record and makes no
    provider call: the cohort preflight reads every repository's failure class before any
    composition spends a token (RESEARCH_AND_GUIDELINES.md section 28.12).

    ``fresh`` skips seeding this run's call store from the sealed bundle's own history, so every
    job makes a genuinely live call - for periodically refreshing a call-volume-sensitive record
    (the canary's own first-attempt-rate floor) against a matured cache, never a routine re-seal
    (CS-03 follow-up, docs/CI_AND_STALENESS_ASSESSMENT.md, 2026-09-09: a maturing cache reduced a
    real re-seal to 14 live calls, below the floor's own ``>= 20`` "enough to mean anything" bar,
    even though the ratio metrics it protects - ``first_attempt_rate``, ``reask_share`` - held).
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    live_values = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
        entry = require_listed(registry, repository)
        print(
            f"admitted: {entry.repository} (mode {entry.mode}, ecosystem {entry.ecosystem}, "
            f"family {entry.family}, platform {entry.platform})"
        )
        # The gateway, the governed manifests, and the recorded catalog are checked before any
        # clone: a transaction never runs without them and never queries the catalog itself.
        config = load_gateway_config(os.environ)
        prompts = load_manifests(root / PROMPTS_DIRNAME)
        catalog_ids = read_catalog_ids(root / RUNS_DIRNAME / PREFLIGHT_DIRNAME / CATALOG_FILENAME)
        validate_routes(prompts, catalog_ids)
        clone = pinned_read_only_clone(
            entry.clone_url,
            root / RUNS_DIRNAME / "clones" / f"{entry.owner}__{entry.name}",
            token=os.environ.get("GH_TOKEN") or None,
        )
        print(
            f"snapshot: {entry.repository} at {clone.revision} in "
            f"{clone.path.relative_to(root).as_posix()} (push disabled, verified)"
        )
        snapshot = capture_snapshot(entry.repository, clone)
        transaction = (
            root / RUNS_DIRNAME / "transactions" / f"{entry.owner}__{entry.name}" / clone.revision
        )
        artifacts = write_source_artifacts(snapshot, clone.path, transaction / "source")
        verify_snapshot(snapshot, clone.path)
        print(
            f"source: {artifacts.directory.relative_to(root).as_posix()} "
            f"({len(artifacts.files)} files, {snapshot.tree_entries} tree entries, "
            f"readme {snapshot.readme_path or 'absent'}, digest {artifacts.digest})"
        )
        plugin = plugin_for(entry.ecosystem)
        manifest = plugin.detect_manifest(clone.path)
        tree_paths = list_tree_paths(clone.path)
        manifest_path = None if manifest is None else manifest.relative_to(clone.path).as_posix()
        disposition = assess_processability(snapshot, tree_paths, plugin, manifest_path)
        if disposition is not None:
            write_disposition(disposition, transaction / DISPOSITION_FILENAME)
            print(
                f"insufficient_evidence: {disposition.reason_code} for {entry.repository} "
                f"at {clone.revision}; resume when {disposition.resume_predicate}"
            )
            return EXIT_INCONSISTENT
        candidates: list[ExampleCandidate] = []
        receipts: list[ExampleReceipt] = []
        if snapshot.readme_path is not None:
            readme_bytes = (clone.path / snapshot.readme_path).read_bytes()
            candidates = select_examples(snapshot.readme_path, readme_bytes, entry.ecosystem)
            # A short workspace: a virtual environment nested under the transaction
            # directory overruns the Windows path limit before pip finishes.
            workspace_key = hashlib.sha256(
                f"{entry.repository}@{clone.revision}".encode()
            ).hexdigest()[:12]
            # Example verification builds and executes code against clone.path (TB-03, external
            # review D3, 2026-09-08): re-verify immediately before handing it a working tree that
            # could have drifted since capture, rather than trusting the one check done earlier.
            verify_snapshot(snapshot, clone.path)
            receipts = plugin.verify_examples(
                clone.path, tree_paths, candidates, root / RUNS_DIRNAME / "verify" / workspace_key
            )
            write_receipts(receipts, transaction / RECEIPTS_FILENAME)
        outcomes = ", ".join(
            f"{outcome.lower()} {count}"
            for outcome, count in sorted(Counter(r.outcome for r in receipts).items())
        )
        print(f"examples: {len(candidates)} candidates; {outcomes or 'none'}")
        # Example verification (above) is the stage most likely to have just run build/install
        # tooling against clone.path; re-verify once more before fact extraction reads it too.
        verify_snapshot(snapshot, clone.path)
        document, probes = extract_facts(
            entry, snapshot, clone.path, tree_paths, plugin, manifest, candidates, receipts
        )
        write_probes(probes, transaction / PROBES_FILENAME)
        facts_digest = write_facts(document, transaction / FACTS_FILENAME)
        kinds = sorted({fact.kind for fact in document.facts})
        counts = ", ".join(f"{kind} {len(document.by_kind(kind))}" for kind in kinds)
        print(
            f"facts: {(transaction / FACTS_FILENAME).relative_to(root).as_posix()} "
            f"({len(document.facts)} records: {counts}; digest {facts_digest})"
        )
        # Dependency evaluation: the sealed bundle's consumed inputs against this run's, class
        # by class, naming the earliest stage that reopens - derived from the candidate's own
        # record alone, never from a global hash.
        bundle = bundle_directory(root / CANDIDATES_DIRNAME, entry, clone.revision)
        sealed_manifest = verify_bundle(bundle)  # a corrupt/missing artifact fails closed here
        sealed_dependencies = bundle / DEPENDENCIES_FILENAME
        evaluation = None
        if sealed_dependencies.is_file():
            evaluation = evaluate(
                json.loads(sealed_dependencies.read_text(encoding="utf-8")),
                upstream_dependencies(clone.revision, snapshot.tree_sha256, document, prompts),
            )
        evaluated = evaluation_document(clone.revision if evaluation else None, evaluation)
        evaluation_digest = write_evaluation(evaluated, transaction / EVALUATION_FILENAME)
        print(
            f"evaluation: {(transaction / EVALUATION_FILENAME).relative_to(root).as_posix()} "
            f"({summarize_evaluation(evaluated)}; digest {evaluation_digest})"
        )
        if facts_only:
            return _report_facts_only(root, entry, clone.revision, document, transaction)
        # Fallback chains (core/llm/fallback.py), decided once at run start before any content
        # call: each route's own model must pass consecutive tiny schema-constrained probes, or the
        # run fails closed. No substitute model is ever chosen. A sealed bundle's recorded model
        # is kept while it is the route's own model and still answers.
        selection = select_models(
            config,
            prompts.routes().values(),
            listed=catalog_ids,
            recorded=None if sealed_manifest is None else sealed_models(bundle, sealed_manifest),
        )
        for line in describe(selection):
            print(line)
        original_bytes: bytes | None = None
        original = ""
        if snapshot.readme_path is not None:
            original_bytes = (clone.path / snapshot.readme_path).read_bytes()
            original = original_bytes.decode("utf-8", errors="replace")
        # Stages S3 to S10 run as rounds: a blocking defect is repaired once at its causal
        # stage and the downstream stages re-run; a second equivalent failure is reported,
        # never retried.
        ledger = Ledger(transaction / LEDGER_FILENAME)
        if fresh:
            # A prior local run of this exact repo+revision (runs/ is gitignored, ephemeral
            # working state, never the durable record) would otherwise still answer from its own
            # leftover call cache even with seeding from the sealed bundle skipped below - fresh
            # means fresh, not merely un-seeded.
            shutil.rmtree(transaction / CALLS_DIRNAME, ignore_errors=True)
        store = CallStore(transaction / CALLS_DIRNAME)
        if sealed_manifest is not None and not fresh:
            # RC4: runs/ is gitignored, so a hosted runner's first run of an already-sealed
            # revision starts with nothing to reuse - seed what the sealed bundle's own
            # artifacts can answer for before making any call. Skipped under --fresh: every job
            # makes a genuinely live call instead (CS-03 follow-up, see this function's own
            # docstring).
            seeded = set(seed_call_store(bundle, store))
            # G5-W02's own remaining gap: seed_call_store only ever reaches the three 1:1 jobs
            # its own _SEEDABLE_JOBS names; coherence, independent_review, and a batch
            # section_authoring task each need raw_calls.json's own, differently-keyed seeding
            # instead (bundle/seal.py::seed_additional_calls's own docstring explains why no
            # lineage check is needed there). Both run before anything in this transaction makes
            # a call, so a job either mechanism can answer for never reaches the gateway.
            seeded |= set(seed_additional_calls(bundle, store))
            if seeded:
                print(f"seeded from sealed bundle: {', '.join(sorted(seeded))}")
        elif fresh:
            print("fresh: call store not seeded from the sealed bundle; every job calls live")
        final, repairs, rounds = run_transaction(
            TransactionInputs(
                entry=entry,
                facts=document,
                prompts=prompts,
                config=config,
                ledger=ledger,
                store=store,
                context=JobContext(entry.repository, clone.revision, models=selection),
                original=original,
                original_bytes=original_bytes,
                source_revision=clone.revision,
                readme_sha256=snapshot.readme_sha256,
                tree_paths=tree_paths,
                directory=transaction,
                secrets=configured_secrets(os.environ),
                sealed_bundle=bundle if sealed_manifest is not None else None,
            )
        )
    except (PresenterError, RetryableOperationError) as exc:
        failure = _typed(exc)
        _fail(redact(str(failure), live_values))
        return failure.exit_code
    _print_round(root, transaction, final)
    print(f"repair: {repairs.summary()}; rounds {rounds}")
    failed = blocking_failures(final.validation)
    if failed:
        first = failed[0]
        attempted = any(a["outcome"] == "repaired" for a in repairs.attempts.values())
        standing = (
            "after one repair attempt the equivalent failure stands"
            if attempted
            else "no repair could act on it"
        )
        if invalidates(first) and invalidate_bundle(bundle, first) is not None:
            # A factual, safety, or protected-content failure invalidates the accepted candidate.
            print(
                f"bundle: {bundle.relative_to(root).as_posix()} (state INVALIDATED; "
                f"{first['id']} failed at {first['causal_stage'] or 'the bundle'})"
            )
            # G4-W17, docs/investigations/12-supervisor-and-production-reassessment.md section 6:
            # a genuine upstream-content defect (BC-02 at EXTRACTING, backed by a real
            # non-SUPPORTED install_command fact in this run's own facts.json) gets the
            # evidence-backed handoff artifact components/issues already knows how to build and
            # later re-check, automatically - not only via the separate, manually-invoked
            # redetect-upstream-defects subcommand. eligible_for_handoff/draft_handoff fail closed
            # on every other check shape (never guessed); dedup is by the ledger's own
            # {repository, defect_fingerprint} key, so a redrawn identical defect never
            # duplicates. Never a GitHub write.
            if eligible_for_handoff(first):
                handoff_path = record_handoff_if_new(
                    root / "evidence" / UPSTREAM_DEFECTS_DIRNAME,
                    repository=entry.repository,
                    source_revision=clone.revision,
                    check=first,
                    facts=document,
                )
                if handoff_path is not None:
                    print(
                        "upstream-defect handoff: "
                        f"{handoff_path.relative_to(root).as_posix()} (HANDOFF_PENDING)"
                    )
        _fail(
            f"validation: {first['id']} failed at {first['causal_stage'] or 'the bundle'}: "
            f"{first['details'][0]}; {standing}"
        )
        return EXIT_INCONSISTENT
    # Stage S12: seal the accepted transaction; a fresh process that reproduces it byte for
    # byte with zero provider calls is the no-op proof that judges check 11.
    try:
        sealed = seal_candidate(
            SealInputs(
                entry=entry,
                source_revision=clone.revision,
                tree_sha256=snapshot.tree_sha256,
                facts=document,
                prompts=prompts,
                validation=final.validation,
                transaction=transaction,
                candidates=root / CANDIDATES_DIRNAME,
                provider_calls=ledger.provider_calls_made,
                consumed_calls=ledger.consumed_calls,
                secrets=configured_secrets(os.environ),
                earliest_affected_stage=evaluated["earliest_affected_stage"],
                models_used=selection.models_used(),
            )
        )
    except (PresenterError, RetryableOperationError) as exc:
        failure = _typed(exc)
        _fail(redact(str(failure), live_values))
        return failure.exit_code
    print(
        f"bundle: {sealed.bundle.relative_to(root).as_posix()} (state {sealed.state}, "
        f"{len(sealed.files)} files, provider calls {ledger.provider_calls_made}; {sealed.note})"
    )
    return EXIT_OK


def run_present_hosted(
    repository: str,
    root_argument: Path | None,
    *,
    facts_only: bool,
    fresh: bool,
    trigger_event_type: str,
    workflow_run_id: str | None,
    holder_id: str | None,
    state_remote: str,
) -> int:
    """``present --durable-state`` (G5-W05): wire G5-W04's durable-state backend around one
    unmodified :func:`run_present` invocation - see
    ``core/state/present_transaction.py``'s module docstring for the full design and what this
    deliberately does not attempt.

    The durable-state ref lives on this control repository's own remote (``--state-remote``,
    default ``origin``), authenticated by ``REPOSITORY_PRESENTER_STATE_TOKEN`` when set (a hosted
    run's own job token, scoped only to this repository) - never the read-only ``GH_TOKEN`` the
    wrapped :func:`run_present` call uses to clone the *target* repository. The two credentials
    are intentionally distinct: one is this project's own operational state, the other is a
    read-only analysis grant on a repository this project does not own.
    """
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
        entry = require_listed(registry, repository)
    except PresenterError as exc:
        _fail(str(exc))
        return exc.exit_code
    run_id = workflow_run_id or os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        _fail(
            "present --durable-state requires --workflow-run-id (or GITHUB_RUN_ID in the "
            "environment) as the trigger's own dedup identity"
        )
        return EXIT_USAGE
    holder = holder_id or f"present.yml:{run_id}"
    backend = GitStateBackend(
        remote=state_remote, token=os.environ.get(STATE_TOKEN_VARIABLE) or None
    )
    live_values = [secret.value.decode("utf-8") for secret in configured_secrets(os.environ)]
    try:
        return run_present_transaction(
            backend=backend,
            repository=entry.repository,
            provider_repository_id=entry.provider_identity.repository_id,
            holder_id=holder,
            trigger_event_type=cast(TriggerEventType, trigger_event_type),
            workflow_run_id=run_id,
            run=lambda: run_present(repository, root_argument, facts_only=facts_only, fresh=fresh),
            classify=lambda exit_code: classify_present_outcome(root, entry, exit_code),
        )
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
    finally:
        backend.close()


def _print_round(root: Path, transaction: Path, final: Round) -> None:
    """The stage lines of the round the bundle holds, in stage order."""

    def where(name: str) -> str:
        return (transaction / name).relative_to(root).as_posix()

    def served(result: JobResult) -> str:
        model = result.model_served or "stored output reused"
        return f"provider calls {result.provider_calls}, model {model}"

    output = final.investigation.output
    print(
        f"investigation: {where(INVESTIGATION_FILENAME)} "
        f"(capabilities {len(output.get('capabilities', []))}, "
        f"workflows {len(output.get('workflows', []))}, "
        f"limitations {len(output.get('limitations', []))}; "
        f"{served(final.investigation)}; digest {final.digests['investigation']})"
    )
    counts = summarize(final.dispositions)
    tally = ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
    # PHASE0/G: one run_job() call per reconciliation batch now, not one - reported the same
    # multi-call way authoring's own line below already does (a per-call "model served" no
    # longer names one thing once there can be more than one batch).
    reconciliation_calls = sum(result.provider_calls for result in final.reconciled.values())
    print(
        f"dispositions: {where(DISPOSITIONS_FILENAME)} ({sum(counts.values())} units: {tally}; "
        f"provider calls {reconciliation_calls}; digest {final.digests['dispositions']})"
    )
    print(
        f"plan: {where(PLAN_FILENAME)} ({summarize_plan(final.planned.output)}; "
        f"{served(final.planned)}; digest {final.digests['plan']})"
    )
    authoring_calls = sum(result.provider_calls for result in final.authored.values())
    sections = list(dict.fromkeys(task.section_id for task in final.tasks))  # batches share one
    print(
        f"units: {where(CONTENT_UNITS_FILENAME)} ({len(final.units['units'])} units across "
        f"{len(sections)} sections: {', '.join(sections)}; "
        f"provider calls {authoring_calls}; digest {final.digests['units']})"
    )
    # PDFPY-03: one run_job() call per coherence batch now, not one - reported the same multi-call
    # way authoring's/reconciliation's own lines above already do (a per-call "model served" no
    # longer names one thing once there can be more than one batch).
    coherence_calls = sum(result.provider_calls for result in final.coherent.values())
    print(
        f"coherence: {len(final.revised)} of {len(final.units['units'])} units revised; "
        f"provider calls {coherence_calls}"
    )
    visible, total = line_counts(final.readme)
    print(
        f"readme: {where(README_FILENAME)} ({visible} visible lines of {total}; "
        f"digest {final.digests['readme']})"
    )
    print(f"patch: {where(PATCH_FILENAME)} (digest {final.digests['patch']})")
    print(
        f"validation: {where(VALIDATION_FILENAME)} ({summarize_validation(final.validation)}; "
        f"digest {final.digests['validation']})"
    )
    if final.reviewed is not None:
        print(
            f"review: {where(REVIEW_FILENAME)} ({summarize_review(final.review)}; "
            f"{served(final.reviewed)}; digest {final.digests['review']})"
        )


def _resolve_root(root_argument: Path | None) -> Path | None:
    """Return the project root, printing the usage failure when it cannot be found."""
    if root_argument is None:
        root = find_project_root(Path.cwd())
        if root is None:
            _fail(f"no {CURSOR_RELATIVE_PATH.as_posix()} found at or above {Path.cwd()}")
        return root
    root = root_argument.resolve()
    if not (root / CURSOR_RELATIVE_PATH).is_file():
        _fail(f"no {CURSOR_RELATIVE_PATH.as_posix()} under {root}")
        return None
    return root


def _typed(exc: PresenterError | RetryableOperationError) -> PresenterError:
    """Every failure this CLI reports is typed; an exhausted bounded retry becomes a JobError.

    ``run_with_retry`` re-raises the last ``RetryableOperationError`` once a policy's attempts are
    spent (``core/retry.py``), and the job boundary deliberately leaves it retryable rather than
    converting it, so nothing between there and here typed it: ``present`` printed a bare Python
    traceback instead of its usual ``repository-presenter: ...`` line whenever a job's three
    attempts all timed out against the gateway (measured twice on
    aspose-pdf-foss/Aspose.PDF-FOSS-for-TypeScript, 2026-09-06; G4-W17 arrival item 35). A
    provider that never answered is exactly what ``JobError`` describes, so it carries that exit
    code and reads like every other typed failure.
    """
    if isinstance(exc, PresenterError):
        return exc
    return JobError(f"the gateway did not answer after the bounded retries: {exc}")


def _fail(message: str) -> None:
    print(f"{PROGRAM}: {message}", file=sys.stderr)
