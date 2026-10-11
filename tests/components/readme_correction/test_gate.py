"""The correction bundle and its typed propose gate, with negative controls that re-seal a tampered
bundle so the manifest digests pass and only the gate's own re-derivation can catch the change."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.candidates import (
    count_current_candidates,
    load_proposable_candidate,
    verify_bundle,
)
from repository_presenter.core.hashing import sha256_text
from support import REPO_ROOT

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
README = """# Aspose.3D FOSS for Java

Opening the maintainers wrote.

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

## Dependencies

None.

## Scope and Limitations

An unrelated limitation sentence the maintainers wrote.

## Development and Testing

Run mvn test.

## License

MIT.
"""


def make_bundle(tmp_path: Path, make_context: Any, readme: str = README) -> Path:
    ctx = make_context(readme)
    result = correct(ctx)
    delta = validation_delta(ctx, result, readme.encode())
    directory = tmp_path / "bundle"
    files.write_bundle(ctx, readme.encode(), result, delta, directory)
    return directory


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
    (directory / files.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def refusal(directory: Path) -> WriteRefusedError:
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT)
    return raised.value


def test_a_proven_correction_loads_as_the_one_thing_a_proposal_carries(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    manifest = verify_bundle(directory)  # the existing integrity reader accepts the format
    assert manifest is not None and manifest["kind"] == "correction"
    assert manifest["no_op_proof"]["provider_calls"] == 0
    assert (
        manifest["no_op_proof"]["byte_identical"]
        and manifest["no_op_proof"]["idempotent_on_output"]
    )
    candidate = load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT)
    assert candidate.readme_text == README.replace("26.5.0", "26.7.0")
    assert candidate.candidate_hash == sha256_text(candidate.readme_text)
    assert candidate.revision == manifest["revision"]
    patch = (directory / files.PATCH_NAME).read_text(encoding="utf-8")
    assert "-mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0" in patch
    assert "+mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0" in patch


def test_corrections_json_lists_every_edit_with_its_evidence(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    document = json.loads((directory / files.CORRECTIONS_NAME).read_text(encoding="utf-8"))
    assert document["kind"] == "correction" and document["stability"]["provider_calls"] == 0
    (edit,) = [e for e in document["edits"] if e["detector"] == "claim_version"]
    assert edit["kind"] == "FALSE_CLAIM_FIX" and edit["original"] == "26.5.0"
    assert edit["replacement"] == "26.7.0" and edit["line"] == 8
    assert {(e["fact_id"], e["status"]) for e in edit["evidence"]} == {
        ("package:name", "SUPPORTED"),
        ("package:published_version", "SUPPORTED"),
    }
    assert sum(document["summary"].values()) == len(document["edits"])


def test_a_correction_bundle_is_invisible_to_the_regenerated_candidate_path(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    root = tmp_path / "control"
    slot = root / "candidates" / REPOSITORY.replace("/", "__")
    slot.mkdir(parents=True)
    manifest = json.loads((directory / files.MANIFEST_NAME).read_text(encoding="utf-8"))
    target = slot / manifest["revision"]
    target.mkdir()
    for path in directory.iterdir():
        (target / path.name).write_bytes(path.read_bytes())
    (slot / "CURRENT").write_text(manifest["revision"] + "\n", encoding="utf-8")
    assert count_current_candidates(root) == 0  # never counted as a reviewable candidate
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_candidate(root, REPOSITORY, acceptance=lambda *_: None)
    assert raised.value.code == Refusal.BUNDLE_NOT_READY


def test_a_regenerated_state_cannot_borrow_the_correction_gate(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    manifest_path = directory / files.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "READY_FOR_PROPOSAL"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert refusal(directory).code == Refusal.CORRECTION_NOT_PROVEN


def test_a_corrected_readme_that_changes_more_than_its_edits_is_refused_even_when_resealed(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    readme = directory / files.README_NAME
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "An unrelated limitation", "A rewritten limitation"
        ),
        encoding="utf-8",
    )
    reseal(directory)
    error = refusal(directory)
    assert error.code == Refusal.CORRECTION_NOT_PROVEN
    assert "does not reproduce README.md byte for byte" in error.message


def test_an_unlisted_or_forged_edit_is_refused_even_when_resealed(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    path = directory / files.CORRECTIONS_NAME
    document = json.loads(path.read_text(encoding="utf-8"))
    document["edits"][0]["replacement"] = "9.9.9"
    path.write_text(json.dumps(document), encoding="utf-8")
    reseal(directory)
    assert "does not list exactly the edits" in refusal(directory).message


def test_evidence_that_is_not_supported_is_refused_even_when_resealed(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    path = directory / "facts.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for fact in document["facts"]:
        if fact["id"] == "package:published_version":
            fact["polarity"] = "UNRESOLVED"
    path.write_text(json.dumps(document), encoding="utf-8")
    reseal(directory)
    assert refusal(directory).code == Refusal.CORRECTION_NOT_PROVEN  # no edit is left to justify


def test_a_bundle_that_corrects_nothing_is_not_proposable(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context, README.replace("26.5.0", "26.7.0"))
    assert "nothing to propose" in refusal(directory).message


def test_a_bundle_for_another_repository_or_with_a_corrupt_file_is_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    with pytest.raises(WriteRefusedError) as other:
        load_proposable_correction(
            directory, "aspose-cells-foss/Aspose.Cells-FOSS-for-Java", root=REPO_ROOT
        )
    assert other.value.code == Refusal.BUNDLE_INCONSISTENT
    (directory / files.README_NAME).write_bytes(b"corrupt")
    assert refusal(directory).code == Refusal.BUNDLE_INCONSISTENT


def test_the_pull_request_lists_each_edit_with_its_evidence_and_claims_nothing_else(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context)
    content = compose_correction_pull_request(
        bundle=directory,
        repository=REPOSITORY,
        candidate_hash="h" * 64,
        source_revision="a" * 40,
        policy_version="p1",
    )
    assert "`26.5.0` -> `26.7.0`" in content.body
    assert "`package:published_version` (SUPPORTED)" in content.body
    assert "Refreshes the README" not in content.body and "reconciled" not in content.body
    assert "kind: correction" in content.body and "no model wrote" in content.body


STRUCTURE_README = README.replace("## Dependencies", "# Dependencies note").replace(
    "## Scope and Limitations",
    "<details>\n<summary>More</summary>\n\nhidden\n\n## Scope and Limitations",
)


def test_structure_fixes_are_proposable_evidenced_by_their_readme_lines(
    tmp_path: Path, make_context: Any
) -> None:
    directory = make_bundle(tmp_path, make_context, STRUCTURE_README)
    candidate = load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT)
    assert candidate.readme_text.count("</details>") == 1
    assert "\n## Dependencies note\n" in candidate.readme_text
    document = json.loads((directory / files.CORRECTIONS_NAME).read_text(encoding="utf-8"))
    fixes = [e for e in document["edits"] if e["kind"] == "STRUCTURE_FIX"]
    assert {e["detector"] for e in fixes} == {"second_h1", "unclosed_details"}
    assert all(
        ev["status"] == "README_TEXT" and ev["value"].startswith("README.md:")
        for e in fixes
        for ev in e["evidence"]
    )
    content = compose_correction_pull_request(
        bundle=directory,
        repository=REPOSITORY,
        candidate_hash="h" * 64,
        source_revision="a" * 40,
        policy_version="p1",
    )
    assert "Broken markup repaired" in content.body and "`README.md:" in content.body
    assert "inserted `</details>` before line" in content.body
