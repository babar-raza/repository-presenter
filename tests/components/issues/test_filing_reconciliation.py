"""TC-ISS-09: a filing whose response was lost is reconciled, never duplicated.

A fake upstream stands in for GitHub: it holds the issues that were really created, so a "lost
response" can be the case that matters (the POST took effect and the answer never arrived) as well
as the harmless one (the POST never took effect). The search is the real
``find_issue_with_marker`` over the fake's listing; no test here touches the network."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from repository_presenter.components.issues.file import (
    FileResult,
    fingerprint_marker,
)
from repository_presenter.components.issues.file import file_handoff as _file_handoff
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import find_issue_with_marker
from support import accepting_token_verifier, approving_store, make_permit

REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
FINGERPRINT = "sha256:" + "c" * 64
ENVIRONMENT = {"REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED": "1"}


def _handoff() -> Handoff:
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-02", version="3", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="src/x/NumberFormat.cpp", detail="trigraph is fatal"),),
        claim="a claim",
        suggested_issue_title="Aspose Cells: the build fails on a trigraph",
        suggested_issue_body="Body.\n",
        status="HANDOFF_PENDING",
        issue_ref=None,
    )


class FakeUpstream:
    """The target repository's issue tracker. ``script`` is the fate of each successive POST:
    ``ok`` (created, answered), ``applied`` (created, answer lost), ``dropped`` (not created,
    answer lost), ``reject`` (HTTP 422, not created)."""

    def __init__(self, *script: str, list_fails: bool = False) -> None:
        self.script = list(script)
        self.issues: list[dict[str, Any]] = []
        self.log: list[str] = []
        self.list_fails = list_fails

    def post(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        fate = self.script.pop(0)
        self.log.append(f"POST:{fate}")
        if fate == "reject":
            return 422, {"message": "Validation Failed"}
        if fate in {"ok", "applied"}:
            number = len(self.issues) + 1
            self.issues.append(
                {
                    "number": number,
                    "html_url": f"https://github.com/{REPO}/issues/{number}",
                    "body": payload["body"],
                    "state": "open",
                    "created_at": "2026-10-11T08:00:00Z",
                }
            )
            if fate == "ok":
                return 201, self.issues[-1]
        return -1, "ReadTimeout: timed out"

    def fetch(self, url: str, token: str | None) -> tuple[int, Any]:
        self.log.append("GET")
        if self.list_fails:
            return 503, None
        return 200, list(self.issues)

    def existing(self) -> IssueRef | None:
        owner, name = REPO.split("/", 1)
        found = find_issue_with_marker(
            owner, name, fingerprint_marker(FINGERPRINT), token="r", fetch=self.fetch
        )
        return None if found is None else IssueRef(found.number, found.url)


def _file(upstream: FakeUpstream, *, with_search: bool = True, **extra: Any) -> FileResult:
    handoff = _handoff()
    recheck: Callable[[], RedetectionResult] = lambda: RedetectionResult(  # noqa: E731
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="BC-02",
        checked_at="2026-10-11T08:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=True,
        note="still fires",
        fresh_evidence=(),
        proposed_status=None,
    )
    return _file_handoff(
        handoff,
        token="w",
        environment=ENVIRONMENT,
        create=upstream.post,
        existing=upstream.existing if with_search else None,
        recheck=recheck,
        approvals=approving_store(handoff),
        permit=make_permit(REPO, effect="issue_filing"),
        verify_token=accepting_token_verifier,
        **extra,
    )


def test_a_clean_filing_posts_once() -> None:
    upstream = FakeUpstream("ok")
    result = _file(upstream)
    assert result.filed is True and result.reconciled is False
    assert upstream.log == ["GET", "POST:ok"]  # the pre-filing search, then the one POST
    assert len(upstream.issues) == 1


def test_a_lost_response_after_the_issue_was_created_is_reconciled_not_refiled() -> None:
    upstream = FakeUpstream("applied")
    result = _file(upstream)
    assert len(upstream.issues) == 1  # exactly one issue exists
    assert upstream.log == ["GET", "POST:applied", "GET"]  # search before any second POST
    assert result.issue_ref == IssueRef(1, f"https://github.com/{REPO}/issues/1")
    assert result.reconciled is True
    assert result.filed is False and result.error is False
    assert "reconciled" in result.reason


def test_a_lost_response_before_the_issue_was_created_is_retried_after_a_search() -> None:
    upstream = FakeUpstream("dropped", "ok")
    result = _file(upstream)
    assert upstream.log == ["GET", "POST:dropped", "GET", "POST:ok"]
    assert len(upstream.issues) == 1
    assert result.filed is True and result.issue_ref is not None
    assert result.reconciled is False


def test_two_lost_responses_stop_at_the_attempt_bound_and_report_an_error() -> None:
    upstream = FakeUpstream("dropped", "dropped", "ok")
    result = _file(upstream)
    assert upstream.log.count("POST:dropped") == 2
    assert "POST:ok" not in upstream.log  # never a third attempt
    assert upstream.issues == []
    assert result.error is True and result.filed is False and result.issue_ref is None


def test_the_second_attempt_that_is_applied_but_lost_is_also_reconciled() -> None:
    upstream = FakeUpstream("dropped", "applied")
    result = _file(upstream)
    assert upstream.log == ["GET", "POST:dropped", "GET", "POST:applied", "GET"]
    assert len(upstream.issues) == 1
    assert result.reconciled is True and result.issue_ref is not None


def test_an_unsearchable_target_is_never_retried_after_a_lost_response() -> None:
    upstream = FakeUpstream("applied")
    # The pre-filing search succeeds; the one after the lost response cannot complete.
    results = iter([False, True])
    original = upstream.fetch

    def flaky(url: str, token: str | None) -> tuple[int, Any]:
        upstream.list_fails = next(results)
        return original(url, token)

    upstream.fetch = flaky  # type: ignore[method-assign]
    result = _file(upstream)
    assert upstream.log.count("POST:applied") == 1  # no blind retry
    assert result.error is True and result.issue_ref is None
    assert "cannot be reconciled" in result.reason or "inconclusive" in result.reason


def test_without_a_search_a_lost_response_is_reported_and_not_retried() -> None:
    upstream = FakeUpstream("dropped", "ok")
    result = _file(upstream, with_search=False)
    assert upstream.log == ["POST:dropped"]
    assert result.error is True and result.filed is False


def test_a_definite_rejection_is_neither_searched_nor_retried() -> None:
    upstream = FakeUpstream("reject", "ok")
    result = _file(upstream)
    assert upstream.log == ["GET", "POST:reject"]
    assert result.error is True and result.filed is False


def test_the_write_hook_can_refuse_after_every_other_gate_with_no_post() -> None:
    upstream = FakeUpstream("ok")
    result = _file(upstream, before_write=lambda: "daily cap reached")
    assert upstream.log == ["GET"]
    assert result.filed is False and result.error is False
    assert result.reason == "daily cap reached"


def test_the_write_hook_runs_once_before_the_first_post_only() -> None:
    upstream = FakeUpstream("dropped", "ok")
    calls: list[str] = []
    _file(upstream, before_write=lambda: calls.append("hook"))
    assert calls == ["hook"]


def test_a_search_failure_before_filing_still_refuses_without_a_post() -> None:
    upstream = FakeUpstream("ok", list_fails=True)
    result = _file(upstream)
    assert "POST:ok" not in upstream.log
    assert result.filed is False


def test_the_unknown_outcome_error_type_is_what_triggers_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A plain metadata error from the POST (a rejection) must not reconcile."""
    upstream = FakeUpstream("ok")
    calls: list[str] = []

    def boom(*args: Any, **kwargs: Any) -> Any:
        calls.append("create")
        raise RepositoryMetadataError("rejected")

    monkeypatch.setattr("repository_presenter.components.issues.file.create_issue", boom)
    result = _file(upstream)
    assert calls == ["create"]
    assert result.error is True
    assert upstream.log == ["GET"]
