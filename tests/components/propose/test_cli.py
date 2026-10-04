"""``repository-presenter propose`` wiring. A proposal carries one thing - a registry-``full``
repository's sealed, ``READY_FOR_PROPOSAL`` CURRENT candidate - and even then writes nothing
without a committed authorization record, the owner switch, and an installation token scoped to the
target. No test here makes a live GitHub call: every GitHub-facing function is replaced on the
``cli`` module by an in-memory remote, and the authorization record's provenance is checked against
a real disposable git repository (the property is about git history).

Each ``test_*_refused`` pair below is a negative control for one requirement: the same fixture
succeeds in ``test_propose_authorized_with_token_creates_branch_and_pr`` and fails, with its typed
reason and no remote write, when exactly one precondition is removed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, EXIT_USAGE, main
from repository_presenter.components.propose.effect import AUTHORIZATION_VARIABLE
from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    authorize_proposal,
    render_record,
)
from repository_presenter.core.github.client import (
    CommitOutcome,
    FileContents,
    PullRequestRef,
)
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.github.token_provenance import (
    TokenDecision,
    verify_installation_token,
)
from repository_presenter.core.hashing import sha256_text
from support import (
    REPO_ROOT,
    head_revision,
    merge_to_origin_main,
    monitor_registry_entry,
    write_proposable_bundle,
    write_registry_file,
)

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
DRY_RUN_REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
README_TEXT = "# Cells\n\nProposed content.\n"
BRANCH = "repository-presenter/readme-update"
TOKEN = "ghs_fake-installation-token-for-this-test-only"

#: A real, currently-sealed Cells-family candidate (G6-W03's "best real candidate to propose"):
#: used to prove the mechanism against real ~27KB content, not only a 28-byte fixture.
_REAL_CANDIDATE_REPOSITORY_DIR = "aspose-cells-foss__Aspose.Cells-FOSS-for-Java"
_REAL_CANDIDATE_REVISION = "c65329e7257b1311abb9686d7e4957a8cc002955"


def _now() -> datetime:
    return datetime.now(UTC)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def _no_ambient_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hosted CI sets GITHUB_SHA; these tests choose the trigger commit themselves."""
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)
    monkeypatch.delenv("GH_PROPOSAL_WRITE_TOKEN", raising=False)


@pytest.fixture
def control(project: Path) -> Path:
    """A control checkout: a registry with one ``full`` and one ``dry_run`` entry, and a sealed
    READY_FOR_PROPOSAL bundle for the ``full`` one."""
    write_registry_file(
        project,
        [
            monitor_registry_entry(REPOSITORY, mode="full", repository_id=1),
            monitor_registry_entry(DRY_RUN_REPOSITORY, mode="dry_run", repository_id=2),
        ],
    )
    write_proposable_bundle(project, REPOSITORY, REVISION, README_TEXT)
    return project


def commit_record(root: Path, readme_text: str = README_TEXT, **overrides: Any) -> tuple[Path, str]:
    """Write an authorization record, merge it to origin/main, return ``(path, its commit)``."""
    fields: dict[str, Any] = {
        "repository": REPOSITORY,
        "candidate_hash": sha256_text(readme_text),
        "source_revision": REVISION,
        "base_branch": "main",
        "branch": BRANCH,
        "approver": "a-person",
        "issued_at": _stamp(_now() - timedelta(minutes=5)),
        "expires_at": _stamp(_now() + timedelta(hours=1)),
    }
    fields.update(overrides)
    path = root / AUTHORIZATION_DIRNAME / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_record(authorize_proposal(**fields)), encoding="utf-8")
    return path, merge_to_origin_main(root, "approve the candidate")


class Remote:
    """An in-memory GitHub: refs, one file per branch, one open PR and any number of settled PRs."""

    def __init__(self, *, live_revision: str = REVISION, readme: str | None = None) -> None:
        self.live_revision = live_revision
        self.refs: dict[str, str] = {"main": "base-sha-1"}
        self.files: dict[tuple[str, str], FileContents] = {}
        self.open_pr: PullRequestRef | None = None
        self.settled: list[PullRequestRef] = []
        self.calls: list[str] = []
        self.put_calls: list[dict[str, Any]] = []
        self.create_pr_calls: list[dict[str, Any]] = []
        self.update_pr_calls: list[dict[str, Any]] = []
        self.token_checks: list[tuple[str, str]] = []
        self.verify_token: Callable[[str, str], TokenDecision] = self._ok_token
        if readme is not None:
            self.refs[BRANCH] = "base-sha-1"
            self.files[(BRANCH, "README.md")] = FileContents("README.md", "sha-1", readme)

    @property
    def wrote(self) -> bool:
        return bool(
            self.put_calls
            or self.create_pr_calls
            or self.update_pr_calls
            or "create_ref" in self.calls
        )

    def _ok_token(self, repository: str, token: str) -> TokenDecision:
        return TokenDecision(True)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def verify(repository: str, token: str) -> TokenDecision:
            self.token_checks.append((repository, token))
            return self.verify_token(repository, token)

        monkeypatch.setattr(
            cli,
            "fetch_default_branch_sha",
            lambda repo, *, token=None: DefaultBranchRead(
                repo, sha=self.live_revision, branch="main"
            ),
        )
        monkeypatch.setattr(cli, "default_verify_installation_token", verify)
        monkeypatch.setattr(
            cli,
            "default_verify_pull_request_app",
            lambda *a, **k: TokenDecision(True),
        )
        monkeypatch.setattr(cli, "default_get_ref", self.get_ref)
        monkeypatch.setattr(cli, "default_create_ref", self.create_ref)
        monkeypatch.setattr(cli, "default_get_contents", self.get_contents)
        monkeypatch.setattr(cli, "default_put_contents", self.put_contents)
        monkeypatch.setattr(cli, "default_find_pull_requests", self.find_pull_requests)
        monkeypatch.setattr(cli, "default_create_pull_request", self.create_pull_request)
        monkeypatch.setattr(cli, "default_update_pull_request", self.update_pull_request)

    def get_ref(self, owner: str, name: str, branch: str, *, token: str) -> str | None:
        self.calls.append("get_ref")
        return self.refs.get(branch)

    def create_ref(self, owner: str, name: str, branch: str, sha: str, *, token: str) -> None:
        self.calls.append("create_ref")
        self.refs[branch] = sha

    def get_contents(
        self, owner: str, name: str, path: str, *, ref: str, token: str
    ) -> FileContents | None:
        return self.files.get((ref, path))

    def put_contents(
        self,
        owner: str,
        name: str,
        path: str,
        *,
        branch: str,
        message: str,
        text: str,
        sha: str | None,
        token: str,
    ) -> CommitOutcome:
        self.put_calls.append({"branch": branch, "text": text, "sha": sha, "message": message})
        self.files[(branch, path)] = FileContents(path, "sha-after", text)
        return CommitOutcome(content_sha="sha-after", commit_sha="commit-1")

    def find_pull_requests(
        self, owner: str, name: str, *, head_branch: str, token: str
    ) -> tuple[PullRequestRef, ...]:
        return (*([self.open_pr] if self.open_pr else []), *self.settled)

    def create_pull_request(
        self, owner: str, name: str, *, title: str, body: str, head: str, base: str, token: str
    ) -> PullRequestRef:
        self.create_pr_calls.append({"title": title, "body": body, "head": head, "base": base})
        self.open_pr = PullRequestRef(
            number=1, url=f"https://github.com/{owner}/{name}/pull/1", title=title, body=body
        )
        return self.open_pr

    def update_pull_request(
        self, owner: str, name: str, number: int, *, title: str, body: str, token: str
    ) -> PullRequestRef:
        self.update_pr_calls.append({"number": number, "title": title, "body": body})
        assert self.open_pr is not None
        self.open_pr = PullRequestRef(number, self.open_pr.url, title, body)
        return self.open_pr


def _propose_args(
    root: Path, record: Path | None, trigger: str | None, *extra: str, repo: str = REPOSITORY
) -> list[str]:
    args = ["propose", "--repo", repo, "--root", str(root)]
    if record is not None:
        args += ["--authorization-record", str(record)]
    if trigger is not None:
        args += ["--trigger-sha", trigger]
    return [*args, *extra]


def _arm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", TOKEN)


def _run_refused(capsys: pytest.CaptureFixture[str], args: list[str], code: str) -> str:
    exit_code = main(args)
    captured = capsys.readouterr()
    assert exit_code == EXIT_UNSAFE, captured
    assert code in captured.out + captured.err
    return captured.out + captured.err


# ---------------------------------------------------------------------------
# the authorized path
# ---------------------------------------------------------------------------


def test_propose_authorized_with_token_creates_branch_and_pr(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)

    exit_code = main(_propose_args(control, record, trigger, "--propose"))

    out = capsys.readouterr().out
    assert exit_code == EXIT_OK, out
    assert "effected=True" in out
    assert "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java/pull/1" in out
    assert "approved by a-person" in out  # the record and its provenance are in the audit trail
    assert remote.token_checks == [(REPOSITORY, TOKEN)]
    assert remote.refs[BRANCH] == "base-sha-1"
    assert [call["text"] for call in remote.put_calls] == [README_TEXT]
    assert len(remote.create_pr_calls) == 1
    assert f"candidate_hash: {sha256_text(README_TEXT)}" in remote.create_pr_calls[0]["body"]


def test_the_base_branch_defaults_to_the_targets_live_default_branch(
    control: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    assert main(_propose_args(control, record, trigger, "--propose")) == EXIT_OK
    assert remote.create_pr_calls[0]["base"] == "main"


def test_a_trigger_commit_defaults_to_github_sha_then_head(
    control: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    monkeypatch.setenv("GITHUB_SHA", trigger)
    assert main(_propose_args(control, record, None, "--propose")) == EXIT_OK
    monkeypatch.delenv("GITHUB_SHA")
    remote.open_pr = None
    assert main(_propose_args(control, record, None, "--propose")) == EXIT_OK  # HEAD


# ---------------------------------------------------------------------------
# (a) the registry mode is enforced in code
# ---------------------------------------------------------------------------


def test_a_dry_run_registry_entry_gets_a_dry_run_result_and_never_a_write(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_proposable_bundle(control, DRY_RUN_REPOSITORY, REVISION, README_TEXT)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    record, trigger = commit_record(control, repository=DRY_RUN_REPOSITORY)

    # dry run: allowed, and says what mode makes it
    assert main(_propose_args(control, None, None, repo=DRY_RUN_REPOSITORY)) == EXIT_OK
    assert "dry-run result is all this can be" in capsys.readouterr().out

    # --propose: refused before the bundle, the record, the token, or any GitHub call
    out = _run_refused(
        capsys,
        _propose_args(control, record, trigger, "--propose", repo=DRY_RUN_REPOSITORY),
        "registry_dry_run",
    )
    assert "dry_run" in out
    assert remote.calls == [] and not remote.wrote and remote.token_checks == []


def test_a_disabled_or_unlisted_repository_cannot_be_proposed(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    # unlisted is refused by the read gate (exit 3) before anything else
    assert main(_propose_args(control, None, None, "--propose", repo="some-org/not-listed")) == 3
    assert "not in the registry allow-list" in capsys.readouterr().err
    assert not remote.wrote


# ---------------------------------------------------------------------------
# (b) the bundle must be final and current; local-test content can never write
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("extra", [[], ["--propose"]])
def test_a_valid_update_available_bundle_is_refused(
    control: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    extra: list[str],
) -> None:
    """The Slides-Java shape: CURRENT names a sealed, intact bundle that is no longer final."""
    write_proposable_bundle(
        control, REPOSITORY, REVISION, README_TEXT, state="VALID_UPDATE_AVAILABLE"
    )
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)

    out = _run_refused(capsys, _propose_args(control, record, trigger, *extra), "bundle_not_ready")
    assert "VALID_UPDATE_AVAILABLE" in out
    assert not remote.wrote


def test_a_repository_with_no_current_candidate_is_refused(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (control / "candidates" / "aspose-cells-foss__Aspose.Cells-FOSS-for-Java" / "CURRENT").unlink()
    remote = Remote()
    remote.install(monkeypatch)
    _run_refused(capsys, _propose_args(control, None, None), "bundle_missing")


def test_a_bundle_behind_the_targets_current_revision_is_refused_in_dry_run(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = Remote(live_revision="0" * 40)
    remote.install(monkeypatch)
    _run_refused(capsys, _propose_args(control, None, None), "source_moved")


def test_a_bundle_behind_the_targets_current_revision_is_refused_before_the_write(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote(live_revision="0" * 40)
    remote.install(monkeypatch)
    _arm(monkeypatch)

    out = _run_refused(capsys, _propose_args(control, record, trigger, "--propose"), "source_moved")
    assert "stale source" in out
    assert not remote.wrote


def test_the_dry_run_reports_freshness_and_the_record_match(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)

    assert main(_propose_args(control, record, trigger)) == EXIT_OK

    out = capsys.readouterr().out
    assert "bundle revision equals the target's current revision" in out
    assert "the authorization record matches this candidate" in out
    assert "dry run" in out
    assert not remote.wrote


def test_local_test_mode_makes_a_dry_run_plan_and_no_github_call(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("local test mode must make no GitHub call")

    for name in ("fetch_default_branch_sha", "default_get_ref", "default_put_contents"):
        monkeypatch.setattr(cli, name, fail)
    content = tmp_path / "candidate-readme.md"
    content.write_text(README_TEXT, encoding="utf-8")

    exit_code = main(
        [
            "propose",
            "--repo",
            "babar-raza/disposable-target",
            "--root",
            str(project),
            "--local-test-readme-file",
            str(content),
            "--source-revision",
            REVISION,
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == EXIT_OK
    assert "LOCAL TEST ONLY" in out
    assert f"candidate_hash={sha256_text(README_TEXT)}" in out
    assert f"source_revision={REVISION}" in out
    assert "never writes" in out


def test_local_test_mode_cannot_reach_a_write_even_fully_armed(
    control: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    content = tmp_path / "candidate-readme.md"
    content.write_text(README_TEXT, encoding="utf-8")

    for repo in (REPOSITORY, "babar-raza/disposable-target"):
        _run_refused(
            capsys,
            [
                *_propose_args(control, record, trigger, repo=repo),
                "--local-test-readme-file",
                str(content),
                "--source-revision",
                REVISION,
                "--propose",
            ],
            "local_test_cannot_write",
        )
    assert remote.calls == [] and not remote.wrote and remote.token_checks == []


def test_local_test_mode_requires_a_source_revision(
    project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = tmp_path / "candidate-readme.md"
    content.write_text(README_TEXT, encoding="utf-8")
    exit_code = main(
        [
            "propose",
            "--repo",
            "x/y",
            "--root",
            str(project),
            "--local-test-readme-file",
            str(content),
        ]
    )
    assert exit_code == EXIT_USAGE


def test_the_old_readme_file_flag_no_longer_exists(project: Path) -> None:
    with pytest.raises(SystemExit) as info:
        main(["propose", "--repo", "x/y", "--root", str(project), "--readme-file", "r.md"])
    assert info.value.code == 2


# ---------------------------------------------------------------------------
# (c) the authorization record is independent of the proposal
# ---------------------------------------------------------------------------


def test_a_missing_authorization_record_refuses_with_no_write(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    _run_refused(capsys, _propose_args(control, None, None, "--propose"), "authorization_missing")
    assert not remote.wrote and remote.token_checks == []

    absent = control / AUTHORIZATION_DIRNAME / "absent.json"
    _run_refused(capsys, _propose_args(control, absent, None, "--propose"), "authorization_missing")
    assert not remote.wrote


def test_an_expired_authorization_record_refuses_with_no_write(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(
        control,
        issued_at=_stamp(_now() - timedelta(hours=3)),
        expires_at=_stamp(_now() - timedelta(hours=1)),
    )
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "authorization_expired"
    )
    assert not remote.wrote and remote.token_checks == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"candidate_hash": "0" * 64},  # approves different README bytes
        {"source_revision": "a" * 40},  # approves a different upstream revision
        {"repository": "aspose-words-foss/Aspose.Words-FOSS-for-Java"},
        {"base_branch": "develop"},
        {"branch": "some-other-branch"},
    ],
)
def test_a_mismatched_authorization_record_refuses_with_no_write(
    control: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    overrides: dict[str, str],
) -> None:
    record, trigger = commit_record(control, **overrides)
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "authorization_mismatch"
    )
    assert not remote.wrote and remote.token_checks == []


def test_a_record_for_other_readme_bytes_does_not_authorize_this_candidate(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The bundle moved on after the record was approved: the record names the old bytes."""
    record, trigger = commit_record(control, readme_text="# an earlier candidate\n")
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "authorization_mismatch"
    )
    assert not remote.wrote


def test_a_record_not_merged_to_origin_main_is_refused(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Written, even committed locally, but never merged: the dispatcher's own say-so."""
    merge_to_origin_main(control, "main without any record")
    trigger = head_revision(control)
    path = control / AUTHORIZATION_DIRNAME / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_record(
            authorize_proposal(
                repository=REPOSITORY,
                candidate_hash=sha256_text(README_TEXT),
                source_revision=REVISION,
                base_branch="main",
                branch=BRANCH,
                approver="the-dispatcher",
                issued_at=_stamp(_now() - timedelta(minutes=5)),
                expires_at=_stamp(_now() + timedelta(hours=1)),
            )
        ),
        encoding="utf-8",
    )
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)

    _run_refused(
        capsys, _propose_args(control, path, trigger, "--propose"), "authorization_not_committed"
    )
    assert not remote.wrote and remote.token_checks == []


def test_a_record_pushed_after_the_trigger_commit_is_refused(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The run's own commit: merged to main, but after the commit the run was triggered at."""
    trigger = merge_to_origin_main(control, "the commit the run is dispatched at")
    record, _ = commit_record(control)  # created and pushed by the run
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)

    out = _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "authorization_not_committed"
    )
    assert "cannot authorize itself" in out
    assert not remote.wrote


def test_a_malformed_authorization_record_is_refused(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    record.write_text('{"repository": "x"}', encoding="utf-8")
    trigger = merge_to_origin_main(control, "garbage record")
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "authorization_unreadable"
    )
    assert not remote.wrote


def test_without_the_owner_switch_nothing_is_written_and_no_github_call_is_made(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", TOKEN)  # a token without the owner switch

    out = _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "write_not_enabled"
    )
    assert "not authorized" in out
    assert remote.calls == [] and remote.token_checks == [] and not remote.wrote


def test_without_a_write_token_nothing_is_written(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    _run_refused(capsys, _propose_args(control, record, trigger, "--propose"), "no_write_token")
    assert remote.token_checks == [] and not remote.wrote


# ---------------------------------------------------------------------------
# (d) the write token must be a repository-scoped installation token
# ---------------------------------------------------------------------------


def test_a_hand_set_personal_access_token_is_refused_by_the_real_check(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Nothing about the token is faked here: the real verifier refuses a ``ghp_`` token on its
    prefix, before any request leaves the process."""
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)

    def no_network(url: str, token: str | None) -> tuple[int, Any]:
        raise AssertionError("a refused token must not be sent anywhere")

    monkeypatch.setattr(
        cli,
        "default_verify_installation_token",
        partial(verify_installation_token, fetch=no_network),
    )
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", "ghp_hand_set_personal_access_token")

    out = _run_refused(
        capsys, _propose_args(control, record, trigger, "--propose"), "token_not_installation"
    )
    assert "ghp_hand_set_personal_access_token" not in out  # never echoed
    assert not remote.wrote and remote.calls == []


def test_an_installation_token_with_a_wider_scope_than_the_target_is_refused(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.install(monkeypatch)

    def two_repositories(url: str, token: str | None) -> tuple[int, Any]:
        return 200, {
            "total_count": 2,
            "repositories": [{"full_name": REPOSITORY}, {"full_name": DRY_RUN_REPOSITORY}],
        }

    monkeypatch.setattr(
        cli,
        "default_verify_installation_token",
        partial(verify_installation_token, fetch=two_repositories),
    )
    _arm(monkeypatch)
    _run_refused(capsys, _propose_args(control, record, trigger, "--propose"), "token_wrong_scope")
    assert not remote.wrote


# ---------------------------------------------------------------------------
# (e) a merged or closed presenter PR is not recreated
# ---------------------------------------------------------------------------


def _settled(state: str, *, number: int = 3, readme_text: str = README_TEXT) -> PullRequestRef:
    return PullRequestRef(
        number=number,
        url=f"https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java/pull/{number}",
        title="Update README via repository-presenter",
        body=f"- candidate_hash: {sha256_text(readme_text)}\n",
        state=state,
    )


@pytest.mark.parametrize(
    ("state", "code"), [("merged", "pr_already_merged"), ("closed", "pr_already_closed")]
)
def test_a_settled_presenter_pr_is_not_recreated(
    control: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    state: str,
    code: str,
) -> None:
    record, trigger = commit_record(control)
    remote = Remote()
    remote.settled = [_settled(state)]
    remote.install(monkeypatch)
    _arm(monkeypatch)

    out = _run_refused(capsys, _propose_args(control, record, trigger, "--propose"), code)
    assert "#3" in out
    assert not remote.wrote and BRANCH not in remote.refs


def test_a_record_that_names_the_settled_pr_permits_the_reproposal(
    control: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, trigger = commit_record(control, supersedes_prs=(3,))
    remote = Remote()
    remote.settled = [_settled("closed")]
    remote.install(monkeypatch)
    _arm(monkeypatch)

    assert main(_propose_args(control, record, trigger, "--propose")) == EXIT_OK
    assert len(remote.create_pr_calls) == 1


# ---------------------------------------------------------------------------
# idempotency, against a real sealed candidate's real bytes
# ---------------------------------------------------------------------------


def test_propose_handles_a_real_sealed_candidates_full_readme_and_is_idempotent(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """G6-W03's gap-closing proof, on the registry/bundle/record path: the identical authorized
    CLI invocation against a real ~27KB README creates the PR once, and a second run, finding the
    branch and PR already holding that content, writes and PATCHes nothing."""
    real = (
        REPO_ROOT / "candidates" / _REAL_CANDIDATE_REPOSITORY_DIR / _REAL_CANDIDATE_REVISION
    ).joinpath("README.md")
    real_text = real.read_bytes().decode("utf-8")
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode="full", repository_id=1)])
    write_proposable_bundle(project, REPOSITORY, _REAL_CANDIDATE_REVISION, real_text)
    record, trigger = commit_record(
        project, readme_text=real_text, source_revision=_REAL_CANDIDATE_REVISION
    )
    remote = Remote(live_revision=_REAL_CANDIDATE_REVISION)
    remote.install(monkeypatch)
    _arm(monkeypatch)
    args = _propose_args(project, record, trigger, "--propose")

    assert main(args) == EXIT_OK
    assert "effected=True" in capsys.readouterr().out
    assert [call["text"] for call in remote.put_calls] == [real_text]
    assert len(remote.create_pr_calls) == 1

    assert main(args) == EXIT_OK
    out = capsys.readouterr().out
    assert "no change needed" in out
    assert len(remote.put_calls) == 1
    assert len(remote.create_pr_calls) == 1
    assert remote.update_pr_calls == []


# ---------------------------------------------------------------------------
# drafting the record
# ---------------------------------------------------------------------------


def test_drafting_writes_a_record_that_is_inert_until_merged(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = Remote()
    remote.install(monkeypatch)
    _arm(monkeypatch)
    merge_to_origin_main(control, "main before the record")
    trigger = head_revision(control)

    exit_code = main(
        [
            "draft-proposal-authorization",
            "--repo",
            REPOSITORY,
            "--root",
            str(control),
            "--approver",
            "a-person",
            "--supersedes-pr",
            "3",
        ]
    )
    assert exit_code == EXIT_OK, capsys.readouterr()
    drafted = next((control / AUTHORIZATION_DIRNAME).glob("*.json"))
    document = json.loads(drafted.read_text(encoding="utf-8"))
    assert document["candidate_hash"] == sha256_text(README_TEXT)
    assert document["source_revision"] == REVISION
    assert document["base_branch"] == "main"
    assert document["approver"] == "a-person"
    assert document["supersedes_prs"] == [3]

    # drafted but not merged: a run triggered now cannot use it
    _run_refused(
        capsys, _propose_args(control, drafted, trigger, "--propose"), "authorization_not_committed"
    )
    assert not remote.wrote

    # merged through review, then used by a later run
    merge_to_origin_main(control, "approve the candidate")
    (control / "later.txt").write_text("unrelated\n", encoding="utf-8")
    later = merge_to_origin_main(control, "a later change; the run is triggered here")
    assert main(_propose_args(control, drafted, later, "--propose")) == EXIT_OK
    assert len(remote.create_pr_calls) == 1


def test_drafting_refuses_a_dry_run_entry_a_non_final_bundle_a_stale_bundle_and_an_overwrite(
    control: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    remote = Remote()
    remote.install(monkeypatch)
    base = ["draft-proposal-authorization", "--root", str(control), "--approver", "a-person"]

    _run_refused(capsys, [*base, "--repo", DRY_RUN_REPOSITORY], "registry_dry_run")

    remote.live_revision = "0" * 40
    _run_refused(capsys, [*base, "--repo", REPOSITORY], "source_moved")
    remote.live_revision = REVISION

    write_proposable_bundle(control, REPOSITORY, REVISION, README_TEXT, state="INVALIDATED")
    _run_refused(capsys, [*base, "--repo", REPOSITORY], "bundle_not_ready")
    write_proposable_bundle(control, REPOSITORY, REVISION, README_TEXT)

    assert main([*base, "--repo", REPOSITORY]) == EXIT_OK
    capsys.readouterr()
    assert main([*base, "--repo", REPOSITORY]) == EXIT_USAGE  # never overwrites a record
    assert main([*base, "--repo", REPOSITORY, "--expires-in-hours", "1000"]) == EXIT_USAGE
