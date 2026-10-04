"""``repository-presenter file-upstream-defects --file`` wiring: dry-run by default, and, even
with --file, writes nothing without the explicit authorization variable, a write-scoped token, and
a recheck confirming the defect still fires. No test here makes a live GitHub call -
``default_post`` and ``redetect`` are both monkeypatched fakes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.issues.approval import handoff_id
from repository_presenter.components.issues.file import AUTHORIZATION_VARIABLE
from repository_presenter.components.issues.model import load_handoff
from support import approval_text, monitor_registry_entry, write_registry_file

REPO_DIR = "aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp"
REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
FINGERPRINT = "b3df5761421b54a0e30d65eafab785a0c6ca8f3a13653e1dbb63a8488e170365"

HANDOFF_PAYLOAD = {
    "schema_version": 1,
    "repository": REPOSITORY,
    "source_revision": REVISION,
    "defect_fingerprint": f"sha256:{FINGERPRINT}",
    "triggering_check": {"id": "BC-02", "version": "3", "causal_stage": "EXTRACTING"},
    "evidence": [{"path": "src/x/NumberFormat.cpp", "detail": "trigraph '??/' is fatal"}],
    "claim": f"At revision {REVISION}, {REPOSITORY}'s own install_command:cmake is UNRESOLVED.",
    "suggested_issue_title": f"install_command:cmake is UNRESOLVED at {REVISION[:12]}",
    "suggested_issue_body": "repository-presenter's validation pipeline found this.\n",
    "status": "HANDOFF_PENDING",
    "issue_ref": None,
    "close_reason": None,
}


@pytest.fixture(autouse=True)
def _no_live_github(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every upstream call these tests reach is an injected fake: the marker lookup finds nothing
    by default, the recheck confirms the defect still fires, and any PATCH is recorded, never sent.
    A test that needs a different answer overrides the one name it cares about."""
    monkeypatch.setattr(cli, "find_issue_with_marker", lambda *a, **k: None)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setattr(cli, "default_patch", _RecordingCreate(status_code=200, body={}))
    monkeypatch.setattr(cli, "default_post", _RecordingCreate())


class _CommittedApprovals:
    """Stands in for ``GitApprovalStore`` (which reads committed files from a git ref): approves
    exactly the handoffs whose repository is in ``approved``, with the record text overridden per
    handoff id in ``overrides``. The git store itself is tested against real repositories in
    test_approval.py."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.approved = {REPOSITORY}
        self.overrides: dict[str, dict[str, Any]] = {}

    def read(self, identifier: str) -> str | None:
        for path in sorted((self.root / "evidence" / "upstream-defects").glob("*/*.json")):
            handoff = load_handoff(path)
            if handoff_id(handoff) == identifier and handoff.repository in self.approved:
                return approval_text(handoff, **self.overrides.get(identifier, {}))
        return None


@pytest.fixture(autouse=True)
def approvals(monkeypatch: pytest.MonkeyPatch) -> list[_CommittedApprovals]:
    """The approval store the CLI builds; the single entry is the one it created."""
    created: list[_CommittedApprovals] = []

    def factory(root: Path, ref: str = "HEAD") -> _CommittedApprovals:
        store = _CommittedApprovals(root)
        created.append(store)
        return store

    monkeypatch.setattr(cli, "GitApprovalStore", factory)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)
    return created


@pytest.fixture
def project_with_handoff(project: Path) -> Path:
    handoff_dir = project / "evidence" / "upstream-defects" / REPO_DIR
    handoff_dir.mkdir(parents=True)
    (handoff_dir / f"{FINGERPRINT}.json").write_text(
        json.dumps(HANDOFF_PAYLOAD, indent=2) + "\n", encoding="utf-8"
    )
    # `--file` writes only to a registry-`full` entry (core/registry/write_gate.py).
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode="full")])
    return project


class _RecordingCreate:
    def __init__(self, status_code: int = 201, body: object = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.status_code = status_code
        self.body = body if body is not None else {"number": 7, "html_url": "https://x/issues/7"}

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return self.status_code, self.body


def _fires_true(handoff: object) -> object:
    from repository_presenter.components.issues.redetect import RedetectionResult

    return RedetectionResult(
        repository=REPOSITORY,
        defect_fingerprint=f"sha256:{FINGERPRINT}",
        triggering_check_id="BC-02",
        checked_at="2026-09-27T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=True,
        note="still fires",
        fresh_evidence=(),
        proposed_status=None,
    )


def test_dry_run_without_file_flag_writes_nothing_and_says_so(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)

    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "WOULD-FILE" in out
    assert "WOULD-NOT-FILE" not in out
    assert "dry run" in out


def test_file_without_authorization_writes_nothing(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "kill switch engaged" in out
    assert AUTHORIZATION_VARIABLE in out


def test_file_authorized_with_token_and_confirmed_recheck_writes_and_updates_the_artifact(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert len(create.calls) == 1
    url, token, payload = create.calls[0]
    assert url == f"https://api.github.com/repos/{REPOSITORY}/issues"
    assert token == "fake-write-token-for-this-test-only"
    assert payload["title"] == HANDOFF_PAYLOAD["suggested_issue_title"]
    out = capsys.readouterr().out
    assert "filed=True" in out
    assert "now FILED" in out

    handoff_path = (
        project_with_handoff / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"
    )
    updated = load_handoff(handoff_path)
    assert updated.status == "FILED"
    assert updated.issue_ref is not None
    assert updated.issue_ref.number == 7
    assert updated.issue_ref.url == "https://x/issues/7"


def test_file_aborts_when_recheck_says_the_defect_no_longer_fires(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from repository_presenter.components.issues.redetect import RedetectionResult

    def fires_false(handoff: object) -> RedetectionResult:
        return RedetectionResult(
            repository=REPOSITORY,
            defect_fingerprint=f"sha256:{FINGERPRINT}",
            triggering_check_id="BC-02",
            checked_at="2026-09-27T00:00:00+00:00",
            checked_at_revision=REVISION,
            revision_drifted=False,
            still_fires=False,
            note="no longer fires: upstream fixed it",
            fresh_evidence=(),
            proposed_status=None,
        )

    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", fires_false)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    assert "no longer fires" in out
    handoff_path = (
        project_with_handoff / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"
    )
    assert load_handoff(handoff_path).status == "HANDOFF_PENDING"


def test_a_second_file_run_never_double_files_the_same_handoff(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(cli, "redetect", _fires_true)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    first = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )
    capsys.readouterr()
    second = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert first == EXIT_OK
    assert second == EXIT_OK
    assert len(create.calls) == 1
    out = capsys.readouterr().out
    assert "skip - status is 'FILED'" in out


def test_no_handoffs_on_record_is_reported_plainly(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["file-upstream-defects", "--root", str(project)])
    assert exit_code == EXIT_OK
    assert "no handoffs on record" in capsys.readouterr().out


def test_repo_filter_reports_plainly_when_nothing_matches(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--repo",
            "someone-else/unrelated",
        ]
    )
    assert exit_code == EXIT_OK
    assert "no handoff found for 'someone-else/unrelated'" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# The scheduled run: dedup across fresh checkouts, failure isolation, the gated close, and the
# matrix the workflow fans out over.
# ---------------------------------------------------------------------------

OTHER_REPO = "acme-org/second-repo"
OTHER_FINGERPRINT = "c" * 64


def _write_second_handoff(project: Path) -> None:
    payload = {
        **HANDOFF_PAYLOAD,
        "repository": OTHER_REPO,
        "defect_fingerprint": f"sha256:{OTHER_FINGERPRINT}",
        "suggested_issue_title": "second, independent defect",
        "suggested_issue_body": "independent finding\n",
    }
    directory = project / "evidence" / "upstream-defects" / "acme-org__second-repo"
    directory.mkdir(parents=True)
    (directory / f"{OTHER_FINGERPRINT}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _handoff_path(project: Path) -> Path:
    return project / "evidence" / "upstream-defects" / REPO_DIR / f"{FINGERPRINT}.json"


def _write_filed_handoff(project: Path, *, number: int = 7) -> None:
    payload = {
        **HANDOFF_PAYLOAD,
        "status": "FILED",
        "issue_ref": {"number": number, "url": f"https://x/issues/{number}"},
    }
    _handoff_path(project).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _resolved_not_planned(handoff: object) -> object:
    from repository_presenter.components.issues.redetect import RedetectionResult

    return RedetectionResult(
        repository=REPOSITORY,
        defect_fingerprint=f"sha256:{FINGERPRINT}",
        triggering_check_id="BC-02",
        checked_at="2026-10-04T00:00:00+00:00",
        checked_at_revision=REVISION,
        revision_drifted=False,
        still_fires=False,
        note="no longer fires",
        fresh_evidence=(),
        proposed_status="RESOLVED_UPSTREAM",
        proposed_close_reason="not planned",
    )


def test_a_second_run_from_a_fresh_checkout_files_nothing_when_the_upstream_issue_exists(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from repository_presenter.components.issues.model import IssueRef

    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setattr(
        cli, "find_issue_with_marker", lambda *a, **k: _Found(number=7, url="https://x/issues/7")
    )
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert create.calls == []
    assert "already filed" in capsys.readouterr().out
    updated = load_handoff(_handoff_path(project_with_handoff))
    assert updated.status == "FILED"
    assert updated.issue_ref == IssueRef(number=7, url="https://x/issues/7")


def _approve(
    monkeypatch: pytest.MonkeyPatch, *repositories: str, **overrides: dict[str, Any]
) -> None:
    """Make the CLI's approval store approve exactly ``repositories``."""
    original_factory = cli.GitApprovalStore

    def factory(root: Path, ref: str = "HEAD") -> _CommittedApprovals:
        store = original_factory(root, ref)
        store.approved = set(repositories)
        store.overrides = dict(overrides)
        return store

    monkeypatch.setattr(cli, "GitApprovalStore", factory)


def _open_gates(monkeypatch: pytest.MonkeyPatch, create: _RecordingCreate) -> None:
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")


def test_a_run_files_only_for_the_repository_it_is_bound_to(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both handoffs are approved, but a run bound to one target (a matrix leg) never touches the
    other one's issue tracker, whatever the artifacts on disk say."""
    _write_second_handoff(project_with_handoff)
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)
    _approve(monkeypatch, REPOSITORY, OTHER_REPO)

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert [url for url, _, _ in create.calls] == [
        f"https://api.github.com/repos/{REPOSITORY}/issues"
    ]
    other = project_with_handoff / "evidence" / "upstream-defects" / "acme-org__second-repo"
    assert load_handoff(other / f"{OTHER_FINGERPRINT}.json").status == "HANDOFF_PENDING"
    assert "filed=True" in capsys.readouterr().out


def test_a_failed_filing_is_reported_and_leaves_the_artifact_pending(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = _RecordingCreate(status_code=500, body={"message": "boom"})
    _open_gates(monkeypatch, failing)

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert len(failing.calls) == 1
    assert exit_code != EXIT_OK
    assert load_handoff(_handoff_path(project_with_handoff)).status == "HANDOFF_PENDING"


def test_file_requires_a_repo_binding_and_writes_nothing_without_one(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff), "--file"])

    assert exit_code == EXIT_USAGE
    assert create.calls == []


def test_the_kill_switch_and_token_without_an_approval_file_nothing(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The incident this guards: the repository variable set, a token minted, nothing approved."""
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)
    _approve(monkeypatch)

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert create.calls == []
    assert "no approval record" in capsys.readouterr().out
    assert load_handoff(_handoff_path(project_with_handoff)).status == "HANDOFF_PENDING"


def test_a_handoff_edited_after_its_approval_is_not_filed(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)
    identifier = f"aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp__{FINGERPRINT}"
    _approve(monkeypatch, REPOSITORY, **{identifier: {"digest": "sha256:" + "0" * 64}})

    exit_code = main(
        [
            "file-upstream-defects",
            "--root",
            str(project_with_handoff),
            "--file",
            "--repo",
            REPOSITORY,
        ]
    )

    assert exit_code == EXIT_OK
    assert create.calls == []
    assert "approval digest mismatch" in capsys.readouterr().out


def test_count_writable_counts_only_approved_pending_handoffs(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    base = ["file-upstream-defects", "--root", str(project_with_handoff), "--count-writable"]
    assert main([*base, "--repo", REPOSITORY]) == EXIT_OK
    assert capsys.readouterr().out.strip() == "1"
    assert main([*base, "--repo", OTHER_REPO]) == EXIT_OK
    assert capsys.readouterr().out.strip() == "0"
    assert main([*base, "--repo", "nobody/nothing"]) == EXIT_OK
    assert capsys.readouterr().out.strip() == "0"


def test_a_resolved_filed_handoff_is_closed_with_its_close_reason(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_filed_handoff(project_with_handoff)
    patch = _RecordingCreate(status_code=200, body={"state": "closed"})
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "redetect", _resolved_not_planned)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_ISSUES_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(["redetect-upstream-defects", "--root", str(project_with_handoff), "--close"])

    assert exit_code == EXIT_OK
    assert len(patch.calls) == 1
    url, token, payload = patch.calls[0]
    assert url == f"https://api.github.com/repos/{REPOSITORY}/issues/7"
    assert token == "fake-write-token-for-this-test-only"
    assert payload == {"state": "closed", "state_reason": "not_planned"}
    updated = load_handoff(_handoff_path(project_with_handoff))
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "not planned"
    assert updated.issue_ref is not None and updated.issue_ref.number == 7
    assert "fake-write-token-for-this-test-only" not in capsys.readouterr().out


def test_close_without_the_gate_makes_no_call_and_says_what_it_would_close(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_filed_handoff(project_with_handoff)
    patch = _RecordingCreate(status_code=200, body={"state": "closed"})
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "redetect", _resolved_not_planned)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(["redetect-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    assert patch.calls == []
    out = capsys.readouterr().out
    assert "would close #7" in out
    assert load_handoff(_handoff_path(project_with_handoff)).status == "FILED"


def test_the_dry_run_reports_each_handoff_with_its_verdict_and_reason(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    create = _RecordingCreate()
    monkeypatch.setattr(cli, "default_post", create)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")

    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    assert create.calls == []
    out = capsys.readouterr().out
    approved_line = next(line for line in out.splitlines() if REPOSITORY in line)
    unapproved_line = next(line for line in out.splitlines() if OTHER_REPO in line)
    assert "WOULD-FILE" in approved_line
    assert "WOULD-NOT-FILE" in unapproved_line
    assert "no approval record" in unapproved_line
    assert "second, independent defect" in out
    assert f"ops/issue_approvals/acme-org__second-repo__{OTHER_FINGERPRINT}.json" in out
    assert "evidence_digest sha256:" in out


def test_the_dry_run_says_the_kill_switch_is_off_instead_of_promising_a_filing(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["file-upstream-defects", "--root", str(project_with_handoff)])

    assert exit_code == EXIT_OK
    out = capsys.readouterr().out
    assert f"kill switch {AUTHORIZATION_VARIABLE} = OFF" in out
    assert "WOULD-NOT-FILE" in out
    assert "WOULD-FILE" not in out.replace("WOULD-NOT-FILE", "")


def test_issue_targets_lists_each_repository_with_pending_or_filed_handoffs_as_json(
    project_with_handoff: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_second_handoff(project_with_handoff)
    exit_code = main(["issue-targets", "--root", str(project_with_handoff)])
    assert exit_code == EXIT_OK
    targets = json.loads(capsys.readouterr().out)
    assert targets == [
        {"repo": OTHER_REPO, "owner": "acme-org", "name": "second-repo"},
        {"repo": REPOSITORY, "owner": "aspose-cells-foss", "name": "Aspose.Cells-FOSS-for-Cpp"},
    ]


def test_issue_targets_is_an_empty_list_when_nothing_is_actionable(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["issue-targets", "--root", str(project)]) == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []


class _Found:
    """Stands in for a ``CreatedIssue`` returned by the upstream marker lookup."""

    def __init__(self, *, number: int, url: str) -> None:
        self.number = number
        self.url = url


# ---------------------------------------------------------------------------
# The two independent gates on the filing path: the registry write gate (mode `full` -> a
# `WritePermit`) and the per-handoff approval record. Each alone is insufficient, so removing
# either one makes exactly one of these tests fail.
# ---------------------------------------------------------------------------


def _file_args(project: Path) -> list[str]:
    return ["file-upstream-defects", "--root", str(project), "--file", "--repo", REPOSITORY]


def _set_registry_mode(project: Path, mode: str) -> None:
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode=mode)])


def test_end_to_end_a_handoff_is_filed_only_when_all_four_gates_hold(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Registry mode full + permit, an approval record that verifies against the handoff digest, the
    kill switch on, and a write token: exactly one issue is filed, and the handoff is recorded."""
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)

    assert main(_file_args(project_with_handoff)) == EXIT_OK

    assert [url for url, _, _ in create.calls] == [
        f"https://api.github.com/repos/{REPOSITORY}/issues"
    ]
    assert load_handoff(_handoff_path(project_with_handoff)).status == "FILED"
    assert "filed=True" in capsys.readouterr().out


@pytest.mark.parametrize("mode", ["dry_run", "disabled"])
def test_end_to_end_an_approved_handoff_is_not_filed_when_the_registry_mode_is_not_full(
    project_with_handoff: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    """Approval record present and verifying, kill switch on, token present - and still nothing:
    the registry write gate alone refuses. Fails if the permit check is removed."""
    _set_registry_mode(project_with_handoff, mode)
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)

    assert main(_file_args(project_with_handoff)) == EXIT_OK

    assert create.calls == []
    assert load_handoff(_handoff_path(project_with_handoff)).status == "HANDOFF_PENDING"
    out = capsys.readouterr().out
    assert "not filed (registry_" in out


def test_end_to_end_a_full_mode_handoff_is_not_filed_without_its_approval_record(
    project_with_handoff: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    approvals: list[_CommittedApprovals],
) -> None:
    """Registry mode full and a permit, kill switch on, token present - and still nothing: no
    approval record. Fails if the approval check is removed."""
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)
    _approve(monkeypatch)  # approves no repository

    assert main(_file_args(project_with_handoff)) == EXIT_OK

    assert create.calls == []
    assert load_handoff(_handoff_path(project_with_handoff)).status == "HANDOFF_PENDING"


def test_end_to_end_a_full_mode_approved_handoff_is_not_filed_with_the_kill_switch_off(
    project_with_handoff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    create = _RecordingCreate()
    _open_gates(monkeypatch, create)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE)

    assert main(_file_args(project_with_handoff)) == EXIT_OK

    assert create.calls == []


def test_the_filing_effect_cannot_be_reached_without_a_matching_permit(
    project_with_handoff: Path,
) -> None:
    """``file_handoff`` takes the registry permit as a required argument and checks it names this
    effect and this repository."""
    from repository_presenter.components.issues.file import file_handoff
    from support import make_permit

    handoff = load_handoff(_handoff_path(project_with_handoff))
    with pytest.raises(TypeError, match="permit"):
        file_handoff(handoff, token="t", environment={AUTHORIZATION_VARIABLE: "1"})  # type: ignore[call-arg]
    for wrong in (
        make_permit("someone/else", effect="issue_filing"),
        make_permit(REPOSITORY, effect="readme_proposal"),
    ):
        with pytest.raises(ValueError, match="permit"):
            file_handoff(
                handoff, token="t", environment={AUTHORIZATION_VARIABLE: "1"}, permit=wrong
            )
