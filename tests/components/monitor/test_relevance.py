"""Relevance-aware change classification (G7-W06, TC-REF-01): a head change that touches nothing the
sealed README consumed is not a reseal.

The classification is pure over the sealed scope and the trees read, and the monitor reads trees
through an injected reader, so no test here reaches the network.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.monitor.drift import (
    RepositoryDrift,
    assemble_drift_contract,
    drift_document,
    observe_drift,
    write_drift_document,
)
from repository_presenter.components.monitor.relevance import (
    LiveObservation,
    SealedScope,
    classify_change,
    load_scope,
)
from repository_presenter.core.github.read_client import TreeRead
from repository_presenter.core.registry.models import Registry
from repository_presenter.core.sealing_plan import parse_drift_contract, plan_sealing_run
from support import FakeDefaultBranchReader, monitor_registry_entry, write_bundle

TOKEN = "ghs_fixture_read_token_value_0123456789"
SEALED = "1" * 40
HEAD = "2" * 40
PYTHON = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
PYTHON_DIR = "aspose-3d-foss__Aspose.3D-FOSS-for-Python"
README = "README.md"
POM = "pom.xml"
SOURCE = "src/api.py"
VERSION_FILE = "gradle.properties"
CHANGELOG = "CHANGELOG.md"
SEALED_FILES = {
    README: "a1" * 20,
    POM: "b2" * 20,
    SOURCE: "c3" * 20,
    VERSION_FILE: "d4" * 20,
    CHANGELOG: "e5" * 20,
    "docs/guide.md": "f6" * 20,
}


def tree(files: Mapping[str, str], revision: str = HEAD) -> TreeRead:
    return TreeRead(PYTHON, revision, paths=tuple(sorted(files)), blob_shas=dict(files))


def fact(fact_id: str, *paths: str) -> dict[str, Any]:
    return {"id": fact_id, "evidence": [{"path": p, "detail": None} for p in paths]}


# The README states the install command (manifest) and an API symbol (source); the release
# version lives in gradle.properties, cited only by a fact the README does not state.
FACTS = [
    fact("install_command:pip", POM),
    fact("public_symbol:Api", SOURCE),
    fact("package:version", VERSION_FILE),
    fact("link_target:badge", "https://img.shields.io/x.svg"),
    fact("build_test_asset:docs", "docs/"),
]
BLOBS = {README: SEALED_FILES[README], POM: SEALED_FILES[POM], SOURCE: SEALED_FILES[SOURCE]}
BLOBS_WITH_VERSION = {**BLOBS, VERSION_FILE: SEALED_FILES[VERSION_FILE]}


def scope_with_blobs(**kwargs: Any) -> SealedScope:
    fact_paths = {
        f["id"]: frozenset(e["path"] for e in f["evidence"] if "://" not in e["path"])
        for f in FACTS
    }
    return SealedScope(SEALED, BLOBS_WITH_VERSION, fact_paths, **kwargs)


def scope_without_blobs(**kwargs: Any) -> SealedScope:
    fact_paths = {
        f["id"]: frozenset(e["path"] for e in f["evidence"] if "://" not in e["path"])
        for f in FACTS
    }
    return SealedScope(SEALED, {}, fact_paths, **kwargs)


# --- the pure classification, recorded-blob mode ----------------------------------------------


def test_a_version_bump_only_commit_is_irrelevant_when_the_version_is_not_consumed() -> None:
    # PDF-Java's release chore: only the version file moved. The README states the install command
    # and an API symbol, not the version, so the bundle's consumed facts exclude package:version.
    scope = scope_with_blobs(
        consumed_fact_ids=frozenset({"install_command:pip", "public_symbol:Api"})
    )
    bumped = {**BLOBS_WITH_VERSION, VERSION_FILE: "99" * 20, CHANGELOG: "98" * 20}

    result = classify_change(scope, LiveObservation(HEAD, head_tree=tree(bumped)))

    assert result.change == "IRRELEVANT_CHANGE"
    assert result.changed_paths == ()


def test_the_same_bump_is_relevant_when_the_readme_consumes_the_version() -> None:
    scope = scope_with_blobs(
        consumed_fact_ids=frozenset({"package:version", "install_command:pip"})
    )
    bumped = {**BLOBS_WITH_VERSION, VERSION_FILE: "99" * 20}

    result = classify_change(scope, LiveObservation(HEAD, head_tree=tree(bumped)))

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == (VERSION_FILE,)


def test_without_consumed_fact_ids_every_recorded_path_is_consumed() -> None:
    # The other lane's field is absent: the version file is a recorded, fact-cited path, so its
    # change is relevant. Never guess a fact is unconsumed.
    bumped = {**BLOBS_WITH_VERSION, VERSION_FILE: "99" * 20}

    result = classify_change(scope_with_blobs(), LiveObservation(HEAD, head_tree=tree(bumped)))

    assert result.change == "RELEVANT_CHANGE"


def test_a_maintainer_readme_edit_is_relevant_even_when_no_fact_cites_it() -> None:
    # README is recorded structurally (no fact cites it), so it is consumed whatever the facts say.
    scope = scope_with_blobs(consumed_fact_ids=frozenset({"public_symbol:Api"}))
    edited = {**BLOBS_WITH_VERSION, README: "77" * 20}

    result = classify_change(scope, LiveObservation(HEAD, head_tree=tree(edited)))

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == (README,)


def test_a_changed_consumed_manifest_is_relevant() -> None:
    edited = {**BLOBS_WITH_VERSION, POM: "66" * 20}

    result = classify_change(scope_with_blobs(), LiveObservation(HEAD, head_tree=tree(edited)))

    assert result.change == "RELEVANT_CHANGE"
    assert POM in (result.detail or "")


def test_a_deleted_consumed_path_is_relevant() -> None:
    without_source = {k: v for k, v in BLOBS_WITH_VERSION.items() if k != SOURCE}

    result = classify_change(
        scope_with_blobs(), LiveObservation(HEAD, head_tree=tree(without_source))
    )

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == (SOURCE,)


def test_an_unchanged_head_with_unchanged_blobs_is_no_change() -> None:
    result = classify_change(
        scope_with_blobs(), LiveObservation(SEALED, head_tree=tree(BLOBS_WITH_VERSION, SEALED))
    )

    assert result.change == "NO_CHANGE"


def test_an_unreadable_head_is_unreachable() -> None:
    assert classify_change(scope_with_blobs(), LiveObservation(None)).change == "UNREACHABLE"


@pytest.mark.parametrize(
    "head_tree",
    [
        None,
        TreeRead(PYTHON, HEAD, error="HTTP 503"),
        TreeRead(PYTHON, HEAD, paths=(README,), truncated=True, blob_shas={README: "a1" * 20}),
        TreeRead(PYTHON, HEAD, paths=(README,)),
    ],
    ids=["not-read", "error", "truncated", "no-blob-ids"],
)
def test_a_tree_that_cannot_be_judged_is_unknown_never_a_change(head_tree: TreeRead | None) -> None:
    result = classify_change(scope_with_blobs(), LiveObservation(HEAD, head_tree=head_tree))

    assert result.change == "UNKNOWN"


# --- the conservative fallback: no recorded blob ids ------------------------------------------


def test_fallback_a_version_bump_that_touches_no_cited_path_is_irrelevant() -> None:
    sealed_tree = tree(SEALED_FILES, SEALED)
    head_tree = tree({**SEALED_FILES, CHANGELOG: "98" * 20, "release.txt": "97" * 20})
    scope = scope_without_blobs(consumed_fact_ids=frozenset({"install_command:pip"}))

    result = classify_change(scope, LiveObservation(HEAD, head_tree, sealed_tree))

    assert result.change == "IRRELEVANT_CHANGE"


def test_fallback_a_changed_cited_path_is_relevant() -> None:
    head_tree = tree({**SEALED_FILES, SOURCE: "99" * 20})

    result = classify_change(
        scope_without_blobs(), LiveObservation(HEAD, head_tree, tree(SEALED_FILES, SEALED))
    )

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == (SOURCE,)


def test_fallback_a_readme_edit_is_relevant_even_though_no_fact_cites_it() -> None:
    head_tree = tree({**SEALED_FILES, README: "77" * 20})

    result = classify_change(
        scope_without_blobs(), LiveObservation(HEAD, head_tree, tree(SEALED_FILES, SEALED))
    )

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == (README,)


def test_fallback_a_change_inside_a_cited_directory_is_relevant() -> None:
    head_tree = tree({**SEALED_FILES, "docs/new.md": "55" * 20})

    result = classify_change(
        scope_without_blobs(), LiveObservation(HEAD, head_tree, tree(SEALED_FILES, SEALED))
    )

    assert result.change == "RELEVANT_CHANGE"
    assert result.changed_paths == ("docs/",)


def test_fallback_with_unreadable_facts_is_unknown() -> None:
    scope = SealedScope(SEALED, {}, None)

    result = classify_change(
        scope, LiveObservation(HEAD, tree(SEALED_FILES), tree(SEALED_FILES, SEALED))
    )

    assert result.change == "UNKNOWN"


@pytest.mark.parametrize("missing", ["sealed", "head"])
def test_fallback_with_either_tree_unreadable_is_unknown(missing: str) -> None:
    bad = TreeRead(PYTHON, HEAD, error="HTTP 502")
    sealed_tree = bad if missing == "sealed" else tree(SEALED_FILES, SEALED)
    head_tree = bad if missing == "head" else tree(SEALED_FILES)

    result = classify_change(scope_without_blobs(), LiveObservation(HEAD, head_tree, sealed_tree))

    assert result.change == "UNKNOWN"
    assert "502" in (result.detail or "")


# --- through the monitor: bundle on disk, injected readers ------------------------------------


class TreeBySha:
    """A tree reader that answers per revision and records which revisions were read."""

    def __init__(self, trees: Mapping[str, Mapping[str, str]]) -> None:
        self.trees = trees
        self.calls: list[str] = []

    def __call__(self, repository: str, revision: str, *, token: str | None = None) -> TreeRead:
        self.calls.append(revision)
        return tree(self.trees[revision], revision)


def observe(root: Path, reader: TreeBySha, head: str = HEAD) -> RepositoryDrift:
    entry = Registry.model_validate(
        {"schema_version": 1, "entries": [monitor_registry_entry(PYTHON)]}
    ).entries[0]
    (row,) = observe_drift(
        root,
        [entry],
        token=TOKEN,
        read_head=FakeDefaultBranchReader({PYTHON: head}),
        read_tree=reader,
    )
    return row


def test_monitor_on_a_bundle_without_blob_ids_reads_both_trees_and_judges_the_facts(
    tmp_path: Path,
) -> None:
    write_bundle(tmp_path, PYTHON_DIR, SEALED, "READY_FOR_PROPOSAL", facts=FACTS)
    bumped = {**SEALED_FILES, CHANGELOG: "98" * 20}
    reader = TreeBySha({SEALED: SEALED_FILES, HEAD: bumped})

    row = observe(tmp_path, reader)

    assert (row.status, row.change) == ("CURRENT", "IRRELEVANT_CHANGE")
    assert sorted(reader.calls) == sorted([SEALED, HEAD])


def test_monitor_on_a_bundle_without_blob_ids_sees_a_manifest_change(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, SEALED, "READY_FOR_PROPOSAL", facts=FACTS)
    edited = {**SEALED_FILES, POM: "66" * 20}

    row = observe(tmp_path, TreeBySha({SEALED: SEALED_FILES, HEAD: edited}))

    assert (row.status, row.change) == ("DRIFTED", "RELEVANT_CHANGE")
    assert row.detail is not None and POM in row.detail


def test_monitor_reads_consumed_fact_ids_from_the_manifest(tmp_path: Path) -> None:
    write_bundle(
        tmp_path,
        PYTHON_DIR,
        SEALED,
        "READY_FOR_PROPOSAL",
        upstream_blobs=BLOBS_WITH_VERSION,
        facts=FACTS,
        manifest_extra={"consumed_fact_ids": ["install_command:pip", "public_symbol:Api"]},
    )
    bumped = {**BLOBS_WITH_VERSION, VERSION_FILE: "99" * 20}
    reader = TreeBySha({HEAD: bumped})

    row = observe(tmp_path, reader)

    assert (row.status, row.change) == ("CURRENT", "IRRELEVANT_CHANGE")
    assert reader.calls == [HEAD]


def test_load_scope_reads_consumed_fact_ids_from_dependencies_json(tmp_path: Path) -> None:
    bundle = write_bundle(
        tmp_path, PYTHON_DIR, SEALED, "READY_FOR_PROPOSAL", upstream_blobs=BLOBS, facts=FACTS
    )
    (bundle / "dependencies.json").write_text(
        '{"consumed_fact_ids": ["public_symbol:Api"]}', encoding="utf-8"
    )

    scope = load_scope(bundle, SEALED, {"upstream_blobs": BLOBS})

    assert scope.consumed_fact_ids == frozenset({"public_symbol:Api"})


def test_a_malformed_consumed_fact_ids_field_is_never_read_as_an_empty_consumption(
    tmp_path: Path,
) -> None:
    bundle = write_bundle(tmp_path, PYTHON_DIR, SEALED, "READY_FOR_PROPOSAL", facts=FACTS)

    scope = load_scope(bundle, SEALED, {"consumed_fact_ids": "install_command:pip"})

    assert scope.consumed_fact_ids is None


def test_monitor_tree_failure_during_a_moved_head_is_unknown(tmp_path: Path) -> None:
    write_bundle(tmp_path, PYTHON_DIR, SEALED, "READY_FOR_PROPOSAL", facts=FACTS)

    def failing(repository: str, revision: str, *, token: str | None = None) -> TreeRead:
        raise ConnectionError(f"reset with {token}")

    entry = Registry.model_validate(
        {"schema_version": 1, "entries": [monitor_registry_entry(PYTHON)]}
    ).entries[0]
    (row,) = observe_drift(
        tmp_path,
        [entry],
        token=TOKEN,
        read_head=FakeDefaultBranchReader({PYTHON: HEAD}),
        read_tree=failing,
    )

    assert (row.status, row.change) == ("UNKNOWN", "UNKNOWN")
    assert TOKEN not in (row.detail or "")


# --- the handoff to the sealing plan ----------------------------------------------------------

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
JAVA = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"


def _plan_registry(*repositories: str) -> Registry:
    raw = [
        monitor_registry_entry(repository, mode="full", repository_id=index)
        for index, repository in enumerate(repositories, start=1)
    ]
    return Registry.model_validate({"schema_version": 1, "entries": raw})


def _contract(tmp_path: Path, rows: list[RepositoryDrift]) -> dict[str, Any]:
    stamp = (NOW - timedelta(hours=1)).isoformat(timespec="seconds")
    write_drift_document(
        drift_document(rows, observed_at=stamp, owner="aspose-3d-foss"),
        tmp_path / "drift-aspose-3d-foss.json",
    )
    expected = {"aspose-3d-foss": frozenset(r.repository for r in rows)}
    return assemble_drift_contract(tmp_path, expected=expected, now=NOW).document


def test_the_plan_selects_a_relevant_change_and_never_an_irrelevant_one(tmp_path: Path) -> None:
    rows = [
        RepositoryDrift(PYTHON, "full", "DRIFTED", HEAD, "main", SEALED, "x", "RELEVANT_CHANGE"),
        RepositoryDrift(JAVA, "full", "CURRENT", HEAD, "main", SEALED, "y", "IRRELEVANT_CHANGE"),
    ]

    contract = _contract(tmp_path, rows)
    statuses = {r["repository"]: r["status"] for r in contract["repositories"]}
    plan = plan_sealing_run(parse_drift_contract(contract), _plan_registry(PYTHON, JAVA), now=NOW)

    assert statuses == {PYTHON: "RELEVANT_CHANGE", JAVA: "IRRELEVANT_CHANGE"}
    assert plan.selected == (PYTHON,)


def test_evidence_without_a_change_field_selects_exactly_as_before(tmp_path: Path) -> None:
    rows = [
        RepositoryDrift(PYTHON, "full", "DRIFTED", HEAD, "main", SEALED),
        RepositoryDrift(JAVA, "full", "CURRENT", HEAD, "main", SEALED),
    ]

    contract = _contract(tmp_path, rows)
    plan = plan_sealing_run(parse_drift_contract(contract), _plan_registry(PYTHON, JAVA), now=NOW)

    statuses = {r["repository"]: r["status"] for r in contract["repositories"]}
    assert statuses == {PYTHON: "DRIFTED", JAVA: "CURRENT"}
    assert plan.selected == (PYTHON,)
