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
previous proof on the manifest for the record.

Two files carry timestamps by design and are exempt from the byte comparison: the ledger and the
manifest itself. validation.json is compared with check 11 blanked, since the proof is what
judges it. CURRENT names the revision a reviewer opens.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import SHELL_VERSION
from repository_presenter.components.readme.composition.policy import (
    POLICY_VERSION,
    policy_packet,
)
from repository_presenter.components.readme.composition.renderer import RENDERER_VERSION
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    VALIDATOR_VERSION,
    record_replay_verdict,
)
from repository_presenter.core.candidates import BUNDLE_MANIFEST_NAME
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.facts import FactsDocument
from repository_presenter.core.llm.ledger import canonical_hash
from repository_presenter.core.llm.prompts import PromptRegistry
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret, scan_for_secrets

DEPENDENCIES_FILENAME = "dependencies.json"
CURRENT_FILENAME = "CURRENT"
CONTRACT_VERSION = "readme-contract-v1-draft"
ACCEPTANCE_PROFILE_VERSION = None  # the 30-point profile arrives at G2
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
OPTIONAL_ARTIFACTS = ("investigation.json", "content_units.json", "repairs.json")
REPLAY_EXEMPT = frozenset({"calls.jsonl", BUNDLE_MANIFEST_NAME})
STATE_ACCEPTED = "ACCEPTED"
STATE_READY = "READY_FOR_PROPOSAL"


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
    earliest_affected_stage: str | None = None


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


def upstream_dependencies(
    source_revision: str, tree_sha256: str, facts: FactsDocument, prompts: PromptRegistry
) -> dict[str, Any]:
    """The inputs a run consumes before any agentic stage, each by a hash that reopens a stage
    when it changes (docs/STATE_MACHINE.md section 9): known before the first call, so an
    evaluation can name the earliest affected stage without running anything."""
    return {
        "schema_version": 1,
        "source": {"revision": source_revision, "tree_sha256": tree_sha256},
        "facts": {
            fact.id: canonical_hash(asdict(fact))
            for fact in sorted(facts.facts, key=lambda fact: fact.id)
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
        "components": {"shell": SHELL_VERSION, "renderer": RENDERER_VERSION},
        "validators": {check.id: check.version for check in BLOCKING_CHECKS},
        "validator_version": VALIDATOR_VERSION,
        "acceptance_profile_version": ACCEPTANCE_PROFILE_VERSION,
        "policy": {"version": POLICY_VERSION, "sha256": canonical_hash(policy_packet())},
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
    staged[DEPENDENCIES_FILENAME] = _canonical_json(dependencies_document(inputs))
    return staged


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
    bundle.mkdir(parents=True, exist_ok=True)
    for name, data in staged.items():
        (bundle / name).write_bytes(data)
    files = {
        name: {"sha256": _sha256(data), "bytes": len(data)} for name, data in sorted(staged.items())
    }
    manifest = {
        "schema_version": 1,
        "repository": inputs.entry.repository,
        "revision": inputs.source_revision,
        "state": state,
        "sealed_at": _now(),
        "files": files,
        "provider_calls": provider_calls,
        "no_op_proof": proof,
        "composition": _composition(staged),
        **dict(extra or {}),
    }
    (bundle / BUNDLE_MANIFEST_NAME).write_bytes(_canonical_json(manifest))
    current = bundle.parent / CURRENT_FILENAME
    pointer = f"{inputs.source_revision}\n".encode()
    if not current.is_file() or current.read_bytes() != pointer:
        current.write_bytes(pointer)
    leaks = scan_for_secrets(bundle, inputs.secrets)
    if leaks:
        names = ", ".join(sorted({f"{leak.variable} in {leak.path.name}" for leak in leaks}))
        raise BundleLeakError(f"seal: a configured secret appears in the bundle: {names}")
    return files


def verify_bundle(bundle: Path) -> dict[str, Any] | None:
    """The bundle's manifest, after every file it lists is present with its recorded digest;
    a missing or corrupt artifact fails closed naming the file. None when there is no bundle."""
    manifest = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    if manifest is None:
        return None
    for name, digest in sorted(dict(manifest.get("files", {})).items()):
        path = bundle / name
        if not path.is_file():
            raise SealError(f"bundle artifact {name} is missing from {bundle.name}")
        data = path.read_bytes()
        if _sha256(data) != digest.get("sha256") or len(data) != digest.get("bytes"):
            raise SealError(f"bundle artifact {name} is corrupt in {bundle.name}")
    return manifest


FACTUAL_ARTIFACTS = frozenset({"facts.json", "dispositions.json"})
EARLY_STATES = frozenset({"EXTRACTING", "INVESTIGATING", "RECONCILING"})


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
) -> SealResult:
    factual = bool(FACTUAL_ARTIFACTS & set(differing)) or (
        inputs.earliest_affected_stage in EARLY_STATES
    )
    update = {
        "available": True,
        "classification": "factual" if factual else "presentation",
        "earliest_affected_stage": inputs.earliest_affected_stage,
        "changed": differing,
        "transaction": inputs.transaction.name,
        "files": _update_digests(staged),
    }
    existing = {k: v for k, v in dict(manifest.get("update") or {}).items() if k != "recorded_at"}
    changed = existing != update
    if changed:
        (bundle / BUNDLE_MANIFEST_NAME).write_bytes(
            _canonical_json({**manifest, "update": {**update, "recorded_at": _now()}})
        )
    return SealResult(
        bundle,
        STATE_READY,
        dict(manifest.get("files", {})),
        manifest.get("no_op_proof"),
        changed,
        f"valid update available ({update['classification']}): {', '.join(differing)} changed "
        f"at {inputs.earliest_affected_stage or 'an unknown stage'}; the proven candidate stays "
        "valid and the update waits in the transaction",
    )


def _adopt_update(
    bundle: Path,
    manifest: dict[str, Any],
    waiting: dict[str, Any],
    staged: Mapping[str, bytes],
    inputs: SealInputs,
) -> SealResult:
    proof = {
        "proven_at": _now(),
        "fresh_process": True,
        "byte_identical": True,
        "provider_calls": 0,
    }
    proven = {
        **staged,
        "validation.json": _canonical_json(record_replay_verdict(inputs.validation)),
    }
    changed = [str(name) for name in waiting.get("changed", [])]
    adopted = {
        "classification": waiting.get("classification"),
        "earliest_affected_stage": waiting.get("earliest_affected_stage"),
        "changed": changed,
        "recorded_at": waiting.get("recorded_at"),
        "previous_proof": manifest.get("no_op_proof"),
        "adopted_at": proof["proven_at"],
    }
    files = _write_bundle(
        bundle,
        proven,
        state=STATE_READY,
        proof=proof,
        provider_calls=0,
        inputs=inputs,
        extra={"adopted": adopted},
    )
    return SealResult(
        bundle,
        STATE_READY,
        files,
        proof,
        True,
        f"update adopted ({waiting.get('classification')}): a fresh process reproduced the "
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
    details = list(check.get("details", []))
    return check.get("id") == "BC-10" and bool(details) and details[0] in INVALIDATING_VERDICTS


def invalidate_bundle(bundle: Path, check: Mapping[str, Any]) -> dict[str, Any] | None:
    """Record INVALIDATED on the bundle's manifest for a failing check; None without a bundle."""
    manifest = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    if manifest is None:
        return None
    details = list(check.get("details", []))
    record = {
        "check": check.get("id"),
        "causal_stage": check.get("causal_stage"),
        "detail": str(details[0]) if details else "",
        "recorded_at": _now(),
    }
    updated = {**manifest, "state": "INVALIDATED", "invalidated": record}
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
    manifest = _read_manifest(bundle / BUNDLE_MANIFEST_NAME)
    if manifest is None:
        files = _write_bundle(
            bundle,
            staged,
            state=STATE_ACCEPTED,
            proof=None,
            provider_calls=inputs.provider_calls,
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
    if differing and manifest.get("state") == STATE_READY and manifest.get("no_op_proof"):
        waiting = dict(manifest.get("update") or {})
        if inputs.provider_calls == 0 and waiting.get("files") == _update_digests(staged):
            # The waiting update is proven the way a first seal is: a fresh process reproduced
            # it byte for byte with zero provider calls, so the bundle adopts it as its proven
            # content and keeps the previous proof for the record. Scheduling that rerun is
            # the policy decision docs/STATE_MACHINE.md section 5 leaves to the operator.
            return _adopt_update(bundle, manifest, waiting, staged, inputs)
        # The proven candidate stays valid; the run produced a valid update, recorded on the
        # manifest and left in the transaction (docs/STATE_MACHINE.md section 9).
        return _record_update(bundle, manifest, differing, staged, inputs)
    if differing:
        files = _write_bundle(
            bundle,
            staged,
            state=STATE_ACCEPTED,
            proof=None,
            provider_calls=inputs.provider_calls,
            inputs=inputs,
        )
        return SealResult(
            bundle,
            STATE_ACCEPTED,
            files,
            None,
            True,
            f"re-sealed: {', '.join(differing)} changed since the last seal; proof withdrawn",
        )
    if inputs.provider_calls > 0:
        return SealResult(
            bundle,
            str(manifest.get("state")),
            dict(manifest.get("files", {})),
            manifest.get("no_op_proof"),
            False,
            f"byte-identical, but this process made {inputs.provider_calls} provider calls; "
            "proof withheld",
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
    proof = {
        "proven_at": _now(),
        "fresh_process": True,
        "byte_identical": True,
        "provider_calls": 0,
    }
    judged = record_replay_verdict(inputs.validation)
    proven = {**staged, "validation.json": _canonical_json(judged)}
    files = _write_bundle(
        bundle, proven, state=STATE_READY, proof=proof, provider_calls=0, inputs=inputs
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
