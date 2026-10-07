"""Seal-time recording of the upstream blob ids a candidate depends on (the drift monitor's content
check reads them back from the manifest). The blob ids come from the transaction's own tree
listing, so these tests need no clone and no network."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.readme.bundle.seal import record_upstream_blobs
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REVISION = "1" * 40
LICENSE_BLOB = "a" * 40
EXAMPLE_BLOB = "b" * 40
README_BLOB = "c" * 40
UNRELATED_BLOB = "d" * 40
TREE = (
    f"100644 blob {LICENSE_BLOB}\tLICENSE\n"
    f"040000 tree {'e' * 40}\texamples\n"
    f"100644 blob {EXAMPLE_BLOB}\texamples/demo.py\n"
    f"100644 blob {README_BLOB}\tREADME.md\n"
    f"100644 blob {UNRELATED_BLOB}\tdocs/notes.md\n"
)


def facts_citing(*paths: str) -> FactsDocument:
    fact = Fact(
        id="package:demo",
        kind="package",
        value="demo",
        evidence=tuple(Evidence(path) for path in paths),
    )
    return FactsDocument(repository="o/r", source_revision=REVISION, facts=(fact,))


def write_source(transaction: Path, *, tree: str | None = TREE) -> None:
    source = transaction / "source"
    source.mkdir(parents=True)
    if tree is not None:
        (source / "tree.txt").write_text(tree, encoding="utf-8")
    snapshot = {
        "readme_path": "README.md",
        "license_path": "LICENSE",
        "notices_path": None,
    }
    (source / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")


def test_records_the_blob_ids_of_cited_files_and_the_readme_and_license(tmp_path: Path) -> None:
    write_source(tmp_path)

    recorded = record_upstream_blobs(tmp_path, facts_citing("examples/demo.py"))

    assert recorded == {
        "LICENSE": LICENSE_BLOB,
        "README.md": README_BLOB,
        "examples/demo.py": EXAMPLE_BLOB,
    }


def test_an_uncited_file_is_not_recorded(tmp_path: Path) -> None:
    # Negative control: docs/notes.md is in the tree but no fact cites it, so it is not a
    # dependency and changing it can never drift the repository.
    write_source(tmp_path)

    recorded = record_upstream_blobs(tmp_path, facts_citing("examples/demo.py"))

    assert "docs/notes.md" not in recorded


def test_a_cited_path_that_is_not_a_blob_is_not_recorded(tmp_path: Path) -> None:
    write_source(tmp_path)

    recorded = record_upstream_blobs(tmp_path, facts_citing("examples"))

    assert "examples" not in recorded


def test_a_transaction_without_its_source_listing_records_nothing(tmp_path: Path) -> None:
    # Nothing recorded means the monitor reads the bundle as UNKNOWN, never CURRENT.
    write_source(tmp_path, tree=None)

    assert record_upstream_blobs(tmp_path, facts_citing("examples/demo.py")) == {}
