"""Stage S12: seal the accepted transaction into a content-addressed bundle and prove the no-op.

The bundle at candidates/<owner>__<name>/<revision>/ (docs/README_CONTRACT.md section 7) is a
copy of the accepted transaction's artifacts plus dependencies.json, which names exactly the
inputs the candidate consumed (docs/STATE_MACHINE.md section 9), sealed by manifest.json with a
digest for every file. The first seal records state ACCEPTED with no proof. A later run in a
fresh process that reproduces every artifact byte for byte with zero provider calls is the no-op
proof: it judges check 11, records the proof in the manifest, and moves the bundle to
READY_FOR_PROPOSAL, the only state progress counts. A run that reproduces a proven bundle writes
nothing. A run whose artifacts differ re-seals at ACCEPTED and withdraws the proof.

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


def dependencies_document(inputs: SealInputs) -> dict[str, Any]:
    """Exactly the inputs the candidate consumed, each by a hash that reopens a stage when it
    changes (docs/STATE_MACHINE.md section 9); nothing else can invalidate the candidate."""
    return {
        "schema_version": 1,
        "source": {"revision": inputs.source_revision, "tree_sha256": inputs.tree_sha256},
        "facts": {
            fact.id: canonical_hash(asdict(fact))
            for fact in sorted(inputs.facts.facts, key=lambda fact: fact.id)
        },
        "prompts": {
            name: {
                "sha256": inputs.prompts[name].sha256,
                "version": inputs.prompts[name].manifest.version,
                "model_route": inputs.prompts[name].manifest.model_route,
            }
            for name in sorted(inputs.prompts.hashes())
        },
        "contract_version": CONTRACT_VERSION,
        "components": {"shell": SHELL_VERSION, "renderer": RENDERER_VERSION},
        "validators": {check.id: check.version for check in BLOCKING_CHECKS},
        "validator_version": VALIDATOR_VERSION,
        "acceptance_profile_version": ACCEPTANCE_PROFILE_VERSION,
        "protected_content_fingerprint": inputs.validation.get("protected_content_fingerprint"),
        "policy": {"version": POLICY_VERSION, "sha256": canonical_hash(policy_packet())},
    }


def _canonical_json(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


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
    differing = sorted(
        name
        for name, data in staged.items()
        if name not in REPLAY_EXEMPT
        and (
            not (bundle / name).is_file()
            or not _identical(name, data, (bundle / name).read_bytes())
        )
    )
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
    return SealResult(
        bundle,
        STATE_READY,
        files,
        proof,
        True,
        "no-op proven: a fresh process reproduced every artifact byte for byte with zero "
        "provider calls; check 11 judged",
    )
