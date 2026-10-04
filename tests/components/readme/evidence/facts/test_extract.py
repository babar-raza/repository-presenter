"""The facts document for a real local clone: identity, manifest, license, and assets."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.evidence.facts.extract import (
    _source_build_fact,
    extract_facts,
)
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.extractors.platforms.registry import plugin_for
from repository_presenter.components.readme.extractors.surface.registry import RegistryObservation
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt, MeasuredBuild
from repository_presenter.core.facts import Evidence, Fact
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.snapshot.capture import capture_snapshot, list_tree_paths
from support import REPO_ROOT, commit_all, fake_npm, init_git_repository


@pytest.fixture(autouse=True)
def _no_live_product_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "fetch_status", lambda url: (404, url))


ENTRY = RegistryEntry.model_validate(
    {
        "repository": "example-org/Aspose.Example-FOSS-for-Python",
        "family": "example",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "example",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 7, "node_id": "R_7"},
    }
)


def _canary_like_source(tmp_path: Path) -> Path:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    (source / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="aspose-example", version="1.0.0",'
        ' python_requires=">=3.8")\n',
        encoding="utf-8",
    )
    (source / "aspose" / "example").mkdir(parents=True)
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (source / "aspose" / "example" / "__init__.py").write_text("VERSION = '1.0.0'\n", "utf-8")
    (source / "tests").mkdir()
    (source / "tests" / "test_example.py").write_text("def test_ok():\n    pass\n", "utf-8")
    commit_all(source, "seed")
    return source


def test_facts_document_for_a_local_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={"message": "Not Found"}),
    )
    source = _canary_like_source(tmp_path)
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    plugin = plugin_for(ENTRY.ecosystem)
    tree_paths = list_tree_paths(clone.path)

    document, probes = extract_facts(
        ENTRY, snapshot, clone.path, tree_paths, plugin, plugin.detect_manifest(clone.path)
    )

    # Every live read is recorded beside the facts, never inside them: a probe carries the
    # duration and the registry's current version, which no fact may hash (section 27.2 RC7).
    assert {probe.kind for probe in probes} <= {"link", "package_registry"}
    assert all(probe.elapsed_ms is not None for probe in probes)
    hashed = " ".join(
        evidence.detail or "" for fact in document.facts for evidence in fact.evidence
    )
    assert "latest " not in hashed
    ids = sorted(fact.id for fact in document.facts)
    assert ids == [
        "build_test_asset:tests",
        "dependency:none",
        "identity:ecosystem",
        "identity:family",
        "identity:platform",
        "identity:repository",
        "identity:revision",
        "import_path:aspose",
        "import_path:aspose.example",
        "inherited_unit:001.heading",
        "install_command:pip",
        "license:file",
        "license:spdx",
        "link_target:product.banner",
        "link_target:product.enterprise",
        "link_target:product.homepage",
        "package:name",
        "package:python_requires",
        "package:version",
        "public_symbol:aspose",
        "public_symbol:aspose.example",
    ]
    by_id = {fact.id: fact for fact in document.facts}
    assert by_id["identity:revision"].value == clone.revision
    assert by_id["license:spdx"].value == "MIT"
    assert by_id["package:name"].value == "aspose-example"
    assert by_id["install_command:pip"].polarity == "CONTRADICTED"
    assert by_id["install_command:pip"].evidence[1].detail == (
        "package registry: distribution not found"
    )
    assert all(fact.evidence for fact in document.facts)

    schema = json.loads((REPO_ROOT / "schemas" / "facts.schema.json").read_text("utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(json.loads(document.to_json()))) == []

    again, _ = extract_facts(
        ENTRY, snapshot, clone.path, tree_paths, plugin, plugin.detect_manifest(clone.path)
    )
    assert again.to_json() == document.to_json()


def test_a_license_the_manifest_declares_is_a_fact_when_the_repository_ships_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 51. The declaration reaches license_facts through the ManifestReader
    facade the plugins already read identity from, so the repository's own manifest is the
    evidence - never a portfolio policy the repository does not state itself."""
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(404, json={"message": "Not Found"}),
    )
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "pyproject.toml").write_text(
        '[project]\nname = "aspose-example"\nversion = "1.0.0"\nrequires-python = ">=3.8"\n'
        'license = {text = "MIT"}\n',
        encoding="utf-8",
    )
    (source / "aspose" / "example").mkdir(parents=True)
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (source / "aspose" / "example" / "__init__.py").write_text("VERSION = '1.0.0'\n", "utf-8")
    commit_all(source, "seed")
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    assert snapshot.license_path is None
    plugin = plugin_for(ENTRY.ecosystem)
    manifest = plugin.detect_manifest(clone.path)
    document, _ = extract_facts(
        ENTRY, snapshot, clone.path, list_tree_paths(clone.path), plugin, manifest
    )
    by_id = {fact.id: fact for fact in document.facts}
    assert "license:file" not in by_id
    assert (by_id["license:spdx"].value, by_id["license:spdx"].polarity) == ("MIT", "SUPPORTED")
    assert by_id["license:spdx"].evidence == (
        Evidence(
            "pyproject.toml", "license declared by the manifest; no license file at this revision"
        ),
    )


def test_without_a_manifest_only_identity_license_and_assets_remain(tmp_path: Path) -> None:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text("# Example\n", encoding="utf-8")
    (source / "pkg").mkdir()
    (source / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    commit_all(source, "seed")
    clone = pinned_read_only_clone(str(source), tmp_path / "clone")
    snapshot = capture_snapshot(ENTRY.repository, clone)
    plugin = plugin_for("python")

    document, _ = extract_facts(
        ENTRY, snapshot, clone.path, list_tree_paths(clone.path), plugin, None
    )

    assert {fact.kind for fact in document.facts} == {
        "identity",
        "inherited_unit",
        "link_target",  # the product-page lookup, unresolved offline
        "public_symbol",
    }
    assert [f.value for f in document.by_kind("inherited_unit")] == ["# Example"]
    assert [f.value for f in document.by_kind("public_symbol")] == ["pkg"]


def _install(polarity: str = "CONTRADICTED") -> Fact:
    return Fact(
        "install_command:dotnet",
        "install_command",
        "dotnet add package Aspose.Widget",
        (Evidence("Widget.csproj", "install command for the package id declared by the manifest"),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _receipt(outcome: str, build_verified: bool = True) -> ExampleReceipt:
    return ExampleReceipt(1, outcome, 0, "", "", "d", build_verified=build_verified)  # type: ignore[arg-type]


NET_ENTRY = RegistryEntry.model_validate(
    {
        **ENTRY.model_dump(mode="json"),
        "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-.NET",
        "family": "widget",
        "platform": "net",
        "ecosystem": "net",
    }
)
CPP_ENTRY = RegistryEntry.model_validate(
    {
        **ENTRY.model_dump(mode="json"),
        "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-Cpp",
        "family": "widget",
        "platform": "cpp",
        "ecosystem": "cpp",
    }
)


def test_a_verified_source_build_is_admitted_when_the_registry_says_not_yet_published() -> None:
    """G4-W17 arrival item 0. A registry's CONTRADICTED reading means the package is not there,
    not that the repository cannot be used - an EXECUTED example already proves the source
    compiles at this revision, using the exact command the ecosystem's own spec names."""
    admitted = _source_build_fact(_install(), NET_ENTRY, [_receipt("FAILED"), _receipt("EXECUTED")])
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
        "cd Aspose.Widget-FOSS-for-.NET\ndotnet build"
    )
    assert admitted.attributes == {"install_kind": "source"}
    assert "verified source build" in admitted.evidence[-1].detail
    # The manifest's own evidence is kept, not replaced - both facts justify the value now.
    assert (
        admitted.evidence[0].detail == "install command for the package id declared by the manifest"
    )


def test_a_verified_source_build_is_not_admitted_without_reason() -> None:
    # No executed example: nothing proves the source compiles.
    assert (
        _source_build_fact(_install(), NET_ENTRY, [_receipt("FAILED")]).polarity == "CONTRADICTED"
    )
    # Already SUPPORTED: nothing to admit.
    assert _source_build_fact(
        _install("SUPPORTED"), NET_ENTRY, [_receipt("EXECUTED")]
    ).polarity == ("SUPPORTED")
    # Not an install_command fact at all: nothing to admit.
    not_install = replace(_install(), kind="package", id="package:name")
    assert _source_build_fact(not_install, NET_ENTRY, [_receipt("EXECUTED")]) is not_install


def test_a_registry_less_ecosystems_unresolved_install_is_admitted_too() -> None:
    """G4-W17 arrival item 24. With no registry to read as "not there", a registry-less
    ecosystem's install fact can never become CONTRADICTED - it starts and stays UNRESOLVED
    forever, so item 0's gate never opened for it. Measured 2026-09-06 on the whole C++ cohort:
    `cpp` has no `REGISTRY_TYPES` entry, and PDF and Cells C++ had no other blocker."""
    plugin_for("cpp")  # imports platforms/cpp.py, which registers its own EcosystemSpec
    admitted = _source_build_fact(_install("UNRESOLVED"), CPP_ENTRY, [_receipt("EXECUTED")])
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Cpp.git\n"
        "cd Aspose.Widget-FOSS-for-Cpp\ncmake -S . -B build"
    )
    assert admitted.attributes == {"install_kind": "source"}


def test_an_executed_receipt_that_did_not_verify_the_build_admits_nothing() -> None:
    """TB-01, external review D1, 2026-09-08: EXECUTED alone is not proof the advertised command
    itself succeeded - a syntax-only check (C++'s -fsyntax-only) or a source-tree fallback after a
    failed install (Python) both leave the example EXECUTED without proving the build/install this
    fact is about to advertise as "verified against this revision". Only a receipt whose
    build_verified is also True may admit the fact."""
    unverified = _receipt("EXECUTED", build_verified=False)
    assert _source_build_fact(_install(), NET_ENTRY, [unverified]).polarity == "CONTRADICTED"
    # A verified receipt alongside an unverified one still admits - one genuine proof suffices.
    verified = _receipt("EXECUTED", build_verified=True)
    admitted = _source_build_fact(_install(), NET_ENTRY, [unverified, verified])
    assert admitted.polarity == "SUPPORTED"


def _measured(verified: bool = True) -> MeasuredBuild:
    if not verified:
        return MeasuredBuild(False, "", "failed (`dotnet build src/Widget/Widget.csproj` exited 1)")
    return MeasuredBuild(
        True,
        "dotnet build src/Widget/Widget.csproj",
        "succeeded (`dotnet build src/Widget/Widget.csproj` exited 0)",
    )


def test_a_measured_build_admits_a_404_contradicted_install_with_no_example_at_all() -> None:
    """Rule for a .NET install claim (Imaging-FOSS for .NET, measured 2026-10-04; GIS, same
    day): the package is not on NuGet (404, CONTRADICTED), and the product's own `dotnet build`
    of its project exits 0. No README example is needed for that proof - the snippet defect in
    Imaging and the absent README in GIS both leave no example to compile. The source install is
    admitted from exactly the measured steps; the registry command the 404 contradicts never is."""
    admitted = _source_build_fact(_install(), NET_ENTRY, [], _measured())
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-.NET.git\n"
        "cd Aspose.Widget-FOSS-for-.NET\ndotnet build src/Widget/Widget.csproj"
    )
    assert admitted.attributes == {
        "install_kind": "source",
        "build_command": "dotnet build src/Widget/Widget.csproj",
    }
    assert "verified source build" in admitted.evidence[-1].detail
    assert "dotnet add package" not in admitted.value


def test_an_unreadable_registry_stays_unresolved_even_beside_a_verified_build() -> None:
    """The boundary of the rule: UNRESOLVED on a registry-having ecosystem means the probe could
    not read this time - transient, never a "not published" answer - so it fails closed as it
    always has (item 24's own rule). Only a conclusive 404 takes the measured build."""
    unreadable = _install("UNRESOLVED")
    assert _source_build_fact(unreadable, NET_ENTRY, [], _measured()).polarity == "UNRESOLVED"


def test_a_project_with_no_package_id_reaches_the_measured_build_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GIS path, end to end through the real .NET plugin (2026-10-04): the claim is derived from
    the project file's default name, the NuGet reading is a conclusive 404, and the one rule then
    admits the measured `dotnet build` - never the `dotnet add package` the 404 contradicts."""
    from repository_presenter.components.readme.extractors.platforms import net
    from repository_presenter.components.readme.extractors.surface.registry import (
        RegistryObservation,
    )

    project = tmp_path / "src" / "Aspose.Gis.Foss" / "Aspose.Gis.Foss.csproj"
    project.parent.mkdir(parents=True)
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
        "    <TargetFramework>net10.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n",
        encoding="utf-8",
    )
    url = "https://api.nuget.org/v3-flatcontainer/aspose.gis.foss/index.json"
    not_there = RegistryObservation("nuget", "Aspose.Gis.Foss", False, False, url, "flat", "live")
    monkeypatch.setattr(net, "observe", lambda *args, **kwargs: not_there)
    plugin = plugin_for("net")
    resolved, _ = plugin.registry_facts(plugin.manifest_facts(tmp_path, project, []))
    install = next(fact for fact in resolved if fact.id == "install_command:dotnet")
    assert install.polarity == "CONTRADICTED"
    measured = MeasuredBuild(
        True,
        "dotnet build src/Aspose.Gis.Foss/Aspose.Gis.Foss.csproj",
        "succeeded (`dotnet build src/Aspose.Gis.Foss/Aspose.Gis.Foss.csproj` exited 0)",
    )
    admitted = _source_build_fact(install, NET_ENTRY, [], measured)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value.endswith("\ndotnet build src/Aspose.Gis.Foss/Aspose.Gis.Foss.csproj")
    assert "dotnet add package" not in admitted.value


def test_an_unverified_measured_build_admits_nothing() -> None:
    """Mutation control: a build that did not exit 0 leaves the 404 answer standing, so the
    unverified `dotnet add package` claim is what BC-02 then refuses (validation/test_registry)."""
    refused = _source_build_fact(_install(), NET_ENTRY, [], _measured(verified=False))
    assert refused.polarity == "CONTRADICTED"
    assert refused.value == "dotnet add package Aspose.Widget"


def test_an_unproven_product_build_admits_nothing_even_beside_a_failed_example() -> None:
    """The same shape with the product build NOT proven (no SDK, or `dotnet build` exited
    non-zero): nothing carries a measured command, nothing EXECUTED, so the fact stays CONTRADICTED
    and the registry's own answer is what a reader is told."""
    not_built = ExampleReceipt(
        1,
        "NOT_VERIFIED",
        None,
        "",
        "",
        "d",
        build_verified=False,
        build_command="",  # type: ignore[arg-type]
    )
    failed = ExampleReceipt(
        2,
        "FAILED",
        1,
        "",
        "",
        "d",
        build_verified=False,
        build_command="",  # type: ignore[arg-type]
    )
    assert _source_build_fact(_install(), NET_ENTRY, [not_built, failed]).polarity == "CONTRADICTED"


def test_a_nuget_404_falls_back_to_the_measured_source_build_never_the_add_package_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Imaging-FOSS for .NET, measured live 2026-10-04 (AGENTS.md rule 16): NuGet answers 404 for
    the package id the project declares, so the `dotnet add package` claim is CONTRADICTED. That
    one claim must not block the candidate, and must not render: it falls back to the source
    install the product's own `dotnet build` proved, while the README example beside it fails.
    The 404 is read through the plugin's real `registry_facts`; only the network read is replaced
    by its 404 answer (the upstream evidence is in evidence/upstream-defects/)."""
    from repository_presenter.components.readme.extractors.platforms import net
    from repository_presenter.components.readme.extractors.surface.registry import (
        RegistryObservation,
    )

    not_published = RegistryObservation(
        "nuget",
        "Aspose.Widget",
        False,
        False,
        "https://api.nuget.org/v3-flatcontainer/aspose.widget/index.json",
        "flat-container",
        "test",
    )
    monkeypatch.setattr(net, "observe", lambda *args, **kwargs: not_published)
    declared = [
        Fact(
            "package:name",
            "package",
            "Aspose.Widget",
            (Evidence("Widget.csproj", "package id declared by the project file"),),
        ),
        _install(polarity="UNRESOLVED"),
    ]
    resolved, _ = net.PLUGIN.registry_facts(declared)
    (install,) = resolved
    assert install.polarity == "CONTRADICTED"
    assert "distribution not found" in install.evidence[-1].detail
    product = "dotnet build src/Aspose.Widget/Aspose.Widget.csproj"
    snippet_failed = ExampleReceipt(
        1,
        "FAILED",
        1,
        "",
        "",
        "d",
        build_verified=True,
        build_command=product,  # type: ignore[arg-type]
    )
    # The admission now takes the measured build the facts stage supplies (one rule for every
    # path); the failed snippet beside it proves nothing and changes nothing.
    built = MeasuredBuild(True, product, f"succeeded (`{product}` exited 0)")
    admitted = _source_build_fact(install, NET_ENTRY, [snippet_failed], built)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.attributes == {"install_kind": "source", "build_command": product}
    assert admitted.value.endswith(product)
    assert "dotnet add package" not in admitted.value
    # No measured build: the 404 stands and nothing is admitted in its place.
    unbuilt = ExampleReceipt(
        1,
        "FAILED",
        1,
        "",
        "",
        "d",
        build_verified=False,
        build_command="",  # type: ignore[arg-type]
    )
    not_built = MeasuredBuild(False, "", f"failed (`{product}` exited 1)")
    refused = _source_build_fact(install, NET_ENTRY, [unbuilt], not_built)
    assert refused.polarity == "CONTRADICTED"
    assert refused.value == "dotnet add package Aspose.Widget"


TS_ENTRY = RegistryEntry.model_validate(
    {
        **ENTRY.model_dump(mode="json"),
        "repository": "aspose-widget-foss/Aspose.Widget-FOSS-for-TypeScript",
        "family": "widget",
        "platform": "typescript",
        "ecosystem": "typescript",
    }
)


def _built(command: str, build_verified: bool = True) -> ExampleReceipt:
    return ExampleReceipt(
        1, "EXECUTED", 0, "", "", "d", build_verified=build_verified, build_command=command
    )


def _npm_install() -> Fact:
    return Fact(
        "install_command:npm",
        "install_command",
        "npm install @aspose/widget",
        (
            Evidence("package.json", "install command for the name declared by the manifest"),
            Evidence("https://registry.npmjs.org/@aspose%2Fwidget", "not found on npm"),
        ),
        polarity="CONTRADICTED",
    )


def test_a_receipt_naming_the_steps_it_proved_outranks_the_ecosystems_template() -> None:
    """G4-W17 arrival item 50 (lane B, RESEARCH_LANE_B 617-645). Item 0's gate consulted an
    example receipt and the ecosystem's one template; TypeScript declares none, because no
    single command is verified for both its repositories - Aspose.3D builds (`npm run build`
    exit 0), Aspose.Cells has nothing to build and does not compile - so writing item 0's
    sentence for either would be a fabricated claim. A verifier that drove the manifest's own
    build names the exact steps that exited 0 on the receipt, per repository; the fact
    advertises those steps and states exactly what was proven, and nothing else."""
    plugin_for("typescript")  # imports platforms/typescript.py, which registers its own spec
    fact = _npm_install()
    # Before a receipt names a step: nothing to admit, exactly as before this item.
    assert _source_build_fact(fact, TS_ENTRY, [_receipt("EXECUTED")]) is fact
    admitted = _source_build_fact(fact, TS_ENTRY, [_built("npm install\nnpm run build")])
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-TypeScript.git\n"
        "cd Aspose.Widget-FOSS-for-TypeScript\nnpm install\nnpm run build"
    )
    assert admitted.attributes == {
        "install_kind": "source",
        "build_command": "npm install\nnpm run build",
    }
    assert admitted.evidence[-1].path == "examples.json"
    assert admitted.evidence[-1].detail == (
        "verified source build: the verifier ran `npm install` and `npm run build` against "
        "this revision, every step exiting 0; the advertised steps are exactly the ones it ran"
    )
    # Aspose.Cells' shape: only the install proved. The fact says that much and no more.
    install_only = _source_build_fact(fact, TS_ENTRY, [_built("npm install")])
    assert install_only.value.endswith("\nnpm install") and "run build" not in install_only.value
    assert install_only.evidence[-1].detail.startswith(
        "verified source build: the verifier ran `npm install` against this revision"
    )
    # A receipt naming steps it did not verify admits nothing (TB-01 still gates).
    assert _source_build_fact(fact, TS_ENTRY, [_built("npm install", build_verified=False)]) is fact
    # Where a template exists too, the measured steps outrank it - the receipt is per repository.
    measured = _source_build_fact(_install(), NET_ENTRY, [_built("dotnet build -c Release")])
    assert measured.value.endswith("\ndotnet build -c Release")
    assert measured.attributes == {
        "install_kind": "source",
        "build_command": "dotnet build -c Release",
    }
    # A verifier that drove no build leaves the template path exactly as before, receipt-less.
    templated = _source_build_fact(_install(), NET_ENTRY, [_receipt("EXECUTED")])
    assert templated.value.endswith("\ndotnet build")
    assert templated.attributes == {"install_kind": "source"}


def test_a_registry_having_ecosystems_unresolved_install_stays_unresolved() -> None:
    """G4-W17 arrival item 24's own mutation test. UNRESOLVED for a registry-having ecosystem
    means the probe could not be read this time - a transient reading, never "not published" -
    so it must keep failing closed even with an EXECUTED receipt, exactly as it did before this
    item; only a registry-less ecosystem's UNRESOLVED is admitted."""
    assert (
        _source_build_fact(_install("UNRESOLVED"), NET_ENTRY, [_receipt("EXECUTED")]).polarity
        == "UNRESOLVED"
    )


def _pip_install(polarity: str = "CONTRADICTED") -> Fact:
    return Fact(
        "install_command:pip",
        "install_command",
        "pip install aspose-html-foss",
        (
            Evidence("pyproject.toml", "distribution name declared by the manifest"),
            Evidence(
                "https://pypi.org/pypi/aspose-html-foss/json",
                "package registry: distribution not found",
            ),
        ),
        polarity=polarity,  # type: ignore[arg-type]
    )


def _checkout_receipt(
    ordinal: int = 1, outcome: str = "EXECUTED", source_roots: tuple[str, ...] = ("src", ".")
) -> ExampleReceipt:
    return ExampleReceipt(
        ordinal, outcome, 0, "from source", "", "d", build_verified=False, source_roots=source_roots
    )  # type: ignore[arg-type]


def test_a_source_checkout_is_admitted_when_no_build_ever_succeeds() -> None:
    """`RESEARCH_LANE_E.md`'s documented-PYTHONPATH-source-install observation, reproducing
    `aspose-html-foss/Aspose.HTML-FOSS-for-Python`'s exact shape: its `pyproject.toml` declares
    `build-backend = "setuptools.backends.legacy:build"`, a module in no setuptools release, so
    `pip install .` fails identically for every invocation - every receipt's `build_verified` is
    `False` - yet several examples still ran against the repository's own source tree with no
    build step at all. RED: a receipt with no `source_roots` (the shape before this tier existed)
    still leaves the fact CONTRADICTED, exactly as item (0)'s own gate did. GREEN: a receipt
    carrying `source_roots` - proof the fallback both ran and executed - admits a strictly weaker
    `install_kind`, whose value is honest PYTHONPATH instructions, never a pip command."""
    # RED: no source_roots anywhere (a plain failed build, not the fallback shape) - nothing to
    # admit, exactly item (0)'s own precedent for an unbuildable, unpublished package.
    plain_failure = [ExampleReceipt(1, "FAILED", 1, "", "boom", "d", build_verified=False)]
    assert _source_build_fact(_pip_install(), ENTRY, plain_failure).polarity == "CONTRADICTED"

    # GREEN: the fallback ran and at least one example executed against it.
    receipts = [
        _checkout_receipt(1, "EXECUTED"),
        _checkout_receipt(2, "FAILED"),  # not every example need succeed - one EXECUTED suffices
    ]
    admitted = _source_build_fact(_pip_install(), ENTRY, receipts)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.attributes == {"install_kind": "source_checkout"}
    assert admitted.value == (
        "git clone https://github.com/example-org/Aspose.Example-FOSS-for-Python.git\n"
        "cd Aspose.Example-FOSS-for-Python\n"
        'export PYTHONPATH="src:.:$PYTHONPATH"'
    )
    assert "pip install" not in admitted.value and "build" not in admitted.value
    assert admitted.evidence[-1].detail == (
        "source checkout only: every build/install attempt failed identically for this "
        "revision, but an example executed against the repository's own source tree with no "
        "build step - the advertised step is adding that tree to the interpreter's path, never "
        "a build or install command, which was never proven to succeed"
    )
    # The manifest's own evidence is kept, not replaced - it still justifies the value.
    assert admitted.evidence[0].detail == "distribution name declared by the manifest"


def test_a_genuine_verified_build_still_outranks_the_source_checkout_tier() -> None:
    """The new, weaker `source_checkout` tier must never compete with or suppress the existing
    verified-source-build tier (item (0)/(24)'s own precedent): a single genuine build receipt
    always wins, even alongside fallback receipts that would otherwise admit the weaker kind."""
    receipts = [
        _checkout_receipt(1, "EXECUTED"),  # a fallback receipt, as from an earlier, broken run
        _receipt("EXECUTED", build_verified=True),  # a genuine, verified build
    ]
    admitted = _source_build_fact(_pip_install(), ENTRY, receipts)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.attributes == {"install_kind": "source"}
    assert admitted.value.endswith("pip install .")


def test_the_fallbacks_own_receipts_wire_into_the_source_checkout_fact_end_to_end(
    tmp_path: Path,
) -> None:
    """The real `verify_python_examples` fallback path - not a hand-built receipt - reproduces
    the wiring `aspose-html-foss/Aspose.HTML-FOSS-for-Python` needs: a broken build-backend, a
    `src`-layout package `_source_roots` locates, and an example that only runs via the fallback.
    Proves `ExampleReceipt.source_roots` actually reaches `_source_build_fact` through the real
    extractor, not just through a test double."""
    from repository_presenter.components.readme.extractors.platforms.python_examples import (
        verify_python_examples,
    )

    root = tmp_path / "repo"
    root.mkdir()
    (root / "src" / "aspose_html_foss").mkdir(parents=True)
    (root / "src" / "aspose_html_foss" / "__init__.py").write_text(
        "VALUE = 'from source'\n", encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools"]\n'
        'build-backend = "setuptools.backends.legacy:build"\n'
        '[project]\nname = "aspose-html-foss"\nversion = "1.0"\n',
        encoding="utf-8",
    )
    tree = ["pyproject.toml", "src/aspose_html_foss/__init__.py"]
    candidate = ExampleCandidate(
        1,
        "python",
        "import aspose_html_foss\nprint(aspose_html_foss.VALUE)\n",
        "README.md",
        1,
        2,
        "inherited_unit:001.code_block",
    )
    receipts = verify_python_examples(root, tree, [candidate], tmp_path / "run")
    assert [(r.outcome, r.build_verified) for r in receipts] == [("EXECUTED", False)]
    assert receipts[0].source_roots == ("src", ".")

    admitted = _source_build_fact(_pip_install(), ENTRY, receipts)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.attributes == {"install_kind": "source_checkout"}
    assert admitted.value == (
        "git clone https://github.com/example-org/Aspose.Example-FOSS-for-Python.git\n"
        "cd Aspose.Example-FOSS-for-Python\n"
        'export PYTHONPATH="src:.:$PYTHONPATH"'
    )


def _npm_widget_repository(root: Path) -> Path:
    """A TypeScript package the registry does not list, declaring a build script: the shape of
    Aspose.PDF for TypeScript, whose `build` runs `tsc -p tsconfig.build.json`."""
    manifest = root / "package.json"
    manifest.write_text(
        json.dumps({"name": "@aspose/widget", "version": "1.0.0", "scripts": {"build": "tsc"}}),
        encoding="utf-8",
    )
    return manifest


def _npm_registry_reading(published: bool) -> RegistryObservation:
    return RegistryObservation(
        "npm",
        "@aspose/widget",
        published,
        False,
        "https://registry.npmjs.org/@aspose%2Fwidget",
        "packument",
        "test",
    )


def test_an_npm_404_falls_back_to_the_measured_npm_build_never_the_npm_install_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Aspose.PDF and Aspose.3D for TypeScript (measured 2026-10-04): npm answers 404 for the
    package the manifest declares, so `npm install <name>` is CONTRADICTED ("distribution not
    found"). That claim must neither block the candidate nor render. The one source-install rule
    admits exactly the steps the package's own build exited 0 on - here with no README example in
    the repository at all, end to end through the real TypeScript plugin. Only the registry read
    is replaced by its 404 answer."""
    from repository_presenter.components.readme.extractors.platforms import (
        typescript,
        typescript_examples,
    )
    from repository_presenter.components.readme.extractors.platforms.registry import verify_build

    repository = tmp_path / "repository"
    repository.mkdir()
    manifest = _npm_widget_repository(repository)
    npm = fake_npm(tmp_path / "tools")
    monkeypatch.setattr(typescript_examples, "npm_executable", lambda: npm)
    monkeypatch.setattr(typescript, "observe", lambda *args, **kwargs: _npm_registry_reading(False))
    plugin = plugin_for("typescript")
    resolved, _ = plugin.registry_facts(plugin.manifest_facts(repository, manifest, []))
    (install,) = [fact for fact in resolved if fact.id == "install_command:npm"]
    assert install.polarity == "CONTRADICTED"
    assert "distribution not found" in install.evidence[-1].detail

    measured = verify_build(plugin, repository, manifest, tmp_path / "ws")
    admitted = _source_build_fact(install, TS_ENTRY, [], measured)
    assert admitted.polarity == "SUPPORTED"
    assert admitted.value == (
        "git clone https://github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-TypeScript.git\n"
        "cd Aspose.Widget-FOSS-for-TypeScript\nnpm install\nnpm run build"
    )
    assert admitted.attributes == {
        "install_kind": "source",
        "build_command": "npm install\nnpm run build",
    }
    assert "npm install @" not in admitted.value
    assert "verified source build" in admitted.evidence[-1].detail


def test_a_published_npm_package_keeps_its_registry_claim_beside_a_measured_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: a registry hit is the claim the registry confirms. A measured build
    exists but is never substituted for a published package's own install command."""
    from repository_presenter.components.readme.extractors.platforms import typescript

    manifest = _npm_widget_repository(tmp_path)
    monkeypatch.setattr(typescript, "observe", lambda *args, **kwargs: _npm_registry_reading(True))
    plugin = plugin_for("typescript")
    resolved, _ = plugin.registry_facts(plugin.manifest_facts(tmp_path, manifest, []))
    (install,) = [fact for fact in resolved if fact.id == "install_command:npm"]
    assert install.polarity == "SUPPORTED" and install.value == "npm install @aspose/widget"
    built = MeasuredBuild(True, "npm install\nnpm run build", "succeeded (exited 0)")
    assert _source_build_fact(install, TS_ENTRY, [], built) is install


def test_an_unverified_npm_build_admits_nothing_and_the_404_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation control: a build that did not exit 0 proves nothing, so the 404 stands and the
    unverified `npm install` claim is what BC-02 then refuses (validation/test_registry)."""
    from repository_presenter.components.readme.extractors.platforms import typescript

    manifest = _npm_widget_repository(tmp_path)
    monkeypatch.setattr(typescript, "observe", lambda *args, **kwargs: _npm_registry_reading(False))
    plugin = plugin_for("typescript")
    resolved, _ = plugin.registry_facts(plugin.manifest_facts(tmp_path, manifest, []))
    (install,) = [fact for fact in resolved if fact.id == "install_command:npm"]
    # The command is named here on purpose: the `verified` flag alone must refuse it, not the
    # empty command every real failed build carries.
    not_built = MeasuredBuild(
        False,
        "npm install\nnpm run build",
        "failed (`npm run build` exited 3 after `npm install` exited 0)",
    )
    refused = _source_build_fact(install, TS_ENTRY, [], not_built)
    assert refused.polarity == "CONTRADICTED"
    assert refused.value == "npm install @aspose/widget"
