"""Assemble the facts document for one snapshot: identity, examples, manifest, surface, README."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path

from repository_presenter.components.readme.evidence.facts.assets import (
    asset_facts,
    ci_badge_fact,
)
from repository_presenter.components.readme.evidence.facts.commands import (
    ci_matrix_fact,
    command_facts,
    release_workflow_fact,
)
from repository_presenter.components.readme.evidence.facts.formats import format_facts
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.evidence.facts.license import (
    license_facts,
    settle_declared_license,
)
from repository_presenter.components.readme.evidence.facts.links import link_facts
from repository_presenter.components.readme.evidence.facts.product_pages import (
    ENTERPRISE_FACT_ID,
    enterprise_from_readme_link,
    product_page_facts,
)
from repository_presenter.components.readme.evidence.facts.published_version import (
    PACKAGE_NAME_FACT_ID,
    pin_install_version,
    published_version_fact,
)
from repository_presenter.components.readme.evidence.facts.registry_lag import registry_lag_fact
from repository_presenter.components.readme.evidence.facts.unpublished import (
    documented_source_install,
)
from repository_presenter.components.readme.extractors.examples.verify import example_facts
from repository_presenter.components.readme.extractors.platforms.registry import PlatformPlugin
from repository_presenter.components.readme.extractors.surface.doc_text import usable_symbol_docs
from repository_presenter.components.readme.extractors.surface.manifest import read_identity
from repository_presenter.components.readme.extractors.surface.registry import REGISTRY_TYPES
from repository_presenter.core.ecosystems import SPECS, EcosystemSpec, spec_for
from repository_presenter.core.examples import (
    RECEIPTS_FILENAME,
    ExampleCandidate,
    ExampleReceipt,
    MeasuredBuild,
)
from repository_presenter.core.facts import (
    SOURCE_CHECKOUT_COMMAND_ATTRIBUTE,
    SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE,
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
    fact: Fact,
    entry: RegistryEntry,
    receipts: Sequence[ExampleReceipt],
    build: MeasuredBuild | None = None,
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
    spec = spec_for(entry.ecosystem)
    name = entry.repository.split("/")[-1]
    # The one rule for a .NET or npm install claim the registry does not confirm (Imaging-FOSS for
    # .NET and GIS, 2026-10-04; Aspose.PDF and Aspose.3D for TypeScript, 2026-10-04): a package
    # the registry lists as absent, or whose claim no manifest
    # field produced, is advertised only as the source install the package's own build proved -
    # never as the registry command. A build that did not exit 0 admits nothing here. The
    # measured steps are the one command the proof ran; no example is needed for this proof, and
    # a failed README snippet is that snippet's defect, not the package's.
    if build is not None and build.verified and build.command:
        detail = (
            f"verified source build: the package's own build ran `{build.command}` against this "
            "revision and exited 0; the advertised command is exactly the one it ran"
        )
        return replace(
            fact,
            value=spec.clone_and_run(entry.repository, name, build.command),
            polarity="SUPPORTED",
            confidence=1.0,
            attributes={
                **(fact.attributes or {}),
                "install_kind": "source",
                "build_command": build.command,
            },
            evidence=(*fact.evidence, Evidence(fact.evidence[0].path, detail)),
        )
    proven = [r for r in receipts if r.outcome == "EXECUTED" and r.build_verified]
    if not proven:
        return _source_checkout_fact(fact, entry, receipts)
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


# The install kinds a verified build or checkout already states as the install itself.
_SOURCE_INSTALL_KINDS = frozenset({"source", "source_checkout"})


def _has_root_manifest(spec: EcosystemSpec, tree_paths: Sequence[str]) -> bool:
    """Whether the checkout root holds a file the ecosystem's build tool starts from."""
    return any(
        "/" not in path and fnmatchcase(path, glob)
        for path in tree_paths
        for glob in spec.manifest_globs
    )


def _with_source_checkout(
    fact: Fact,
    entry: RegistryEntry,
    plugin: PlatformPlugin,
    tree_paths: Sequence[str],
    receipts: Sequence[ExampleReceipt],
    build: MeasuredBuild | None,
) -> Fact:
    """Record, on the registry install fact, the clone-and-build block the Installation section
    may offer beside it: the command a build proved from the checkout root, or why none did.

    TC-TST-01 (Aspose.3D for .NET, 2026-10-11): the block was the ecosystem's template, printed
    whenever an example executed, and ``dotnet build`` at a root that holds no project or
    solution fails with MSB1003. Nothing had run that command from that directory, and BC-02
    never saw it because the block was not a fact. Now it is one:

    - an ecosystem that drives its own build (``verify_build``) is held to what that build ran,
      spelled relative to the checkout root, and a build that did not exit 0 leaves no block;
    - any other ecosystem's template stands only when an example executed against a build that
      succeeded (``build_verified``, the same proof ``_source_build_fact`` asks for) and the
      checkout root holds a manifest for the template, which starts at the root, to build.

    A source-kind install is the proof itself and needs no second block. The record rides in the
    fact's attributes, not its evidence, because the renderer reads the evidence's last line as
    the registry's reading.
    """
    spec = SPECS.get(entry.ecosystem)
    if (
        spec is None
        or fact.kind != "install_command"
        or fact.id != spec.install_fact_id
        or (fact.attributes or {}).get("install_kind") in _SOURCE_INSTALL_KINDS
        or not spec.source_install
        or not spec.source_install_lead
    ):
        return fact
    name = entry.repository.split("/")[-1]

    def record(attribute: str, value: str) -> Fact:
        return replace(fact, attributes={**(fact.attributes or {}), attribute: value})

    if build is not None and build.verified and build.command:
        return record(
            SOURCE_CHECKOUT_COMMAND_ATTRIBUTE,
            spec.clone_and_run(entry.repository, name, build.command),
        )
    if getattr(plugin, "verify_build", None) is not None:
        # This ecosystem measures its own build, so its template was never the thing measured.
        reason = build.summary if build is not None else "not attempted"
        return record(SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE, f"no build exited 0: {reason}")
    proven = [r for r in receipts if r.outcome == "EXECUTED" and r.build_verified]
    if not proven:
        return record(
            SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE,
            "no example executed against a build of this checkout that succeeded",
        )
    measured = next((r.build_command for r in proven if r.build_command), "")
    if measured:
        return record(
            SOURCE_CHECKOUT_COMMAND_ATTRIBUTE, spec.clone_and_run(entry.repository, name, measured)
        )
    if not _has_root_manifest(spec, tree_paths):
        return record(
            SOURCE_CHECKOUT_UNVERIFIED_ATTRIBUTE,
            "the checkout root holds no manifest for the build to start from",
        )
    return record(SOURCE_CHECKOUT_COMMAND_ATTRIBUTE, spec.clone_and_build(entry.repository, name))


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
    build: MeasuredBuild | None = None,
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
        # The identity facts ride along so a plugin can ask the registry whether the package
        # it found under the manifest's name points back at THIS repository: a name on a
        # registry is not ownership (TC-EXT-01).
        registry_facts, registry_probes = plugin.registry_facts([*facts, *manifest_facts])
        observed = {fact.id: fact for fact in registry_facts}
        resolved = (observed.get(fact.id, fact) for fact in manifest_facts)
        facts.extend(
            _with_source_checkout(
                _source_build_fact(fact, entry, receipts, build),
                entry,
                plugin,
                tree_paths,
                receipts,
                build,
            )
            for fact in resolved
        )
        probes.extend(registry_probes)
        # TC-CLM-01 (G3-W08): the registry's current stable release, so BC-14 can hold a README's
        # version statement to what a reader can fetch. Absent unless the registry answered
        # conclusively (published_version.py); a second read of the registry the plugin just asked.
        published = published_version_fact(
            entry, next((f for f in manifest_facts if f.id == PACKAGE_NAME_FACT_ID), None)
        )
        if published is not None:
            facts.append(published)
            # A coordinate-form install command embeds the manifest's version; a reader can
            # fetch only the registry's, which BC-14 holds the command to.
            manifest_version = next(
                (f.value for f in manifest_facts if f.id == "package:version"), ""
            )
            facts[:] = [pin_install_version(f, manifest_version, published) for f in facts]
    # A symbol whose own documentation has a hole ("Base class for  and") is an undocumented
    # symbol: the table row and the member bullet quote only a summary that reads whole.
    facts.extend(usable_symbol_docs(list(plugin.surface_facts(clone_path, tree_paths))))
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
    # The manifest's declaration is held to the license file's own text (one licence, stated once).
    facts[:] = settle_declared_license(facts)
    # The registry's release lags this source tree (manifest ahead, or unreleased changelog work).
    lag = registry_lag_fact(facts, clone_path, tree_paths)
    if lag is not None:
        facts.append(lag)
    ecosystem_spec = SPECS.get(entry.ecosystem)
    facts.extend(
        asset_facts(
            tree_paths,
            suite_files=ecosystem_spec.suite_files if ecosystem_spec is not None else None,
            root=clone_path,
        )
    )
    # TC-COV-02 (G3-W08): the build and test commands and the CI matrix the clone itself names.
    facts.extend(command_facts(clone_path, tree_paths))
    matrix = ci_matrix_fact(clone_path, tree_paths)
    if matrix is not None:
        facts.append(matrix)
    # A release sentence needs a workflow whose own step releases something, never a file name.
    release_workflow = release_workflow_fact(clone_path, tree_paths)
    if release_workflow is not None:
        facts.append(release_workflow)
    # plans/idea.md: a build-status badge only for a real workflow in the clone.
    ci_badge = ci_badge_fact(entry.repository, clone_path, tree_paths)
    if ci_badge is not None:
        facts.append(ci_badge)
    facts.extend(product_page_facts(entry, probes))
    if snapshot.readme_path is not None:
        readme_bytes = (clone_path / snapshot.readme_path).read_bytes()
        # A package the registry reads as absent AND the maintainers' README says is unpublished is
        # a source checkout, not a failed install (BC-02, wave 6: the JMAP libraries). The measured
        # and receipt-proven source tiers above already won where a build proved; this is the one
        # beneath them, and it reads the clone's own build commands, so it comes after them.
        readme_text = readme_bytes.decode("utf-8", errors="replace")
        registry_less = entry.ecosystem not in REGISTRY_TYPES
        facts[:] = [
            documented_source_install(
                fact,
                entry,
                facts=facts,
                tree_paths=tree_paths,
                readme_path=snapshot.readme_path,
                readme_text=readme_text,
                registry_less=registry_less,
            )
            for fact in facts
        ]
        public_symbol_facts = tuple(f for f in facts if f.kind == "public_symbol")
        facts.extend(
            inherited_unit_facts(
                snapshot.readme_path, readme_bytes, public_symbol_facts, tree_paths
            )
        )
        link_records, link_probes = link_facts(snapshot.readme_path, readme_bytes, tree_paths)
        facts.extend(link_records)
        probes.extend(link_probes)
        # An ambiguous Enterprise Edition lookup is settled by the README's own verified link.
        settled = enterprise_from_readme_link(facts)
        if settled is not None:
            facts[:] = [settled if fact.id == ENTERPRISE_FACT_ID else fact for fact in facts]
    document = FactsDocument(
        repository=entry.repository,
        source_revision=snapshot.source_revision,
        facts=tuple(facts),
    )
    return document, probes
