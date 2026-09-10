"""PA-03's third count: does a sealed candidate still render byte-identical to its own README
under the code running right now - promoted from tests/test_sealed_bytes.py's own logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.bundle.reproducibility import reproducible_candidates
from repository_presenter.components.readme.composition.renderer import render_readme
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.models import RegistryEntry
from support import write_bundle

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def _fact(
    fact_id: str, kind: str, value: str, detail: str = "", polarity: str = "SUPPORTED"
) -> Fact:
    return Fact(fact_id, kind, value, (Evidence("x", detail or None),), polarity=polarity)  # type: ignore[arg-type]


FACTS = FactsDocument(
    ENTRY.repository,
    "a" * 40,
    (
        _fact("identity:repository", "identity", ENTRY.repository),
        _fact("package:name", "package", "aspose-3d-foss"),
        _fact("package:version", "package", "26.1.0"),
        _fact("package:python_requires", "package", ">=3.7"),
        _fact("package:python_versions", "package", "3.7,3.8,3.12"),
        _fact("import_path:aspose", "import_path", "aspose"),
        _fact("import_path:aspose.threed", "import_path", "aspose.threed"),
        _fact("install_command:pip", "install_command", "pip install aspose-3d-foss"),
        _fact("license:spdx", "license", "MIT"),
        _fact("license:file", "license", "LICENSE"),
        Fact(
            "public_symbol:aspose.threed.scene",
            "public_symbol",
            "aspose.threed.Scene",
            (Evidence("x", "line 1; class; public by name"),),
            attributes={"symbol_kind": "class"},
        ),
        Fact(
            "public_symbol:aspose.threed.scene.save",
            "public_symbol",
            "aspose.threed.Scene.save",
            (Evidence("x", "line 9; method; public by name"),),
            attributes={"symbol_kind": "method"},
        ),
        _fact("format:output.glb", "format", ".glb"),
        _fact("format:input.obj", "format", ".obj"),
        _fact("example:001", "example", "from aspose.threed import Scene\nScene().save('a.glb')\n"),
        _fact("example:002", "example", "print(2)\n"),
        _fact(
            "link_target:002",
            "link_target",
            "https://docs.example.com/3d",
            "line 5; external; text 'Docs'",
        ),
        _fact("build_test_asset:tests", "build_test_asset", "tests/"),
    ),
)

PLAN: dict[str, Any] = {
    "sections": [
        {
            "section_id": s,
            "include": s
            not in {"banner", "dependencies", "enterprise_relationship", "third_party_notices"},
            "reason": "r",
        }
        for s in [
            "identity",
            "badges",
            "banner",
            "opening",
            "navigation",
            "at_a_glance",
            "key_capabilities",
            "installation",
            "dependencies",
            "quick_start",
            "additional_examples",
            "api_reference",
            "documentation_resources",
            "scope_limitations",
            "development_testing",
            "enterprise_relationship",
            "third_party_notices",
            "license",
        ]
    ],
    "core_capabilities": [
        {"title": "Build scenes", "fact_ids": ["public_symbol:aspose.threed.scene"]},
        {"title": "Save GLB", "fact_ids": ["format:output.glb"]},
    ],
    "at_a_glance": {
        "input_format_ids": ["format:input.obj"],
        "output_format_ids": ["format:output.glb"],
        "capability_titles": ["Build scenes", "Save GLB"],
    },
    "quick_start_example_id": "example:001",
    "additional_example_ids": ["example:002"],
    "api_hubs": [
        {"symbol_fact_id": "public_symbol:aspose.threed.scene", "fact_ids": ["example:001"]}
    ],
    "material_limitations": [{"fact_ids": ["format:input.obj"], "unit_ids": []}],
    "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
    "deviations": [],
}


def _unit(section: str, slot: str, text: str) -> dict[str, Any]:
    return {"section": section, "slot": slot, "text": text, "fact_ids": ["identity:repository"]}


UNITS = {
    "units": [
        _unit(
            "opening",
            "opening",
            "Aspose.3D FOSS for Python builds scenes with Scene and saves them with Scene.save.",
        ),
        _unit(
            "key_capabilities", "capability:1", "Scenes are built from aspose.threed.Scene objects."
        ),
        _unit("key_capabilities", "capability:2", "A scene saves as GLB."),
        _unit("quick_start", "lead_in", "Create a scene and save it."),
        _unit("additional_examples", "preview", "One more workflow follows."),
        _unit("additional_examples", "workflow:example:002", "Print a number"),
        _unit("api_reference", "intro", "Scene is the entry point; Node hangs off it."),
        _unit(
            "api_reference", "hub:public_symbol:aspose.threed.scene", "Scene holds the scene graph."
        ),
        _unit("documentation_resources", "link:link_target:002", "The docs explain the API."),
        _unit("scope_limitations", "scope", "The package writes GLB only."),
        _unit("scope_limitations", "limitation:1", "OBJ import is unverified."),
        _unit("development_testing", "summary", "Run the tests with the standard runner."),
    ],
    "omitted": [],
}
DISPOSITIONS: dict[str, Any] = {"dispositions": []}


def _seed_bundle(root: Path, repository_dir: str, revision: str) -> Path:
    """A real, genuinely-renderable bundle: seed via write_bundle for CURRENT/manifest.json's
    own boilerplate, then overwrite the documents render_readme actually reads with the fixture
    above - the same one that would produce a real README for this exact facts/plan/units set."""
    bundle = write_bundle(root, repository_dir, revision, "READY_FOR_PROPOSAL")
    (bundle / "facts.json").write_text(FACTS.to_json(), encoding="utf-8")
    (bundle / "plan.json").write_text(json.dumps(PLAN), encoding="utf-8")
    (bundle / "content_units.json").write_text(json.dumps(UNITS), encoding="utf-8")
    (bundle / "dispositions.json").write_text(json.dumps(DISPOSITIONS), encoding="utf-8")
    registry_path = root / "data" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"entries": [ENTRY.model_dump()]}), encoding="utf-8")
    return bundle


def test_reproducible_candidates_with_no_candidates_directory_is_zero(tmp_path: Path) -> None:
    assert reproducible_candidates(tmp_path) == 0


def test_reproducible_candidates_counts_a_bundle_that_still_renders_to_its_own_bytes(
    tmp_path: Path,
) -> None:
    bundle = _seed_bundle(tmp_path, "aspose-3d-foss__Aspose.3D-FOSS-for-Python", "rev1")
    rendered = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    (bundle / "README.md").write_text(rendered, encoding="utf-8")
    assert reproducible_candidates(tmp_path) == 1


def test_reproducible_candidates_excludes_a_candidate_whose_readme_diverges_from_a_real_render(
    tmp_path: Path,
) -> None:
    """The genuine synthetic-divergence case PA-03's own appendix asks for: a real render_readme()
    call against a minimal, valid facts/plan/dispositions set, deliberately compared against a
    README that does not match it - not a trivial empty-file stub."""
    bundle = _seed_bundle(tmp_path, "aspose-3d-foss__Aspose.3D-FOSS-for-Python", "rev1")
    (bundle / "README.md").write_text("# stale content, not what render_readme produces\n")
    assert reproducible_candidates(tmp_path) == 0


def test_reproducible_candidates_excludes_a_non_counted_state_bundle(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, "aspose-3d-foss__Aspose.3D-FOSS-for-Python", "rev1", "ACCEPTED")
    (bundle / "facts.json").write_text(FACTS.to_json(), encoding="utf-8")
    (bundle / "plan.json").write_text(json.dumps(PLAN), encoding="utf-8")
    (bundle / "content_units.json").write_text(json.dumps(UNITS), encoding="utf-8")
    (bundle / "dispositions.json").write_text(json.dumps(DISPOSITIONS), encoding="utf-8")
    registry_path = tmp_path / "data" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"entries": [ENTRY.model_dump()]}), encoding="utf-8")
    rendered = render_readme(ENTRY, FACTS, PLAN, UNITS, DISPOSITIONS)
    (bundle / "README.md").write_text(rendered, encoding="utf-8")
    assert reproducible_candidates(tmp_path) == 0


def test_reproducible_candidates_excludes_an_unlisted_repository(tmp_path: Path) -> None:
    """A bundle whose repository is not in the registry cannot be matched to a RegistryEntry, so
    it cannot be rendered at all - excluded silently, not an error (module docstring)."""
    bundle = write_bundle(tmp_path, "unlisted__repo", "rev1", "READY_FOR_PROPOSAL")
    (bundle / "facts.json").write_text(
        FactsDocument("unlisted/repo", "a" * 40, FACTS.facts).to_json(), encoding="utf-8"
    )
    (bundle / "plan.json").write_text(json.dumps(PLAN), encoding="utf-8")
    (bundle / "content_units.json").write_text(json.dumps(UNITS), encoding="utf-8")
    (bundle / "dispositions.json").write_text(json.dumps(DISPOSITIONS), encoding="utf-8")
    registry_path = tmp_path / "data" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({"entries": [ENTRY.model_dump()]}), encoding="utf-8")
    (bundle / "README.md").write_text("irrelevant\n", encoding="utf-8")
    assert reproducible_candidates(tmp_path) == 0


def test_reproducible_candidates_with_no_registry_file_is_zero_not_a_crash(tmp_path: Path) -> None:
    write_bundle(
        tmp_path, "aspose-3d-foss__Aspose.3D-FOSS-for-Python", "rev1", "READY_FOR_PROPOSAL"
    )
    assert reproducible_candidates(tmp_path) == 0
