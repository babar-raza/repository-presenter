"""TC-ISS-10: the gated write half of the lifecycle - one update comment on an issue this system
filed. A fake upstream holds the issue and its comments; nothing here touches the network.

The comment is a write to a product repository, so it passes the gates a filing passes (registry
permit, kill switch, write-scoped token with verified provenance) and proves the target is this
system's own open issue (its fingerprint marker) before it posts; an unknown outcome is reconciled
by listing the comments, never repeated blind."""

from __future__ import annotations

from typing import Any

import pytest

from repository_presenter.components.issues.file import CommentResult, comment_on_filed
from repository_presenter.components.issues.lifecycle import evidence_state_digest, update_marker
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    IssueComment,
    IssueSnapshot,
    list_issue_comments,
)
from repository_presenter.core.github.token_provenance import TokenDecision
from support import accepting_token_verifier, make_permit

REPO = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
FILED_AT = "a" * 40
HEAD = "b" * 40
FINGERPRINT = "sha256:" + "d" * 64
ENVIRONMENT = {
    "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1",
    "REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED": "1",
}
ISSUE_BODY = f"report\n\n<!-- repository-presenter-defect: {FINGERPRINT} -->\n"


def _handoff() -> Handoff:
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=FILED_AT,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(
            id="NOT_PROCESSABLE", version="1", causal_stage="EXTRACTING"
        ),
        evidence=(EvidenceEntry(path="src/a.py", detail="SyntaxError"),),
        claim="102 of 119 source files do not parse",
        suggested_issue_title="Aspose.TeX FOSS for Python: source files do not parse",
        suggested_issue_body="body\n",
        status="FILED",
        issue_ref=IssueRef(12, f"https://github.com/{REPO}/issues/12"),
    )


def _result(
    *, fires: bool | None = True, note: str = "still fires: 90/119 files"
) -> RedetectionResult:
    return RedetectionResult(
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="NOT_PROCESSABLE",
        checked_at="2026-10-11T09:00:00+00:00",
        checked_at_revision=HEAD,
        revision_drifted=True,
        still_fires=fires,
        note=note,
        fresh_evidence=(EvidenceEntry(path="src/a.py", detail="SyntaxError at line 3"),),
        proposed_status=None,
    )


class FakeIssue:
    """One upstream issue and its comment thread. ``fates`` is what each POST does:
    ``ok``, ``applied`` (posted, answer lost), ``dropped`` (not posted, answer lost), ``reject``."""

    def __init__(
        self,
        *fates: str,
        body: str = ISSUE_BODY,
        state: str = "open",
        comments: tuple[str, ...] = (),
        list_fails: bool = False,
    ) -> None:
        self.fates = list(fates)
        self.body, self.state = body, state
        self.comments = [
            IssueComment(i + 1, text, "2026-10-10T00:00:00Z") for i, text in enumerate(comments)
        ]
        self.posts: list[str] = []
        self.list_fails = list_fails

    def post(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        fate = self.fates.pop(0)
        self.posts.append(fate)
        if fate == "reject":
            return 403, {"message": "Forbidden"}
        if fate in {"ok", "applied"}:
            self.comments.append(
                IssueComment(len(self.comments) + 1, payload["body"], "2026-10-11T09:00:00Z")
            )
            if fate == "ok":
                last = self.comments[-1]
                return 201, {"id": last.id, "body": last.body, "created_at": last.created_at}
        return -1, "ReadTimeout"

    def fetch(self, url: str, token: str | None) -> tuple[int, Any]:
        if self.list_fails:
            return 503, None
        return 200, [
            {"id": c.id, "body": c.body, "created_at": c.created_at} for c in self.comments
        ]

    def issue(self) -> IssueSnapshot:
        return IssueSnapshot(12, self.state, self.body, False)

    def thread(self) -> tuple[IssueComment, ...]:
        owner, name = REPO.split("/", 1)
        return list_issue_comments(owner, name, 12, token="r", fetch=self.fetch)


def _comment(
    issue: FakeIssue, result: RedetectionResult | None = None, **extra: Any
) -> CommentResult:
    kwargs: dict[str, Any] = {
        "token": "w",
        "environment": ENVIRONMENT,
        "permit": make_permit(REPO, effect="issue_filing"),
        "verify_token": accepting_token_verifier,
        "issue_lookup": issue.issue,
        "comments_lookup": issue.thread,
        "create": issue.post,
    }
    kwargs.update(extra)
    return comment_on_filed(_handoff(), result or _result(), **kwargs)


def test_changed_evidence_posts_one_comment_on_the_existing_issue() -> None:
    issue = FakeIssue("ok")
    outcome = _comment(issue)
    assert outcome.commented is True and outcome.error is False
    assert issue.posts == ["ok"]
    assert (
        update_marker(FINGERPRINT, evidence_state_digest(_result()), HEAD)
        in issue.comments[-1].body
    )


def test_a_second_cycle_with_the_same_evidence_posts_nothing() -> None:
    issue = FakeIssue("ok", "ok")
    assert _comment(issue).commented is True
    again = _comment(issue)
    assert again.commented is False and "already" in again.reason
    assert issue.posts == ["ok"]  # one comment in all, never a duplicate


def test_changed_evidence_on_the_next_cycle_posts_a_second_comment() -> None:
    issue = FakeIssue("ok", "ok")
    _comment(issue)
    follow = _comment(issue, _result(note="still fires: 40/119 files"))
    assert follow.commented is True
    assert issue.posts == ["ok", "ok"]


def test_the_kill_switch_off_posts_nothing_and_reads_nothing() -> None:
    issue = FakeIssue("ok")
    outcome = _comment(issue, environment={})
    assert outcome.authorized is False and outcome.commented is False
    assert issue.posts == []


def test_the_separate_comments_switch_must_also_be_on() -> None:
    issue = FakeIssue("ok")
    only_filing = {"REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1"}
    outcome = _comment(issue, environment=only_filing)
    assert outcome.authorized is False and outcome.commented is False
    assert "COMMENTS_AUTHORIZED" in outcome.reason
    assert issue.posts == []
    only_comments = {"REPOSITORY_PRESENTER_ISSUES_COMMENTS_AUTHORIZED": "1"}
    assert _comment(issue, environment=only_comments).commented is False
    assert issue.posts == []


def test_no_write_token_posts_nothing() -> None:
    issue = FakeIssue("ok")
    assert _comment(issue, token=None).commented is False
    assert issue.posts == []


def test_a_token_that_is_not_a_scoped_installation_token_posts_nothing() -> None:
    issue = FakeIssue("ok")
    outcome = _comment(
        issue,
        verify_token=lambda token: TokenDecision(False, Refusal.TOKEN_NOT_INSTALLATION, "a PAT"),
    )
    assert outcome.commented is False and "token refused" in outcome.reason
    assert issue.posts == []


def test_a_permit_for_another_effect_or_repository_is_a_programming_error() -> None:
    issue = FakeIssue("ok")
    with pytest.raises(ValueError):
        _comment(issue, permit=make_permit(REPO, effect="issue_close"))
    with pytest.raises(ValueError):
        _comment(issue, permit=make_permit("other-org/other-repo", effect="issue_filing"))


def test_an_issue_without_this_systems_marker_is_never_commented_on() -> None:
    issue = FakeIssue("ok", body="someone else's issue, no marker")
    outcome = _comment(issue)
    assert outcome.commented is False and "marker" in outcome.reason
    assert issue.posts == []


def test_a_closed_issue_is_not_commented_on() -> None:
    issue = FakeIssue("ok", state="closed")
    assert _comment(issue).commented is False
    assert issue.posts == []


def test_an_unreadable_thread_posts_nothing() -> None:
    issue = FakeIssue("ok", list_fails=True)
    outcome = _comment(issue)
    assert outcome.commented is False and issue.posts == []


def test_a_defect_that_no_longer_fires_gets_no_comment() -> None:
    issue = FakeIssue("ok")
    outcome = _comment(issue, _result(fires=False))
    assert outcome.commented is False and "close" in outcome.reason
    assert issue.posts == []


def test_a_lost_response_after_the_comment_landed_is_reconciled_not_reposted() -> None:
    issue = FakeIssue("applied", "ok")
    outcome = _comment(issue)
    assert issue.posts == ["applied"]
    assert outcome.reconciled is True and outcome.error is False and outcome.commented is False
    assert len(issue.comments) == 1


def test_a_lost_response_before_the_comment_landed_is_an_error_left_for_the_next_cycle() -> None:
    issue = FakeIssue("dropped", "ok")
    outcome = _comment(issue)
    assert issue.posts == ["dropped"]  # not repeated blind within the cycle
    assert outcome.error is True and outcome.commented is False
    assert _comment(issue).commented is True  # the next cycle posts it
    assert len(issue.comments) == 1


def test_a_rejection_is_an_error_and_is_not_retried() -> None:
    issue = FakeIssue("reject", "ok")
    outcome = _comment(issue)
    assert outcome.error is True
    assert issue.posts == ["reject"]


def test_an_unreadable_issue_posts_nothing() -> None:
    issue = FakeIssue("ok")

    def broken() -> IssueSnapshot:
        raise RepositoryMetadataError("o/n: GET returned HTTP 502")

    outcome = _comment(issue, issue_lookup=broken)
    assert outcome.commented is False and issue.posts == []
