"""The repository files an inherited README unit names, each checked against the pinned tree.

A README says "see CONTRIBUTING.md", "the samples are basic.rs and charts.rs", "run
_examples/<name>/main.go". Those are file names, and a file name is a dotted token that the
authoring gate's identifier rule (``composition.authoring.identifier_tokens``) reads as an
identifier no fact records: a faithful sentence carrying the upstream's own file reference was
refused twice and the section stopped (aspose-slides-foss/Aspose.Slides-FOSS-for-.NET,
CONTRIBUTING.md and SECURITY.md; aspose-cells-foss/Aspose.Cells-FOSS-for-Rust, basic.rs and
twelve other samples; aspose-pdf-foss/Aspose-PDF-FOSS-for-Go, examples_test.go and main.go - the
2026-10-09 re-seal transactions, docs/DEFECT_INDEX.md
"readme.dotted_file_name_in_prose_not_a_recorded_fact").

The cause sits here, at extraction, not in the identifier rule: the tree inventory the extractor
already holds proves the file exists at the pinned revision, but no fact recorded it, so the rule
had nothing to accept. This module closes that gap without loosening the rule and without a new
fact kind (the kind enum is closed by schemas/facts.schema.json): an ``inherited_unit`` fact
records, in ``attributes["repository_files"]``, each file name its own text spells that the tree
contains. ``authoring.allowed_identifiers`` reads it, so the guard, the renderer's code spans and
BC-04 accept exactly these names and no others.

The match is exact and case-sensitive, and only against the tree:

- a name the README spells that the tree does not contain (a removed file, a file on another
  branch or revision, a typo) is not recorded, so prose cannot assert it;
- ``AGENTS.md`` is not ``agents.md``: a name differing in case is another name;
- a bare name (``basic.rs``) is recorded when any tree path ends in it, since the README lists
  files by the name a reader sees inside a directory it has just named; a name written with a
  directory (``docs/guide.md``, ``.github/workflows/pages.yml``) must match the end of a tree path
  on a directory boundary;
- a name written with a directory is recorded in both forms, the path as spelled and its final
  segment, because prose paraphrasing ``_examples/<name>/main.go`` says ``main.go``.

- a project name (CUT-2, BC-12): the README names a build target without its extension ("the test
  project `Aspose.Pdf.Foss.Tests`", "the Aspose.GIS.FOSS.Tests/ directory"). The name is recorded
  when it is the stem of a project or solution file in the tree
  (``tests/Aspose.Pdf.Foss.Tests.csproj``) or the name of a directory in it, by exact,
  case-sensitive match. A source file's stem is not a project (``Scene.cs``), and a stem that is
  only the prefix of a longer project's name is not that project. Left unrecorded, the name was a
  bare proper noun in prose that BC-12 read as a short spelling of the product (its
  ``Aspose.Pdf.Foss`` head), and the repair loop could not fix it
  (aspose-pdf-foss/Aspose.PDF-FOSS-for-.NET, 2026-10-10 baseline); recorded,
  ``authoring.allowed_identifiers`` admits it, so the renderer wraps it in a code span, which
  BC-12 does not judge.

A URL is removed before scanning, so ``https://github.com/o/r/blob/main/SECURITY.md`` contributes
nothing and the link text ``SECURITY.md`` does; a link target the tree resolves is recorded as the
README wrote it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

# A path-like token: optional ./ or ../, directory segments, and a final segment with an extension
# of one to eight characters opening with a letter (.md, .rs, .go, .yml, .csproj, not .5 or 1.2).
# Segments allow a leading dot (.github) and the characters a repository file name uses.
_FILE_TOKEN = re.compile(
    r"(?<![\w.\-])"
    r"((?:\.{1,2}/)?(?:[\w.\-]+/)*[\w\-][\w.\-]*\.[A-Za-z][A-Za-z0-9]{0,7})"
    r"(?![\w\-]|\.[A-Za-z0-9])"
)
# A dotted name as a whole word (``Aspose.Pdf.Foss.Tests``), not a prefix of a longer one or of a
# file name (``Aspose.Pdf.Foss.Tests.csproj``): a project is named without its extension.
_DOTTED_NAME = re.compile(r"(?<![\w.\-/])\w+(?:\.\w+)+(?![\w\-]|\.\w)")
_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s)>\]\"']+")
# A placeholder segment (``_examples/<name>/main.go``) splits a path; the file after it counts.
_PLACEHOLDER = re.compile(r"<[\w\-]+>")


# The files that name a build target: the stem of one is a project's name.
_PROJECT_EXTENSIONS = frozenset(
    {".csproj", ".vbproj", ".fsproj", ".vcxproj", ".vcproj", ".pyproj", ".sln", ".slnx"}
)


class TreeIndex(NamedTuple):
    """The tree's full paths, its final path segments and its project names, built once per
    extraction. ``projects`` holds the stem of each project or solution file and the name of each
    directory (every path segment before the last)."""

    paths: frozenset[str]
    names: frozenset[str]
    projects: frozenset[str] = frozenset()


def tree_index(tree_paths: Iterable[str]) -> TreeIndex:
    paths = frozenset(tree_paths)
    projects: set[str] = set()
    for path in paths:
        *directories, final = path.split("/")
        projects.update(directory for directory in directories if "." in directory)
        stem, dot, extension = final.rpartition(".")
        if dot and f".{extension.lower()}" in _PROJECT_EXTENSIONS:
            projects.add(stem)
    names = frozenset(path.rsplit("/", 1)[-1] for path in paths)
    return TreeIndex(paths, names, frozenset(projects))


def repository_files(text: str, index: TreeIndex) -> list[str]:
    """The file names ``text`` spells that the indexed tree contains, sorted and distinct."""
    if not index.paths:
        return []
    found: set[str] = set()
    prose = _PLACEHOLDER.sub(" ", _URL.sub(" ", text))
    if index.projects:
        found.update(
            match.group(0)
            for match in _DOTTED_NAME.finditer(prose)
            if match.group(0) in index.projects
        )
    for match in _FILE_TOKEN.finditer(prose):
        token = match.group(1)
        while token.startswith("./"):
            token = token[2:]
        if not token or token.startswith("../"):
            continue
        name = token.rsplit("/", 1)[-1]
        if "/" not in token:
            resolved = token in index.names
        else:
            resolved = token in index.paths or any(
                path.endswith("/" + token) for path in index.paths
            )
        if resolved:
            found.add(token)
            found.add(name)
    return sorted(found)
