"""The processability decision: a repository without implementation evidence fails honestly.

A README-only placeholder is the primary case (STATE_MACHINE.md section 6). The disposition names
the reason, the revision and tree hash it was decided on, every path inspected, and the predicate
that reopens the repository. Nothing agentic runs before this decision.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from repository_presenter.components.readme.extractors.platforms.registry import PlatformPlugin
from repository_presenter.core.snapshot.capture import RepositorySnapshot

DISPOSITION_FILENAME = "disposition.json"
NO_IMPLEMENTATION_EVIDENCE = "NO_IMPLEMENTATION_EVIDENCE"


@dataclass(frozen=True)
class NonProcessableDisposition:
    """Why the repository cannot receive a truthful README at this revision."""

    reason_code: str
    repository: str
    source_revision: str
    tree_sha256: str
    ecosystem: str
    evidence_paths_inspected: tuple[str, ...]
    resume_predicate: str
    schema_version: int = 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def assess_processability(
    snapshot: RepositorySnapshot,
    tree_paths: Sequence[str],
    plugin: PlatformPlugin,
    manifest_path: str | None,
) -> NonProcessableDisposition | None:
    """``None`` when the tree holds a manifest or source for the ecosystem; else the disposition."""
    source_files = sorted(
        path for path in tree_paths if Path(path).suffix in plugin.source_suffixes
    )
    if manifest_path is not None or source_files:
        return None
    inspected = tuple(sorted(tree_paths))
    return NonProcessableDisposition(
        reason_code=NO_IMPLEMENTATION_EVIDENCE,
        repository=snapshot.repository,
        source_revision=snapshot.source_revision,
        tree_sha256=snapshot.tree_sha256,
        ecosystem=plugin.ecosystem,
        evidence_paths_inspected=inspected,
        resume_predicate=(
            f"a later default-branch revision adds a {plugin.ecosystem} manifest "
            f"({', '.join(plugin.manifest_globs)}) or source files "
            f"({', '.join(sorted(plugin.source_suffixes))})"
        ),
    )


def write_disposition(disposition: NonProcessableDisposition, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(disposition.to_json().encode("utf-8"))
