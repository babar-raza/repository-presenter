"""Check each README example against the package's own sources, with Node, in an isolated copy.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table. A JavaScript example has no compiler to type-check it, and running it would reach for the
network the library talks to, so what this proves is what the contract can honestly claim of a
snippet that is not run: it parses (`node --check`), and everything it imports from the package -
by the published name, a subpath, or a path inside the checkout - resolves and exists, because
Node loads those imports, and only those, against the package staged where `npm install` would put
it (`node_modules/<name>`, beside the package's own installed dependencies). A named import the
package does not export is a SyntaxError from Node's own linker, which is the same refusal a
consumer's program would hit.

Four rules the outcome respects. A toolchain this machine lacks is `NOT_VERIFIED`, which the facts
stage records as `UNRESOLVED` - never `CONTRADICTED`, because "we could not check" is not "we
checked and it is false". A snippet that imports nothing from the package is `NOT_VERIFIED` too:
it parses, but nothing about *this* package was resolved, and a fragment that leans on variables an
earlier snippet defined must not read as a verified example. A package that will not load because
a module it needs is missing (an unbuilt `dist/`, an uninstalled dependency) is a fact about the
build environment, not the snippet, so it is `NOT_VERIFIED` as well. And every cache and credential
store is redirected into the run directory, with nothing added to the user's `PATH`.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.components.readme.extractors.surface.npm_build import (
    PRODUCT_DIRECTORY,
    blocked,
    build_product,
    clip,
    fresh_workspace,
    npm_executable,
    scrub,
    verify_package_build,
)
from repository_presenter.components.readme.extractors.surface.npm_package import read_json
from repository_presenter.core.examples import (
    ExampleCandidate,
    ExampleOutcome,
    ExampleReceipt,
    MeasuredBuild,
)
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment
from repository_presenter.core.toolchains import resolve_tool

# What the copy of the checkout leaves behind: version control, and whatever an earlier install put
# there. Mirrors the build copy's own rule.
_NOT_COPIED = (".git", "node_modules")
_FALLBACK_DIRECTORY = "rp_example_run"
# An ES `import` statement of a quoted module specifier, with or without a clause:
# `import { A, B as C } from "pkg"`, `import X, * as Y from 'pkg'`, `import "pkg"`.
_ESM_IMPORT = re.compile(
    r"""(?m)^[ \t]*import\s+(?:[\w$*{},\s]+?\s+from\s+)?(['"])(?P<spec>[^'"\n]+)\1[ \t]*;?"""
)
# A CommonJS binding of a required module: `const x = require("pkg")`, `const { A, B: C } = ...`.
_CJS_REQUIRE = re.compile(
    r"""(?m)^[ \t]*(?:const|let|var)\s+(?P<binding>[\w$]+|\{[^}]*\})\s*=\s*"""
    r"""require\(\s*(['"])(?P<spec>[^'"\n]+)\2\s*\)[ \t]*;?"""
)
# A statement that makes a snippet an ES module whatever else it contains.
_ESM_SYNTAX = re.compile(r"(?m)^[ \t]*(?:import|export)\b")
_USES_REQUIRE = re.compile(r"\brequire\(")
_DESTRUCTURED = re.compile(r"([\w$]+)\s*(?::\s*[\w$]+)?\s*(?:=[^,]*)?(?:,|$)")
_FIRST_LINE_CHARS = 300


def _is_commonjs(code: str) -> bool:
    """Whether the snippet is a CommonJS script: it requires a module and has no ES syntax."""
    return bool(_USES_REQUIRE.search(code)) and not _ESM_SYNTAX.search(code)


def _own(specifier: str, package: str) -> bool:
    """Whether ``specifier`` names the package under test: its name, a subpath of it, or a path."""
    if specifier.startswith("."):
        return True
    return bool(package) and (specifier == package or specifier.startswith(package + "/"))


def _own_imports(code: str, package: str, commonjs: bool) -> list[str]:
    """The snippet's own import statements of the package, verbatim, ready to be run alone."""
    if commonjs:
        return [
            match.group(0).strip()
            for match in _CJS_REQUIRE.finditer(code)
            if _own(match.group("spec"), package)
        ]
    return [
        match.group(0).strip()
        for match in _ESM_IMPORT.finditer(code)
        if _own(match.group("spec"), package)
    ]


def _property_checks(code: str, package: str) -> list[str]:
    """For each destructured `require`, a check that every name it takes exists on the module.

    An ES import of a name the package lacks is a link-time SyntaxError; destructuring a CommonJS
    module just yields `undefined`, which would let a README name a member that is not there.
    """
    checks: list[str] = []
    for index, match in enumerate(_CJS_REQUIRE.finditer(code)):
        binding = match.group("binding")
        if not _own(match.group("spec"), package) or not binding.startswith("{"):
            continue
        inner = binding[1:-1]
        # A nested pattern or a rest element names no member of the module, so it is not read.
        if any(mark in inner for mark in ("{", "[", "...")):
            continue
        names = [m.group(1) for m in _DESTRUCTURED.finditer(inner)]
        if not names:
            continue
        module = f"__rp_module_{index}"
        checks.append(f"const {module} = require({match.group('spec')!r});")
        for name in names:
            checks.append(
                f"if (!({name!r} in {module})) "
                f"throw new SyntaxError(`does not provide an export named {name}`);"
            )
    return checks


def _first_line(text: str) -> str:
    """The first line of a tool's output that says what went wrong."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(("SyntaxError", "Error", "TypeError", "ReferenceError")) or (
            "ERR_" in line
        ):
            return line[:_FIRST_LINE_CHARS]
    return lines[0][:_FIRST_LINE_CHARS] if lines else ""


def _stage(root: Path, workspace: Path, product: MeasuredBuild) -> Path | None:
    """The directory the snippets run in: a copy of the checkout with the package self-staged.

    The built copy when the package's own build succeeded (its dependencies are installed there),
    a plain copy of the checkout otherwise. Either way the package sits at
    `node_modules/<name>`, which is what `npm install <name>` gives a consumer, so a snippet that
    imports it by name resolves the way a reader's does - and a path inside the checkout resolves
    because the examples sit at the checkout's root.
    """
    built = workspace / PRODUCT_DIRECTORY
    if product.verified and built.is_dir():
        run, source = built, built
    else:
        run, source = workspace / _FALLBACK_DIRECTORY, root
        try:
            shutil.copytree(
                root, run, ignore=shutil.ignore_patterns(*_NOT_COPIED), dirs_exist_ok=True
            )
        except OSError:
            return None
    name = read_json(source / "package.json").get("name")
    if not isinstance(name, str) or not name.strip():
        return run
    target = run / "node_modules"
    for part in name.strip("/").split("/"):
        target = target / part
    if not target.exists():
        try:
            shutil.copytree(
                source, target, ignore=shutil.ignore_patterns(*_NOT_COPIED), dirs_exist_ok=True
            )
        except OSError:
            return None
    return run


def _version(node: str, run: Path) -> str:
    result = execute(
        [node, "--version"],
        workspace=run,
        timeout_seconds=60.0,
        extra_environment=profile_environment(run),
    )
    return result.stdout.strip() if result.return_code == 0 else ""


def _receipt(
    candidate: ExampleCandidate,
    outcome: ExampleOutcome,
    detail: str,
    result: ExecutionResult | None,
    run: Path,
    product: MeasuredBuild,
) -> ExampleReceipt:
    return ExampleReceipt(
        ordinal=candidate.ordinal,
        outcome=outcome,
        return_code=result.return_code if result is not None else None,
        stdout=clip(scrub(result.stdout, run)) if result is not None else "",
        stderr=clip(scrub(result.stderr, run)) if result is not None else "",
        detail=detail,
        fixtures=(),
        build_verified=product.verified,
        build_command=product.command,
    )


def _classify(output: str) -> tuple[ExampleOutcome, str]:
    """What Node's refusal to load a snippet's imports means for the snippet.

    The snippet is condemned only for what its own text decides: a named import the package does
    not export, or a subpath its `exports` map does not offer. A module that cannot be found at
    all, or a package that throws as it loads, says the build environment is incomplete - an
    unbuilt `dist/`, an uninstalled dependency - not that the README is wrong.
    """
    if "does not provide an export named" in output:
        return "FAILED", _first_line(output)
    if "ERR_PACKAGE_PATH_NOT_EXPORTED" in output:
        return "FAILED", _first_line(output)
    if "ERR_MODULE_NOT_FOUND" in output or "MODULE_NOT_FOUND" in output:
        return (
            "NOT_VERIFIED",
            f"BLOCKED_TOOLCHAIN: a module it needs is missing here ({_first_line(output)})",
        )
    return (
        "NOT_VERIFIED",
        f"BLOCKED_TOOLCHAIN: the package would not load here ({_first_line(output)})",
    )


def _check(
    candidate: ExampleCandidate,
    package: str,
    node: str,
    version: str,
    run: Path,
    product: MeasuredBuild,
    timeout_seconds: float,
) -> ExampleReceipt:
    commonjs = _is_commonjs(candidate.code)
    stem = f"example_{candidate.ordinal:03d}"
    suffix = ".cjs" if commonjs else ".mjs"
    (run / f"{stem}{suffix}").write_text(candidate.code, encoding="utf-8", newline="\n")
    environment = profile_environment(run)
    syntax = execute(
        [node, "--check", f"{stem}{suffix}"],
        workspace=run,
        timeout_seconds=timeout_seconds,
        extra_environment=environment,
    )
    if syntax.timed_out:
        detail = f"BLOCKED_TOOLCHAIN: node did not answer within {timeout_seconds:g}s"
        return _receipt(candidate, "NOT_VERIFIED", detail, syntax, run, product)
    if syntax.return_code != 0:
        detail = _first_line(scrub(syntax.stderr + "\n" + syntax.stdout, run))
        return _receipt(
            candidate, "FAILED", detail or "node --check refused the snippet", syntax, run, product
        )
    statements = _own_imports(candidate.code, package, commonjs)
    if not statements:
        detail = (
            f"syntax-checked with node {version}, but the snippet imports nothing from the "
            "package, so nothing about this package was resolved"
        )
        return _receipt(candidate, "NOT_VERIFIED", detail, syntax, run, product)
    probe = f"{stem}.imports{suffix}"
    lines = [*statements, *(_property_checks(candidate.code, package) if commonjs else [])]
    (run / probe).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    loaded = execute(
        [node, probe],
        workspace=run,
        timeout_seconds=timeout_seconds,
        extra_environment=environment,
    )
    if loaded.timed_out:
        detail = f"BLOCKED_TOOLCHAIN: the package did not load within {timeout_seconds:g}s"
        return _receipt(candidate, "NOT_VERIFIED", detail, loaded, run, product)
    if loaded.return_code != 0:
        outcome, detail = _classify(scrub(loaded.stderr + "\n" + loaded.stdout, run))
        return _receipt(candidate, outcome, detail, loaded, run, product)
    count = len(statements)
    detail = (
        f"syntax-checked with node {version}; its {count} import statement"
        f"{'' if count == 1 else 's'} from the package loaded against the package's own sources "
        f"(not run, since an example may reach a network); the package's own npm build "
        f"{product.summary}"
    )
    return _receipt(candidate, "EXECUTED", detail, loaded, run, product)


def verify_nodejs_build(package: Path, workspace: Path, timeout_seconds: float) -> MeasuredBuild:
    """The package's own npm build, measured whether or not any README example exists.

    The one rule for an npm install claim the registry does not confirm
    (`evidence/facts/extract.py`); the measurement itself is the shared `npm_build` one.
    """
    return verify_package_build(package, workspace, npm_executable(), timeout_seconds)


def verify_nodejs_examples(
    root: Path,
    barrel: Path | None,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
    install_timeout_seconds: float = 300.0,
) -> list[ExampleReceipt]:
    """One receipt per candidate: loaded, failed, or not verified at all.

    Every receipt also carries what the package's own build proved (`build_product`), because a
    checked snippet proves nothing about that and `_source_build_fact` must not read it as if it
    did (G4-W17 arrival item 50).
    """
    if not candidates:
        return []
    if barrel is None:
        return blocked(candidates, "no package entry point to check against; nothing to resolve")
    node = resolve_tool("node")
    if node is None:
        return blocked(candidates, "BLOCKED_TOOLCHAIN: no node on this machine")
    fresh = fresh_workspace(workspace)
    if fresh is None:
        return blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to check in")
    version = _version(node, fresh)
    if not version:
        return blocked(candidates, "BLOCKED_TOOLCHAIN: node did not report a version")
    product = build_product(root, fresh, npm_executable(), install_timeout_seconds)
    run = _stage(root, fresh, product)
    if run is None:
        return blocked(candidates, "BLOCKED_TOOLCHAIN: the sources would not stage")
    name = read_json(root / "package.json").get("name")
    package = name.strip() if isinstance(name, str) else ""
    return [
        _check(candidate, package, node, version, run, product, timeout_seconds)
        for candidate in candidates
    ]
