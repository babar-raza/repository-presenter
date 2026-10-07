"""The drift monitor (G7-W06): each enabled registry repository's upstream default-branch head,
compared with the revision its CURRENT sealed bundle was built from.

Every GitHub read is injected through ``FakeDefaultBranchReader``, a stand-in for
``core/github/read_client.py::fetch_default_branch_sha`` - no test here reaches the network.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.cli import main
from repository_presenter.components.monitor.drift import (
    MAX_DRIFT_AGE,
    RepositoryDrift,
    Status,
    assemble_drift_contract,
    drift_document,
    observe_drift,
    write_drift_document,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    enabled_entries,
    load_registry,
)
from repository_presenter.core.registry.models import Registry, RegistryEntry
from repository_presenter.core.sealing_plan import (
    DRIFT_CONTRACT_VERSION,
    plan_sealing_run,
    read_drift_contract,
)
from support import REPO_ROOT, FakeDefaultBranchReader, monitor_registry_entry, write_bundle

TOKEN = "ghs_fixture_read_token_value_0123456789"
BUNDLED = "1111111111111111111111111111111111111111"
NEWER = "2222222222222222222222222222222222222222"
OLDER = "3333333333333333333333333333333333333333"
PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
JAVA = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
NET = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
PYTHON_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"


def entries_of(*raw: dict[str, Any]) -> tuple[RegistryEntry, ...]:
    return Registry.model_validate({"schema_version": 1, "entries": list(raw)}).entries


def observe_one(root: Path, repository: str, reader: FakeDefaultBranchReader) -> RepositoryDrift:
    (observation,) = observe_drift(
        root, entries_of(monitor_registry_entry(repository)), token=TOKEN, read_head=reader
    )
    return observation


def test_head_equal_to_a_bundle_without_recorded_hashes_is_unknown(tmp_path: Path) -> None:
    # A bundle sealed before upstream blob ids were recorded: the head matches, but its
    # dependencies cannot be judged, so it is UNKNOWN (never CURRENT) until it is re-sealed.
    # The CURRENT path with recorded hashes is covered in test_drift_content.py.
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "UNKNOWN"
    assert observation.head_revision == BUNDLED
    assert observation.bundle_revision == BUNDLED


def test_a_different_head_is_drifted_and_both_revisions_are_recorded(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: NEWER}))

    assert observation.status == "DRIFTED"
    assert observation.head_revision == NEWER
    assert observation.bundle_revision == BUNDLED


def test_a_repository_without_any_bundle_is_no_bundle(tmp_path: Path) -> None:
    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: NEWER}))

    assert observation.status == "NO_BUNDLE"
    assert observation.head_revision == NEWER
    assert observation.bundle_revision is None
    assert observation.detail == "no CURRENT pointer"


def test_a_current_bundle_that_fails_integrity_verification_is_no_bundle(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, None, raw="{ not json")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "NO_BUNDLE"
    assert observation.bundle_revision is None
    assert observation.detail is not None
    assert "fails verification" in observation.detail


def test_a_manifest_describing_another_revision_is_not_trusted(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    manifest["revision"] = OLDER
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    observation = observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED}))

    assert observation.status == "NO_BUNDLE"
    assert observation.detail is not None
    assert "does not describe" in observation.detail


def test_a_read_failure_is_unreachable_and_never_stops_the_other_repositories(
    tmp_path: Path,
) -> None:
    # Negative control: the failing repositories come first, so an abort would skip the healthy one.
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    reader = FakeDefaultBranchReader(
        {
            JAVA: ConnectionError("connection reset"),
            NET: DefaultBranchRead(NET, error="HTTP 503"),
            PYTHON: BUNDLED,
        }
    )
    registry = entries_of(
        monitor_registry_entry(JAVA, repository_id=2),
        monitor_registry_entry(NET, repository_id=3),
        monitor_registry_entry(PYTHON, repository_id=1),
    )

    observations = observe_drift(tmp_path, registry, token=TOKEN, read_head=reader)

    assert reader.calls == [JAVA, NET, PYTHON]
    assert [(o.repository, o.status) for o in observations] == [
        (JAVA, "UNREACHABLE"),
        (NET, "UNREACHABLE"),
        (PYTHON, "UNKNOWN"),
    ]
    assert observations[0].detail == "ConnectionError: connection reset"
    assert observations[1].detail == "HTTP 503"
    assert observations[1].bundle_revision is None
    assert observations[2].bundle_revision == BUNDLED


def test_an_unreachable_repository_keeps_no_revision_it_never_observed(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")

    observation = observe_one(
        tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: RuntimeError("boom")})
    )

    assert observation.status == "UNREACHABLE"
    assert observation.head_revision is None
    assert observation.bundle_revision is None


def test_the_read_token_is_passed_to_the_reader_and_never_appears_in_evidence(
    tmp_path: Path,
) -> None:
    reader = FakeDefaultBranchReader({PYTHON: RuntimeError(f"401 for Bearer {TOKEN}")})

    observations = observe_drift(
        tmp_path, entries_of(monitor_registry_entry(PYTHON)), token=TOKEN, read_head=reader
    )
    document = drift_document(observations, observed_at="2026-10-04T00:00:00+00:00", owner=None)

    assert reader.tokens == [TOKEN]
    assert TOKEN not in json.dumps(document)
    assert "[REDACTED]" in (observations[0].detail or "")


def test_the_document_counts_every_status_and_lists_repositories_in_order(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, BUNDLED, "READY_FOR_PROPOSAL")
    observations = [
        observe_one(tmp_path, JAVA, FakeDefaultBranchReader({JAVA: NEWER})),
        observe_one(tmp_path, PYTHON, FakeDefaultBranchReader({PYTHON: BUNDLED})),
        observe_one(tmp_path, NET, FakeDefaultBranchReader({NET: RuntimeError("down")})),
    ]

    document = drift_document(
        observations, observed_at="2026-10-04T00:00:00+00:00", owner="aspose-3d-foss"
    )

    assert document["schema_version"] == 1
    assert document["owner"] == "aspose-3d-foss"
    assert document["summary"] == {
        "CURRENT": 0,
        "DRIFTED": 0,
        "UNKNOWN": 1,
        "NO_BUNDLE": 1,
        "UNREACHABLE": 1,
    }
    # Sorted by repository name: "." (in ".NET") sorts before "J" (in "Java").
    assert [row["repository"] for row in document["repositories"]] == [NET, JAVA, PYTHON]
    assert document["repositories"][2]["status"] == "UNKNOWN"


# The handoff (G7-W06): the monitor's per-owner evidence must become the one sealing contract the
# scheduled plan reads. A monitor document is not that contract as written: it carries NO_BUNDLE and
# UNREACHABLE, which the contract refuses, and it is one file per owner.

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
FRESH = (NOW - timedelta(hours=1)).isoformat(timespec="seconds")


def _write_owner_evidence(
    directory: Path, owner: str, rows: list[RepositoryDrift], *, observed_at: str = FRESH
) -> None:
    document = drift_document(rows, observed_at=observed_at, owner=owner)
    write_drift_document(document, directory / f"drift-{owner}.json")


def _row(repository: str, status: Status) -> RepositoryDrift:
    return RepositoryDrift(repository, "full", status, None, "main", None, None)


def test_every_owners_evidence_becomes_one_contract_the_sealing_plan_accepts(
    tmp_path: Path,
) -> None:
    # Negative control: the monitor's raw NO_BUNDLE/UNREACHABLE rows must not reach the plan. Before
    # the fix, the plan read the monitor document directly and refused the whole run on them.
    _write_owner_evidence(
        tmp_path,
        "aspose-3d-foss",
        [_row(JAVA, "DRIFTED"), _row(PYTHON, "NO_BUNDLE"), _row(NET, "UNREACHABLE")],
    )
    expected = {"aspose-3d-foss": frozenset({JAVA, PYTHON, NET})}

    result = assemble_drift_contract(tmp_path, expected=expected, now=NOW)

    assert result.notices == ()
    assert result.document["schema_version"] == DRIFT_CONTRACT_VERSION
    assert [(r["repository"], r["status"]) for r in result.document["repositories"]] == [
        (NET, "UNKNOWN"),
        (JAVA, "DRIFTED"),
        (PYTHON, "UNKNOWN"),
    ]
    contract = tmp_path / "drift.json"
    contract.write_text(json.dumps(result.document), encoding="utf-8")
    records = read_drift_contract(contract)
    plan = plan_sealing_run(records, _plan_registry(JAVA, PYTHON, NET))
    assert plan.selected == (JAVA,)


def test_an_owner_without_evidence_fails_closed_unless_its_app_is_recorded_not_installed(
    tmp_path: Path,
) -> None:
    _write_owner_evidence(tmp_path, "aspose-3d-foss", [_row(JAVA, "CURRENT")])
    expected = {
        "aspose-3d-foss": frozenset({JAVA}),
        "other-owner": frozenset({"other-owner/Thing"}),
    }
    with pytest.raises(ConfigError, match="no drift evidence for enabled owner other-owner"):
        assemble_drift_contract(tmp_path, expected=expected, now=NOW)

    # A confirmed NOT_INSTALLED owner is a notice, never zero drift and never a refusal.
    (tmp_path / "install-other-owner.json").write_text(
        json.dumps({"owner": "other-owner", "state": "NOT_INSTALLED", "repositories": ""}),
        encoding="utf-8",
    )
    result = assemble_drift_contract(tmp_path, expected=expected, now=NOW)
    assert [r["repository"] for r in result.document["repositories"]] == [JAVA]
    assert any("other-owner" in notice for notice in result.notices)


def test_evidence_that_omits_an_enabled_repository_fails_closed(tmp_path: Path) -> None:
    _write_owner_evidence(tmp_path, "aspose-3d-foss", [_row(JAVA, "CURRENT")])
    expected = {"aspose-3d-foss": frozenset({JAVA, PYTHON})}

    with pytest.raises(ConfigError, match="omits enabled repositories"):
        assemble_drift_contract(tmp_path, expected=expected, now=NOW)


def test_stale_or_future_evidence_fails_closed(tmp_path: Path) -> None:
    expected = {"aspose-3d-foss": frozenset({JAVA})}
    stale = (NOW - MAX_DRIFT_AGE - timedelta(minutes=1)).isoformat(timespec="seconds")
    _write_owner_evidence(tmp_path, "aspose-3d-foss", [_row(JAVA, "DRIFTED")], observed_at=stale)
    with pytest.raises(ConfigError, match="stale or future-dated"):
        assemble_drift_contract(tmp_path, expected=expected, now=NOW)

    future = (NOW + timedelta(hours=1)).isoformat(timespec="seconds")
    _write_owner_evidence(tmp_path, "aspose-3d-foss", [_row(JAVA, "DRIFTED")], observed_at=future)
    with pytest.raises(ConfigError, match="stale or future-dated"):
        assemble_drift_contract(tmp_path, expected=expected, now=NOW)


def test_no_evidence_at_all_is_a_named_failure_never_zero_work(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        assemble_drift_contract(tmp_path, expected={"aspose-3d-foss": frozenset({JAVA})}, now=NOW)


def _plan_registry(*repositories: str) -> Registry:
    raw = [
        monitor_registry_entry(repository, mode="full", repository_id=index)
        for index, repository in enumerate(repositories, start=1)
    ]
    return Registry.model_validate({"schema_version": 1, "entries": raw})


def test_the_drift_contract_command_runs_through_the_real_parser_with_the_workflow_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The workflow's own argv, through the real argparse tree. Before the fix the subcommand had no
    # --root, so main() raised AttributeError ('Namespace' object has no attribute 'root') and the
    # plan job crashed before it could plan anything.
    registry = load_registry(REPO_ROOT / REGISTRY_RELATIVE_PATH)
    monitor = tmp_path / "monitor"
    now = datetime.now(UTC).isoformat(timespec="seconds")
    for owner in sorted({entry.owner for entry in enabled_entries(registry)}):
        rows = [
            RepositoryDrift(entry.repository, entry.mode, "CURRENT", None, "main", None, None)
            for entry in enabled_entries(registry)
            if entry.owner == owner
        ]
        write_drift_document(
            drift_document(rows, observed_at=now, owner=owner), monitor / f"drift-{owner}.json"
        )
    out = tmp_path / "drift" / "drift.json"
    monkeypatch.chdir(REPO_ROOT)

    code = main(["monitor-drift-contract", str(monitor), "--out", str(out)])

    assert code == 0
    records = read_drift_contract(out)
    assert {record.repository for record in records} == {
        entry.repository for entry in enabled_entries(registry)
    }


def test_the_drift_contract_command_refuses_with_its_exit_code_when_evidence_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    out = tmp_path / "drift.json"

    code = main(["monitor-drift-contract", str(tmp_path / "empty"), "--out", str(out)])

    assert code == ConfigError.exit_code
    assert not out.exists()
