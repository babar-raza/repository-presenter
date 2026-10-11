"""Driving an npm package's own build in a disposable copy, and the run directory it needs.

`RESEARCH_AND_GUIDELINES.md` §7.4 and §29.6 E5. Every npm plugin's verifier needs the same four
things around its own check - an `npm` this machine offers, an empty run directory, a copy of the
checkout it can install into, and a receipt that never carries the developer's paths - so they sit
here, shared, and the TypeScript and Node.js verifiers each keep only what is theirs: how a
snippet is checked. Nothing here names a language.

A toolchain this machine lacks is `NOT_VERIFIED`, which the facts stage records as `UNRESOLVED` -
never `CONTRADICTED`, because "we could not check" is not "we checked and it is false".
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.components.readme.extractors.surface.npm_package import read_json
from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt, MeasuredBuild
from repository_presenter.core.execution import execute, profile_environment
from repository_presenter.core.toolchains import resolve_tool

MAX_OUTPUT_CHARS = 4000
_WORKSPACE_ATTEMPTS = 5
# Where the package's own build is driven: a copy of the checkout under the run workspace, because
# the clone is read-only and `npm install` writes a lockfile and `node_modules` into the tree.
PRODUCT_DIRECTORY = "rp_product_build"
# What the copy leaves behind: version control, and whatever an earlier install put there.
_NOT_COPIED = (".git", "node_modules")


def clip(text: str) -> str:
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + "..."


def blocked(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
    """One `NOT_VERIFIED` receipt per candidate, all saying why nothing was checked."""
    return [
        ExampleReceipt(
            ordinal=candidate.ordinal,
            outcome="NOT_VERIFIED",
            return_code=None,
            stdout="",
            stderr="",
            detail=detail,
            fixtures=(),
        )
        for candidate in candidates
    ]


def fresh_workspace(workspace: Path) -> Path | None:
    """An empty run directory, even when Windows will not let the last one go.

    The same rule the .NET verifier needs: this checkout is on OneDrive, which holds handles, and
    failing to clean scratch space must never cost a repository its candidate.
    """
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def scrub(text: str, workspace: Path) -> str:
    """This machine's paths out of a tool's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home directory
    must not appear in it - and a path that differs per machine would move a sealed candidate's
    bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {workspace, workspace.resolve()}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def npm_executable() -> str | None:
    """`npm` as this machine offers it, or None when it offers none.

    Resolved the way `typescript_compiler` resolves `tsc`: by `which` (the `.cmd` shim first on
    Windows, where the bare `npm` is a shell script CreateProcess cannot run), then by the
    toolchain registry, then beside whichever `node` is found - nothing is added to `PATH`.
    """
    names = ("npm.cmd", "npm") if os.name == "nt" else ("npm",)
    found = resolve_tool("npm")
    if found:
        return found
    node = resolve_tool("node")
    if node:
        for candidate in names:
            sibling = Path(node).with_name(candidate)
            if sibling.is_file():
                return str(sibling)
    return None


def build_product(
    root: Path, workspace: Path, npm: str | None, timeout_seconds: float
) -> MeasuredBuild:
    """Drive the manifest's own build in a copy of the checkout and say exactly what exited 0.

    Lane B's measurement (RESEARCH_LANE_B 617-645) is why nothing here is a template: `npm
    install`, then `npm run build` only when `package.json` declares `scripts.build`. Aspose.3D
    for TypeScript declares one and both steps exit 0; Aspose.Cells declares none and its own
    sources do not compile (`npx tsc --noEmit` exits 2), so the honest command for it is the
    install alone and the receipt says nothing was compiled. A checked example proves none of
    this - the snippet is checked against the sources, not against a build - which is why the
    receipt's `build_verified` and `build_command` are read from here (cpp_examples.py's
    `build_product` is the same shape for CMake).
    """
    if npm is None:
        return MeasuredBuild(False, "", "not attempted (no npm on this machine)")
    copy = workspace / PRODUCT_DIRECTORY
    try:
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns(*_NOT_COPIED), dirs_exist_ok=True)
    except OSError as error:
        # The error's text would carry this machine's paths into a receipt; its class does not.
        return MeasuredBuild(
            False, "", f"not attempted (the sources would not copy: {type(error).__name__})"
        )
    scripts = read_json(copy / "package.json").get("scripts")
    declares_build = isinstance(scripts, dict) and bool(scripts.get("build"))
    steps: list[tuple[str, ...]] = [("install",)]
    if declares_build:
        steps.append(("run", "build"))
    environment = profile_environment(workspace)
    ran: list[str] = []
    for step in steps:
        spelled = " ".join(("npm", *step))
        result = execute(
            [npm, *step],
            workspace=copy,
            timeout_seconds=timeout_seconds,
            extra_environment=environment,
        )
        after = f" after {' and '.join(f'`{done}` exited 0' for done in ran)}" if ran else ""
        if result.timed_out:
            return MeasuredBuild(
                False, "", f"failed (`{spelled}` did not exit within {timeout_seconds:g}s{after})"
            )
        if result.return_code != 0:
            return MeasuredBuild(
                False, "", f"failed (`{spelled}` exited {result.return_code}{after})"
            )
        ran.append(spelled)
    proven = "; ".join(f"`{done}` exited 0" for done in ran)
    aside = (
        "" if declares_build else "; the manifest declares no build script, so nothing was compiled"
    )
    return MeasuredBuild(True, "\n".join(ran), f"succeeded ({proven}{aside})")


def verify_package_build(
    package: Path, workspace: Path, npm: str | None, timeout_seconds: float
) -> MeasuredBuild:
    """The package's own npm build, measured whether or not any README example exists.

    The one rule for an npm install claim the registry does not confirm
    (`evidence/facts/extract.py`, the same rule `net_examples.verify_net_build` applies to NuGet).
    A README snippet that fails is that snippet's defect, and a repository with no snippet has no
    receipt to read at all, so the build is driven here, once, on its own fresh run directory -
    never the examples' workspace.
    """
    fresh = fresh_workspace(workspace)
    if fresh is None:
        return MeasuredBuild(False, "", "not attempted (no clean workspace to build in)")
    return build_product(package, fresh, npm, timeout_seconds)
