"""``package:registry_lag``: the registry's release lags this source tree, decided from files."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.evidence.facts.registry_lag import (
    REGISTRY_LAG_FACT_ID,
    registry_lag_fact,
    unreleased_entries,
)
from repository_presenter.core.facts import Evidence, Fact

CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Hyperlinks on text portions and shapes.
- Strict property assignment.

## [26.8.0] - 2026-08-01

- First tagged release.
"""


def _fact(fact_id: str, value: str, path: str = "pyproject.toml") -> Fact:
    return Fact(fact_id, "package", value, (Evidence(path, None),))


def _repository(root: Path, changelog: str | None) -> tuple[Path, list[str]]:
    root.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    if changelog is not None:
        (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8", newline="\n")
        paths.append("CHANGELOG.md")
    return root, paths


def test_unreleased_entries_counts_bullets_under_the_unreleased_heading_only() -> None:
    assert unreleased_entries(CHANGELOG) == 2
    assert (
        unreleased_entries("## Unreleased\n\n- one\n  - nested\n\n## [1.0.0]\n\n- shipped\n") == 2
    )
    assert unreleased_entries("## [Unreleased]\n\n## [1.0.0]\n\n- shipped\n") == 0
    assert unreleased_entries("## [1.0.0]\n\n- shipped\n") == 0


def test_unreleased_changelog_entries_beside_a_matching_registry_version_are_a_lag(
    tmp_path: Path,
) -> None:
    """Slides-Python: manifest and PyPI both say 26.8.0, and the changelog lists unreleased work."""
    root, paths = _repository(tmp_path, CHANGELOG)
    facts = [_fact("package:version", "26.8.0"), _fact("package:published_version", "26.8.0")]
    lag = registry_lag_fact(facts, root, paths)
    assert lag is not None
    assert (lag.id, lag.kind, lag.value, lag.polarity) == (
        REGISTRY_LAG_FACT_ID,
        "package",
        "26.8.0",
        "SUPPORTED",
    )
    assert lag.attributes == {"basis": "changelog_unreleased"}
    assert lag.evidence[0].path == "CHANGELOG.md" and "2 entries" in (lag.evidence[0].detail or "")


def test_a_manifest_newer_than_the_registry_is_a_lag_without_any_changelog(
    tmp_path: Path,
) -> None:
    root, paths = _repository(tmp_path, None)
    facts = [_fact("package:version", "26.9.0"), _fact("package:published_version", "26.8.0")]
    lag = registry_lag_fact(facts, root, paths)
    assert lag is not None and lag.attributes == {"basis": "manifest_newer"}
    assert "newer than the registry's current release 26.8.0" in (lag.evidence[0].detail or "")


def test_both_bases_are_recorded_when_both_hold(tmp_path: Path) -> None:
    root, paths = _repository(tmp_path, CHANGELOG)
    facts = [_fact("package:version", "26.9.0"), _fact("package:published_version", "26.8.0")]
    lag = registry_lag_fact(facts, root, paths)
    assert lag is not None and lag.attributes == {"basis": "manifest_newer,changelog_unreleased"}
    assert len(lag.evidence) == 2


def test_no_lag_is_claimed_without_a_registry_reading_or_without_unreleased_work(
    tmp_path: Path,
) -> None:
    root, paths = _repository(tmp_path / "busy", CHANGELOG)
    assert registry_lag_fact([_fact("package:version", "26.8.0")], root, paths) is None
    quiet_root, quiet_paths = _repository(tmp_path / "quiet", "## [Unreleased]\n\n## [1.0.0]\n")
    even = [_fact("package:version", "1.0.0"), _fact("package:published_version", "1.0.0")]
    assert registry_lag_fact(even, quiet_root, quiet_paths) is None
    behind = [_fact("package:version", "1.0.0"), _fact("package:published_version", "1.1.0")]
    assert registry_lag_fact(behind, quiet_root, quiet_paths) is None  # the registry is ahead
    unreadable = Fact(
        "package:published_version",
        "package",
        "26.8.0",
        (Evidence("https://pypi.org", None),),
        polarity="UNRESOLVED",
    )
    assert registry_lag_fact([_fact("package:version", "26.8.0"), unreadable], root, paths) is None
