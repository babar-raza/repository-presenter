"""D14 template checker: templated text is DISQUALIFIED, repository-specific text passes, and
input it cannot judge is UNEVALUATED rather than a silent pass."""

from __future__ import annotations

from repository_presenter.components.readme.review.acceptance.template_check import (
    Evidence,
    ReferenceSection,
    Verdict,
    check_template_filling,
)

BOILERPLATE = (
    "Install {name} {ver} with the standard steps for this product and follow the usual "
    "setup instructions for your platform before you start using it."
)

EVIDENCE = Evidence(
    product_name="Demo Pro",
    version="2.0",
    fact_tokens=frozenset({"demo-pro-cli", "demo_pro.core", "parse_document"}),
)


def _reference(body: str, product: str = "Other Tool", version: str = "3.1") -> ReferenceSection:
    return ReferenceSection("Installation", body, product, version)


def _readme(body: str) -> str:
    return f"# Demo Pro\n\n## Installation\n\n{body}\n"


def test_templated_section_with_swapped_product_and_version_is_disqualified() -> None:
    reference = _reference(BOILERPLATE.format(name="Other Tool", ver="3.1"))
    readme = _readme(BOILERPLATE.format(name="Demo Pro", ver="2.0"))

    result = check_template_filling(readme, EVIDENCE, [reference])

    assert result.verdict is Verdict.DISQUALIFIED
    assert any("'Installation'" in item for item in result.evidence)


def test_section_with_repository_specific_fact_passes_even_when_shape_matches() -> None:
    # The reference is the candidate's text with only the product and version swapped, so the
    # section matches after masking. The package command names a repository fact, so it passes.
    body = "Install {name} {ver} with `pip install demo-pro-cli` and follow the usual setup steps."
    reference = _reference(body.format(name="Other Tool", ver="3.1"))
    readme = _readme(body.format(name="Demo Pro", ver="2.0"))

    result = check_template_filling(readme, EVIDENCE, [reference])

    assert result.verdict is Verdict.PASS
    assert any("names a repository fact" in item for item in result.evidence)


def test_distinct_prose_that_matches_no_reference_passes() -> None:
    reference = _reference(BOILERPLATE.format(name="Other Tool", ver="3.1"))
    readme = _readme(
        "The parser streams each page, so memory stays flat on very large documents while "
        "callers keep a single handle for the whole run and can cancel it safely."
    )

    result = check_template_filling(readme, EVIDENCE, [reference])

    assert result.verdict is Verdict.PASS


def test_a_fact_in_a_code_block_counts_as_a_repository_fact() -> None:
    prose = (
        "Call the entry point and read the result object that the library returns once the run "
        "has finished without any error."
    )
    block = "\n\n```python\nparse_document(path)\n```"
    reference = _reference(prose + block)
    readme = _readme(prose + block)

    result = check_template_filling(readme, EVIDENCE, [reference])

    assert result.verdict is Verdict.PASS
    assert any("names a repository fact" in item for item in result.evidence)


def test_empty_template_corpus_is_unevaluated_not_a_pass() -> None:
    result = check_template_filling(
        _readme(BOILERPLATE.format(name="Demo Pro", ver="2.0")), EVIDENCE, []
    )

    assert result.verdict is Verdict.UNEVALUATED
    assert "no reference README corpus" in result.evidence[0]


def test_evidence_without_usable_fact_tokens_is_unevaluated() -> None:
    reference = _reference(BOILERPLATE.format(name="Other Tool", ver="3.1"))
    no_facts = Evidence(product_name="Demo Pro", version="2.0", fact_tokens=frozenset({"ab"}))

    result = check_template_filling(
        _readme(BOILERPLATE.format(name="Demo Pro", ver="2.0")), no_facts, [reference]
    )

    assert result.verdict is Verdict.UNEVALUATED
    assert "fact token" in result.evidence[0]


def test_missing_product_name_is_unevaluated() -> None:
    reference = _reference(BOILERPLATE.format(name="Other Tool", ver="3.1"))
    unnamed = Evidence(product_name=" ", version="2.0", fact_tokens=EVIDENCE.fact_tokens)

    result = check_template_filling(
        _readme(BOILERPLATE.format(name="Demo Pro", ver="2.0")), unnamed, [reference]
    )

    assert result.verdict is Verdict.UNEVALUATED


def test_readme_with_only_short_sections_is_unevaluated() -> None:
    reference = _reference(BOILERPLATE.format(name="Other Tool", ver="3.1"))

    result = check_template_filling(
        "# Demo Pro\n\n## Installation\n\nSee above.\n", EVIDENCE, [reference]
    )

    assert result.verdict is Verdict.UNEVALUATED
    assert "at least 8 words" in result.evidence[0]
