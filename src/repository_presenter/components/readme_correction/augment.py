"""Keep the rendered Dependencies section from repeating what the README already states.

The renderer prints a dependency section from the dependency facts and the ecosystem's floor and
build-tool facts, including the lowest CMake the project accepts (``package:cmake_minimum``, which
the independent review of the first correction bundles asked for). A reader of the maintainers'
README does not need it twice, so when the README already states that minimum the row is dropped
from the inserted section (the redundancy rule), and a requirements group left empty loses its
heading.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme_correction.model import Context

CMAKE_FACT_ID = "package:cmake_minimum"
_GROUP = "### Native and System Requirements"


def augment_dependencies(ctx: Context, body: str) -> str:
    """``body`` (a rendered Dependencies section) without a CMake minimum row the README states."""
    cmake = ctx.supported(CMAKE_FACT_ID)
    if cmake is None or not body:
        return body
    version = re.escape(cmake.value)
    if re.search(rf"(?i)cmake[^\n]{{0,40}}{version}", ctx.readme) is None:
        return body
    row = re.compile(rf"^- Requires CMake {version}(?: or later)?\b")
    lines = [line for line in body.splitlines() if not row.match(line)]
    if _GROUP in lines:
        start = lines.index(_GROUP) + 1
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("#")), len(lines))
        if not any(line.strip() for line in lines[start:end]):
            del lines[start - 1 : end]
    text = "\n".join(lines)
    return text + "\n" if body.endswith("\n") else text
