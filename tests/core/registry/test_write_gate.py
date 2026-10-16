"""The one registry write gate: a listed, active entry whose consulted mode permits the effect."""

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


ISSUE_EFFECTS: tuple[WriteEffect, ...] = ("issue_filing", "issue_close")
PR_EFFECTS: tuple[WriteEffect, ...] = ("readme_proposal", "metadata_write")


def _with_issues_mode(tmp_path: Path, *, mode: str, issues_mode: str | None, active: bool = True):
    entry = monitor_registry_entry(FULL, mode=mode, repository_id=1)
    if issues_mode is not None:
        entry["issues_mode"] = issues_mode
    entry["active"] = active
    return load_registry(write_registry_file(tmp_path, [entry]))


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


@pytest.mark.parametrize("effect", ISSUE_EFFECTS)
def test_issues_mode_file_with_dry_run_mode_permits_issues_but_not_a_readme_proposal(
    tmp_path: Path, effect: WriteEffect
) -> None:
    """The negative control: issue-eligible does not mean PR-eligible, through the real gate."""
    registry = _with_issues_mode(tmp_path, mode="dry_run", issues_mode="file")
    assert require_write_permitted(registry, FULL, effect).effect == effect
    for pr_effect in PR_EFFECTS:
        with pytest.raises(WriteRefusedError) as info:
            require_write_permitted(registry, FULL, pr_effect)
        assert info.value.code is Refusal.REGISTRY_DRY_RUN


@pytest.mark.parametrize("effect", ISSUE_EFFECTS)
def test_issues_mode_off_refuses_issue_effects_even_when_mode_is_full(
    tmp_path: Path, effect: WriteEffect
) -> None:
    registry = _with_issues_mode(tmp_path, mode="full", issues_mode="off")
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(registry, FULL, effect)
    assert info.value.code is Refusal.REGISTRY_DISABLED and "issues_mode 'off'" in str(info.value)
    for pr_effect in PR_EFFECTS:  # mode full still permits the PR-side effects
        assert require_write_permitted(registry, FULL, pr_effect).effect == pr_effect


@pytest.mark.parametrize("effect", ISSUE_EFFECTS)
def test_issues_mode_dry_run_refuses_issue_effects_even_when_mode_is_full(
    tmp_path: Path, effect: WriteEffect
) -> None:
    registry = _with_issues_mode(tmp_path, mode="full", issues_mode="dry_run")
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(registry, FULL, effect)
    assert info.value.code is Refusal.REGISTRY_DRY_RUN and "issues_mode" in str(info.value)


@pytest.mark.parametrize("effect", EFFECTS)
def test_a_disabled_mode_refuses_every_effect_whatever_issues_mode_says(
    tmp_path: Path, effect: WriteEffect
) -> None:
    registry = _with_issues_mode(tmp_path, mode="disabled", issues_mode="file")
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(registry, FULL, effect)
    assert info.value.code is Refusal.REGISTRY_DISABLED


@pytest.mark.parametrize("effect", ISSUE_EFFECTS)
def test_an_inactive_entry_is_refused_issue_effects_even_with_issues_mode_file(
    tmp_path: Path, effect: WriteEffect
) -> None:
    registry = _with_issues_mode(tmp_path, mode="full", issues_mode="file", active=False)
    with pytest.raises(WriteRefusedError) as info:
        require_write_permitted(registry, FULL, effect)
    assert info.value.code is Refusal.REGISTRY_INACTIVE


# The shipped entries that set ``issues_mode`` explicitly, each with the owner approval that
# admitted it. Any other entry setting the field fails this test: a flip is an owner act
# (docs/DECISION_LOG.md 2026-10-14, "reset to shipping": Cells-Cpp opts into issue filing;
# 2026-10-16, lane iss4: the owner asked for the Aspose.3D TypeScript and Aspose.TeX Python
# handoffs to be prepared for filing).
ISSUE_FILING_OPT_INS: dict[str, str] = {
    "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript": "file",
    "aspose-tex-foss/Aspose.TeX-FOSS-for-Python": "file",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET": "file",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp": "file",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Python": "file",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript": "file",
}


def test_the_real_registry_default_derivation_leaves_every_entry_behaving_as_before() -> None:
    """Of the 44 shipped entries, only the owner-approved opt-ins set ``issues_mode``; every other
    entry derives it from ``mode``. The README-side effects are permitted for exactly the 2
    ``full`` entries, as before; issue_filing and issue_close for those 2 plus the opt-ins, and
    an opt-in never arms a README pull request."""
    from support import REPO_ROOT

    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    assert len(registry.entries) == 44
    explicit = {e.repository: e.issues_mode for e in registry.entries if e.issues_mode is not None}
    assert explicit == ISSUE_FILING_OPT_INS

    def permitted(repository: str, effect: WriteEffect) -> bool:
        try:
            require_write_permitted(registry, repository, effect)
        except WriteRefusedError:
            return False
        return True

    full = {e.repository for e in registry.entries if e.mode == "full"}
    assert len(full) == 2
    for effect in EFFECTS:
        allowed = {e.repository for e in registry.entries if permitted(e.repository, effect)}
        if effect in ("issue_filing", "issue_close"):
            assert allowed == full | set(ISSUE_FILING_OPT_INS)
        else:
            assert allowed == full
