"""The drift monitor: is each enabled repository's upstream default branch still the revision its
sealed bundle was built from?

G7-W06 (``docs/EXECUTION_STATE_MACHINE.md`` G7 work item 3): an unattended, read-only observation.
For each enabled registry entry it reads the repository's current default-branch head through
``core/github/read_client.py`` (one bounded GET pair, the same read the redetection pass uses) and
compares it with the revision the repository's ``CURRENT`` sealed bundle names. Each repository
receives exactly one status:

- ``CURRENT``: the head equals the bundle's source revision.
- ``DRIFTED``: the head differs, so the bundle is behind upstream and due a re-run.
- ``NO_BUNDLE``: no usable sealed bundle (none, a ``CURRENT`` that names none, or one failing
  integrity verification). ``detail`` says which.
- ``UNREACHABLE``: the head could not be read. The failure is recorded and the run continues with
  the remaining repositories; one repository never aborts the others.

The status is a deterministic fact about upstream and local disk, so no LLM is involved
(``AGENTS.md``, Agentic and Deterministic Boundary). Nothing here writes to any repository, and the
only credential is the read-only token the caller passes in. ``observe_drift`` takes its GitHub
reader as an argument, so tests inject a fake and never reach the network.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from repository_presenter.core.candidates import (
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    BundleError,
    verify_bundle,
)
from repository_presenter.core.github.read_client import DefaultBranchRead, fetch_default_branch_sha
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import redact

Status = Literal["CURRENT", "DRIFTED", "NO_BUNDLE", "UNREACHABLE"]
STATUSES: tuple[Status, ...] = ("CURRENT", "DRIFTED", "NO_BUNDLE", "UNREACHABLE")
SCHEMA_VERSION = 1
_REVISION = re.compile(r"^[0-9a-f]{40}$")

HeadReader = Callable[..., DefaultBranchRead]


@dataclass(frozen=True)
class RepositoryDrift:
    """One repository's observation. A revision the run never observed is ``None``."""

    repository: str
    mode: str
    status: Status
    head_revision: str | None
    branch: str | None
    bundle_revision: str | None
    detail: str | None = None


def observe_drift(
    root: Path,
    entries: Iterable[RegistryEntry],
    *,
    token: str,
    read_head: HeadReader = fetch_default_branch_sha,
) -> list[RepositoryDrift]:
    """Observe each entry in order. A failure on one entry is recorded, never raised past it."""
    return [observe_repository(root, entry, token=token, read_head=read_head) for entry in entries]


def observe_repository(
    root: Path, entry: RegistryEntry, *, token: str, read_head: HeadReader
) -> RepositoryDrift:
    """Read one repository's head, then classify it against its ``CURRENT`` sealed bundle."""
    repository = entry.repository
    try:
        read = read_head(repository, token=token)
    except Exception as exc:  # the per-repository isolation boundary: nothing escapes it
        message = redact(f"{type(exc).__name__}: {exc}", [token])
        return RepositoryDrift(repository, entry.mode, "UNREACHABLE", None, None, None, message)
    if read.sha is None:
        message = redact(read.error or "no default-branch head returned", [token])
        return RepositoryDrift(
            repository, entry.mode, "UNREACHABLE", None, read.branch, None, message
        )
    bundle_revision, problem = current_bundle_revision(root, repository)
    if bundle_revision is None:
        return RepositoryDrift(
            repository, entry.mode, "NO_BUNDLE", read.sha, read.branch, None, problem
        )
    status: Status = "CURRENT" if read.sha == bundle_revision else "DRIFTED"
    return RepositoryDrift(
        repository, entry.mode, status, read.sha, read.branch, bundle_revision, None
    )


def current_bundle_revision(root: Path, repository: str) -> tuple[str | None, str | None]:
    """The revision ``CURRENT`` names when it has a sealed, self-consistent bundle.

    Returns ``(revision, None)`` on success and ``(None, reason)`` otherwise. Only the ``CURRENT``
    pointer is consulted, the same rule ``core/candidates.py`` applies to progress counting, so a
    superseded revision directory left behind can never stand in for the current bundle.
    """
    directory = root / CANDIDATES_DIRNAME / repository.replace("/", "__")
    pointer = directory / CURRENT_FILENAME
    if not pointer.is_file():
        return None, "no CURRENT pointer"
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
    except (OSError, ValueError) as exc:
        return None, f"CURRENT pointer is unreadable: {exc}"
    if not _REVISION.fullmatch(revision):
        return None, "CURRENT does not name a 40-character revision"
    try:
        manifest = verify_bundle(directory / revision)
    except (BundleError, OSError) as exc:
        return None, f"CURRENT bundle fails verification: {exc}"
    if manifest is None:
        return None, f"CURRENT names {revision} with no sealed bundle"
    if manifest.get("revision") != revision or manifest.get("repository") != repository:
        return None, f"bundle manifest does not describe {repository} at {revision}"
    return revision, None


def drift_document(
    observations: Sequence[RepositoryDrift], *, observed_at: str, owner: str | None
) -> dict[str, Any]:
    """The evidence document: a status summary and one row per repository, sorted by name."""
    ordered = sorted(observations, key=lambda observation: observation.repository)
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": observed_at,
        "owner": owner,
        "summary": {
            status: sum(1 for observation in ordered if observation.status == status)
            for status in STATUSES
        },
        "repositories": [asdict(observation) for observation in ordered],
    }


def write_drift_document(document: dict[str, Any], path: Path) -> Path:
    """Write the evidence document as deterministic JSON, creating its directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path
