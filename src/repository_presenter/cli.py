"""The single command-line entry point, ``repository-presenter``."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from repository_presenter import __version__
from repository_presenter.components.readme.bundle.evaluation import (
    EVALUATION_FILENAME,
    evaluate,
    evaluation_document,
    summarize_evaluation,
    write_evaluation,
)
from repository_presenter.components.readme.bundle.seal import (
    DEPENDENCIES_FILENAME,
    SealInputs,
    bundle_directory,
    invalidate_bundle,
    invalidates,
    seal_candidate,
    upstream_dependencies,
    verify_bundle,
)
from repository_presenter.components.readme.composition.authoring import (
    CONTENT_UNITS_FILENAME,
)
from repository_presenter.components.readme.composition.planning import (
    PLAN_FILENAME,
    summarize_plan,
)
from repository_presenter.components.readme.composition.renderer import (
    PATCH_FILENAME,
    README_FILENAME,
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
    summarize_review,
)
from repository_presenter.components.readme.validation.registry import (
    VALIDATION_FILENAME,
    blocking_failures,
    summarize_validation,
)
from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    BundleError,
    count_current_candidates,
)
from repository_presenter.core.config import API_KEY_VARIABLE, load_gateway_config
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.examples import (
    RECEIPTS_FILENAME,
    ExampleCandidate,
    ExampleReceipt,
    write_receipts,
)
from repository_presenter.core.facts import (
    FACTS_FILENAME,
    write_facts,
)
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
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
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    load_registry,
    require_listed,
)
from repository_presenter.core.secrets import configured_secrets, find_secret_leaks, redact
from repository_presenter.core.snapshot.capture import (
    capture_snapshot,
    list_tree_paths,
    verify_snapshot,
    write_source_artifacts,
)
from repository_presenter.cursor import (
    CURSOR_RELATIVE_PATH,
    CursorError,
    find_project_root,
    load_cursor,
)

PROGRAM = "repository-presenter"
RUNS_DIRNAME = "runs"
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
    preflight = subcommands.add_parser(
        "preflight",
        help="reach the LLM gateway from the process environment and record its model catalog",
    )
    preflight.add_argument("--root", type=Path, default=None, help=root_help)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return run_status(args.root)
    if args.command == "present":
        return run_present(args.repo, args.root)
    if args.command == "preflight":
        return run_preflight(args.root)
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
    print(f"catalog: {catalog_path.relative_to(root).as_posix()} (digest {digest})")
    return EXIT_OK


def run_status(root_argument: Path | None) -> int:
    """Print version, gate, work item, and N/34 progress from sealed bundles on disk."""
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        cursor = load_cursor(root)
        leaks = find_secret_leaks(root, configured_secrets(os.environ))
        on_disk = count_current_candidates(root)
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
    print(f"canary: {cursor.canary}")
    if on_disk != cursor.recorded_candidates:
        _fail(
            f"cursor records {cursor.recorded_candidates} current candidates "
            f"but {on_disk} sealed on disk"
        )
        return EXIT_INCONSISTENT
    return EXIT_OK


def run_present(repository: str, root_argument: Path | None) -> int:
    """Admit ``repository`` from the registry, then run the transaction stages."""
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
        validate_routes(
            prompts, read_catalog_ids(root / RUNS_DIRNAME / PREFLIGHT_DIRNAME / CATALOG_FILENAME)
        )
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
            receipts = plugin.verify_examples(
                clone.path, tree_paths, candidates, root / RUNS_DIRNAME / "verify" / workspace_key
            )
            write_receipts(receipts, transaction / RECEIPTS_FILENAME)
        outcomes = ", ".join(
            f"{outcome.lower()} {count}"
            for outcome, count in sorted(Counter(r.outcome for r in receipts).items())
        )
        print(f"examples: {len(candidates)} candidates; {outcomes or 'none'}")
        document = extract_facts(
            entry, snapshot, clone.path, tree_paths, plugin, manifest, candidates, receipts
        )
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
        verify_bundle(bundle)  # a corrupt or missing artifact fails closed before any call
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
        original_bytes: bytes | None = None
        original = ""
        if snapshot.readme_path is not None:
            original_bytes = (clone.path / snapshot.readme_path).read_bytes()
            original = original_bytes.decode("utf-8", errors="replace")
        # Stages S3 to S10 run as rounds: a blocking defect is repaired once at its causal
        # stage and the downstream stages re-run; a second equivalent failure is reported,
        # never retried.
        ledger = Ledger(transaction / LEDGER_FILENAME)
        final, repairs, rounds = run_transaction(
            TransactionInputs(
                entry=entry,
                facts=document,
                prompts=prompts,
                config=config,
                ledger=ledger,
                store=CallStore(transaction / CALLS_DIRNAME),
                context=JobContext(entry.repository, clone.revision),
                original=original,
                original_bytes=original_bytes,
                source_revision=clone.revision,
                readme_sha256=snapshot.readme_sha256,
                tree_paths=tree_paths,
                directory=transaction,
                secrets=configured_secrets(os.environ),
            )
        )
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
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
            )
        )
    except PresenterError as exc:
        _fail(redact(str(exc), live_values))
        return exc.exit_code
    print(
        f"bundle: {sealed.bundle.relative_to(root).as_posix()} (state {sealed.state}, "
        f"{len(sealed.files)} files, provider calls {ledger.provider_calls_made}; {sealed.note})"
    )
    return EXIT_OK


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
    counts = summarize(final.reconciled.output)
    tally = ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
    print(
        f"dispositions: {where(DISPOSITIONS_FILENAME)} ({sum(counts.values())} units: {tally}; "
        f"{served(final.reconciled)}; digest {final.digests['dispositions']})"
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
    print(
        f"coherence: {len(final.revised)} of {len(final.units['units'])} units revised; "
        f"{served(final.coherent)}"
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


def _fail(message: str) -> None:
    print(f"{PROGRAM}: {message}", file=sys.stderr)
