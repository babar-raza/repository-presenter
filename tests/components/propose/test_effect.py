"""The gated README-proposal PR effect (G6-W02). Every test injects fake branch/contents/pull-
request functions against an in-memory GitHub model - no test here makes a live call. The point of
this file is the gate itself, the idempotent branch/PR mechanics, the stale-source recheck, and the
lost-response reconciliation path - never a blind retry."""

from __future__ import annotations

from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    ProposalEffectResult,
    propose_candidate,
)
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import CommitOutcome, FileContents, PullRequestRef
from repository_presenter.core.hashing import sha256_text

REPOSITORY = "babar-raza/disposable-target"
BASE_BRANCH = "main"
BRANCH = "repository-presenter/readme-update"
SOURCE_REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
README_V1 = "# Disposable Target\n\nOriginal content.\n"
README_V2 = "# Disposable Target\n\nUpdated content.\n"


def _authorization(readme_text: str = README_V1, **overrides: object) -> object:
    fields: dict[str, object] = {
        "repository": REPOSITORY,
        "candidate_hash": sha256_text(readme_text),
        "source_revision": SOURCE_REVISION,
        "branch": BRANCH,
        "issued_at": "2026-10-01T00:00:00Z",
        "expires_at": "2026-10-01T01:00:00Z",
    }
    fields.update(overrides)
    return authorize_proposal(**fields)  # type: ignore[arg-type]


class FakeGitHub:
    """An in-memory model of exactly the GitHub state ``propose_candidate`` reads and writes:
    branch refs, one file's content per branch, and one open PR per head branch."""

    def __init__(self, *, base_sha: str = "base-sha-1") -> None:
        self.refs: dict[str, str] = {BASE_BRANCH: base_sha}
        self.files: dict[tuple[str, str], FileContents] = {}
        self.prs: dict[str, PullRequestRef] = {}
        self._next_pr_number = 100
        self._next_file_sha = 1
        # "ok" | "unreachable_landed" | "unreachable_lost" | "fail"; "ok" is the default.
        # "unreachable_landed" models a response genuinely lost in flight *after* GitHub committed
        # the write (the realistic shape a timeout/connection-reset produces); "unreachable_lost"
        # models the write never reaching GitHub at all - both raise the identical exception from
        # this module's own point of view, which is exactly why reconciliation (a real read, never
        # a guess) is the only way to tell them apart.
        self.put_behaviors: list[str] = []
        self.put_calls: list[tuple[str, str | None]] = []  # (branch, sha_given)
        self.create_ref_calls: list[tuple[str, str]] = []
        self.create_pr_calls = 0
        self.update_pr_calls = 0

    # -- injected functions, matching core/github/client.py's own call shapes -----------------

    def get_ref(self, owner: str, name: str, branch: str, *, token: str) -> str | None:
        return self.refs.get(branch)

    def create_ref(self, owner: str, name: str, branch: str, sha: str, *, token: str) -> None:
        self.create_ref_calls.append((branch, sha))
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
        self.put_calls.append((branch, sha))
        behavior = self.put_behaviors.pop(0) if self.put_behaviors else "ok"
        if behavior == "unreachable_landed":
            new_sha = f"filesha-{self._next_file_sha}"
            self._next_file_sha += 1
            self.files[(branch, path)] = FileContents(path=path, sha=new_sha, text=text)
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable (ReadTimeout)")
        if behavior == "unreachable_lost":
            raise RepositoryMetadataError(f"{owner}/{name}: unreachable (ReadTimeout)")
        if behavior == "fail":
            raise RepositoryMetadataError(f"{owner}/{name}: PUT ... returned HTTP 422")
        new_sha = f"filesha-{self._next_file_sha}"
        self._next_file_sha += 1
        self.files[(branch, path)] = FileContents(path=path, sha=new_sha, text=text)
        return CommitOutcome(content_sha=new_sha, commit_sha=f"commit-{new_sha}")

    def find_open_pull_request(
        self, owner: str, name: str, *, head_branch: str, token: str
    ) -> PullRequestRef | None:
        return self.prs.get(head_branch)

    def create_pull_request(
        self, owner: str, name: str, *, title: str, body: str, head: str, base: str, token: str
    ) -> PullRequestRef:
        self.create_pr_calls += 1
        number = self._next_pr_number
        self._next_pr_number += 1
        pr = PullRequestRef(
            number=number,
            url=f"https://github.com/{owner}/{name}/pull/{number}",
            title=title,
            body=body,
        )
        self.prs[head] = pr
        return pr

    def update_pull_request(
        self, owner: str, name: str, number: int, *, title: str, body: str, token: str
    ) -> PullRequestRef:
        self.update_pr_calls += 1
        for branch, pr in self.prs.items():
            if pr.number == number:
                updated = PullRequestRef(number=number, url=pr.url, title=title, body=body)
                self.prs[branch] = updated
                return updated
        raise RepositoryMetadataError("no such pull request")

    def reconcile_read(self) -> FileContents | None:
        return self.files.get((BRANCH, "README.md"))

    def kwargs(self) -> dict[str, object]:
        return {
            "get_ref": self.get_ref,
            "create_ref": self.create_ref,
            "get_contents": self.get_contents,
            "put_contents": self.put_contents,
            "find_open_pull_request": self.find_open_pull_request,
            "create_pull_request": self.create_pull_request,
            "update_pull_request": self.update_pull_request,
        }


def _propose(github: FakeGitHub, *, readme_text: str = README_V1, authorization=None, **overrides):
    authorization = authorization or _authorization(readme_text)
    kwargs: dict[str, object] = {
        "repository": REPOSITORY,
        "readme_text": readme_text,
        "source_revision": SOURCE_REVISION,
        "authorization": authorization,
        "base_branch": BASE_BRANCH,
        "pr_title": "Update README via repository-presenter",
        "pr_body": "Automated README proposal.",
        "token": "ghp_write",
        "environment": {AUTHORIZATION_VARIABLE: "1"},
        "clock": lambda: "2026-10-01T00:30:00Z",  # deterministic: authorization expires 01:00:00Z
    }
    kwargs.update(github.kwargs())
    kwargs.update(overrides)
    return propose_candidate(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# refused before any network call
# ---------------------------------------------------------------------------


def test_unauthorized_makes_no_github_call_at_all() -> None:
    github = FakeGitHub()
    result = _propose(github, environment={})
    assert result.authorized is False
    assert result.effected is False
    assert AUTHORIZATION_VARIABLE in result.reason
    assert github.create_ref_calls == []
    assert github.put_calls == []
    assert github.create_pr_calls == 0


def test_authorized_but_no_token_makes_no_github_call() -> None:
    github = FakeGitHub()
    result = _propose(github, token=None)
    assert result.authorized is True
    assert result.effected is False
    assert "token" in result.reason
    assert github.put_calls == []


def test_a_candidate_hash_mismatch_refuses_before_any_github_call() -> None:
    """The authorization was minted for README_V1; proposing README_V2 against it must be refused,
    not silently proposed - the sealed bundle changed since authorization was minted."""
    github = FakeGitHub()
    authorization = _authorization(README_V1)
    result = _propose(github, readme_text=README_V2, authorization=authorization)
    assert result.effected is False
    assert "candidate_hash" in result.reason
    assert github.put_calls == []


def test_an_expired_authorization_refuses_before_any_github_call() -> None:
    github = FakeGitHub()
    authorization = _authorization(expires_at="2020-01-01T00:00:00Z")
    result = _propose(github, authorization=authorization)
    assert result.effected is False
    assert "expired" in result.reason
    assert github.put_calls == []


def test_an_authorization_bound_to_a_different_branch_is_refused() -> None:
    """``propose_candidate`` validates an authorization's own ``branch`` against the canonical
    presenter branch it computes independently - it never just trusts whatever branch the
    authorization claims."""
    github = FakeGitHub()
    authorization = _authorization(branch="some-other-branch")
    result = _propose(github, authorization=authorization)
    assert result.effected is False
    assert "branch" in result.reason
    assert github.put_calls == []


# ---------------------------------------------------------------------------
# stale-source recheck
# ---------------------------------------------------------------------------


def test_a_drifted_live_source_revision_blocks_the_effect() -> None:
    github = FakeGitHub()
    result = _propose(github, recheck_source=lambda: "a" * 40)
    assert result.effected is False
    assert "stale source" in result.reason
    assert github.put_calls == []


def test_a_confirmed_live_source_revision_proceeds() -> None:
    github = FakeGitHub()
    result = _propose(github, recheck_source=lambda: SOURCE_REVISION)
    assert result.effected is True


def test_no_recheck_supplied_still_proceeds_recheck_is_optional() -> None:
    github = FakeGitHub()
    result = _propose(github)
    assert result.effected is True


# ---------------------------------------------------------------------------
# the authorized effect: branch creation, commit, PR creation
# ---------------------------------------------------------------------------


def test_first_proposal_creates_the_branch_commits_and_opens_one_pr() -> None:
    github = FakeGitHub(base_sha="base-sha-1")
    result = _propose(github)
    assert result.effected is True
    assert result.branch == BRANCH
    assert github.create_ref_calls == [(BRANCH, "base-sha-1")]
    assert github.files[(BRANCH, "README.md")].text == README_V1
    assert result.commit_written is True
    assert result.pr_created is True
    assert result.pr_updated is False
    assert github.create_pr_calls == 1
    assert isinstance(result, ProposalEffectResult)
    assert result.pr_number is not None


def test_a_missing_base_branch_refuses() -> None:
    github = FakeGitHub()
    del github.refs[BASE_BRANCH]
    result = _propose(github)
    assert result.effected is False
    assert "base branch" in result.reason


# ---------------------------------------------------------------------------
# idempotency: a second, unchanged invocation creates no duplicate
# ---------------------------------------------------------------------------


def test_a_second_unchanged_invocation_creates_no_duplicate() -> None:
    github = FakeGitHub()
    first = _propose(github)
    assert first.effected is True
    assert len(github.put_calls) == 1
    assert github.create_pr_calls == 1

    second = _propose(github)
    assert second.effected is True
    assert second.commit_written is False
    assert second.pr_created is False
    assert second.pr_updated is False
    assert second.reason == "no change needed"
    # No new branch, no new commit, no new or duplicate PR.
    assert len(github.create_ref_calls) == 1
    assert len(github.put_calls) == 1
    assert github.create_pr_calls == 1
    assert github.update_pr_calls == 0
    assert second.pr_number == first.pr_number


def test_a_changed_candidate_on_an_existing_branch_updates_rather_than_duplicates() -> None:
    github = FakeGitHub()
    first = _propose(github, readme_text=README_V1)
    assert first.effected is True

    authorization_v2 = _authorization(README_V2)
    second = _propose(github, readme_text=README_V2, authorization=authorization_v2)
    assert second.effected is True
    assert second.commit_written is True
    assert second.pr_created is False  # the existing PR is reused, never duplicated
    assert github.create_pr_calls == 1
    assert github.files[(BRANCH, "README.md")].text == README_V2
    assert second.pr_number == first.pr_number


def test_a_changed_pr_title_or_body_updates_the_existing_pr_in_place() -> None:
    github = FakeGitHub()
    _propose(github)
    result = _propose(github, pr_body="A revised body.")
    assert result.pr_updated is True
    assert result.pr_created is False
    assert github.create_pr_calls == 1
    assert github.update_pr_calls == 1


# ---------------------------------------------------------------------------
# lost-response reconciliation: never a blind retry
# ---------------------------------------------------------------------------


def test_a_lost_write_response_that_reconciliation_confirms_landed_is_not_retried() -> None:
    """``put_contents`` raises "unreachable" after GitHub actually committed the write - the
    response alone was lost in flight. Reconciliation must observe the real landed content and
    must not call ``put_contents`` again (AGENTS.md "reconcile uncertain remote effects before
    retrying")."""
    github = FakeGitHub()
    github.refs[BRANCH] = "base-sha-1"  # branch already exists, as if created by a prior attempt
    github.put_behaviors = ["unreachable_landed"]

    result = _propose(github, reconcile_write=github.reconcile_read)
    assert result.effected is True
    assert result.commit_written is True
    assert len(github.put_calls) == 1  # no retry - reconciliation confirmed it already landed
    assert github.files[(BRANCH, "README.md")].text == README_V1


def test_a_lost_write_response_that_reconciliation_confirms_absent_retries_once() -> None:
    """The write genuinely did not land - reconciliation must see that and the module retries
    exactly once, using the freshly observed sha (``None``, since nothing landed) rather than the
    stale one from the first attempt."""
    github = FakeGitHub()
    github.refs[BRANCH] = "base-sha-1"
    github.put_behaviors = ["unreachable_lost", "ok"]

    result = _propose(github, reconcile_write=github.reconcile_read)
    assert result.effected is True
    assert result.commit_written is True
    assert len(github.put_calls) == 2
    assert github.files[(BRANCH, "README.md")].text == README_V1


def test_a_lost_write_response_with_no_reconcile_callable_is_refused_never_retried() -> None:
    github = FakeGitHub()
    github.refs[BRANCH] = "base-sha-1"
    github.put_behaviors = ["unreachable_lost"]

    result = _propose(github)  # no reconcile_write given
    assert result.effected is False
    assert "unreachable" in result.reason
    assert len(github.put_calls) == 1


def test_a_hard_write_failure_is_never_treated_as_reconcilable() -> None:
    """A real rejection (422) is not a lost response - it must never trigger reconciliation or a
    retry, even when a ``reconcile_write`` callable is supplied."""
    github = FakeGitHub()
    github.refs[BRANCH] = "base-sha-1"
    github.put_behaviors = ["fail"]

    result = _propose(github, reconcile_write=github.reconcile_read)
    assert result.effected is False
    assert "422" in result.reason
    assert len(github.put_calls) == 1


def test_a_retry_that_also_fails_after_reconciliation_is_refused() -> None:
    github = FakeGitHub()
    github.refs[BRANCH] = "base-sha-1"
    github.put_behaviors = ["unreachable_lost", "fail"]

    result = _propose(github, reconcile_write=github.reconcile_read)
    assert result.effected is False
    assert "reconciliation" in result.reason
    assert len(github.put_calls) == 2


# ---------------------------------------------------------------------------
# the token never leaks
# ---------------------------------------------------------------------------


def test_result_never_echoes_the_token() -> None:
    github = FakeGitHub()
    result = _propose(github, token="ghp_super_secret_write_token")
    assert "ghp_super_secret_write_token" not in repr(result)
