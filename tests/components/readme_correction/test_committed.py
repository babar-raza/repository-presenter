"""The committed correction bundle (``corrections/<run>/<slug>/``): the closed file set, SHA256SUMS,
and the pull request text the reviewer reads being the text that is posted. Each negative control
changes the committed copy after it was assembled and shows the check that catches it - including
the ones a forger who also re-seals the manifest would pass, which only the digests can catch."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme_correction import bundle as files
from repository_presenter.components.readme_correction.check import validation_delta
from repository_presenter.components.readme_correction.committed import (
    BUNDLE_FILES,
    COMMITTED_FILES,
    PULL_REQUEST_NAME,
    SUMS_NAME,
    pull_request_text,
    pull_request_text_problem,
    sums_problems,
    write_sums,
)
from repository_presenter.components.readme_correction.engine import correct
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.core.authorization.proposal import CURRENT_POLICY_VERSION
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
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

## License

MIT.
"""


def committed(tmp_path: Path, make_context: Any) -> Path:
    """What ``tools/corrections/assemble.py`` leaves for one repository: the bundle, the text the
    effect will post, and the digests over all of it."""
    ctx = make_context(README)
    result = correct(ctx)
    directory = tmp_path / "bundle"
    files.write_bundle(
        ctx, README.encode(), result, validation_delta(ctx, result, README.encode()), directory
    )
    manifest = json.loads((directory / files.MANIFEST_NAME).read_text(encoding="utf-8"))
    text = pull_request_text(
        compose_correction_pull_request(
            bundle=directory,
            repository=REPOSITORY,
            candidate_hash=manifest["corrected_sha256"],
            source_revision=manifest["revision"],
            policy_version=CURRENT_POLICY_VERSION,
        )
    )
    # the candidate hash the effect uses is the LF-normalized text's, which for this LF README is
    # the file digest
    corrected = (directory / files.README_NAME).read_text(encoding="utf-8")
    assert sha256_text(corrected) == manifest["corrected_sha256"]
    (directory / PULL_REQUEST_NAME).write_bytes(text.encode("utf-8"))
    write_sums(directory)
    return directory


def refusal(directory: Path) -> WriteRefusedError:
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT, require_sums=True)
    return raised.value


def test_the_committed_file_set_is_the_bundles_own_files_and_the_pull_request_text() -> None:
    assert set(BUNDLE_FILES) == {
        "manifest.json",
        "README.md",
        "README.original.md",
        "README.patch",
        "corrections.json",
        "validation_delta.json",
        "facts.json",
        "tree.txt",
    }
    assert {"PULL_REQUEST.md", *BUNDLE_FILES} == COMMITTED_FILES
    assert SUMS_NAME not in COMMITTED_FILES  # the digests do not list themselves


def test_a_write_bundle_directory_is_exactly_the_bundle_files(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    assert {p.name for p in directory.iterdir()} == COMMITTED_FILES | {SUMS_NAME}
    assert sums_problems(directory) == []


def test_sums_are_in_sha256sum_format_so_the_hosted_step_can_check_them_with_the_platform_tool(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    raw = (directory / SUMS_NAME).read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    lines = raw.decode("utf-8").splitlines()
    assert lines == sorted(lines, key=lambda line: line.split("  ", 1)[1])
    assert all(len(line.split("  ", 1)[0]) == 64 for line in lines) and len(lines) == 9
    tool = shutil.which("sha256sum")
    if tool is None:
        pytest.skip("sha256sum is not available")
    done = subprocess.run(
        [tool, "--check", "--strict", "--quiet", SUMS_NAME],
        cwd=directory,
        capture_output=True,
        text=True,
        env={**os.environ},
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_an_intact_committed_bundle_loads_through_the_typed_gate_with_sums_required(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    candidate = load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT, require_sums=True)
    assert "aspose-3d-foss:26.7.0" in candidate.readme_text
    assert candidate.candidate_hash == sha256_text(candidate.readme_text)
    assert (
        pull_request_text_problem(
            directory,
            repository=REPOSITORY,
            candidate_hash=candidate.candidate_hash,
            source_revision=candidate.revision,
            policy_version=CURRENT_POLICY_VERSION,
        )
        is None
    )


def test_the_gate_without_require_sums_is_unchanged_for_a_plain_bundle(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    (directory / SUMS_NAME).unlink()
    (directory / PULL_REQUEST_NAME).unlink()
    assert load_proposable_correction(directory, REPOSITORY, root=REPO_ROOT).readme_text
    assert refusal(directory).code == Refusal.BUNDLE_INCONSISTENT  # but not as a committed one


@pytest.mark.parametrize("name", sorted(COMMITTED_FILES))
def test_editing_any_committed_file_is_caught_by_its_digest_even_with_the_manifest_resealed(
    tmp_path: Path, make_context: Any, name: str
) -> None:
    directory = committed(tmp_path, make_context)
    path = directory / name
    path.write_bytes(path.read_bytes() + b"\n")
    problems = sums_problems(directory)
    assert problems == [f"{name} does not match its digest in {SUMS_NAME}"]
    error = refusal(directory)
    assert error.code == Refusal.BUNDLE_INCONSISTENT
    assert "not intact" in error.message and name in error.message


def test_a_forger_who_recomputes_the_sums_is_caught_by_the_manifest_and_the_rederivation(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    readme = directory / files.README_NAME
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nA forged paragraph.\n", encoding="utf-8"
    )
    write_sums(directory)  # the digests now agree with the forgery
    assert sums_problems(directory) == []
    assert refusal(directory).code == Refusal.BUNDLE_INCONSISTENT  # the manifest digest disagrees


def test_a_file_that_is_not_part_of_a_committed_bundle_is_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    (directory / "run.log").write_text("internal\n", encoding="utf-8")
    assert sums_problems(directory) == ["run.log is not part of a committed correction bundle"]
    write_sums(directory)  # even listed in the digests, an unknown name is refused
    assert any("is not '<sha256>" in p for p in sums_problems(directory))


def test_a_missing_file_or_missing_digest_is_refused(tmp_path: Path, make_context: Any) -> None:
    directory = committed(tmp_path, make_context)
    (directory / "tree.txt").unlink()
    problems = sums_problems(directory)
    assert "tree.txt is missing" in problems
    path = directory / SUMS_NAME
    kept = [
        line
        for line in path.read_text(encoding="utf-8").splitlines(True)
        if "README.patch" not in line
    ]
    path.write_text("".join(kept), encoding="utf-8")
    assert f"{SUMS_NAME} does not list README.patch" in sums_problems(directory)


@pytest.mark.parametrize(
    "line",
    [
        "not a digest  README.md\n",
        "0" * 64 + " README.md\n",  # one space
        "0" * 64 + "  ../README.md\n",
        "0" * 64 + "  sub/README.md\n",
        "0" * 63 + "G  README.md\n",
    ],
)
def test_a_malformed_sums_line_is_refused(tmp_path: Path, make_context: Any, line: str) -> None:
    directory = committed(tmp_path, make_context)
    path = directory / SUMS_NAME
    path.write_text(path.read_text(encoding="utf-8") + line, encoding="utf-8")
    assert any("is not '<sha256>" in p for p in sums_problems(directory))


def test_a_duplicated_digest_line_and_carriage_returns_are_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    path = directory / SUMS_NAME
    first = path.read_text(encoding="utf-8").splitlines()[0]
    path.write_bytes(path.read_bytes() + first.encode() + b"\n")
    assert any("twice" in p for p in sums_problems(directory))
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert any("carriage returns" in p for p in sums_problems(directory))


def test_no_sums_file_and_a_link_instead_of_one_are_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    original = (directory / SUMS_NAME).read_bytes()
    (directory / SUMS_NAME).unlink()
    assert sums_problems(directory) == [f"{SUMS_NAME} is missing"]
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_bytes(original)
    try:
        (directory / SUMS_NAME).symlink_to(elsewhere)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available")
    assert sums_problems(directory) == [f"{SUMS_NAME} is missing"]  # a link is not a regular file


def test_a_subdirectory_or_link_among_the_files_is_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    (directory / "nested").mkdir()
    assert "nested is not a regular file" in sums_problems(directory)
    (directory / "nested").rmdir()
    assert sums_problems(directory) == []


def test_a_directory_that_is_not_there_is_refused(tmp_path: Path) -> None:
    assert sums_problems(tmp_path / "absent") == ["absent is not a regular directory"]


def test_pull_request_text_that_is_not_what_the_effect_would_post_is_refused(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    path = directory / PULL_REQUEST_NAME
    path.write_text(
        path.read_text(encoding="utf-8").replace("### How to decline", "### Ignore this"),
        encoding="utf-8",
    )
    write_sums(directory)  # digests agree; the text still is not what would be posted
    assert sums_problems(directory) == []
    error = refusal(directory)
    assert error.code == Refusal.BUNDLE_INCONSISTENT
    assert "not the pull request text" in error.message


def test_the_committed_text_carries_the_title_and_the_provenance_block_the_effect_reads_back(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    text = (directory / PULL_REQUEST_NAME).read_text(encoding="utf-8")
    manifest = json.loads((directory / files.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert text.startswith("Title: docs(readme): ")
    assert f"- candidate_hash: {manifest['corrected_sha256']}" in text
    assert f"- source_revision: {manifest['revision']}" in text
    assert "- kind: correction" in text


def test_a_gate_refusal_for_another_repository_still_applies_to_a_committed_bundle(
    tmp_path: Path, make_context: Any
) -> None:
    directory = committed(tmp_path, make_context)
    with pytest.raises(WriteRefusedError) as raised:
        load_proposable_correction(
            directory,
            "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
            root=REPO_ROOT,
            require_sums=True,
        )
    assert raised.value.code == Refusal.BUNDLE_INCONSISTENT
