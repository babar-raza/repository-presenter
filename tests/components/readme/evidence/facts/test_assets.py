"""Build and test assets are read from the tree inventory, never guessed."""

from __future__ import annotations

from repository_presenter.components.readme.evidence.facts.assets import asset_facts


def test_assets_present_in_the_tree_become_facts() -> None:
    paths = [
        "README.md",
        "setup.py",
        "tests/test_a.py",
        "tests/test_b.py",
        ".github/workflows/publish.yml",
        "docs/releasing.md",
        "aspose/threed/__init__.py",
    ]
    facts = asset_facts(paths)
    assert [(f.id, f.value) for f in facts] == [
        ("build_test_asset:tests", "tests/"),
        ("build_test_asset:ci", ".github/workflows/"),
        ("build_test_asset:docs", "docs/"),
    ]
    tests = facts[0]
    assert [e.path for e in tests.evidence] == ["tests/test_a.py", "tests/test_b.py", "tests/"]
    assert tests.evidence[-1].detail == "2 files; test suite"


def test_no_assets_yield_no_facts() -> None:
    assert asset_facts(["README.md", "LICENSE"]) == []


def test_evidence_paths_are_bounded() -> None:
    paths = [f"tests/test_{i}.py" for i in range(20)]
    facts = asset_facts(paths)
    assert len(facts[0].evidence) == 6
    assert facts[0].evidence[-1].detail == "20 files; test suite"
