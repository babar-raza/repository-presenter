"""The gated candidates-publish effect (G7-W14). Every test injects fake git and GitHub functions
against an in-memory model - no test here makes a live call, matching
``tests/components/propose/test_effect.py``'s own discipline."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from repository_presenter.components.candidates_publish.effect import (
    AUTHORIZATION_VARIABLE,
    publish_candidates,
)
from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import PullRequestRef
from repository_presenter.core.github.token_provenance import TokenDecision

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
CONTROL_REPOSITORY = "babar-raza/repository-presenter"
BASE_BRANCH = "main"
BRANCH = "repository-presenter/candidates-update/aspose-cells-foss__Aspose.Cells-FOSS-for-Go"
TOKEN = "gha-fake-token"
CURRENT_PATH = "candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Go/CURRENT"
BUNDLE_PATHS = ("candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Go",)
OLD_REVISION = "a" * 40
NEW_REVISION = "b" * 40


def _authorized_environment() -> dict[str, str]:
    return {AUTHORIZATION_VARIABLE: "1"}


def _always_ok_token(repository: str, token: str) -> TokenDecision:
    return TokenDecision(True)


def _always_ok_attribution(owner: str, name: str, number: int, *, token: str) -> TokenDecision:
    return TokenDecision(True)


@dataclass
class FakeControlGit:
    """An in-memory model of exactly the local git state this effect reads and writes: one
    branch's committed ``CURRENT`` content, which branch is currently checked out, and plain
    call logs for every operation - never a mock that merely records being called."""

    #: branch name -> committed CURRENT content on that branch (None once no file exists yet)
    committed: dict[str, str | None]
    checked_out: str | None = None
    #: the revision this run's overlay would apply, bound by the test
    pending_revision: str = NEW_REVISION
    overlaid: list[str] = field(default_factory=list)
    committed_messages: list[str] = field(default_factory=list)
    pushed: list[str] = field(default_factory=list)
    fail_push: bool = False

    def remote_branch_sha(self, branch: str) -> str | None:
        if branch == BASE_BRANCH or branch not in self.committed:
            return None
        return f"sha-of-{branch}"

    def checkout(self, branch: str, start_point: str) -> None:
        # start_point is always a ref *name* here (branch itself, or BASE_BRANCH) - never a bare
        # sha, matching git_ops.checkout_branch's own "fetch by name, then checkout" contract.
        if branch not in self.committed:
            self.committed[branch] = self.committed.get(start_point)
        self.checked_out = branch

    def read_committed(self, path: str) -> str | None:
        assert self.checked_out is not None
        return self.committed[self.checked_out]

    def overlay(self) -> None:
        assert self.checked_out is not None
        self.overlaid.append(self.checked_out)

    def stage_and_commit(self, paths: tuple[str, ...], message: str) -> str | None:
        assert self.checked_out is not None
        if self.committed[self.checked_out] == self.pending_revision:
            return None  # nothing actually changed - git's own "nothing to commit"
        self.committed[self.checked_out] = self.pending_revision
        self.committed_messages.append(message)
        return "new-commit-sha"

    def push(self, branch: str) -> None:
        if self.fail_push:
            raise RepositoryMetadataError("push refused (simulated)")
        self.pushed.append(branch)


@dataclass
class FakeGitHub:
    prs: dict[str, PullRequestRef] = field(default_factory=dict)
    create_calls: int = 0
    update_calls: int = 0

    def find_pull_requests(
        self, owner: str, name: str, *, head_branch: str, token: str
    ) -> tuple[PullRequestRef, ...]:
        found = self.prs.get(head_branch)
        return (found,) if found is not None else ()

    def create_pull_request(
        self, owner: str, name: str, *, title: str, body: str, head: str, base: str, token: str
    ) -> PullRequestRef:
        self.create_calls += 1
        pr = PullRequestRef(
            number=500, url="https://github.com/x/y/pull/500", title=title, body=body
        )
        self.prs[head] = pr
        return pr

    def update_pull_request(
        self, owner: str, name: str, number: int, *, title: str, body: str, token: str
    ) -> PullRequestRef:
        self.update_calls += 1
        existing = next(pr for pr in self.prs.values() if pr.number == number)
        updated = PullRequestRef(number=number, url=existing.url, title=title, body=body)
        self.prs[BRANCH] = updated
        return updated


def _call(
    git: FakeControlGit,
    hub: FakeGitHub,
    *,
    environment: dict[str, str] | None = None,
    token: str | None = TOKEN,
    verify_token=_always_ok_token,
    verify_pull_request_app=_always_ok_attribution,
    revision: str = NEW_REVISION,
):
    return publish_candidates(
        repository=REPOSITORY,
        control_repository=CONTROL_REPOSITORY,
        revision=revision,
        base_branch=BASE_BRANCH,
        token=token,
        environment=environment if environment is not None else _authorized_environment(),
        pr_title=f"Update candidates/ for {REPOSITORY}",
        pr_body=f"revision: {revision}\n",
        bundle_paths=BUNDLE_PATHS,
        current_path=CURRENT_PATH,
        remote_branch_sha=git.remote_branch_sha,
        checkout=git.checkout,
        read_committed=git.read_committed,
        overlay=git.overlay,
        stage_and_commit=git.stage_and_commit,
        push=git.push,
        verify_token=verify_token,
        verify_pull_request_app=verify_pull_request_app,
        find_pull_requests=hub.find_pull_requests,
        create_pull_request=hub.create_pull_request,
        update_pull_request=hub.update_pull_request,
    )


def test_the_kill_switch_refuses_before_any_call() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    result = _call(git, hub, environment={})
    assert result.authorized is False
    assert result.effected is False
    assert result.reason_code is Refusal.WRITE_NOT_ENABLED
    assert git.checked_out is None
    assert git.pushed == []
    assert hub.create_calls == 0


@pytest.mark.parametrize("value", ["0", "false", "", "yes-please", "TRUE "])
def test_only_exact_truthy_values_authorize(value: str) -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    result = _call(git, hub, environment={AUTHORIZATION_VARIABLE: value})
    if value.strip().lower() in ("true", "1", "yes"):
        assert result.authorized is True
    else:
        assert result.authorized is False
        assert result.reason_code is Refusal.WRITE_NOT_ENABLED


def test_no_token_refuses_before_any_git_or_github_call() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    result = _call(git, hub, token=None)
    assert result.authorized is True
    assert result.effected is False
    assert result.reason_code is Refusal.NO_WRITE_TOKEN
    assert git.checked_out is None


def test_an_unverifiable_token_refuses_before_any_git_call() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()

    def refuse(repository: str, token: str) -> TokenDecision:
        return TokenDecision(False, Refusal.TOKEN_WRONG_SCOPE, "wrong repository")

    result = _call(git, hub, verify_token=refuse)
    assert result.reason_code is Refusal.TOKEN_WRONG_SCOPE
    assert git.checked_out is None


def test_a_fresh_branch_is_created_committed_pushed_and_a_pr_opened() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    result = _call(git, hub)
    assert result.authorized is True
    assert result.effected is True
    assert result.commit_written is True
    assert result.pr_created is True
    assert result.pr_updated is False
    assert git.pushed == [BRANCH]
    assert git.committed[BRANCH] == NEW_REVISION
    assert hub.create_calls == 1
    assert f"revision: {NEW_REVISION}" in git.committed_messages[0]


def test_an_already_current_candidate_is_a_no_op() -> None:
    """The base branch already carries the exact revision about to be published - no commit, no
    push, no pull request, and the branch is still checked out read-only to confirm it."""
    git = FakeControlGit(committed={BASE_BRANCH: NEW_REVISION}, pending_revision=NEW_REVISION)
    hub = FakeGitHub()
    result = _call(git, hub)
    assert result.effected is True
    assert result.commit_written is False
    assert result.pr_created is False
    assert git.pushed == []
    assert git.overlaid == []
    assert hub.create_calls == 0


def test_a_pending_branch_already_at_this_revision_reports_its_open_pr_without_a_new_push() -> None:
    """A prior run already pushed this exact revision to the pending branch and opened a PR; a
    re-run (e.g. an unchanged candidate re-sealed) must not push again or duplicate the PR."""
    git = FakeControlGit(
        committed={BASE_BRANCH: OLD_REVISION, BRANCH: NEW_REVISION}, pending_revision=NEW_REVISION
    )
    hub = FakeGitHub()
    hub.prs[BRANCH] = PullRequestRef(
        number=500,
        url="https://github.com/x/y/pull/500",
        title="t",
        body=f"revision: {NEW_REVISION}\n",
    )
    result = _call(git, hub)
    assert result.effected is True
    assert result.commit_written is False
    assert result.pr_number == 500
    assert git.pushed == []
    assert hub.create_calls == 0
    assert hub.update_calls == 0


def test_a_pending_branch_at_an_older_revision_is_advanced_and_its_pr_updated() -> None:
    """The pending branch exists from a previous, now-superseded candidate; this run continues
    from its own tip (never the base branch, never force-reset) and updates the existing PR."""
    git = FakeControlGit(
        committed={BASE_BRANCH: OLD_REVISION, BRANCH: "c" * 40}, pending_revision=NEW_REVISION
    )
    hub = FakeGitHub()
    hub.prs[BRANCH] = PullRequestRef(
        number=501,
        url="https://github.com/x/y/pull/501",
        title="old title",
        body="revision: " + "c" * 40 + "\n",
    )
    result = _call(git, hub)
    assert result.effected is True
    assert result.commit_written is True
    assert result.pr_updated is True
    assert result.pr_created is False
    assert git.pushed == [BRANCH]
    assert hub.update_calls == 1


def test_an_open_pr_already_carrying_the_new_revision_is_not_rewritten() -> None:
    """The branch's own CURRENT differs (so a commit is needed), but the open PR's body already
    carries this exact revision (e.g. only metadata changed) - no pointless PR edit."""
    git = FakeControlGit(
        committed={BASE_BRANCH: OLD_REVISION, BRANCH: "c" * 40}, pending_revision=NEW_REVISION
    )
    hub = FakeGitHub()
    title = f"Update candidates/ for {REPOSITORY}"
    hub.prs[BRANCH] = PullRequestRef(
        number=502,
        url="https://github.com/x/y/pull/502",
        title=title,
        body=f"revision: {NEW_REVISION}\n",
    )
    result = _call(git, hub)
    assert result.commit_written is True
    assert result.pr_updated is False
    assert hub.update_calls == 0


def test_a_push_failure_is_reported_as_a_github_error_not_swallowed() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION}, fail_push=True)
    hub = FakeGitHub()
    result = _call(git, hub)
    assert result.effected is False
    assert result.reason_code is Refusal.GITHUB_ERROR
    assert "push refused" in result.reason


def test_a_find_pull_requests_failure_before_any_write_is_reported() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()

    def raising_find(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RepositoryMetadataError("could not list pull requests (simulated)")

    hub.find_pull_requests = raising_find  # type: ignore[assignment]
    result = _call(git, hub)
    assert result.effected is False
    assert result.reason_code is Refusal.GITHUB_ERROR
    # Nothing was committed or pushed before this read failed.
    assert git.pushed == []


# -- App provenance (the ambient GITHUB_TOKEN cannot open the PR or start its required checks on
# this repository, so the write credential is an App installation token; its PR is attributed) ----


def _attribution_spy() -> tuple[list[int], object]:
    seen: list[int] = []

    def verify(owner: str, name: str, number: int, *, token: str) -> TokenDecision:
        assert (owner, name) == tuple(CONTROL_REPOSITORY.split("/"))
        assert token == TOKEN
        seen.append(number)
        return TokenDecision(True)

    return seen, verify


def _foreign(owner: str, name: str, number: int, *, token: str) -> TokenDecision:
    return TokenDecision(
        False, Refusal.TOKEN_APP_MISMATCH, "pull request was performed by another GitHub App"
    )


def test_a_newly_opened_pr_is_attributed_to_the_app() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    seen, verify = _attribution_spy()
    result = _call(git, hub, verify_pull_request_app=verify)
    assert result.effected is True
    assert seen == [500]


def test_a_new_pr_not_attributed_to_the_app_is_reported_not_effected() -> None:
    """The ambient GITHUB_TOKEN wired in by mistake is also a ``ghs_`` token: the push may have
    happened, but the result must say so and must never report success."""
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    result = _call(git, hub, verify_pull_request_app=_foreign)
    assert result.effected is False
    assert result.reason_code is Refusal.TOKEN_APP_MISMATCH
    assert result.pr_number == 500
    assert result.pr_created is True
    assert result.commit_written is True
    assert "review and close" in result.reason


def test_an_existing_pr_not_attributed_to_the_app_stops_before_any_write() -> None:
    """A hand-made or foreign PR on the reserved branch name: nothing is overlaid, committed,
    pushed or edited."""
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION, BRANCH: "c" * 40})
    hub = FakeGitHub()
    hub.prs[BRANCH] = PullRequestRef(
        number=501, url="https://github.com/x/y/pull/501", title="t", body="revision: c\n"
    )
    result = _call(git, hub, verify_pull_request_app=_foreign)
    assert result.effected is False
    assert result.reason_code is Refusal.TOKEN_APP_MISMATCH
    assert git.overlaid == []
    assert git.committed_messages == []
    assert git.pushed == []
    assert hub.create_calls == 0
    assert hub.update_calls == 0


def test_an_unverifiable_existing_pr_attribution_stops_before_any_write() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION, BRANCH: "c" * 40})
    hub = FakeGitHub()
    hub.prs[BRANCH] = PullRequestRef(
        number=501, url="https://github.com/x/y/pull/501", title="t", body="revision: c\n"
    )

    def unverifiable(owner: str, name: str, number: int, *, token: str) -> TokenDecision:
        return TokenDecision(False, None, "could not attribute pull request")

    result = _call(git, hub, verify_pull_request_app=unverifiable)
    assert result.effected is False
    assert result.reason_code is Refusal.TOKEN_UNVERIFIABLE
    assert git.pushed == []


def test_an_attributed_existing_pr_is_checked_before_the_push_then_updated() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION, BRANCH: "c" * 40})
    hub = FakeGitHub()
    hub.prs[BRANCH] = PullRequestRef(
        number=501, url="https://github.com/x/y/pull/501", title="t", body="revision: c\n"
    )
    seen, verify = _attribution_spy()
    result = _call(git, hub, verify_pull_request_app=verify)
    assert result.effected is True
    assert seen == [501]
    assert result.pr_updated is True


def test_the_kill_switch_and_token_gates_run_before_any_attribution_call() -> None:
    calls: list[int] = []

    def spy(owner: str, name: str, number: int, *, token: str) -> TokenDecision:
        calls.append(number)
        return TokenDecision(True)

    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    hub = FakeGitHub()
    assert _call(git, hub, environment={}, verify_pull_request_app=spy).effected is False
    assert _call(git, hub, token=None, verify_pull_request_app=spy).effected is False
    assert calls == []
    assert git.checked_out is None


def test_an_already_current_candidate_makes_no_attribution_or_write_call() -> None:
    git = FakeControlGit(committed={BASE_BRANCH: NEW_REVISION}, pending_revision=NEW_REVISION)
    hub = FakeGitHub()
    seen, verify = _attribution_spy()
    result = _call(git, hub, verify_pull_request_app=verify)
    assert result.effected is True
    assert seen == []
    assert git.pushed == []


def test_only_the_reserved_candidates_update_branch_is_ever_pushed() -> None:
    """Negative control: an unrelated branch (and above all the base branch) is never written."""
    git = FakeControlGit(committed={BASE_BRANCH: OLD_REVISION})
    result = _call(git, FakeGitHub())
    assert result.effected is True
    assert git.pushed == [BRANCH]
    assert BASE_BRANCH not in git.pushed
    prefix = "repository-presenter/candidates-update/"
    assert all(branch.startswith(prefix) for branch in git.pushed)
