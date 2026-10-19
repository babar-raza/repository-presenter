"""A correction bundle as it is committed for the hosted propose run: ``corrections/<run>/<slug>/``.

``correct-readme --out`` writes a working directory; the hosted ``propose.yml`` correction mode
reads a *committed* one, reviewed in the same pull request as its authorization record. What makes
that copy trustworthy is a closed shape, checked in one place by one function (``sums_problems``)
that the typed gate calls for ``propose --correction-bundle DIR --require-sums``:

* exactly the files in :data:`COMMITTED_FILES` - the bundle's own eight (``write_bundle``) and
  ``PULL_REQUEST.md``, the text the effect will post, written for the reviewer to read in the diff -
  and nothing else (no run log, no clone, no working file: an unexpected entry is a refusal);
* ``SHA256SUMS`` over all of them, in ``sha256sum --check`` format, so the hosted run can verify the
  copy with the platform's own tool before any token exists, and the gate verifies it again;
* ``PULL_REQUEST.md`` equal to what ``compose_correction_pull_request`` composes from the bundle
  now, so the text a person approved is the text that is posted.

None of this grants anything: the digests prove the copy is the bytes that were assembled; the
manifest, the typed gate's re-derivation, the authorization record (it binds the sha256 of the
corrected README) and the registry write gate remain what authorize a proposal.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from repository_presenter.components.propose.pull_request import PullRequestContent
from repository_presenter.components.readme_correction.bundle import (
    CORRECTIONS_NAME,
    DELTA_NAME,
    MANIFEST_NAME,
    ORIGINAL_NAME,
    PATCH_NAME,
    README_NAME,
    TREE_NAME,
)
from repository_presenter.components.readme_correction.live_bundle import OPERATIONS_NAME
from repository_presenter.components.readme_correction.model import KIND_FIELD, KIND_LIVE_ANCHORED
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)

SUMS_NAME = "SHA256SUMS"
PULL_REQUEST_NAME = "PULL_REQUEST.md"
FACTS_NAME = "facts.json"
#: The files ``write_bundle`` writes - the bundle itself, which ``verify_bundle`` and the typed gate
#: read. The gate re-derives the correction from the original README, the facts and the tree, so
#: they travel with the result.
BUNDLE_FILES: tuple[str, ...] = (
    MANIFEST_NAME,
    README_NAME,
    ORIGINAL_NAME,
    PATCH_NAME,
    CORRECTIONS_NAME,
    DELTA_NAME,
    FACTS_NAME,
    TREE_NAME,
)
#: Everything a committed correction directory holds besides ``SHA256SUMS`` itself.
COMMITTED_FILES: frozenset[str] = frozenset((*BUNDLE_FILES, PULL_REQUEST_NAME))
#: A live-anchored bundle (``live_bundle.py``) holds one file more: the operations it applies.
LIVE_ANCHORED_COMMITTED_FILES: frozenset[str] = COMMITTED_FILES | {OPERATIONS_NAME}
_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9._-]+)$")


def pull_request_text(content: PullRequestContent) -> str:
    """The committed ``PULL_REQUEST.md``: the title, then the body, exactly as they are posted."""
    return f"Title: {content.title}\n\n{content.body}"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sums(directory: Path) -> None:
    """Write ``SHA256SUMS`` over every file of ``directory``: LF line endings, sorted by name (the
    same bytes on every platform)."""
    lines = [
        f"{_digest(path)}  {path.name}\n"
        for path in sorted(directory.iterdir(), key=lambda entry: entry.name)
        if path.name != SUMS_NAME
    ]
    (directory / SUMS_NAME).write_bytes("".join(lines).encode("utf-8"))


def committed_files(directory: Path) -> frozenset[str]:
    """The file set ``directory`` must hold: the correction set, or the live-anchored set when its
    manifest says ``kind: live_anchored``. A manifest that cannot be read leaves the correction
    set, so the typed gate (which reads it too) refuses the bundle for its own reason."""
    try:
        manifest = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return COMMITTED_FILES
    if isinstance(manifest, dict) and manifest.get(KIND_FIELD) == KIND_LIVE_ANCHORED:
        return LIVE_ANCHORED_COMMITTED_FILES
    return COMMITTED_FILES


def sums_problems(directory: Path) -> list[str]:
    """Why ``directory`` is not a committed correction bundle with intact digests; empty when it is.

    Checks, each independently: the directory and ``SHA256SUMS`` are real (not links); every line
    of ``SHA256SUMS`` is ``<64 hex>  <name>`` with a name from the committed file set, once; the
    listed names are exactly the committed file set (:data:`COMMITTED_FILES`, plus
    ``operations.json`` for a live-anchored bundle); the directory holds nothing else, and no
    entry is a link or a subdirectory; every digest is the file's."""
    if directory.is_symlink() or not directory.is_dir():
        return [f"{directory.name} is not a regular directory"]
    wanted = committed_files(directory)
    sums = directory / SUMS_NAME
    if sums.is_symlink() or not sums.is_file():
        return [f"{SUMS_NAME} is missing"]
    try:
        text = sums.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return [f"{SUMS_NAME} is not UTF-8"]
    problems: list[str] = []
    expected: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        found = _LINE.match(line)
        if found is None or found.group(2) not in wanted:
            problems.append(f"{SUMS_NAME} line {number} is not '<sha256>  <committed file>'")
        elif found.group(2) in expected:
            problems.append(f"{SUMS_NAME} lists {found.group(2)} twice")
        else:
            expected[found.group(2)] = found.group(1)
    if "\r" in text:
        problems.append(f"{SUMS_NAME} has carriage returns")
    present = {path.name: path for path in directory.iterdir() if path.name != SUMS_NAME}
    for name, path in sorted(present.items()):
        if path.is_symlink() or not path.is_file():
            problems.append(f"{name} is not a regular file")
        elif name not in wanted:
            problems.append(f"{name} is not part of a committed correction bundle")
    for name in sorted(wanted - set(expected)):
        problems.append(f"{SUMS_NAME} does not list {name}")
    for name in sorted(wanted - set(present)):
        problems.append(f"{name} is missing")
    for name, digest in sorted(expected.items()):
        listed = present.get(name)
        if (
            listed is not None
            and listed.is_file()
            and not listed.is_symlink()
            and _digest(listed) != digest
        ):
            problems.append(f"{name} does not match its digest in {SUMS_NAME}")
    return problems


def pull_request_text_problem(
    directory: Path,
    *,
    repository: str,
    candidate_hash: str,
    source_revision: str,
    policy_version: str,
) -> str | None:
    """Why the committed ``PULL_REQUEST.md`` is not the text this run would post, or None."""
    expected = pull_request_text(
        compose_correction_pull_request(
            bundle=directory,
            repository=repository,
            candidate_hash=candidate_hash,
            source_revision=source_revision,
            policy_version=policy_version,
        )
    )
    try:
        committed = (directory / PULL_REQUEST_NAME).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"{PULL_REQUEST_NAME} cannot be read: {exc}"
    if committed != expected:
        return (
            f"{PULL_REQUEST_NAME} is not the pull request text this bundle composes now: "
            "re-assemble the correction run so the reviewed text is the posted text"
        )
    return None
