"""The official entry point: ``--version``, ``status``, and ``present``."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter import __version__, cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_UNSAFE, EXIT_USAGE, main
from repository_presenter.components.readme.evidence.facts import links
from repository_presenter.components.readme.extractors.platforms import python_registry
from repository_presenter.components.readme.repair.targeted import defect_fingerprint
from repository_presenter.core.errors import GitSafetyError
from repository_presenter.core.git_safety.clone import ReadOnlyClone, pinned_read_only_clone
from repository_presenter.core.git_safety.verify import PushBlockProof
from repository_presenter.core.llm.prompts import load_manifests
from support import (
    REPO_ROOT,
    commit_all,
    init_git_repository,
    mock_gateway,
    write_bundle,
    write_cursor,
)

STATUS = r"\((READY|IN_PROGRESS|VERIFYING|ACCEPTED|BLOCKED_EXTERNAL|FAILED_INTERNAL)\)"
CANARY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REVISION = "f" * 40


def test_version_flag_reports_program_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"repository-presenter {__version__}"


def test_status_reports_this_repository_cursor(
    repo_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["status", "--root", str(repo_root)]) == EXIT_OK
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"repository-presenter {__version__}"
    assert re.fullmatch(rf"gate: G\d_[A-Z_]+ {STATUS}", out[1])
    assert re.fullmatch(rf"work item: G\d-W\d\d {STATUS}", out[2])
    assert re.fullmatch(r"candidates: \d+/34 current reviewable no-op-proven", out[3])
    assert out[4] == "canary: aspose-3d-foss/Aspose.3D-FOSS-for-Python"


def test_status_discovers_root_from_nested_working_directory(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    nested = project / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert main(["status"]) == EXIT_OK
    assert "candidates: 0/34 current reviewable no-op-proven" in capsys.readouterr().out


def test_status_without_cursor_is_a_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == EXIT_USAGE
    assert "no project/state.yaml found at or above" in capsys.readouterr().err
    assert main(["status", "--root", str(tmp_path)]) == EXIT_USAGE
    assert "no project/state.yaml under" in capsys.readouterr().err


def test_status_counts_each_repository_once(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    write_bundle(project, "owner__alpha", "bbb222", "READY_FOR_PROPOSAL")
    write_bundle(project, "owner__beta", "ccc333", "READY_FOR_PROPOSAL")
    write_cursor(project, recorded_candidates=2)
    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "candidates: 2/34" in capsys.readouterr().out


def test_status_ignores_unsealed_and_uncounted_bundles(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", None)
    write_bundle(project, "owner__beta", "bbb222", "ACCEPTED")
    write_bundle(project, "owner__gamma", "ccc333", "SUPERSEDED")
    write_bundle(project, "owner__delta", "ddd444", "INVALIDATED")
    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "candidates: 0/34" in capsys.readouterr().out


def test_status_flags_cursor_that_disagrees_with_disk(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    assert main(["status", "--root", str(project)]) == EXIT_INCONSISTENT
    captured = capsys.readouterr()
    assert "candidates: 1/34" in captured.out
    assert "cursor records 0 current candidates but 1 sealed on disk" in captured.err


def test_status_rejects_corrupt_bundle_manifest(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_bundle(project, "owner__alpha", "aaa111", None, raw="{not json")
    assert main(["status", "--root", str(project)]) == EXIT_INCONSISTENT
    assert "unreadable bundle manifest" in capsys.readouterr().err


def test_status_rejects_malformed_cursor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cursor = write_cursor(tmp_path)
    cursor.write_text("progress: [\n", encoding="utf-8")
    assert main(["status", "--root", str(tmp_path)]) == EXIT_INCONSISTENT
    assert "cursor is not valid YAML" in capsys.readouterr().err


def test_module_entry_point_matches_console_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "repository_presenter", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"repository-presenter {__version__}"


@pytest.fixture
def project_with_registry(project: Path) -> Path:
    (project / "data").mkdir()
    shutil.copy(REPO_ROOT / "data" / "registry.json", project / "data" / "registry.json")
    return project


@pytest.fixture
def fake_clone(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stand in for the network clone; records every call it receives."""
    calls: list[dict[str, Any]] = []

    def fake(clone_url: str, destination: Path, **kwargs: Any) -> ReadOnlyClone:
        calls.append({"clone_url": clone_url, "destination": destination, **kwargs})
        proof = PushBlockProof(True, "DISABLED", clone_url, True, True, None, "ok")
        return ReadOnlyClone(path=destination, clone_url=clone_url, revision=REVISION, proof=proof)

    monkeypatch.setattr(cli, "pinned_read_only_clone", fake)
    return calls


@pytest.fixture
def local_canary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Serve the canary's clone URL from a local repository through the real clone contract."""
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_bytes(
        b"# Aspose.3D for Python\n\nOriginal bytes. See [LICENSE](LICENSE) and "
        b"[docs](https://docs.example.com/3d).\n\n```python\n"
        b"from aspose.threed import Scene\nscene = Scene()\nprint(scene.name)\n"
        b'scene.save("cube.glb")\n```\n\n```python\n'
        b"from aspose.threed import Missing\n```\n"
    )
    (source / "LICENSE").write_text("MIT License\n\nPermission is hereby granted", "utf-8")
    (source / "setup.py").write_text(
        "from setuptools import setup\n"
        'setup(name="aspose-3d-foss", version="26.1.0", packages=["aspose", "aspose.threed"])\n',
        encoding="utf-8",
    )
    (source / "aspose" / "threed").mkdir(parents=True)
    (source / "aspose" / "__init__.py").write_text("", encoding="utf-8")
    (source / "aspose" / "threed" / "__init__.py").write_text(
        "class Scene:\n    name = 'scene'\n\n"
        "    def save(self, path):\n        open(path, 'wb').close()\n",
        encoding="utf-8",
    )
    revision = commit_all(source, "seed")
    calls: list[dict[str, Any]] = []

    def serve_locally(clone_url: str, destination: Path, **kwargs: Any) -> ReadOnlyClone:
        calls.append({"clone_url": clone_url, "destination": destination, **kwargs})
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(cli, "pinned_read_only_clone", serve_locally)
    monkeypatch.setattr(
        python_registry,
        "fetch_project_json",
        lambda url, transport=None: httpx.Response(
            200, json={"info": {"version": "26.1.0"}, "releases": {"26.1.0": []}}
        ),
    )
    monkeypatch.setattr(links, "fetch_status", lambda url: (200, url))
    return {"source": source, "revision": revision, "calls": calls}


LOCAL_INVESTIGATION: dict[str, Any] = {
    "product_summary": {
        "text": "Aspose.3D for Python builds scenes in memory and saves them as GLB files.",
        "fact_ids": ["identity:repository", "package:name", "format:output.glb"],
    },
    "audience": {"text": "Developers using python.", "fact_ids": ["identity:ecosystem"]},
    "problems_solved": [
        {"text": "Writing GLB files from code.", "fact_ids": ["format:output.glb", "example:001"]}
    ],
    "workflows": [
        {
            "name": "Save a scene",
            "text": "Create a Scene and save it.",
            "fact_ids": ["example:001", "public_symbol:aspose.threed.scene"],
        }
    ],
    "capabilities": [
        {
            "title": "Create scenes",
            "text": "Scene objects are created in memory.",
            "fact_ids": ["public_symbol:aspose.threed.scene"],
        },
        {"title": "Save GLB", "text": "Scenes save as GLB.", "fact_ids": ["format:output.glb"]},
        {
            "title": "Import the package",
            "text": "The package imports as aspose.threed.",
            "fact_ids": ["import_path:aspose.threed"],
        },
    ],
    "limitations": [],
    "uncertainties": [],
}


LOCAL_DISPOSITIONS: dict[str, Any] = {
    "dispositions": [
        {
            "unit_id": "inherited_unit:001.heading",
            "disposition": "SUPERSEDE_REDUNDANT",
            "destination_section": None,
            "fact_ids": ["identity:repository"],
            "rationale": "The identity section renders the product name.",
        },
        {
            "unit_id": "inherited_unit:002.paragraph",
            "disposition": "VERIFIED_REWRITE",
            "destination_section": "opening",
            "fact_ids": ["identity:repository"],
            "rationale": "Its substance is the opening.",
        },
        {
            "unit_id": "inherited_unit:003.code_block",
            "disposition": "VERIFIED_PRESERVE",
            "destination_section": "quick_start",
            "fact_ids": ["example:001"],
            "rationale": "The example executed.",
        },
        {
            "unit_id": "inherited_unit:004.code_block",
            "disposition": "OMIT_UNSUPPORTED",
            "destination_section": None,
            "fact_ids": ["example:002"],
            "rationale": "The example failed.",
        },
    ]
}
LOCAL_PLAN_INCLUDED = {
    "identity",
    "badges",
    "opening",
    "navigation",
    "key_capabilities",
    "installation",
    "quick_start",
    "api_reference",
    "documentation_resources",
    "scope_limitations",
    "license",
}
LOCAL_PLAN: dict[str, Any] = {
    "sections": [
        {"section_id": section, "include": section in LOCAL_PLAN_INCLUDED, "reason": "facts"}
        for section in [
            "identity",
            "badges",
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
        {"title": "Create scenes", "fact_ids": ["public_symbol:aspose.threed.scene"]},
        {"title": "Save GLB", "fact_ids": ["format:output.glb"]},
        {"title": "Import the package", "fact_ids": ["import_path:aspose.threed"]},
    ],
    "at_a_glance": None,
    "quick_start_example_id": "example:001",
    "additional_example_ids": [],
    "api_hubs": [
        {
            "symbol_fact_id": "public_symbol:aspose.threed.scene",
            "fact_ids": ["public_symbol:aspose.threed.scene", "example:001"],
        }
    ],
    "material_limitations": [],
    "links": [{"link_fact_id": "link_target:002", "section_id": "documentation_resources"}],
    "deviations": [],
}
SCRIPTED_OUTPUTS: dict[str, dict[str, Any]] = {
    "repository_investigation": LOCAL_INVESTIGATION,
    "source_reconciliation": LOCAL_DISPOSITIONS,
    "presentation_planning": LOCAL_PLAN,
    "independent_review": {"verdict": "ACCEPT", "findings": [], "preserve": []},
}


def _unit(section: str, slot: str, text: str, *fact_ids: str) -> dict[str, Any]:
    return {"section": section, "slot": slot, "text": text, "fact_ids": list(fact_ids)}


LOCAL_UNITS: dict[str, dict[str, Any]] = {
    "opening": {
        "units": [
            _unit(
                "opening",
                "opening",
                "Aspose.3D for Python builds scenes in memory and saves them as GLB files. "
                "Developers using Python use it to write GLB from code.",
                "identity:repository",
                "format:output.glb",
            )
        ],
        "omitted": [],
    },
    "key_capabilities": {
        "units": [
            _unit(
                "key_capabilities",
                "capability:1",
                "Scene objects are created in memory.",
                "public_symbol:aspose.threed.scene",
            ),
            _unit(
                "key_capabilities",
                "capability:2",
                "A scene saves as a GLB file.",
                "format:output.glb",
            ),
            _unit(
                "key_capabilities",
                "capability:3",
                "The package imports as aspose.threed.",
                "import_path:aspose.threed",
            ),
        ],
        "omitted": [],
    },
    "quick_start": {
        "units": [
            _unit(
                "quick_start",
                "lead_in",
                "The example below creates a scene and saves it.",
                "example:001",
            )
        ],
        "omitted": [],
    },
    "api_reference": {
        "units": [
            _unit(
                "api_reference",
                "hub:public_symbol:aspose.threed.scene",
                "Scene holds the scene graph and saves it.",
                "public_symbol:aspose.threed.scene",
            )
        ],
        "omitted": [],
    },
    "documentation_resources": {
        "units": [
            _unit(
                "documentation_resources",
                "resources",
                "The documentation site explains the API.",
                "link_target:002",
            )
        ],
        "omitted": [],
    },
    "scope_limitations": {
        "units": [
            _unit(
                "scope_limitations",
                "scope",
                "The package writes GLB files and nothing else.",
                "identity:repository",
            )
        ],
        "omitted": [],
    },
}


class _ChatGateway:
    """A scripted chat gateway: one canned output per job, every request body recorded."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        # Per-job queues consumed in order before the canned output applies.
        self.queues: dict[str, list[dict[str, Any]]] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        payload = json.loads(request.content)
        self.requests.append(payload)
        job = payload["response_format"]["json_schema"]["name"]
        user = payload["messages"][1]["content"]
        if self.queues.get(job):
            content = json.dumps(self.queues[job].pop(0))
        elif job == "section_authoring":
            section = re.search(r"^Section: (\S+)$", user, re.M).group(1)  # type: ignore[union-attr]
            if section == "all":
                # Coherence returns every unit as it stands, revising nothing.
                existing = user.split("Existing LLM-owned units (coherence mode only):\n", 1)[1]
                existing = existing.rsplit("\n\nReturn the units", 1)[0]
                content = json.dumps({"units": json.loads(existing), "omitted": []})
            else:
                content = json.dumps(LOCAL_UNITS[section])
        else:
            content = json.dumps(SCRIPTED_OUTPUTS[job])
        body = {
            "id": f"chatcmpl-{job}",
            "object": "chat.completion",
            "created": 1,
            "model": "qwen3-next",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 500, "completion_tokens": 120, "total_tokens": 620},
        }
        return httpx.Response(200, json=body)


@pytest.fixture
def gateway_ready(project_with_registry: Path, monkeypatch: pytest.MonkeyPatch) -> _ChatGateway:
    """Credentials, manifests, a recorded catalog, and a scripted gateway for a transaction."""
    monkeypatch.setenv("GPT_OSS_ENDPOINT", "https://gw.example/v1")
    monkeypatch.setenv("GPT_OSS_API_KEY", LIVE_KEY)
    shutil.copytree(REPO_ROOT / "prompts", project_with_registry / "prompts")
    catalog = project_with_registry / "runs" / "preflight" / "catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        json.dumps({"schema_version": 1, "models": [{"id": "qwen3-next", "owned_by": "org"}]}),
        encoding="utf-8",
    )
    gateway = _ChatGateway()
    mock_gateway(monkeypatch, gateway)
    return gateway


@pytest.fixture
def readme_only_upstream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Serve the canary's clone URL from the README-only placeholder fixture."""
    source = init_git_repository(tmp_path / "placeholder", with_commit=False)
    for name in ("README.md", "LICENSE"):
        shutil.copy(REPO_ROOT / "tests" / "fixtures" / "readme_only" / name, source / name)
    commit_all(source, "placeholder")
    monkeypatch.setattr(
        cli,
        "pinned_read_only_clone",
        lambda clone_url, destination, **kwargs: pinned_read_only_clone(str(source), destination),
    )
    return source


def test_present_admits_clones_and_captures_the_source_snapshot(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("GH_TOKEN", "ghp_read_only_token_value")
    revision = local_canary["revision"]
    clone_dir = "runs/clones/aspose-3d-foss__Aspose.3D-FOSS-for-Python"
    source_dir = f"runs/transactions/aspose-3d-foss__Aspose.3D-FOSS-for-Python/{revision}/source"

    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])

    captured = capsys.readouterr()
    assert f"admitted: {CANARY} (mode dry_run, ecosystem python" in captured.out
    assert f"snapshot: {CANARY} at {revision} in {clone_dir} (push disabled, verified)" in (
        captured.out
    )
    source_line = next(line for line in captured.out.splitlines() if line.startswith("source: "))
    assert source_line.startswith(
        f"source: {source_dir} (3 files, 5 tree entries, readme README.md"
    )
    facts_line = next(line for line in captured.out.splitlines() if line.startswith("facts: "))
    facts_dir = source_dir.removesuffix("/source")
    assert facts_line.startswith(f"facts: {facts_dir}/facts.json (")
    assert "identity 5" in facts_line and "license 2" in facts_line and "package 2" in facts_line
    assert "example 2" in facts_line
    assert "examples: 2 candidates; executed 1, failed 1" in captured.out
    facts = json.loads((project_with_registry / facts_dir / "facts.json").read_text("utf-8"))
    assert facts["source_revision"] == revision
    by_id = {fact["id"]: fact for fact in facts["facts"]}
    assert set(by_id) >= {
        "package:name",
        "import_path:aspose.threed",
        "license:spdx",
        "install_command:pip",
        "public_symbol:aspose.threed.scene",
    }
    assert by_id["example:001"]["polarity"] == "SUPPORTED"
    assert by_id["example:002"]["polarity"] == "CONTRADICTED"
    assert (by_id["format:output.glb"]["value"], by_id["format:output.glb"]["polarity"]) == (
        ".glb",
        "SUPPORTED",
    )
    assert by_id["install_command:pip"]["polarity"] == "SUPPORTED"
    assert {f["value"]: f["polarity"] for f in facts["facts"] if f["kind"] == "link_target"} == {
        "LICENSE": "SUPPORTED",
        "https://docs.example.com/3d": "SUPPORTED",
    }
    assert by_id["install_command:pip"]["evidence"][1]["path"] == (
        "https://pypi.org/pypi/aspose-3d-foss/json"
    )
    receipts = json.loads((project_with_registry / facts_dir / "examples.json").read_text("utf-8"))
    assert [r["outcome"] for r in receipts] == ["EXECUTED", "FAILED"]
    assert receipts[0]["stdout"].strip() == "scene"
    investigation_line = next(
        line for line in captured.out.splitlines() if line.startswith("investigation: ")
    )
    assert investigation_line.startswith(
        f"investigation: {facts_dir}/investigation.json (capabilities 3, workflows 1, "
        "limitations 0; provider calls 1, model qwen3-next; digest "
    )
    written_investigation = json.loads(
        (project_with_registry / facts_dir / "investigation.json").read_text("utf-8")
    )
    assert written_investigation == LOCAL_INVESTIGATION
    assert len(gateway_ready.requests) == 11
    request = gateway_ready.requests[0]
    assert request["model"] == "qwen3-next"
    assert request["response_format"]["type"] == "json_schema"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert '"id": "example:001"' in request["messages"][1]["content"]
    dispositions_line = next(
        line for line in captured.out.splitlines() if line.startswith("dispositions: ")
    )
    assert dispositions_line.startswith(
        f"dispositions: {facts_dir}/dispositions.json (4 units: OMIT_UNSUPPORTED 1, "
        "SUPERSEDE_REDUNDANT 1, VERIFIED_PRESERVE 1, VERIFIED_REWRITE 1; provider calls 1, "
        "model qwen3-next; digest "
    )
    written_dispositions = json.loads(
        (project_with_registry / facts_dir / "dispositions.json").read_text("utf-8")
    )
    assert written_dispositions == LOCAL_DISPOSITIONS
    plan_line = next(line for line in captured.out.splitlines() if line.startswith("plan: "))
    assert plan_line.startswith(
        f"plan: {facts_dir}/plan.json (sections 11/17, capabilities 3, hubs 1, examples 1+0, "
        "links 1, limitations 0; provider calls 1, model qwen3-next; digest "
    )
    written_plan = json.loads((project_with_registry / facts_dir / "plan.json").read_text("utf-8"))
    assert written_plan == LOCAL_PLAN
    assert [r["response_format"]["json_schema"]["name"] for r in gateway_ready.requests] == [
        "repository_investigation",
        "source_reconciliation",
        "presentation_planning",
        *(["section_authoring"] * 7),
        "independent_review",
    ]
    shell_packet = json.loads(
        gateway_ready.requests[2]["messages"][1]["content"]
        .split("Semantic shell:\n", 1)[1]
        .split("\n\nPolicy ceilings", 1)[0]
    )
    assert {s["id"]: s["condition_holds"] for s in shell_packet}["at_a_glance"] is False
    assert (
        '"id": "inherited_unit:004.code_block"'
        in gateway_ready.requests[1]["messages"][1]["content"]
    )
    ledger = (project_with_registry / facts_dir / "calls.jsonl").read_text("utf-8").splitlines()
    assert len(ledger) == 11 and all('"disposition":"provider_call"' in line for line in ledger)
    assert "coherence: 0 of 8 units revised; provider calls 1, model qwen3-next" in captured.out
    assert LIVE_KEY not in "".join(ledger)
    units_line = next(line for line in captured.out.splitlines() if line.startswith("units: "))
    assert units_line.startswith(
        f"units: {facts_dir}/content_units.json (8 units across 6 sections: opening, "
        "key_capabilities, quick_start, api_reference, documentation_resources, "
        "scope_limitations; provider calls 6; digest "
    )
    written_units = json.loads(
        (project_with_registry / facts_dir / "content_units.json").read_text("utf-8")
    )
    assert written_units["coherence"] == {"applied": True, "revised": []}
    assert [unit["slot"] for unit in written_units["units"]] == [
        "opening",
        "capability:1",
        "capability:2",
        "capability:3",
        "lead_in",
        "hub:public_symbol:aspose.threed.scene",
        "resources",
        "scope",
    ]
    authoring_requests = [
        r
        for r in gateway_ready.requests
        if r["response_format"]["json_schema"]["name"] == "section_authoring"
    ]
    assert len(authoring_requests) == 7
    assert "Mode: coherence" in authoring_requests[6]["messages"][1]["content"]
    assert "# Aspose.3D FOSS for Python" in authoring_requests[6]["messages"][1]["content"]
    assert (
        "Product name (preserve exactly): Aspose.3D FOSS for Python"
        in (authoring_requests[0]["messages"][1]["content"])
    )
    readme_text = (project_with_registry / facts_dir / "README.md").read_text("utf-8")
    assert readme_text.startswith("# Aspose.3D FOSS for Python\n\n[![PyPI]")
    assert "## Installation\n\n```bash\npip install aspose-3d-foss\n```" in readme_text
    assert (
        "## Quick Start\n\nThe example below creates a scene and saves it.\n\n```python\n"
        in readme_text
    )
    assert "- **Create scenes.** `Scene` objects are created in memory." in readme_text
    assert "- [docs](https://docs.example.com/3d)" in readme_text
    assert readme_text.rstrip("\n").endswith("See [LICENSE](LICENSE).")
    patch_text = (project_with_registry / facts_dir / "README.patch").read_text("utf-8")
    assert patch_text.startswith("--- a/README.md\n+++ b/README.md\n")
    assert "-# Aspose.3D for Python" in patch_text
    readme_line = next(line for line in captured.out.splitlines() if line.startswith("readme: "))
    assert re.fullmatch(
        rf"readme: {re.escape(facts_dir)}/README\.md "
        r"\(\d+ visible lines of \d+; digest [0-9a-f]{64}\)",
        readme_line,
    )
    validation_line = next(
        line for line in captured.out.splitlines() if line.startswith("validation: ")
    )
    assert validation_line.startswith(
        f"validation: {facts_dir}/validation.json (pass 10, fail 0, pending 1; digest "
    )
    written_validation = json.loads(
        (project_with_registry / facts_dir / "validation.json").read_text("utf-8")
    )
    assert [c["verdict"] for c in written_validation["checks"]] == ["PASS"] * 10 + ["PENDING"]
    assert written_validation["advisory"] == []
    review_line = next(line for line in captured.out.splitlines() if line.startswith("review: "))
    assert review_line.startswith(
        f"review: {facts_dir}/review.json (verdict ACCEPT, findings 0, advisory 0, preserve 0; "
        "provider calls 1, model qwen3-next; digest "
    )
    written_review = json.loads(
        (project_with_registry / facts_dir / "review.json").read_text("utf-8")
    )
    assert written_review["identity_separate"] is True
    assert written_review["reviewer"]["job"] == "independent_review"
    review_request = gateway_ready.requests[10]
    assert review_request["response_format"]["json_schema"]["name"] == "independent_review"
    assert "# Aspose.3D FOSS for Python" in review_request["messages"][1]["content"]
    assert "Original bytes." in review_request["messages"][1]["content"]
    assert code == EXIT_OK and captured.err == ""
    bundle_dir = f"candidates/aspose-3d-foss__Aspose.3D-FOSS-for-Python/{revision}"
    assert (
        f"bundle: {bundle_dir} (state ACCEPTED, 11 files, provider calls 11; sealed; "
        "the no-op proof needs a rerun in a fresh process)"
    ) in captured.out
    bundle = project_with_registry / bundle_dir
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "ACCEPTED" and manifest["no_op_proof"] is None
    assert manifest["revision"] == revision and manifest["provider_calls"] == 11
    assert sorted(manifest["files"]) == sorted(
        [
            "README.md",
            "README.patch",
            "calls.jsonl",
            "content_units.json",
            "dependencies.json",
            "dispositions.json",
            "facts.json",
            "investigation.json",
            "plan.json",
            "review.json",
            "validation.json",
        ]
    )  # repairs.json exists only once a repair loop ran
    for name, digest in manifest["files"].items():
        data = (bundle / name).read_bytes()
        assert digest == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    assert (bundle / "README.md").read_bytes() == readme_text.encode("utf-8")
    assert (bundle.parent / "CURRENT").read_text("utf-8") == f"{revision}\n"
    dependencies = json.loads((bundle / "dependencies.json").read_text("utf-8"))
    assert dependencies["source"]["revision"] == revision
    assert set(dependencies["prompts"]) == {
        "repository_investigation",
        "source_reconciliation",
        "presentation_planning",
        "section_authoring",
        "independent_review",
        "targeted_repair",
    }
    assert dependencies["validators"]["BC-11"] == "1" and dependencies["components"] == {
        "shell": "1",
        "renderer": "1",
    }
    assert "install_command:pip" in dependencies["facts"]
    assert local_canary["calls"] == [
        {
            "clone_url": f"https://github.com/{CANARY}.git",
            "destination": project_with_registry / Path(clone_dir),
            "token": "ghp_read_only_token_value",
        }
    ]
    assert "ghp_read_only_token_value" not in captured.out + captured.err
    written = project_with_registry / source_dir
    readme_bytes = (written / "README.md").read_bytes()
    assert readme_bytes.startswith(b"# Aspose.3D for Python\n\nOriginal bytes. See [LICENSE]")
    assert readme_bytes == (local_canary["source"] / "README.md").read_bytes()
    assert (written / "tree.txt").read_text(encoding="utf-8").count("\n") == 5
    assert json.loads((written / "snapshot.json").read_text("utf-8"))["source_revision"] == revision


def test_present_rerun_on_the_same_revision_is_byte_identical_with_zero_calls(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    prefixes = (
        "source: ",
        "facts: ",
        "investigation: ",
        "dispositions: ",
        "plan: ",
        "units: ",
        "readme: ",
        "patch: ",
        "validation: ",
        "review: ",
    )

    def digests(text: str) -> list[str]:
        lines = [line for line in text.splitlines() if line.startswith(prefixes)]
        assert len(lines) == 10
        return [line.rsplit("digest ", 1)[1] for line in lines]

    main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    first = capsys.readouterr().out
    main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    second = capsys.readouterr().out
    assert digests(first) == digests(second)
    assert "evaluation: " in first and "no sealed bundle" in first and "NONE; 0 changes" in second
    assert first.count("provider calls 1, model qwen3-next") == 5
    assert second.count("provider calls 0, model stored output reused") == 5
    assert len(gateway_ready.requests) == 11
    assert "provider calls 6; digest" in first and "provider calls 0; digest" in second
    assert "coherence: 0 of 8 units revised; provider calls 0, model stored output reused" in second
    transaction = next((project_with_registry / "runs" / "transactions").glob("*/*"))
    ledger = (transaction / "calls.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(line)["disposition"] for line in ledger] == ["provider_call"] * 11 + [
        "cache_reuse"
    ] * 11


OPENING_QUOTE = "Developers using Python use it to write GLB from code."
_PROMPTS = load_manifests(REPO_ROOT / "prompts")
OPENING_FINGERPRINT = defect_fingerprint(
    "review",
    "opening",
    "S6",
    "factuality",
    f"{_PROMPTS['independent_review'].sha256}|{_PROMPTS['targeted_repair'].sha256}",
)
REVISED_OPENING = (
    "Aspose.3D for Python builds scenes in memory and saves them as GLB files. "
    "Python developers use it to write GLB files from code."
)


def _rejection(label: str, quote: str = OPENING_QUOTE) -> dict[str, Any]:
    return {
        "verdict": "REJECT_PRESENTATION",
        "findings": [
            {
                "id": label,
                "section_id": "opening",
                "causal_stage": "S6",
                "criterion": "factuality",
                "text": "The audience sentence is generic.",
                "quote": quote,
                "fact_ids": ["identity:repository"],
                "repair": "Name the developers concretely.",
            }
        ],
        "preserve": ["the quick start"],
    }


def _opening_repair() -> dict[str, Any]:
    return {
        "fingerprint": OPENING_FINGERPRINT,
        "causal_stage": "S6",
        "revised_output": {
            "units": [
                _unit(
                    "opening",
                    "opening",
                    REVISED_OPENING,
                    "identity:repository",
                    "format:output.glb",
                )
            ],
            "omitted": [],
        },
        "changes": [
            {
                "id": "R01",
                "path": "$.units[0].text",
                "before": OPENING_QUOTE,
                "after": "Python developers use it to write GLB files from code.",
                "fact_ids": ["identity:repository"],
            }
        ],
    }


def test_present_repairs_a_rejected_candidate_once_and_re_reviews(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sibling = _rejection("F02", "builds scenes in memory")["findings"][0]
    first_review = _rejection("F01")
    first_review["findings"].append(sibling)
    gateway_ready.queues = {
        "independent_review": [
            first_review,
            {"verdict": "ACCEPT", "findings": [], "preserve": []},
        ],
        "targeted_repair": [_opening_repair()],
    }
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    assert code == EXIT_OK and "state ACCEPTED" in captured.out
    assert (
        "repair: 1 repaired (F01+F02 S6 opening), 0 unrepairable recorded advisory; rounds 2"
    ) in captured.out
    names = [r["response_format"]["json_schema"]["name"] for r in gateway_ready.requests]
    assert names[11:] == ["targeted_repair", "section_authoring", "independent_review"]
    repair_request = gateway_ready.requests[11]["messages"][1]["content"]
    assert "Causal stage: S6" in repair_request and OPENING_QUOTE in repair_request
    assert '"equivalent_findings"' in repair_request and '"F02"' in repair_request
    assert '"the quick start"' in repair_request
    transaction = next((project_with_registry / "runs" / "transactions").glob("*/*"))
    readme = (transaction / "README.md").read_text("utf-8")
    assert "Python developers use it to write GLB files from code." in readme
    assert OPENING_QUOTE not in readme
    review = json.loads((transaction / "review.json").read_text("utf-8"))
    assert review["verdict"] == "ACCEPT"
    validation = json.loads((transaction / "validation.json").read_text("utf-8"))
    assert validation["summary"] == {"pass": 10, "fail": 0, "pending": 1}
    repairs = json.loads((transaction / "repairs.json").read_text("utf-8"))
    attempt = repairs["attempts"][OPENING_FINGERPRINT]
    assert attempt["outcome"] == "repaired" and attempt["changes"][0]["id"] == "R01"
    assert "provider calls 1, model qwen3-next; digest" in next(
        line for line in captured.out.splitlines() if line.startswith("review: ")
    )

    def digests(text: str) -> list[str]:
        # The evaluation records this run's basis (no bundle, then the sealed one) by design.
        return [
            line.rsplit("digest ", 1)[1]
            for line in text.splitlines()
            if "digest " in line and not line.startswith("evaluation: ")
        ]

    first_digests = digests(captured.out)

    again = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    rerun = capsys.readouterr().out
    assert again == EXIT_OK
    assert digests(rerun) == first_digests and len(first_digests) == 10
    # The rerun is the fresh-process no-op proof: the bundle moves to READY_FOR_PROPOSAL.
    assert "state READY_FOR_PROPOSAL" in rerun and "check 11 judged" in rerun
    assert "(no sealed bundle for this revision; every stage runs; digest " in captured.out
    assert "(earliest affected stage NONE; 0 changes; digest " in rerun
    evaluation = json.loads((transaction / "evaluation.json").read_text("utf-8"))
    assert evaluation["earliest_affected_stage"] == "NONE" and evaluation["changes"] == []
    assert evaluation["sealed_bundle"] == transaction.name
    bundle = next((project_with_registry / "candidates").glob("*/*/manifest.json")).parent
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    assert manifest["no_op_proof"]["provider_calls"] == 0 and manifest["provider_calls"] == 0
    bundle_validation = json.loads((bundle / "validation.json").read_text("utf-8"))
    assert bundle_validation["summary"] == {"pass": 11, "fail": 0, "pending": 0}
    assert (bundle / "README.md").read_bytes() == (transaction / "README.md").read_bytes()
    assert "provider calls 1" not in rerun and len(gateway_ready.requests) == 14
    # repairs.json is the transaction's history: the rerun reports it and attempts nothing.
    assert (
        "repair: 1 repaired (F01+F02 S6 opening), 0 unrepairable recorded advisory; rounds 1"
    ) in rerun
    ledger = (transaction / "calls.jsonl").read_text("utf-8").splitlines()
    # Round one and the repair call the provider; round two reuses every unchanged stage and
    # calls only coherence and the review; the rerun reuses everything.
    dispositions = [json.loads(line)["disposition"] for line in ledger]
    assert dispositions[:12] == ["provider_call"] * 12
    assert dispositions[12:21] == ["cache_reuse"] * 9
    assert dispositions[21:23] == ["provider_call"] * 2
    assert dispositions[23:] == ["cache_reuse"] * 11


def test_present_reports_a_second_equivalent_failure_instead_of_retrying(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gateway_ready.queues = {
        "independent_review": [
            _rejection("F01"),
            _rejection("F02", "Python developers use it to write GLB files from code."),
        ],
        "targeted_repair": [_opening_repair()],
    }
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    # The re-raised finding had its one attempt: it is recorded advisory and never blocks
    # again, so the candidate proceeds on the blocking findings that remain, which is none.
    assert code == EXIT_OK and "state ACCEPTED" in captured.out
    assert (
        "repair: 1 repaired (F01 S6 opening), 0 unrepairable recorded advisory, "
        "1 re-raised after repair recorded advisory; rounds 2"
    ) in captured.out
    assert len(gateway_ready.requests) == 14
    transaction = next((project_with_registry / "runs" / "transactions").glob("*/*"))
    review = json.loads((transaction / "review.json").read_text("utf-8"))
    assert review["verdict"] == "ACCEPT" and review["verdict_as_returned"] == "REJECT_PRESENTATION"
    assert [f["id"] for f in review["advisory"]] == ["F02"]
    assert review["advisory"][0]["text"].startswith(
        "[reviewer-scope defect at S6: re-raised after the one repair attempt"
    )
    validation = json.loads((transaction / "validation.json").read_text("utf-8"))
    assert validation["summary"] == {"pass": 10, "fail": 0, "pending": 1}
    repairs = json.loads((transaction / "repairs.json").read_text("utf-8"))
    assert repairs["attempts"][OPENING_FINGERPRINT]["re_raised"] == ["F02"]
    # The rerun reaches the same outcome from the stored outputs with no call.
    again = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    rerun = capsys.readouterr()
    assert again == EXIT_OK and "state READY_FOR_PROPOSAL" in rerun.out
    assert len(gateway_ready.requests) == 14
    assert json.loads((transaction / "review.json").read_text("utf-8")) == review


def test_present_records_an_unrepairable_finding_as_advisory_and_stops(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evidence_finding = {
        **_rejection("F01")["findings"][0],
        "section_id": "installation",
        "causal_stage": "S2",
        "criterion": "completeness",
        "quote": "pip install aspose-3d-foss",
        "fact_ids": [],
    }
    gateway_ready.queues = {
        "independent_review": [
            {"verdict": "REJECT_FACTUAL", "findings": [evidence_finding], "preserve": []}
        ]
    }
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    assert code == EXIT_INCONSISTENT
    assert "BC-10 failed at EXTRACTING: REJECT_FACTUAL; no repair could act on it" in captured.err
    assert "repair: 0 repaired, 1 unrepairable recorded advisory; rounds 1" in captured.out
    assert len(gateway_ready.requests) == 11
    transaction = next((project_with_registry / "runs" / "transactions").glob("*/*"))
    repairs = json.loads((transaction / "repairs.json").read_text("utf-8"))
    (attempt,) = repairs["attempts"].values()
    assert attempt["outcome"] == "unrepairable" and attempt["reason"].startswith("evidence defect")


def _seal_and_prove(project: Path, capsys: pytest.CaptureFixture[str]) -> Path:
    assert main(["present", "--repo", CANARY, "--root", str(project)]) == EXIT_OK
    assert main(["present", "--repo", CANARY, "--root", str(project)]) == EXIT_OK
    capsys.readouterr()
    bundle = next((project / "candidates").glob("*/*/manifest.json")).parent
    assert json.loads((bundle / "manifest.json").read_text("utf-8"))["state"] == (
        "READY_FOR_PROPOSAL"
    )
    return bundle


def test_a_changed_prompt_reopens_only_its_stage_and_records_an_update(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle = _seal_and_prove(project_with_registry, capsys)
    before = {name: (bundle / name).read_bytes() for name in ("README.md", "plan.json")}
    manifest_path = project_with_registry / "prompts" / "section_authoring.yaml"
    manifest_path.write_text(
        manifest_path.read_text("utf-8") + "\n# revised wording\n", encoding="utf-8", newline="\n"
    )
    requests_before = len(gateway_ready.requests)

    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert (
        "(earliest affected stage COMPOSING; 1 changes (prompts.section_authoring -> COMPOSING)"
    ) in out
    # Only authoring and coherence asked again; every upstream stage and the review reused.
    assert len(gateway_ready.requests) - requests_before == 7
    assert "provider calls 0, model stored output reused; digest" in next(
        line for line in out.splitlines() if line.startswith("plan: ")
    )
    assert "provider calls 6; digest" in next(
        line for line in out.splitlines() if line.startswith("units: ")
    )
    assert "review: " in out and "provider calls 0, model stored output reused" in next(
        line for line in out.splitlines() if line.startswith("review: ")
    )
    transaction = next((project_with_registry / "runs" / "transactions").glob("*/*"))
    for name in ("investigation.json", "dispositions.json", "plan.json"):
        assert (transaction / name).read_bytes() == (bundle / name).read_bytes()
    # review.json names the authoring prompt's hash, so it changes with the prompt too.
    bundle_line = next(line for line in out.splitlines() if line.startswith("bundle: "))
    assert "(state READY_FOR_PROPOSAL, 11 files, provider calls 7; " in bundle_line
    assert (
        "valid update available (presentation): dependencies.json, review.json changed at "
        "COMPOSING; the proven candidate stays valid and the update waits in the transaction)"
    ) in bundle_line
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL" and manifest["update"]["available"]
    assert manifest["update"]["changed"] == ["dependencies.json", "review.json"]
    assert {name: (bundle / name).read_bytes() for name in before} == before


def test_a_factual_failure_invalidates_the_proven_candidate(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from repository_presenter.components.readme.repair import rounds

    bundle = _seal_and_prove(project_with_registry, capsys)
    genuine = rounds.validate_candidate

    def contradicted(*args: Any, **kwargs: Any) -> dict[str, Any]:
        document = genuine(*args, **kwargs)
        for check in document["checks"]:
            if check["id"] == "BC-02":
                check["verdict"] = "FAIL"
                check["causal_stage"] = "EXTRACTING"
                check["details"] = ["install_command:pip is CONTRADICTED: registry: not found"]
        document["summary"] = {"pass": 9, "fail": 1, "pending": 1}
        return document

    monkeypatch.setattr(rounds, "validate_candidate", contradicted)
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    assert code == EXIT_INCONSISTENT
    assert "BC-02 failed at EXTRACTING" in captured.err
    assert "(state INVALIDATED; BC-02 failed at EXTRACTING)" in captured.out
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "INVALIDATED" and manifest["invalidated"]["check"] == "BC-02"
    assert main(["status", "--root", str(project_with_registry)]) == EXIT_OK
    assert "candidates: 0/34" in capsys.readouterr().out


def test_a_corrupt_bundle_artifact_fails_closed_before_any_call(
    project_with_registry: Path,
    local_canary: dict[str, Any],
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bundle = _seal_and_prove(project_with_registry, capsys)
    (bundle / "README.md").unlink()
    requests_before = len(gateway_ready.requests)
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])
    captured = capsys.readouterr()
    assert code == EXIT_INCONSISTENT
    assert "bundle artifact README.md is missing from" in captured.err
    assert len(gateway_ready.requests) == requests_before


def test_present_reports_a_readme_only_placeholder_as_insufficient_evidence(
    project_with_registry: Path,
    readme_only_upstream: Path,
    gateway_ready: _ChatGateway,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["present", "--repo", CANARY, "--root", str(project_with_registry)])

    captured = capsys.readouterr()
    assert gateway_ready.requests == []
    assert code == EXIT_INCONSISTENT
    assert "insufficient_evidence: NO_IMPLEMENTATION_EVIDENCE for " + CANARY in captured.out
    assert "resume when a later default-branch revision adds a python manifest" in captured.out
    transaction = next(
        (project_with_registry / "runs" / "transactions").glob("aspose-3d-foss__*/*")
    )
    assert (transaction / "disposition.json").is_file()
    assert not (transaction / "facts.json").exists()
    document = json.loads((transaction / "disposition.json").read_text("utf-8"))
    assert document["evidence_paths_inspected"] == ["LICENSE", "README.md"]
    assert "not implemented" not in captured.err


def test_present_refuses_a_repository_outside_the_allow_list_before_cloning(
    project_with_registry: Path,
    fake_clone: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        ["present", "--repo", "some-org/Aspose.X-FOSS-for-Go", "--root", str(project_with_registry)]
    )
    captured = capsys.readouterr()
    assert code == EXIT_UNSAFE
    assert captured.out == ""
    assert "some-org/Aspose.X-FOSS-for-Go is not in the registry allow-list" in captured.err
    assert fake_clone == []


def test_present_reports_a_clone_that_cannot_be_proven_safe(
    project_with_registry: Path,
    gateway_ready: _ChatGateway,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> ReadOnlyClone:
        raise GitSafetyError("push is not proven blocked in the clone")

    monkeypatch.setattr(cli, "pinned_read_only_clone", refuse)
    assert main(["present", "--repo", CANARY, "--root", str(project_with_registry)]) == EXIT_UNSAFE
    assert "push is not proven blocked" in capsys.readouterr().err


def test_present_fails_closed_without_a_registry(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["present", "--repo", CANARY, "--root", str(project)]) == EXIT_USAGE
    assert "registry not found" in capsys.readouterr().err


def test_present_fails_closed_on_a_malformed_registry(
    project_with_registry: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    registry = project_with_registry / "data" / "registry.json"
    document = json.loads(registry.read_text("utf-8"))
    document["entries"][0]["mode"] = "publish"
    registry.write_text(json.dumps(document), encoding="utf-8")
    assert main(["present", "--repo", CANARY, "--root", str(project_with_registry)]) == EXIT_USAGE
    assert "registry is malformed" in capsys.readouterr().err


def test_present_discovers_the_root_like_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["present", "--repo", CANARY]) == EXIT_USAGE
    assert "no project/state.yaml found at or above" in capsys.readouterr().err
    write_cursor(tmp_path)
    assert main(["present", "--repo", CANARY]) == EXIT_USAGE
    assert "registry not found" in capsys.readouterr().err


LIVE_KEY = "sk-live-key-0123456789abcdef"


def _gateway(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    """Configure the gateway variables and serve the gateway from a mock transport."""
    monkeypatch.setenv("GPT_OSS_ENDPOINT", "https://gw.example/v1/")
    monkeypatch.setenv("GPT_OSS_API_KEY", LIVE_KEY)
    mock_gateway(monkeypatch, handler)


def test_preflight_without_the_gateway_variables_names_the_owner_item(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["preflight", "--root", str(project)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert (
        "OWNER-02: GPT_OSS_ENDPOINT and GPT_OSS_API_KEY not set in the process environment" in err
    )
    assert "resume when GPT_OSS_ENDPOINT and GPT_OSS_API_KEY are present" in err
    assert not (project / "runs" / "preflight").exists()


def test_preflight_records_the_catalog_and_never_prints_the_key(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {LIVE_KEY}"
        data = [
            {"id": "qwen3-next", "object": "model", "owned_by": "org"},
            {"id": "gpt-oss", "object": "model", "owned_by": "org"},
        ]
        return httpx.Response(200, json={"object": "list", "data": data})

    _gateway(monkeypatch, handler)
    shutil.copytree(REPO_ROOT / "prompts", project / "prompts")
    assert main(["preflight", "--root", str(project)]) == EXIT_OK
    captured = capsys.readouterr()
    out = captured.out.splitlines()
    assert out[0] == "gateway: gw.example reachable (GPT_OSS_API_KEY read, never printed)"
    assert out[1] == "models: gpt-oss, qwen3-next (2)"
    assert out[2] == "prompts: 6 manifests routed to qwen3-next; content hashes recorded"
    assert re.fullmatch(r"catalog: runs/preflight/catalog\.json \(digest [0-9a-f]{64}\)", out[3])
    assert LIVE_KEY not in captured.out + captured.err
    raw = (project / "runs" / "preflight" / "catalog.json").read_text("utf-8")
    catalog = json.loads(raw)
    assert [m["id"] for m in catalog["models"]] == ["gpt-oss", "qwen3-next"]
    assert [p["prompt_id"] for p in catalog["prompts"]] == [
        "independent_review",
        "presentation_planning",
        "repository_investigation",
        "section_authoring",
        "source_reconciliation",
        "targeted_repair",
    ]
    assert LIVE_KEY not in raw


def test_preflight_without_manifests_is_a_configuration_failure(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _gateway(monkeypatch, lambda request: httpx.Response(200, json={"object": "list", "data": []}))
    assert main(["preflight", "--root", str(project)]) == EXIT_USAGE
    assert "prompt manifests not found: no prompts/ directory" in capsys.readouterr().err


def test_preflight_refusal_is_reported_by_status_with_nothing_else(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _gateway(
        monkeypatch,
        lambda request: httpx.Response(401, json={"error": {"message": f"bad key {LIVE_KEY}"}}),
    )
    shutil.copytree(REPO_ROOT / "prompts", project / "prompts")
    assert main(["preflight", "--root", str(project)]) == EXIT_INCONSISTENT
    captured = capsys.readouterr()
    assert (
        captured.err == "repository-presenter: GET https://gw.example/v1/models answered HTTP 401\n"
    )
    assert LIVE_KEY not in captured.out + captured.err
    assert not (project / "runs" / "preflight").exists()
