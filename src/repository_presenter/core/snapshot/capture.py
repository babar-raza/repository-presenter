"""Capture one immutable view of a pinned clone and write it as the ``source/`` stage artifact.

The artifact is a pure function of the revision: it carries no timestamps and no absolute paths,
so a rerun on the same revision is byte-identical. The tree inventory is git's own
``ls-tree -r --full-tree HEAD`` listing, and the README is copied byte for byte under its own
name. Drift between capture and any later stage fails closed through :func:`verify_snapshot`.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from repository_presenter.core.errors import RepositorySnapshotError
from repository_presenter.core.git_safety.clone import ReadOnlyClone
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.snapshot.inventory import scan

SNAPSHOT_FILENAME = "snapshot.json"
TREE_FILENAME = "tree.txt"


@dataclass(frozen=True)
class RepositorySnapshot:
    """The identity and checksums of one immutable repository view."""

    repository: str
    clone_url: str
    source_revision: str
    tree_sha256: str
    tree_entries: int
    readme_path: str | None
    readme_sha256: str | None
    license_path: str | None
    notices_path: str | None = None
    schema_version: int = 1


@dataclass(frozen=True)
class SourceArtifacts:
    """The files written under ``source/`` and one digest over all of them."""

    directory: Path
    files: tuple[str, ...]
    digest: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_text(root: Path, args: list[str], label: str) -> str:
    result = run_git(args, cwd=root, timeout=60)
    if result.returncode != 0:
        raise RepositorySnapshotError(f"cannot capture {label} in {root}: {result.stderr}")
    return result.stdout


def _tree_listing(root: Path) -> str:
    return _git_text(root, ["ls-tree", "-r", "--full-tree", "HEAD"], "repository tree inventory")


def _relative(root: Path, path: Path | None) -> str | None:
    return None if path is None else path.relative_to(root).as_posix()


def capture_snapshot(repository: str, clone: ReadOnlyClone) -> RepositorySnapshot:
    """Read the checked-out revision, tree inventory, README, and license of ``clone``."""
    root = clone.path
    if not root.is_dir():
        raise RepositorySnapshotError(f"snapshot root does not exist: {root}")
    revision = _git_text(root, ["rev-parse", "HEAD"], "repository revision").strip()
    if revision != clone.revision:
        raise RepositorySnapshotError(
            f"clone of {repository} is at {revision}, not the pinned {clone.revision}"
        )
    listing = _tree_listing(root)
    inventory = scan(root)
    readme_sha256 = (
        _sha256(inventory.readme_path.read_bytes()) if inventory.readme_path is not None else None
    )
    return RepositorySnapshot(
        repository=repository,
        clone_url=clone.clone_url,
        source_revision=revision,
        tree_sha256=_sha256(listing.encode("utf-8")),
        tree_entries=len(listing.splitlines()),
        readme_path=_relative(root, inventory.readme_path),
        readme_sha256=readme_sha256,
        license_path=_relative(root, inventory.license_path),
        notices_path=_relative(root, inventory.notices_path),
    )


def write_source_artifacts(
    snapshot: RepositorySnapshot, clone_path: Path, directory: Path
) -> SourceArtifacts:
    """Write ``snapshot.json``, ``tree.txt``, and the exact README bytes under ``directory``."""
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    (directory / TREE_FILENAME).write_bytes(_tree_listing(clone_path).encode("utf-8"))
    if snapshot.readme_path is not None:
        source = clone_path / snapshot.readme_path
        (directory / source.name).write_bytes(source.read_bytes())
    document = json.dumps(asdict(snapshot), indent=2, sort_keys=True) + "\n"
    (directory / SNAPSHOT_FILENAME).write_bytes(document.encode("utf-8"))
    files = tuple(sorted(p.name for p in directory.iterdir() if p.is_file()))
    digest_input = "".join(
        f"{name}\0{_sha256((directory / name).read_bytes())}\n" for name in files
    )
    return SourceArtifacts(directory=directory, files=files, digest=_sha256(digest_input.encode()))


def verify_snapshot(snapshot: RepositorySnapshot, clone_path: Path) -> None:
    """Fail closed if the clone, its tree, or its README changed since capture."""
    if not clone_path.is_dir():
        raise RepositorySnapshotError(f"snapshot root disappeared: {clone_path}")
    revision = _git_text(clone_path, ["rev-parse", "HEAD"], "repository revision").strip()
    if revision != snapshot.source_revision:
        raise RepositorySnapshotError(
            f"snapshot revision drifted from {snapshot.source_revision} to {revision}"
        )
    if _sha256(_tree_listing(clone_path).encode("utf-8")) != snapshot.tree_sha256:
        raise RepositorySnapshotError("snapshot tree inventory changed during the transaction")
    if snapshot.readme_path is not None:
        readme = clone_path / snapshot.readme_path
        if not readme.is_file():
            raise RepositorySnapshotError("snapshot README disappeared during the transaction")
        if _sha256(readme.read_bytes()) != snapshot.readme_sha256:
            raise RepositorySnapshotError("snapshot README changed during the transaction")


def list_tree_paths(clone_path: Path) -> list[str]:
    """Every tracked path at HEAD, from the same ``ls-tree`` listing the artifact records."""
    listing = _tree_listing(clone_path)
    return [line.split("\t", 1)[1] for line in listing.splitlines() if "\t" in line]
