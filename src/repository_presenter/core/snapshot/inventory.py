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
# Directories a repository conventionally keeps its own licence in when it has none at the root
# (``License/LICENSE.txt`` in the Aspose cells repositories, the REUSE layout's ``LICENSES/``).
# Only these: ``docs/``, ``third_party/`` and ``legal/`` hold other people's licences.
LICENSE_DIRECTORIES = frozenset({"license", "licenses", "licence", "licences"})
# A REUSE-style licence file is named for its SPDX identifier (``LICENSES/MIT.txt``). Only the
# identifiers the license-text classifier knows, plus the other common ones.
_SPDX_NAMED_LICENSE = re.compile(
    r"^(?:mit|isc|0bsd|unlicense|apache-2\.0|bsd-[23]-clause|mpl-2\.0|cc0-1\.0"
    r"|[al]?gpl-[23]\.[01](?:-only|-or-later)?)(?:\.txt|\.md)?$",
    re.IGNORECASE,
)
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


def _license_directories(root: Path) -> list[Path]:
    """The conventionally named licence directories directly under ``root``, in name order."""
    if not root.is_dir():
        return []
    return [
        entry
        for entry in sorted(root.iterdir(), key=lambda p: p.name)
        if entry.is_dir() and entry.name.lower() in LICENSE_DIRECTORIES
    ]


def _find_license_in(directory: Path) -> Path | None:
    """A licence file named as a licence, else the one file named for an SPDX identifier.

    Two identifier-named files (``MIT.txt`` and ``Apache-2.0.txt``) may be a dual licence or a
    bundled dependency's, so none is taken for the project's own."""
    named = _find_case_insensitive(directory, LICENSE_FILENAMES)
    if named is not None:
        return named
    spdx_named = [
        entry
        for entry in sorted(directory.iterdir(), key=lambda p: p.name)
        if entry.is_file() and _SPDX_NAMED_LICENSE.match(entry.name)
    ]
    return spdx_named[0] if len(spdx_named) == 1 else None


def scan(root: Path) -> FileInventory:
    """Inventory the root of ``root``; a licence or notices file may also sit in a licence
    directory (``License/``, ``LICENSES/``), and the path recorded is the real one."""
    readme_path = _find_case_insensitive(root, README_FILENAMES)
    license_directories = _license_directories(root)
    license_path = _find_case_insensitive(root, LICENSE_FILENAMES)
    if license_path is None:
        license_path = next(
            (found for d in license_directories if (found := _find_license_in(d)) is not None),
            None,
        )
    # A notices file beside the licence (``License/ThirdPartyNotices.txt``) is looked up by its
    # notices name only: ``license`` is not a ``NOTICES_DIRECTORIES`` entry, because
    # ``_NOTICE_BEARING_FILE`` would then take ``LICENSE.txt`` itself for the attribution.
    notices_path = (
        _find_case_insensitive(root, NOTICES_FILENAMES)
        or next(
            (
                found
                for d in license_directories
                if (found := _find_case_insensitive(d, NOTICES_FILENAMES)) is not None
            ),
            None,
        )
        or _find_covering_notices(root)
    )
    community_paths: dict[str, Path] = {}
    for canonical_name, names in COMMUNITY_FILENAMES.items():
        found = _find_case_insensitive(root, names)
        if found is not None:
            community_paths[canonical_name] = found
    return FileInventory(
        readme_path=readme_path,
        license_path=license_path,
        community_paths=community_paths,
        notices_path=notices_path,
    )
