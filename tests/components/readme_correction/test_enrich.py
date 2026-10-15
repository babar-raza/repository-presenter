"""What the correction run adds to the facts: the command chain with its receipt, and the
documentation fact. A receipt already stored for the revision and chain is reused and never re-run;
a missing one is made only when asked; enriching twice changes nothing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repository_presenter.components.readme_correction.chain import (
    CHAIN_ATTRIBUTE,
    RECEIPT_ATTRIBUTE,
    RECEIPT_FAILURE_ATTRIBUTE,
    plan_chain,
)
from repository_presenter.components.readme_correction.docs import (
    DOCS_FACT_ID,
    MIN_PROSE_WORDS,
    documentation_fact,
    documentation_paths,
    prose_words,
)
from repository_presenter.components.readme_correction.enrich import (
    ReceiptOptions,
    already_enriched,
    enrich_facts,
)
from repository_presenter.components.readme_correction.receipts import (
    EXECUTED,
    FAILED,
    Receipt,
    StepResult,
    receipt_path,
    store_receipt,
)
from repository_presenter.core.facts import FactsDocument

REVISION = "d" * 40
PROSE = (
    "This guide explains how the library reads a document from a stream and writes it back "
    "to disk. It covers the common cases first and the unusual ones after them. Every example "
    "in this guide runs against the sample files that ship with the repository itself.\n"
)


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def tree_of(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def facts_with_commands(make_fact: Any) -> FactsDocument:
    return FactsDocument(
        "o/r",
        REVISION,
        (
            make_fact(
                "build_test_asset:test-command",
                "go test ./...",
                evidence=(("go.mod", "test command; standard `go test ./...`"),),
                attributes={"role": "test command", "source": "toolchain convention"},
            ),
        ),
    )


def passing(plan: Any) -> Receipt:
    return Receipt(
        "o/r",
        REVISION,
        plan.digest(),
        EXECUTED,
        "every step exited 0",
        (StepResult("go test ./...", EXECUTED, 0),),
        {"go": "go1.26"},
        "Linux (docker container)",
    )


def test_a_command_chain_without_a_receipt_is_marked_as_not_run(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, "go.mod", "module x\n")
    result = enrich_facts(facts_with_commands(make_fact), tmp_path, tree_of(tmp_path))
    attributes = result.facts.facts[0].attributes or {}
    assert attributes[CHAIN_ATTRIBUTE] == "project_files"
    assert attributes[RECEIPT_FAILURE_ATTRIBUTE].startswith("NOT_RUN: ")
    assert RECEIPT_ATTRIBUTE not in attributes and result.receipt is None


def test_a_stored_receipt_is_used_and_the_chain_is_not_run_again(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, "go.mod", "module x\n")
    facts = facts_with_commands(make_fact)
    plan = plan_chain(facts, tmp_path, tree_of(tmp_path))
    store_receipt(receipt_path(tmp_path / "receipts", "o/r", REVISION, plan), passing(plan))

    def refuse(*args: Any, **kwargs: Any) -> Receipt:
        raise AssertionError("a stored receipt must not be re-run")

    options = ReceiptOptions(tmp_path / "receipts", verify=True, scratch=tmp_path, runner=refuse)
    result = enrich_facts(facts, tmp_path, tree_of(tmp_path), options)
    assert (result.facts.facts[0].attributes or {})[RECEIPT_ATTRIBUTE] == (
        passing(plan).stable_digest()
    )


def test_a_missing_receipt_is_made_when_asked_and_kept_for_the_next_run(
    tmp_path: Path, make_fact: Any
) -> None:
    write(tmp_path, "go.mod", "module x\n")
    facts = facts_with_commands(make_fact)
    calls: list[str] = []

    def runner(plan: Any, **kwargs: Any) -> Receipt:
        calls.append(kwargs["revision"])
        assert kwargs["clone_path"] == tmp_path and kwargs["scratch"] == tmp_path / "work"
        return passing(plan)

    options = ReceiptOptions(
        tmp_path / "receipts", verify=True, scratch=tmp_path / "work", runner=runner
    )
    first = enrich_facts(facts, tmp_path, tree_of(tmp_path), options)
    second = enrich_facts(facts, tmp_path, tree_of(tmp_path), options)
    assert calls == [REVISION]  # the second run found the stored receipt
    assert first.facts == second.facts
    assert (first.facts.facts[0].attributes or {})[RECEIPT_ATTRIBUTE]


def test_a_failed_receipt_is_kept_and_its_reason_travels(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "go.mod", "module x\n")

    def runner(plan: Any, **kwargs: Any) -> Receipt:
        return Receipt("o/r", REVISION, plan.digest(), FAILED, "`go test ./...` exited 1: FAIL")

    options = ReceiptOptions(tmp_path / "r", verify=True, scratch=tmp_path / "w", runner=runner)
    result = enrich_facts(facts_with_commands(make_fact), tmp_path, tree_of(tmp_path), options)
    attributes = result.facts.facts[0].attributes or {}
    assert attributes[RECEIPT_FAILURE_ATTRIBUTE] == "FAILED: `go test ./...` exited 1: FAIL"
    assert RECEIPT_ATTRIBUTE not in attributes


def test_enriching_twice_changes_nothing(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "go.mod", "module x\n")
    write(tmp_path, "docs/guide.md", PROSE * 2)
    once = enrich_facts(facts_with_commands(make_fact), tmp_path, tree_of(tmp_path))
    assert already_enriched(once.facts)
    twice = enrich_facts(once.facts, tmp_path, tree_of(tmp_path))
    assert twice.facts == once.facts


def test_prose_is_running_text_not_code_tables_headings_or_link_lists() -> None:
    assert prose_words(PROSE) >= MIN_PROSE_WORDS - 10
    only_structure = (
        "# Title\n\n| a | b | c | d | e | f | g |\n|---|---|---|---|---|---|---|\n"
        "- [one](1.md)\n- [two](2.md)\n\n```python\n"
        "the words inside a fence are not prose at all really\n```\n"
    )
    assert prose_words(only_structure) == 0
    assert prose_words(PROSE * 3) > prose_words(PROSE)


def test_docs_holding_prose_make_the_documentation_fact(tmp_path: Path) -> None:
    write(tmp_path, "docs/guide.md", PROSE * 2)
    write(tmp_path, "docs/media/banner.png", "x")
    fact = documentation_fact(tmp_path, tree_of(tmp_path))
    assert fact is not None and fact.id == DOCS_FACT_ID and fact.value == "docs/"
    assert fact.evidence[0].path == "docs/guide.md"
    assert "words of prose" in (fact.evidence[0].detail or "")


def test_a_docs_directory_of_assets_or_stubs_is_not_documentation(tmp_path: Path) -> None:
    write(tmp_path, "docs/nuget/README.md", PROSE * 2)  # a package README: an asset directory
    write(tmp_path, "docs/media/banner.png", "x")
    write(tmp_path, "docs/index.md", "# Docs\n\n- [a](a.md)\n- [b](b.md)\n")  # links only
    tree = tree_of(tmp_path)
    assert "docs/index.md" in documentation_paths(
        tree
    ) and "docs/nuget/README.md" not in documentation_paths(tree)
    assert documentation_fact(tmp_path, tree) is None


def test_the_documentation_fact_joins_the_facts_of_the_run(tmp_path: Path, make_fact: Any) -> None:
    write(tmp_path, "docs/guide.md", PROSE * 2)
    facts = FactsDocument("o/r", REVISION, (make_fact("license:spdx", "MIT"),))
    result = enrich_facts(facts, tmp_path, tree_of(tmp_path))
    assert {f.id for f in result.facts.facts} == {"license:spdx", DOCS_FACT_ID}
