"""Verified facts the renderer's Dependencies section has no line for.

The renderer prints a dependency section from the dependency facts and the ecosystem's floor fact.
The C++ extractor also records the lowest CMake the project accepts (``package:cmake_minimum``),
which the review of the first correction bundles asked for: a reader building from source needs it
beside the C++ standard. It is added here as one more entry of "Native and System Requirements",
only when the README does not already state it.
"""

from __future__ import annotations

import re

from repository_presenter.components.readme_correction.model import Context

CMAKE_FACT_ID = "package:cmake_minimum"
_GROUP = "### Native and System Requirements"


def augment_dependencies(ctx: Context, body: str) -> str:
    """``body`` (a rendered Dependencies section or group set) with the CMake minimum added."""
    cmake = ctx.supported(CMAKE_FACT_ID)
    if cmake is None or not body:
        return body
    stated = re.search(rf"(?i)cmake[^\n]{{0,40}}{re.escape(cmake.value)}", ctx.readme + "\n" + body)
    if stated is not None:
        return body
    bullet = f"- Requires CMake {cmake.value} or later."
    lines = body.splitlines()
    if _GROUP not in lines:
        return body + "\n\n" + _GROUP + "\n\n" + bullet
    start = lines.index(_GROUP) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("### ")), len(lines))
    while end > start and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, bullet)
    return "\n".join(lines)
