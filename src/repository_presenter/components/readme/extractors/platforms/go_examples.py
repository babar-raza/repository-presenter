"""Build each README example against the repository's own module, in an isolated workspace.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: Go's bar is a *compilable* example, not an executed one. A README snippet is rarely a
program - seven of Aspose.Cells for Go's ten Go fences are a bare `func main() { … }` and five of
Aspose.PDF for Go's six are loose statements (measured 2026-09-06) - so the snippet is completed
into a package and built against the product's own module through a `replace` directive, with a
disposable `GOPATH` and module cache. What that proves is exactly what the contract claims: the
example's identifiers and calls exist and type-check against this revision.

The imports a completed snippet needs are asked of the compiler, never guessed. A first build
with no import block reports `undefined: fmt`, `undefined: cells_foss` and nothing else about
names the snippet declares itself, so the missing packages are read off those diagnostics: a
name in the standard-library table becomes its own import, and the single remaining name is the
product, imported at the module's own import path. A snippet whose diagnostics name more than one
unresolved package - Aspose.PDF's signing example aliases `crypto/rand` as `cryptorand` - is
`NOT_VERIFIED`, because a wrapper we could not complete is not an example that is false.

Three rules the outcome must respect. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED` — never `CONTRADICTED`. Every cache and credential store is
redirected into the run directory, so a build cannot read or leave state in the developer's
account. And the resolved toolchain version goes into the receipt, because a build is only as
reproducible as the toolchain that ran.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from repository_presenter.core.examples import ExampleCandidate, ExampleReceipt
from repository_presenter.core.execution import ExecutionResult, execute, profile_environment

_MAX_OUTPUT_CHARS = 4000
_WORKSPACE_ATTEMPTS = 5
_WRAPPER_MODULE = "rpexample"
_FALLBACK_GO_VERSION = "1.21"
_SOURCE_NAME = "main.go"
_PACKAGE_CLAUSE = re.compile(r"^package\s+\w+", re.MULTILINE)
# Anchored at the snippet's first token, never searched through it: a README fence writes a
# function body unindented, so Aspose.PDF for Go's encryption example carries `var buf
# bytes.Buffer` at column 0 in the middle of a run of statements. Searching for a declaration
# anywhere called that snippet a run of top-level declarations and every statement above it
# became "non-declaration statement outside function body" - a syntax error the example does not
# have (measured 2026-09-06 on two of its six fences).
_TOP_LEVEL_DECLARATION = re.compile(r"^(?:func|type)\s")
_IMPORT_CLAUSE = re.compile(r"^import\b")
_UNDEFINED = re.compile(r"undefined:\s*([A-Za-z_]\w*)")
_GO_VERSION = re.compile(r"go(\d+\.\d+(?:\.\d+)?)")
_MAJOR_SUFFIX = re.compile(r"/v([2-9]|[1-9]\d+)$")
# The standard-library packages a README example reaches for, each keyed by the qualifier the
# import binds. A package whose qualifier is ambiguous is deliberately absent: `crypto/rand` and
# `math/rand` both bind `rand`, and choosing one would compile a snippet against a package its
# author did not mean.
_STANDARD_LIBRARY: dict[str, str] = {
    "bufio": "bufio",
    "bytes": "bytes",
    "context": "context",
    "csv": "encoding/csv",
    "errors": "errors",
    "filepath": "path/filepath",
    "fmt": "fmt",
    "http": "net/http",
    "io": "io",
    "json": "encoding/json",
    "log": "log",
    "math": "math",
    "os": "os",
    "regexp": "regexp",
    "sort": "sort",
    "strconv": "strconv",
    "strings": "strings",
    "sync": "sync",
    "time": "time",
    "xml": "encoding/xml",
}


def go_executable() -> str | None:
    """The Go toolchain this machine offers, shim included, or None when it has none."""
    for name in ("go", "go.exe", "go.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _clip(text: str) -> str:
    return text if len(text) <= _MAX_OUTPUT_CHARS else text[:_MAX_OUTPUT_CHARS] + "..."


def _blocked(candidates: Sequence[ExampleCandidate], detail: str) -> list[ExampleReceipt]:
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


def _fresh_workspace(workspace: Path) -> Path | None:
    """An empty run directory, even when Windows will not let the last one go.

    A run that cannot have the directory back can always have the next one; failing to clean
    scratch space must never cost a repository its candidate (the .NET verifier measured this
    against a module cache OneDrive still held). None means every attempt was refused, which is
    BLOCKED_TOOLCHAIN.
    """
    # Absolute, because the go command refuses a relative GOPATH outright ("GOPATH entry is
    # relative; must be absolute path") and the disposable profile is built from this path.
    workspace = Path(workspace).absolute()
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def _scrub(text: str, *paths: Path) -> str:
    """This machine's paths out of the toolchain's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home
    directory must not appear in it - and a path that differs per machine would move a sealed
    candidate's bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {path for source in paths for path in (source, source.resolve())}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def require_version(module_path: str) -> str:
    """The version a requirement on ``module_path`` must carry to parse at all.

    Go rejects `require …/v26 v0.0.0` outright - "should be v26, not v0" - so a module whose path
    carries a major-version suffix is required at that major version (measured 2026-09-06 on
    Aspose.Cells for Go, whose module path ends `/v26`).
    """
    match = _MAJOR_SUFFIX.search(module_path.strip())
    return f"v{match.group(1)}.0.0" if match else "v0.0.0"


def wrapper_module(module_path: str, module_directory: Path, go_version: str) -> str:
    """A module file that resolves the product from the clone on disk and nothing else."""
    version = go_version.strip() or _FALLBACK_GO_VERSION
    return (
        f"module {_WRAPPER_MODULE}\n\ngo {version}\n\n"
        f"require {module_path} {require_version(module_path)}\n\n"
        f"replace {module_path} => {module_directory.resolve().as_posix()}\n"
    )


def completed_source(code: str, imports: Sequence[str] = ()) -> str:
    """The snippet as a compilable Go file, with the import block the compiler asked for.

    Three shapes, in the order a README uses them: a whole file already declaring its package is
    left exactly as it is, a run of top-level declarations gets a package clause, and loose
    statements are wrapped in `func main`. Only the last two ever receive a synthesized import
    block - a whole file declares its own, and completing those would hide the very defect the
    verification is for.
    """
    block = ""
    if imports:
        rendered = "\n".join(f"\t{line}" for line in imports)
        block = f"import (\n{rendered}\n)\n\n"
    if _PACKAGE_CLAUSE.search(code):
        return code if code.endswith("\n") else code + "\n"
    body = code if code.endswith("\n") else code + "\n"
    if _TOP_LEVEL_DECLARATION.match(code.lstrip()):
        return f"package main\n\n{block}{body}"
    indented = "\n".join(f"\t{line}" if line.strip() else "" for line in body.splitlines())
    return f"package main\n\n{block}func main() {{\n{indented}\n}}\n"


def declares_only_imports(code: str) -> bool:
    """Whether the fence is an import declaration and nothing a compiler could exercise.

    Aspose.Cells for Go's README opens with a lone
    `import cells_foss "…/aspose/cells_foss"`, which is a true statement about the module and
    not a program: wrapping it in `func main` is a syntax error and declaring it at file scope
    is an unused import, so either way the build fails and the fact would say the example is
    false. It is not false; there is nothing in it to verify.
    """
    body = code.strip()
    if not _IMPORT_CLAUSE.match(body):
        return False
    inside = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if inside:
            inside = line != ")"
        elif line.startswith("import ("):
            inside = True
        elif not line.startswith("import "):
            return False
    return True


def resolve_imports(diagnostics: str, product_path: str, code: str) -> tuple[list[str], list[str]]:
    """The import lines the reported undefined names call for, and the names left unresolved.

    Only a name the snippet uses as a qualifier - `fmt.Println`, `cells_foss.NewWorkbook` - can
    be a missing import; a name called on its own is a helper the README never defines, and
    adding an import for it would hide a real defect. Of the qualifiers, a name in the
    standard-library table is that package and exactly one remaining name is the product, bound
    at the import path the manifest declares. Two or more remaining names cannot be told apart -
    either could be the product - so both are returned unresolved and the example is not
    verified rather than verified against a guess.
    """
    names = sorted(set(_UNDEFINED.findall(diagnostics)))
    qualifiers = [name for name in names if re.search(rf"(?<![\w.]){re.escape(name)}\s*\.", code)]
    imports = [f'"{_STANDARD_LIBRARY[name]}"' for name in qualifiers if name in _STANDARD_LIBRARY]
    unknown = [name for name in qualifiers if name not in _STANDARD_LIBRARY]
    if len(unknown) == 1 and product_path:
        imports.append(f'{unknown[0]} "{product_path}"')
        unknown = []
    return (sorted(imports), unknown)


def _build(
    go: str, run_dir: Path, timeout: float, module_directory: Path
) -> tuple[ExecutionResult, str]:
    result = execute(
        [go, "build", "./..."],
        workspace=run_dir,
        timeout_seconds=timeout,
        extra_environment={**profile_environment(run_dir), "GOFLAGS": "-mod=mod"},
    )
    return (result, _scrub(result.stdout + "\n" + result.stderr, run_dir, module_directory))


def _first_diagnostic(output: str) -> str:
    """The compiler's own first diagnostic, which names the identifier that is missing."""
    for line in output.splitlines():
        stripped = line.strip()
        if re.search(r"\.go:\d+:\d+:", stripped) or stripped.startswith("go: "):
            return stripped[:400]
    return "the build failed without naming a diagnostic"


def verify_go_examples(
    module_directory: Path,
    module_path: str,
    product_import_path: str,
    go_version: str,
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
) -> list[ExampleReceipt]:
    """One receipt per candidate: built, failed to build, or not verified at all."""
    if not candidates:
        return []
    if not module_path:
        return _blocked(candidates, "no module file to build against; nothing to compile")
    go = go_executable()
    if go is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no Go toolchain on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to build in")
    workspace = fresh
    probe = execute(
        [go, "version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment=profile_environment(workspace),
    )
    found = _GO_VERSION.search(probe.stdout) if probe.return_code == 0 else None
    if found is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: the Go toolchain did not report a version")
    toolchain = found.group(1)

    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        if declares_only_imports(candidate.code):
            receipts.extend(
                _blocked(
                    [candidate],
                    "the fence declares an import and no statement; there is nothing to compile",
                )
            )
            continue
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        run_dir.mkdir()
        (run_dir / "go.mod").write_text(
            wrapper_module(module_path, module_directory, go_version),
            encoding="utf-8",
            newline="\n",
        )
        source = run_dir / _SOURCE_NAME
        source.write_text(completed_source(candidate.code), encoding="utf-8", newline="\n")
        result, output = _build(go, run_dir, timeout_seconds, module_directory)
        synthesized: list[str] = []
        unknown: list[str] = []
        if (
            result.return_code != 0
            and not result.timed_out
            and not _PACKAGE_CLAUSE.search(candidate.code)
        ):
            synthesized, unknown = resolve_imports(output, product_import_path, candidate.code)
            if not unknown and synthesized:
                source.write_text(
                    completed_source(candidate.code, synthesized), encoding="utf-8", newline="\n"
                )
                result, output = _build(go, run_dir, timeout_seconds, module_directory)
        outcome, detail = _outcome(
            go, run_dir, module_directory, result, output, unknown, toolchain, timeout_seconds
        )
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(_scrub(result.stdout, run_dir, module_directory)),
                stderr=_clip(_scrub(result.stderr, run_dir, module_directory)),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts


def _outcome(
    go: str,
    run_dir: Path,
    module_directory: Path,
    result: ExecutionResult,
    output: str,
    unknown: Sequence[str],
    toolchain: str,
    timeout_seconds: float,
) -> tuple[str, str]:
    """What the build said, and the sentence a disposition or a fact's evidence acts on."""
    if result.timed_out:
        return ("TIMED_OUT", f"no exit within {timeout_seconds:g}s")
    if unknown:
        return (
            "NOT_VERIFIED",
            "the snippet uses package "
            + ", ".join(f"`{name}`" for name in unknown)
            + " and the verifier cannot tell which import binds it",
        )
    if result.return_code != 0:
        return ("FAILED", _first_diagnostic(output))
    vet = execute(
        [go, "vet", "./..."],
        workspace=run_dir,
        timeout_seconds=timeout_seconds,
        extra_environment={**profile_environment(run_dir), "GOFLAGS": "-mod=mod"},
    )
    if vet.return_code == 0 and not vet.timed_out:
        return ("EXECUTED", f"COMPILED and vetted against {module_directory.name}; Go {toolchain}")
    reported = _first_diagnostic(_scrub(vet.stdout + "\n" + vet.stderr, run_dir, module_directory))
    return (
        "EXECUTED",
        f"COMPILED against {module_directory.name}; Go {toolchain}; go vet reported: {reported}",
    )
