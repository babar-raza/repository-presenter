"""The portfolio dry run: what every CURRENT sealed bundle would become under the running code.

A pure read. It compares each current bundle's own ``dependencies.json`` with the inputs the
running code owns (prompt hashes, component, check, contract, acceptance-profile and policy
versions, extractor versions), routes every difference through the invalidation scope table
(``invalidation.py``), and reports the manifest state a re-run would record. It never clones,
never calls a provider, never writes, and never touches a sealed bundle.

What it cannot see is reported as unchanged rather than guessed: the source revision and tree, the
fact records, and the host-observed environment (Python version, OS, installed package set) need
a clone or the original host. A ``facts`` scope therefore never appears here; it appears only in
a real run, when ``evaluation.evaluate`` compares the live extraction with the sealed record.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.bundle.evaluation import evaluate
from repository_presenter.components.readme.bundle.invalidation import (
    STATE_INVALIDATED,
    STATE_UPDATE_AVAILABLE,
    Routing,
    route,
)
from repository_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    DEPENDENCIES_FILENAME,
)

HELD_STATES = frozenset({STATE_INVALIDATED, STATE_UPDATE_AVAILABLE})
_CODE_OWNED = (
    "prompts",
    "contract_version",
    "components",
    "validators",
    "validator_version",
    "acceptance_profile_version",
    "policy",
)
_CODE_OWNED_ENVIRONMENT = ("extractor_version", "inherited_units_version")


@dataclass(frozen=True)
class BundleRouting:
    """What one CURRENT sealed bundle would become if it were re-run against the running code."""

    repository_dir: str
    revision: str
    state: str  # the manifest state today
    changed: tuple[str, ...]  # input classes that differ
    routing: Routing

    @property
    def would_become(self) -> str:
        """A bundle with no changed code-owned input keeps its state; otherwise the routing's."""
        return self.routing.state or self.state


def code_derived_dependencies(
    sealed: Mapping[str, Any], current_code: Mapping[str, Any]
) -> dict[str, Any]:
    """The sealed record with only the inputs the candidate consumed, and the running code owns,
    replaced by the running code's value.

    A prompt, component or check the sealed record never named is a component the candidate did
    not consume, so it cannot reopen it (docs/STATE_MACHINE.md section 9): only the keys the
    sealed record holds are compared, as ``stale_candidates`` already does.
    """
    merged = dict(sealed)
    for key in _CODE_OWNED:
        if key not in sealed or key not in current_code:
            continue
        sealed_value, current_value = sealed[key], current_code[key]
        if isinstance(sealed_value, dict) and isinstance(current_value, dict):
            merged[key] = {
                name: current_value[name] for name in sealed_value if name in current_value
            } | {name: value for name, value in sealed_value.items() if name not in current_value}
        else:
            merged[key] = current_value
    environment = dict(sealed.get("environment", {}))
    current_environment = current_code.get("environment", {})
    for name in _CODE_OWNED_ENVIRONMENT:
        if name in environment and name in current_environment:
            environment[name] = current_environment[name]
    merged["environment"] = environment
    return merged


def portfolio_routing(root: Path, current_code: Mapping[str, Any]) -> list[BundleRouting]:
    """Every CURRENT bundle under ``candidates/``, routed against ``current_code`` (the shape of
    ``seal.upstream_dependencies``); an unreadable bundle is skipped, as ``stale_candidates`` does,
    since integrity is ``status``'s own separate check."""
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    rows: list[BundleRouting] = []
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        pointer = repository_dir / CURRENT_FILENAME
        if not pointer.is_file():
            continue
        revision = pointer.read_text(encoding="utf-8").strip()
        bundle = repository_dir / revision
        try:
            manifest = json.loads((bundle / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8"))
            sealed = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict) or not isinstance(sealed, dict):
            continue
        evaluation = evaluate(sealed, code_derived_dependencies(sealed, current_code))
        changed = tuple(change.dependency for change in evaluation.changes)
        rows.append(
            BundleRouting(
                repository_dir.name, revision, str(manifest.get("state")), changed, route(changed)
            )
        )
    return rows


@dataclass(frozen=True)
class HeldUpdate:
    """A CURRENT bundle whose manifest records an update that has not been adopted yet."""

    repository_dir: str
    revision: str
    state: str
    scope: str | None  # the triggering scope the manifest recorded; None for an older record
    stage: str | None  # the earliest affected stage the manifest recorded


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def held_updates(root: Path) -> list[HeldUpdate]:
    """Every CURRENT bundle sitting at VALID_UPDATE_AVAILABLE or INVALIDATED, with the scope its
    manifest names as the trigger (``update.triggering_scope``, or ``invalidated.scope``). A pure
    read, as :func:`portfolio_routing` is."""
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    held: list[HeldUpdate] = []
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        pointer = repository_dir / CURRENT_FILENAME
        if not pointer.is_file():
            continue
        revision = pointer.read_text(encoding="utf-8").strip()
        try:
            manifest = json.loads(
                (repository_dir / revision / BUNDLE_MANIFEST_NAME).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict) or manifest.get("state") not in HELD_STATES:
            continue
        update = _mapping(manifest.get("update"))
        invalidated = _mapping(manifest.get("invalidated"))
        held.append(
            HeldUpdate(
                repository_dir.name,
                revision,
                str(manifest["state"]),
                update.get("triggering_scope") or invalidated.get("scope"),
                update.get("earliest_affected_stage") or invalidated.get("causal_stage"),
            )
        )
    return held
