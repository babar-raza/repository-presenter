"""License facts come from the license text itself and never guess."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.evidence.facts.license import (
    classify_license_text,
    license_facts,
)


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
