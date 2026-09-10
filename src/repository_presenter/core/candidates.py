"""Count current reviewable no-op-proven candidates from sealed bundles on disk.

A candidate bundle lives at ``candidates/<owner>__<name>/<revision>/`` and is sealed by its
``manifest.json``. Progress has exactly one unit: repositories whose *currently pointed-at*
revision (``CURRENT``) has a bundle in ``READY_FOR_PROPOSAL``, the runtime state that records an
independently accepted candidate whose fresh-process replay was byte-identical with zero provider
calls. A revision directory without a manifest is an unsealed transaction and is ignored. A
manifest that cannot be read, fails integrity verification, or disagrees with ``CURRENT`` about
its own identity is corrupt evidence and is an error, never a silent zero.

Only the revision ``CURRENT`` names is ever consulted (TB-06, external review D6, 2026-09-08):
counting used to scan every historical revision directory and count a repository if *any* of them
was ``READY_FOR_PROPOSAL``, so an older, superseded revision left in that state - by a corrupt
write, a hand edit, or a ``_supersede_siblings`` run that never happened - inflated the count even
though a reviewer opening the repository would see a different, current revision entirely.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repository_presenter.core.errors import PresenterError
from repository_presenter.core.examples import RECEIPTS_FILENAME

CANDIDATES_DIRNAME = "candidates"
BUNDLE_MANIFEST_NAME = "manifest.json"
CURRENT_FILENAME = "CURRENT"
# Must match bundle/seal.py's own DEPENDENCIES_FILENAME - duplicated rather than imported, since
# core/ may not import a components/readme/ module (this file's own docstring; see also
# core/ecosystems.py's identical note).
DEPENDENCIES_FILENAME = "dependencies.json"
COUNTED_STATES = frozenset({"READY_FOR_PROPOSAL"})
# The only manifest shape this code knows how to trust. A future, incompatible schema_version
# must fail closed rather than have its (possibly differently-shaped) `files` map trusted as if
# it were this one (TB-06, external review D6, 2026-09-08).
SUPPORTED_SCHEMA_VERSIONS = frozenset({1})


class BundleError(PresenterError, ValueError):
    """A sealed bundle on disk cannot be read, or fails integrity or currentness verification.

    Inherits ``ValueError`` too, since that was this class's original base and nothing downstream
    should have to change how it catches this; inherits ``PresenterError`` so a caller that only
    catches presenter failures (``cli.py``'s ``run_present``) still fails closed on it rather than
    letting it escape as an unhandled exception (TB-06, external review D6, 2026-09-08 - the risk
    became real the moment ``count_current_candidates`` started calling ``verify_bundle``, which
    a corrupt or adversarial manifest can now reach from either call site).
    """


@dataclass(frozen=True)
class SealedBundle:
    """The identity and state of one sealed bundle."""

    repository_dir: str
    revision: str
    state: str


def iter_sealed_bundles(root: Path) -> Iterator[SealedBundle]:
    """Yield every sealed bundle under ``root/candidates`` in path order.

    Every revision of every repository, sealed or not proven, current or superseded: a raw
    inventory, not a progress count. ``count_current_candidates`` deliberately does not use this -
    see the module docstring.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        for revision_dir in sorted(p for p in repository_dir.iterdir() if p.is_dir()):
            manifest = revision_dir / BUNDLE_MANIFEST_NAME
            if not manifest.is_file():
                continue
            yield SealedBundle(
                repository_dir=repository_dir.name,
                revision=revision_dir.name,
                state=_read_state(manifest),
            )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(bundle: Path) -> dict[str, Any] | None:
    """The bundle's manifest, after its inventory and every file it lists check out; a missing,
    empty, corrupt, or unsupported-schema manifest fails closed naming the problem. None when
    there is no bundle at all.

    Checks, each independently regression-tested (TB-06, external review D6, 2026-09-08): the
    manifest is a readable JSON object naming a non-empty ``state``; it declares a
    ``schema_version`` this code knows how to read; its ``files`` inventory is non-empty (an
    empty inventory is not "nothing to verify", it is a bundle that was never really sealed);
    every listed file is present on disk; every listed file's digest matches what is actually
    there.
    """
    manifest_path = bundle / BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BundleError(f"unreadable bundle manifest: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BundleError(f"bundle manifest is not an object: {manifest_path}")
    state = manifest.get("state")
    if not isinstance(state, str) or not state:
        raise BundleError(f"bundle manifest has no state: {manifest_path}")
    schema_version = manifest.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise BundleError(
            f"bundle manifest has unsupported schema_version {schema_version!r}: {manifest_path}"
        )
    files = dict(manifest.get("files", {}))
    if not files:
        raise BundleError(f"bundle manifest lists no files: {manifest_path}")
    for name, digest in sorted(files.items()):
        path = bundle / name
        if not path.is_file():
            raise BundleError(f"bundle artifact {name} is missing from {bundle.name}")
        data = path.read_bytes()
        if not isinstance(digest, dict) or (
            _sha256(data) != digest.get("sha256") or len(data) != digest.get("bytes")
        ):
            raise BundleError(f"bundle artifact {name} is corrupt in {bundle.name}")
    return manifest


def integrity_valid_candidates(root: Path) -> int:
    """How many repositories have a `CURRENT` bundle that passes `verify_bundle` cleanly.

    PA-03's second count: a pass/fail wrapper around the same check `count_current_candidates`
    already applies, but reported as a count on its own rather than raising on the first bad
    bundle - a repository whose `CURRENT` names no sealed bundle, or whose manifest fails
    integrity verification, simply is not counted here, the same way a repository with no
    `CURRENT` at all is not counted (this is a portfolio-health signal, not a gate; the raising
    behaviour `count_current_candidates` still needs for its own contract is untouched).
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return 0
    valid = 0
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        try:
            manifest = verify_bundle(repository_dir / revision)
        except BundleError:
            continue
        if manifest is not None:
            valid += 1
    return valid


def count_current_candidates(root: Path) -> int:
    """Return how many repositories have their ``CURRENT`` revision sealed in a counted state.

    Reads ``CURRENT``, resolves to that exact revision's manifest, and verifies it - never scans
    every historical revision directory for any counted state (see the module docstring). A
    repository with no ``CURRENT`` file has never sealed anything and is silently not counted; a
    ``CURRENT`` that names a revision without a valid, self-consistent bundle is corrupt evidence
    and is an error.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return 0
    counted = 0
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        manifest = verify_bundle(repository_dir / revision)
        if manifest is None:
            raise BundleError(
                f"{repository_dir.name}: CURRENT names revision {revision!r} with no sealed "
                "bundle there"
            )
        if manifest.get("revision") != revision:
            raise BundleError(
                f"{repository_dir.name}: bundle manifest revision {manifest.get('revision')!r} "
                f"does not match CURRENT {revision!r}"
            )
        # The inverse of seal.py's bundle_directory(): candidates/<owner>__<name>/<revision>,
        # where owner and name are exactly repository.split("/") - so a manifest's own claimed
        # repository must map back to the directory it was actually found under.
        if str(manifest.get("repository", "")).replace("/", "__") != repository_dir.name:
            raise BundleError(
                f"{repository_dir.name}: bundle manifest repository "
                f"{manifest.get('repository')!r} does not match its directory"
            )
        if manifest.get("state") in COUNTED_STATES:
            counted += 1
    return counted


def examples_verification_summary(root: Path) -> tuple[int, int]:
    """``(executed, total)`` examples across every ``CURRENT`` bundle in a counted state, read
    from each bundle's own ``examples.json``.

    Taskcard F Tier 4: a non-blocking, portfolio-visible signal - a candidate with unresolved or
    failed examples still counts toward ``count_current_candidates``'s own N/34 exactly as it
    already does; nothing here changes that or any blocking check. Assumes the caller already
    established bundle integrity in the same pass (e.g. via ``count_current_candidates`` just
    before it), so this reads ``manifest.json``'s state and ``examples.json`` directly rather than
    re-verifying every file's digest a second time; a bundle with no ``examples.json`` (an
    ecosystem that verifies nothing, or a seal that predates this file) contributes zero to both
    counts, not an error - this signal is informational, never a reason to fail closed.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return (0, 0)
    executed = 0
    total = 0
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        bundle = repository_dir / revision
        manifest_path = bundle / BUNDLE_MANIFEST_NAME
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(manifest, dict) or manifest.get("state") not in COUNTED_STATES:
            continue
        examples_path = bundle / RECEIPTS_FILENAME
        if not examples_path.is_file():
            continue
        try:
            receipts = json.loads(examples_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(receipts, list):
            continue
        for receipt in receipts:
            if isinstance(receipt, dict):
                total += 1
                if receipt.get("outcome") == "EXECUTED":
                    executed += 1
    return (executed, total)


@dataclass(frozen=True)
class StaleCandidate:
    """One CURRENT candidate whose dependencies.json names a component or check version older
    than what the running code currently declares."""

    repository_dir: str
    revision: str
    reasons: tuple[str, ...]


def stale_candidates(
    root: Path,
    current_components: Mapping[str, str],
    current_validators: Mapping[str, str],
    current_validator_version: str,
) -> list[StaleCandidate]:
    """Every CURRENT candidate whose sealed ``dependencies.json`` is behind the running code, by
    the same versioning rule ``docs/STATE_MACHINE.md`` section 9 already defines (a component or
    validator version change reopens the earliest affected stage of every candidate that consumed
    it) - read back as a report instead of requiring a human to diff ``test_sealed_bytes.py``'s
    raw bytes and reason about it by hand each time (2026-09-09,
    ``docs/CI_AND_STALENESS_ASSESSMENT.md``: two version bumps were silently skipped in one
    session before this report existed, and the resulting staleness was invisible until a raw
    byte comparison against committed state was run by hand).

    A pure read: no clone, no provider call, no state change, and it cannot itself invalidate a
    candidate - it only reports what the existing rule already says. The caller supplies the
    running code's current version values, since this module may not import the higher-level
    modules (``renderer.py``, ``validation/registry.py``) that own them.

    A candidate whose ``dependencies.json`` predates a given component or check entirely (an
    older schema that never recorded it) is silently not flagged for that one - a component this
    code has never heard of cannot be judged stale by it, only genuinely absent recordings are
    skipped, never invented.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    stale: list[StaleCandidate] = []
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        current = repository_dir / CURRENT_FILENAME
        if not current.is_file():
            continue
        revision = current.read_text(encoding="utf-8").strip()
        deps_path = repository_dir / revision / DEPENDENCIES_FILENAME
        if not deps_path.is_file():
            continue
        try:
            deps = json.loads(deps_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(deps, dict):
            continue
        reasons: list[str] = []
        recorded_components = deps.get("components") or {}
        for name, current_value in sorted(current_components.items()):
            recorded = recorded_components.get(name)
            if recorded is not None and recorded != current_value:
                reasons.append(f"components.{name} {recorded} -> {current_value}")
        recorded_validators = deps.get("validators") or {}
        for check_id, current_value in sorted(current_validators.items()):
            recorded = recorded_validators.get(check_id)
            if recorded is not None and recorded != current_value:
                reasons.append(f"validators.{check_id} {recorded} -> {current_value}")
        recorded_validator_version = deps.get("validator_version")
        if (
            recorded_validator_version is not None
            and recorded_validator_version != current_validator_version
        ):
            reasons.append(
                f"validator_version {recorded_validator_version} -> {current_validator_version}"
            )
        if reasons:
            stale.append(StaleCandidate(repository_dir.name, revision, tuple(reasons)))
    return stale


def _read_state(manifest: Path) -> str:
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"unreadable bundle manifest: {manifest}: {exc}") from exc
    if not isinstance(raw, dict):
        raise BundleError(f"bundle manifest is not an object: {manifest}")
    state = raw.get("state")
    if not isinstance(state, str) or not state:
        raise BundleError(f"bundle manifest has no state: {manifest}")
    return state
