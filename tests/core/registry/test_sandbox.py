"""The sandbox allow-list: a narrow second registry that never merges with the production one."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.errors import ConfigError, NotAllowlistedError
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    load_registry,
    require_listed,
)
from repository_presenter.core.registry.models import Registry, RegistryEntry
from repository_presenter.core.registry.sandbox import (
    SANDBOX_REGISTRY_RELATIVE_PATH,
    SANDBOX_REPOSITORIES,
    load_registry_for,
    load_sandbox_registry,
)
from repository_presenter.core.registry.write_gate import require_write_permitted
from support import REPO_ROOT

SANDBOX = "babar-raza/presenter-sandbox"
PRODUCTION = load_registry(REPO_ROOT / REGISTRY_RELATIVE_PATH)


def entry(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "repository": SANDBOX,
        "family": "cells",
        "platform": "go",
        "ecosystem": "go",
        "mode": "full",
        "issues_mode": "off",
        "policy_profile": "sandbox-canary",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 7, "node_id": "R_sandbox"},
    }
    base.update(overrides)
    return base


def write(path: Path, *entries: dict[str, Any]) -> Path:
    path.write_text(json.dumps({"schema_version": 1, "entries": list(entries)}), encoding="utf-8")
    return path


def test_the_committed_sandbox_registry_names_only_the_pinned_repository() -> None:
    sandbox = load_sandbox_registry(
        REPO_ROOT / SANDBOX_REGISTRY_RELATIVE_PATH, production=PRODUCTION
    )
    assert [e.repository for e in sandbox.entries] == [SANDBOX]
    assert set(SANDBOX_REPOSITORIES) == {SANDBOX}
    (only,) = sandbox.entries
    assert only.effective_issues_mode == "off"  # README proposals only
    assert only.active


def test_the_production_registry_is_unchanged_by_the_sandbox() -> None:
    assert len(PRODUCTION.entries) == 36
    assert SANDBOX not in {e.repository for e in PRODUCTION.entries}
    assert load_registry_for(REPO_ROOT) is not None
    assert load_registry_for(REPO_ROOT).entries == PRODUCTION.entries  # never the two merged


def test_the_production_loader_and_the_name_gate_still_refuse_the_sandbox(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="repository name must match"):
        RegistryEntry.model_validate(entry())
    with pytest.raises(ConfigError, match="malformed"):
        load_registry(write(tmp_path / "registry.json", entry()))
    with pytest.raises(ConfigError, match="malformed"):  # no spelling of a "sandbox" flag gets in
        load_registry(write(tmp_path / "flagged.json", {**entry(), "sandbox": True}))
    with pytest.raises(NotAllowlistedError):
        require_listed(PRODUCTION, SANDBOX)


def test_a_sandbox_registry_cannot_name_anything_but_the_pinned_repository(tmp_path: Path) -> None:
    for repository in (
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Go",  # a product
        "babar-raza/repository-presenter",  # the control repository
        "babar-raza/presenter-sandbox-2",
        "someone-else/presenter-sandbox",
    ):
        path = write(tmp_path / "s.json", entry(repository=repository))
        with pytest.raises(ConfigError, match=r"not a sandbox target|production registry"):
            load_sandbox_registry(path, production=PRODUCTION)


@pytest.mark.parametrize("issues_mode", [None, "file", "dry_run"])
def test_a_sandbox_entry_must_switch_issue_effects_off(
    tmp_path: Path, issues_mode: str | None
) -> None:
    candidate = entry(issues_mode=issues_mode)
    if issues_mode is None:
        del candidate["issues_mode"]
    with pytest.raises(ConfigError, match="issues_mode 'off'"):
        load_sandbox_registry(write(tmp_path / "s.json", candidate), production=PRODUCTION)


def test_a_repository_in_both_registries_is_refused_by_name_and_by_identity(tmp_path: Path) -> None:
    real = PRODUCTION.entries[0]
    same_id = {
        "provider": "github",
        "repository_id": real.provider_identity.repository_id,
        "node_id": "x",
    }
    with pytest.raises(ConfigError, match="never both a governed product and a sandbox"):
        load_sandbox_registry(
            write(tmp_path / "id.json", entry(provider_identity=same_id)), production=PRODUCTION
        )
    # A production registry that (impossibly, today) names the sandbox, in any letter case.
    named = Registry.model_construct(
        schema_version=1,
        entries=(
            RegistryEntry.model_construct(
                repository=SANDBOX.upper(), provider_identity=real.provider_identity
            ),
        ),
    )
    with pytest.raises(ConfigError, match="never both a governed product and a sandbox"):
        load_sandbox_registry(write(tmp_path / "name.json", entry()), production=named)


def test_a_missing_or_malformed_sandbox_registry_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_sandbox_registry(tmp_path / "absent.json", production=PRODUCTION)
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_sandbox_registry(broken, production=PRODUCTION)
    with pytest.raises(ConfigError, match="malformed"):
        load_sandbox_registry(
            write(tmp_path / "x.json", {"repository": SANDBOX}), production=PRODUCTION
        )


def test_the_write_gate_treats_a_sandbox_entry_like_any_other(tmp_path: Path) -> None:
    root = tmp_path
    (root / "data").mkdir()
    (root / REGISTRY_RELATIVE_PATH).write_bytes((REPO_ROOT / REGISTRY_RELATIVE_PATH).read_bytes())
    write(root / SANDBOX_REGISTRY_RELATIVE_PATH, entry(mode="full"))
    permit = require_write_permitted(
        load_registry_for(root, sandbox=True), SANDBOX, "readme_proposal"
    )
    assert permit.entry.repository == SANDBOX and permit.effect == "readme_proposal"
    write(root / SANDBOX_REGISTRY_RELATIVE_PATH, entry(mode="dry_run"))
    with pytest.raises(WriteRefusedError) as dry:
        require_write_permitted(load_registry_for(root, sandbox=True), SANDBOX, "readme_proposal")
    assert dry.value.code == Refusal.REGISTRY_DRY_RUN
    write(root / SANDBOX_REGISTRY_RELATIVE_PATH, entry(mode="disabled"))
    with pytest.raises(WriteRefusedError) as off:
        require_write_permitted(load_registry_for(root, sandbox=True), SANDBOX, "readme_proposal")
    assert off.value.code == Refusal.REGISTRY_DISABLED
    # An issue effect on a sandbox entry is refused even at mode full (issues_mode is pinned off).
    write(root / SANDBOX_REGISTRY_RELATIVE_PATH, entry(mode="full"))
    with pytest.raises(WriteRefusedError) as issue:
        require_write_permitted(load_registry_for(root, sandbox=True), SANDBOX, "issue_filing")
    assert issue.value.code == Refusal.REGISTRY_DISABLED
    # A product is not in the sandbox registry, so the sandbox flag cannot reach it.
    with pytest.raises(WriteRefusedError) as product:
        require_write_permitted(
            load_registry_for(root, sandbox=True),
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            "readme_proposal",
        )
    assert product.value.code == Refusal.REGISTRY_NOT_LISTED
