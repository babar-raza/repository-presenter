"""The drift monitor's content check: a bundle's recorded upstream blob ids, compared with the same
files at the repository's head.

``head unchanged`` is the case this check exists for: the revision is the one the bundle was sealed
from, so only a recorded dependency's blob id can say it changed. Every GitHub read is injected
through a fake, so no test here reaches the network.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.monitor.drift import (
    RepositoryDrift,
    drift_document,
    observe_drift,
)
from repository_presenter.core.github.read_client import TreeRead
from repository_presenter.core.registry.models import Registry, RegistryEntry
from support import FakeDefaultBranchReader, monitor_registry_entry, write_bundle

TOKEN = "ghs_fixture_read_token_value_0123456789"
BUNDLED = "1111111111111111111111111111111111111111"
NEWER = "2222222222222222222222222222222222222222"
PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PYTHON_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
LICENSE = "LICENSE"
MANIFEST = "pyproject.toml"
EXAMPLE = "examples/demo.py"
UNRELATED = "docs/notes.md"
RECORDED = {
    LICENSE: "aa" * 20,
    MANIFEST: "bb" * 20,
    EXAMPLE: "cc" * 20,
}


class FakeTreeReader:
    """Injected stand-in for ``core/github/read_client.py::fetch_tree``.

    ``outcome`` is the blob-id map a successful read returns, a ready ``TreeRead``, or an exception
    to raise. Every call is recorded with its revision and token.
    """

    def __init__(self, outcome: Mapping[str, str] | TreeRead | Exception) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, str]] = []
        self.tokens: list[str | None] = []

    def __call__(self, repository: str, revision: str, *, token: str | None = None) -> TreeRead:
        self.calls.append((repository, revision))
        self.tokens.append(token)
        outcome = self.outcome
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, TreeRead):
            return outcome
        return TreeRead(repository, revision, paths=tuple(sorted(outcome)), blob_shas=dict(outcome))


def entry_of(repository: str) -> RegistryEntry:
    return Registry.model_validate(
        {"schema_version": 1, "entries": [monitor_registry_entry(repository)]}
    ).entries[0]


def observe_one(
    root: Path,
    head: str,
    tree: FakeTreeReader,
) -> RepositoryDrift:
    reader = FakeDefaultBranchReader({PYTHON: head})
    (observation,) = observe_drift(
        root, [entry_of(PYTHON)], token=TOKEN, read_head=reader, read_tree=tree
    )
    return observation


def test_unchanged_head_with_a_changed_dependency_blob_is_drifted(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    tree = FakeTreeReader({**RECORDED, LICENSE: "dd" * 20})

    observation = observe_one(tmp_path, BUNDLED, tree)

    assert observation.status == "DRIFTED"
    assert observation.head_revision == BUNDLED
    assert observation.bundle_revision == BUNDLED
    assert observation.detail is not None
    assert LICENSE in observation.detail
    assert MANIFEST not in observation.detail
    # The tree was read at the head the bundle is sealed from, with the run's read-only token.
    assert tree.calls == [(PYTHON, BUNDLED)]
    assert tree.tokens == [TOKEN]


def test_unchanged_head_and_every_recorded_hash_unchanged_is_current(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    tree = FakeTreeReader(dict(RECORDED))

    observation = observe_one(tmp_path, BUNDLED, tree)

    assert observation.status == "CURRENT"
    assert observation.detail is None
    assert tree.calls == [(PYTHON, BUNDLED)]


def test_a_changed_file_the_candidate_does_not_depend_on_never_drifts(tmp_path: Path) -> None:
    # Negative control: UNRELATED changed (it is not among the recorded dependencies) and a new
    # file appeared; every recorded dependency still matches, so the repository stays CURRENT.
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    tree = FakeTreeReader({**RECORDED, UNRELATED: "ee" * 20, "src/new.py": "ff" * 20})

    observation = observe_one(tmp_path, BUNDLED, tree)

    assert observation.status == "CURRENT"
    assert observation.detail is None


def test_a_moved_head_is_drifted_without_reading_the_tree(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    tree = FakeTreeReader(dict(RECORDED))

    observation = observe_one(tmp_path, NEWER, tree)

    assert observation.status == "DRIFTED"
    assert observation.detail is None
    assert tree.calls == []


def test_a_bundle_sealed_without_recorded_hashes_is_unknown_until_resealed(
    tmp_path: Path,
) -> None:
    # A bundle sealed before upstream blob ids were recorded has no such field. Sealed bundles are
    # not rewritten, so it reads UNKNOWN - neither CURRENT nor DRIFTED - until a re-seal records
    # them. Its tree is never read: there is nothing to compare against.
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    tree = FakeTreeReader(dict(RECORDED))

    observation = observe_one(tmp_path, BUNDLED, tree)

    assert observation.status == "UNKNOWN"
    assert observation.head_revision == BUNDLED
    assert observation.bundle_revision == BUNDLED
    assert observation.detail is not None and "re-seal" in observation.detail
    assert tree.calls == []


def test_an_empty_record_of_hashes_is_unknown_too(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs={})
    tree = FakeTreeReader(dict(RECORDED))

    observation = observe_one(tmp_path, BUNDLED, tree)

    assert observation.status == "UNKNOWN"
    assert tree.calls == []


@pytest.mark.parametrize(
    "outcome",
    [
        TreeRead(PYTHON, BUNDLED, error="HTTP 503"),
        TreeRead(PYTHON, BUNDLED, paths=tuple(sorted(RECORDED)), truncated=True),
        ConnectionError("connection reset"),
    ],
    ids=["tree-error", "tree-truncated", "tree-raises"],
)
def test_an_unreadable_upstream_tree_is_unknown_not_current(
    tmp_path: Path, outcome: TreeRead | Exception
) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)

    observation = observe_one(tmp_path, BUNDLED, FakeTreeReader(outcome))

    assert observation.status == "UNKNOWN"
    assert observation.head_revision == BUNDLED
    assert observation.detail is not None
    assert TOKEN not in observation.detail


def test_a_failing_tree_read_never_stops_the_other_repositories(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    java = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
    java_dir = "aspose-3d-foss__Aspose.3D-FOSS-for-Java"
    write_bundle(tmp_path, java_dir, BUNDLED, "READY_FOR_PROPOSAL", upstream_blobs=RECORDED)
    reader = FakeDefaultBranchReader({PYTHON: BUNDLED, java: BUNDLED})
    registry = [entry_of(java), entry_of(PYTHON)]

    def tree_for(repository: str, revision: str, *, token: str | None = None) -> TreeRead:
        if repository == java:
            raise ConnectionError("connection reset")
        return TreeRead(repository, revision, blob_shas=dict(RECORDED))

    observations = observe_drift(
        tmp_path, registry, token=TOKEN, read_head=reader, read_tree=tree_for
    )

    assert [(o.repository, o.status) for o in observations] == [
        (java, "UNKNOWN"),
        (PYTHON, "CURRENT"),
    ]


def test_the_summary_counts_unknown_as_its_own_status(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    observation = observe_one(tmp_path, BUNDLED, FakeTreeReader(dict(RECORDED)))

    document: dict[str, Any] = drift_document(
        [observation], observed_at="2026-10-06T00:00:00+00:00", owner=None
    )

    assert document["summary"] == {
        "CURRENT": 0,
        "DRIFTED": 0,
        "UNKNOWN": 1,
        "NO_BUNDLE": 0,
        "UNREACHABLE": 0,
    }
