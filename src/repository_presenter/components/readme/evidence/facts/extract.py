"""Assemble the facts document for one snapshot: identity, examples, manifest, surface, README."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.assets import asset_facts
from repository_presenter.components.readme.evidence.facts.formats import format_facts
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.license import license_facts
from repository_presenter.components.readme.evidence.facts.links import link_facts
from repository_presenter.components.readme.evidence.facts.product_pages import product_page_facts
from repository_presenter.components.readme.extractors.examples.verify import example_facts
from repository_presenter.components.readme.extractors.platforms.registry import PlatformPlugin
from repository_presenter.core.examples import (
    RECEIPTS_FILENAME,
    ExampleCandidate,
    ExampleReceipt,
)
from repository_presenter.core.facts import (
    Evidence,
    Fact,
    FactsDocument,
    fact_id,
)
from repository_presenter.core.probes import ProbeRecord
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import RepositorySnapshot


def identity_facts(entry: RegistryEntry, snapshot: RepositorySnapshot) -> list[Fact]:
    registry = Evidence("data/registry.json", "admitted registry entry")
    return [
        Fact(fact_id("identity", "repository"), "identity", entry.repository, (registry,)),
        Fact(
            fact_id("identity", "revision"),
            "identity",
            snapshot.source_revision,
            (Evidence("source/snapshot.json", "pinned default-branch revision"),),
        ),
        Fact(fact_id("identity", "family"), "identity", entry.family, (registry,)),
        Fact(fact_id("identity", "platform"), "identity", entry.platform, (registry,)),
        Fact(fact_id("identity", "ecosystem"), "identity", entry.ecosystem, (registry,)),
    ]


def extract_facts(
    entry: RegistryEntry,
    snapshot: RepositorySnapshot,
    clone_path: Path,
    tree_paths: list[str],
    plugin: PlatformPlugin,
    manifest: Path | None,
    examples: Sequence[ExampleCandidate] = (),
    receipts: Sequence[ExampleReceipt] = (),
    receipts_path: str = RECEIPTS_FILENAME,
) -> tuple[FactsDocument, list[ProbeRecord]]:
    """Every deterministic fact the snapshot supports, and every live read that informed one.

    The probe records are returned rather than folded into the facts because they carry what a
    fact must not: the duration of a read, and a reading that changes without the repository
    changing (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC7).
    """
    facts = identity_facts(entry, snapshot)
    probes: list[ProbeRecord] = []
    facts.extend(example_facts(examples, receipts, receipts_path))
    facts.extend(
        format_facts(
            examples,
            receipts,
            plugin.format_claims,
            receipts_path,
            plugin.format_declarations(clone_path, tree_paths),
        )
    )
    if manifest is not None:
        manifest_facts = plugin.manifest_facts(clone_path, manifest, tree_paths)
        registry_facts, registry_probes = plugin.registry_facts(manifest_facts)
        observed = {fact.id: fact for fact in registry_facts}
        facts.extend(observed.get(fact.id, fact) for fact in manifest_facts)
        probes.extend(registry_probes)
    facts.extend(plugin.surface_facts(clone_path, tree_paths))
    facts.extend(license_facts(clone_path, snapshot.license_path, snapshot.notices_path))
    facts.extend(asset_facts(tree_paths))
    facts.extend(product_page_facts(entry))
    if snapshot.readme_path is not None:
        readme_bytes = (clone_path / snapshot.readme_path).read_bytes()
        facts.extend(inherited_unit_facts(snapshot.readme_path, readme_bytes))
        link_records, link_probes = link_facts(snapshot.readme_path, readme_bytes, tree_paths)
        facts.extend(link_records)
        probes.extend(link_probes)
    document = FactsDocument(
        repository=entry.repository,
        source_revision=snapshot.source_revision,
        facts=tuple(facts),
    )
    return document, probes
