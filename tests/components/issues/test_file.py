"""Phase 3 file: gated ``POST /repos/{owner}/{repo}/issues``. Every test injects a fake ``create``
function - no test here, or anywhere in this suite, makes a live GitHub call. The point of this
file is the gate itself: an unauthorized, under-credentialed, already-filed, or recheck-failed
handoff must never reach ``create``."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from repository_presenter.components.issues.file import (
    AUTHORIZATION_VARIABLE,
    FileResult,
    plan_close_gated,
    write_authorized,
)
from repository_presenter.components.issues.file import close_handoff as _close_handoff
from repository_presenter.components.issues.file import file_handoff as _file_handoff
from repository_presenter.components.issues.file import plan_filing as _plan_filing
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import IssueSnapshot
from repository_presenter.core.github.token_provenance import TokenDecision
from support import MemoryApprovalStore, approving_store, closing_store, make_permit

REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
FINGERPRINT = "sha256:b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365"


def _handoff(*, status: str = "HANDOFF_PENDING", issue_ref: IssueRef | None = None) -> Handoff:
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-02", version="3", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="src/x/NumberFormat.cpp", detail="trigraph '??/' is fatal"),),
        claim=f"At revision {REVISION}, {REPO}'s own install_command:cmake is UNRESOLVED.",
        suggested_issue_title=f"install_command:cmake is UNRESOLVED at {REVISION[:12]}",
        suggested_issue_body="repository-presenter's validation pipeline found this.\n",
        status=status,  # type: ignore[arg-type]
        issue_ref=issue_ref,
    )


def _fires(*, still_fires: bool | None, note: str = "still fires") -> RedetectionResult:
    return RedetectionResult(
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="BC-02",
        checked_at="2026-09-27T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=still_fires,
        note=note,
        fresh_evidence=(),
        proposed_status=None,
    )


def file_handoff(handoff: Handoff, **kwargs: Any) -> FileResult:
    """``file_handoff`` with the owner's approval for ``handoff`` committed. These tests are about
    the other gates; the approval gate's own refusals are in test_approval.py."""
    kwargs.setdefault("approvals", approving_store(handoff))
    kwargs.setdefault("permit", make_permit(handoff.repository, effect="issue_filing"))
    return _file_handoff(handoff, **kwargs)


def plan_filing(handoff: Handoff, **kwargs: Any) -> Any:
    kwargs.setdefault("approvals", approving_store(handoff))
    return _plan_filing(handoff, **kwargs)


class _RecordingCreate:
    """A fake ``WriteFn`` that records every call and returns a fixed response."""

    def __init__(self, status_code: int = 201, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body if body is not None else {"number": 7, "html_url": "https://x/issues/7"}

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


# ---------------------------------------------------------------------------
# write_authorized
# ---------------------------------------------------------------------------


def test_write_authorized_true_for_1_true_or_yes_case_insensitive() -> None:
    for value in ("1", "true", "True", "TRUE", "yes", "Yes"):
        assert write_authorized({AUTHORIZATION_VARIABLE: value}) is True


def test_write_authorized_false_when_absent_empty_or_any_other_value() -> None:
    assert write_authorized({}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: ""}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "0"}) is False
    assert write_authorized({AUTHORIZATION_VARIABLE: "false"}) is False


def test_write_authorized_ignores_credential_looking_variables() -> None:
    """A write-scoped token being present must never itself flip authorization on."""
    assert write_authorized({"GH_ISSUES_WRITE_TOKEN": "ghp_realtoken1234567890"}) is False


# ---------------------------------------------------------------------------
# file_handoff: refused before any network call
# ---------------------------------------------------------------------------


def test_unauthorized_makes_no_create_call_at_all() -> None:
    create = _RecordingCreate()
    result = file_handoff(_handoff(), token="ghp_write", environment={}, create=create)
    assert create.calls == []
    assert result.authorized is False
    assert result.filed is False
    assert AUTHORIZATION_VARIABLE in result.reason
    assert "kill switch" in result.reason


def test_authorized_but_no_token_makes_no_create_call() -> None:
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(), token=None, environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert create.calls == []
    assert result.authorized is True
    assert result.filed is False
    assert "token" in result.reason


def test_a_non_pending_status_is_refused_even_when_fully_authorized() -> None:
    create = _RecordingCreate()
    handoff = _handoff(status="FILED", issue_ref=IssueRef(number=1, url="https://x/issues/1"))
    result = file_handoff(
        handoff, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert create.calls == []
    assert result.filed is False
    assert "FILED" in result.reason
    assert "HANDOFF_PENDING" in result.reason


def test_an_acknowledged_handoff_is_also_refused_never_re_filed() -> None:
    create = _RecordingCreate()
    handoff = _handoff(status="HANDOFF_ACKNOWLEDGED")
    result = file_handoff(
        handoff, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert create.calls == []
    assert result.filed is False


# ---------------------------------------------------------------------------
# file_handoff: recheck-before-effect
# ---------------------------------------------------------------------------


def test_recheck_says_no_longer_fires_aborts_the_write() -> None:
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
        recheck=lambda: _fires(still_fires=False, note="no longer fires: fixed upstream"),
    )
    assert create.calls == []
    assert result.filed is False
    assert "no longer fires" in result.reason


def test_recheck_inconclusive_aborts_the_write() -> None:
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
        recheck=lambda: _fires(still_fires=None, note="inconclusive: network error"),
    )
    assert create.calls == []
    assert result.filed is False
    assert "inconclusive" in result.reason


def test_recheck_confirms_still_fires_and_proceeds_to_file() -> None:
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
        recheck=lambda: _fires(still_fires=True),
    )
    assert len(create.calls) == 1
    assert result.filed is True


def test_no_recheck_supplied_proceeds_to_file() -> None:
    """``recheck`` is optional - a caller with no redetector wiring still gets the base gates."""
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(), token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert len(create.calls) == 1
    assert result.filed is True


# ---------------------------------------------------------------------------
# file_handoff: the authorized write path
# ---------------------------------------------------------------------------


def test_authorized_write_posts_the_suggested_title_and_body() -> None:
    create = _RecordingCreate()
    handoff = _handoff()
    result = file_handoff(
        handoff, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert len(create.calls) == 1
    url, token, payload = create.calls[0]
    assert url == "https://api.github.com/repos/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues"
    assert token == "ghp_write"
    assert payload["title"] == handoff.suggested_issue_title
    assert payload["body"].startswith(handoff.suggested_issue_body.rstrip())
    assert payload["body"].rstrip().endswith(f"<!-- repository-presenter-defect: {FINGERPRINT} -->")
    assert result.filed is True
    assert result.issue_ref == IssueRef(number=7, url="https://x/issues/7")
    assert result.reason == "filed"


def test_a_create_failure_is_reported_never_raised() -> None:
    create = _RecordingCreate(status_code=422, body={"message": "Validation failed"})
    result = file_handoff(
        _handoff(), token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert result.filed is False
    assert "422" in result.reason
    assert result.issue_ref is None


# ---------------------------------------------------------------------------
# FileResult never leaks the token
# ---------------------------------------------------------------------------


def test_file_result_never_echoes_the_token() -> None:
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_super_secret_write_token",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
    )
    assert isinstance(result, FileResult)
    assert "ghp_super_secret_write_token" not in repr(result)


def test_a_second_call_against_a_filed_handoff_never_double_files() -> None:
    """The idempotency guard end to end: file once, then simulate the on-disk status update
    (as the CLI does) and confirm a second call refuses without a network call."""
    create = _RecordingCreate()
    handoff = _handoff()
    first = file_handoff(
        handoff, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert first.filed is True
    refiled = replace(handoff, status="FILED", issue_ref=first.issue_ref)
    second = file_handoff(
        refiled, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert second.filed is False
    assert len(create.calls) == 1


# ---------------------------------------------------------------------------
# Scheduled-run dedup: the upstream marker, the fail-closed lookup, and the read-only plan
# ---------------------------------------------------------------------------

MARKER = f"<!-- repository-presenter-defect: {FINGERPRINT} -->"


def _issue_ref(number: int = 7) -> IssueRef:
    return IssueRef(number=number, url=f"https://x/issues/{number}")


def test_the_posted_body_carries_the_fingerprint_marker_so_a_later_run_can_find_it() -> None:
    create = _RecordingCreate()
    file_handoff(
        _handoff(), token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    _, _, payload = create.calls[0]
    assert payload["body"].startswith("repository-presenter's validation pipeline found this.")
    assert payload["body"].rstrip().endswith(MARKER)


def test_a_body_that_already_carries_the_marker_is_not_given_a_second_one() -> None:
    create = _RecordingCreate()
    handoff = replace(_handoff(), suggested_issue_body=f"text\n\n{MARKER}\n")
    file_handoff(
        handoff, token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert create.calls[0][2]["body"].count(MARKER) == 1


def test_a_second_run_from_a_fresh_checkout_files_nothing_when_the_upstream_issue_exists() -> None:
    """The local artifact still reads HANDOFF_PENDING (a fresh checkout never kept the FILED
    write); the upstream issue body alone proves the defect is already filed."""
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
        existing=lambda: _issue_ref(7),
        recheck=lambda: _fires(still_fires=True),
    )
    assert create.calls == []
    assert result.filed is False
    assert result.error is False
    assert result.issue_ref == _issue_ref(7)
    assert "already filed" in result.reason


def test_an_inconclusive_upstream_lookup_refuses_to_file_never_assumes_absence() -> None:
    def broken() -> IssueRef | None:
        raise RepositoryMetadataError("o/n: GET returned HTTP 403")

    create = _RecordingCreate()
    result = file_handoff(
        _handoff(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        create=create,
        existing=broken,
    )
    assert create.calls == []
    assert result.filed is False
    assert result.issue_ref is None
    assert "inconclusive" in result.reason


def test_an_authorized_create_failure_is_flagged_as_an_error_not_a_refusal() -> None:
    create = _RecordingCreate(status_code=500, body={"message": "boom"})
    result = file_handoff(
        _handoff(), token="ghp_write", environment={AUTHORIZATION_VARIABLE: "1"}, create=create
    )
    assert result.filed is False
    assert result.error is True


def test_plan_filing_is_read_only_and_reports_ready_when_nothing_blocks_it() -> None:
    plan = plan_filing(_handoff(), existing=lambda: None, recheck=lambda: _fires(still_fires=True))
    assert plan.ready is True
    assert plan.refusal is None
    assert plan.already_filed is None


def test_plan_filing_reports_an_existing_upstream_issue_as_already_filed() -> None:
    plan = plan_filing(
        _handoff(), existing=lambda: _issue_ref(7), recheck=lambda: _fires(still_fires=True)
    )
    assert plan.ready is False
    assert plan.already_filed == _issue_ref(7)


def test_plan_filing_refuses_a_non_pending_handoff_without_any_lookup() -> None:
    def must_not_run() -> IssueRef | None:
        raise AssertionError("a lookup must not run for a non-pending handoff")

    plan = plan_filing(_handoff(status="FILED", issue_ref=_issue_ref()), existing=must_not_run)
    assert plan.refusal is not None
    assert "not HANDOFF_PENDING" in plan.refusal


# ---------------------------------------------------------------------------
# close_handoff: the gated close of a FILED handoff that redetection proved resolved.
# Closing is a write to a product repository, so it needs the registry permit, the kill switch, a
# write token, the owner's per-issue close approval, a verified token and a live issue carrying
# this handoff's marker. Each negative control below fails if exactly that gate is removed.
# ---------------------------------------------------------------------------


def _resolved(
    reason: str | None = "not planned", *, still_fires: bool | None = False
) -> RedetectionResult:
    resolves = still_fires is False
    return RedetectionResult(
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="BC-02",
        checked_at="2026-10-04T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=reason == "completed",
        still_fires=still_fires,
        note="no longer fires",
        fresh_evidence=(),
        proposed_status="RESOLVED_UPSTREAM" if resolves else None,
        proposed_close_reason=reason if resolves else None,  # type: ignore[arg-type]
    )


def _open_issue(
    number: int = 7, *, body: str | None = None, state: str = "open", pull_request: bool = False
) -> IssueSnapshot:
    text = f"found a defect\n\n{MARKER}\n" if body is None else body
    return IssueSnapshot(number=number, state=state, body=text, is_pull_request=pull_request)


class _Spy:
    """A fake that records that it was called; ``ok`` is the answer, ``error`` raises instead."""

    def __init__(self, answer: Any, *, error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.calls = 0

    def __call__(self, *args: Any) -> Any:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.answer


def _token_ok() -> _Spy:
    return _Spy(TokenDecision(True))


def close_handoff(handoff: Handoff, result: RedetectionResult, **kwargs: Any) -> Any:
    """``close_handoff`` with every gate satisfied unless a keyword overrides it. The environment
    and token are not defaulted: the kill switch and token tests state theirs."""
    reason = {"completed": "completed", "not planned": "not_planned"}.get(
        str(result.proposed_close_reason), "not_planned"
    )
    number = handoff.issue_ref.number if handoff.issue_ref is not None else 7
    kwargs.setdefault("permit", make_permit(handoff.repository, effect="issue_close"))
    if handoff.issue_ref is not None:
        kwargs.setdefault("approvals", closing_store(handoff, close_reason=reason))
    else:
        kwargs.setdefault("approvals", None)
    kwargs.setdefault("verify_token", _token_ok())
    kwargs.setdefault("issue_lookup", _Spy(_open_issue(number)))
    return _close_handoff(handoff, result, **kwargs)


def _armed(**extra: Any) -> dict[str, Any]:
    return {"token": "ghp_write", "environment": {AUTHORIZATION_VARIABLE: "1"}, **extra}


def _filed(number: int = 7) -> Handoff:
    return _handoff(status="FILED", issue_ref=_issue_ref(number))


def test_close_is_refused_without_the_gate_and_makes_no_call() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    verify, lookup = _token_ok(), _Spy(_open_issue())
    result = close_handoff(
        _filed(),
        _resolved(),
        token="ghp_write",
        environment={},
        write=write,
        verify_token=verify,
        issue_lookup=lookup,
    )
    assert write.calls == []
    assert (verify.calls, lookup.calls) == (0, 0)
    assert result.closed is False
    assert "kill switch engaged" in result.reason


def test_a_resolved_filed_handoff_is_closed_with_its_close_reason_as_github_state_reason() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    verify, lookup = _token_ok(), _Spy(_open_issue(7))
    result = close_handoff(
        _filed(7),
        _resolved("not planned"),
        **_armed(write=write, verify_token=verify, issue_lookup=lookup),
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"https://api.github.com/repos/{REPO}/issues/7"
    assert token == "ghp_write"
    assert payload == {"state": "closed", "state_reason": "not_planned"}
    assert (verify.calls, lookup.calls) == (1, 1)
    assert result.closed is True
    assert result.close_reason == "not planned"


def test_a_completed_resolution_maps_to_github_completed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    close_handoff(_filed(7), _resolved("completed"), **_armed(write=write))
    assert write.calls[0][2] == {"state": "closed", "state_reason": "completed"}


def test_a_handoff_that_still_fires_is_never_closed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(_filed(), _resolved(still_fires=True), **_armed(write=write))
    assert write.calls == []
    assert result.closed is False


def test_an_inconclusive_recheck_is_never_closed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(_filed(), _resolved(still_fires=None), **_armed(write=write))
    assert write.calls == []
    assert result.closed is False


def test_a_pending_handoff_is_never_closed_because_it_was_never_filed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(_handoff(), _resolved(), **_armed(write=write))
    assert write.calls == []
    assert result.closed is False


def test_a_failed_close_is_reported_as_an_error_never_raised() -> None:
    write = _RecordingCreate(status_code=500, body={"message": "boom"})
    result = close_handoff(_filed(), _resolved(), **_armed(write=write))
    assert result.closed is False
    assert result.error is True


def test_close_without_a_write_token_is_refused_and_makes_no_call() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _filed(), _resolved(), token=None, environment={AUTHORIZATION_VARIABLE: "1"}, write=write
    )
    assert write.calls == []
    assert result.closed is False
    assert "no write-scoped token" in result.reason


# --- the registry permit ------------------------------------------------------------------------


def test_close_cannot_be_called_without_a_permit() -> None:
    with pytest.raises(TypeError, match="permit"):
        _close_handoff(  # type: ignore[call-arg]
            _filed(),
            _resolved(),
            **_armed(approvals=None, verify_token=_token_ok(), issue_lookup=_Spy(_open_issue())),
        )


def test_a_permit_for_another_effect_or_repository_is_refused_before_anything_else() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    for wrong in (
        make_permit(REPO, effect="issue_filing"),
        make_permit(REPO, effect="readme_proposal"),
        make_permit("someone/else", effect="issue_close"),
    ):
        with pytest.raises(ValueError, match="permit"):
            close_handoff(_filed(), _resolved(), **_armed(write=write, permit=wrong))
    assert write.calls == []


# --- the owner's per-issue close approval -------------------------------------------------------


def _assert_refused_before_the_network(result: Any, write: _RecordingCreate, *spies: _Spy) -> None:
    assert result.closed is False
    assert result.error is False
    assert write.calls == []
    assert [spy.calls for spy in spies] == [0] * len(spies)


def test_a_missing_close_approval_is_refused_before_any_network_call() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    verify, lookup = _token_ok(), _Spy(_open_issue())
    result = close_handoff(
        _filed(),
        _resolved(),
        **_armed(
            write=write, approvals=MemoryApprovalStore(), verify_token=verify, issue_lookup=lookup
        ),
    )
    _assert_refused_before_the_network(result, write, verify, lookup)
    assert "no close approval record" in result.reason
    assert "ops/issue_close_approvals/" in result.reason


def test_no_approval_source_at_all_is_a_refusal() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(_filed(), _resolved(), **_armed(write=write, approvals=None))
    _assert_refused_before_the_network(result, write)
    assert "no close approval record source" in result.reason


def test_a_filing_approval_does_not_authorize_a_close() -> None:
    """Approving the *filing* of a handoff is a different act; it sits in another directory and is
    never consulted for a close."""
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed()
    result = close_handoff(
        handoff, _resolved(), **_armed(write=write, approvals=MemoryApprovalStore())
    )
    assert approving_store(handoff).records  # a filing approval exists...
    _assert_refused_before_the_network(result, write)  # ...and changes nothing


def test_an_expired_close_approval_is_refused() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed()
    long_ago = datetime.now(UTC) - timedelta(days=10)
    store = closing_store(
        handoff,
        close_reason="not_planned",
        approved_at=long_ago,
        expires_at=long_ago + timedelta(days=1),
    )
    verify, lookup = _token_ok(), _Spy(_open_issue())
    result = close_handoff(
        handoff,
        _resolved(),
        **_armed(write=write, approvals=store, verify_token=verify, issue_lookup=lookup),
    )
    _assert_refused_before_the_network(result, write, verify, lookup)
    assert "expired" in result.reason


def test_a_close_approval_for_another_issue_number_is_refused() -> None:
    """The owner approved closing #8; this handoff filed #7. The approval cannot be repointed."""
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed(7)
    verify, lookup = _token_ok(), _Spy(_open_issue(7))
    result = close_handoff(
        handoff,
        _resolved(),
        **_armed(
            write=write,
            approvals=closing_store(handoff, issue_number=8),
            verify_token=verify,
            issue_lookup=lookup,
        ),
    )
    _assert_refused_before_the_network(result, write, verify, lookup)
    assert "#8" in result.reason and "#7" in result.reason


@pytest.mark.parametrize(
    ("proved", "approved_for"),
    [("not planned", "completed"), ("completed", "not_planned")],
)
def test_a_close_approval_for_the_other_reason_is_refused(proved: str, approved_for: str) -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed()
    verify, lookup = _token_ok(), _Spy(_open_issue())
    result = close_handoff(
        handoff,
        _resolved(proved),
        **_armed(
            write=write,
            approvals=closing_store(handoff, close_reason=approved_for),
            verify_token=verify,
            issue_lookup=lookup,
        ),
    )
    _assert_refused_before_the_network(result, write, verify, lookup)
    assert "reason" in result.reason


def test_a_close_approval_whose_digest_no_longer_matches_the_handoff_is_refused() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed()
    store = closing_store(handoff, digest="sha256:" + "0" * 64)
    result = close_handoff(handoff, _resolved(), **_armed(write=write, approvals=store))
    _assert_refused_before_the_network(result, write)
    assert "digest mismatch" in result.reason


def test_a_close_approval_naming_another_repository_is_refused() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    handoff = _filed()
    store = closing_store(handoff, repository="someone-else/other-repo")
    result = close_handoff(handoff, _resolved(), **_armed(write=write, approvals=store))
    _assert_refused_before_the_network(result, write)
    assert "target mismatch" in result.reason


def test_a_run_bound_to_another_target_does_not_close() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _filed(), _resolved(), **_armed(write=write, expected_repository="someone-else/other")
    )
    _assert_refused_before_the_network(result, write)
    assert "target mismatch" in result.reason


# --- write-token provenance ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [Refusal.TOKEN_NOT_INSTALLATION, Refusal.TOKEN_WRONG_SCOPE, Refusal.TOKEN_UNVERIFIABLE],
)
def test_an_unverified_write_token_is_refused_before_the_issue_is_read_or_written(
    code: Refusal,
) -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    verify = _Spy(TokenDecision(False, code, "not this one"))
    lookup = _Spy(_open_issue())
    result = close_handoff(
        _filed(), _resolved(), **_armed(write=write, verify_token=verify, issue_lookup=lookup)
    )
    assert verify.calls == 1
    assert lookup.calls == 0
    assert write.calls == []
    assert result.closed is False
    assert str(code) in result.reason


def test_the_token_is_verified_for_the_exact_token_that_would_write() -> None:
    seen: list[str] = []

    def verify(token: str) -> TokenDecision:
        seen.append(token)
        return TokenDecision(True)

    close_handoff(
        _filed(),
        _resolved(),
        **_armed(write=_RecordingCreate(status_code=200, body={}), verify_token=verify),
    )
    assert seen == ["ghp_write"]


# --- the live issue must be one this system filed for this handoff ------------------------------


def test_an_issue_without_the_systems_marker_is_never_closed() -> None:
    """Issue #7 exists and is approved, but it is somebody else's: no fingerprint marker."""
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(_open_issue(7, body="a human wrote this issue, nothing from this system\n"))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert lookup.calls == 1
    assert write.calls == []
    assert result.closed is False
    assert "fingerprint marker" in result.reason


def test_an_issue_carrying_another_defects_marker_is_never_closed() -> None:
    other = "<!-- repository-presenter-defect: sha256:" + "d" * 64 + " -->"
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(_open_issue(7, body=f"another defect\n\n{other}\n"))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert write.calls == []
    assert "fingerprint marker" in result.reason


def test_a_pull_request_is_never_closed_as_an_issue() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(_open_issue(7, pull_request=True))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert write.calls == []
    assert "pull request" in result.reason


def test_an_already_closed_issue_is_left_alone() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(_open_issue(7, state="closed"))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert write.calls == []
    assert "already closed" in result.reason
    assert result.error is False


def test_an_issue_read_that_returns_a_different_number_is_refused() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(_open_issue(9))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert write.calls == []
    assert "#9" in result.reason


def test_an_inconclusive_issue_read_is_refused_not_assumed_fine() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    lookup = _Spy(None, error=RepositoryMetadataError("x/y: unreachable (timeout)"))
    result = close_handoff(_filed(7), _resolved(), **_armed(write=write, issue_lookup=lookup))
    assert write.calls == []
    assert result.closed is False
    assert "inconclusive" in result.reason


# --- the dry-run plan (the same gates, no write) -----------------------------------------------


def test_the_close_plan_reports_would_close_only_when_the_approval_verifies() -> None:
    handoff = _filed(7)
    ready = plan_close_gated(
        handoff,
        _resolved(),
        approvals=closing_store(handoff, close_reason="not_planned"),
        issue_lookup=_Spy(_open_issue(7)),
    )
    assert ready.ready and ready.verified
    assert (ready.issue_number, ready.state_reason) == (7, "not_planned")
    refused = plan_close_gated(
        handoff, _resolved(), approvals=MemoryApprovalStore(), issue_lookup=_Spy(_open_issue(7))
    )
    assert not refused.ready
    assert refused.refusal is not None and "no close approval record" in refused.refusal


def test_the_close_plan_without_a_read_credential_is_ready_but_not_verified() -> None:
    handoff = _filed(7)
    plan = plan_close_gated(
        handoff,
        _resolved(),
        approvals=closing_store(handoff, close_reason="not_planned"),
        issue_lookup=None,
    )
    assert plan.ready
    assert plan.verified is False
