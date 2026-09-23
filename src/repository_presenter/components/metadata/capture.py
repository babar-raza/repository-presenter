"""Phase 0: capture GitHub's currently-observed repo metadata, read-only.

``GET /repos/{owner}/{repo}`` only, at the same repository-scoped read access Gate A/B already use
to clone (``GH_TOKEN``); no new credential scope
(docs/investigations/02-repo-metadata-community-files.md section 5, Phase 0). The result is written
as a typed, versioned JSON artifact mirroring ``core/snapshot/capture.py``'s own
``RepositorySnapshot`` shape: a plain dataclass with an embedded ``schema_version``, serialized with
sorted keys so a rerun against an unchanged GitHub observation is byte-identical, and a SHA-256
digest over those bytes for checksum-valid evidence (AGENTS.md "Testing and Evidence").
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from repository_presenter.core.github.client import (
    ClockFn,
    FetchFn,
    ObservedRepository,
    default_fetch,
    get_repository,
)
from repository_presenter.core.registry.models import RegistryEntry

CAPTURE_FILENAME = "repo_metadata_observed.json"


def capture_repo_metadata(
    entry: RegistryEntry,
    *,
    token: str | None,
    fetch: FetchFn = default_fetch,
    clock: ClockFn | None = None,
) -> ObservedRepository:
    """Read ``entry``'s current GitHub description/homepage/topics. Never writes anything."""
    kwargs = {"clock": clock} if clock is not None else {}
    return get_repository(entry.owner, entry.name, token=token, fetch=fetch, **kwargs)


def write_capture(observed: ObservedRepository, path: Path) -> str:
    """Write ``observed`` as sorted-key JSON and return the SHA-256 of the written bytes."""
    payload = asdict(observed)
    payload["topics"] = list(observed.topics)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
