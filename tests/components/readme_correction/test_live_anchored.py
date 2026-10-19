"""The live-anchored family end to end: ``correct-readme --ops`` against a local upstream, the
bundle it writes, the typed gate that re-proves it from the bundle's own bytes (one negative
control per rule, each re-sealed so only the gate's recomputation can catch it), the committed
file set and the pull request text."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from live_anchored_support import (
    README,
    RELEASE_LINE,
    REPOSITORY,
    TREE,
    corrected,
    extra_facts,
    good_ops,
    line_of,
)
from repository_presenter.cli import EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction import live_gate as lg
from repository_presenter.components.readme_correction import live_ops as lo
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.committed import (
    BUNDLE_FILES,
    COMMITTED_FILES,
    LIVE_ANCHORED_COMMITTED_FILES,
    PULL_REQUEST_NAME,
    SUMS_NAME,
    committed_files,
    pull_request_text,
    sums_problems,
    write_sums,
)
from repository_presenter.components.readme_correction.engine import CorrectionError, correct
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.live_bundle import (
    LIVE_BUNDLE_FILES,
    OPERATIONS_NAME,
    dump,
)
from repository_presenter.components.readme_correction.model import KIND_LIVE_ANCHORED
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
    internal_identifiers,
)
from repository_presenter.components.readme_correction.run import write_live_anchored
from repository_presenter.core.authorization.proposal import CURRENT_POLICY_VERSION
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.facts import FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from support import (
    REPO_ROOT,
    commit_all,
    init_git_repository,
    monitor_registry_entry,
    write_registry_file,
)

OLD_README = (
    "# Aspose.3D FOSS for Java\n\n## Installation\n\n```bash\n"
    "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0\n```\n\n"
    "## Dependencies\n\nNone.\n\n## License\n\nMIT.\n"
)


def reseal(directory: Path) -> None:
    """Recompute the manifest digests, as a forger who also edits the manifest would."""
    manifest = json.loads((directory / files.MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["files"] = {
        path.name: {"sha256": files.sha256(path.read_bytes()), "bytes": path.stat().st_size}
        for path in sorted(directory.iterdir())
        if path.name != files.MANIFEST_NAME
    }
    manifest["corrected_sha256"] = files.sha256((directory / files.README_NAME).read_bytes())
    manifest["original_sha256"] = files.sha256((directory / files.ORIGINAL_NAME).read_bytes())
    (directory / files.MANIFEST_NAME).write_text(dump(manifest), encoding="utf-8", newline="\n")


def read(directory: Path, name: str) -> Any:
    return json.loads((directory / name).read_text(encoding="utf-8"))


def write(directory: Path, name: str, document: Any) -> None:
    (directory / name).write_text(dump(document), encoding="utf-8", newline="\n")


@pytest.fixture
def live_bundle(tmp_path: Path, make_context: Any, make_facts: Any) -> Path:
    ctx = make_context(README, make_facts(*extra_facts()), TREE)
    directory = tmp_path / "bundle"
    manifest = write_live_anchored(ctx, README.encode(), good_ops(), directory)
    assert manifest["kind"] == KIND_LIVE_ANCHORED
    return directory


def accept(bundle: Path, **kwargs: Any) -> Any:
    return load_proposable_correction(bundle, REPOSITORY, root=REPO_ROOT, **kwargs)


def refusal_of(bundle: Path) -> str:
    with pytest.raises(WriteRefusedError) as raised:
        accept(bundle)
    assert raised.value.code is Refusal.CORRECTION_NOT_PROVEN
    return str(raised.value)


# ------------------------------------------------------------------------------- the bundle
def test_the_bundle_has_the_correction_layout_plus_operations_json(live_bundle: Path) -> None:
    assert {p.name for p in live_bundle.iterdir()} == set(LIVE_BUNDLE_FILES)
    assert set(LIVE_BUNDLE_FILES) == set(BUNDLE_FILES) | {OPERATIONS_NAME}
    manifest = read(live_bundle, files.MANIFEST_NAME)
    assert manifest["kind"] == KIND_LIVE_ANCHORED and manifest["state"] == files.STATE
    assert manifest["summary"] == {"DELETE_LINE": 1, "INSERT_BEFORE": 2, "REFLOW": 1, "RETITLE": 5}
    assert manifest["no_op_proof"]["provider_calls"] == 0
    assert (live_bundle / files.README_NAME).read_text(encoding="utf-8") == corrected()
    assert (live_bundle / files.ORIGINAL_NAME).read_text(encoding="utf-8") == README
    assert set(lo.ops_from_json(read(live_bundle, OPERATIONS_NAME))) == set(good_ops())


def test_the_delta_is_the_correction_judges_and_introduces_nothing(live_bundle: Path) -> None:
    delta = read(live_bundle, files.DELTA_NAME)
    assert delta["judge"] == "validate_candidate" and delta["introduced"] == []
    document = read(live_bundle, files.CORRECTIONS_NAME)
    assert document["kind"] == KIND_LIVE_ANCHORED
    assert document["stability"] == {
        "deterministic": True,
        "order_independent": True,
        "provider_calls": 0,
    }
    assert document["confinement"]["verified"] and document["confinement"]["operations"] == 9
    record = {r["id"]: r for r in document["operations"]}["release"]
    assert record["kind"] == lo.DELETE_LINE and record["line"] == line_of(RELEASE_LINE)
    assert [e["status"] for e in record["evidence"]] == ["CONTRADICTED", "README_TEXT"]


def test_the_gate_accepts_the_bundle_and_returns_the_corrected_readme(live_bundle: Path) -> None:
    candidate = accept(live_bundle)
    assert candidate.readme_text == corrected() and candidate.repository == REPOSITORY
    assert candidate.revision == read(live_bundle, files.MANIFEST_NAME)["revision"]


def test_an_existing_correction_bundle_still_goes_through_the_original_gate(
    tmp_path: Path, make_context: Any
) -> None:
    text = OLD_README
    ctx = make_context(text)
    result = correct(ctx)
    directory = tmp_path / "old"
    files.write_bundle(
        ctx, text.encode(), result, validation_delta(ctx, result, text.encode()), directory
    )
    assert read(directory, files.MANIFEST_NAME)["kind"] == "correction"
    assert not (directory / OPERATIONS_NAME).exists()
    assert accept(directory).readme_text == result.corrected


# --------------------------------------------------------- the gate recomputes from the bytes
def test_a_bundle_whose_files_were_changed_without_resealing_is_not_a_bundle(
    live_bundle: Path,
) -> None:
    (live_bundle / files.README_NAME).write_bytes(b"# changed\n")
    with pytest.raises(WriteRefusedError) as raised:
        accept(live_bundle)
    assert raised.value.code is Refusal.BUNDLE_INCONSISTENT


def test_a_tampered_readme_is_refused_even_when_the_manifest_is_resealed(
    live_bundle: Path,
) -> None:
    path = live_bundle / files.README_NAME
    path.write_text(
        path.read_text(encoding="utf-8").replace("MIT.", "Proprietary."), encoding="utf-8"
    )
    reseal(live_bundle)
    assert lg.README_NOT_REPRODUCED in refusal_of(live_bundle)


def test_tampered_operations_are_refused_whatever_the_tampering(live_bundle: Path) -> None:
    def tampered(change: Any) -> str:
        work = live_bundle.parent / "work"
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(live_bundle, work)
        operations = read(work, OPERATIONS_NAME)
        change(operations)
        write(work, OPERATIONS_NAME, operations)
        reseal(work)
        return refusal_of(work)

    def by_id(operations: list[dict[str, Any]], op_id: str) -> dict[str, Any]:
        return next(op for op in operations if op["id"] == op_id)

    def unknown_kind(ops: list[dict[str, Any]]) -> None:
        by_id(ops, "release")["kind"] = "REWRITE"

    def anchor_moved(ops: list[dict[str, Any]]) -> None:
        by_id(ops, "scope")["anchor"] = "## Scoping\n"

    def evidence_dropped(ops: list[dict[str, Any]]) -> None:
        by_id(ops, "release")["evidence"] = []

    def evidence_forged(ops: list[dict[str, Any]]) -> None:
        by_id(ops, "release")["evidence"] = ["link_target:002"]

    def another_op_added(ops: list[dict[str, Any]]) -> None:
        ops.append(
            {
                "id": "extra",
                "kind": "REFLOW",
                "anchor": "Run the example.\n",
                "replacement": "Run  the example.\n",
                "evidence": [f"readme:{line_of('Run the example.')}"],
            }
        )

    def replacement_changed(ops: list[dict[str, Any]]) -> None:
        by_id(ops, "sub")["replacement"] = "### Read a Scene and Sell It\n"

    assert lo.UNKNOWN_KIND in tampered(unknown_kind)
    assert lo.ANCHOR_NOT_FOUND in tampered(anchor_moved)
    assert lo.MISSING_EVIDENCE in tampered(evidence_dropped)
    assert lo.DELETE_EVIDENCE_MISSING in tampered(evidence_forged)
    assert lg.README_NOT_REPRODUCED in tampered(another_op_added)
    assert lo.RETITLE_NOT_COSMETIC in tampered(replacement_changed)


def test_an_operations_file_that_is_not_a_list_of_operations_is_refused(live_bundle: Path) -> None:
    write(live_bundle, OPERATIONS_NAME, {"ops": []})
    reseal(live_bundle)
    assert lo.BAD_OPERATIONS in refusal_of(live_bundle)


def test_a_bundle_with_the_operations_removed_is_refused(live_bundle: Path) -> None:
    write(live_bundle, OPERATIONS_NAME, [])
    reseal(live_bundle)
    assert lo.NO_OPERATIONS in refusal_of(live_bundle)


def test_an_original_readme_that_no_longer_holds_the_anchors_is_refused(live_bundle: Path) -> None:
    path = live_bundle / files.ORIGINAL_NAME
    path.write_text(
        path.read_text(encoding="utf-8").replace("## Scope\n", "## Limits\n"), encoding="utf-8"
    )
    reseal(live_bundle)
    assert lo.ANCHOR_NOT_FOUND in refusal_of(live_bundle)


def test_facts_for_another_revision_are_refused_as_stale(live_bundle: Path) -> None:
    facts = read(live_bundle, "facts.json")
    facts["source_revision"] = "b" * 40
    write(live_bundle, "facts.json", facts)
    reseal(live_bundle)
    assert lo.STALE_REVISION in refusal_of(live_bundle)


def test_a_manifest_for_another_revision_than_the_records_is_refused_as_stale(
    live_bundle: Path,
) -> None:
    manifest = read(live_bundle, files.MANIFEST_NAME)
    manifest["revision"] = "c" * 40
    write(live_bundle, files.MANIFEST_NAME, manifest)
    assert lo.STALE_REVISION in refusal_of(live_bundle)


def test_evidence_the_bundles_own_facts_do_not_hold_is_refused(live_bundle: Path) -> None:
    facts = read(live_bundle, "facts.json")
    facts["facts"] = [f for f in facts["facts"] if f["id"] != "dependency:guava"]
    write(live_bundle, "facts.json", facts)
    reseal(live_bundle)
    assert lo.EVIDENCE_UNKNOWN in refusal_of(live_bundle)


def test_a_fact_whose_polarity_was_flipped_cannot_back_an_operation(live_bundle: Path) -> None:
    facts = read(live_bundle, "facts.json")
    for fact in facts["facts"]:
        if fact["id"] == "dependency:guava":
            fact["polarity"] = "UNRESOLVED"
    write(live_bundle, "facts.json", facts)
    reseal(live_bundle)
    assert lo.EVIDENCE_WRONG_POLARITY in refusal_of(live_bundle)


def test_a_tree_that_holds_the_deleted_target_cannot_be_used_to_hide_a_fact_flip(
    live_bundle: Path,
) -> None:
    # the delete rests on a CONTRADICTED fact; flipping it while the tree lists the file refuses
    facts = read(live_bundle, "facts.json")
    for fact in facts["facts"]:
        if fact["id"] == "link_target:005":
            fact["polarity"] = "SUPPORTED"
    write(live_bundle, "facts.json", facts)
    (live_bundle / files.TREE_NAME).write_text(
        "\n".join([*TREE, "RELEASE_NOTES.md"]) + "\n", encoding="utf-8"
    )
    reseal(live_bundle)
    assert lo.DELETE_LINK_NOT_BROKEN in refusal_of(live_bundle)


def test_a_record_that_misstates_the_operations_is_refused(live_bundle: Path) -> None:
    document = read(live_bundle, files.CORRECTIONS_NAME)
    document["operations"][0]["line"] += 1
    write(live_bundle, files.CORRECTIONS_NAME, document)
    reseal(live_bundle)
    assert lg.RECORD_MISMATCH in refusal_of(live_bundle)


def test_a_delta_that_does_not_match_the_judges_is_refused(live_bundle: Path) -> None:
    delta = read(live_bundle, files.DELTA_NAME)
    delta["corrected_failures"] = {}
    write(live_bundle, files.DELTA_NAME, delta)
    reseal(live_bundle)
    assert lg.DELTA_MISMATCH in refusal_of(live_bundle)


def test_a_kind_that_is_neither_family_is_refused(live_bundle: Path) -> None:
    manifest = read(live_bundle, files.MANIFEST_NAME)
    manifest["kind"] = "regenerated"
    write(live_bundle, files.MANIFEST_NAME, manifest)
    assert "not a correction bundle" in refusal_of(live_bundle)


def test_operations_that_would_introduce_a_failing_check_are_refused_at_production(
    tmp_path: Path, make_context: Any, make_facts: Any
) -> None:
    ctx = make_context(README, make_facts(*extra_facts()), TREE)
    # a second badge row is a failure the live README does not have; the judge counts it
    ops = [
        lo.Op(
            "split",
            lo.REFLOW,
            README.split("\n\n")[1] + "\n",
            README.split("\n\n")[1].replace("\n", "\n\n") + "\n",
            ("link_target:001",),
        )
    ]
    out = tmp_path / "out"
    with pytest.raises(CorrectionError) as raised:
        write_live_anchored(ctx, README.encode(), ops, out)
    assert "REFLOW_CHANGES_LINKS" in str(raised.value) and not out.exists()


# ------------------------------------------------------------ committed file set and the text
def committed(tmp_path: Path, live_bundle: Path) -> Path:
    directory = tmp_path / "committed"
    shutil.copytree(live_bundle, directory)
    manifest = read(directory, files.MANIFEST_NAME)
    text = pull_request_text(
        compose_correction_pull_request(
            bundle=directory,
            repository=REPOSITORY,
            candidate_hash=manifest["corrected_sha256"],
            source_revision=manifest["revision"],
            policy_version=CURRENT_POLICY_VERSION,
        )
    )
    (directory / PULL_REQUEST_NAME).write_bytes(text.encode("utf-8"))
    write_sums(directory)
    return directory


def test_a_committed_live_bundle_holds_the_correction_set_plus_operations(
    tmp_path: Path, live_bundle: Path
) -> None:
    directory = committed(tmp_path, live_bundle)
    assert committed_files(directory) == LIVE_ANCHORED_COMMITTED_FILES
    assert COMMITTED_FILES | {OPERATIONS_NAME} == LIVE_ANCHORED_COMMITTED_FILES
    assert {p.name for p in directory.iterdir()} == LIVE_ANCHORED_COMMITTED_FILES | {SUMS_NAME}
    assert sums_problems(directory) == []
    assert accept(directory, require_sums=True).readme_text == corrected()


def test_a_committed_live_bundle_without_its_operations_or_with_a_stray_file_is_refused(
    tmp_path: Path, live_bundle: Path
) -> None:
    directory = committed(tmp_path, live_bundle)
    (directory / "notes.txt").write_text("x", encoding="utf-8")
    assert any(
        "notes.txt is not part of a committed correction bundle" in p
        for p in sums_problems(directory)
    )
    (directory / "notes.txt").unlink()
    (directory / OPERATIONS_NAME).unlink()
    problems = sums_problems(directory)
    assert f"{OPERATIONS_NAME} is missing" in problems


def test_a_committed_correction_bundle_may_not_carry_operations(
    tmp_path: Path, make_context: Any
) -> None:
    text = OLD_README
    ctx = make_context(text)
    result = correct(ctx)
    directory = tmp_path / "old"
    files.write_bundle(
        ctx, text.encode(), result, validation_delta(ctx, result, text.encode()), directory
    )
    (directory / PULL_REQUEST_NAME).write_text("x", encoding="utf-8")
    (directory / OPERATIONS_NAME).write_text("[]", encoding="utf-8")
    write_sums(directory)
    assert committed_files(directory) == COMMITTED_FILES
    assert any(
        f"{OPERATIONS_NAME} is not part of a committed correction bundle" in p
        for p in sums_problems(directory)
    )


def test_the_pull_request_text_is_what_the_committed_copy_must_hold(
    tmp_path: Path, live_bundle: Path
) -> None:
    directory = committed(tmp_path, live_bundle)
    (directory / PULL_REQUEST_NAME).write_text("Title: other\n\nbody", encoding="utf-8")
    write_sums(directory)
    with pytest.raises(WriteRefusedError) as raised:
        accept(directory, require_sums=True)
    assert "pull request text" in str(raised.value)


def compose(bundle: Path) -> Any:
    manifest = read(bundle, files.MANIFEST_NAME)
    return compose_correction_pull_request(
        bundle=bundle,
        repository=REPOSITORY,
        candidate_hash=manifest["corrected_sha256"],
        source_revision=manifest["revision"],
        policy_version=CURRENT_POLICY_VERSION,
    )


def test_the_pull_request_lists_every_operation_by_kind_with_its_evidence(
    live_bundle: Path,
) -> None:
    content = compose(live_bundle)
    body = content.body
    assert content.title.startswith("docs(readme): ") and "retitle 5 headings" in content.title
    assert "add Navigation, At a Glance and Dependencies" in content.title
    assert "`## Features` -> `## Key Capabilities`" in body
    assert "`## Scope` -> `## Scope and Limitations`" in body
    assert "inserted `## Navigation`, `## At a Glance` before line" in body
    assert "inserted `## Dependencies` before line" in body
    assert "2 badge lines are joined onto one line" in body
    assert "removed `- Read the [release notes](RELEASE_NOTES.md).`" in body
    assert "link target `RELEASE_NOTES.md`" in body  # the evidence, in words
    assert "dependency `com.google.guava:guava:33.0`" in body
    assert "- kind: live_anchored" in body


def test_the_pull_request_states_that_no_text_changes_except_at_the_listed_places(
    live_bundle: Path,
) -> None:
    body = compose(live_bundle).body
    assert "Only `README.md` changes, and only at the places listed" in body
    assert "Every other line is byte for byte yours" in body
    assert "No sentence you wrote is rewritten" in body
    assert "model calls: 0" in body and "deterministic: yes" in body
    assert "idempotent" not in body  # that is the detectors' property, not this family's
    assert "No model wrote any of this text" not in body  # the operations' author is not claimed


def test_the_pull_request_never_blames_the_readme_for_checks_it_is_not_held_to(
    live_bundle: Path,
) -> None:
    delta = read(live_bundle, files.DELTA_NAME)
    body = compose(live_bundle).body
    counted = ("BC-03", "BC-04", "BC-06", "BC-12", "BC-14")  # commands, examples, links, versions
    before = sum(n for k, n in delta["live_failures"].items() if k.split("/")[0] in counted)
    after = sum(n for k, n in delta["corrected_failures"].items() if k.split("/")[0] in counted)
    assert f"They report {before} failure(s) on yours and {after} on the corrected one" in body
    # the layout and wording checks (BC-07) are not held up against the live README
    assert "BC-07" not in body and "title case" not in body
    assert internal_identifiers(body, quoted=False) == []


def test_the_pull_request_notes_the_diagram_layout_defects_that_were_left(
    tmp_path: Path, live_bundle: Path
) -> None:
    document = read(live_bundle, files.CORRECTIONS_NAME)
    assert document["diagram_notes"] == []  # a canonical drawing needs no note
    document["diagram_notes"] = [{"code": "COLUMN_ORDER", "detail": "capl is declared before capr"}]
    write(live_bundle, files.CORRECTIONS_NAME, document)
    assert "1 layout note on the new At a Glance diagram" in compose(live_bundle).body


# ------------------------------------------------------------------------- the CLI end to end
@pytest.fixture
def target(tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    source = init_git_repository(tmp_path / "upstream", with_commit=False)
    (source / "README.md").write_text(README, encoding="utf-8", newline="\n")
    for name in ("LICENSE", "pom.xml", "CHANGELOG.md"):
        (source / name).write_text(f"{name}\n", encoding="utf-8")
    revision = commit_all(source, "seed")
    write_registry_file(project, [monitor_registry_entry(REPOSITORY, mode="dry_run")])

    def serve(clone_url: str, destination: Path, **kwargs: Any) -> Any:
        return pinned_read_only_clone(str(source), destination)

    monkeypatch.setattr(correction_run, "pinned_read_only_clone", serve)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return {"root": project, "revision": revision, "tmp": tmp_path}


def run_cli(target: dict[str, Any], *extra: str) -> int:
    return main(["correct-readme", "--repo", REPOSITORY, "--root", str(target["root"]), *extra])


def prepare(
    target: dict[str, Any], make_facts: Any, ops: list[lo.Op] | None = None
) -> tuple[Path, Path]:
    facts = target["tmp"] / "facts.json"
    write_facts(
        FactsDocument(REPOSITORY, target["revision"], tuple(make_facts(*extra_facts()))), facts
    )
    operations = target["tmp"] / "ops.json"
    operations.write_text(dump(lo.ops_to_json(ops or good_ops())), encoding="utf-8", newline="\n")
    return facts, operations


def test_correct_readme_with_ops_writes_a_bundle_the_gate_accepts(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts, operations = prepare(target, make_facts)
    out = target["tmp"] / "bundle"
    assert (
        run_cli(target, "--facts", str(facts), "--ops", str(operations), "--out", str(out))
        == EXIT_OK
    )
    said = capsys.readouterr().out
    assert "corrected: 9 operation(s) (DELETE_LINE 1, INSERT_BEFORE 2, REFLOW 1, RETITLE 5)" in said
    assert (out / files.README_NAME).read_text(encoding="utf-8") == corrected()
    manifest = read(out, files.MANIFEST_NAME)
    assert manifest["kind"] == KIND_LIVE_ANCHORED and manifest["revision"] == target["revision"]
    assert read(out, files.DELTA_NAME)["introduced"] == []
    assert read(out, files.CORRECTIONS_NAME)["stability"]["provider_calls"] == 0
    assert accept_with_root(out, target).readme_text == corrected()


def accept_with_root(bundle: Path, target: dict[str, Any]) -> Any:
    return load_proposable_correction(bundle, REPOSITORY, root=target["root"])


def test_correct_readme_with_ops_refuses_a_refused_operation_and_writes_no_bundle(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = lo.Op(
        "gone",
        lo.DELETE_LINE,
        "- Read the [changelog](CHANGELOG.md).\n",
        "",
        ("link_target:006",),
    )
    facts, operations = prepare(target, make_facts, [bad])
    out = target["tmp"] / "bundle"
    assert (
        run_cli(target, "--facts", str(facts), "--ops", str(operations), "--out", str(out))
        != EXIT_OK
    )
    assert "DELETE_LINK_NOT_BROKEN" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_correct_readme_with_ops_needs_facts_for_exactly_the_head(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    _facts, operations = prepare(target, make_facts)
    out = target["tmp"] / "bundle"
    assert run_cli(target, "--ops", str(operations), "--out", str(out)) == EXIT_USAGE
    stale = target["tmp"] / "stale.json"
    write_facts(FactsDocument(REPOSITORY, "b" * 40, tuple(make_facts(*extra_facts()))), stale)
    assert (
        run_cli(target, "--facts", str(stale), "--ops", str(operations), "--out", str(out))
        != EXIT_OK
    )
    assert "facts are for" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())


def test_correct_readme_with_ops_refuses_an_operations_file_it_cannot_read(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts, operations = prepare(target, make_facts)
    operations.write_text('[{"id": "a", "kind": "REWRITE"}]', encoding="utf-8")
    out = target["tmp"] / "bundle"
    assert (
        run_cli(target, "--facts", str(facts), "--ops", str(operations), "--out", str(out))
        != EXIT_OK
    )
    assert "cannot be used" in capsys.readouterr().err


def test_correct_readme_without_ops_is_unchanged(
    target: dict[str, Any], make_facts: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    facts, _operations = prepare(target, make_facts)
    out = target["tmp"] / "bundle"
    assert run_cli(target, "--facts", str(facts), "--out", str(out)) == EXIT_OK
    assert read(out, files.MANIFEST_NAME)["kind"] == "correction"
    assert not (out / OPERATIONS_NAME).exists()
    assert "edit(s)" in capsys.readouterr().out
