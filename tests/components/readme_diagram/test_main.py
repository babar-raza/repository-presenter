"""The command line over README files: lint, rebuild, and the renderer's absence."""

from __future__ import annotations

from pathlib import Path

import pytest

from repository_presenter.components.readme_diagram.__main__ import main

DIAGRAM = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing XLSX workbook"]
  end
  PRODUCT["Aspose.Cells FOSS for Go"]
  subgraph Capabilities["Core Capabilities"]
    direction TB
    c1["Cell read and write"]
    c2["Font, fill, and border styling"]
    c3["CSV import and export"]
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["XLSX workbooks"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""


def write(tmp_path: Path, text: str, name: str = "README.md") -> Path:
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return path


def test_lint_reports_each_defect_and_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, f"# T\n\n```mermaid\n{DIAGRAM}```\n")
    assert main(["lint", str(path)]) == 1
    out = capsys.readouterr().out
    assert f"{path}:4: ORIENTATION_VERTICAL" in out
    assert "CLIP_HTML_LABELS" in out


def test_lint_exits_zero_for_a_conforming_diagram_and_a_readme_without_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path, f"# T\n\n```mermaid\n{DIAGRAM}```\n")
    assert main(["rebuild", "--write", str(path)]) == 0
    capsys.readouterr()
    assert main(["lint", str(path)]) == 0
    assert "conforming" in capsys.readouterr().out
    plain = write(tmp_path, "# Only text\n", "PLAIN.md")
    assert main(["lint", str(plain)]) == 0


def test_rebuild_without_write_changes_nothing_and_with_write_keeps_line_endings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = f"# T\r\n\r\n```mermaid\r\n{DIAGRAM.replace(chr(10), chr(13) + chr(10))}```\r\n"
    path = write(tmp_path, text)
    assert main(["rebuild", str(path)]) == 0
    assert path.read_bytes() == text.encode("utf-8")
    assert "rebuilt (" in capsys.readouterr().out
    assert main(["rebuild", "--write", str(path)]) == 0
    written = path.read_bytes().decode("utf-8")
    assert "flowchart LR" in written and written.startswith("# T\r\n\r\n```mermaid\r\n")
    assert "\n" not in written.replace("\r\n", "")
    assert main(["rebuild", "--write", str(path)]) == 0
    assert "nothing to rebuild" in capsys.readouterr().out


def test_a_mermaid_fence_that_is_not_an_at_a_glance_chain_is_reported_not_rewritten(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "```mermaid\nsequenceDiagram\n  A->>B: hi\n```\n"
    path = write(tmp_path, text)
    assert main(["lint", str(path)]) == 0
    assert "not an At a Glance chain" in capsys.readouterr().out
    assert main(["rebuild", "--write", str(path)]) == 0
    assert path.read_text(encoding="utf-8") == text


def test_render_check_without_an_installed_renderer_says_so_and_exits_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RP_MERMAID_TOOLS", raising=False)
    path = write(tmp_path, f"```mermaid\n{DIAGRAM}```\n")
    assert main(["render-check", str(path)]) == 2
    assert "no renderer" in capsys.readouterr().out
