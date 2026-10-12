"""What the correction run adds to the facts before any detector reads them.

Two re-enable conditions need something the extractors do not record, and both are read from the
pinned clone, so both are made here and travel in the bundle's ``facts.json`` (the typed gate
re-derives a correction from that file alone):

* ``add_dev_commands``: the build and test commands are one chain (``chain.plan_chain``) and a
  receipt says it ran on a clean clone (``verify.run_chain``); ``receipts.apply_plan`` puts both on
  the command facts;
* ``add_doc_links``: a docs directory holds prose documentation (``docs.documentation_fact``).

A receipt is looked up in the receipts directory first (a stored one for this very revision and
chain is reused, never re-run), and a chain without one is run only when asked (``verify``): the
default correction run stays free of builds. Enrichment is skipped for facts that already carry
it, so running it twice changes nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from repository_presenter.components.readme_correction.chain import (
    CHAIN_ATTRIBUTE,
    COMMAND_FACT_IDS,
    EXCLUDED_ATTRIBUTE,
    ChainPlan,
    plan_chain,
)
from repository_presenter.components.readme_correction.docs import DOCS_FACT_ID, documentation_fact
from repository_presenter.components.readme_correction.receipts import (
    Receipt,
    apply_plan,
    load_receipt,
    receipt_path,
    store_receipt,
)
from repository_presenter.components.readme_correction.verify import run_chain
from repository_presenter.core.facts import FactsDocument

ChainRunner = Callable[..., Receipt]


@dataclass(frozen=True)
class ReceiptOptions:
    """Where receipts are kept, and whether a missing one is made."""

    directory: Path | None = None
    verify: bool = False
    scratch: Path | None = None
    runner: ChainRunner = run_chain


@dataclass(frozen=True)
class Enrichment:
    facts: FactsDocument
    plan: ChainPlan
    receipt: Receipt | None


def already_enriched(facts: FactsDocument) -> bool:
    return any(
        fact.id in COMMAND_FACT_IDS
        and {CHAIN_ATTRIBUTE, EXCLUDED_ATTRIBUTE} & set(fact.attributes or {})
        for fact in facts.facts
    ) or any(fact.id == DOCS_FACT_ID for fact in facts.facts)


def enrich_facts(
    facts: FactsDocument,
    clone_path: Path,
    tree_paths: Sequence[str],
    options: ReceiptOptions | None = None,
) -> Enrichment:
    """``facts`` with the command chain's findings and the documentation fact added."""
    if already_enriched(facts):
        return Enrichment(facts, ChainPlan(note="already enriched"), None)
    options = options or ReceiptOptions()
    plan = plan_chain(facts, clone_path, tree_paths)
    receipt: Receipt | None = None
    if plan.kind:
        path = (
            receipt_path(options.directory, facts.repository, facts.source_revision, plan)
            if options.directory is not None
            else None
        )
        if path is not None:
            receipt = load_receipt(path, facts.repository, facts.source_revision, plan)
        if receipt is None and options.verify:
            if options.scratch is None:
                raise ValueError("verifying a command chain needs a scratch directory")
            receipt = options.runner(
                plan,
                repository=facts.repository,
                revision=facts.source_revision,
                clone_path=clone_path,
                scratch=options.scratch,
            )
            if path is not None:
                store_receipt(path, receipt)
    enriched = apply_plan(facts, plan, receipt)
    documentation = documentation_fact(clone_path, tree_paths)
    if documentation is not None:
        enriched = FactsDocument(
            enriched.repository,
            enriched.source_revision,
            (*enriched.facts, documentation),
            enriched.schema_version,
        )
    # the order a bundle stores and the typed gate reads back, so both derive the same bytes
    return Enrichment(enriched.canonical(), plan, receipt)
