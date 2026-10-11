"""Registry discovery through the official entry point: ``monitor``, ``registry-gaps``, ``status``.

Every GitHub reader is replaced (``cli.list_organization_repositories``,
``cli.fetch_default_branch_sha``), so no test reaches the network. The negative controls are the
point: an unregistered repository is reported and never admitted, the denominator never moves, no
repository found by discovery is read a second time, and a finding never turns a run red.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.monitor.discovery import (
    EXCLUSIONS_RELATIVE_PATH,
    discover,
    discovery_document,
    load_exclusions,
)
from repository_presenter.components.monitor.drift import drift_document
from repository_presenter.components.monitor.org_listing import UpstreamRepository
from repository_presenter.core.registry.loader import load_registry
from support import (
    REPO_ROOT,
    TODAYS_UNADMITTED,
    TODAYS_UNREGISTERED,
    FakeDefaultBranchReader,
    FakeOrganizationLister,
    mirror,
    monitor_registry_entry,
    registry_without_todays_unadmitted,
    with_extra,
    write_registry_file,
)

TOKEN = "ghs_fixture_gaps_read_token_9876543210"
PYTHON_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
JAVA_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
PYTHON_CELLS = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"
NEW_PRODUCT = "aspose-3d-foss/Aspose.3D-FOSS-for-Rust"
HEAD = "4" * 40


def _repo(full_name: str, identity: int, **flags: Any) -> UpstreamRepository:
    return UpstreamRepository(full_name, identity, default_branch="main", **flags)


@pytest.fixture
def gaps_project(project: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic project: three admitted repositories in two organizations, the real policy."""
    write_registry_file(
        project,
        [
            monitor_registry_entry(PYTHON_3D, repository_id=10),
            monitor_registry_entry(JAVA_3D, repository_id=11),
            monitor_registry_entry(PYTHON_CELLS, repository_id=12),
        ],
    )
    shutil.copy(REPO_ROOT / EXCLUSIONS_RELATIVE_PATH, project / EXCLUSIONS_RELATIVE_PATH)
    monkeypatch.setenv("GH_TOKEN", TOKEN)
    return project


def _admitted() -> dict[str, list[UpstreamRepository]]:
    return {
        "aspose-3d-foss": [_repo(PYTHON_3D, 10), _repo(JAVA_3D, 11)],
        "aspose-cells-foss": [_repo(PYTHON_CELLS, 12)],
    }


def _lister(
    monkeypatch: pytest.MonkeyPatch,
    extra: list[UpstreamRepository] | None = None,
    **kwargs: Any,
) -> FakeOrganizationLister:
    lister = FakeOrganizationLister(with_extra(_admitted(), extra or []), **kwargs)
    monkeypatch.setattr(cli, "list_organization_repositories", lister)
    return lister


def _heads(monkeypatch: pytest.MonkeyPatch) -> FakeDefaultBranchReader:
    reader = FakeDefaultBranchReader({PYTHON_3D: HEAD, JAVA_3D: HEAD, PYTHON_CELLS: HEAD})
    monkeypatch.setattr(cli, "fetch_default_branch_sha", reader)
    return reader


# --- monitor: an additive section, never a failure, never a second read ---


def test_monitor_adds_a_discovery_section_and_an_unregistered_repository_is_no_failure(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lister = _lister(monkeypatch, [_repo(NEW_PRODUCT, 99, language="Rust")])
    reader = _heads(monkeypatch)

    code = main(["monitor", "--root", str(gaps_project)])

    assert code == EXIT_OK
    document = json.loads((gaps_project / "runs" / "monitor" / "drift.json").read_text("utf-8"))
    assert document["schema_version"] == 1
    assert {"summary", "changes", "repositories", "observed_at", "owner"} <= set(document)
    assert document["discovery"]["counts"] == {
        "REGISTERED": 3,
        "UNREGISTERED": 1,
        "EXCLUDED_BY_POLICY": 0,
        "MISSING_UPSTREAM": 0,
    }
    assert [row["repository"] for row in document["discovery"]["unregistered"]] == [NEW_PRODUCT]
    out = capsys.readouterr().out
    assert f"unregistered: {NEW_PRODUCT}" in out and "1 unregistered" in out
    # Negative controls: one listing per organization; the unregistered repository gets no read.
    assert lister.calls == ["aspose-3d-foss", "aspose-cells-foss"]
    assert sorted(reader.calls) == sorted([PYTHON_3D, JAVA_3D, PYTHON_CELLS])
    assert NEW_PRODUCT not in reader.calls
    registry = load_registry(gaps_project / "data" / "registry.json")
    assert NEW_PRODUCT not in {entry.repository for entry in registry.entries}
    assert len(registry.entries) == 3


def test_monitor_owner_leg_discovers_only_its_own_organization(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lister = _lister(monkeypatch, [_repo(NEW_PRODUCT, 99)])
    _heads(monkeypatch)

    code = main(["monitor", "--root", str(gaps_project), "--owner", "aspose-3d-foss"])

    assert code == EXIT_OK and lister.calls == ["aspose-3d-foss"]
    path = gaps_project / "runs" / "monitor" / "drift-aspose-3d-foss.json"
    assert json.loads(path.read_text("utf-8"))["discovery"]["admitted"] == 2


def test_monitor_no_discovery_lists_no_organization_and_writes_no_section(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lister = _lister(monkeypatch)
    _heads(monkeypatch)

    code = main(["monitor", "--root", str(gaps_project), "--no-discovery"])

    assert code == EXIT_OK and lister.calls == []
    document = json.loads((gaps_project / "runs" / "monitor" / "drift.json").read_text("utf-8"))
    assert "discovery" not in document


def test_monitor_survives_a_failed_listing_and_says_discovery_is_incomplete(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _lister(monkeypatch, errors={"aspose-cells-foss": RuntimeError(f"boom {TOKEN}")})
    _heads(monkeypatch)

    code = main(["monitor", "--root", str(gaps_project)])

    assert code == EXIT_OK  # the drift observation itself completed
    text = (gaps_project / "runs" / "monitor" / "drift.json").read_text("utf-8")
    section = json.loads(text)["discovery"]
    assert section["complete"] is False
    assert section["organizations"]["aspose-cells-foss"]["error"]
    captured = capsys.readouterr()
    assert "discovery incomplete: aspose-cells-foss" in captured.out
    assert TOKEN not in text + captured.out + captured.err


def test_monitor_without_the_policy_file_still_observes_and_records_the_discovery_error(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (gaps_project / EXCLUSIONS_RELATIVE_PATH).unlink()
    lister = _lister(monkeypatch)
    _heads(monkeypatch)

    code = main(["monitor", "--root", str(gaps_project)])

    assert code == EXIT_OK and lister.calls == []
    section = json.loads((gaps_project / "runs" / "monitor" / "drift.json").read_text("utf-8"))[
        "discovery"
    ]
    assert section["complete"] is False and "exclusions not found" in section["error"]


# --- registry-gaps: live ---


def test_registry_gaps_needs_the_read_token_and_lists_nothing_without_it(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lister = _lister(monkeypatch)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    code = main(["registry-gaps", "--root", str(gaps_project)])

    assert code == EXIT_USAGE and lister.calls == []
    assert "GH_TOKEN" in capsys.readouterr().err


def test_registry_gaps_json_prints_the_discovery_document(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lister = _lister(monkeypatch, [_repo(NEW_PRODUCT, 99, language="Rust")])

    code = main(["registry-gaps", "--root", str(gaps_project), "--json"])

    assert code == EXIT_OK  # a finding, not a failure
    document = json.loads(capsys.readouterr().out)
    section = document["discovery"]
    assert document["schema_version"] == 1
    assert section["counts"]["UNREGISTERED"] == 1 and section["admitted"] == 3
    assert section["unregistered"][0]["repository"] == NEW_PRODUCT
    assert lister.tokens == [TOKEN, TOKEN]


def test_registry_gaps_text_names_each_repository_and_out_writes_the_document(
    gaps_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    _lister(
        monkeypatch, [_repo(NEW_PRODUCT, 99, language="Rust"), _repo("aspose-3d-foss/.github", 98)]
    )
    out = tmp_path / "gaps.json"

    code = main(["registry-gaps", "--root", str(gaps_project), "--out", str(out)])

    text = capsys.readouterr().out
    assert code == EXIT_OK
    assert (
        "discovery: 3 registered, 1 unregistered, 1 excluded by policy, 0 missing upstream" in text
    )
    assert f"unregistered: {NEW_PRODUCT} (id 99, Rust)" in text
    assert "excluded by policy: aspose-3d-foss/.github" in text
    assert json.loads(out.read_text("utf-8"))["discovery"]["counts"]["UNREGISTERED"] == 1


def test_registry_gaps_owner_filter_and_unknown_owner(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lister = _lister(monkeypatch)

    assert main(["registry-gaps", "--root", str(gaps_project), "--owner", "aspose-cells-foss"]) == 0
    assert lister.calls == ["aspose-cells-foss"]
    capsys.readouterr()

    assert main(["registry-gaps", "--root", str(gaps_project), "--owner", "aspose-nope-foss"]) == (
        EXIT_USAGE
    )
    assert lister.calls == ["aspose-cells-foss"]  # the unknown organization was never listed
    assert "not an organization in the registry" in capsys.readouterr().err


def test_registry_gaps_exits_one_when_an_organization_cannot_be_listed(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _lister(monkeypatch, errors={"aspose-3d-foss": "HTTP 403"})

    code = main(["registry-gaps", "--root", str(gaps_project)])

    captured = capsys.readouterr()
    assert code == EXIT_INCONSISTENT
    assert "discovery incomplete: aspose-3d-foss: HTTP 403" in captured.out
    assert "registry discovery is incomplete" in captured.err


def test_registry_gaps_warn_only_annotates_withholds_private_names_and_never_fails(
    gaps_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _lister(
        monkeypatch,
        [_repo(NEW_PRODUCT, 99), _repo("aspose-3d-foss/Hidden-Thing", 98, private=True)],
        errors={"aspose-cells-foss": "HTTP 403"},
    )

    code = main(["registry-gaps", "--root", str(gaps_project), "--warn-only"])

    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert "::warning title=Repositories not in the registry::2 repositor(ies)" in out
    assert NEW_PRODUCT in out
    assert "Hidden-Thing" not in out and "(private repository, name withheld)" in out
    assert "::warning title=Registry discovery incomplete::" in out


# --- registry-gaps --from: the workflow summary ---


def _evidence_dir(root: Path, directory: Path, extra: list[UpstreamRepository]) -> Path:
    """Two owners' drift documents, as the monitor legs upload them, plus an install record."""
    directory.mkdir(parents=True, exist_ok=True)
    registry = load_registry(root / "data" / "registry.json")
    listing = FakeOrganizationLister(with_extra(_admitted(), extra))
    for owner in ("aspose-3d-foss", "aspose-cells-foss"):
        report = discover(
            registry,
            load_exclusions(root / EXCLUSIONS_RELATIVE_PATH),
            lister=listing,
            token=TOKEN,
            observed_at="2026-10-11T12:00:00+00:00",
            organization=owner,
        )
        (directory / f"drift-{owner}.json").write_text(
            json.dumps(
                drift_document(
                    [],
                    observed_at="2026-10-11T12:00:00+00:00",
                    owner=owner,
                    discovery=report.to_json(),
                )
            ),
            encoding="utf-8",
        )
    (directory / "install-aspose-3d-foss.json").write_text(
        json.dumps({"owner": "aspose-3d-foss", "state": "INSTALLED"}), encoding="utf-8"
    )
    return directory


def test_registry_gaps_from_evidence_warns_summarises_and_exits_zero(
    gaps_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence = _evidence_dir(gaps_project, tmp_path / "monitor", [_repo(NEW_PRODUCT, 99)])
    summary = tmp_path / "summary.md"
    summary.write_text("earlier step\n", encoding="utf-8")
    lister = _lister(monkeypatch)  # must not be used: --from reads nothing
    monkeypatch.delenv("GH_TOKEN", raising=False)

    code = main(
        [
            "registry-gaps",
            "--root",
            str(gaps_project),
            "--from",
            str(evidence),
            "--summary",
            str(summary),
            "--warn-only",
        ]
    )

    out = capsys.readouterr().out
    assert code == EXIT_OK and lister.calls == []
    assert "::warning title=Repositories not in the registry::1 repositor(ies)" in out
    assert NEW_PRODUCT in out
    text = summary.read_text("utf-8")
    assert text.startswith("earlier step\n### Registry discovery")
    assert f"| {NEW_PRODUCT} |" in text and "3 admitted; **1 unregistered**" in text


def test_registry_gaps_from_a_clean_portfolio_is_quiet(
    gaps_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = _evidence_dir(gaps_project, tmp_path / "monitor", [])

    code = main(
        ["registry-gaps", "--root", str(gaps_project), "--from", str(evidence), "--warn-only"]
    )

    out = capsys.readouterr().out
    assert code == EXIT_OK and "::warning" not in out
    assert "discovery: 3 registered, 0 unregistered" in out


def test_registry_gaps_from_missing_evidence_is_a_warning_in_workflow_mode_else_an_error(
    gaps_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "install-x.json").write_text(json.dumps({"owner": "x"}), encoding="utf-8")
    argv = ["registry-gaps", "--root", str(gaps_project), "--from", str(empty)]

    assert main([*argv, "--warn-only"]) == EXIT_OK
    assert "::warning title=Registry discovery not reported::" in capsys.readouterr().out
    assert main(argv) == EXIT_INCONSISTENT
    assert "no registry discovery recorded" in capsys.readouterr().err

    absent = ["registry-gaps", "--root", str(gaps_project), "--from", str(tmp_path / "absent")]
    assert main([*absent, "--warn-only"]) == EXIT_OK
    assert main(absent) == EXIT_USAGE


# --- status: one separate line, the denominator untouched ---


@pytest.fixture
def real_registry_project(project: Path) -> Path:
    (project / "data").mkdir()
    shutil.copy(REPO_ROOT / "data" / "registry.json", project / "data" / "registry.json")
    return project


def _reality_evidence(path: Path) -> int:
    """Today's reality as a standalone discovery document; returns the admitted count."""
    registry = registry_without_todays_unadmitted(REPO_ROOT / "data" / "registry.json")
    report = discover(
        registry,
        load_exclusions(REPO_ROOT / EXCLUSIONS_RELATIVE_PATH),
        lister=FakeOrganizationLister(with_extra(mirror(registry.entries), TODAYS_UNADMITTED)),
        token=TOKEN,
        observed_at="2026-10-11T12:00:00+00:00",
    )
    path.write_text(json.dumps(discovery_document(report)), encoding="utf-8")
    return len(registry.entries)


def test_status_without_evidence_says_discovery_was_not_observed(
    real_registry_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    admitted = len(load_registry(real_registry_project / "data" / "registry.json").entries)

    assert main(["status", "--root", str(real_registry_project)]) == EXIT_OK

    lines = capsys.readouterr().out.splitlines()
    assert any(
        line.startswith(f"registry: {admitted} admitted; discovery not observed") for line in lines
    )
    assert any(
        line.startswith(f"candidates: 0/{34} ") for line in lines
    )  # denominator: the cursor's


def test_status_reports_the_unregistered_count_on_its_own_line_and_lists_them_with_verbose(
    real_registry_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = tmp_path / "gaps.json"
    _reality_evidence(evidence)
    admitted = len(load_registry(real_registry_project / "data" / "registry.json").entries)
    argv = ["status", "--root", str(real_registry_project), "--discovery", str(evidence)]

    assert main(argv) == EXIT_OK
    plain = capsys.readouterr().out
    assert main([*argv, "--verbose"]) == EXIT_OK
    verbose = capsys.readouterr().out

    expected = f"registry: {admitted} admitted; "
    registry_line = next(line for line in plain.splitlines() if line.startswith("registry:"))
    assert registry_line.startswith(expected + "9 unregistered in authorized organizations")
    assert "(list with --verbose)" in registry_line
    for name in TODAYS_UNREGISTERED:
        assert name not in plain and name in verbose
    # The count line and the portfolio denominator are exactly what they were: discovery is its
    # own line, never a number in the denominator.
    assert f"portfolio: {admitted} live registry entries" in plain
    assert plain.index("canary:") < plain.index("registry:") < plain.index("portfolio:")


def test_status_json_gains_a_registry_key_and_changes_nothing_else(
    real_registry_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = tmp_path / "gaps.json"
    admitted = _reality_evidence(evidence)
    base = ["status", "--root", str(real_registry_project), "--json"]

    assert main(base) == EXIT_OK
    without = json.loads(capsys.readouterr().out)
    assert main([*base, "--discovery", str(evidence)]) == EXIT_OK
    observed = json.loads(capsys.readouterr().out)

    assert without["registry"]["discovery"] is None and without["registry"]["admitted"] == admitted
    assert observed["registry"]["discovery"]["counts"]["UNREGISTERED"] == 9
    for key in ("candidates", "portfolio", "progress", "canary"):
        assert observed[key] == without[key]
    assert observed["portfolio"]["denominator"] == admitted


def test_status_reads_discovery_from_the_drift_evidence_it_was_given(
    real_registry_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    standalone = tmp_path / "gaps.json"
    _reality_evidence(standalone)
    section = json.loads(standalone.read_text("utf-8"))["discovery"]
    (evidence / "drift.json").write_text(
        json.dumps(
            drift_document(
                [], observed_at="2026-10-11T12:00:00+00:00", owner=None, discovery=section
            )
        ),
        encoding="utf-8",
    )

    code = main(["status", "--root", str(real_registry_project), "--drift", str(evidence)])

    assert code == EXIT_OK
    assert "9 unregistered in authorized organizations" in capsys.readouterr().out


def test_status_picks_up_the_local_monitor_run_and_survives_its_being_unreadable(
    real_registry_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monitor = real_registry_project / "runs" / "monitor"
    monitor.mkdir(parents=True)
    _reality_evidence(monitor / "gaps.json")

    assert main(["status", "--root", str(real_registry_project)]) == EXIT_OK
    assert "9 unregistered in authorized organizations" in capsys.readouterr().out

    (monitor / "gaps.json").write_text("{nope", encoding="utf-8")
    assert main(["status", "--root", str(real_registry_project)]) == EXIT_OK
    assert "monitor evidence unreadable" in capsys.readouterr().out


def test_status_rejects_discovery_evidence_named_on_the_command_line_that_is_unusable(
    real_registry_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")

    code = main(["status", "--root", str(real_registry_project), "--discovery", str(bad)])

    assert code == EXIT_USAGE
    assert "discovery evidence is unreadable" in capsys.readouterr().err
    absent = ["status", "--root", str(real_registry_project), "--discovery", str(tmp_path / "x")]
    assert main(absent) == EXIT_USAGE


def test_status_without_a_registry_prints_no_registry_line(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "registry:" not in capsys.readouterr().out
    assert main(["status", "--root", str(project), "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["registry"] is None
