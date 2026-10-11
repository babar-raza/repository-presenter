"""Case-insensitive detection of the README, license, and community files at a clone root.

Casing is deliberately ignored: the registry repositories disagree (``LICENSE``, ``License.txt``,
``License/LICENSE.txt``), and a case-insensitive filesystem would hide a mismatch until a Linux
runner saw it. Candidates are visited in name order so the result is the same on every host.
Manifest detection belongs to the platform plugins of the facts stage, not here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

README_FILENAMES = frozenset({"readme.md", "readme", "readme.rst", "readme.txt"})
LICENSE_FILENAMES = frozenset({"license", "license.txt", "license.md", "copying", "license.rst"})
NOTICES_FILENAMES = frozenset(
    {
        "notice",
        "notice.txt",
        "notice.md",
        "notices",
        "notices.txt",
        "notices.md",
        "third-party-notices",
        "third-party-notices.txt",
        "third-party-notices.md",
        "third_party_notices",
        "third_party_notices.txt",
        "third_party_notices.md",
        "thirdpartynotices.txt",
        "thirdpartynotices.md",
    }
)
# Notices that a repository keeps beside its main licence rather than under a notices name: a root
# file named for the bundled material it covers (``LICENSE-FONTS``, ``LICENSE_THIRD_PARTY``; never
# ``LICENSE-MIT``, which is a dual-licence project's own) or a licence or notice
# file inside a directory that holds material the project did not write (CUT-2: TeX-Python keeps
# ``LICENSE-FONTS`` at the root, PDF-Go ``fonts/LICENSE.txt`` and ``third_party/*-NOTICE.txt``). The
# README documents these as bundled-material attribution, so they are the third_party_notices
# record; without one the attribution has nowhere to render (BC-05 NOTICES_WITHOUT_RECORD).
_COVERING_LICENSE_FILE = re.compile(
    r"^licen[cs]e[-_](?:fonts?|third[-_]?party|bundled|vendor(?:ed)?|deps|dependencies|assets|data"
    r"|notices?)(?:[.]\w+)?$",
    re.IGNORECASE,
)
NOTICES_DIRECTORIES: tuple[str, ...] = (
    "third_party",
    "third-party",
    "thirdparty",
    "vendor",
    "fonts",
)
_NOTICE_BEARING_FILE = re.compile(
    r"(?:^|[-_.])(?:notices?|licen[cs]es?|copying|ofl)(?:[-_.]|$)", re.IGNORECASE
)
COMMUNITY_FILENAMES: dict[str, frozenset[str]] = {
    "CONTRIBUTING": frozenset(
        {"contributing.md", "contributing", "contributing.txt", "contributing.rst"}
    ),
    "CODE_OF_CONDUCT": frozenset(
        {"code_of_conduct.md", "code_of_conduct", "code_of_conduct.txt", "code_of_conduct.rst"}
    ),
    "SECURITY": frozenset({"security.md", "security", "security.txt", "security.rst"}),
    "SUPPORT": frozenset({"support.md", "support", "support.txt", "support.rst"}),
}


@dataclass(frozen=True)
class FileInventory:
    """Where the README, license, and community files are, if anywhere."""

    readme_path: Path | None
    license_path: Path | None
    community_paths: dict[str, Path] = field(default_factory=dict)
    notices_path: Path | None = None


def _find_case_insensitive(directory: Path, names: frozenset[str]) -> Path | None:
    if not directory.is_dir():
        return None
    for entry in sorted(directory.iterdir(), key=lambda p: p.name):
        if entry.is_file() and entry.name.lower() in names:
            return entry
    return None


def _find_covering_notices(root: Path) -> Path | None:
    """A licence or notice file kept for bundled material: a root ``LICENSE-<what>`` file first,
    then the first file inside ``NOTICES_DIRECTORIES`` (in that order) that is named a notice or a
    licence. Visited in name order, so the result is the same on every host."""
    if not root.is_dir():
        return None
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_file() and _COVERING_LICENSE_FILE.match(entry.name):
            return entry
    directories = {e.name.lower(): e for e in root.iterdir() if e.is_dir()}
    for name in NOTICES_DIRECTORIES:
        directory = directories.get(name)
        if directory is None:
            continue
        for entry in sorted(directory.iterdir(), key=lambda p: p.name):
            if entry.is_file() and _NOTICE_BEARING_FILE.search(entry.name):
                return entry
    return None


def scan(root: Path) -> FileInventory:
    """Inventory the root of ``root``; a license may also sit in a ``License`` directory."""
    readme_path = _find_case_insensitive(root, README_FILENAMES)
    license_path = _find_case_insensitive(root, LICENSE_FILENAMES)
    if license_path is None and root.is_dir():
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            if entry.is_dir() and entry.name.lower() == "license":
                license_path = _find_case_insensitive(entry, LICENSE_FILENAMES)
                if license_path is not None:
                    break
    community_paths: dict[str, Path] = {}
    for canonical_name, names in COMMUNITY_FILENAMES.items():
        found = _find_case_insensitive(root, names)
        if found is not None:
            community_paths[canonical_name] = found
    return FileInventory(
        readme_path=readme_path,
        license_path=license_path,
        community_paths=community_paths,
        notices_path=(
            _find_case_insensitive(root, NOTICES_FILENAMES) or _find_covering_notices(root)
        ),
    )
