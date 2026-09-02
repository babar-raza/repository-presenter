"""A README-only placeholder is non-processable; any manifest or source makes it processable."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.evidence.processability import (
    NO_IMPLEMENTATION_EVIDENCE,
    assess_processability,
    write_disposition,
)
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.core.snapshot.capture import RepositorySnapshot

SNAPSHOT = RepositorySnapshot(
    repository="aspose-psd-foss/Aspose.PSD-FOSS-for-Python",
    clone_url="https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Python.git",
    source_revision="b" * 40,
    tree_sha256="c" * 64,
    tree_entries=2,
    readme_path="README.md",
    readme_sha256="d" * 64,
    license_path="LICENSE",
)


def test_readme_only_tree_is_non_processable(tmp_path: Path) -> None:
    plugin = plugin_for("python")
    disposition = assess_processability(SNAPSHOT, ["README.md", "LICENSE"], plugin, None)
    assert disposition is not None
    assert disposition.reason_code == NO_IMPLEMENTATION_EVIDENCE
    assert disposition.source_revision == "b" * 40
    assert disposition.tree_sha256 == "c" * 64
    assert disposition.evidence_paths_inspected == ("LICENSE", "README.md")
    assert "pyproject.toml, setup.cfg, setup.py" in disposition.resume_predicate
    assert ".py" in disposition.resume_predicate

    write_disposition(disposition, tmp_path / "disposition.json")
    document = json.loads((tmp_path / "disposition.json").read_text("utf-8"))
    assert document["reason_code"] == NO_IMPLEMENTATION_EVIDENCE
    assert document["ecosystem"] == "python"
    assert document["schema_version"] == 1


def test_a_manifest_or_source_file_makes_the_tree_processable() -> None:
    plugin = plugin_for("python")
    assert assess_processability(SNAPSHOT, ["README.md"], plugin, "setup.py") is None
    assert assess_processability(SNAPSHOT, ["README.md", "pkg/__init__.py"], plugin, None) is None
