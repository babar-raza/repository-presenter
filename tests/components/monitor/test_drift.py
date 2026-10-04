"""The drift monitor (G7-W06): each enabled registry repository's upstream default-branch head,
compared with the revision its CURRENT sealed bundle was built from.

Every GitHub read is injected through ``FakeDefaultBranchReader``, a stand-in for
``core/github/read_client.py::fetch_default_branch_sha`` - no test here reaches the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.monitor.drift import (
    RepositoryDrift,
    drift_document,
    observe_drift,
)
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.registry.models import Registry, RegistryEntry
from support import FakeDefaultBranchReader, monitor_registry_entry, write_bundle

TOKEN = "ghs_fixture_read_token_value_0123456789"
BUNDLED = "1111111111111111111111111111111111111111"
NEWER = "2222222222222222222222222222222222222222"
OLDER = "3333333333333333333333333333333333333333"
PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
JAVA = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
PYTHON_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"


def entries_of(*raw: dict[str, Any]) -> tuple[RegistryEntry, ...]:
    return Registry.model_validate({"schema_version": 1, "entries": list(raw)}).entries


def observe_one(root: Path, repository: str, reader: FakeDefaultBranchReader) -> RepositoryDrift:
    (observation,) = observe_drift(
        root, entries_of(monitor_registry_entry(repository)), token=TOKEN, read_head=reader
    )
    return observation


def test_head_equal_to_the_bundle_revision_is_current(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "CURRENT"
    assert observation.head_revision == BUNDLED
    assert observation.bundle_revision == BUNDLED


def test_a_different_head_is_drifted_and_both_revisions_are_recorded(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: NEWER}))

    assert observation.status == "DRIFTED"
    assert observation.head_revision == NEWER
    assert observation.bundle_revision == BUNDLED


def test_a_repository_without_any_bundle_is_no_bundle(tmp_path: Path) -> None:
    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: NEWER}))

    assert observation.status == "NO_BUNDLE"
    assert observation.head_revision == NEWER
    assert observation.bundle_revision is None
    assert observation.detail == "no CURRENT pointer"


def test_a_current_bundle_that_fails_integrity_verification_is_no_bundle(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, None, raw="{ not json")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "NO_BUNDLE"
    assert observation.bundle_revision is None
    assert observation.detail is not None
    assert "fails verification" in observation.detail


def test_a_manifest_describing_another_revision_is_not_trusted(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["revision"] = OLDER
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "NO_BUNDLE"
    assert observation.detail is not None
    assert "does not describe" in observation.detail


def test_a_read_failure_is_unreachable_and_never_stops_the_other_repositories(
    tmp_path: Path,
) -> None:
    # Negative control: the failing repositories come first, so an abort would skip the healthy one.
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    reader = FakeDefaultBranchReader(
        {
            JAVA: ConnectionError("connection reset"),
            NET: DefaultBranchRead(NET, error="HTTP 503"),
            PYTHON: BUNDLED,
        }
    )
    registry = entries_of(
        monitor_registry_entry(JAVA, repository_id=2),
        monitor_registry_entry(NET, repository_id=3),
        monitor_registry_entry(PYTHON, repository_id=1),
    )

    observations = observe_drift(tmp_path, registry, token=TOKEN, read_head=reader)

    assert reader.calls == [JAVA, NET, PYTHON]
    assert [(o.repository, o.status) for o in observations] == [
        (JAVA, "UNREACHABLE"),
        (NET, "UNREACHABLE"),
        (PYTHON, "CURRENT"),
    ]
    assert observations[0].detail == "ConnectionError: connection reset"
    assert observations[1].detail == "HTTP 503"
    assert observations[1].bundle_revision is None
    assert observations[2].bundle_revision == BUNDLED


def test_an_unreachable_repository_keeps_no_revision_it_never_observed(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(
        tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: RuntimeError("boom")})
    )

    assert observation.status == "UNREACHABLE"
    assert observation.head_revision is None
    assert observation.bundle_revision is None


def test_the_read_token_is_passed_to_the_reader_and_never_appears_in_evidence(
    tmp_path: Path,
) -> None:
    reader = FakeDefaultBranchReader({PYTHON: RuntimeError(f"401 for Bearer {TOKEN}")})

    observations = observe_drift(
        tmp_path, entries_of(monitor_registry_entry(PYTHON)), token=TOKEN, read_head=reader
    )
    document = drift_document(observations, observed_at="2026-10-04T00:00:00+00:00", owner=None)

    assert reader.tokens == [TOKEN]
    assert TOKEN not in json.dumps(document)
    assert "[REDACTED]" in (observations[0].detail or "")


def test_the_document_counts_every_status_and_lists_repositories_in_order(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    observations = [
        observe_one(tmp_path, JAVA, FakeDefaultBranchReader({JAVA: NEWER})),
        observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED})),
        observe_one(tmp_path, NET, FakeDefaultBranchReader({NET: RuntimeError("down")})),
    ]

    document = drift_document(
        observations, observed_at="2026-10-04T00:00:00+00:00", owner="aspose-3d-foss"
    )

    assert document["schema_version"] == 1
    assert document["owner"] == "aspose-3d-foss"
    assert document["summary"] == {"CURRENT": 1, "DRIFTED": 0, "NO_BUNDLE": 1, "UNREACHABLE": 1}
    # Sorted by repository name: "." (in ".NET") sorts before "J" (in "Java").
    assert [row["repository"] for row in document["repositories"]] == [NET, JAVA, PYTHON]
    assert document["repositories"][2]["status"] == "CURRENT"
