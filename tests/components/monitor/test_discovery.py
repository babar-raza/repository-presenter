"""Registry discovery: the allow-list reconciled against the organizations it was drawn from.

The reality tests reproduce 2026-10-11, when GitHub held 46 repositories in the 15 authorized
organizations and the registry admitted 36 of them (the owner's finding: the count was exact for
the registry and silent about the world). The negative controls pin the part that must never
change: discovery admits nothing, lists only the organizations the registry names, reads no
repository a second time, and never turns an incomplete listing into an absence.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.monitor import discovery
from repository_presenter.components.monitor.discovery import (
    EXCLUSIONS_RELATIVE_PATH,
    DiscoveryReport,
    Exclusions,
    OrganizationDiscovery,
    discover,
    discovery_document,
    load_discovery,
    load_exclusions,
    merge_reports,
    observe_registry_gaps,
    reconcile_organization,
    registry_status_json,
    status_lines,
    summary_markdown,
    workflow_annotations,
)
from repository_presenter.components.monitor.drift import SCHEMA_VERSION, drift_document
from repository_presenter.components.monitor.org_listing import (
    OrganizationListing,
    UpstreamRepository,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.registry.loader import load_registry
from repository_presenter.core.registry.models import Registry, RegistryEntry
from support import (
    REPO_ROOT,
    TODAYS_UNADMITTED,
    TODAYS_UNREGISTERED,
    FakeOrganizationLister,
    mirror,
    monitor_registry_entry,
    registry_without_todays_unadmitted,
    with_extra,
)

TOKEN = "ghs_fixture_discovery_read_token_0123456789"
NOW = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
OBSERVED = NOW.isoformat(timespec="seconds")
REGISTRY_PATH = REPO_ROOT / "data" / "registry.json"
EXCLUSIONS_PATH = REPO_ROOT / EXCLUSIONS_RELATIVE_PATH

PYTHON_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
JAVA_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
PYTHON_CELLS = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"


def _registry(*pairs: tuple[str, int]) -> Registry:
    return Registry(
        entries=tuple(
            RegistryEntry.model_validate(monitor_registry_entry(name, repository_id=identity))
            for name, identity in pairs
        )
    )


def _exclusions() -> Exclusions:
    return load_exclusions(EXCLUSIONS_PATH)


def _report(registry: Registry, lister: FakeOrganizationLister, **kwargs: Any) -> DiscoveryReport:
    return discover(
        registry, _exclusions(), lister=lister, token=TOKEN, observed_at=OBSERVED, **kwargs
    )


def _repo(full_name: str, identity: int, **flags: Any) -> UpstreamRepository:
    return UpstreamRepository(full_name, identity, default_branch="main", **flags)


# --- Today's reality ---


def test_todays_reality_is_detected_36_admitted_9_unregistered_1_excluded() -> None:
    registry = registry_without_todays_unadmitted(REGISTRY_PATH)
    admitted = len(registry.entries)
    lister = FakeOrganizationLister(with_extra(mirror(registry.entries), TODAYS_UNADMITTED))

    report = _report(registry, lister)

    counts = report.counts()
    assert counts == {
        "REGISTERED": admitted,
        "UNREGISTERED": 9,
        "EXCLUDED_BY_POLICY": 1,
        "MISSING_UPSTREAM": 0,
    }
    assert report.listed == admitted + 10 and report.admitted == admitted
    assert {row.repository for row in report.unregistered} == set(TODAYS_UNREGISTERED)
    assert sum("JMAP" in row.repository for row in report.unregistered) == 8
    assert "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go-MCP" in {
        r.repository for r in report.unregistered
    }
    (profile,) = report.excluded
    assert profile.repository == "aspose-slides-foss/.github"
    assert profile.reason == "org-profile-repository" and profile.detail
    assert report.complete and report.missing_upstream == ()


def test_the_real_registry_and_policy_load_and_the_registry_is_what_it_was() -> None:
    registry = load_registry(REGISTRY_PATH)
    exclusions = _exclusions()

    assert {rule.id for rule in exclusions.rules} >= {"org-profile-repository", "archived", "fork"}
    assert all(rule.reason for rule in exclusions.rules)
    assert exclusions.repositories == ()
    # Every registry owner would be listed, and only those.
    owners = {entry.owner for entry in registry.entries}
    lister = FakeOrganizationLister(mirror(registry.entries))
    _report(registry, lister)
    assert sorted(lister.calls) == sorted(owners)


# --- Negative controls: discovery never admits, never reaches further ---


def test_discovery_admits_nothing_and_leaves_registry_and_denominator_alone() -> None:
    registry = registry_without_todays_unadmitted(REGISTRY_PATH)
    before_file = REGISTRY_PATH.read_bytes()
    before_entries = registry.model_dump_json()
    lister = FakeOrganizationLister(with_extra(mirror(registry.entries), TODAYS_UNADMITTED))

    report = _report(registry, lister)

    assert registry.model_dump_json() == before_entries
    assert REGISTRY_PATH.read_bytes() == before_file
    assert len(registry.entries) == report.counts()["REGISTERED"]
    admitted_names = {entry.repository for entry in registry.entries}
    assert not admitted_names & set(TODAYS_UNREGISTERED)
    assert not hasattr(discovery, "admit") and not hasattr(report, "admit")


def test_only_registry_organizations_are_listed_each_exactly_once_with_the_given_token() -> None:
    registry = _registry((PYTHON_3D, 10), (JAVA_3D, 11), (PYTHON_CELLS, 12))
    stray = _repo("aspose-unlisted-foss/Aspose.X-FOSS-for-Python", 99)
    lister = FakeOrganizationLister({**mirror(registry.entries), stray.owner: [stray]})

    report = _report(registry, lister)

    assert lister.calls == ["aspose-3d-foss", "aspose-cells-foss"]
    assert lister.tokens == [TOKEN, TOKEN]
    # Nothing the registry does not name is ever reached, so the stray repository is unknown.
    assert stray.full_name not in {row.repository for row in report.unregistered}


def test_an_organization_outside_the_registry_is_refused_before_any_listing() -> None:
    registry = _registry((PYTHON_3D, 10))
    lister = FakeOrganizationLister({})

    with pytest.raises(ConfigError, match="not an organization in the registry"):
        _report(registry, lister, organization="aspose-nope-foss")

    assert lister.calls == []


def test_the_organization_filter_lists_only_that_organization() -> None:
    registry = _registry((PYTHON_3D, 10), (PYTHON_CELLS, 12))
    lister = FakeOrganizationLister(mirror(registry.entries))

    report = _report(registry, lister, organization="ASPOSE-CELLS-FOSS")

    assert lister.calls == ["aspose-cells-foss"]
    assert [item.organization for item in report.organizations] == ["aspose-cells-foss"]


# --- MISSING_UPSTREAM and the rename pair ---


def test_a_rename_is_a_missing_upstream_and_unregistered_pair_joined_by_repository_id() -> None:
    registry = _registry((PYTHON_3D, 10), (JAVA_3D, 11))
    renamed = "aspose-3d-foss/Aspose.3D-FOSS-for-Java-Next"
    lister = FakeOrganizationLister({"aspose-3d-foss": [_repo(PYTHON_3D, 10), _repo(renamed, 11)]})

    report = _report(registry, lister)

    (missing,) = report.missing_upstream
    (new,) = report.unregistered
    assert (missing.repository, missing.reason, missing.renamed_to) == (JAVA_3D, "renamed", renamed)
    assert (new.repository, new.renamed_from) == (renamed, JAVA_3D)
    assert report.counts()["REGISTERED"] == 1
    assert report.complete  # a rename is a finding, not an incompleteness


def test_a_deleted_or_transferred_repository_is_missing_upstream() -> None:
    registry = _registry((PYTHON_3D, 10), (JAVA_3D, 11))
    lister = FakeOrganizationLister({"aspose-3d-foss": [_repo(PYTHON_3D, 10)]})

    report = _report(registry, lister)

    (missing,) = report.missing_upstream
    assert (missing.repository, missing.reason, missing.repository_id) == (JAVA_3D, "not_found", 11)
    assert report.unregistered == ()


def test_the_name_re_created_with_a_different_id_is_not_the_admitted_repository() -> None:
    registry = _registry((PYTHON_3D, 10))
    lister = FakeOrganizationLister({"aspose-3d-foss": [_repo(PYTHON_3D, 777)]})

    report = _report(registry, lister)

    (missing,) = report.missing_upstream
    (impostor,) = report.unregistered
    assert missing.reason == "identity_changed" and "777" in (missing.detail or "")
    assert impostor.repository == PYTHON_3D and impostor.repository_id == 777
    assert report.counts()["REGISTERED"] == 0


def test_an_archived_admitted_repository_is_missing_upstream_and_counted_once() -> None:
    registry = _registry((PYTHON_3D, 10))
    lister = FakeOrganizationLister({"aspose-3d-foss": [_repo(PYTHON_3D, 10, archived=True)]})

    report = _report(registry, lister)

    (missing,) = report.missing_upstream
    assert missing.reason == "archived"
    assert report.counts() == {
        "REGISTERED": 0,
        "UNREGISTERED": 0,
        "EXCLUDED_BY_POLICY": 0,
        "MISSING_UPSTREAM": 1,
    }


def test_an_incomplete_listing_never_becomes_an_absence() -> None:
    registry = _registry((PYTHON_3D, 10), (JAVA_3D, 11), (PYTHON_CELLS, 12))
    lister = FakeOrganizationLister(
        {"aspose-3d-foss": [_repo(PYTHON_3D, 10)], "aspose-cells-foss": [_repo(PYTHON_CELLS, 12)]},
        errors={"aspose-cells-foss": "HTTP 403"},
        truncated=["aspose-3d-foss"],
    )

    report = _report(registry, lister)

    by_name = {item.organization: item for item in report.organizations}
    # Truncated: Java is not in the prefix, which proves nothing. Failed: no rows at all.
    assert report.missing_upstream == ()
    assert by_name["aspose-3d-foss"].truncated and by_name["aspose-3d-foss"].registered == 1
    assert (
        by_name["aspose-cells-foss"].error == "HTTP 403" and by_name["aspose-cells-foss"].rows == ()
    )
    assert not report.complete
    assert [item.organization for item in report.incomplete_organizations] == [
        "aspose-3d-foss",
        "aspose-cells-foss",
    ]


def test_a_lister_that_raises_is_isolated_and_its_message_carries_no_token() -> None:
    registry = _registry((PYTHON_3D, 10), (PYTHON_CELLS, 12))
    lister = FakeOrganizationLister(
        {"aspose-cells-foss": [_repo(PYTHON_CELLS, 12)]},
        errors={"aspose-3d-foss": RuntimeError(f"401 rejected {TOKEN}")},
    )

    report = _report(registry, lister)

    failed = next(item for item in report.organizations if item.organization == "aspose-3d-foss")
    assert failed.error is not None and TOKEN not in failed.error
    assert report.counts()["REGISTERED"] == 1  # the other organization still reconciled


# --- Exclusion policy ---


def test_policy_excludes_the_profile_repository_archived_repositories_and_forks() -> None:
    registry = _registry((PYTHON_3D, 10))
    extras = [
        _repo("aspose-3d-foss/.github", 20),
        _repo("aspose-3d-foss/.GitHub-Mirror", 21),
        _repo("aspose-3d-foss/Old-Thing", 22, archived=True),
        _repo("aspose-3d-foss/Somebody-Elses", 23, fork=True),
        _repo("aspose-3d-foss/Secret-Thing", 24, private=True),
        _repo("aspose-3d-foss/New-Product", 25),
    ]
    lister = FakeOrganizationLister(with_extra(mirror(registry.entries), extras))

    report = _report(registry, lister)

    excluded = {row.repository: row.reason for row in report.excluded}
    assert excluded == {
        "aspose-3d-foss/.github": "org-profile-repository",
        "aspose-3d-foss/Old-Thing": "archived",
        "aspose-3d-foss/Somebody-Elses": "fork",
    }
    # A private repository is a candidate (flagged), not silently excluded; a look-alike is not
    # the profile repository.
    assert {row.repository for row in report.unregistered} == {
        "aspose-3d-foss/.GitHub-Mirror",
        "aspose-3d-foss/Secret-Thing",
        "aspose-3d-foss/New-Product",
    }
    assert next(r for r in report.unregistered if r.repository.endswith("Secret-Thing")).private


def test_the_profile_repository_rule_is_case_insensitive_on_the_name() -> None:
    upstream = _repo("aspose-3d-foss/.GITHUB", 30)

    assert _exclusions().reason_for(upstream) is not None


def test_a_named_exclusion_applies_only_to_the_repository_id_it_names() -> None:
    exclusions = Exclusions.model_validate(
        {
            "schema_version": 1,
            "repositories": [
                {
                    "repository": "aspose-3d-foss/Sandbox",
                    "repository_id": 40,
                    "reason": "Owner decision: an internal sandbox, not a product.",
                }
            ],
        }
    )

    assert exclusions.reason_for(_repo("aspose-3d-foss/Sandbox", 40)) == (
        "listed",
        "Owner decision: an internal sandbox, not a product.",
    )
    assert exclusions.reason_for(_repo("aspose-3d-foss/Sandbox", 41)) is None
    assert exclusions.reason_for(_repo("aspose-3d-foss/Elsewhere", 40)) is None


@pytest.mark.parametrize(
    "document",
    [
        {"schema_version": 2},
        {"schema_version": 1, "unknown": []},
        {"schema_version": 1, "rules": [{"id": "r", "match": {}, "reason": "long enough reason"}]},
        {
            "schema_version": 1,
            "rules": [{"id": "r", "match": {"archived": "yes"}, "reason": "long enough reason"}],
        },
        {"schema_version": 1, "rules": [{"id": "r", "match": {"fork": True}, "reason": "short"}]},
        {
            "schema_version": 1,
            "rules": [{"id": "R!", "match": {"fork": True}, "reason": "long enough reason"}],
        },
        {
            "schema_version": 1,
            "rules": [{"id": "r", "match": {"fork": True, "x": 1}, "reason": "long enough reason"}],
        },
        {
            "schema_version": 1,
            "rules": [
                {"id": "r", "match": {"fork": True}, "reason": "long enough reason"},
                {"id": "r", "match": {"archived": True}, "reason": "long enough reason"},
            ],
        },
        {
            "schema_version": 1,
            "repositories": [{"repository": "no-slash", "reason": "long enough reason"}],
        },
        {
            "schema_version": 1,
            "repositories": [
                {"repository": "a/b", "reason": "long enough reason"},
                {"repository": "A/B", "reason": "long enough reason"},
            ],
        },
    ],
)
def test_a_malformed_policy_file_fails_closed(tmp_path: Path, document: dict[str, Any]) -> None:
    path = tmp_path / "exclusions.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ConfigError, match="registry exclusions"):
        load_exclusions(path)


def test_a_missing_or_unparseable_policy_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_exclusions(tmp_path / "absent.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError, match="not readable JSON"):
        load_exclusions(broken)


def test_an_unreadable_policy_makes_discovery_a_typed_failure_with_no_listing(
    tmp_path: Path,
) -> None:
    registry = _registry((PYTHON_3D, 10))
    lister = FakeOrganizationLister(mirror(registry.entries))

    report = observe_registry_gaps(tmp_path, registry, lister=lister, token=TOKEN, now=NOW)

    assert report.error is not None and "registry exclusions not found" in report.error
    assert lister.calls == [] and report.organizations == () and not report.complete


def test_observe_registry_gaps_reads_the_projects_policy_file(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / EXCLUSIONS_RELATIVE_PATH).write_bytes(EXCLUSIONS_PATH.read_bytes())
    registry = _registry((PYTHON_3D, 10))
    extras = [_repo("aspose-3d-foss/.github", 20)]
    lister = FakeOrganizationLister(with_extra(mirror(registry.entries), extras))

    report = observe_registry_gaps(tmp_path, registry, lister=lister, token=TOKEN, now=NOW)

    assert report.observed_at == OBSERVED and report.error is None
    assert report.counts()["EXCLUDED_BY_POLICY"] == 1


def test_reconcile_is_pure_over_a_listing_and_never_touches_the_registry() -> None:
    registry = _registry((PYTHON_3D, 10))
    listing = OrganizationListing(
        "aspose-3d-foss", (_repo(PYTHON_3D, 10), _repo("aspose-3d-foss/New", 5))
    )

    result = reconcile_organization("aspose-3d-foss", registry.entries, listing, _exclusions())

    assert (result.admitted, result.listed, result.registered) == (1, 2, 1)
    assert [row.repository for row in result.rows] == ["aspose-3d-foss/New"]
    assert len(registry.entries) == 1


def discovery_row(name: str) -> discovery.DiscoveryRow:
    return discovery.DiscoveryRow(
        name, "UNREGISTERED", 1, language="Go", pushed_at="2026-09-26T20:04:12Z"
    )


# --- Evidence: the drift section, the standalone document, loading and merging ---


def _reality_report() -> DiscoveryReport:
    registry = registry_without_todays_unadmitted(REGISTRY_PATH)
    lister = FakeOrganizationLister(with_extra(mirror(registry.entries), TODAYS_UNADMITTED))
    return _report(registry, lister)


def test_the_section_round_trips_and_carries_counts_and_the_unregistered_list() -> None:
    report = _reality_report()

    section = report.to_json()
    again = DiscoveryReport.from_json(json.loads(json.dumps(section)))

    assert section["counts"] == report.counts() and section["complete"] is True
    assert len(section["unregistered"]) == 9 and len(section["excluded_by_policy"]) == 1
    assert section["missing_upstream"] == []
    assert again.to_json() == section
    assert again.counts() == report.counts()


def test_drift_document_gains_a_discovery_section_without_changing_schema_one() -> None:
    plain = drift_document([], observed_at=OBSERVED, owner=None)
    with_section = drift_document(
        [], observed_at=OBSERVED, owner=None, discovery=_reality_report().to_json()
    )

    assert "discovery" not in plain
    assert with_section["schema_version"] == plain["schema_version"] == SCHEMA_VERSION
    assert {k: v for k, v in with_section.items() if k != "discovery"} == plain
    assert with_section["discovery"]["counts"]["UNREGISTERED"] == 9


def test_load_discovery_reads_drift_documents_and_ignores_install_records(tmp_path: Path) -> None:
    section = _reality_report().to_json()
    (tmp_path / "drift-aspose-email-foss.json").write_text(
        json.dumps(
            drift_document([], observed_at=OBSERVED, owner="aspose-email-foss", discovery=section)
        ),
        encoding="utf-8",
    )
    (tmp_path / "install-aspose-email-foss.json").write_text(
        json.dumps({"owner": "aspose-email-foss", "state": "INSTALLED"}), encoding="utf-8"
    )
    (tmp_path / "drift-old.json").write_text(
        json.dumps(drift_document([], observed_at=OBSERVED, owner="old")), encoding="utf-8"
    )

    report = load_discovery(tmp_path)

    assert report is not None and report.counts()["UNREGISTERED"] == 9


def test_load_discovery_is_none_without_a_section_and_strict_about_bad_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "drift.json").write_text(json.dumps({"repositories": []}), encoding="utf-8")
    assert load_discovery(tmp_path) is None

    with pytest.raises(ConfigError, match="not found"):
        load_discovery(tmp_path / "absent")
    (tmp_path / "bad.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(ConfigError, match="unreadable"):
        load_discovery(tmp_path)
    (tmp_path / "bad.json").write_text(
        json.dumps({"discovery": {"observed_at": "x"}}), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="malformed"):
        load_discovery(tmp_path)


def test_the_standalone_document_loads_like_a_drift_section(tmp_path: Path) -> None:
    report = _reality_report()
    path = tmp_path / "gaps.json"
    path.write_text(json.dumps(discovery_document(report)), encoding="utf-8")

    loaded = load_discovery(path)

    assert loaded is not None and loaded.to_json() == report.to_json()


def test_merge_keeps_the_newest_word_per_organization_and_the_oldest_stamp() -> None:
    old = DiscoveryReport(
        "2026-10-11T06:00:00+00:00",
        (
            OrganizationDiscovery("aspose-3d-foss", 2, 2, 2),
            OrganizationDiscovery("aspose-cells-foss", 1, 1, 1),
        ),
    )
    new = DiscoveryReport(
        "2026-10-11T12:00:00+00:00",
        (OrganizationDiscovery("aspose-3d-foss", 2, 3, 2, (discovery_row("aspose-3d-foss/New"),)),),
    )

    merged = merge_reports([new, old])

    assert merged is not None
    assert merged.observed_at == "2026-10-11T06:00:00+00:00"
    assert merged.counts()["UNREGISTERED"] == 1 and merged.listed == 4
    assert [item.organization for item in merged.organizations] == [
        "aspose-3d-foss",
        "aspose-cells-foss",
    ]
    assert merge_reports([]) is None


# --- Presentation ---


def test_the_status_line_is_a_separate_line_that_leaves_the_denominator_alone() -> None:
    report = _reality_report()
    admitted = report.counts()["REGISTERED"]

    (line,) = status_lines(admitted, report, authorized_organizations=15)

    assert line.startswith(
        f"registry: {admitted} admitted; 9 unregistered in authorized organizations "
        "(list with --verbose)"
    )
    assert "1 excluded by policy" in line and f"observed {OBSERVED}" in line
    assert "incomplete" not in line


def test_verbose_status_lists_each_repository_with_what_the_owner_needs() -> None:
    report = _reality_report()

    lines = status_lines(36, report, authorized_organizations=15, verbose=True)

    assert "(list with --verbose)" not in lines[0]
    joined = "\n".join(lines)
    assert (
        "unregistered: aspose-email-foss/Aspose.JMAP-FOSS-for-Python "
        "(id 1389232730, Python, pushed 2026-09-26)"
    ) in joined
    assert "excluded by policy: aspose-slides-foss/.github" in joined


def test_the_status_line_says_when_discovery_was_not_observed_or_is_incomplete() -> None:
    (unobserved,) = status_lines(36, None, authorized_organizations=15)
    assert unobserved.startswith("registry: 36 admitted; discovery not observed (")

    partial = DiscoveryReport(OBSERVED, (OrganizationDiscovery("aspose-3d-foss", 4, 4, 4),))
    (line,) = status_lines(36, partial, authorized_organizations=15)
    assert "0 unregistered" in line
    assert "discovery incomplete (14 of 15 organizations not observed)" in line

    failed = DiscoveryReport(
        OBSERVED, (OrganizationDiscovery("aspose-3d-foss", 4, None, 0, error="HTTP 403"),)
    )
    (line,) = status_lines(4, failed, authorized_organizations=1)
    assert "discovery incomplete (1 organization(s) not fully listed)" in line


def test_status_json_adds_a_registry_key_with_the_section() -> None:
    report = _reality_report()

    payload = registry_status_json(36, 15, report)

    assert payload["admitted"] == 36 and payload["authorized_organizations"] == 15
    assert payload["discovery"]["counts"]["UNREGISTERED"] == 9
    assert registry_status_json(36, 15, None)["discovery"] is None


def test_annotations_are_warnings_that_name_the_unregistered_repositories() -> None:
    report = _reality_report()

    lines = workflow_annotations(report, authorized_organizations=15)

    assert len(lines) == 1
    assert lines[0].startswith("::warning title=Repositories not in the registry::9 repositor")
    for name in TODAYS_UNREGISTERED:
        assert name in lines[0]
    assert ".github" not in lines[0]  # the policy-excluded one is not a warning


def test_annotations_withhold_private_names_cap_the_list_and_escape_workflow_commands() -> None:
    rows = tuple(
        discovery.DiscoveryRow(f"aspose-3d-foss/Product-{n:02d}", "UNREGISTERED", n, private=n == 0)
        for n in range(30)
    )
    hostile = OrganizationDiscovery(
        "aspose-3d-foss", 1, 30, 0, rows, error="HTTP 403\n::error::injected%"
    )
    report = DiscoveryReport(OBSERVED, (hostile,))

    first, second = workflow_annotations(report, authorized_organizations=1)

    assert "Product-00" not in first and "(private repository, name withheld)" in first
    assert "and 5 more" in first and "Product-29" not in first
    assert "\n" not in second and "%0A::error::injected%25" in second


def test_annotations_flag_missing_upstream_and_incomplete_discovery_but_stay_quiet_when_clean() -> (
    None
):
    registry = _registry((PYTHON_3D, 10), (JAVA_3D, 11))
    lister = FakeOrganizationLister({"aspose-3d-foss": [_repo(PYTHON_3D, 10)]})
    report = _report(registry, lister)

    (missing_line,) = workflow_annotations(report, authorized_organizations=1)
    assert missing_line.startswith("::warning title=Admitted repositories missing upstream::")
    assert JAVA_3D in missing_line

    clean = _report(registry, FakeOrganizationLister(mirror(registry.entries)))
    assert workflow_annotations(clean, authorized_organizations=1) == []


def test_the_markdown_summary_tables_what_needs_an_owner_decision() -> None:
    report = _reality_report()
    admitted = report.counts()["REGISTERED"]

    text = summary_markdown(report, admitted=admitted, authorized_organizations=15)

    assert text.startswith("### Registry discovery")
    assert f"{admitted} admitted; **9 unregistered**" in text
    assert "| aspose-email-foss/Aspose.JMAP-FOSS-for-Go | Go | 2026-09-26 |" in text
    assert "admission is an owner act" in text
    assert "Discovery incomplete" not in text
