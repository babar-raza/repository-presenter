"""Scoring a sealed bundle: D14's evidence and corpus come from the sealed files, a bundle is never
compared with itself, and anything unreadable leaves D14 unevaluated instead of passing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.review.acceptance.scorer import INCOMPLETE
from repository_presenter.components.readme.review.acceptance.sealed import (
    load_current_readmes,
    load_sealed_readme,
    reference_corpus,
    score_sealed_bundle,
    template_inputs,
)
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS

FACTS = {
    "repository": "owner/Aspose.Demo-FOSS-for-Python",
    "facts": [
        {"id": "package:name", "kind": "package", "value": "aspose-demo", "polarity": "SUPPORTED"},
        {"id": "package:version", "kind": "package", "value": "1.2.3", "polarity": "SUPPORTED"},
        {
            "id": "install_command:pip",
            "kind": "install_command",
            "value": "pip install aspose-demo",
            "polarity": "SUPPORTED",
        },
        {
            "id": "public_symbol:demo.Document",
            "kind": "public_symbol",
            "value": "demo.Document",
            "polarity": "SUPPORTED",
        },
        {
            "id": "public_symbol:demo.Gone",
            "kind": "public_symbol",
            "value": "demo.Gone",
            "polarity": "UNSUPPORTED",
        },
        {"id": "format:input.obj", "kind": "format", "value": ".obj", "polarity": "SUPPORTED"},
    ],
}


def _bundle(root: Path, directory: str, readme: str, facts: dict[str, Any] | None) -> Path:
    bundle = root / "candidates" / directory / "rev1"
    bundle.mkdir(parents=True)
    (bundle / "README.md").write_text(readme, encoding="utf-8")
    if facts is not None:
        (bundle / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (bundle / "validation.json").write_text(
        json.dumps({"checks": [{"id": c.id, "verdict": "PASS"} for c in BLOCKING_CHECKS]}),
        encoding="utf-8",
    )
    (bundle / "review.json").write_text(
        json.dumps({"verdict": "ACCEPT", "findings": [], "advisory": []}), encoding="utf-8"
    )
    (bundle.parent / "CURRENT").write_text("rev1\n", encoding="utf-8")
    return bundle


def test_the_evidence_is_read_from_the_sealed_facts(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, "owner__Aspose.Demo-FOSS-for-Python", "# T\n", FACTS)
    sealed = load_sealed_readme("owner__Aspose.Demo-FOSS-for-Python", bundle)
    assert sealed is not None
    assert sealed.product_name == "Aspose.Demo FOSS for Python"
    assert sealed.version == "1.2.3"
    # Identifiers, commands and the package name count; an unsupported symbol and a format do not.
    assert sealed.fact_tokens == {"aspose-demo", "pip install aspose-demo", "demo.Document"}


def test_a_bundle_without_readable_readme_or_facts_loads_as_none(tmp_path: Path) -> None:
    no_facts = _bundle(tmp_path, "a__A-for-X", "# T\n", None)
    assert load_sealed_readme("a__A-for-X", no_facts) is None
    assert load_sealed_readme("missing", tmp_path / "nope") is None
    broken = _bundle(tmp_path, "b__B-for-X", "# T\n", {"repository": "b/B-for-X"})
    assert load_sealed_readme("b__B-for-X", broken) is None  # facts key absent


def test_current_readmes_follow_the_current_pointer_and_skip_unloadable(tmp_path: Path) -> None:
    _bundle(tmp_path, "a__A-for-X", "# A\n", {**FACTS, "repository": "a/A-for-X"})
    _bundle(tmp_path, "b__B-for-X", "# B\n", None)  # unloadable: skipped, not an error
    assert [r.directory for r in load_current_readmes(tmp_path)] == ["a__A-for-X"]
    assert load_current_readmes(tmp_path / "empty") == []


def test_the_corpus_is_every_other_repositorys_sections_and_never_the_subjects_own(
    tmp_path: Path,
) -> None:
    _bundle(
        tmp_path, "a__A-for-X", "# A\n\n## Usage\n\nA body.\n", {**FACTS, "repository": "a/A-for-X"}
    )
    _bundle(
        tmp_path, "b__B-for-X", "# B\n\n## Usage\n\nB body.\n", {**FACTS, "repository": "b/B-for-X"}
    )
    readmes = load_current_readmes(tmp_path)
    corpus = reference_corpus(readmes, exclude="a__A-for-X")
    assert {section.body.strip() for section in corpus if section.heading == "Usage"} == {"B body."}
    assert {section.product_name for section in corpus} == {"B for X"}


def test_a_lone_bundle_has_no_template_inputs(tmp_path: Path) -> None:
    _bundle(tmp_path, "a__A-for-X", "# A\n", {**FACTS, "repository": "a/A-for-X"})
    readmes = load_current_readmes(tmp_path)
    assert template_inputs(readmes[0], readmes) is None


def test_a_lone_bundle_scores_incomplete_because_d14_cannot_be_judged(tmp_path: Path) -> None:
    bundle = _bundle(
        tmp_path, "a__A-for-X", "# A\n\nA body.\n", {**FACTS, "repository": "a/A-for-X"}
    )
    readmes = load_current_readmes(tmp_path)
    record = score_sealed_bundle(bundle, readmes[0], readmes)
    assert record["unevaluated"]["disqualifiers"] == ["D14"]
    assert record["outcome"] != "PASS"
    assert record["outcome"] in (INCOMPLETE, "DISQUALIFIED")


def test_an_unreadable_bundle_scores_as_an_empty_readme_and_never_passes(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, "a__A-for-X", "# A\n", None)
    record = score_sealed_bundle(bundle, None, [])
    assert record["outcome"] != "PASS"
    assert "D05" in record["triggered_disqualifiers"]  # no H1 in an empty document
