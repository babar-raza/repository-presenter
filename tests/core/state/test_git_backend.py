"""The real git-ref CAS backend (docs/STATE_MACHINE.md sections 13.2, 14) against a disposable
local "remote" repository - no network, but real git subprocesses and a real non-fast-forward
push race, not a mock.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.core.errors import StateBackendError
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.state.cas import acquire_lease, save_state_patch
from repository_presenter.core.state.git_backend import STATE_REF_PREFIX, GitStateBackend, _ref_key
from repository_presenter.core.state.schema import RepositoryRecord
from support import init_git_repository

REPO = "aspose-3d-foss/example"
PROVIDER_ID = 42


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    """A disposable local repository standing in for this project's own state remote."""
    return init_git_repository(tmp_path / "remote")


def test_load_returns_none_for_an_unknown_repository(remote: Path) -> None:
    with GitStateBackend(remote=str(remote)) as backend:
        assert backend.load(REPO) is None


def test_save_then_load_round_trips_through_a_real_git_ref(remote: Path) -> None:
    with GitStateBackend(remote=str(remote)) as backend:
        record = RepositoryRecord(
            repository=REPO, provider_repository_id=PROVIDER_ID, state="SNAPSHOTTING"
        )
        result = backend.save(REPO, record, expected_version=None)
        assert result.outcome == "saved"
        assert result.record is not None
        assert result.record.state_version == 1

        loaded = backend.load(REPO)
        assert loaded is not None
        assert loaded.state == "SNAPSHOTTING"
        assert loaded.state_version == 1


def test_save_rejects_a_stale_expected_version(remote: Path) -> None:
    with GitStateBackend(remote=str(remote)) as backend:
        first = RepositoryRecord(repository=REPO, provider_repository_id=PROVIDER_ID)
        backend.save(REPO, first, expected_version=None)

        stale_attempt = RepositoryRecord(
            repository=REPO, provider_repository_id=PROVIDER_ID, state="EXTRACTING"
        )
        result = backend.save(REPO, stale_attempt, expected_version=0)
        assert result.outcome == "stale"
        assert result.record is not None
        assert result.record.state_version == 1
        assert result.record.state == "OBSERVED"  # the stale write never actually landed


def test_two_independent_backends_racing_the_same_remote_cas_conflict(remote: Path) -> None:
    """The real non-fast-forward push rejection, not a mocked one: two separate
    ``GitStateBackend`` instances (as two concurrent worker processes would be) against the same
    remote, where only one writer's CAS can win."""
    with (
        GitStateBackend(remote=str(remote)) as worker_a,
        GitStateBackend(remote=str(remote)) as worker_b,
    ):
        # Both workers observe "no prior state" and race to create the first record.
        a_result = worker_a.save(
            REPO,
            RepositoryRecord(
                repository=REPO, provider_repository_id=PROVIDER_ID, state="SNAPSHOTTING"
            ),
            expected_version=None,
        )
        b_result = worker_b.save(
            REPO,
            RepositoryRecord(
                repository=REPO, provider_repository_id=PROVIDER_ID, state="SNAPSHOTTING"
            ),
            expected_version=None,
        )
        outcomes = {a_result.outcome, b_result.outcome}
        assert outcomes == {"saved", "stale"}  # exactly one writer wins; the other is told so

        # Negative control: duplicate effects never apply twice - the loser retries against the
        # winner's now-current version rather than silently overwriting it.
        loser, winner_version = (
            (worker_a, b_result.record)
            if a_result.outcome == "stale"
            else (worker_b, a_result.record)
        )
        assert winner_version is not None
        retried = loser.save(
            REPO,
            RepositoryRecord(
                repository=REPO, provider_repository_id=PROVIDER_ID, state="EXTRACTING"
            ).model_copy(update={"state_version": winner_version.state_version}),
            expected_version=winner_version.state_version,
        )
        assert retried.outcome == "saved"
        assert retried.record is not None
        assert retried.record.state_version == winner_version.state_version + 1


def test_load_fails_closed_on_corrupt_stored_state(remote: Path, tmp_path: Path) -> None:
    """Negative control: a malformed/corrupt durable-state blob must never be silently accepted
    as empty or default state - it is a fail-closed error."""
    scratch = init_git_repository(tmp_path / "scratch")
    bad = scratch / "record.json"
    bad.write_text("{not valid json", encoding="utf-8")
    add = run_git(["add", "record.json"], cwd=scratch)
    assert add.returncode == 0
    commit = run_git(["commit", "-q", "-m", "corrupt"], cwd=scratch)
    assert commit.returncode == 0
    head = run_git(["rev-parse", "HEAD"], cwd=scratch)
    assert head.returncode == 0
    remote_ref = f"{STATE_REF_PREFIX}/{_ref_key(REPO)}"
    push = run_git(["push", str(remote), f"{head.stdout.strip()}:{remote_ref}"], cwd=scratch)
    assert push.returncode == 0

    with GitStateBackend(remote=str(remote)) as backend, pytest.raises(StateBackendError):
        backend.load(REPO)


def test_lease_and_transition_helpers_compose_with_the_real_backend(remote: Path) -> None:
    """The backend-agnostic cas.py helpers (acquire_lease, save_state_patch) work unchanged
    against the real git-ref backend, not only the in-memory test double."""
    with GitStateBackend(remote=str(remote)) as backend:
        lease = acquire_lease(
            backend, REPO, holder_id="worker-a", provider_repository_id=PROVIDER_ID
        )
        assert lease is not None

        save_state_patch(
            backend,
            REPO,
            lambda r: r.model_copy(
                update={"active_transaction_id": "tx-1", "state": "SNAPSHOTTING"}
            ),
            provider_repository_id=PROVIDER_ID,
        )
        loaded = backend.load(REPO)
        assert loaded is not None
        assert loaded.lease is not None
        assert loaded.lease.holder_id == "worker-a"
        assert loaded.active_transaction_id == "tx-1"
