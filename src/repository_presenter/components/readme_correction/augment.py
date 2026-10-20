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


#: A floor row whose value is a ``;``-joined MSBuild ``TargetFrameworks`` list.
_MULTI_TARGET_ROW = re.compile(
    r"^- Requires [^`\n]+`(?P<value>[^`\n;]+(?:;[^`\n;]+)+)`(?P<rest>.*)$"
)


def split_targets(body: str) -> str:
    """``body`` with each ``Requires .NET `a;b``` row rewritten as ``Targets a and b.``: the project
    file's list of frameworks it builds for, not frameworks a consumer must all have. The names stay
    plain text: BC-04 accepts a code span only when it is a whole fact value or a line the
    renderer wrote, and a single framework is neither."""
    lines = []
    for line in body.splitlines():
        match = _MULTI_TARGET_ROW.match(line)
        if match is not None:
            names = [name.strip() for name in match.group("value").split(";") if name.strip()]
            joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
            line = f"- Targets {joined}{match.group('rest')}"
        lines.append(line)
    text = "\n".join(lines)
    return text + "\n" if body.endswith("\n") else text


def augment_dependencies(ctx: Context, body: str) -> str:
    """``body`` (a rendered Dependencies section) without a CMake minimum row the README states,
    and with a list of target frameworks stated as the list it is."""
    return _without_stated_cmake(ctx, split_targets(body) if ctx.requirements_v2 else body)


def _without_stated_cmake(ctx: Context, body: str) -> str:
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
