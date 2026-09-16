"""License facts come from the license text itself and never guess."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.evidence.facts.license import (
    DECLARED_LICENSE_DETAIL,
    classify_license_text,
    license_facts,
)
from repository_presenter.core.facts import Evidence


def test_classifies_known_license_texts() -> None:
    assert classify_license_text("MIT License\n\nCopyright...") == "MIT"
    assert classify_license_text("Apache License\nVersion 2.0, January 2004") == "Apache-2.0"
    assert classify_license_text("Some proprietary terms nobody wrote down properly.") is None


def test_mit_file_yields_file_and_spdx_facts(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    facts = license_facts(tmp_path, "LICENSE")
    assert [(f.id, f.value, f.polarity) for f in facts] == [
        ("license:file", "LICENSE", "SUPPORTED"),
        ("license:spdx", "MIT", "SUPPORTED"),
    ]
    assert facts[1].evidence[0].path == "LICENSE"


def test_nested_license_directory_still_classifies(tmp_path: Path) -> None:
    (tmp_path / "License").mkdir()
    (tmp_path / "License" / "LICENSE.txt").write_text(
        "This repository includes the MIT license. See below.\n\nMIT License\n...", "utf-8"
    )
    facts = license_facts(tmp_path, "License/LICENSE.txt")
    assert facts[1].value == "MIT"


def test_unrecognized_text_is_recorded_as_unresolved(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("All rights reserved, terms unclear.", "utf-8")
    facts = license_facts(tmp_path, "LICENSE")
    assert facts[1].value == "UNCLASSIFIED"
    assert facts[1].polarity == "UNRESOLVED"
    assert facts[1].confidence == 0.0


def test_no_license_file_yields_no_facts(tmp_path: Path) -> None:
    assert license_facts(tmp_path, None) == []


def test_a_manifest_declared_license_stands_in_when_no_license_file_exists(tmp_path: Path) -> None:
    """G4-W17 arrival item 51 (DIRECTIVE 2026-09-06 20:05 rule 1). Aspose.3D for TypeScript ships
    no LICENSE file and declares `"license": "MIT"` in package.json - the repository's own
    statement, and the only license evidence it carries. With no file to read, that declaration
    is the fact; where a file exists its text stays the evidence, so no sealed bundle's facts move
    (all ten CURRENT bundles carry license:file)."""
    facts = license_facts(tmp_path, None, declared="MIT", declared_in="package.json")
    assert [(f.id, f.value, f.polarity) for f in facts] == [("license:spdx", "MIT", "SUPPORTED")]
    assert facts[0].evidence == (Evidence("package.json", DECLARED_LICENSE_DETAIL),)
    assert DECLARED_LICENSE_DETAIL == (
        "license declared by the manifest; no license file at this revision"
    )
    # A declaration spelled as the licence's name classifies the way a file's text does.
    named = license_facts(tmp_path, None, declared="MIT License", declared_in="pyproject.toml")
    assert [(f.value, f.evidence[0].path) for f in named] == [("MIT", "pyproject.toml")]
    # A declaration naming nothing the classifier knows is not a fact the contract can render,
    # and an empty one is no declaration at all.
    assert license_facts(tmp_path, None, declared="SEE LICENSE IN EULA.txt", declared_in="x") == []
    assert license_facts(tmp_path, None, declared="", declared_in="package.json") == []
    # The file's own text outranks the declaration whenever a file exists.
    (tmp_path / "LICENSE").write_text("Apache License\nVersion 2.0, January 2004", "utf-8")
    with_file = license_facts(tmp_path, "LICENSE", declared="MIT", declared_in="package.json")
    assert [(f.id, f.value) for f in with_file] == [
        ("license:file", "LICENSE"),
        ("license:spdx", "Apache-2.0"),
    ]
    assert with_file[1].evidence[0].path == "LICENSE"


def test_a_notices_file_is_a_fact_with_or_without_a_license(tmp_path: Path) -> None:
    (tmp_path / "NOTICE").write_text("Includes zlib.\n", "utf-8")
    facts = license_facts(tmp_path, None, "NOTICE")
    assert [(f.id, f.kind, f.value) for f in facts] == [
        ("third_party_notices:file", "third_party_notices", "NOTICE")
    ]
    (tmp_path / "LICENSE").write_text("MIT License\n", "utf-8")
    assert [f.id for f in license_facts(tmp_path, "LICENSE", "NOTICE")] == [
        "license:file",
        "license:spdx",
        "third_party_notices:file",
    ]
