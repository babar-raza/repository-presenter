"""``correct-readme`` and ``propose --correction-bundle`` through the real CLI, against a local git
repository standing in for the target (no network, no gateway, no write to any remote)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.bundle import CORRECTIONS_NAME
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.facts import FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.registry.loader import load_registry, require_listed
from support import (
    commit_all,
    init_git_repository,
    monitor_registry_entry,
    write_registry_file,
)

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
README = (
    "# Aspose.3D FOSS for Java\n\n## Installation\n\n```bash\n"
    "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0\n```\n\n"
    "```xml\n<artifactId>aspose-3d-foss</artifactId>\n```\n\n"
    "```groovy\nimplementation 'org.aspose:aspose-3d-foss'\n```\n\n"
    "## Dependencies\n\nNone.\n\n## Development and Testing\n\nRun it.\n\n## License\n\nMIT.\n"
)


@pytest.fixture
def target(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text(README, encoding="utf-8", newline="\n")
    (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = commit_all(source, "seed")
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode="dry_run")])
    served: list[str] = []

    def serve(clone_url: str, destination: Path, **kwargs: Any) -> Any:
        served.append(clone_url)
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(correction_run, "pinned_read_only_clone", serve)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return {"root": project, "revision": revision, "served": served, "tmp": tmp_path}


def facts_file(directory: Path, revision: str, make_facts: Any) -> Path:
    path = directory / "facts.json"
    write_facts(FactsDocument(REPOSITORY, revision, tuple(make_facts())), path)
    return path


def run_correct(target: dict[str, Any], facts: Path, out: Path) -> int:
    return main(
        [
            "correct-readme",
            "--repo",
            REPOSITORY,
            "--root",
            str(target["root"]),
            "--facts",
            str(facts),
            "--out",
            str(out),
        ]
    )


def test_correct_readme_writes_the_bundle_for_the_live_head(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts = facts_file(target["tmp"], target["revision"], make_facts)
    out = target["tmp"] / "bundle"
    assert run_correct(target, facts, out) == EXIT_OK
    said = capsys.readouterr().out
    assert "1 edit(s) (FALSE_CLAIM_FIX 1)" in said and target["revision"][:12] in said
    document = json.loads((out / CORRECTIONS_NAME).read_text(encoding="utf-8"))
    assert [e["replacement"] for e in document["edits"]] == ["26.7.0"]
    assert (out / "README.md").read_text(encoding="utf-8") == README.replace("26.5.0", "26.7.0")
    assert target["served"]  # the registry admitted the repository before any clone


def test_correct_readme_refuses_facts_for_another_revision_and_writes_nothing_useful(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts = facts_file(target["tmp"], "b" * 40, make_facts)
    out = target["tmp"] / "bundle"
    assert run_correct(target, facts, out) != EXIT_OK
    assert "facts are for" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_correct_readme_refuses_an_unlisted_repository_before_any_network_work(
    target: dict[str, Any], make_facts: Any
) -> None:
    facts = facts_file(target["tmp"], target["revision"], make_facts)
    code = main(
        [
            "correct-readme",
            "--repo",
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            "--root",
            str(target["root"]),
            "--facts",
            str(facts),
            "--out",
            str(target["tmp"] / "bundle"),
        ]
    )
    assert code != EXIT_OK and target["served"] == []


def test_correct_readme_never_merges_into_an_existing_bundle(
    target: dict[str, Any], make_facts: Any
) -> None:
    facts = facts_file(target["tmp"], target["revision"], make_facts)
    out = target["tmp"] / "bundle"
    out.mkdir()
    (out / "keep.txt").write_text("x", encoding="utf-8")
    assert run_correct(target, facts, out) == EXIT_USAGE
    assert sorted(p.name for p in out.iterdir()) == ["keep.txt"]


def test_propose_accepts_a_correction_bundle_in_dry_run_and_refuses_a_tampered_one(
    target: dict[str, Any],
    make_facts: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    facts = facts_file(target["tmp"], target["revision"], make_facts)
    out = target["tmp"] / "bundle"
    assert run_correct(target, facts, out) == EXIT_OK
    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repo, *, token=None: DefaultBranchRead(repo, sha=target["revision"], branch="main"),
    )
    args = [
        "propose",
        "--repo",
        REPOSITORY,
        "--root",
        str(target["root"]),
        "--correction-bundle",
        str(out),
    ]
    capsys.readouterr()
    assert main(args) == EXIT_OK
    said = capsys.readouterr().out
    assert "typed correction gate" in said and "bundle revision equals" in said
    assert "dry run" in said

    # Edit the corrected README by hand and re-seal nothing: the digest refuses it first.
    (out / "README.md").write_text(README + "\nunreviewed addition\n", encoding="utf-8")
    assert main(args) != EXIT_OK
    assert "bundle_inconsistent" in capsys.readouterr().err


def serve_other(monkeypatch: pytest.MonkeyPatch, source: Path) -> None:
    monkeypatch.setattr(
        correction_run,
        "pinned_read_only_clone",
        lambda clone_url, destination, **kwargs: pinned_read_only_clone(str(source), destination),
    )


def test_a_repository_with_no_readme_is_a_status_not_a_bundle_and_not_proposable(
    target: dict[str, Any],
    make_facts: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bare = init_git_repository(target["tmp"] / "bare", with_commit=False)
    (bare / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = commit_all(bare, "license only")
    serve_other(monkeypatch, bare)
    facts = facts_file(target["tmp"], revision, make_facts)
    out = target["tmp"] / "bundle"
    assert run_correct(target, facts, out) == EXIT_OK
    assert "no_live_readme" in capsys.readouterr().out
    assert [p.name for p in out.iterdir()] == ["status.json"]
    status = json.loads((out / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "no_live_readme" and status["revision"] == revision
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_correction(out, REPOSITORY, root=target["root"])
    assert raised.value.code == Refusal.BUNDLE_MISSING


def test_a_placeholder_the_facts_only_run_cannot_process_is_insufficient_evidence(
    target: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    entry = require_listed(load_registry(target["root"] / "data" / "registry.json"), REPOSITORY)
    out = target["tmp"] / "bundle"
    outcome = correction_run.produce_correction(
        entry,
        clone_directory=target["tmp"] / "clone",
        out_directory=out,
        extract_facts=lambda revision: None,
    )
    assert outcome.status == "insufficient_evidence" and not outcome.manifest
    assert [p.name for p in out.iterdir()] == ["status.json"]


def test_a_conformant_readme_yields_no_corrections_and_nothing_to_propose(
    target: dict[str, Any], make_facts: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    clean = init_git_repository(target["tmp"] / "clean", with_commit=False)
    (clean / "README.md").write_text(
        README.replace("26.5.0", "26.7.0"), encoding="utf-8", newline="\n"
    )
    revision = commit_all(clean, "seed")
    serve_other(monkeypatch, clean)
    out = target["tmp"] / "bundle"
    assert run_correct(target, facts_file(target["tmp"], revision, make_facts), out) == EXIT_OK
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"] == {}
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_correction(out, REPOSITORY, root=target["root"])
    assert "nothing to propose" in raised.value.message


def command_facts_for(revision: str, make_facts: Any, make_fact: Any) -> list[Any]:
    """The base facts plus a build and a test command from the project's own manifest."""
    return [
        *make_facts(),
        make_fact(
            "build_test_asset:build-command",
            "mvn package",
            evidence=(("pom.xml", "standard `mvn package`; no workflow step or script names it"),),
            attributes={"role": "build command", "source": "toolchain convention"},
        ),
        make_fact(
            "build_test_asset:test-command",
            "mvn test",
            evidence=(("pom.xml", "standard `mvn test`; no workflow step or script names it"),),
            attributes={"role": "test command", "source": "toolchain convention"},
        ),
    ]


def test_commands_are_printed_only_with_the_receipt_the_run_is_given(
    target: dict[str, Any], make_facts: Any, make_fact: Any
) -> None:
    from repository_presenter.components.readme_correction.chain import plan_chain
    from repository_presenter.components.readme_correction.receipts import (
        EXECUTED,
        Receipt,
        StepResult,
        receipt_path,
        store_receipt,
    )

    document = FactsDocument(
        REPOSITORY,
        target["revision"],
        tuple(command_facts_for(target["revision"], make_facts, make_fact)),
    )
    facts = target["tmp"] / "facts.json"
    write_facts(document, facts)
    # without a receipts directory the commands are held back
    bare = target["tmp"] / "bare"
    assert run_correct(target, facts, bare) == EXIT_OK
    held = json.loads((bare / CORRECTIONS_NAME).read_text(encoding="utf-8"))["report_only"]
    assert "NO_BUILD_RECEIPT" in {entry["report_only_reason"] for entry in held}
    assert "mvn package" not in (bare / "README.md").read_text(encoding="utf-8")
    # with a stored receipt for this revision and this chain they are printed, and the bundle's
    # own facts carry the proof the typed gate re-derives the addition from
    plan = plan_chain(document, target["tmp"] / "upstream", [])
    receipts = target["tmp"] / "receipts"
    steps = tuple(StepResult(s.command, EXECUTED, 0) for s in plan.steps)
    store_receipt(
        receipt_path(receipts, REPOSITORY, target["revision"], plan),
        Receipt(
            REPOSITORY,
            target["revision"],
            plan.digest(),
            EXECUTED,
            "every step exited 0",
            steps,
            {"mvn": "3.9"},
            "Windows 11 AMD64",
        ),
    )
    proven = target["tmp"] / "proven"
    code = main(
        [
            "correct-readme",
            "--repo",
            REPOSITORY,
            "--root",
            str(target["root"]),
            "--facts",
            str(facts),
            "--receipts",
            str(receipts),
            "--out",
            str(proven),
        ]
    )
    assert code == EXIT_OK
    corrected = (proven / "README.md").read_text(encoding="utf-8")
    assert "```bash\nmvn package\nmvn test\n```" in corrected
    assert corrected.index("mvn package") < corrected.index("## License")
    stored = {f["id"]: f for f in json.loads((proven / "facts.json").read_text("utf-8"))["facts"]}
    attributes = stored["build_test_asset:test-command"]["attributes"]
    assert attributes["command_chain"] == "project_files" and len(attributes["build_receipt"]) == 64
    assert (
        load_proposable_correction(proven, REPOSITORY, root=target["root"]).readme_text == corrected
    )
