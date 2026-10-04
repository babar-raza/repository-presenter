"""The Java verifier resolves its compiler from the machine's record, never from the shell's PATH.

Measured 2026-10-04 on this machine: `javac` is absent from the shell's PATH while a JDK 21 is
installed under `D:\\Program Files\\Eclipse Adoptium`, so the same present run executed examples in
one shell and reported BLOCKED_TOOLCHAIN in another. These tests fake only the subprocess itself;
the resolution, the version capture and the receipts are the production code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.platforms import java_examples
from repository_presenter.core import toolchains
from repository_presenter.core.examples import ExampleCandidate
from repository_presenter.core.execution import ExecutionResult
from repository_presenter.core.toolchains import REGISTRY_VARIABLE

WIDGET = 'package org.x;\n\npublic class Widget {\n    public String name() { return "w"; }\n}\n'


def _source_root(root: Path) -> Path:
    source = root / "src" / "org" / "x"
    source.mkdir(parents=True)
    (source / "Widget.java").write_text(WIDGET, encoding="utf-8", newline="\n")
    return root / "src"


def _javac(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


class _FakeJavac:
    """Stands in for `execute`: every javac call succeeds and is recorded for inspection."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        argv: list[str],
        *,
        workspace: Path,
        timeout_seconds: float,
        extra_environment: dict[str, str] | None = None,
        **_: Any,
    ) -> ExecutionResult:
        self.calls.append({"argv": list(argv), "environment": dict(extra_environment or {})})
        return ExecutionResult(
            argv=tuple(argv),
            return_code=0,
            stdout="javac 21.0.11\n" if "-version" in argv else "",
            stderr="",
            timed_out=False,
        )


def _candidates() -> list[ExampleCandidate]:
    return [ExampleCandidate(1, "java", "new Widget().name();", "README.md", 1, 3, "unit:001")]


@pytest.fixture
def isolated_machine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """An empty PATH, no registry file, and no installed JDK anywhere but what a test places."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv(REGISTRY_VARIABLE, str(tmp_path / "absent-registry.txt"))
    monkeypatch.setattr(toolchains, "_install_roots", lambda: (tmp_path / "no-install",))
    return tmp_path


def test_javac_absent_from_path_but_recorded_is_executed_not_blocked(
    isolated_machine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = isolated_machine
    recorded = _javac(tmp_path / "jdk21" / "bin" / "javac.exe")
    registry = tmp_path / "rp-toolchains" / "TOOLCHAIN_PATHS.txt"
    registry.parent.mkdir()
    registry.write_text(f"javac={recorded}\n", encoding="utf-8", newline="\n")
    monkeypatch.setenv(REGISTRY_VARIABLE, str(registry))
    fake = _FakeJavac()
    monkeypatch.setattr(java_examples, "execute", fake)
    system_path = os.environ["PATH"]

    receipts = java_examples.verify_java_examples(
        _source_root(tmp_path / "product"), "17", False, (), _candidates(), tmp_path / "run", 60.0
    )

    assert [receipt.outcome for receipt in receipts] == ["EXECUTED"]
    assert not any("BLOCKED_TOOLCHAIN" in receipt.detail for receipt in receipts)
    assert "javac 21.0.11" in receipts[0].detail
    assert fake.calls and all(call["argv"][0] == str(recorded) for call in fake.calls)
    # The subprocess PATH carries the JDK's own directory; the process's PATH is untouched.
    for call in fake.calls:
        assert call["environment"]["PATH"].split(os.pathsep)[0] == str(recorded.parent)
    assert os.environ["PATH"] == system_path


def test_javac_found_by_the_install_search_is_executed_not_blocked(
    isolated_machine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = isolated_machine
    installed = _javac(
        tmp_path
        / "no-install"
        / "Eclipse Adoptium"
        / "jdk-21.0.11.10-hotspot"
        / "bin"
        / "javac.exe"
    )
    monkeypatch.setattr(toolchains, "_install_roots", lambda: (tmp_path / "no-install",))
    fake = _FakeJavac()
    monkeypatch.setattr(java_examples, "execute", fake)

    receipts = java_examples.verify_java_examples(
        _source_root(tmp_path / "product"), "17", False, (), _candidates(), tmp_path / "run", 60.0
    )

    assert [receipt.outcome for receipt in receipts] == ["EXECUTED"]
    assert fake.calls and all(call["argv"][0] == str(installed) for call in fake.calls)


def test_no_jdk_anywhere_still_reports_blocked_toolchain(
    isolated_machine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: no compiler recorded or installed means no compiler invented."""
    fake = _FakeJavac()
    monkeypatch.setattr(java_examples, "execute", fake)

    receipts = java_examples.verify_java_examples(
        _source_root(isolated_machine / "product"),
        "17",
        False,
        (),
        _candidates(),
        isolated_machine / "run",
        60.0,
    )

    assert [receipt.outcome for receipt in receipts] == ["NOT_VERIFIED"]
    assert receipts[0].detail == "BLOCKED_TOOLCHAIN: no Java compiler on this machine"
    assert fake.calls == []
