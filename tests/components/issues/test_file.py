"""Phase 3 file: gated ``POST /repos/{owner}/{repo}/issues``. Every test injects a fake ``create``
function - no test here, or anywhere in this suite, makes a live GitHub call. The point of this
file is the gate itself: an unauthorized, under-credentialed, already-filed, or recheck-failed
handoff must never reach ``create``."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from repository_presenter.components.issues.file import (
    AUTHORIZATION_VARIABLE,
    FileResult,
    close_handoff,
    file_handoff,
    plan_filing,
    write_authorized,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.errors import RepositoryMetadataError

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
# close_handoff: the gated close of a FILED handoff that redetection proved resolved
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


def test_close_is_refused_without_the_gate_and_makes_no_call() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref()),
        _resolved(),
        token="ghp_write",
        environment={},
        write=write,
    )
    assert write.calls == []
    assert result.closed is False
    assert "not authorized" in result.reason


def test_a_resolved_filed_handoff_is_closed_with_its_close_reason_as_github_state_reason() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref(7)),
        _resolved("not planned"),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert len(write.calls) == 1
    url, token, payload = write.calls[0]
    assert url == f"https://api.github.com/repos/{REPO}/issues/7"
    assert token == "ghp_write"
    assert payload == {"state": "closed", "state_reason": "not_planned"}
    assert result.closed is True
    assert result.close_reason == "not planned"


def test_a_completed_resolution_maps_to_github_completed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref(7)),
        _resolved("completed"),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert write.calls[0][2] == {"state": "closed", "state_reason": "completed"}


def test_a_handoff_that_still_fires_is_never_closed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref()),
        _resolved(still_fires=True),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert write.calls == []
    assert result.closed is False


def test_an_inconclusive_recheck_is_never_closed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref()),
        _resolved(still_fires=None),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert write.calls == []
    assert result.closed is False


def test_a_pending_handoff_is_never_closed_because_it_was_never_filed() -> None:
    write = _RecordingCreate(status_code=200, body={"state": "closed"})
    result = close_handoff(
        _handoff(),
        _resolved(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert write.calls == []
    assert result.closed is False


def test_a_failed_close_is_reported_as_an_error_never_raised() -> None:
    write = _RecordingCreate(status_code=500, body={"message": "boom"})
    result = close_handoff(
        _handoff(status="FILED", issue_ref=_issue_ref()),
        _resolved(),
        token="ghp_write",
        environment={AUTHORIZATION_VARIABLE: "1"},
        write=write,
    )
    assert result.closed is False
    assert result.error is True
