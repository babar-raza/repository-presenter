"""The prompt registry loads exactly the six governed manifests and fails loud on anything else."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from repository_presenter.core.errors import ConfigError, GatewayError
from repository_presenter.core.llm.prompts import (
    JOB_IDS,
    JOB_STAGES,
    load_manifests,
    validate_routes,
)
from support import REPO_ROOT

REAL_PROMPTS = REPO_ROOT / "prompts"


def _copy(tmp_path: Path) -> Path:
    prompts = tmp_path / "prompts"
    shutil.copytree(REAL_PROMPTS, prompts)
    return prompts


def _rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def test_the_real_manifests_load_with_stable_hashes_and_bound_templates() -> None:
    registry = load_manifests(REAL_PROMPTS)
    assert tuple(sorted(registry.manifests)) == tuple(sorted(JOB_IDS))
    for job, loaded in registry.manifests.items():
        manifest = loaded.manifest
        assert manifest.prompt_id == job == loaded.path.stem
        assert manifest.stage == JOB_STAGES[job]
        assert manifest.placeholders() <= manifest.packet.names
        assert manifest.sampling.temperature == 0.0
        assert manifest.output.schema_["type"] == "object"
        assert len(loaded.sha256) == 64
    assert registry.hashes() == load_manifests(REAL_PROMPTS).hashes()
    assert set(registry.routes().values()) == {"qwen3-next"}
    assert registry["independent_review"].manifest.output.binding == "finding_ids"


def test_a_manifest_edit_changes_only_its_own_hash(tmp_path: Path) -> None:
    prompts = _copy(tmp_path)
    before = load_manifests(prompts).hashes()
    _rewrite(prompts / "section_authoring.yaml", "sentences averaging", "sentences  averaging")
    after = load_manifests(prompts).hashes()
    assert after["section_authoring"] != before["section_authoring"]
    assert {job: after[job] for job in after if job != "section_authoring"} == {
        job: before[job] for job in before if job != "section_authoring"
    }


def test_line_endings_do_not_change_a_manifest_hash(tmp_path: Path) -> None:
    prompts = _copy(tmp_path)
    before = load_manifests(prompts).hashes()
    path = prompts / "targeted_repair.yaml"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert load_manifests(prompts).hashes() == before


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: (p / "notes.md").write_text("x", encoding="utf-8"), "not job manifests"),
        (lambda p: (p / "targeted_repair.yaml").unlink(), "lacks manifests for: targeted_repair"),
        (
            lambda p: (p / "targeted_repair.yaml").rename(p / "repair.yaml"),
            "not job manifests: ['repair.yaml']",
        ),
        (
            lambda p: _rewrite(p / "targeted_repair.yaml", "stage: S11", "stage: S6"),
            "runs at S11, not S6",
        ),
        (
            lambda p: _rewrite(p / "targeted_repair.yaml", "Repository: $repository", "$typo"),
            "names fields outside its packet: ['typo']",
        ),
        (
            lambda p: _rewrite(
                p / "targeted_repair.yaml", 'version: "1"', 'version: "1"\nowner: x'
            ),
            "is malformed",
        ),
        (
            lambda p: _rewrite(p / "targeted_repair.yaml", "temperature: 0.0", "temperature: 3"),
            "is malformed",
        ),
        (
            lambda p: _rewrite(
                p / "targeted_repair.yaml", "prompt_id: targeted_repair", "prompt_id: [x"
            ),
            "is not valid YAML",
        ),
    ],
    ids=["stray", "missing", "renamed", "stage", "placeholder", "extra-field", "sampling", "yaml"],
)
def test_every_deviation_from_the_governed_shape_fails_closed(
    tmp_path: Path, mutate: object, message: str
) -> None:
    prompts = _copy(tmp_path)
    mutate(prompts)  # type: ignore[operator]
    with pytest.raises(ConfigError, match=re.escape(message)):
        load_manifests(prompts)


def test_a_missing_prompts_directory_is_a_configuration_failure(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no prompts/ directory"):
        load_manifests(tmp_path / "prompts")


def test_routes_must_appear_in_the_recorded_catalog() -> None:
    registry = load_manifests(REAL_PROMPTS)
    validate_routes(registry, ("gpt-oss", "qwen3-next"))
    with pytest.raises(GatewayError, match="independent_review routes to 'qwen3-next'"):
        validate_routes(registry, ("gpt-oss",))
