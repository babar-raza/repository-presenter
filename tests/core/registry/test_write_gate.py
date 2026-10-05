"""The one registry write gate: only a listed, active, mode-``full`` entry may receive a write."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.registry.loader import load_registry
from repository_presenter.core.registry.write_gate import WriteEffect, require_write_permitted
from support import monitor_registry_entry, write_registry_file

FULL = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
DRY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
OFF = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
EFFECTS: tuple[WriteEffect, ...] = (
    "readme_proposal",
    "metadata_write",
    "issue_filing",
    "issue_close",
)


def _registry(tmp_path: Path, *, inactive: bool = False) -> Any:
    entries = [
        monitor_registry_entry(FULL, mode="full", repository_id=1),
        monitor_registry_entry(DRY, mode="dry_run", repository_id=2),
        monitor_registry_entry(OFF, mode="disabled", repository_id=3),
    ]
    if inactive:
        entries[0]["active"] = False
    return load_registry(write_registry_file(tmp_path, entries))


@pytest.mark.parametrize("effect", EFFECTS)
def test_a_full_entry_receives_a_permit_for_each_write_effect(
    tmp_path: Path, effect: WriteEffect
) -> None:
    permit = require_write_permitted(_registry(tmp_path), FULL, effect)
    assert permit.effect == effect
    assert permit.entry.repository == FULL


@pytest.mark.parametrize("effect", EFFECTS)
def test_a_dry_run_entry_is_refused_every_write_effect(tmp_path: Path, effect: WriteEffect) -> None:
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(_registry(tmp_path), DRY, effect)
    assert info.value.code is Refusal.REGISTRY_DRY_RUN
    assert info.value.exit_code == 3
    assert "dry_run" in str(info.value)


@pytest.mark.parametrize("effect", EFFECTS)
def test_a_disabled_entry_is_refused_every_write_effect(
    tmp_path: Path, effect: WriteEffect
) -> None:
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(_registry(tmp_path), OFF, effect)
    assert info.value.code is Refusal.REGISTRY_DISABLED


def test_an_unlisted_repository_is_refused(tmp_path: Path) -> None:
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(_registry(tmp_path), "some-org/not-listed", "readme_proposal")
    assert info.value.code is Refusal.REGISTRY_NOT_LISTED


def test_an_inactive_full_entry_is_refused(tmp_path: Path) -> None:
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(_registry(tmp_path, inactive=True), FULL, "readme_proposal")
    assert info.value.code is Refusal.REGISTRY_INACTIVE


def test_the_real_registry_grants_no_write_to_a_dry_run_entry() -> None:
    """Against the shipped ``data/registry.json``: the canary is dry_run, so it can never be
    written to however it is asked."""
    from support import REPO_ROOT

    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(
            registry, "aspose-3d-foss/Aspose.3D-FOSS-for-Python", "readme_proposal"
        )
    assert info.value.code is Refusal.REGISTRY_DRY_RUN
