"""Prompt hygiene, enforced structurally: prompt text lives only in manifests, loaded only once.

Ported from the legacy prompt source audit as a CI-time check rather than a runtime module: no
production stage consumes an audit report, so the rules are asserted here against the syntax tree
of every module under src/.
"""

from __future__ import annotations

import ast
from pathlib import Path

from repository_presenter.core.llm.prompts import JOB_IDS
from support import REPO_ROOT

PACKAGE = REPO_ROOT / "src" / "repository_presenter"
_ROLES = {"system", "user", "assistant"}


def _modules() -> list[tuple[str, ast.Module]]:
    modules = []
    for path in sorted(PACKAGE.rglob("*.py")):
        relative = path.relative_to(PACKAGE).as_posix()
        modules.append((relative, ast.parse(path.read_text(encoding="utf-8"), filename=relative)))
    return modules


def _string_keys(node: ast.Dict) -> dict[str, ast.expr]:
    return {
        key.value: value
        for key, value in zip(node.keys, node.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }


def inline_message_literals() -> list[str]:
    """Every chat message built in code whose content is a literal rather than manifest text."""
    found: list[str] = []
    for relative, tree in _modules():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            values = _string_keys(node)
            role = values.get("role")
            content = values.get("content")
            if (
                isinstance(role, ast.Constant)
                and role.value in _ROLES
                and isinstance(content, ast.Constant | ast.JoinedStr | ast.BinOp)
            ):
                found.append(f"{relative}:{node.lineno}")
    return found


def string_constants(tree: ast.Module) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_no_prompt_text_lives_in_code() -> None:
    assert inline_message_literals() == []


def test_only_the_registry_reads_the_manifest_directory() -> None:
    readers = sorted(relative for relative, tree in _modules() if ".yaml" in string_constants(tree))
    assert readers == ["core/llm/prompts.py"]
    yaml_readers = sorted(
        relative
        for relative, tree in _modules()
        if any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "yaml"
            for node in ast.walk(tree)
        )
    )
    assert yaml_readers == ["core/llm/prompts.py", "cursor.py"]


def test_code_names_only_governed_jobs() -> None:
    job_like = {
        constant
        for _, tree in _modules()
        for constant in string_constants(tree)
        if constant.endswith(
            ("_investigation", "_reconciliation", "_planning", "_authoring", "_review", "_repair")
        )
    }
    assert job_like <= set(JOB_IDS)
    assert "repository_investigation" in job_like


def test_the_manifest_tree_is_flat_and_complete() -> None:
    names = sorted(path.name for path in (REPO_ROOT / "prompts").iterdir())
    assert names == sorted(f"{job}.yaml" for job in JOB_IDS)
    assert not any(path.is_dir() for path in (REPO_ROOT / "prompts").iterdir())
    assert Path(REPO_ROOT / "prompts").is_dir()
