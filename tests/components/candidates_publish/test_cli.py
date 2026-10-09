"""``repository-presenter publish-candidates`` wiring (G7-W14). No test here makes a live git or
GitHub call: every git_ops function and every GitHub-facing default_* function the command reads
off the ``cli`` module is replaced with an in-memory fake, mirroring
``tests/components/propose/test_cli.py``'s own discipline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_UNSAFE, main
from repository_presenter.components.candidates_publish.effect import AUTHORIZATION_VARIABLE
from repository_presenter.core.github.client import PullRequestRef
from repository_presenter.core.github.token_provenance import TokenDecision
from support import write_bundle, write_cursor

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
CONTROL_REPOSITORY = "babar-raza/repository-presenter"
BRANCH = "repository-presenter/candidates-update/aspose-cells-foss__Aspose.Cells-FOSS-for-Go"
TOKEN = "fake-actions-job-token"
REVISION = "b" * 40


@pytest.fixture(autouse=True)
def _no_ambient_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)
    monkeypatch.delenv("GH_CANDIDATES_WRITE_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    write_cursor(tmp_path)
    return tmp_path


def _import_dir(tmp_path: Path, revision: str, state: str = "READY_FOR_PROPOSAL") -> Path:
    # write_bundle always writes under <root>/candidates/<repository_dir>/<revision> and records
    # manifest["repository"] = repository_dir.replace("__", "/", 1) - using REPOSITORY's own
    # slug here is what makes this importable artifact verify as a bundle *for REPOSITORY*
    # (ready_revision_at's own identity check), reusing the fixture with a throwaway root rather
    # than inventing a second bundle writer.
    scratch = tmp_path / "import-scratch"
    directory = REPOSITORY.replace("/", "__", 1)
    write_bundle(scratch, directory, revision, state)
    return scratch / "candidates" / directory


class FakeGitOps:
    """An in-memory model of exactly the control-repository git operations
    ``run_publish_candidates`` wires - never a mock that merely records being called."""

    def __init__(self, *, base_current: str | None = "a" * 40) -> None:
        self.committed: dict[str, str | None] = {"main": base_current}
        self.checked_out: str | None = None
        self.overlay_calls = 0
        self.pending: str | None = None
        self.pushed: list[str] = []

    def remote_branch_sha(self, root: Path, branch: str, *, token: str | None) -> str | None:
        return f"sha-{branch}" if branch in self.committed else None

    def checkout_branch(
        self, root: Path, branch: str, start_point: str, *, token: str | None
    ) -> None:
        if branch not in self.committed:
            self.committed[branch] = self.committed.get(start_point)
        self.checked_out = branch

    def read_committed_file(self, root: Path, path: str) -> str | None:
        assert self.checked_out is not None
        return self.committed[self.checked_out]

    def overlay_bundle(self, root: Path, slug: str, import_dir: Path) -> None:
        self.overlay_calls += 1

    def stage_and_commit(self, root: Path, paths: tuple[str, ...], message: str) -> str | None:
        assert self.checked_out is not None
        if self.committed[self.checked_out] == self.pending:
            return None
        self.committed[self.checked_out] = self.pending
        return "new-commit-sha"

    def push_branch(self, root: Path, branch: str, *, token: str | None) -> None:
        self.pushed.append(branch)


def _wire_git_ops(monkeypatch: pytest.MonkeyPatch, fake: FakeGitOps) -> None:
    monkeypatch.setattr(cli.candidates_git_ops, "remote_branch_sha", fake.remote_branch_sha)
    monkeypatch.setattr(cli.candidates_git_ops, "checkout_branch", fake.checkout_branch)
    monkeypatch.setattr(cli.candidates_git_ops, "read_committed_file", fake.read_committed_file)
    monkeypatch.setattr(cli.candidates_git_ops, "overlay_bundle", fake.overlay_bundle)
    monkeypatch.setattr(cli.candidates_git_ops, "stage_and_commit", fake.stage_and_commit)
    monkeypatch.setattr(cli.candidates_git_ops, "push_branch", fake.push_branch)


def _refuse_if_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("no git or GitHub call is expected here")

    for name in (
        "remote_branch_sha",
        "checkout_branch",
        "read_committed_file",
        "overlay_bundle",
        "stage_and_commit",
        "push_branch",
    ):
        monkeypatch.setattr(cli.candidates_git_ops, name, fail)
    monkeypatch.setattr(cli, "default_find_pull_requests", fail)
    monkeypatch.setattr(cli, "default_create_pull_request", fail)
    monkeypatch.setattr(cli, "default_update_pull_request", fail)


def test_dry_run_reports_the_plan_and_makes_no_call(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _refuse_if_called(monkeypatch)
    import_dir = _import_dir(tmp_path, REVISION)
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
        ]
    )
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert REVISION in out
    assert "dry run" in out


def test_a_bundle_that_is_not_ready_for_proposal_is_refused(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refuse_if_called(monkeypatch)
    import_dir = _import_dir(tmp_path, REVISION, state="ACCEPTED")
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
        ]
    )
    assert code == EXIT_INCONSISTENT


def test_publish_without_the_owner_switch_refuses_with_no_call(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refuse_if_called(monkeypatch)
    monkeypatch.setenv("GH_CANDIDATES_WRITE_TOKEN", TOKEN)
    import_dir = _import_dir(tmp_path, REVISION)
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
            "--publish",
        ]
    )
    assert code == EXIT_UNSAFE


def test_publish_without_a_write_token_refuses(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refuse_if_called(monkeypatch)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    import_dir = _import_dir(tmp_path, REVISION)
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
            "--publish",
        ]
    )
    assert code == EXIT_UNSAFE


def test_a_fully_authorized_publish_creates_a_branch_and_a_pull_request(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = FakeGitOps()
    fake.pending = REVISION
    _wire_git_ops(monkeypatch, fake)

    created: dict[str, PullRequestRef] = {}

    def fake_find(
        owner: str, name: str, *, head_branch: str, token: str
    ) -> tuple[PullRequestRef, ...]:
        found = created.get(head_branch)
        return (found,) if found else ()

    def fake_create(
        owner: str, name: str, *, title: str, body: str, head: str, base: str, token: str
    ) -> PullRequestRef:
        pr = PullRequestRef(number=42, url="https://github.com/x/y/pull/42", title=title, body=body)
        created[head] = pr
        return pr

    def fake_update(*args: object, **kwargs: object) -> PullRequestRef:
        raise AssertionError("no pull request exists yet - update should never be called")

    def fake_verify_token(repository: str, token: str) -> TokenDecision:
        assert repository == CONTROL_REPOSITORY
        assert token == TOKEN
        return TokenDecision(True)

    monkeypatch.setattr(cli, "default_find_pull_requests", fake_find)
    monkeypatch.setattr(cli, "default_create_pull_request", fake_create)
    monkeypatch.setattr(cli, "default_update_pull_request", fake_update)
    monkeypatch.setattr(cli, "default_verify_installation_token", fake_verify_token)
    monkeypatch.setattr(cli, "default_verify_pull_request_app", lambda *a, **k: TokenDecision(True))
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_CANDIDATES_WRITE_TOKEN", TOKEN)

    import_dir = _import_dir(tmp_path, REVISION)
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
            "--publish",
        ]
    )
    assert code == EXIT_OK
    assert fake.pushed == [BRANCH]
    assert fake.overlay_calls == 1
    assert created[BRANCH].number == 42
    out = capsys.readouterr().out
    assert "effected=True" in out
    assert "pull/42" in out


def test_an_already_current_candidate_is_published_as_a_no_op(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control repository's own candidates/<slug> already names this exact revision - a
    re-run (e.g. a cron tick after a prior success) must not commit, push, or open anything."""
    fake = FakeGitOps(base_current=REVISION)
    fake.pending = REVISION
    _wire_git_ops(monkeypatch, fake)

    def fail_create(*args: object, **kwargs: object) -> PullRequestRef:
        raise AssertionError("already current - no pull request should be created")

    monkeypatch.setattr(cli, "default_find_pull_requests", lambda *a, **k: ())
    monkeypatch.setattr(cli, "default_create_pull_request", fail_create)
    monkeypatch.setattr(
        cli, "default_verify_installation_token", lambda repository, token: TokenDecision(True)
    )
    monkeypatch.setattr(cli, "default_verify_pull_request_app", lambda *a, **k: TokenDecision(True))
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_CANDIDATES_WRITE_TOKEN", TOKEN)

    import_dir = _import_dir(tmp_path, REVISION)
    code = main(
        [
            "publish-candidates",
            "--repo",
            REPOSITORY,
            "--root",
            str(project),
            "--import-dir",
            str(import_dir),
            "--control-repo",
            CONTROL_REPOSITORY,
            "--base-branch",
            "main",
            "--publish",
        ]
    )
    assert code == EXIT_OK
    assert fake.pushed == []
    assert fake.overlay_calls == 0
