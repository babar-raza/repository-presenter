"""``python -m repository_presenter.components.readme_diagram``: look at, repair and prove an At a
Glance diagram in README files, without a model call or a network read.

    lint        README...                 every defect of each diagram (exit 1 when any)
    rebuild     [--write] README...       the canonical drawing of the same content
    render-check [--package P] README...  the real-render verdict on each diagram, before and after
                                          (needs RP_MERMAID_TOOLS; see ``render_check.py``)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repository_presenter.components.readme_diagram.lint import lint_source
from repository_presenter.components.readme_diagram.model import NotAGlanceError
from repository_presenter.components.readme_diagram.parse import parse
from repository_presenter.components.readme_diagram.rebuild import (
    mermaid_fences,
    rebuild_body,
    rebuild_readme,
)


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _lint(paths: list[Path]) -> int:
    failing = 0
    for path in paths:
        lines = _read(path).splitlines(keepends=True)
        for fence in mermaid_fences(lines):
            report = lint_source(fence.body)
            where = f"{path}:{fence.first + 1}"
            if not report.recognized:
                print(f"{where}: not an At a Glance chain ({report.defects[0].detail})")
                continue
            if report.conforming:
                print(f"{where}: conforming")
                continue
            failing += 1
            for defect in report.defects:
                print(f"{where}: {defect.code}: {defect.detail}")
            for advisory in report.advisories:
                print(f"{where}: advisory {advisory.code}: {advisory.detail}")
    return 1 if failing else 0


def _rebuild(paths: list[Path], write: bool) -> int:
    for path in paths:
        text = _read(path)
        rebuilt = rebuild_readme(text)
        for change in rebuilt.changes:
            codes = ", ".join(sorted(change.report.codes))
            print(f"{path}:{change.first_line}: rebuilt ({codes})")
        for number, reason in rebuilt.skipped:
            print(f"{path}:{number}: left alone ({reason})")
        if not rebuilt.changes:
            print(f"{path}: nothing to rebuild")
        elif write:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(rebuilt.text)
    return 0


def _render_check(paths: list[Path], package: str) -> int:
    from repository_presenter.components.readme_diagram import render_check as check

    renderer = check.find_renderer()
    if renderer is None:
        print("no renderer: set RP_MERMAID_TOOLS (npm ci in render/) and put node on PATH")
        return 2
    sources: dict[str, str] = {}
    meanings = {}
    for path in paths:
        for fence in mermaid_fences(_read(path).splitlines(keepends=True)):
            try:
                glance = parse(fence.body).glance
            except NotAGlanceError:
                continue
            key = f"{path}:{fence.first + 1}"
            sources[f"{key} before"] = fence.body
            sources[f"{key} after"] = rebuild_body(fence.body)
            meanings[key] = glance
    run = check.measure(renderer, sources, package=package)
    print(f"mermaid {run.mermaid} in {run.browser}")
    failed = 0
    for key, glance in meanings.items():
        for phase in ("before", "after"):
            entry = run.entries[f"{key} {phase}"]
            problems = check.check_entry(
                entry, glance, columns_in_order=not package.endswith("12_1_0")
            )
            failed += bool(problems) and phase == "after"
            fonts = check.clipped_fonts(entry) if not entry.get("error") else {}
            shape = check.orientation(entry) if not entry.get("error") else "error"
            print(
                f"{key} {phase}: {shape}, clipped in {sum(1 for n in fonts.values() if n)} of "
                f"{len(fonts)} fonts, {len(problems)} problem(s)"
            )
            for problem in problems[:3] if phase == "after" else []:
                print(f"    {problem}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="readme_diagram", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("lint", "rebuild", "render-check"):
        sub = commands.add_parser(name)
        sub.add_argument("paths", nargs="+", type=Path)
        if name == "rebuild":
            sub.add_argument("--write", action="store_true")
        if name == "render-check":
            sub.add_argument("--package", default="mermaid")
    args = parser.parse_args(argv)
    if args.command == "lint":
        return _lint(args.paths)
    if args.command == "rebuild":
        return _rebuild(args.paths, args.write)
    return _render_check(args.paths, args.package)


if __name__ == "__main__":
    sys.exit(main())
