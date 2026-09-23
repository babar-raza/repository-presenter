"""Phase 0 capture: wraps the read-only GitHub client and writes a checksum-valid artifact."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.metadata.capture import (
    CAPTURE_FILENAME,
    capture_repo_metadata,
    write_capture,
)
from repository_presenter.core.registry.models import RegistryEntry

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def _fetch(body: object) -> object:
    def fetch(url: str, token: str | None) -> tuple[int, object]:
        return 200, body

    return fetch


def test_capture_reads_the_entrys_own_owner_and_name() -> None:
    seen: list[str] = []

    def fetch(url: str, token: str | None) -> tuple[int, object]:
        seen.append(url)
        return 200, {"description": "x", "homepage": None, "topics": []}

    observed = capture_repo_metadata(
        ENTRY, token="ghp_test", fetch=fetch, clock=lambda: "2026-09-23T00:00:00Z"
    )
    assert seen == ["https://api.github.com/repos/aspose-3d-foss/Aspose.3D-FOSS-for-Python"]
    assert observed.repository == "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    assert observed.observed_at == "2026-09-23T00:00:00Z"


def test_write_capture_produces_sorted_key_json_and_a_matching_digest(tmp_path: Path) -> None:
    observed = capture_repo_metadata(
        ENTRY,
        token=None,
        fetch=_fetch(
            {
                "description": "A 3D library",
                "homepage": "https://products.aspose.org/3d/python/",
                "topics": ["python", "3d"],
            }
        ),
        clock=lambda: "2026-09-23T00:00:00Z",
    )
    path = tmp_path / CAPTURE_FILENAME
    digest = write_capture(observed, path)
    data = path.read_bytes()
    assert digest == __import__("hashlib").sha256(data).hexdigest()
    parsed = json.loads(data)
    assert parsed == {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "description": "A 3D library",
        "homepage": "https://products.aspose.org/3d/python/",
        "topics": ["python", "3d"],
        "observed_at": "2026-09-23T00:00:00Z",
        "schema_version": 1,
    }
    # sorted-key, trailing-newline JSON - a rerun against an unchanged observation is byte-identical
    assert data == (json.dumps(parsed, indent=2, sort_keys=True) + "\n").encode("utf-8")


def test_write_capture_creates_missing_parent_directories(tmp_path: Path) -> None:
    observed = capture_repo_metadata(
        ENTRY, token=None, fetch=_fetch({"description": None, "homepage": None, "topics": []})
    )
    path = tmp_path / "nested" / "dir" / CAPTURE_FILENAME
    write_capture(observed, path)
    assert path.is_file()
