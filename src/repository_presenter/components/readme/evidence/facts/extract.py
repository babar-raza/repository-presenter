"""Assemble the facts document for one snapshot: identity, manifest, license, and assets."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.components.readme.evidence.facts.assets import asset_facts
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.license import license_facts
from repository_presenter.components.readme.evidence.facts.records import (
    Evidence,
    Fact,
    FactsDocument,
    fact_id,
)
from repository_presenter.components.readme.extractors.platforms.registry import PlatformPlugin
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
) -> FactsDocument:
    """Every deterministic fact the snapshot supports, in one document."""
    facts = identity_facts(entry, snapshot)
    if manifest is not None:
        facts.extend(plugin.manifest_facts(clone_path, manifest, tree_paths))
    facts.extend(license_facts(clone_path, snapshot.license_path))
    facts.extend(asset_facts(tree_paths))
    if snapshot.readme_path is not None:
        readme_bytes = (clone_path / snapshot.readme_path).read_bytes()
        facts.extend(inherited_unit_facts(snapshot.readme_path, readme_bytes))
    return FactsDocument(
        repository=entry.repository,
        source_revision=snapshot.source_revision,
        facts=tuple(facts),
    )
