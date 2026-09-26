"""``repository-presenter metadata --apply`` wiring: dry-run by default, and, even with --apply,
writes nothing without the explicit authorization variable. No test here makes a live GitHub call -
``capture_repo_metadata``, ``default_patch``, and ``default_put`` are all monkeypatched fakes."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, main
from repository_presenter.components.metadata.apply import AUTHORIZATION_VARIABLE
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id, write_facts
from repository_presenter.core.github.client import ObservedRepository
from support import REPO_ROOT

REPOSITORY_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
REVISION = "f" * 40
README_TEXT = (
    "# Aspose.3D FOSS for Python\n\n"
    "Aspose.3D FOSS for Python is a Python library for 3D file processing.\n\n"
    "## Navigation\n\n- [At a Glance](#at-a-glance)\n"
)


@pytest.fixture
def project_with_registry(project: Path) -> Path:
    (project / "data").mkdir()
    shutil.copy(REPO_ROOT / "data" / "registry.json", project / "data" / "registry.json")
    return project


@pytest.fixture
def project_with_sealed_candidate(project_with_registry: Path) -> Path:
    """A sealed CURRENT candidate for the canary with real facts, so ``run_metadata`` computes a
    genuine, non-trivial proposal/diff (not just a capture-only run)."""
    bundle = project_with_registry / "candidates" / REPOSITORY_DIR / REVISION
    bundle.mkdir(parents=True)
    (bundle.parent / "CURRENT").write_text(f"{REVISION}\n", encoding="utf-8")
    (bundle / "README.md").write_text(README_TEXT, encoding="utf-8")
    facts = FactsDocument(
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        REVISION,
        (
            Fact(
                fact_id("identity", "platform"), "identity", "python", (Evidence("registry", None),)
            ),
            Fact(fact_id("identity", "family"), "identity", "3d", (Evidence("registry", None),)),
            Fact(fact_id("license", "spdx"), "license", "MIT", (Evidence("LICENSE", None),)),
            Fact(
                fact_id("link_target", "product.homepage"),
                "link_target",
                "https://products.aspose.org/3d/python/",
                (Evidence("https://products.aspose.org/3d/python/", "HTTP 200"),),
            ),
        ),
    )
    write_facts(facts, bundle / "facts.json")
    return project_with_registry


def _observed(
    *,
    description: str | None = "Old description.",
    homepage: str | None = "https://old.example/",
    topics: tuple[str, ...] = (),
) -> ObservedRepository:
    return ObservedRepository(
        repository="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        description=description,
        homepage=homepage,
        topics=topics,
        observed_at="2026-09-26T00:00:00Z",
    )


class _RecordingWrite:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def __call__(self, url: str, token: str, payload: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((url, token, payload))
        return 200, {}


def test_apply_without_authorization_writes_nothing(
    project_with_sealed_candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "capture_repo_metadata", lambda entry, *, token: _observed())
    patch = _RecordingWrite()
    put = _RecordingWrite()
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "default_put", put)
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)

    exit_code = main(
        [
            "metadata",
            "--repo",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            "--root",
            str(project_with_sealed_candidate),
            "--apply",
        ]
    )

    assert exit_code == EXIT_OK
    assert patch.calls == []
    assert put.calls == []
    out = capsys.readouterr().out
    assert "not authorized" in out
    assert AUTHORIZATION_VARIABLE in out


def test_dry_run_without_apply_flag_writes_nothing_and_says_so(
    project_with_sealed_candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "capture_repo_metadata", lambda entry, *, token: _observed())
    patch = _RecordingWrite()
    put = _RecordingWrite()
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "default_put", put)

    exit_code = main(
        [
            "metadata",
            "--repo",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            "--root",
            str(project_with_sealed_candidate),
        ]
    )

    assert exit_code == EXIT_OK
    assert patch.calls == []
    assert put.calls == []
    out = capsys.readouterr().out
    assert "dry run" in out


def test_apply_authorized_with_token_and_no_drift_writes_all_changed_fields(
    project_with_sealed_candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Same observation returned on every capture call (the initial one and apply's own
    # recheck-before-effect refetch) - no drift, so the write should proceed.
    monkeypatch.setattr(cli, "capture_repo_metadata", lambda entry, *, token: _observed())
    patch = _RecordingWrite()
    put = _RecordingWrite()
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "default_put", put)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_METADATA_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(
        [
            "metadata",
            "--repo",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            "--root",
            str(project_with_sealed_candidate),
            "--apply",
        ]
    )

    assert exit_code == EXIT_OK
    assert len(patch.calls) == 1
    _, token, payload = patch.calls[0]
    assert token == "fake-write-token-for-this-test-only"
    assert payload["description"].startswith("Aspose.3D FOSS for Python is a Python library")
    assert payload["homepage"] == "https://products.aspose.org/3d/python/"
    assert len(put.calls) == 1
    out = capsys.readouterr().out
    assert "description written - written" in out
    assert "homepage written - written" in out
    assert "topics written - written" in out


def test_apply_aborts_on_live_drift_since_capture(
    project_with_sealed_candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # First call (Phase 0 capture) returns the baseline; the second call (apply's own
    # recheck-before-effect refetch) returns a homepage that moved on GitHub in between.
    responses = [_observed(), _observed(homepage="https://someone-else-changed-this.example/")]

    def fake_capture(entry: object, *, token: str | None) -> ObservedRepository:
        return responses.pop(0)

    monkeypatch.setattr(cli, "capture_repo_metadata", fake_capture)
    patch = _RecordingWrite()
    put = _RecordingWrite()
    monkeypatch.setattr(cli, "default_patch", patch)
    monkeypatch.setattr(cli, "default_put", put)
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")
    monkeypatch.setenv("GH_METADATA_WRITE_TOKEN", "fake-write-token-for-this-test-only")

    exit_code = main(
        [
            "metadata",
            "--repo",
            "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            "--root",
            str(project_with_sealed_candidate),
            "--apply",
        ]
    )

    assert exit_code == EXIT_OK
    assert patch.calls == []
    assert put.calls == []
    out = capsys.readouterr().out
    assert "changed since this diff was captured" in out
