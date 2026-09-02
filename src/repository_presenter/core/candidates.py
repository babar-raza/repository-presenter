"""Count current reviewable no-op-proven candidates from sealed bundles on disk.

A candidate bundle lives at ``candidates/<owner>__<name>/<revision>/`` and is sealed by its
``manifest.json``. Progress has exactly one unit: repositories whose bundle has reached
``READY_FOR_PROPOSAL``, the runtime state that records an independently accepted candidate whose
fresh-process replay was byte-identical with zero provider calls. A revision directory without a
manifest is an unsealed transaction and is ignored. A manifest that cannot be read is corrupt
evidence and is an error, never a silent zero.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

CANDIDATES_DIRNAME = "candidates"
BUNDLE_MANIFEST_NAME = "manifest.json"
COUNTED_STATES = frozenset({"READY_FOR_PROPOSAL"})


class BundleError(ValueError):
    """A sealed bundle on disk cannot be read."""


@dataclass(frozen=True)
class SealedBundle:
    """The identity and state of one sealed bundle."""

    repository_dir: str
    revision: str
    state: str


def iter_sealed_bundles(root: Path) -> Iterator[SealedBundle]:
    """Yield every sealed bundle under ``root/candidates`` in path order."""
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


def count_current_candidates(root: Path) -> int:
    """Return how many repositories have a sealed bundle in a counted state."""
    counted = {b.repository_dir for b in iter_sealed_bundles(root) if b.state in COUNTED_STATES}
    return len(counted)


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
