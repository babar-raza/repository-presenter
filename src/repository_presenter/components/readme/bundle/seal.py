"""Stage S12: seal the accepted transaction into a content-addressed bundle and prove the no-op.

The bundle at candidates/<owner>__<name>/<revision>/ (docs/README_CONTRACT.md section 7) is a
copy of the accepted transaction's artifacts plus dependencies.json, which names exactly the
inputs the candidate consumed (docs/STATE_MACHINE.md section 9), sealed by manifest.json with a
digest for every file. The first seal records state ACCEPTED with no proof. A later run in a
fresh process that reproduces every artifact byte for byte with zero provider calls is the no-op
proof: it judges check 11, records the proof in the manifest, and moves the bundle to
READY_FOR_PROPOSAL, the only state progress counts. A run that reproduces a proven bundle writes
nothing. A run whose artifacts differ re-seals an unproven bundle at ACCEPTED and withdraws the
proof; on a proven bundle it records a valid update instead and touches no artifact
(docs/STATE_MACHINE.md section 5), and a later fresh process that reproduces that exact update
with zero provider calls proves it, so the bundle adopts it as its proven content and keeps the
previous proof on the manifest for the record. Where a recorded update lands is decided by the
typed invalidation scope of the input that changed (invalidation.py, docs/STATE_MACHINE.md
section 9): a change to a factual input the candidate consumed - the source, the extraction
environment, the fact records - is the ``facts`` scope and invalidates it (INVALIDATED, re-entering
at EXTRACTING); a change to any other consumed input - a prompt or route, a template component,
the validators, the reviewer, the policy - leaves the proven candidate valid and records
VALID_UPDATE_AVAILABLE. Either way the update waits in the transaction until a fresh zero-call
process adopts it, and the manifest names the scope that triggered it. Before 2026-10-04 this was
inverted (TB-06 sent the factual case to VALID_UPDATE_AVAILABLE and left the presentation case
unmarked at READY_FOR_PROPOSAL), against the text of docs/STATE_MACHINE.md section 9.

Three files carry a clock by design and are exempt from the byte comparison: the ledger, the
manifest itself, and the probe record. validation.json is compared with check 11 blanked, since
the proof is what judges it. CURRENT names the revision a reviewer opens.

A bundle is published by staging every file to a sibling temp directory, scanning *that* for
configured secrets, and only promoting it into place - and only then updating CURRENT - once the
scan passes: a leak must leave no trace on disk, never merely raise after the files and CURRENT
were already published (TB-06, external review D6, 2026-09-08).

The manifest also carries an optional call_variance: any job whose successful attempts across the
transaction's whole history never settled on one response, named with every distinct response
hash, so provider non-determinism is visible from manifest.json alone (RC-05,
RESEARCH_AND_GUIDELINES.md 27.2 RC5/SW6).

models_used maps each manifest route to the model the run answered it with (core/llm/fallback.py).
It is provenance and a consumed input: a rerun whose effective model for any route differs from
the sealed one is a recorded change, scoped by the prompts that route answers (a model-route change
is a prompt-class change, docs/DECISION_LOG.md 2026-09-06 07:45), never a silent switch.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Any, cast

from repository_presenter.components.readme.bundle.invalidation import (
    STATE_INVALIDATED,
    STATE_UPDATE_AVAILABLE,
    ScopeError,
)
from repository_presenter.components.readme.bundle.invalidation import route as route_scopes
from repository_presenter.components.readme.composition.authoring import (
    NORMALISATION_VERSION,
    RAW_CALLS_FILENAME,
)
from repository_presenter.components.readme.composition.components.shell import SHELL_VERSION
from repository_presenter.components.readme.composition.policy import (
    POLICY_VERSION,
    policy_packet,
)
from repository_presenter.components.readme.composition.renderer import RENDERER_VERSION
from repository_presenter.components.readme.evidence.facts.inherited import (
    INHERITED_UNITS_VERSION,
)
from repository_presenter.components.readme.extractors.surface.extractor import EXTRACTOR_VERSION
from repository_presenter.components.readme.review.independent.review import REVIEWER_LOGIC_VERSION
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    VALIDATOR_VERSION,
    record_replay_verdict,
)
from repository_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    UPSTREAM_BLOBS_FIELD,
    verify_bundle,
)
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.jobs import CallStore
from repository_presenter.core.llm.ledger import (
    LEDGER_FILENAME,
    canonical_hash,
    parse_records,
)
from repository_presenter.core.llm.prompts import PromptRegistry
from repository_presenter.core.noop_proof import (
    Invocation,
    LedgerReconciliationError,
    Measurement,
    identity_of_run_ref,
    ledger_totals,
    measure_invocation,
    reconcile_ledger,
    same_process,
)
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret, scan_for_secrets
from repository_presenter.core.snapshot.capture import SNAPSHOT_FILENAME, TREE_FILENAME
from repository_presenter.core.toolchains import toolchain_fingerprint

DEPENDENCIES_FILENAME = "dependencies.json"
CURRENT_FILENAME = "CURRENT"
CONTRACT_VERSION = "readme-contract-v1"
# G3-W02: the acceptance profile version a sealed bundle CONSUMED, recorded in dependencies.json and
# read by evaluation.py as a reviewer-scope input. It is "1", frozen 2026-10-01 with the contract
# (docs/DECISION_LOG.md PA-05), and is deliberately NOT ``PROFILE_VERSION`` any more: the owner
# ratified the profile on 2026-10-10 (G7-W20, OWNER-13) and the profile is now "2", but ratification
# changes nothing a sealed review consumed. The independent review (prompts, routes, review logic)
# is unchanged; the score is recomputed from the sealed README, validation.json and review.json by
# the portfolio funnel (bundle/portfolio.py), and READY_FOR_PROPOSAL does not read it. Bumping this
# would reopen REVIEWING for every sealed candidate (status --stale routing, a provider re-review)
# for no change in content, and would drop the current candidates from the headline count. Move it
# when a change alters what the independent review itself reads or decides.
ACCEPTANCE_PROFILE_VERSION = "1"
REQUIRED_ARTIFACTS = (
    "README.md",
    "README.patch",
    "facts.json",
    "dispositions.json",
    "plan.json",
    "validation.json",
    "review.json",
    "calls.jsonl",
)
# examples.json is the receipt every example fact cites as its evidence path, and repairs.json
# is the record of what a repair attempted; a bundle that omits them carries facts whose
# evidence dangles outside it (README_CONTRACT.md section 7, RESEARCH_AND_GUIDELINES.md 27.2
# RC7). Optional because a transaction that composed without them seals without them.
OPTIONAL_ARTIFACTS = (
    "investigation.json",
    "content_units.json",
    RAW_CALLS_FILENAME,
    "examples.json",
    "probes.json",
    "repairs.json",
)
# Three files carry a clock by design and cannot be compared byte for byte across runs: the
# ledger, the manifest, and the probe record, whose whole point is how long a live read took
# (core/probes.py; RESEARCH_AND_GUIDELINES.md 27.2 RC7). Nothing a candidate depends on is
# only in them.
REPLAY_EXEMPT = frozenset({"calls.jsonl", "probes.json", BUNDLE_MANIFEST_NAME})
STATE_ACCEPTED = "ACCEPTED"
STATE_READY = "READY_FOR_PROPOSAL"
# STATE_UPDATE_AVAILABLE and STATE_INVALIDATED (imported from invalidation.py) are the two states
# a recorded update can land in; the scope table, not this module, decides which.


class SealError(PresenterError):
    """The transaction cannot be sealed as a bundle."""

    exit_code = 1


class BundleLeakError(SealError):
    """A configured secret's value appears in the bundle."""

    exit_code = 3


@dataclass(frozen=True)
class SealInputs:
    entry: RegistryEntry
    source_revision: str
    tree_sha256: str
    facts: FactsDocument
    prompts: PromptRegistry
    validation: dict[str, Any]
    transaction: Path
    candidates: Path
    provider_calls: int
    secrets: Sequence[ConfiguredSecret]
    # The invocation sealing this transaction: its process identity and the id its ledger records
    # carry. The seal measures the provider-call count from the ledger on disk by this id and
    # derives the no-op proof's freshness from this identity against the one the bundle was last
    # sealed by - neither is taken on the caller's word (core/noop_proof.py).
    invocation: Invocation
    consumed_calls: frozenset[str] = frozenset()
    earliest_affected_stage: str | None = None
    # route -> the model this run answered it with. ``None`` means no fallback decision was made
    # and every route answered as its own primary, exactly as before chains existed.
    models_used: Mapping[str, str] | None = None
    # The input classes evaluation.evaluate found changed (``Change.dependency``), e.g.
    # "prompts.section_authoring" or "facts": what the typed invalidation scope is computed from.
    changed_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class SealResult:
    bundle: Path
    state: str
    files: dict[str, dict[str, Any]]
    proof: dict[str, Any] | None
    changed: bool
    note: str


def bundle_directory(candidates: Path, entry: RegistryEntry, revision: str) -> Path:
    return candidates / f"{entry.owner}__{entry.name}" / revision


def record_upstream_blobs(transaction: Path, facts: FactsDocument) -> dict[str, str]:
    """The git blob id, at the sealed revision, of each upstream file the candidate depends on.

    The dependencies are the files the facts cite as evidence, plus the README, license and
    notices paths the snapshot names. Blob ids come from the transaction's own tree listing
    (``source/tree.txt``, written from the same revision), so nothing here reads the network or
    the clone. A dependency absent from the listing (a directory, or no file at that path) is not
    recorded. Returns ``{}`` when the snapshot or listing is missing, which the monitor then reports
    as UNKNOWN rather than CURRENT.
    """
    source = transaction / "source"
    tree = source / TREE_FILENAME
    snapshot_file = source / SNAPSHOT_FILENAME
    if not tree.is_file() or not snapshot_file.is_file():
        return {}
    blobs: dict[str, str] = {}
    for line in tree.read_text(encoding="utf-8").splitlines():
        meta, separator, path = line.partition("\t")
        fields = meta.split()
        if separator and len(fields) == 3 and fields[1] == "blob":
            blobs[path] = fields[2]
    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    dependencies = {evidence.path for fact in facts.facts for evidence in fact.evidence}
    dependencies.update(
        str(snapshot[key])
        for key in ("readme_path", "license_path", "notices_path")
        if snapshot.get(key)
    )
    return {path: blobs[path] for path in sorted(dependencies) if path in blobs}


def _presenter_site_manifest_hash() -> str:
    """A canonical hash of *repository-presenter's own* resolved installed package set - the
    process running this code, never the separate environment a target candidate's own examples
    were verified in (TB-07 part 2, external review D7, 2026-09-08: named ``site_manifest`` and
    read as if it fingerprinted the target's own resolved dependencies; it never has - a Java,
    C++, Rust, or Go candidate's toolchain has no Python "installed package set" to fingerprint
    at all, and even for a Python candidate this measures the tool's own venv, not the target's).

    Kept, correctly scoped and honestly named: a change in *this* process's own dependencies can
    change extraction or rendering behavior in ways worth reopening for, exactly like
    ``extractor_version``. It is deliberately not claimed to be more than that. The target's own
    verifier toolchains are a separate class, ``toolchain_fingerprint()`` (core/toolchains.py),
    recorded under ``environment.toolchains`` by ``environment_dependencies`` (2026-10-04).
    """
    packages = sorted(f"{dist.name}=={dist.version}" for dist in distributions() if dist.name)
    return canonical_hash(packages)


def environment_dependencies() -> dict[str, Any]:
    """What answered this run's extraction, never a claim the repository itself makes (27.2
    RC7): the Python version the venv was cloned from, the OS, this codebase's own extractor and
    inherited-unit-inventory versions, and repository-presenter's own resolved package set (never
    the target's - see ``_presenter_site_manifest_hash``), and every machine toolchain a verifier
    resolves, by its resolved version or ``absent`` (``toolchains``, 2026-10-04: a toolchain that
    appears, disappears or changes version changed what the examples could have proven). A change
    in any reopens EXTRACTING, the same stage a source or fact change would - a fact SUPPORTED
    under one environment is not trusted unchanged under a different one."""
    return {
        "python_version": platform.python_version(),
        "os": platform.system(),
        "extractor_version": EXTRACTOR_VERSION,
        "inherited_units_version": INHERITED_UNITS_VERSION,
        "presenter_site_manifest": _presenter_site_manifest_hash(),
        "toolchains": toolchain_fingerprint(),
    }


def code_dependencies(prompts: PromptRegistry) -> dict[str, Any]:
    """The consumed-input classes the running code itself owns - prompts, contract, template
    components, checks, acceptance profile, policy and the extractor builds - with nothing read
    from a repository. ``upstream_dependencies`` adds the source and the facts; the portfolio dry
    run (portfolio.py) compares exactly these, so it never reports a change it cannot observe."""
    return {
        "environment": {
            "extractor_version": EXTRACTOR_VERSION,
            "inherited_units_version": INHERITED_UNITS_VERSION,
        },
        "prompts": {
            name: {
                "sha256": prompts[name].sha256,
                "version": prompts[name].manifest.version,
                "model_route": prompts[name].manifest.model_route,
            }
            for name in sorted(prompts.hashes())
        },
        "contract_version": CONTRACT_VERSION,
        "components": {
            "shell": SHELL_VERSION,
            "renderer": RENDERER_VERSION,
            "normalisation": NORMALISATION_VERSION,
            "reviewer_logic": REVIEWER_LOGIC_VERSION,
        },
        "validators": {check.id: check.version for check in BLOCKING_CHECKS},
        "validator_version": VALIDATOR_VERSION,
        "acceptance_profile_version": ACCEPTANCE_PROFILE_VERSION,
        "policy": {"version": POLICY_VERSION, "sha256": canonical_hash(policy_packet())},
    }


def upstream_dependencies(
    source_revision: str, tree_sha256: str, facts: FactsDocument, prompts: PromptRegistry
) -> dict[str, Any]:
    """The inputs a run consumes before any agentic stage, each by a hash that reopens a stage
    when it changes (docs/STATE_MACHINE.md section 9): known before the first call, so an
    evaluation can name the earliest affected stage without running anything."""
    code = code_dependencies(prompts)
    return {
        "schema_version": 1,
        "source": {"revision": source_revision, "tree_sha256": tree_sha256},
        "environment": environment_dependencies(),
        "facts": {
            fact.id: canonical_hash(asdict(fact))
            for fact in sorted(facts.facts, key=lambda fact: fact.id)
        },
        "prompts": code["prompts"],
        "contract_version": code["contract_version"],
        "components": code["components"],
        "validators": code["validators"],
        "validator_version": code["validator_version"],
        "acceptance_profile_version": code["acceptance_profile_version"],
        "policy": code["policy"],
    }


def dependencies_document(inputs: SealInputs) -> dict[str, Any]:
    """Exactly the inputs the candidate consumed: the upstream inputs plus the protected-content
    fingerprint the accepted dispositions produced; nothing else can invalidate the candidate."""
    return {
        **upstream_dependencies(
            inputs.source_revision, inputs.tree_sha256, inputs.facts, inputs.prompts
        ),
        "protected_content_fingerprint": inputs.validation.get("protected_content_fingerprint"),
    }


def _canonical_json(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _composition(staged: Mapping[str, bytes]) -> dict[str, Any]:
    """What this composition cost in quality terms: advisories and blocking failures.

    Recorded per composition so variance is measured rather than sampled by accident
    (docs/RESEARCH_AND_GUIDELINES.md section 27.10). Both come from artifacts already staged,
    so nothing new is computed and nothing can disagree with the bundle.
    """
    review = json.loads(staged["review.json"]) if "review.json" in staged else {}
    validation = json.loads(staged["validation.json"]) if "validation.json" in staged else {}
    checks = validation.get("checks") or []
    return {
        "review_verdict": review.get("verdict"),
        "review_verdict_as_returned": review.get("verdict_as_returned"),
        "advisories": len(review.get("advisory") or []),
        "coverage_advisories": len(validation.get("advisory") or []),
        "blocking_failures": sorted(
            check["id"] for check in checks if check.get("verdict") == "FAIL"
        ),
    }


def _call_variance(ledger: bytes) -> list[dict[str, Any]]:
    """Distinct-response variance among a job's successful attempts across the transaction's
    whole history - every repair round and reopening, not only what the final accepted
    composition consumed - naming a job whose provider never settled on one answer.

    Surfaced on the manifest so a later reader sees non-determinism in one ``manifest.json``
    lookup instead of the 30+ minutes of manual ``calls.jsonl`` reading the Aspose.Email Python
    ``source_reconciliation`` diagnosis needed this session (RC-05, RESEARCH_AND_GUIDELINES.md
    27.2 RC5/SW6; empirically confirmed against that candidate's own real transaction ledger,
    which reproduces exactly the four distinct responses that diagnosis found by hand). This does
    not fix non-determinism; it makes it observable. Grouped by job alone, not job and
    ``logical_call_id`` together: a job re-run across separate repair rounds gets a *different*
    ``logical_call_id`` each time (a changed packet), so restricting to one ``logical_call_id``
    would miss exactly the cross-round drift this exists to surface. Empty when every job's
    successful attempts agree, or there are none - never a trivial single-entry list, so a caller
    can treat "no ``call_variance`` on the manifest" as "no variance seen."
    """
    responses: dict[str, set[str]] = {}
    for line in ledger.decode("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("outcome") != "success":
            continue
        response = record.get("response_sha256")
        if not response:
            continue
        responses.setdefault(str(record.get("job")), set()).add(response)
    return [
        {"job": job, "distinct_responses": len(hashes), "response_sha256s": sorted(hashes)}
        for job, hashes in sorted(responses.items())
        if len(hashes) > 1
    ]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _blank_check_eleven(data: bytes) -> bytes:
    """validation.json with check 11 in its unjudged form, for the replay comparison."""
    document = json.loads(data.decode("utf-8"))
    checks = [
        {**check, "verdict": "PENDING", "causal_stage": None, "details": ["judged at S12"]}
        if check.get("id") == "BC-11"
        else check
        for check in document.get("checks", [])
    ]
    return canonical_hash({**document, "checks": checks, "summary": None}).encode("utf-8")


def _staged_artifacts(inputs: SealInputs) -> dict[str, bytes]:
    staged: dict[str, bytes] = {}
    for name in REQUIRED_ARTIFACTS:
        path = inputs.transaction / name
        if not path.is_file():
            raise SealError(f"seal: the transaction has no {name}; nothing to seal")
        staged[name] = path.read_bytes()
    for name in OPTIONAL_ARTIFACTS:
        path = inputs.transaction / name
        if path.is_file():
            staged[name] = path.read_bytes()
    staged[LEDGER_FILENAME] = composition_ledger(staged[LEDGER_FILENAME], inputs.consumed_calls)
    staged[DEPENDENCIES_FILENAME] = _canonical_json(dependencies_document(inputs))
    return staged


def composition_ledger(raw: bytes, consumed: frozenset[str]) -> bytes:
    """The transaction ledger as sealed: consumed calls as written, every other attempt retained
    as an audit-only line carrying the reason it is not part of this composition.

    A transaction outlives its compositions. A prompt version change, a repair round, a review
    whose successor supersedes it - each leaves records of calls nothing in the current candidate
    came from. Dropping them made the sealed ledger lie by omission: a rejected or abandoned
    attempt vanished, and per-README totals could not reconcile with the calls actually made
    (the 2026-09-05 canary's transaction carried 65 provider calls where its composition consumed
    28, docs/RESEARCH_AND_GUIDELINES.md section 27.6 control 1). Those lines stay, marked with
    ``retained_reason``, so a reader measuring first-attempt acceptance over what the composition
    consumed filters on that field, an audit reads the rest with its reason, and replay seeding
    ignores them (``seed_call_store``) - they never answer for a candidate. Every attempt of a
    consumed call is kept as before, rejections included. A run that consumed nothing has nothing
    to mark and seals the ledger whole.
    """
    if not consumed:
        return raw
    lines: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("logical_call_id") not in consumed:
            record["retained_reason"] = (
                f"unconsumed by the sealed composition (outcome {record.get('outcome')})"
            )
            line = json.dumps(record, sort_keys=True, separators=(",", ":"))
        lines.append(line)
    return "".join(f"{line}\n" for line in lines).encode("utf-8")


def _identical(name: str, staged: bytes, existing: bytes) -> bool:
    if name == "validation.json":
        return _blank_check_eleven(staged) == _blank_check_eleven(existing)
    return staged == existing


def _read_manifest(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SealError(f"seal: unreadable bundle manifest {path}: {exc}") from exc
    return loaded if isinstance(loaded, dict) else None


def _current_models(inputs: SealInputs) -> dict[str, str]:
    """route -> the model this run answered it with; without a fallback decision, each route's
    own name, which is what every run before chains answered with."""
    if inputs.models_used is not None:
        return dict(sorted(inputs.models_used.items()))
    return {route: route for route in sorted(set(inputs.prompts.routes().values()))}


def sealed_models(bundle: Path, manifest: Mapping[str, Any]) -> dict[str, str]:
    """route -> the model the proven bundle was sealed with. A bundle sealed before models_used
    existed answered every route with its own name, so its routes are read from dependencies.json,
    the record of what it consumed."""
    recorded = manifest.get("models_used")
    if isinstance(recorded, dict):
        return {str(route): str(model) for route, model in recorded.items()}
    dependencies = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
    routes = {str(prompt["model_route"]) for prompt in dependencies.get("prompts", {}).values()}
    return {route: route for route in sorted(routes)}


def _changed_routes(sealed: Mapping[str, str], current: Mapping[str, str]) -> list[str]:
    """The routes whose effective model differs from the sealed one, in route order."""
    return [
        route
        for route in sorted(set(sealed) | set(current))
        if sealed.get(route) != current.get(route)
    ]


def _model_changes(sealed: Mapping[str, str], current: Mapping[str, str]) -> list[str]:
    """One line per route whose effective model differs from the sealed one, in route order."""
    return [
        f"models[{route}]: {sealed.get(route, '(none)')} -> {current.get(route, '(none)')}"
        for route in _changed_routes(sealed, current)
    ]


def _model_dependencies(inputs: SealInputs, routes: Sequence[str]) -> list[str]:
    """The prompt input classes a changed model route lands on: a route is consumed through the
    prompts it answers, so its scope is theirs. A route no prompt uses any more is attributed to
    the generic prompt family, whose row in the scope table is the earliest agentic stage."""
    answered = inputs.prompts.routes()
    dependencies: list[str] = []
    for changed in routes:
        jobs = sorted(job for job, used in answered.items() if used == changed)
        dependencies.extend(f"prompts.{job}" for job in jobs or [changed])
    return dependencies


def _write_bundle(
    bundle: Path,
    staged: Mapping[str, bytes],
    *,
    state: str,
    proof: dict[str, Any] | None,
    provider_calls: int,
    inputs: SealInputs,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    files = {
        name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(staged.items())
    }
    # The full, unfiltered transaction ledger, not staged[LEDGER_FILENAME]: composition_ledger()
    # already trimmed that to only the calls the *final accepted* composition consumed, which
    # hides exactly the cross-repair-round drift this is meant to surface (confirmed empirically
    # - the sealed, filtered ledger showed no source_reconciliation variance at all for the real
    # Aspose.Email Python candidate, while its raw transaction ledger reproduced the diagnosis).
    variance = _call_variance((inputs.transaction / LEDGER_FILENAME).read_bytes())
    manifest = {
        "schema_version": 1,
        "repository": inputs.entry.repository,
        "revision": inputs.source_revision,
        "state": state,
        "sealed_at": _now(),
        "files": files,
        "provider_calls": provider_calls,
        "no_op_proof": proof,
        # Which invocation wrote this bundle, and the sums over the ledger sealed beside it: the
        # next fresh process proves its freshness against the first, and the manifest reconciles
        # against the second whenever the bundle is verified (core/noop_proof.py).
        "sealed_by": inputs.invocation.run_ref(),
        "ledger_totals": ledger_totals(
            parse_records(staged[LEDGER_FILENAME].decode("utf-8"), LEDGER_FILENAME)
        ),
        "composition": _composition(staged),
        "models_used": _current_models(inputs),
        # The blob ids of the upstream files this candidate depends on, for the drift monitor's
        # content check (core/candidates.py UPSTREAM_BLOBS_FIELD).
        UPSTREAM_BLOBS_FIELD: record_upstream_blobs(inputs.transaction, inputs.facts),
        **({"call_variance": variance} if variance else {}),
        **dict(extra or {}),
    }
    bundle.parent.mkdir(parents=True, exist_ok=True)
    # Staged to a sibling temp directory and scanned for secrets before anything under `bundle`
    # itself - or CURRENT - is touched: a leak must leave no trace on disk, never merely raise
    # after the files and CURRENT pointer were already published (TB-06, external review D6,
    # 2026-09-08). No existing staging/atomic-publication facility exists anywhere in this
    # codebase to reuse (checked first); a temp-directory-then-rename is the narrowest primitive
    # that closes the gap without a new general-purpose framework.
    staging = Path(tempfile.mkdtemp(dir=bundle.parent, prefix=f".{bundle.name}.staging-"))
    try:
        for name, data in staged.items():
            (staging / name).write_bytes(data)
        (staging / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(manifest))
        # A bundle whose own totals do not reconcile with its ledger is never published.
        reconcile_ledger(manifest, staging / LEDGER_FILENAME)
        leaks = scan_for_secrets(staging, inputs.secrets)
        if leaks:
            names = ", ".join(sorted({f"{leak.variable} in {leak.path.name}" for leak in leaks}))
            raise BundleLeakError(f"seal: a configured secret appears in the bundle: {names}")
        if bundle.is_dir():
            shutil.rmtree(bundle)
        staging.rename(bundle)
    finally:
        if staging.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
    # CURRENT is updated last, strictly after the rename above: it must never be able to point at
    # a bundle directory that is only partially published (TB-06, external review D6, 2026-09-08).
    current = bundle.parent / CURRENT_FILENAME
    pointer = f"{inputs.source_revision}\n".encode()
    if not current.is_file() or current.read_bytes() != pointer:
        current.write_bytes(pointer)
    return files


# ``verify_bundle`` now lives in core/candidates.py, the lower-level module both this file and
# count_current_candidates() depend on - candidates.py could not call back into this module
# without a circular import, so the check moved down to where both callers can reach it
# (TB-06, external review D6, 2026-09-08). Imported above and used directly by name here.

# G5-W02 (27.2 RC4). Each of these three jobs' sealed artifact is that one job's own accepted
# output written verbatim (investigation.py::write_investigation, dispositions.py::
# write_dispositions, planning.py::write_plan each do a bare json.dumps(output) - confirmed by
# reading all three before relying on it). section_authoring (content_units.json merges many
# calls via merge_units) and independent_review (review.json is post-processed, not one call's
# raw reply) are not 1:1 this way and need their own mechanism; they are not seeded here.
_SEEDABLE_JOBS: dict[str, str] = {
    "repository_investigation": "investigation.json",
    "source_reconciliation": "dispositions.json",
    "presentation_planning": "plan.json",
}


def seed_call_store(bundle: Path, store: CallStore) -> list[str]:
    """Pre-populate ``store`` from a sealed bundle's own committed artifacts, so a fresh clone's
    first run of an already-sealed revision reuses those calls instead of making them again -
    the gap RC4 names: the call cache lives under the gitignored runs/ directory, so a hosted
    runner that never had a prior local run starts with nothing to reuse from.

    Keyed by ``logical_call_id``, not the ledger's own ``request_sha256`` field: the latter is
    ``canonical_hash(payload)`` for one physical attempt (distinct per retry, if a re-ask changed
    the payload), while ``core/llm/jobs.py::run_job``'s actual ``CallStore`` cache key is
    ``canonical_hash({"prompt_sha256": ..., "payload": ...})`` - carried on every attempt's own
    record as ``logical_call_id`` precisely so a caller never has to recompute it. Confirmed by a
    live integration test (``test_present_from_an_empty_runs_directory_reuses_a_sealed_bundle``)
    after this field mix-up shipped silently once: the "seeded from sealed bundle" line printed
    correctly, but every seeded job still made a real call, because nothing had ever looked up
    the key it was actually stored under.

    Seeds a job only when its sealed ``calls.jsonl`` carries exactly one successful attempt: a
    repository whose composition reopened this stage through a repair round left two or more
    successful attempts under the same job name, each against a different packet, and only the
    last one's output matches what the sealed artifact holds - pairing an earlier attempt's
    logical call ID with the final content would claim a call returned something it never did.
    That job is left unseeded, so a replay still makes one real call for it rather than lying
    about which attempt is genuine.

    Returns the job names actually seeded, so a caller can report or test the count without
    reading the store back.
    """
    ledger_path = bundle / LEDGER_FILENAME
    if not ledger_path.is_file():
        return []
    successes: dict[str, list[dict[str, Any]]] = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("retained_reason"):
            continue  # an audit-only line (composition_ledger): never answers for a candidate
        if record.get("outcome") == "success":
            successes.setdefault(str(record.get("job")), []).append(record)
    seeded: list[str] = []
    for job, filename in _SEEDABLE_JOBS.items():
        attempts = successes.get(job, [])
        artifact = bundle / filename
        if len(attempts) != 1 or not artifact.is_file():
            continue
        record = attempts[0]
        logical_call_id = record.get("logical_call_id")
        if not isinstance(logical_call_id, str) or not logical_call_id:
            continue
        output = json.loads(artifact.read_text(encoding="utf-8"))
        store.put(logical_call_id, job, record.get("model_served"), output)
        seeded.append(job)
    return seeded


def seed_additional_calls(bundle: Path, store: CallStore) -> list[str]:
    """Pre-populate ``store`` from a sealed bundle's own ``raw_calls.json`` (when it has one) -
    the counterpart to :func:`seed_call_store` above for the calls that function's own
    ``_SEEDABLE_JOBS`` (and ``composition/authoring.py::reconstructed_task_output``, which
    ``repair/rounds.py`` already applies per non-batch ``section_authoring`` task) cannot reach:
    each ``source_reconciliation`` batch, a ``coherence`` batch, an ``independent_review`` read,
    and a batch ``section_authoring`` task (G5-W02's own remaining gap, named explicitly in
    ``tests/test_cli.py::test_present_from_an_
    empty_runs_directory_reuses_a_sealed_bundle``'s docstring before this function existed).

    Unlike ``seed_call_store``, no per-job "exactly one success" constraint applies here:
    ``raw_calls.json`` is already keyed by each call's own ``request_sha256``
    (``composition/authoring.py::write_raw_calls``'s own docstring explains why that key alone is
    enough - a later run's freshly computed request hash only ever matches the entry it actually
    came from), so every entry seeds unconditionally, the same way a repeated job name is already
    disambiguated for free by the hash itself.

    Returns the distinct job names actually seeded (a job already present in ``store`` - from an
    earlier call in this same function, or from :func:`seed_call_store` - is left alone, not
    re-seeded), for the same CLI reporting :func:`seed_call_store` already gives.
    """
    path = bundle / RAW_CALLS_FILENAME
    if not path.is_file():
        return []
    calls = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(calls, dict):
        return []
    seeded: set[str] = set()
    for request_sha256, record in calls.items():
        if not isinstance(record, dict) or not isinstance(request_sha256, str):
            continue
        job = record.get("job")
        output = record.get("output")
        if not isinstance(job, str) or not isinstance(output, dict):
            continue
        if store.get(request_sha256) is not None:
            continue
        # raw_calls.json never carries model_served (write_raw_calls's own docstring explains
        # why: run_job hardcodes it to None on its own cache-reuse path, so sealing it here would
        # make a seeded reuse's own written raw_calls.json differ from the original live call's).
        store.put(request_sha256, job, None, output)
        seeded.add(job)
    return sorted(seeded)


def _update_digests(staged: Mapping[str, bytes]) -> dict[str, str]:
    """The replay identity of the staged artifacts: every non-exempt file's digest, with check
    11 blanked in validation.json so a judged and an unjudged copy compare equal."""
    return {
        name: _sha256(_blank_check_eleven(data) if name == "validation.json" else data)
        for name, data in sorted(staged.items())
        if name not in REPLAY_EXEMPT
    }


def _record_update(
    bundle: Path,
    manifest: dict[str, Any],
    differing: list[str],
    staged: Mapping[str, bytes],
    inputs: SealInputs,
    model_changes: Sequence[str] = (),
    changed_routes: Sequence[str] = (),
) -> SealResult:
    # The state follows the typed scope of what changed (invalidation.py), computed from the
    # inputs the candidate consumed - the changed dependencies and any model route that moved -
    # and from the differing artifacts only when no input explains the difference. A factual
    # input (the facts scope) invalidates; every other scope leaves the proven candidate valid
    # with an update available (docs/STATE_MACHINE.md section 9).
    try:
        routing = route_scopes(
            [*inputs.changed_dependencies, *_model_dependencies(inputs, changed_routes)],
            differing,
        )
    except ScopeError as exc:
        raise SealError(f"seal: {exc}") from exc
    if routing.state is None or routing.triggering_scope is None:
        raise SealError("seal: a recorded update with no changed input and no differing artifact")
    differing = [*differing, *model_changes]
    state = routing.state
    scope = routing.triggering_scope
    stage = inputs.earliest_affected_stage or routing.stage
    update = {
        "available": True,
        "classification": "factual" if routing.invalidates else "presentation",
        "scopes": list(routing.scopes),
        "triggering_scope": scope,
        "scope_basis": routing.basis,
        "earliest_affected_stage": stage,
        "changed": differing,
        "transaction": inputs.transaction.name,
        "files": _update_digests(staged),
        "models_used": _current_models(inputs),
    }
    invalidated = (
        {
            "check": None,
            "scope": scope,
            "causal_stage": stage,
            "detail": f"{', '.join(differing)} changed",
        }
        if routing.invalidates
        else None
    )
    waiting = dict(manifest.get("update") or {})
    existing = {k: v for k, v in waiting.items() if k not in ("recorded_at", "recorded_by")}
    # The process that first recorded this update is the one a later run must differ from to adopt
    # it, so an unchanged update keeps its original recorder. An update recorded before processes
    # were identified has none and is recorded again, so the next fresh process can adopt it.
    already_recorded = identity_of_run_ref(waiting.get("recorded_by")) is not None
    new_update = existing != update
    recorder = (
        waiting["recorded_by"]
        if already_recorded and not new_update
        else inputs.invocation.run_ref()
    )
    existing_invalidated = (
        {k: v for k, v in dict(manifest["invalidated"]).items() if k != "recorded_at"}
        if manifest.get("invalidated")
        else None
    )
    changed = (
        new_update
        or manifest.get("state") != state
        or existing_invalidated != invalidated
        or not already_recorded
    )
    if changed:
        recorded = {k: v for k, v in manifest.items() if k != "invalidated"}
        recorded.update(
            state=state,
            update={**update, "recorded_at": _now(), "recorded_by": recorder},
        )
        if invalidated is not None:
            recorded["invalidated"] = {**invalidated, "recorded_at": _now()}
        (bundle / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(recorded))
    where = stage or "an unknown stage"
    if routing.invalidates:
        note = (
            f"invalidated ({scope}): {', '.join(differing)} changed at {where}; the candidate "
            f"no longer counts as current and re-enters at {routing.stage}; this run's update "
            "waits for a fresh zero-call rerun to adopt it"
        )
    else:
        note = (
            f"valid update available ({scope}): {', '.join(differing)} changed at {where}; "
            "the proven candidate stays valid and the update waits in the transaction"
        )
    return SealResult(
        bundle,
        state,
        dict(manifest.get("files", {})),
        manifest.get("no_op_proof"),
        changed,
        note,
    )


def _fresh_after(prior_ref: object, inputs: SealInputs) -> bool:
    """Whether this invocation is a different process from the one ``prior_ref`` names. A
    reference that names no process (a bundle sealed before processes were identified) cannot
    establish freshness, so it is not fresh."""
    prior = identity_of_run_ref(prior_ref)
    return prior is not None and not same_process(prior, inputs.invocation.identity)


def _proof(
    prior_ref: Mapping[str, Any],
    inputs: SealInputs,
    measured: Measurement,
    *,
    byte_identical: bool,
) -> dict[str, Any]:
    """The no-op proof record: every field is something this seal measured or compared.

    ``fresh_process`` is the comparison of the sealing process the bundle recorded against this
    one, ``provider_calls`` the count read from the ledger on disk, ``byte_identical`` the replay
    comparison. A caller reaches here only with all three holding (the seal withholds the proof
    otherwise), and the record names both runs so an audit can repeat the comparison.
    """
    fresh = _fresh_after(prior_ref, inputs)
    if not (fresh and byte_identical and measured.provider_calls == 0):
        raise SealError("seal: a no-op proof was requested for a rerun that does not hold one")
    return {
        "proven_at": _now(),
        "fresh_process": fresh,
        "byte_identical": byte_identical,
        "provider_calls": measured.provider_calls,
        "first_run": dict(prior_ref),
        "rerun": {**inputs.invocation.run_ref(), **measured.to_dict()},
    }


def _adopt_update(
    bundle: Path,
    manifest: dict[str, Any],
    waiting: dict[str, Any],
    staged: Mapping[str, bytes],
    inputs: SealInputs,
    measured: Measurement,
) -> SealResult:
    proof = _proof(waiting["recorded_by"], inputs, measured, byte_identical=True)
    proven = {
        **staged,
        "validation.json": _canonical_json(record_replay_verdict(inputs.validation)),
    }
    changed = [str(name) for name in waiting.get("changed", [])]
    scoped = {
        key: waiting[key]
        for key in ("scopes", "triggering_scope", "scope_basis")
        if waiting.get(key) is not None
    }
    adopted = {
        **scoped,
        "classification": waiting.get("classification"),
        "earliest_affected_stage": waiting.get("earliest_affected_stage"),
        "changed": changed,
        "recorded_at": waiting.get("recorded_at"),
        "previous_proof": manifest.get("no_op_proof"),
        "previous_models_used": sealed_models(bundle, manifest),
        "adopted_at": proof["proven_at"],
    }
    files = _write_bundle(
        bundle,
        proven,
        state=STATE_READY,
        proof=proof,
        provider_calls=measured.provider_calls,
        inputs=inputs,
        extra={"adopted": adopted},
    )
    return SealResult(
        bundle,
        STATE_READY,
        files,
        proof,
        True,
        f"update adopted ({waiting.get('triggering_scope') or waiting.get('classification')}): "
        "a fresh process reproduced the "
        f"waiting update byte for byte with zero provider calls; "
        f"{', '.join(changed)} replaced; check 11 judged",
    )


INVALIDATING_CHECKS = frozenset(
    {"BC-01", "BC-02", "BC-03", "BC-04", "BC-05", "BC-06", "BC-08", "BC-09"}
)
INVALIDATING_VERDICTS = frozenset({"REJECT_FACTUAL", "REJECT_PRESERVATION"})


def invalidates(check: Mapping[str, Any]) -> bool:
    """Whether a failing check is a factual, safety, or protected-content failure, the only
    failures that invalidate an accepted candidate (docs/STATE_MACHINE.md section 9)."""
    if check.get("id") in INVALIDATING_CHECKS:
        return True
    # The reviewer's verdict is a field on the check record; reading it out of details[0] made a
    # detail string a control plane (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC8).
    return check.get("id") == "BC-10" and check.get("review_verdict") in INVALIDATING_VERDICTS


def invalidate_bundle(bundle: Path, check: Mapping[str, Any]) -> dict[str, Any] | None:
    """Record INVALIDATED on the bundle's manifest for a failing check; None without a bundle."""
    manifest = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    if manifest is None:
        return None
    # Every reason the check gave, joined for the reader: taking the first alone lost the rest
    # and made a detail string a control plane (RESEARCH_AND_GUIDELINES.md section 27.2 RC8).
    record = {
        "check": check.get("id"),
        "causal_stage": check.get("causal_stage"),
        "detail": "; ".join(str(detail) for detail in check.get("details", [])),
        "recorded_at": _now(),
    }
    updated = {**manifest, "state": STATE_INVALIDATED, "invalidated": record}
    (bundle / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(updated))
    return updated


STATE_SUPERSEDED = "SUPERSEDED"


def _supersede_siblings(bundle: Path) -> list[str]:
    """Older proven revisions of the same repository stay in place as SUPERSEDED once a newer
    revision is proven (docs/README_CONTRACT.md section 7); returns the revisions marked."""
    marked: list[str] = []
    for sibling in sorted(p for p in bundle.parent.iterdir() if p.is_dir() and p != bundle):
        manifest = _read_manifest(sibling / BUNDLE_MANIFEST_NAME)
        if manifest is None or manifest.get("state") != STATE_READY:
            continue
        (sibling / BUNDLE_MANIFEST_NAME).write_bytes(
            _canonical_json({**manifest, "state": STATE_SUPERSEDED, "superseded_by": bundle.name})
        )
        marked.append(sibling.name)
    return marked


def seal_candidate(inputs: SealInputs) -> SealResult:
    """Seal the transaction, prove the no-op when this fresh process reproduced a sealed bundle
    with zero provider calls, or leave a proven bundle untouched."""
    bundle = bundle_directory(inputs.candidates, inputs.entry, inputs.source_revision)
    staged = _staged_artifacts(inputs)
    # The provider-call count every decision below rests on is read from the ledger on disk, by
    # this invocation's id; the caller's in-memory count must agree with it or the seal stops.
    measured = measure_invocation(
        inputs.transaction / LEDGER_FILENAME, inputs.invocation.invocation_id
    )
    if measured.provider_calls != inputs.provider_calls:
        raise LedgerReconciliationError(
            f"this process counted {inputs.provider_calls} provider calls, its ledger holds "
            f"{measured.provider_calls}"
        )
    calls = measured.provider_calls
    manifest = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    if manifest is None:
        files = _write_bundle(
            bundle,
            staged,
            state=STATE_ACCEPTED,
            proof=None,
            provider_calls=calls,
            inputs=inputs,
        )
        return SealResult(
            bundle,
            STATE_ACCEPTED,
            files,
            None,
            True,
            "sealed; the no-op proof needs a rerun in a fresh process",
        )
    verify_bundle(bundle)
    differing = sorted(
        name
        for name, data in staged.items()
        if name not in REPLAY_EXEMPT
        and (
            not (bundle / name).is_file()
            or not _identical(name, data, (bundle / name).read_bytes())
        )
    )
    # A bundle already sitting at VALID_UPDATE_AVAILABLE or INVALIDATED (a previously recorded,
    # not yet adopted update) is still a proven bundle with a waiting update: a rerun reproducing
    # that exact update must still be able to adopt it, not fall through to the destructive
    # re-seal-as-ACCEPTED branch below just because the state moved off READY_FOR_PROPOSAL.
    # The models this run answered with, against the models the bundle was sealed with: a change
    # is a consumed input that moved, so it counts exactly like a changed artifact does here.
    current_models = _current_models(inputs)
    recorded_models = sealed_models(bundle, manifest)
    changed_routes = _changed_routes(recorded_models, current_models)
    model_changes = _model_changes(recorded_models, current_models)
    # A bundle INVALIDATED by a changed factual input carries the update that re-entered the
    # pipeline and adopts it like any other waiting update; one INVALIDATED by a failing check
    # carries none and is re-sealed below instead.
    waiting_state = manifest.get("state") in (STATE_READY, STATE_UPDATE_AVAILABLE) or (
        manifest.get("state") == STATE_INVALIDATED and bool(manifest.get("update"))
    )
    if (differing or model_changes) and waiting_state and manifest.get("no_op_proof"):
        waiting = dict(manifest.get("update") or {})
        # A waiting update made with the models this run now answers with, reproduced with zero
        # calls, is the same update: adopt it. Anything else replaces it as a new recorded update.
        waiting_models = waiting.get("models_used", recorded_models)
        if (
            calls == 0
            and waiting.get("files") == _update_digests(staged)
            and waiting_models == current_models
            and _fresh_after(waiting.get("recorded_by"), inputs)
        ):
            # The waiting update is proven the way a first seal is: a fresh process reproduced
            # it byte for byte with zero provider calls, so the bundle adopts it as its proven
            # content and keeps the previous proof for the record. Scheduling that rerun is
            # the policy decision docs/STATE_MACHINE.md section 5 leaves to the operator.
            return _adopt_update(bundle, manifest, waiting, staged, inputs, measured)
        # The proven candidate stays valid; the run produced a valid update, recorded on the
        # manifest and left in the transaction (docs/STATE_MACHINE.md section 9).
        return _record_update(
            bundle, manifest, differing, staged, inputs, model_changes, changed_routes
        )
    if differing or model_changes:
        files = _write_bundle(
            bundle,
            staged,
            state=STATE_ACCEPTED,
            proof=None,
            provider_calls=calls,
            inputs=inputs,
        )
        changed = [*differing, *model_changes]
        return SealResult(
            bundle,
            STATE_ACCEPTED,
            files,
            None,
            True,
            f"re-sealed: {', '.join(changed)} changed since the last seal; proof withdrawn",
        )
    if calls > 0:
        return SealResult(
            bundle,
            str(manifest.get("state")),
            dict(manifest.get("files", {})),
            manifest.get("no_op_proof"),
            False,
            f"byte-identical, but this process made {calls} provider calls; proof withheld",
        )
    if manifest.get("state") == STATE_READY and manifest.get("no_op_proof"):
        return SealResult(
            bundle,
            STATE_READY,
            dict(manifest.get("files", {})),
            manifest.get("no_op_proof"),
            False,
            "no-op: the proven bundle was reproduced byte for byte with zero provider calls",
        )
    sealed_by = manifest.get("sealed_by")
    if identity_of_run_ref(sealed_by) is None:
        # Sealed before processes were identified: nothing records which process produced these
        # bytes, so this one cannot be shown to be a different one. The bundle is sealed again
        # recording this process, and the next fresh process proves it.
        files = _write_bundle(
            bundle, staged, state=STATE_ACCEPTED, proof=None, provider_calls=calls, inputs=inputs
        )
        return SealResult(
            bundle,
            STATE_ACCEPTED,
            files,
            None,
            True,
            "sealed again: the bundle recorded no sealing process, so the no-op proof is "
            "withheld until a fresh process reruns it",
        )
    if not _fresh_after(sealed_by, inputs):
        return SealResult(
            bundle,
            str(manifest.get("state")),
            dict(manifest.get("files", {})),
            manifest.get("no_op_proof"),
            False,
            "byte-identical, but this is the process that sealed the bundle, not a fresh one; "
            "proof withheld",
        )
    proof = _proof(
        cast(Mapping[str, Any], sealed_by), inputs, measured, byte_identical=not differing
    )
    judged = record_replay_verdict(inputs.validation)
    proven = {**staged, "validation.json": _canonical_json(judged)}
    files = _write_bundle(
        bundle, proven, state=STATE_READY, proof=proof, provider_calls=calls, inputs=inputs
    )
    _supersede_siblings(bundle)
    return SealResult(
        bundle,
        STATE_READY,
        files,
        proof,
        True,
        "no-op proven: a fresh process reproduced every artifact byte for byte with zero "
        "provider calls; check 11 judged",
    )
