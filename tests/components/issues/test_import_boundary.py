"""The issues component never imports an extractor: it reads a registry through `core/`.

`RESEARCH_AND_GUIDELINES.md` section 7.4: extraction and processing are independent, and no stage
after facts imports an extractor module directly. `components/issues/redetect.py` once imported
`extractors/platforms/python_registry.py` to replay a PyPI read; the read now goes through
`core/package_registry.py`, and this test fails if any module here takes that import back.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from support import REPO_ROOT

ISSUES = REPO_ROOT / "src" / "repository_presenter" / "components" / "issues"
EXTRACTORS = "repository_presenter.components.readme.extractors"


def imported_modules(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def extractor_imports(source: str) -> list[str]:
    return sorted(name for name in imported_modules(source) if name.startswith(EXTRACTORS))


def test_the_detector_sees_an_extractor_import() -> None:
    """Negative control: the scan is not vacuous."""
    source = (
        "from repository_presenter.components.readme.extractors.platforms.python_registry "
        "import observe_pypi\n"
    )
    assert extractor_imports(source) == [
        f"{EXTRACTORS}.platforms.python_registry",
        f"{EXTRACTORS}.platforms.python_registry.observe_pypi",
    ]
    assert extractor_imports("import repository_presenter.core.package_registry\n") == []


def test_there_are_issues_modules_to_scan() -> None:
    assert any(path.name == "redetect.py" for path in ISSUES.glob("*.py"))


@pytest.mark.parametrize("path", sorted(ISSUES.glob("*.py")), ids=lambda p: p.name)
def test_no_issues_module_imports_an_extractor(path: Path) -> None:
    assert extractor_imports(path.read_text("utf-8")) == [], (
        f"{path.name} imports an extractor module; ask `core/package_registry.py` instead"
    )
