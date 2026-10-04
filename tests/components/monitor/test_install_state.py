"""Per-owner GitHub App installation state (G7-W06): a missing installation is a notice, not a
failure, and the run stays red only when no owner at all can be observed.

No test reaches GitHub. The mint outcome is an input string, exactly as the workflow passes
``steps.app-token.outcome``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.monitor.install_state import (
    INSTALLED,
    NOT_INSTALLED,
    InstallStateError,
    record_state,
    summarize_installs,
    write_state,
)

HTML = "aspose-html-foss"
PDF = "aspose-pdf-foss"
HTML_REPOS = "Aspose.HTML-FOSS-for-Python"
PDF_REPOS = "Aspose.PDF-FOSS-for-Go"


def _record(directory: Path, owner: str, outcome: str, repositories: str) -> None:
    write_state(
        record_state(owner, outcome, repositories),
        directory / "runs" / "monitor" / f"install-{owner}.json",
    )


def test_a_successful_mint_is_installed_with_no_detail() -> None:
    state = record_state(PDF, "success", PDF_REPOS)

    assert (state.state, state.detail) == (INSTALLED, None)


def test_a_failed_mint_names_the_owner_the_app_and_the_missing_install() -> None:
    state = record_state(HTML, "failure", HTML_REPOS)

    assert state.state == NOT_INSTALLED
    assert state.detail is not None
    assert f"'{HTML}'" in state.detail
    assert "'repository-presenter' (id 5092474)" in state.detail
    assert HTML_REPOS in state.detail
    assert "not a failure" in state.detail


def test_an_unrecognized_mint_outcome_is_an_internal_error_never_a_notice() -> None:
    # Negative control: 'cancelled' or an empty outcome means the workflow wiring is broken, and
    # must fail loudly rather than be recorded as a quiet "not installed".
    with pytest.raises(InstallStateError):
        record_state(HTML, "cancelled", HTML_REPOS)
    with pytest.raises(InstallStateError):
        record_state(HTML, "", HTML_REPOS)


def test_one_missing_install_among_observed_owners_is_a_notice_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _record(tmp_path, PDF, "success", PDF_REPOS)
    _record(tmp_path, HTML, "failure", HTML_REPOS)

    code = main(["monitor-install-summary", str(tmp_path / "runs" / "monitor")])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert f"::notice title=GitHub App not installed on {HTML}::" in captured.out
    assert f"| {HTML} | {NOT_INSTALLED} |" in captured.out
    assert f"| {PDF} | {INSTALLED} |" in captured.out


def test_the_summary_is_appended_to_the_step_summary_file(tmp_path: Path) -> None:
    _record(tmp_path, PDF, "success", PDF_REPOS)
    step_summary = tmp_path / "summary.md"

    code = main(
        [
            "monitor-install-summary",
            str(tmp_path / "runs" / "monitor"),
            "--summary",
            str(step_summary),
        ]
    )

    assert code == EXIT_OK
    assert "## Monitor installation coverage" in step_summary.read_text(encoding="utf-8")


def test_no_owner_observable_is_red_because_the_credentials_are_the_likely_cause(
    tmp_path: Path,
) -> None:
    # Negative control: when every mint fails, a notice per owner would hide a broken App key.
    _record(tmp_path, HTML, "failure", HTML_REPOS)
    _record(tmp_path, PDF, "failure", PDF_REPOS)

    result = summarize_installs(tmp_path / "runs" / "monitor")

    assert result.exit_code == 1
    assert result.problem is not None
    assert "GH_APP_PRIVATE_KEY" in result.problem


def test_no_records_at_all_is_red_because_nothing_was_observed(tmp_path: Path) -> None:
    result = summarize_installs(tmp_path)

    assert result.exit_code == 1
    assert result.problem is not None
    assert "did not run" in result.problem


def test_record_command_writes_the_state_file_and_never_a_token(tmp_path: Path) -> None:
    out = tmp_path / "runs" / "monitor" / f"install-{HTML}.json"

    code = main(
        [
            "monitor-install-record",
            "--owner",
            HTML,
            "--outcome",
            "failure",
            "--repositories",
            HTML_REPOS,
            "--out",
            str(out),
        ]
    )

    assert code == EXIT_OK
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["state"] == NOT_INSTALLED
    assert "ghs_" not in out.read_text(encoding="utf-8")


def test_record_command_rejects_an_outcome_outside_the_mint_vocabulary(tmp_path: Path) -> None:
    # argparse rejects a value outside its choices before any state is written.
    with pytest.raises(SystemExit):
        main(
            [
                "monitor-install-record",
                "--owner",
                HTML,
                "--outcome",
                "cancelled",
                "--repositories",
                HTML_REPOS,
                "--out",
                str(tmp_path / "x.json"),
            ]
        )
    assert not (tmp_path / "x.json").exists()
