"""Build and test assets read from the tree inventory: tests, CI workflows, docs, examples."""

from __future__ import annotations

from collections.abc import Sequence

from repository_presenter.core.facts import Evidence, Fact, fact_id

_MAX_EVIDENCE_PATHS = 5


def _directory_fact(name: str, prefix: str, paths: Sequence[str], detail: str) -> Fact | None:
    matches = sorted(path for path in paths if path.startswith(prefix))
    if not matches:
        return None
    evidence = tuple(Evidence(path) for path in matches[:_MAX_EVIDENCE_PATHS])
    return Fact(
        fact_id("build_test_asset", name),
        "build_test_asset",
        prefix,
        (*evidence, Evidence(prefix, f"{len(matches)} files; {detail}")),
    )


def asset_facts(tree_paths: Sequence[str]) -> list[Fact]:
    """One fact per asset class present in the tree, with the paths that prove it."""
    candidates = (
        _directory_fact("tests", "tests/", tree_paths, "test suite"),
        _directory_fact("ci", ".github/workflows/", tree_paths, "GitHub Actions workflows"),
        _directory_fact("docs", "docs/", tree_paths, "documentation directory"),
        _directory_fact("examples", "examples/", tree_paths, "example directory"),
    )
    return [fact for fact in candidates if fact is not None]
