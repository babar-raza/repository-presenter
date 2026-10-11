"""The defect-class registry (`components/issues/classes.py`, G6-W07, TC-ISS-03).

Every detector is held to a failing and a passing fixture, taken from the real cases the lane
reviews found (tree listings and file texts trimmed from the pinned clones): the `License/`
directory in Aspose.Cells for Cpp, Java and Python; no license in Aspose.3D for TypeScript and
Aspose.GIS; the `yourorg` URLs and author `SID` in Aspose.PSD for .NET's csproj; the 69-byte
README of Aspose.PSD for Python; no README in Aspose.GIS. The one fixture with no real case,
a license file that contradicts the manifest, is synthetic and named so.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from repository_presenter.components.issues import classes, draft, redetect
from repository_presenter.components.issues.classes import (
    REGISTRY,
    DefectFinding,
    Observation,
    build_observation,
    candidate_manifests,
    detect_all,
    detect_license_mismatch,
    detect_license_missing_root,
    detect_manifest_placeholder_metadata,
    detect_readme_missing_or_placeholder,
    fingerprint,
    observation_from_clone,
    parse_manifest_metadata,
)
from repository_presenter.components.issues.draft import (
    draft_class_handoff,
    draft_class_handoffs,
    eligible_defect_classes,
    record_class_handoffs_if_new,
)
from repository_presenter.components.issues.ledger import load_ledger, lookup
from repository_presenter.components.issues.model import (
    DEFECT_CLASSES,
    EvidenceEntry,
    HandoffError,
    handoff_from_dict,
    handoff_to_dict,
    load_handoff,
)
from repository_presenter.components.issues.quality import HandoffQualityError
from repository_presenter.core.github.read_client import (
    DefaultBranchRead,
    FileRead,
    TreeRead,
)
from support import REPO_ROOT

CPP = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
JAVA = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
PYTHON = "aspose-cells-foss/Aspose.Cells-FOSS-for-Python"
THREE_D_TS = "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript"
GIS = "aspose-gis-foss/Aspose.GIS.FOSS-for-.Net"
PSD_NET = "aspose-psd-foss/Aspose.PSD-FOSS-for-.NET"
PSD_PY = "aspose-psd-foss/Aspose.PSD-FOSS-for-Python"
REV = "9f852d0ff1cfdad2d661556d6b87a8eff8c063a2"
OTHER_REV = "c65329e7257b1311abb9686d7e4957a8cc002955"

SCHEMA = json.loads(
    (REPO_ROOT / "schemas" / "upstream-defect-handoff.schema.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA)

# --- real fixtures -------------------------------------------------------------------------------

CPP_TREE = (
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "License/LICENSE.txt",
    "Aspose.Cells.Foss.Cpp/CMakeLists.txt",
    "Aspose.Cells.Foss.Cpp/include/workbook.hpp",
    "Aspose.Cells.Foss.Cpp.Tests/README.md",
    "samples/README.md",
)
JAVA_TREE = (
    ".gitignore",
    "Agents.md",
    "PUBLISHING.md",
    "README.md",
    "pom.xml",
    "License/LICENSE.txt",
    "docs/apidocs/legal/LICENSE",
)
PYTHON_TREE = (
    "AGENTS.md",
    "README.md",
    "llms.md",
    "pyproject.toml",
    "requirements.txt",
    "License/LICENSE.txt",
)
TS_TREE = (
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "jest.config.js",
    "package.json",
    "tsconfig.json",
)
TS_PACKAGE_JSON = json.dumps(
    {"name": "@aspose/3d", "author": "Lex Chou <lex.chou@aspose.com>", "license": "MIT"}
)
GIS_TREE = (
    ".gitignore",
    "Aspose.GIS.FOSS.slnx",
    "Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj",
    "Aspose.GIS.FOSS.Tests/Aspose.GIS.FOSS.Tests.csproj",
    "Aspose.GIS.FOSS.Tests/MainTests.cs",
)
GIS_CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <AssemblyName>Aspose.GIS.FOSS</AssemblyName>
  </PropertyGroup>
</Project>
"""
PSD_NET_TREE = (
    ".gitignore",
    "Aspose.PSD-FOSS-for-.NET.sln",
    "README.md",
    "documentation/README.md",
    "samples/Aspose.PSD.FOSS.Samples.Basic/Aspose.PSD.FOSS.Samples.Basic.csproj",
    "src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj",
    "src/Aspose.PSD.FOSS.Test/Aspose.PSD.FOSS.Test.csproj",
)
PSD_CSPROJ_PATH = "src/Aspose.PSD.FOSS/Aspose.PSD.FOSS.csproj"
# The csproj as pinned, including its byte-order mark.
PSD_CSPROJ = """﻿<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <AssemblyName>Aspose.PSD.FOSS</AssemblyName>
    <PackageId>Aspose.PSD.FOSS</PackageId>
    <Version>1.0.0</Version>
    <Authors>SID</Authors>
    <Description>Free Open Source .NET library for basic PSD file operations</Description>
    <PackageLicenseExpression>MIT</PackageLicenseExpression>
    <PackageProjectUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</PackageProjectUrl>
    <RepositoryUrl>https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET</RepositoryUrl>
    <RepositoryType>git</RepositoryType>
  </PropertyGroup>

</Project>
"""
PSD_PY_TREE = (".gitignore", "README.md", "aspose_psd_foss/__init__.py", "artifacts/x.txt")
PSD_PY_README = "# Aspose.PSD-FOSS-for-Python\r\nFOSS version of Aspose.PSD for Python\r\n"
MIT_TEXT = "The MIT License (MIT)\n\nCopyright (c) 2001-2025 Aspose Pty Ltd\n"
APACHE_TEXT = "Apache License\nVersion 2.0, January 2004\n"
SUBSTANTIVE_README = "# Product\n\n" + "A library that reads and writes files. " * 30 + "\n"


def _observation(
    repository: str,
    tree: tuple[str, ...],
    files: dict[str, str] | None = None,
    revision: str = REV,
) -> Observation:
    return build_observation(repository, revision, tree, lambda p: (files or {}).get(p))


def _classes_of(observation: Observation) -> list[str]:
    return [finding.defect_class for finding in detect_all(observation)]


# --- the registry ---------------------------------------------------------------------------------


def test_the_registry_the_model_and_the_schema_name_the_same_classes() -> None:
    schema_enum = SCHEMA["properties"]["defect_class"]["enum"]
    assert set(REGISTRY) == set(DEFECT_CLASSES) == set(schema_enum)
    assert len(DEFECT_CLASSES) == len(schema_enum) == len(set(schema_enum))


def test_every_detectable_class_has_a_detector_template_and_a_registered_redetector() -> None:
    registered = set(redetect.registered_check_ids())
    for spec in REGISTRY.values():
        assert spec.severity in {"high", "medium", "low"}
        assert spec.fingerprint_basis
        assert spec.redetector in registered, spec.id
        if spec.detector is not None:
            assert spec.detector_name and spec.detector_name.startswith("detect_")
            assert spec.template is not None
            assert spec.redetector == spec.id
        else:
            assert spec.template is None
            assert spec.redetector != spec.id


def test_the_three_classes_that_reuse_evidence_name_an_existing_check() -> None:
    mapped = {s.id: s.redetector for s in REGISTRY.values() if s.detector is None}
    assert mapped == {
        "SOURCE_UNPARSEABLE": "NOT_PROCESSABLE",
        "BUILD_OR_TESTS_FAIL": "BC-02",
        "EXAMPLE_FAILS": "BC-03",
        "INSTALL_FAILS": "BC-02",
    }


def test_registering_an_unadmitted_or_duplicate_class_is_refused() -> None:
    template = classes.IssueTemplate("s", "t", "e", "a")
    with pytest.raises(ValueError, match="not a defect class"):
        classes.defect_class("MADE_UP", severity="low", fingerprint_basis="x", template=template)(
            lambda observation: []
        )
    with pytest.raises(ValueError, match="registered twice"):
        classes.defect_class(
            "LICENSE_MISMATCH", severity="low", fingerprint_basis="x", template=template
        )(lambda observation: [])
    with pytest.raises(ValueError, match="not a defect class"):
        classes.declare_mapped("MADE_UP", severity="low", redetector="BC-02", fingerprint_basis="x")


def test_a_consumer_of_the_ledger_alone_can_replay_a_class_handoff() -> None:
    """Importing the ledger (what readiness does) registers the class redetectors."""
    code = (
        "import repository_presenter.components.issues.ledger\n"
        "from repository_presenter.components.issues.redetect import registered_check_ids\n"
        "raise SystemExit(0 if 'LICENSE_MISSING_ROOT' in registered_check_ids() else 1)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr


# --- LICENSE_MISSING_ROOT -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("repository", "tree", "manifest_files"),
    [
        (CPP, CPP_TREE, {}),
        (
            JAVA,
            JAVA_TREE,
            {
                "pom.xml": "<project><licenses><license><name>MIT License</name>"
                "</license></licenses></project>"
            },
        ),
        (PYTHON, PYTHON_TREE, {"pyproject.toml": 'license = {text = "MIT"}\n'}),
    ],
    ids=["cells-cpp", "cells-java", "cells-python"],
)
def test_a_license_only_under_license_directory_is_reported_as_moved(
    repository: str, tree: tuple[str, ...], manifest_files: dict[str, str]
) -> None:
    findings = detect_license_missing_root(_observation(repository, tree, manifest_files))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.statement == "the license file is only in License/, not at the repository root"
    assert finding.evidence[1] == EvidenceEntry(
        "License/LICENSE.txt", "the only license file in the tree"
    )
    # The vendored doc-site LICENSE under docs/apidocs/legal is never mistaken for the project's.
    assert "docs/apidocs" not in finding.claim


@pytest.mark.parametrize(
    ("repository", "tree", "files"),
    [
        (THREE_D_TS, TS_TREE, {"package.json": TS_PACKAGE_JSON}),
        (GIS, GIS_TREE, {"Aspose.GIS.FOSS/Aspose.GIS.FOSS.csproj": GIS_CSPROJ}),
    ],
    ids=["3d-typescript", "gis-dotnet"],
)
def test_no_license_anywhere_is_reported_as_absent(
    repository: str, tree: tuple[str, ...], files: dict[str, str]
) -> None:
    findings = detect_license_missing_root(_observation(repository, tree, files))
    assert [f.statement for f in findings] == ["no license file at the repository root"]


def test_the_manifest_declaration_is_named_in_the_report() -> None:
    finding = detect_license_missing_root(
        _observation(THREE_D_TS, TS_TREE, {"package.json": TS_PACKAGE_JSON})
    )[0]
    assert "`package.json` declares the license as `MIT`" in finding.fields["actual"]


@pytest.mark.parametrize("license_name", ["LICENSE", "License.txt", "LICENSE.md", "COPYING"])
def test_a_root_license_in_any_usual_spelling_passes(license_name: str) -> None:
    assert detect_license_missing_root(_observation(CPP, (*CPP_TREE, license_name))) == []


def test_a_license_only_in_a_vendored_or_generated_directory_is_not_the_projects() -> None:
    tree = (*TS_TREE, "node_modules/x/LICENSE", "docs/apidocs/legal/LICENSE")
    finding = detect_license_missing_root(_observation(THREE_D_TS, tree))[0]
    assert finding.statement == "no license file at the repository root"


def test_an_empty_tree_is_unobserved_not_a_defect() -> None:
    assert detect_all(_observation(CPP, ())) == []


# --- LICENSE_MISMATCH -----------------------------------------------------------------------------


def test_a_license_file_that_contradicts_the_manifest_is_reported_synthetic_case() -> None:
    tree = ("LICENSE", "README.md", "pyproject.toml")
    files = {"LICENSE": MIT_TEXT, "pyproject.toml": '[project]\nlicense = "Apache-2.0"\n'}
    findings = detect_license_mismatch(_observation("acme/tool", tree, files))
    assert len(findings) == 1
    assert findings[0].statement == "LICENSE is MIT but pyproject.toml declares Apache-2.0"
    assert findings[0].signature == "LICENSE:MIT != pyproject.toml:Apache-2.0"


def test_a_license_file_that_agrees_with_the_manifest_passes() -> None:
    tree = ("LICENSE", "pyproject.toml")
    files = {"LICENSE": MIT_TEXT, "pyproject.toml": '[project]\nlicense = {text = "MIT"}\n'}
    assert detect_license_mismatch(_observation("acme/tool", tree, files)) == []
    assert (
        detect_license_mismatch(_observation("acme/tool", tree, {**files, "LICENSE": APACHE_TEXT}))
        != []
    )


@pytest.mark.parametrize(
    "manifest",
    [
        '[project]\nlicense = "SEE LICENSE IN EULA.txt"\n',  # names no known license
        '[project]\nname = "x"\n',  # declares nothing
        "not = [valid toml",  # does not parse
    ],
)
def test_an_unknown_or_missing_declaration_is_never_a_mismatch(manifest: str) -> None:
    files = {"LICENSE": MIT_TEXT, "pyproject.toml": manifest}
    assert (
        detect_license_mismatch(_observation("acme/tool", ("LICENSE", "pyproject.toml"), files))
        == []
    )


def test_an_unclassifiable_license_text_is_never_a_mismatch() -> None:
    files = {"LICENSE": "All rights reserved.\n", "pyproject.toml": '[project]\nlicense = "MIT"\n'}
    assert (
        detect_license_mismatch(_observation("acme/tool", ("LICENSE", "pyproject.toml"), files))
        == []
    )


# --- MANIFEST_PLACEHOLDER_METADATA ----------------------------------------------------------------


def test_the_psd_dotnet_csproj_placeholders_are_found() -> None:
    observation = _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: PSD_CSPROJ})
    findings = detect_manifest_placeholder_metadata(observation)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.statement == "Aspose.PSD.FOSS.csproj contains placeholder metadata"
    assert [e.detail for e in finding.evidence] == [
        "Authors = SID",
        "PackageProjectUrl = https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET",
        "RepositoryUrl = https://github.com/yourorg/Aspose.PSD-FOSS-for-.NET",
    ]
    assert finding.signature == f"placeholder metadata in {PSD_CSPROJ_PATH}"


def test_the_same_csproj_with_real_values_passes() -> None:
    fixed = PSD_CSPROJ.replace("yourorg", "aspose-psd-foss").replace(
        "<Authors>SID</Authors>", "<Authors>Aspose</Authors>"
    )
    observation = _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: fixed})
    assert detect_manifest_placeholder_metadata(observation) == []


def test_fixing_one_of_several_placeholders_keeps_the_same_fingerprint() -> None:
    partly = PSD_CSPROJ.replace("<Authors>SID</Authors>", "<Authors>Aspose</Authors>")
    before = detect_manifest_placeholder_metadata(
        _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: PSD_CSPROJ})
    )[0]
    after = detect_manifest_placeholder_metadata(
        _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: partly})
    )[0]
    assert before.signature == after.signature
    assert len(after.evidence) == 2


def test_sample_and_test_projects_are_not_read_for_package_metadata() -> None:
    chosen = candidate_manifests(PSD_NET_TREE)
    assert chosen == (PSD_CSPROJ_PATH,)
    assert candidate_manifests(PSD_NET_TREE, hints=("nowhere.csproj",)) == chosen


@pytest.mark.parametrize(
    ("name", "text", "expected_keys"),
    [
        (
            "package.json",
            json.dumps(
                {
                    "name": "x",
                    "homepage": "https://github.com/your-org/x",
                    "author": {"name": "Your Name", "email": "you@example.com"},
                    "dependencies": {"y": "https://github.com/yourorg/y"},
                }
            ),
            ["author.email", "author.name", "homepage"],
        ),
        (
            "pyproject.toml",
            '[project]\nname = "x"\nauthors = [{name = "Author", email = "a@b.io"}]\n'
            '[project.urls]\nHomepage = "https://example.com/x"\n',
            ["project.authors.0.name", "project.urls.Homepage"],
        ),
    ],
    ids=["package-json", "pyproject"],
)
def test_placeholder_metadata_in_other_manifest_formats(
    name: str, text: str, expected_keys: list[str]
) -> None:
    metadata = parse_manifest_metadata(name, text)
    hits = classes._placeholder_hits(metadata)
    assert sorted(key for key, _ in hits) == expected_keys


def test_a_real_project_manifest_is_clean() -> None:
    metadata = parse_manifest_metadata("package.json", TS_PACKAGE_JSON)
    assert classes._placeholder_hits(metadata) == []


# --- README_MISSING_OR_PLACEHOLDER ----------------------------------------------------------------


def test_gis_dotnet_has_no_readme() -> None:
    findings = detect_readme_missing_or_placeholder(_observation(GIS, GIS_TREE))
    assert [f.statement for f in findings] == ["the repository has no README"]


def test_the_69_byte_psd_python_readme_is_a_placeholder() -> None:
    observation = _observation(PSD_PY, PSD_PY_TREE, {"README.md": PSD_PY_README})
    findings = detect_readme_missing_or_placeholder(observation)
    assert len(findings) == 1
    assert findings[0].statement == "README.md is a 69-byte placeholder with no usable content"
    assert findings[0].signature == "README placeholder README.md"


def test_a_substantive_readme_passes() -> None:
    observation = _observation(PSD_PY, PSD_PY_TREE, {"README.md": SUBSTANTIVE_README})
    assert detect_readme_missing_or_placeholder(observation) == []


@pytest.mark.parametrize(
    "text",
    [
        "# Tiny\n\nInstall with `pip install tiny`.\n",  # small, but it tells a visitor something
        "# Tiny\n\nSee https://example.org/tiny for documentation.\n",
        "# Tiny\n\n" + "word " * 40,  # short in bytes? no: long in words
    ],
)
def test_a_small_readme_that_gives_a_command_or_a_link_is_never_reported(text: str) -> None:
    observation = _observation(PSD_PY, PSD_PY_TREE, {"README.md": text})
    assert detect_readme_missing_or_placeholder(observation) == []


def test_an_unread_readme_is_not_judged() -> None:
    observation = _observation(PSD_PY, PSD_PY_TREE, {})
    assert detect_readme_missing_or_placeholder(observation) == []
    assert observation.unreadable == ("README.md",)


# --- drafting, the quality gate and the ledger ----------------------------------------------------

REAL_CASES = [
    (CPP, CPP_TREE, {}, "LICENSE_MISSING_ROOT"),
    (JAVA, JAVA_TREE, {}, "LICENSE_MISSING_ROOT"),
    (PYTHON, PYTHON_TREE, {"pyproject.toml": 'license = {text = "MIT"}\n'}, "LICENSE_MISSING_ROOT"),
    (THREE_D_TS, TS_TREE, {"package.json": TS_PACKAGE_JSON}, "LICENSE_MISSING_ROOT"),
    (PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: PSD_CSPROJ}, "MANIFEST_PLACEHOLDER_METADATA"),
    (PSD_PY, PSD_PY_TREE, {"README.md": PSD_PY_README}, "README_MISSING_OR_PLACEHOLDER"),
    (GIS, GIS_TREE, {}, "README_MISSING_OR_PLACEHOLDER"),
]


@pytest.mark.parametrize(
    ("repository", "tree", "files", "expected"), REAL_CASES, ids=[c[0] for c in REAL_CASES]
)
def test_a_facts_only_observation_drafts_a_gate_passing_schema_valid_handoff(
    repository: str, tree: tuple[str, ...], files: dict[str, str], expected: str
) -> None:
    observation = _observation(repository, tree, files)
    assert expected in eligible_defect_classes(observation)
    handoffs = [h for h in draft_class_handoffs(observation) if h.defect_class == expected]
    assert len(handoffs) == 1
    handoff = handoffs[0]
    assert handoff.status == "HANDOFF_PENDING"
    assert handoff.triggering_check.id == expected
    assert handoff.suggested_issue_title.startswith(
        repository.split("/", 1)[1].replace("-", " ") + ": "
    )
    assert f"<!-- repository-presenter-defect: {handoff.defect_fingerprint} -->" in (
        handoff.suggested_issue_body
    )
    assert list(VALIDATOR.iter_errors(json.loads(json.dumps(handoff_to_dict(handoff))))) == []


def test_gis_dotnet_yields_both_of_its_handoffs() -> None:
    handoffs = draft_class_handoffs(_observation(GIS, GIS_TREE))
    assert sorted(h.defect_class or "" for h in handoffs) == [
        "LICENSE_MISSING_ROOT",
        "README_MISSING_OR_PLACEHOLDER",
    ]
    assert len({h.defect_fingerprint for h in handoffs}) == 2


def test_a_repository_with_none_of_these_defects_drafts_nothing() -> None:
    tree = ("LICENSE", "README.md", "package.json")
    files = {"LICENSE": MIT_TEXT, "README.md": SUBSTANTIVE_README, "package.json": TS_PACKAGE_JSON}
    observation = _observation("acme/tool", tree, files)
    assert detect_all(observation) == []
    assert draft_class_handoffs(observation) == []


def test_detection_is_deterministic_and_ordered() -> None:
    observation = _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: PSD_CSPROJ})
    assert detect_all(observation) == detect_all(observation)
    assert _classes_of(observation) == ["LICENSE_MISSING_ROOT", "MANIFEST_PLACEHOLDER_METADATA"]


def test_a_new_class_never_collides_with_a_check_fingerprint() -> None:
    signature = "no license file at the root"
    assert fingerprint(CPP, "LICENSE_MISSING_ROOT", signature) != fingerprint(
        CPP, "BC-02", signature
    )
    # ... nor across repositories, revisions are not part of the key.
    assert fingerprint(CPP, "LICENSE_MISSING_ROOT", signature) != fingerprint(
        JAVA, "LICENSE_MISSING_ROOT", signature
    )
    first = draft_class_handoffs(_observation(CPP, CPP_TREE))
    later = draft_class_handoffs(_observation(CPP, CPP_TREE, revision=OTHER_REV))
    assert first[0].defect_fingerprint == later[0].defect_fingerprint


def _hostile_finding(statement: str = "the license is missing", **fields: str) -> DefectFinding:
    return DefectFinding(
        defect_class="LICENSE_MISSING_ROOT",
        signature="x",
        statement=statement,
        claim="At a revision, a repository has no license.",
        fields={"detail": "", "actual": "The root has none.", **fields},
        evidence=(EvidenceEntry("git ls-tree --name-only abc", "none"),),
    )


def test_text_that_fails_the_quality_gate_is_never_drafted() -> None:
    observation = _observation(CPP, CPP_TREE)
    with pytest.raises(HandoffQualityError) as caught:
        draft_class_handoff(
            _hostile_finding(actual="Our wrapper hides it; see BC-02."), observation=observation
        )
    assert {f.code for f in caught.value.findings} >= {"INTERNAL_NAME", "TONE", "EDITION_WORDING"}
    with pytest.raises(HandoffQualityError):
        draft_class_handoff(_hostile_finding(statement="x"), observation=observation)


def test_a_failing_finding_is_dropped_from_the_batch_not_weakened(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good = detect_all(_observation(CPP, CPP_TREE))[0]
    bad = _hostile_finding(actual="Our wrapper hides it.")
    monkeypatch.setattr(draft, "detect_all", lambda observation: [bad, good])
    handoffs = draft_class_handoffs(_observation(CPP, CPP_TREE))
    assert [h.defect_class for h in handoffs] == ["LICENSE_MISSING_ROOT"]


def test_a_secret_in_manifest_metadata_never_reaches_a_handoff() -> None:
    token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
    package = json.dumps({"homepage": "https://github.com/yourorg/x", "author": token})
    observation = _observation(
        "acme/tool",
        ("LICENSE", "README.md", "package.json"),
        {"LICENSE": MIT_TEXT, "README.md": SUBSTANTIVE_README, "package.json": package},
    )
    # the placeholder URL is reported; the author is no placeholder, so the token is not echoed
    handoffs = draft_class_handoffs(observation)
    assert [h.defect_class for h in handoffs] == ["MANIFEST_PLACEHOLDER_METADATA"]
    assert token not in handoffs[0].suggested_issue_body


def test_record_writes_once_and_the_ledger_dedups(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    observation = _observation(GIS, GIS_TREE)
    written = record_class_handoffs_if_new(root, observation=observation)
    assert len(written) == 2
    loaded = [load_handoff(path) for path in written]
    assert sorted(h.defect_class or "" for h in loaded) == [
        "LICENSE_MISSING_ROOT",
        "README_MISSING_OR_PLACEHOLDER",
    ]
    ledger = load_ledger(root)
    for handoff in loaded:
        entry = lookup(ledger, handoff.repository, handoff.defect_fingerprint)
        assert entry is not None and entry.defect_class == handoff.defect_class
    # A later run, even at a newer revision, writes nothing new.
    assert record_class_handoffs_if_new(root, observation=observation) == []
    later = _observation(GIS, GIS_TREE, revision=OTHER_REV)
    assert record_class_handoffs_if_new(root, observation=later) == []
    # A different defect of the same repository is new.
    with_readme = _observation(GIS, (*GIS_TREE, "README.md"), {"README.md": "# x\n"})
    assert len(record_class_handoffs_if_new(root, observation=with_readme)) == 1


# --- the model and the schema ---------------------------------------------------------------------


def _legacy_payload() -> dict:
    """The first committed handoff drafted before the class registry (it carries no class)."""
    for existing in sorted((REPO_ROOT / "evidence" / "upstream-defects").glob("*/*.json")):
        payload = json.loads(existing.read_text(encoding="utf-8"))
        if "defect_class" not in payload:
            return payload
    raise AssertionError("no handoff without a defect class is on record")


def test_every_handoff_on_record_stays_valid_with_or_without_the_field() -> None:
    paths = sorted((REPO_ROOT / "evidence" / "upstream-defects").glob("*/*.json"))
    assert paths
    legacy = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert list(VALIDATOR.iter_errors(payload)) == []
        handoff = handoff_from_dict(payload, path=path)
        if "defect_class" in payload:
            # A handoff drafted with a class round-trips it.
            assert handoff.defect_class == payload["defect_class"]
            assert handoff_to_dict(handoff)["defect_class"] == handoff.defect_class
            continue
        # A handoff drafted before the registry stays valid and serializes without the field.
        legacy += 1
        assert handoff.defect_class is None
        assert "defect_class" not in handoff_to_dict(handoff)
    assert legacy


def test_a_defect_class_round_trips_and_an_unknown_one_is_refused() -> None:
    payload = _legacy_payload()
    payload["defect_class"] = "LICENSE_MISSING_ROOT"
    assert list(VALIDATOR.iter_errors(payload)) == []
    handoff = handoff_from_dict(payload, path=Path("x.json"))
    assert handoff.defect_class == "LICENSE_MISSING_ROOT"
    assert handoff_to_dict(handoff)["defect_class"] == "LICENSE_MISSING_ROOT"
    payload["defect_class"] = "MADE_UP"
    assert list(VALIDATOR.iter_errors(payload)) != []
    with pytest.raises(HandoffError, match="unknown defect_class"):
        handoff_from_dict(payload, path=Path("x.json"))


# --- the redetector -------------------------------------------------------------------------------


def _reads(
    tree: tuple[str, ...],
    files: dict[str, str],
    *,
    head: str = OTHER_REV,
    truncated: bool = False,
    tree_error: str | None = None,
) -> redetect.RedetectionReads:
    def fetch_file(repository: str, revision: str, path: str, **_: object) -> FileRead:
        text = files.get(path)
        return FileRead(repository, revision, path, found=text is not None, content=text)

    return redetect.RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=head, branch="main"
        ),
        fetch_file=fetch_file,
        fetch_tree=lambda repository, revision, **_: TreeRead(
            repository, revision, paths=tree, truncated=truncated, error=tree_error
        ),
    )


def _filed(observation: Observation, class_id: str):
    handoff = next(h for h in draft_class_handoffs(observation) if h.defect_class == class_id)
    return handoff


def test_the_redetector_sees_a_license_defect_still_there() -> None:
    handoff = _filed(_observation(CPP, CPP_TREE), "LICENSE_MISSING_ROOT")
    result = redetect.redetect(handoff, reads=_reads(CPP_TREE, {}))
    assert result.still_fires is True
    assert result.revision_drifted is True
    assert "only in License/" in result.note


def test_the_redetector_sees_a_license_defect_fixed_upstream() -> None:
    handoff = _filed(_observation(CPP, CPP_TREE), "LICENSE_MISSING_ROOT")
    fixed_tree = (*CPP_TREE, "LICENSE")
    result = redetect.redetect(handoff, reads=_reads(fixed_tree, {}))
    assert result.still_fires is False
    assert result.proposed_status is None  # a HANDOFF_PENDING handoff is never auto-resolved


def test_a_filed_handoff_proposes_resolution_once_the_defect_is_gone() -> None:
    from dataclasses import replace

    from repository_presenter.components.issues.model import IssueRef

    handoff = replace(
        _filed(_observation(CPP, CPP_TREE), "LICENSE_MISSING_ROOT"),
        status="FILED",
        issue_ref=IssueRef(
            3, "https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp/issues/3"
        ),
    )
    result = redetect.redetect(handoff, reads=_reads((*CPP_TREE, "LICENSE"), {}))
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert result.proposed_close_reason == "completed"


def test_the_redetector_follows_the_placeholder_through_a_partial_fix() -> None:
    handoff = _filed(
        _observation(PSD_NET, PSD_NET_TREE, {PSD_CSPROJ_PATH: PSD_CSPROJ}),
        "MANIFEST_PLACEHOLDER_METADATA",
    )
    partly = PSD_CSPROJ.replace("<Authors>SID</Authors>", "<Authors>Aspose</Authors>")
    still = redetect.redetect(handoff, reads=_reads(PSD_NET_TREE, {PSD_CSPROJ_PATH: partly}))
    assert still.still_fires is True
    fixed = partly.replace("yourorg", "aspose-psd-foss")
    gone = redetect.redetect(handoff, reads=_reads(PSD_NET_TREE, {PSD_CSPROJ_PATH: fixed}))
    assert gone.still_fires is False


def test_the_redetector_tells_a_placeholder_readme_from_a_fixed_one() -> None:
    handoff = _filed(
        _observation(PSD_PY, PSD_PY_TREE, {"README.md": PSD_PY_README}),
        "README_MISSING_OR_PLACEHOLDER",
    )
    assert (
        redetect.redetect(
            handoff, reads=_reads(PSD_PY_TREE, {"README.md": PSD_PY_README})
        ).still_fires
        is True
    )
    assert (
        redetect.redetect(
            handoff, reads=_reads(PSD_PY_TREE, {"README.md": SUBSTANTIVE_README})
        ).still_fires
        is False
    )


def test_an_unreadable_file_makes_the_redetection_inconclusive_not_clean() -> None:
    handoff = _filed(
        _observation(PSD_PY, PSD_PY_TREE, {"README.md": PSD_PY_README}),
        "README_MISSING_OR_PLACEHOLDER",
    )
    result = redetect.redetect(handoff, reads=_reads(PSD_PY_TREE, {}))
    assert result.still_fires is None
    assert "README.md" in result.note


@pytest.mark.parametrize(
    "kwargs",
    [{"truncated": True}, {"tree_error": "HTTP 502"}],
    ids=["truncated-listing", "tree-error"],
)
def test_a_listing_that_cannot_prove_absence_is_inconclusive(kwargs: dict) -> None:
    handoff = _filed(_observation(GIS, GIS_TREE), "LICENSE_MISSING_ROOT")
    result = redetect.redetect(handoff, reads=_reads(GIS_TREE, {}, **kwargs))
    assert result.still_fires is None


def test_an_unreadable_head_makes_the_redetection_inconclusive() -> None:
    handoff = _filed(_observation(GIS, GIS_TREE), "LICENSE_MISSING_ROOT")
    reads = redetect.RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, error="HTTP 500"
        ),
    )
    assert redetect.redetect(handoff, reads=reads).still_fires is None


def test_a_class_handoff_replays_through_its_own_registered_id_only() -> None:
    handoff = _filed(_observation(GIS, GIS_TREE), "LICENSE_MISSING_ROOT")
    assert redetect.replay_gap(handoff) is None


# --- the clone reader -----------------------------------------------------------------------------


def test_the_clone_observation_reads_sizes_and_manifests_as_the_files_have_them(
    tmp_path: Path,
) -> None:
    clone = tmp_path / "clone"
    (clone / "src" / "Aspose.PSD.FOSS").mkdir(parents=True)
    (clone / "README.md").write_bytes(PSD_PY_README.encode())
    (clone / PSD_CSPROJ_PATH).write_bytes(PSD_CSPROJ.encode())
    tree = ("README.md", PSD_CSPROJ_PATH)
    observation = observation_from_clone(
        PSD_NET, REV, clone, tree, manifest=clone / PSD_CSPROJ_PATH
    )
    assert observation.readme_text is not None
    assert len(observation.readme_text.encode()) == 69
    assert [m.path for m in observation.manifests] == [PSD_CSPROJ_PATH]
    assert _classes_of(observation) == [
        "LICENSE_MISSING_ROOT",
        "README_MISSING_OR_PLACEHOLDER",
        "MANIFEST_PLACEHOLDER_METADATA",
    ]


def test_the_clone_observation_never_reads_outside_the_clone(tmp_path: Path) -> None:
    clone = tmp_path / "clone"
    clone.mkdir()
    (tmp_path / "README.md").write_text("# secret outside the clone\n", encoding="utf-8")
    observation = observation_from_clone(PSD_PY, REV, clone, ("../README.md", "README.md"))
    assert observation.readme_text is None
