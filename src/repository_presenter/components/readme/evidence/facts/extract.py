"""Assemble the facts document for one snapshot: identity, examples, manifest, surface, README."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.assets import asset_facts
from repository_presenter.components.readme.evidence.facts.formats import format_facts
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.license import license_facts
from repository_presenter.components.readme.evidence.facts.links import link_facts
from repository_presenter.components.readme.evidence.facts.product_pages import product_page_facts
from repository_presenter.components.readme.extractors.examples.verify import example_facts
from repository_presenter.components.readme.extractors.platforms.registry import PlatformPlugin
from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.components.readme.extractors.surface.registry import REGISTRY_TYPES
from repository_presenter.core.ecosystems import spec_for
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


def _source_build_fact(
    fact: Fact, entry: RegistryEntry, receipts: Sequence[ExampleReceipt]
) -> Fact:
    """Admit a verified source build as an alternate SUPPORTED path for an unpublished package.

    `RESEARCH_AND_GUIDELINES.md` section 28.12, G4-W17 arrival item 0. A registry's CONTRADICTED
    reading means the package is not there; it does not mean the repository cannot be used. An
    EXECUTED example already proves the source compiles against this revision, using the exact
    command the ecosystem's own spec names - the admitted fact is a source install kind, never a
    registry command, so the renderer never tells a reader to `pip install <name>` or
    `cargo add <name>` for a package no registry lists. An ecosystem with no `source_install`
    template (a registry-less spec has nothing to admit either way) leaves the fact untouched.

    Item (24): a registry-less ecosystem's install fact can never become CONTRADICTED - there is
    no registry to read as "not there" - so it starts and stays UNRESOLVED forever, and this gate
    never opened for it (measured 2026-09-06 on the whole C++ cohort: `cpp` has no `REGISTRY_TYPES`
    entry). UNRESOLVED is admitted too, but only when the ecosystem has no registry at all; for a
    registry-having ecosystem, UNRESOLVED means the probe could not be read this time - a
    transient reading, not a "not published" one - so it must keep failing closed rather than being
    treated as if the registry had spoken.

    `RESEARCH_LANE_E.md`'s "documented PYTHONPATH source install" secondary observation
    (LANE-E-06, corroborated a second time by LANE-E-14/LANE-E-17), supervisor-directed
    2026-09-17: some repositories have no admissible build/install command at all - every
    invocation of the ecosystem's own build backend fails identically, a fact about the packaging,
    not the code (`aspose-html-foss/Aspose.HTML-FOSS-for-Python`'s `pyproject.toml` names a
    `setuptools.backends.legacy` build backend no setuptools release ever provided, so `pip
    install .` fails the same way regardless of isolation flags). An example that only ran via the
    source-tree fallback still proves the code imports and runs; it proves nothing about any
    build/install command, so it is never admitted through the verified-build branch above (a
    fallback receipt's `build_verified` is `False`). It is instead admitted through a strictly
    weaker tier, `install_kind: "source_checkout"`, whose value is honest clone-and-reference
    instructions - adding the source directories the fallback already ran from to the
    interpreter's path - never a pip or build command nobody proved. This tier fires only when no
    receipt anywhere reports `build_verified=True`, so it can never compete with or weaken the
    verified-source-build tier above; a single genuine build receipt always wins.
    """
    if fact.kind != "install_command":
        return fact
    registry_less = entry.ecosystem not in REGISTRY_TYPES
    admissible = fact.polarity == "CONTRADICTED" or (
        fact.polarity == "UNRESOLVED" and registry_less
    )
    if not admissible:
        return fact
    # An EXECUTED outcome alone is not proof the advertised build/install command itself
    # succeeded - only `build_verified` is (TB-01, external review D1, 2026-09-08): C++'s
    # -fsyntax-only check never links the library, and a Python example that ran against the
    # repository's own source tree after a failed install proves the code, never the command
    # this fact is about to advertise as "verified against this revision".
    proven = [r for r in receipts if r.outcome == "EXECUTED" and r.build_verified]
    if not proven:
        return _source_checkout_fact(fact, entry, receipts)
    spec = spec_for(entry.ecosystem)
    name = entry.repository.split("/")[-1]
    # G4-W17 arrival item 50 (lane B, RESEARCH_LANE_B 617-645): a verifier that drove the
    # manifest's own build names the exact steps it proved on the receipt, per repository, and
    # those outrank the ecosystem-wide template. TypeScript declares no template because no one
    # command is true for both of its repositories (Aspose.3D: `npm install` then `npm run build`
    # exit 0; Aspose.Cells: no build script, its own sources do not compile), and this sentence's
    # older form - "an example executed ... proving the source compiles" - was false for a
    # type-checked snippet. The evidence states exactly the steps that exited 0, and BC-02 holds
    # the rendered command to them. A verifier that drove none leaves the template path as it was.
    measured = next((r.build_command for r in proven if r.build_command), "")
    if measured:
        command = spec.clone_and_run(entry.repository, name, measured)
        steps = " and ".join(f"`{step}`" for step in measured.splitlines())
        detail = (
            f"verified source build: the verifier ran {steps} against this revision, every step "
            "exiting 0; the advertised steps are exactly the ones it ran"
        )
        admitted = {"install_kind": "source", "build_command": measured}
    else:
        command = spec.clone_and_build(entry.repository, name)
        if not command:
            return fact
        detail = (
            "verified source build: an example executed against this revision, proving "
            "the source compiles even though the registry does not yet list the package"
        )
        admitted = {"install_kind": "source"}
    return replace(
        fact,
        value=command,
        polarity="SUPPORTED",
        confidence=1.0,
        attributes={**(fact.attributes or {}), **admitted},
        evidence=(*fact.evidence, Evidence(RECEIPTS_FILENAME, detail)),
    )


def _source_checkout_fact(
    fact: Fact, entry: RegistryEntry, receipts: Sequence[ExampleReceipt]
) -> Fact:
    """`RESEARCH_LANE_E.md`'s PYTHONPATH-source-install observation: the weaker admission tier
    `_source_build_fact` falls back to when nothing proved a build.

    Called only once the caller has already confirmed no receipt reports `outcome == "EXECUTED"
    and build_verified`; this re-checks the stronger condition the docstring above promises -
    `build_verified` is `True` by default on every receipt an ecosystem's weaker-EXECUTED path
    never touches, including a non-EXECUTED one, so this tier fires only when nothing anywhere
    reports it, never merely when nothing EXECUTED did. A receipt with `source_roots` is the
    positive proof the source-tree fallback both ran and executed - never a syntax-only check
    (C++), which proves nothing about where the code lives and sets no such paths.
    """
    if any(r.build_verified for r in receipts):
        return fact
    checkout = next((r for r in receipts if r.outcome == "EXECUTED" and r.source_roots), None)
    if checkout is None:
        return fact
    spec = spec_for(entry.ecosystem)
    name = entry.repository.split("/")[-1]
    command = spec.clone_and_reference(entry.repository, name, checkout.source_roots)
    if not command:
        return fact
    detail = (
        "source checkout only: every build/install attempt failed identically for this "
        "revision, but an example executed against the repository's own source tree with no "
        "build step - the advertised step is adding that tree to the interpreter's path, never "
        "a build or install command, which was never proven to succeed"
    )
    return replace(
        fact,
        value=command,
        polarity="SUPPORTED",
        confidence=1.0,
        attributes={**(fact.attributes or {}), "install_kind": "source_checkout"},
        evidence=(*fact.evidence, Evidence(RECEIPTS_FILENAME, detail)),
    )


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
        resolved = (observed.get(fact.id, fact) for fact in manifest_facts)
        facts.extend(_source_build_fact(fact, entry, receipts) for fact in resolved)
        probes.extend(registry_probes)
    facts.extend(plugin.surface_facts(clone_path, tree_paths))
    # G4-W17 arrival item 51: the manifest's own license declaration, through the ManifestReader
    # facade the plugins read identity from, stands in for a license file the repository does
    # not ship (license_facts consults it only then).
    declared = declared_in = None
    if manifest is not None:
        stated = read_identity(clone_path, entry.ecosystem, manifest).raw.get("license")
        if isinstance(stated, str) and stated.strip():
            declared = stated
            declared_in = manifest.relative_to(clone_path).as_posix()
    facts.extend(
        license_facts(
            clone_path, snapshot.license_path, snapshot.notices_path, declared, declared_in
        )
    )
    facts.extend(asset_facts(tree_paths))
    facts.extend(product_page_facts(entry))
    if snapshot.readme_path is not None:
        readme_bytes = (clone_path / snapshot.readme_path).read_bytes()
        public_symbol_facts = tuple(f for f in facts if f.kind == "public_symbol")
        facts.extend(inherited_unit_facts(snapshot.readme_path, readme_bytes, public_symbol_facts))
        link_records, link_probes = link_facts(snapshot.readme_path, readme_bytes, tree_paths)
        facts.extend(link_records)
        probes.extend(link_probes)
    document = FactsDocument(
        repository=entry.repository,
        source_revision=snapshot.source_revision,
        facts=tuple(facts),
    )
    return document, probes
