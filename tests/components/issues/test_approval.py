"""Per-handoff owner approval for upstream issue filing (``components/issues/approval.py``).

Every refusal here is a negative control for the incident this module closes: a single repository
variable used to authorize filing every pending handoff into an Aspose repository. No test makes a
live GitHub call - the issue-creating function is an injected recording fake, and the git store is
exercised against disposable local repositories.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.issues.approval import (
    MAX_APPROVAL_LIFETIME,
    ApprovalProvenanceError,
    GitApprovalStore,
    evidence_digest,
    handoff_id,
    parse_approval,
    verify_approval,
)
from repository_presenter.components.issues.file import (
    AUTHORIZATION_VARIABLE,
    file_handoff,
    plan_filing,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
)
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.git_safety.git import run_git
from support import (
    MemoryApprovalStore,
    approval_text,
    approving_store,
    commit_all,
    committed_approval_path,
    init_git_repository,
)

REPO = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
REVISION = "bf0f1e7a6d29ca9e14de576fe3ff1aa49ddbaf11"
FINGERPRINT = "sha256:ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a"
KILL_SWITCH_ON = {AUTHORIZATION_VARIABLE: "1"}
NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _handoff(**changes: Any) -> Handoff:
    base = Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-02", version="2", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="pyproject.toml", detail="bad build-backend"),),
        claim=f"At revision {REVISION}, {REPO} cannot be built.",
        suggested_issue_title="build-backend does not exist",
        suggested_issue_body="## Summary\n\nbroken.\n",
        status="HANDOFF_PENDING",
        issue_ref=None,
    )
    return replace(base, **changes)


class _RecordingCreate:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return 201, {"number": 9, "html_url": "https://github.com/x/y/issues/9"}


def _still_fires() -> RedetectionResult:
    return RedetectionResult(
        repository=REPO,
        defect_fingerprint=FINGERPRINT,
        triggering_check_id="BC-02",
        checked_at=NOW.isoformat(),
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=True,
        note="still fires",
        fresh_evidence=(),
        proposed_status=None,
    )


def _no_network() -> Any:
    raise AssertionError("a refused filing must make no upstream lookup at all")


def _file(
    handoff: Handoff,
    store: MemoryApprovalStore | None,
    *,
    environment: dict[str, str] | None = None,
    create: _RecordingCreate | None = None,
    **extra: Any,
) -> Any:
    return file_handoff(
        handoff,
        token="fake-write-token",
        environment=KILL_SWITCH_ON if environment is None else environment,
        create=create or _RecordingCreate(),
        approvals=store,
        now=lambda: NOW,
        **extra,
    )


def _fresh(handoff: Handoff, **overrides: Any) -> MemoryApprovalStore:
    overrides.setdefault("approved_at", NOW - timedelta(hours=1))
    return approving_store(handoff, **overrides)


# ---------------------------------------------------------------------------
# The digest
# ---------------------------------------------------------------------------


def test_the_digest_covers_everything_that_would_be_filed_and_where() -> None:
    base = evidence_digest(_handoff())
    assert base == evidence_digest(_handoff())
    for changed in (
        _handoff(suggested_issue_body="different body"),
        _handoff(suggested_issue_title="different title"),
        _handoff(claim="a different claim"),
        _handoff(source_revision="0" * 40),
        _handoff(repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python"),
        _handoff(evidence=(EvidenceEntry(path="pyproject.toml", detail="other"),)),
        _handoff(triggering_check=TriggeringCheck("BC-02", "3", "EXTRACTING")),
    ):
        assert evidence_digest(changed) != base


def test_lifecycle_fields_are_not_part_of_the_digest() -> None:
    filed = _handoff(status="FILED", issue_ref=IssueRef(number=1, url="https://x/issues/1"))
    assert evidence_digest(filed) == evidence_digest(_handoff())


def test_the_handoff_id_names_owner_name_and_fingerprint() -> None:
    assert (
        handoff_id(_handoff())
        == f"aspose-html-foss__Aspose.HTML-FOSS-for-Python__{FINGERPRINT[7:]}"
    )


# ---------------------------------------------------------------------------
# verify_approval: record shape
# ---------------------------------------------------------------------------


def test_a_valid_record_is_approved() -> None:
    handoff = _handoff()
    verdict = verify_approval(handoff, _fresh(handoff), now=lambda: NOW)
    assert verdict.approved is True
    assert verdict.record is not None
    assert verdict.record.approver == "owner-login"


def _edit(**changes: Any) -> Any:
    """A mutation of the record text: set (or, for ``None``, delete) the named fields."""

    def mutate(text: str) -> str:
        record = json.loads(text)
        for key, value in changes.items():
            if value is None:
                del record[key]
            else:
                record[key] = value
        return json.dumps(record)

    return mutate


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (_edit(approver="github-actions[bot]"), "bot"),
        (_edit(approver=""), "approver"),
        (_edit(extra="field"), "unknown field"),
        (_edit(approved_at=None), "missing field"),
        (lambda t: "[1, 2]", "mapping"),
        (_edit(evidence_digest="md5:abc"), "evidence_digest"),
        (lambda t: "{not json", "JSON"),
        (_edit(repository="../evil"), "repository"),
        (_edit(approved_at="2026-10-05T10:00:00"), "timezone"),
        (_edit(approved_at=20261005), "timestamp"),
        (_edit(expires_at="soon"), "timestamp"),
    ],
)
def test_a_malformed_record_is_refused(mutation: Any, expected: str) -> None:
    handoff = _handoff()
    store = MemoryApprovalStore(
        {
            handoff_id(handoff): mutation(
                approval_text(handoff, approved_at=NOW - timedelta(hours=1))
            )
        }
    )
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert expected in verdict.reason


def test_a_standing_approval_longer_than_the_maximum_window_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, expires_at=NOW + MAX_APPROVAL_LIFETIME + timedelta(days=1))
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "standing authorization" in verdict.reason


def test_an_expiry_before_the_approval_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, expires_at=NOW - timedelta(days=3))
    assert verify_approval(handoff, store, now=lambda: NOW).approved is False


def test_a_z_suffixed_timestamp_parses() -> None:
    handoff = _handoff()
    text = approval_text(handoff, approved_at=NOW, expires_at=NOW + timedelta(days=3)).replace(
        "+00:00", "Z"
    )
    assert parse_approval(text).expires_at == datetime(2026, 10, 8, 12, tzinfo=UTC)


# ---------------------------------------------------------------------------
# verify_approval: the four required negative controls plus target binding
# ---------------------------------------------------------------------------


def test_no_record_is_refused() -> None:
    verdict = verify_approval(_handoff(), MemoryApprovalStore(), now=lambda: NOW)
    assert verdict.approved is False
    assert "no approval record" in verdict.reason


def test_a_mismatched_digest_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, digest="sha256:" + "0" * 64)
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "approval digest mismatch" in verdict.reason


def test_a_handoff_changed_after_approval_needs_a_fresh_approval() -> None:
    original = _handoff()
    approved_store = _fresh(original)
    edited = _handoff(suggested_issue_body="## Summary\n\nsomething the owner never read\n")
    approved_store.records[handoff_id(edited)] = approved_store.records[handoff_id(original)]
    verdict = verify_approval(edited, approved_store, now=lambda: NOW)
    assert verdict.approved is False
    assert "digest mismatch" in verdict.reason


def test_an_expired_record_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(
        handoff, approved_at=NOW - timedelta(days=10), expires_at=NOW - timedelta(days=3)
    )
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "expired" in verdict.reason


def test_a_record_dated_in_the_future_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, approved_at=NOW + timedelta(days=1), expires_at=NOW + timedelta(days=2))
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "future" in verdict.reason


def test_a_record_approving_another_repository_is_refused() -> None:
    handoff = _handoff()
    store = _fresh(handoff, repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python")
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "target mismatch" in verdict.reason


def test_a_record_filed_under_another_handoffs_id_is_refused() -> None:
    handoff = _handoff()
    other = _handoff(defect_fingerprint="sha256:" + "1" * 64)
    store = MemoryApprovalStore(
        {handoff_id(handoff): approval_text(other, approved_at=NOW - timedelta(hours=1))}
    )
    verdict = verify_approval(handoff, store, now=lambda: NOW)
    assert verdict.approved is False
    assert "different handoff" in verdict.reason


def test_an_untrusted_store_is_refused() -> None:
    class Untrusted:
        def read(self, identifier: str) -> str | None:
            raise ApprovalProvenanceError("the record was authored or committed by a bot identity")

    verdict = verify_approval(_handoff(), Untrusted(), now=lambda: NOW)
    assert verdict.approved is False
    assert "provenance" in verdict.reason


# ---------------------------------------------------------------------------
# file_handoff: refusals make no write and no upstream call
# ---------------------------------------------------------------------------


def _refused(result: Any, create: _RecordingCreate, fragment: str) -> None:
    assert create.calls == []
    assert result.filed is False
    assert result.issue_ref is None
    assert fragment in result.reason


def test_no_record_refuses_filing_even_with_the_kill_switch_on_and_a_token() -> None:
    create = _RecordingCreate()
    result = _file(
        _handoff(), MemoryApprovalStore(), create=create, existing=_no_network, recheck=_no_network
    )
    _refused(result, create, "no approval record")


def test_a_mismatched_digest_refuses_filing() -> None:
    handoff = _handoff()
    create = _RecordingCreate()
    result = _file(
        handoff, _fresh(handoff, digest="sha256:" + "f" * 64), create=create, existing=_no_network
    )
    _refused(result, create, "approval digest mismatch")


def test_an_expired_record_refuses_filing() -> None:
    handoff = _handoff()
    store = _fresh(
        handoff, approved_at=NOW - timedelta(days=9), expires_at=NOW - timedelta(minutes=1)
    )
    create = _RecordingCreate()
    _refused(_file(handoff, store, create=create, existing=_no_network), create, "expired")


@pytest.mark.parametrize(
    "environment", [{}, {AUTHORIZATION_VARIABLE: "0"}, {AUTHORIZATION_VARIABLE: ""}]
)
def test_the_kill_switch_off_refuses_filing_despite_a_valid_record(
    environment: dict[str, str],
) -> None:
    handoff = _handoff()
    create = _RecordingCreate()
    result = _file(handoff, _fresh(handoff), environment=environment, create=create)
    _refused(result, create, "kill switch engaged")
    assert result.authorized is False


def test_no_approval_source_at_all_refuses_filing() -> None:
    create = _RecordingCreate()
    result = _file(_handoff(), None, create=create)
    _refused(result, create, "no approval record source")


def test_the_kill_switch_alone_never_authorizes_a_filing() -> None:
    """The incident: the variable set, a token present, nothing approved -> nothing filed."""
    create = _RecordingCreate()
    result = file_handoff(
        _handoff(), token="fake-write-token", environment=KILL_SWITCH_ON, create=create
    )
    _refused(result, create, "no approval record source")


def test_a_valid_record_files_through_the_injected_client() -> None:
    handoff = _handoff()
    create = _RecordingCreate()
    result = _file(
        handoff,
        _fresh(handoff),
        create=create,
        existing=lambda: None,
        recheck=_still_fires,
        expected_repository=REPO,
    )
    assert result.filed is True
    assert result.reason == "filed"
    assert result.issue_ref == IssueRef(number=9, url="https://github.com/x/y/issues/9")
    assert len(create.calls) == 1
    url, token, payload = create.calls[0]
    assert url == f"https://api.github.com/repos/{REPO}/issues"
    assert token == "fake-write-token"
    assert payload["title"] == handoff.suggested_issue_title


def test_one_handoffs_approval_does_not_authorize_another() -> None:
    approved = _handoff()
    other = _handoff(
        repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python",
        defect_fingerprint="sha256:" + "2" * 64,
    )
    store = _fresh(approved)
    create = _RecordingCreate()
    _refused(_file(other, store, create=create), create, "no approval record")


# ---------------------------------------------------------------------------
# The target is the handoff's own recorded repository
# ---------------------------------------------------------------------------


def test_filing_refuses_a_run_operating_on_another_repository() -> None:
    handoff = _handoff()
    create = _RecordingCreate()
    result = _file(
        handoff,
        _fresh(handoff),
        create=create,
        expected_repository="aspose-tex-foss/Aspose.TeX-FOSS-for-Python",
    )
    _refused(result, create, "target mismatch")


@pytest.mark.parametrize(
    "repository",
    ["aspose-html-foss", "a/b/c", "../evil/repo", "owner/..", "owner/na me", "/owner/name", ""],
)
def test_a_malformed_recorded_target_is_refused(repository: str) -> None:
    handoff = _handoff(repository=repository)
    create = _RecordingCreate()
    store = MemoryApprovalStore({"x": "y"})
    result = _file(handoff, store, create=create)
    assert create.calls == []
    assert result.filed is False


def test_the_post_goes_only_to_the_approved_repository() -> None:
    handoff = _handoff()
    create = _RecordingCreate()
    _file(handoff, _fresh(handoff), create=create)
    assert {url for url, _, _ in create.calls} == {f"https://api.github.com/repos/{REPO}/issues"}


# ---------------------------------------------------------------------------
# plan_filing (the dry run's source of truth)
# ---------------------------------------------------------------------------


def test_the_plan_for_an_unapproved_handoff_names_the_file_to_add_and_the_digest() -> None:
    handoff = _handoff()
    plan = plan_filing(handoff, approvals=MemoryApprovalStore(), now=lambda: NOW)
    assert plan.ready is False
    assert plan.approval_refused is True
    assert plan.handoff_id == handoff_id(handoff)
    assert plan.evidence_digest == evidence_digest(handoff)
    assert plan.refusal is not None
    assert "no approval record" in plan.refusal


def test_the_plan_for_an_approved_handoff_is_ready_and_makes_no_lookup_for_an_unapproved_one() -> (
    None
):
    handoff = _handoff()
    assert plan_filing(handoff, approvals=_fresh(handoff), now=lambda: NOW).ready is True
    plan = plan_filing(
        handoff, approvals=MemoryApprovalStore(), existing=_no_network, now=lambda: NOW
    )
    assert plan.ready is False


# ---------------------------------------------------------------------------
# GitApprovalStore: a record must be committed, human-authored, and in the run's own commit
# ---------------------------------------------------------------------------


def _commit_record(
    repo: Path, handoff: Handoff, *, name: str = "Owner", email: str = "owner@example.com"
) -> str:
    target = repo / committed_approval_path(handoff)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        approval_text(handoff, approved_at=NOW - timedelta(hours=1)), encoding="utf-8"
    )
    assert run_git(["config", "user.name", name], cwd=repo).returncode == 0
    assert run_git(["config", "user.email", email], cwd=repo).returncode == 0
    return commit_all(repo, "approve a handoff")


def test_a_committed_human_record_is_read_and_verified(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is True


def test_a_record_that_exists_only_in_the_working_tree_is_invisible(tmp_path: Path) -> None:
    """A file a step wrote during the run is not approval: only the checked-out commit is."""
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    target = repo / committed_approval_path(handoff)
    target.parent.mkdir(parents=True)
    target.write_text(
        approval_text(handoff, approved_at=NOW - timedelta(hours=1)), encoding="utf-8"
    )
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "no approval record" in verdict.reason


def test_a_record_committed_after_the_trigger_commit_is_invisible(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    trigger = run_git(["rev-parse", "HEAD"], cwd=repo).stdout.strip()
    handoff = _handoff()
    _commit_record(repo, handoff)
    assert (
        verify_approval(handoff, GitApprovalStore(repo, trigger), now=lambda: NOW).approved is False
    )
    assert (
        verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW).approved is True
    )


def test_an_edit_in_the_working_tree_does_not_change_what_was_approved(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    path = repo / committed_approval_path(handoff)
    path.write_text(
        approval_text(handoff, digest="sha256:" + "a" * 64, approved_at=NOW - timedelta(hours=1)),
        encoding="utf-8",
    )
    assert (
        verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW).approved is True
    )


@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com"),
        ("CI", "bot[bot]@x.io"),
    ],
)
def test_a_bot_authored_record_is_refused(tmp_path: Path, name: str, email: str) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff, name=name, email=email)
    verdict = verify_approval(handoff, GitApprovalStore(repo, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "provenance" in verdict.reason
    assert "bot" in verdict.reason


def test_a_shallow_clone_cannot_prove_who_introduced_the_record(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    clone = tmp_path / "clone"
    result = run_git(["clone", "-q", "--depth", "1", repo.as_uri(), str(clone)], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    verdict = verify_approval(handoff, GitApprovalStore(clone, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False
    assert "shallow" in verdict.reason


def test_a_bad_ref_or_a_non_repository_fails_closed(tmp_path: Path) -> None:
    handoff = _handoff()
    with pytest.raises(ApprovalProvenanceError):
        GitApprovalStore(tmp_path, "--output=evil")
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    verdict = verify_approval(handoff, GitApprovalStore(plain, "HEAD"), now=lambda: NOW)
    assert verdict.approved is False


def test_end_to_end_a_committed_record_files_and_a_changed_handoff_does_not(tmp_path: Path) -> None:
    repo = init_git_repository(tmp_path / "control")
    handoff = _handoff()
    _commit_record(repo, handoff)
    store = GitApprovalStore(repo, "HEAD")
    create = _RecordingCreate()
    result = file_handoff(
        handoff,
        token="fake-write-token",
        environment=KILL_SWITCH_ON,
        create=create,
        approvals=store,
        now=lambda: NOW,
        expected_repository=REPO,
    )
    assert result.filed is True
    assert len(create.calls) == 1

    changed = replace(handoff, suggested_issue_body="edited after approval")
    again = _RecordingCreate()
    refused = file_handoff(
        changed,
        token="fake-write-token",
        environment=KILL_SWITCH_ON,
        create=again,
        approvals=store,
        now=lambda: NOW,
    )
    assert refused.filed is False
    assert again.calls == []
    assert "approval digest mismatch" in refused.reason
