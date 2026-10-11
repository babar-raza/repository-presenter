"""The 30-day freshness check (G7-W06, TC-REF-01-02): registry versions re-resolved against the
sealed package facts, with zero provider calls. The registry probe is injected, so no test here
reaches a registry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from repository_presenter.components.monitor.drift import observe_drift
from repository_presenter.components.monitor.freshness import (
    FRESHNESS_MAX_AGE,
    freshness_check,
    freshness_due,
)
from repository_presenter.components.readme.extractors.surface.registry import (
    RegistryObservation,
)
from repository_presenter.core.github.read_client import TreeRead
from repository_presenter.core.registry.models import Registry
from support import FakeDefaultBranchReader, monitor_registry_entry, write_bundle

TOKEN = "ghs_fixture_read_token_value_0123456789"
REVISION = "1" * 40
PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PYTHON_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def name_fact() -> dict[str, Any]:
    return {
        "id": "package:name",
        "polarity": "SUPPORTED",
        "value": "aspose-3d-foss",
        "evidence": [{"path": "setup.py", "detail": None}],
    }


def version_fact(version: str) -> dict[str, Any]:
    return {
        "id": "package:published_version",
        "polarity": "SUPPORTED",
        "value": version,
        "evidence": [{"path": "https://pypi.org/pypi/aspose-3d-foss/json", "detail": None}],
    }


def install_fact(reading: str) -> dict[str, Any]:
    return {
        "id": "install_command:pip",
        "polarity": "SUPPORTED",
        "value": "pip install aspose-3d-foss",
        "evidence": [{"path": "setup.py", "detail": f"package registry: {reading}"}],
    }


def reading(
    *, published: bool | None = True, version: str | None = "26.2.0", ambiguous: bool = False
) -> RegistryObservation:
    return RegistryObservation(
        registry="pypi",
        name="aspose-3d-foss",
        published=published,
        ambiguous=ambiguous,
        evidence_url="https://pypi.org/pypi/aspose-3d-foss/json",
        method="http",
        source="fixture",
        latest_version=version,
    )


class FakeRegistry:
    def __init__(self, outcome: RegistryObservation | Exception) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, str]] = []

    def __call__(self, ecosystem: str, package: str, **_: Any) -> RegistryObservation:
        self.calls.append((ecosystem, package))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def test_due_only_after_the_max_age() -> None:
    just_inside = (NOW - FRESHNESS_MAX_AGE + timedelta(minutes=1)).isoformat()
    just_past = (NOW - FRESHNESS_MAX_AGE).isoformat()

    assert timedelta(days=30) == FRESHNESS_MAX_AGE
    assert freshness_due(just_inside, now=NOW) is False
    assert freshness_due(just_past, now=NOW) is True
    assert freshness_due("not a date", now=NOW) is True
    assert freshness_due(None, now=NOW) is True


def test_a_newer_registry_release_than_the_sealed_one_is_relevant_when_consumed() -> None:
    facts = [name_fact(), version_fact("26.1.0")]
    registry = FakeRegistry(reading(version="26.2.0"))

    result = freshness_check("python", facts, observe=registry)

    assert result.change == "RELEVANT_CHANGE"
    assert "26.1.0" in (result.detail or "") and "26.2.0" in (result.detail or "")
    assert result.provider_calls == 0
    assert registry.calls == [("python", "aspose-3d-foss")]


def test_the_same_release_is_no_change() -> None:
    result = freshness_check(
        "python", [name_fact(), version_fact("26.2.0")], observe=FakeRegistry(reading())
    )

    assert result.change == "NO_CHANGE"


def test_a_newer_release_the_readme_does_not_consume_is_irrelevant() -> None:
    result = freshness_check(
        "python",
        [name_fact(), version_fact("26.1.0")],
        observe=FakeRegistry(reading(version="26.2.0")),
        consumed_fact_ids={"install_command:pip"},
    )

    assert result.change == "IRRELEVANT_CHANGE"


def test_a_sealed_published_package_the_registry_no_longer_lists_is_relevant() -> None:
    result = freshness_check(
        "python",
        [name_fact(), version_fact("26.1.0")],
        observe=FakeRegistry(reading(published=False, version=None)),
    )

    assert result.change == "RELEVANT_CHANGE"


def test_without_a_sealed_version_fact_a_new_release_alone_is_no_change() -> None:
    # Every bundle sealed before package:published_version existed: a registry release it never
    # recorded must not read as a change, or the first check would reseal the whole portfolio.
    result = freshness_check(
        "python", [name_fact(), install_fact("found")], observe=FakeRegistry(reading())
    )

    assert result.change == "NO_CHANGE"


def test_without_a_sealed_version_fact_a_flipped_published_reading_is_relevant() -> None:
    withdrawn = freshness_check(
        "python",
        [name_fact(), install_fact("found")],
        observe=FakeRegistry(reading(published=False, version=None)),
    )
    appeared = freshness_check(
        "python",
        [name_fact(), install_fact("distribution not found on pypi")],
        observe=FakeRegistry(reading()),
    )

    assert withdrawn.change == "RELEVANT_CHANGE"
    assert appeared.change == "RELEVANT_CHANGE"


def test_an_inconclusive_or_failing_registry_is_unknown_never_a_change() -> None:
    facts = [name_fact(), version_fact("26.1.0")]

    ambiguous = freshness_check(
        "python", facts, observe=FakeRegistry(reading(published=True, ambiguous=True))
    )
    unread = freshness_check("python", facts, observe=FakeRegistry(reading(published=None)))
    raising = freshness_check("python", facts, observe=FakeRegistry(ConnectionError("down")))
    no_release = freshness_check("python", facts, observe=FakeRegistry(reading(version=None)))

    assert [r.change for r in (ambiguous, unread, raising, no_release)] == ["UNKNOWN"] * 4


def test_a_bundle_with_no_package_fact_has_nothing_to_recheck() -> None:
    registry = FakeRegistry(reading())

    result = freshness_check("cpp", [], observe=registry)

    assert result.change == "NO_CHANGE"
    assert registry.calls == []


# --- through the monitor ----------------------------------------------------------------------


def _observe(
    root: Path, registry: FakeRegistry | None, *, sealed_at: str, version: str = "26.1.0"
) -> Any:
    write_bundle(
        root,
        PYTHON_DIR,
        REVISION,
        "READY_FOR_PROPOSAL",
        facts=[name_fact(), version_fact(version)],
        manifest_extra={"sealed_at": sealed_at},
    )
    entry = Registry.model_validate(
        {"schema_version": 1, "entries": [monitor_registry_entry(PYTHON)]}
    ).entries[0]
    (row,) = observe_drift(
        root,
        [entry],
        token=TOKEN,
        read_head=FakeDefaultBranchReader({PYTHON: REVISION}),
        read_tree=lambda repository, revision, *, token=None: TreeRead(repository, revision),
        freshness_observe=registry,
        now=NOW,
    )
    return row


def test_an_old_bundle_whose_registry_release_moved_drifts_with_no_head_change(
    tmp_path: Path,
) -> None:
    registry = FakeRegistry(reading(version="26.2.0"))
    old = (NOW - timedelta(days=31)).isoformat()

    row = _observe(tmp_path, registry, sealed_at=old)

    assert (row.status, row.change) == ("DRIFTED", "RELEVANT_CHANGE")
    assert row.detail is not None and row.detail.startswith("freshness:")
    assert registry.calls == [("python", "aspose-3d-foss")]


def test_a_young_bundle_is_never_rechecked(tmp_path: Path) -> None:
    registry = FakeRegistry(reading(version="26.2.0"))
    young = (NOW - timedelta(days=2)).isoformat()

    row = _observe(tmp_path, registry, sealed_at=young)

    assert (row.status, row.change) == ("CURRENT", "NO_CHANGE")
    assert registry.calls == []


def test_without_the_probe_the_monitor_reads_no_registry(tmp_path: Path) -> None:
    old = (NOW - timedelta(days=90)).isoformat()

    row = _observe(tmp_path, None, sealed_at=old)

    assert (row.status, row.change) == ("CURRENT", "NO_CHANGE")


def test_an_old_bundle_whose_registry_is_down_stays_as_it_was(tmp_path: Path) -> None:
    registry = FakeRegistry(ConnectionError("down"))
    old = (NOW - timedelta(days=31)).isoformat()

    row = _observe(tmp_path, registry, sealed_at=old)

    assert (row.status, row.change) == ("CURRENT", "NO_CHANGE")
