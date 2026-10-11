"""The real-render record of the diagrams a correction redraws, kept in the bundle.

When a renderer is installed (``RP_MERMAID_TOOLS`` and a node, see ``readme_diagram.render_check``)
each redrawn diagram is drawn in a headless browser on every installed Mermaid release, natively and
in five wider fonts, and the verdict is recorded under ``render_check`` in ``corrections.json``: the
releases, whether it is horizontal on all of them, how many labels clip, how many words split across
two lines, and any other problem the check finds. When there is no renderer the record says so, and
the pull request text then claims nothing about it. The record is metadata of the run: it takes no
part in what the edits are, so the gate that re-derives the edits does not read it.
"""

from __future__ import annotations

from typing import Any

from repository_presenter.components.readme_correction.model import DIAGRAM_FIX, CorrectionResult
from repository_presenter.components.readme_diagram import render_check as check
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse


def measure_diagrams(result: CorrectionResult) -> dict[str, Any] | None:
    """The ``render_check`` record of the redrawn diagrams of ``result``, or None when it redraws
    none."""
    bodies = [e.replacement.replace("\r\n", "\n") for e in result.edits if e.kind == DIAGRAM_FIX]
    if not bodies:
        return None
    renderer = check.find_renderer()
    if renderer is None:
        return {"status": "not_run", "reason": "no renderer installed (RP_MERMAID_TOOLS, node)"}
    try:
        glances = [parse(body).glance for body in bodies]
    except NotAGlanceError as exc:
        return {"status": "not_run", "reason": f"a redrawn diagram does not parse: {exc}"}
    sources = {f"d{n}": body for n, body in enumerate(bodies)}
    releases: list[str] = []
    diagrams: list[dict[str, Any]] = [
        {"horizontal": True, "clipped_fonts": 0, "word_splits": 0, "problems": 0} for _ in bodies
    ]
    packages = check.installed_packages(renderer)
    if not packages:
        return {
            "status": "not_run",
            "reason": "no Mermaid release is installed in the tool directory",
        }
    browser = ""
    for package in packages:
        run = check.measure(renderer, sources, package=package)
        releases.append(run.mermaid)
        browser = run.browser
        for n, glance in enumerate(glances):
            entry = run.entries[f"d{n}"]
            record = diagrams[n]
            if entry.get("error"):
                record["problems"] += 1
                continue
            record["horizontal"] = record["horizontal"] and check.orientation(entry) == "horizontal"
            record["clipped_fonts"] = max(
                record["clipped_fonts"], sum(1 for c in check.clipped_fonts(entry).values() if c)
            )
            record["word_splits"] += len(check._split_failures(entry, glance))
            record["problems"] += len(
                check.check_entry(entry, glance, columns_in_order=not package.endswith("12_1_0"))
            )
    return {
        "status": "verified",
        "releases": releases,
        "fonts": 1 + len(check.STRESS_FONTS),
        "diagrams": diagrams,
        "browser": browser,
    }
