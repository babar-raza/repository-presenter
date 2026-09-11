"""A governed source's meaning never changes without its version constant moving.

Every sealed candidate records the component and check versions it was judged under
(``dependencies.json``, ``validation.json``), and ``repository-presenter status --stale`` reads
those records against the running code's constants. That report is only true while every
meaning-affecting edit to a governed source moves its constant - a discipline that was followed
19 times and then silently skipped twice in one session (docs/CI_AND_STALENESS_ASSESSMENT.md
section 4 item 2). This is that proposal's enforcement (PHASE1/F7): a hygiene check on the code
delta itself, never a new judgment over candidate content - it reads only facts that are already
true (two git blobs and the constants in them).

Meaning is an AST fingerprint with docstrings stripped, so a comment, blank-line, formatting, or
docstring edit demands no bump (bumping on prose would mark every sealed bundle stale for
nothing); any other code change does. Two deltas are held to the rule: the last landed commit
(``HEAD~1..HEAD``) and the working tree against ``HEAD`` - the working-tree leg is what bites in
the pre-commit full run, which is exactly where the two measured skips happened. Hosted CI checks
out at depth 1, so the ``HEAD~1`` leg skips there cleanly (git context absent, per the F7 card);
the local full run and the pre-push hook are this test's venue.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

import pytest

from repository_presenter.components.readme.composition.authoring import NORMALISATION_VERSION
from repository_presenter.components.readme.composition.renderer import RENDERER_VERSION
from repository_presenter.components.readme.review.independent.review import (
    REVIEWER_LOGIC_VERSION,
)
from repository_presenter.components.readme.validation.registry import (
    BLOCKING_CHECKS,
    VALIDATOR_VERSION,
)
from repository_presenter.core.git_safety.git import run_git
from support import REPO_ROOT


@dataclass(frozen=True)
class GovernedSource:
    """One versioned component: the file whose meaning its constant governs."""

    component: str
    path: str  # repository-relative, forward slashes (git pathspec form)
    constants: tuple[str, ...]
    per_check: bool = False  # every Check(id, version, ...) literal is a constant too


GOVERNED: tuple[GovernedSource, ...] = (
    GovernedSource(
        "renderer",
        "src/repository_presenter/components/readme/composition/renderer.py",
        ("RENDERER_VERSION",),
    ),
    GovernedSource(
        "normalisation",
        "src/repository_presenter/components/readme/composition/authoring.py",
        ("NORMALISATION_VERSION",),
    ),
    GovernedSource(
        "reviewer_logic",
        "src/repository_presenter/components/readme/review/independent/review.py",
        ("REVIEWER_LOGIC_VERSION",),
    ),
    GovernedSource(
        "validator",
        "src/repository_presenter/components/readme/validation/registry.py",
        ("VALIDATOR_VERSION",),
        per_check=True,
    ),
)


def _without_docstrings(tree: ast.Module) -> ast.Module:
    """Drop every module, class, and function docstring so prose edits never count."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:]
    return tree


def meaning(text: str) -> str:
    """The code's meaning: its AST without docstrings; comments and layout are invisible."""
    return ast.dump(_without_docstrings(ast.parse(text)))


def versions(text: str, source: GovernedSource) -> dict[str, str]:
    """Every governed version value spelled in ``text``, by constant (or ``Check:<id>``) name."""
    found: dict[str, str] = {}
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in source.constants:
                    found[target.id] = str(node.value.value)
        if (
            source.per_check
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Check"
        ):
            fields: dict[str, str] = {}
            for position, name in ((0, "id"), (1, "version")):
                if len(node.args) > position:
                    argument = node.args[position]
                    if isinstance(argument, ast.Constant):
                        fields[name] = str(argument.value)
            for keyword in node.keywords:
                if keyword.arg in ("id", "version") and isinstance(keyword.value, ast.Constant):
                    fields[keyword.arg] = str(keyword.value.value)
            if "id" in fields and "version" in fields:
                found[f"Check:{fields['id']}"] = fields["version"]
    return found


def bump_violation(old_text: str, new_text: str, source: GovernedSource) -> str | None:
    """The violation message for this delta, or ``None`` when it honours the discipline."""
    new_versions = versions(new_text, source)
    assert new_versions, (
        f"no version constant found in {source.path}; the discipline test went blind - fix the"
        " extraction before trusting any of its verdicts"
    )
    if meaning(old_text) == meaning(new_text):
        return None
    if versions(old_text, source) != new_versions:
        return None
    return (
        f"{source.path} changed meaning ({source.component}) with every version constant"
        f" unchanged ({', '.join(sorted(new_versions))}); bump the constant that owns the change"
        " so sealed candidates read as stale against the new code"
        " (docs/CI_AND_STALENESS_ASSESSMENT.md section 4 item 2)"
    )


def _revision_exists(revision: str) -> bool:
    result = run_git(["rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"], cwd=REPO_ROOT)
    return result.returncode == 0


def _blob_at(revision: str, path: str) -> str | None:
    result = run_git(["show", f"{revision}:{path}"], cwd=REPO_ROOT)
    return result.stdout if result.returncode == 0 else None


@pytest.mark.parametrize("source", GOVERNED, ids=lambda source: source.component)
def test_the_last_commit_bumped_the_versions_of_what_it_changed(source: GovernedSource) -> None:
    if not _revision_exists("HEAD"):
        pytest.skip("git context absent (not a checkout)")
    if not _revision_exists("HEAD~1"):
        pytest.skip("no parent commit here (depth-1 hosted checkout, or the root commit)")
    new = _blob_at("HEAD", source.path)
    assert new is not None, f"{source.path} is not tracked at HEAD"
    old = _blob_at("HEAD~1", source.path)
    if old is None:
        return  # the file arrived whole in the last commit, carrying its own constants
    violation = bump_violation(old, new, source)
    assert violation is None, violation


@pytest.mark.parametrize("source", GOVERNED, ids=lambda source: source.component)
def test_the_working_tree_bumps_the_versions_of_what_it_changes(source: GovernedSource) -> None:
    if not _revision_exists("HEAD"):
        pytest.skip("git context absent (not a checkout)")
    old = _blob_at("HEAD", source.path)
    assert old is not None, f"{source.path} is not tracked at HEAD"
    new = (REPO_ROOT / source.path).read_text("utf-8")
    violation = bump_violation(old, new, source)
    assert violation is None, violation


def test_extraction_agrees_with_the_running_constants() -> None:
    """The verifier is verified: what the AST reading finds is what the code actually says."""
    running = {
        "renderer": {"RENDERER_VERSION": RENDERER_VERSION},
        "normalisation": {"NORMALISATION_VERSION": NORMALISATION_VERSION},
        "reviewer_logic": {"REVIEWER_LOGIC_VERSION": REVIEWER_LOGIC_VERSION},
        "validator": {
            "VALIDATOR_VERSION": VALIDATOR_VERSION,
            **{f"Check:{check.id}": check.version for check in BLOCKING_CHECKS},
        },
    }
    for source in GOVERNED:
        found = versions((REPO_ROOT / source.path).read_text("utf-8"), source)
        assert found == running[source.component], (
            f"{source.path}: the AST reading and the imported constants disagree; the discipline"
            " test went blind"
        )


SYNTHETIC = GovernedSource("synthetic", "synthetic.py", ("SYNTHETIC_VERSION",))
SYNTHETIC_OLD = (
    'SYNTHETIC_VERSION = "1"\n'
    "\n"
    "\n"
    "def judge(value: int) -> bool:\n"
    '    """Judge the value."""\n'
    "    return value > 1\n"
)


def test_a_meaning_change_without_a_bump_is_flagged() -> None:
    changed = SYNTHETIC_OLD.replace("value > 1", "value > 2")
    violation = bump_violation(SYNTHETIC_OLD, changed, SYNTHETIC)
    assert violation is not None and "SYNTHETIC_VERSION" in violation


def test_a_meaning_change_with_a_bump_passes() -> None:
    changed = SYNTHETIC_OLD.replace('"1"', '"2"').replace("value > 1", "value > 2")
    assert bump_violation(SYNTHETIC_OLD, changed, SYNTHETIC) is None


def test_comment_layout_and_docstring_edits_demand_no_bump() -> None:
    cosmetic = (
        SYNTHETIC_OLD.replace('"""Judge the value."""', '"""Judge the value harder."""').replace(
            "def judge", "# a new comment\ndef judge"
        )
        + "\n# trailing commentary\n"
    )
    assert bump_violation(SYNTHETIC_OLD, cosmetic, SYNTHETIC) is None


SYNTHETIC_REGISTRY = GovernedSource(
    "synthetic_validator", "registry.py", ("SYNTHETIC_VALIDATOR_VERSION",), per_check=True
)
SYNTHETIC_REGISTRY_OLD = (
    'SYNTHETIC_VALIDATOR_VERSION = "1"\n'
    'CHECKS = (Check("BC-01", "1", "first"), Check("BC-02", "1", "second"))\n'
    "\n"
    "\n"
    "def judge(value: int) -> int:\n"
    "    return value\n"
)


def test_a_per_check_version_move_satisfies_the_registry_delta() -> None:
    changed = SYNTHETIC_REGISTRY_OLD.replace('Check("BC-02", "1"', 'Check("BC-02", "2"').replace(
        "return value", "return value + 1"
    )
    assert bump_violation(SYNTHETIC_REGISTRY_OLD, changed, SYNTHETIC_REGISTRY) is None


def test_a_registry_meaning_change_with_no_version_move_is_flagged() -> None:
    changed = SYNTHETIC_REGISTRY_OLD.replace("return value", "return value + 1")
    assert bump_violation(SYNTHETIC_REGISTRY_OLD, changed, SYNTHETIC_REGISTRY) is not None
