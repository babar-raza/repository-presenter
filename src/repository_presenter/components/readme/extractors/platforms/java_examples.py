"""Compile each README example against the repository's own sources, in an isolated workspace.

`RESEARCH_AND_GUIDELINES.md` §29.6 E5 and `docs/EXECUTION_STATE_MACHINE.md`'s mandatory-truth
table: Java's bar is a *compilable* example, not an executed one. A snippet in a README is not a
program, so it is either taken as the compilation unit it already is or wrapped in one, and
compiled against the product's own classes; what that proves is exactly what the contract claims —
the example's types and calls exist and type-check at this revision.

`javac` rather than `mvn -q compile`: the POMs of this cohort declare no dependency a consumer
resolves (every one is `test` scope), so nothing has to be downloaded. The product tree is
compiled once per repository and each example is then a cheap classpath compile against its
output — which is what `mvn compile` does, and what `-sourcepath` alone cannot do, because javac
finds a type in a source file only when the file is named after it. A repository that *does*
declare a required dependency gets `NOT_VERIFIED` with that stated, never a compile failure
blamed on the example, and so does one whose own sources will not compile.

Four rules the outcome must respect. A toolchain this machine lacks is `NOT_VERIFIED`, which the
facts stage records as `UNRESOLVED` — never `CONTRADICTED`. Every cache and credential store is
redirected into the run directory, so a build cannot read or leave state in the developer's
account. The resolved compiler version goes into the receipt, because a build is only as
reproducible as the toolchain that ran. And an example whose only diagnostics are `cannot find
symbol: variable <name>` is `NOT_VERIFIED`, not false: a fence opening on a binding its README
established in a section this extractor never inherited alongside it (Taskcard F Tier 0; the same
class `rust_examples.py`'s `unbound_values()` and `cpp_examples.py`'s `unbound_identifiers()`
already exclude for their own ecosystems, `Aspose.3D-FOSS-for-Java`'s own `Example.java:10`/`13`,
both `scene`) — a missing *type* or *method* symbol still fails, since `_needed_imports()` above
already resolves a genuinely available type before compilation ever runs.
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
_RELEASE = re.compile(r"^\d+$")
# A README snippet either is a compilation unit already or is a run of statements. `package` is
# dropped because a wrapper compiled outside its declared directory is a javac error about the
# layout, not about the example.
_PACKAGE = re.compile(r"(?m)^\s*package\s+[\w.]+\s*;\s*$")
_IMPORT = re.compile(r"(?m)^\s*import\s+(?:static\s+)?[\w.*]+\s*;\s*$")
_TYPE = re.compile(
    r"(?m)^[ \t]*(?:@\w+[ \t]*)*(?:(?:public|final|abstract|sealed|non-sealed)[ \t]+)*"
    r"(class|interface|enum|record)[ \t]+(\w+)"
)
_PUBLIC_TYPE = re.compile(
    r"(?m)^[ \t]*(?:@\w+[ \t]*)*public[ \t]+"
    r"(?:(?:final|abstract|sealed|non-sealed)[ \t]+)*(?:class|interface|enum|record)[ \t]+(\w+)"
)
# javac's own multi-line diagnostic shape: `<file>:<line>: error: cannot find symbol`, then a few
# lines later `symbol:   variable <name>` (or `class`/`method`, which are real defects and never
# relabeled - `_needed_imports()` above already resolves a genuinely available type).
_JAVAC_ERROR = re.compile(r"^(?P<file>.+?):(?P<line>\d+): error: (?P<message>.+)$")
_UNBOUND_VARIABLE = re.compile(r"^\s*symbol:\s*variable\s+(\S+)\s*$")
_WRAPPER = "Example"
# What a snippet that declares no import of its own is compiled with. Java has no equivalent of
# C#'s implicit usings, and a README fence is written for a reader who already has the imports -
# measured 2026-09-06 on Aspose.3D for Java, where five of ten examples named `Scene`, `File` and
# `FileInputStream` with no import line and javac reported "cannot find symbol" for the language's
# own file classes. The .NET verifier makes exactly this accommodation by enabling
# `ImplicitUsings` in its wrapper project; here it is explicit and it is recorded in the receipt,
# so an EXECUTED outcome always says what the compiler was given.
_IMPLICIT_PACKAGES = ("java.io", "java.util")
# A simple name these on-demand imports already provide is never resolved to a product type, so
# `List` stays `java.util.List` even in a library that ships a `List` of its own.
_JDK_NAMES = frozenset(
    {
        "ArrayList",
        "Arrays",
        "ByteArrayInputStream",
        "ByteArrayOutputStream",
        "Collections",
        "Comparator",
        "Date",
        "File",
        "FileInputStream",
        "FileOutputStream",
        "HashMap",
        "HashSet",
        "IOException",
        "InputStream",
        "Iterator",
        "LinkedList",
        "List",
        "Map",
        "Objects",
        "Optional",
        "OutputStream",
        "Reader",
        "Scanner",
        "Set",
        "Writer",
    }
)
_IDENTIFIER = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")
_MAX_LISTED_IMPORTS = 8
_WRAPPED = """{imports}public class {name} {{
    public static void main(String[] args) throws Exception {{
{body}
    }}
}}
"""


def javac_executable() -> str | None:
    """The compiler this machine offers, `.exe` and `.cmd` shims included, or None."""
    for name in ("javac", "javac.exe", "javac.cmd"):
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

    This checkout is on OneDrive, which holds handles, and `rmtree` has been seen to raise
    WinError 145 on a previous run's build output. A run that cannot have the directory back can
    always have the next one; failing to clean scratch space must never cost a repository its
    candidate. None means every attempt was refused, which is BLOCKED_TOOLCHAIN.
    """
    for suffix in range(_WORKSPACE_ATTEMPTS):
        candidate = workspace if suffix == 0 else workspace.with_name(f"{workspace.name}-{suffix}")
        shutil.rmtree(candidate, ignore_errors=True)
        if candidate.exists():
            continue
        candidate.mkdir(parents=True)
        return candidate
    return None


def _scrub(text: str, run_dir: Path, source_root: Path) -> str:
    """This machine's paths out of the compiler's output.

    A receipt becomes a fact's evidence and a fact is published, so the developer's home
    directory must not appear in it - and a path that differs per machine would move a sealed
    candidate's bytes for a reason that is not the repository.
    """
    cleaned = text
    for base in {run_dir, run_dir.resolve(), source_root, source_root.resolve()}:
        for rendered in (str(base), base.as_posix()):
            cleaned = cleaned.replace(rendered + "\\", "").replace(rendered + "/", "")
            cleaned = cleaned.replace(rendered, "")
    return cleaned


def root_package(source_root: Path) -> str:
    """The shallowest package that declares a type: the product's own root package.

    `com.aspose.threed` for 3D, `org.aspose.pdf` for PDF, `org.aspose.slides.foss` for Slides.
    It is what an import-less snippet is compiled against.
    """
    best: tuple[int, str] | None = None
    for path in source_root.rglob("*.java"):
        parts = path.relative_to(source_root).parts[:-1]
        if not parts:
            return ""
        key = (len(parts), ".".join(parts))
        if best is None or key < best:
            best = key
    return best[1] if best is not None else ""


def public_types(source_root: Path) -> dict[str, str]:
    """Every product type whose simple name is unambiguous, mapped to its fully qualified name.

    A Java file declares its public type under the file's own name, so the index is the tree's
    file names and directories - no parsing. A simple name declared in two packages is dropped
    rather than guessed: an on-demand import of both would be a javac ambiguity error, and
    picking one would be an invention.
    """
    seen: dict[str, str] = {}
    ambiguous: set[str] = set()
    for path in sorted(source_root.rglob("*.java")):
        parts = path.relative_to(source_root).parts
        name = path.stem
        package = ".".join(parts[:-1])
        qualified = f"{package}.{name}" if package else name
        if name in seen and seen[name] != qualified:
            ambiguous.add(name)
        seen[name] = qualified
    return {name: qualified for name, qualified in seen.items() if name not in ambiguous}


def _needed_imports(code: str, declared: Sequence[str], types: dict[str, str]) -> list[str]:
    """Single-type imports for the product types the snippet names and does not import itself.

    Measured 2026-09-06 on Aspose.Slides for Java: seven of eight README examples name
    `Color`, `SaveFormat`, `FillType` and friends, which live in `…foss.drawing` and `…foss.export`
    while the snippet imports only `…foss` - so an on-demand import of the root package was not
    enough and javac reported "cannot find symbol" for types the library really does export.
    Resolving by *name* rather than by wildcard also avoids the ambiguity a wildcard over eighty
    packages would create on Aspose.PDF.
    """
    already = {line.rstrip(";").rsplit(".", 1)[-1] for line in declared}
    wanted = {
        name
        for name in _IDENTIFIER.findall(code)
        if name in types and name not in _JDK_NAMES and name not in already
    }
    return sorted(f"import {types[name]};" for name in wanted)


def compilation_unit(
    code: str, implicit: Sequence[str] = (), types: dict[str, str] | None = None
) -> tuple[str, str, list[str]]:
    """The file name, the source `javac` should compile, and the imports that had to be supplied.

    A snippet that already declares a type is its own compilation unit and keeps its name, because
    javac requires a public type's file to be named after it. A snippet that is a run of statements
    is wrapped in a `main` that throws, so a checked exception in the example is not reported as
    the example's defect. The snippet's own imports are always kept and always win: a single-type
    import takes precedence over any on-demand one, so nothing supplied here can silently redirect
    a name the example resolved for itself.
    """
    body = _PACKAGE.sub("", code)
    declared = [match.group(0).strip() for match in _IMPORT.finditer(body)]
    remainder = _IMPORT.sub("", body).strip("\n")
    supplied = [f"import {package}.*;" for package in implicit]
    supplied += _needed_imports(remainder, declared, types or {})
    imports = sorted(declared) + supplied
    header = "".join(f"{line}\n" for line in imports)
    found = _TYPE.search(remainder)
    if found is not None:
        public = _PUBLIC_TYPE.search(remainder)
        name = public.group(1) if public is not None else found.group(2)
        return (f"{name}.java", f"{header}\n{remainder}\n", supplied)
    indented = "\n".join(
        f"        {line}" if line.strip() else "" for line in remainder.split("\n")
    )
    return (
        f"{_WRAPPER}.java",
        _WRAPPED.format(imports=f"{header}\n", name=_WRAPPER, body=indented),
        supplied,
    )


def _release_flags(release: str, strict: bool) -> list[str]:
    """javac's flags for the floor the POM states, with the POM's own semantics.

    `maven.compiler.release` maps to `--release`, which also restricts the JDK API the code may
    call; `maven.compiler.target`/`source` map to `-source`/`-target`, which set the language
    level and the bytecode version and nothing else. Measured 2026-09-06 on Aspose.PDF for Java:
    its POM declares `target`/`source` 11 and its sources call APIs `--release 11` refuses, so
    treating the two as interchangeable would have failed a build Maven performs happily.
    """
    if not _RELEASE.fullmatch(release.strip()):
        return []
    version = release.strip()
    return ["--release", version] if strict else ["-source", version, "-target", version]


def _compile_product(
    javac: str,
    source_root: Path,
    workspace: Path,
    flags: list[str],
    timeout_seconds: float,
) -> tuple[Path | None, str]:
    """Compile the whole product tree once, and return the class output the examples link against.

    `-sourcepath` alone is not enough. javac finds a type in a source file only when the file is
    named after it, so a package-private top-level class declared beside another one is invisible
    to implicit compilation - measured 2026-09-06 on Aspose.PDF for Java, where every example
    failed on `ReturnSignal`, `BreakSignal` and `ContinueSignal` inside the *product's* own
    `Interpreter.java`, a defect of the compile strategy and not of any README. Compiling every
    source once is what `mvn compile` does, and it makes each example a cheap classpath compile.
    """
    classes = workspace / "classes"
    classes.mkdir()
    sources = sorted(path.resolve().as_posix() for path in source_root.rglob("*.java"))
    listing = workspace / "sources.txt"
    listing.write_text("\n".join(sources) + "\n", encoding="utf-8", newline="\n")
    result = execute(
        [
            javac,
            "-nowarn",
            "-proc:none",
            "-encoding",
            "UTF-8",
            "-d",
            "classes",
            *flags,
            "@sources.txt",
        ],
        workspace=workspace,
        timeout_seconds=timeout_seconds,
        extra_environment=_environment(javac, workspace),
    )
    if result.timed_out:
        return (None, f"the product's own sources did not compile within {timeout_seconds:g}s")
    if result.return_code != 0:
        return (None, _first_error(result.stdout, result.stderr, workspace, source_root))
    return (classes, "")


def _compiler_version(javac: str, workspace: Path, environment: dict[str, str]) -> str:
    result = execute(
        [javac, "-version"],
        workspace=workspace,
        timeout_seconds=60.0,
        extra_environment=environment,
    )
    if result.return_code != 0:
        return ""
    return (result.stdout.strip() or result.stderr.strip()).replace("javac ", "")


def _environment(javac: str, run_dir: Path) -> dict[str, str]:
    """The disposable profile, plus the JDK that `javac` was resolved from.

    `JAVA_HOME` is not on the execution boundary's allow-list, so the subprocess would otherwise
    inherit nothing - and this machine's `JAVA_HOME` names JDK 17 while `javac` resolves to JDK
    21 (§28.11). Deriving it from the resolved binary keeps the compiler and its home the same
    installation.
    """
    overlay = profile_environment(run_dir)
    home = Path(javac).resolve().parent.parent
    if (home / "lib").is_dir():
        overlay["JAVA_HOME"] = str(home)
    return overlay


def verify_java_examples(
    source_root: Path,
    release: str,
    strict_release: bool,
    required: Sequence[str],
    candidates: Sequence[ExampleCandidate],
    workspace: Path,
    timeout_seconds: float,
) -> list[ExampleReceipt]:
    """One receipt per candidate: compiled, failed to compile, or not verified at all."""
    if not candidates:
        return []
    if not source_root.is_dir() or not any(source_root.rglob("*.java")):
        return _blocked(candidates, "no Java source tree to compile against")
    if required:
        listed = ", ".join(sorted(required))
        return _blocked(
            candidates,
            f"BLOCKED_TOOLCHAIN: the POM declares required dependencies javac cannot resolve "
            f"without a Maven repository ({listed})",
        )
    javac = javac_executable()
    if javac is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no Java compiler on this machine")
    fresh = _fresh_workspace(workspace)
    if fresh is None:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: no clean workspace to compile in")
    workspace = fresh
    version = _compiler_version(javac, workspace, _environment(javac, workspace))
    if not version:
        return _blocked(candidates, "BLOCKED_TOOLCHAIN: javac did not report a version")

    flags = _release_flags(release, strict_release)
    classes, failure = _compile_product(javac, source_root, workspace, flags, timeout_seconds)
    if classes is None:
        return _blocked(
            candidates,
            f"BLOCKED_TOOLCHAIN: the product's own sources do not compile with javac "
            f"{version}, so no example can be checked against them ({failure})",
        )
    package = root_package(source_root)
    implicit = (*_IMPLICIT_PACKAGES, package) if package else _IMPLICIT_PACKAGES
    types = public_types(source_root)
    receipts: list[ExampleReceipt] = []
    for candidate in candidates:
        run_dir = workspace / f"example_{candidate.ordinal:03d}"
        run_dir.mkdir()
        name, source, supplied = compilation_unit(candidate.code, implicit, types)
        (run_dir / name).write_text(source, encoding="utf-8", newline="\n")
        argv = [
            javac,
            "-nowarn",
            "-proc:none",
            "-encoding",
            "UTF-8",
            "-d",
            "out",
            "-classpath",
            str(classes.resolve()),
            *flags,
            name,
        ]
        result: ExecutionResult = execute(
            argv,
            workspace=run_dir,
            timeout_seconds=timeout_seconds,
            extra_environment=_environment(javac, run_dir),
        )
        if result.timed_out:
            outcome, detail = "TIMED_OUT", f"no exit within {timeout_seconds:g}s"
        elif result.return_code == 0:
            names = [line.removeprefix("import ").removesuffix(";") for line in supplied]
            if len(names) > _MAX_LISTED_IMPORTS:
                names = [
                    *names[:_MAX_LISTED_IMPORTS],
                    f"and {len(names) - _MAX_LISTED_IMPORTS} more",
                ]
            added = f"; imports supplied: {', '.join(names)}" if names else ""
            outcome = "EXECUTED"
            detail = f"compiled against the product's own classes; javac {version}{added}"
        else:
            unbound = unbound_variables(result.stdout + "\n" + result.stderr)
            if unbound:
                outcome = "NOT_VERIFIED"
                detail = (
                    "the fence uses "
                    + ", ".join(f"`{name}`" for name in dict.fromkeys(unbound))
                    + " without binding it; the README establishes it in an earlier section"
                )
            else:
                outcome = "FAILED"
                detail = _first_error(result.stdout, result.stderr, run_dir, source_root)
        receipts.append(
            ExampleReceipt(
                ordinal=candidate.ordinal,
                outcome=outcome,  # type: ignore[arg-type]
                return_code=result.return_code,
                stdout=_clip(_scrub(result.stdout, run_dir, source_root)),
                stderr=_clip(_scrub(result.stderr, run_dir, source_root)),
                detail=detail,
                fixtures=(),
            )
        )
    return receipts


def _first_error(stdout: str, stderr: str, run_dir: Path, source_root: Path) -> str:
    """The compiler's own first diagnostic, which names the type or member that is missing."""
    for line in _scrub(stdout + "\n" + stderr, run_dir, source_root).splitlines():
        if ": error:" in line:
            return line.strip()[:400]
    return "the compilation failed without naming a diagnostic"


def unbound_variables(output: str) -> list[str]:
    """The variable names an example uses and never binds, when they are the only thing wrong.

    A fence opens on a binding its README established in prose - `scene`, `workbook`. That is
    the one error class which says the fence is incomplete rather than false, so it counts only
    when every error javac raised is `cannot find symbol` naming a *variable* (`Aspose.3D-FOSS-
    for-Java`'s own `Example.java:10`/`13`, both `scene`) - a missing type or method is a real
    defect and must not be excused as missing context.
    """
    lines = output.splitlines()
    names: list[str] = []
    saw_error = False
    for index, line in enumerate(lines):
        match = _JAVAC_ERROR.match(line)
        if match is None:
            continue
        saw_error = True
        if match.group("message").strip() != "cannot find symbol":
            return []
        symbol = None
        for lookahead in lines[index + 1 : index + 5]:
            if _JAVAC_ERROR.match(lookahead):
                break
            variable = _UNBOUND_VARIABLE.match(lookahead)
            if variable:
                symbol = variable.group(1)
                break
        if symbol is None:
            return []
        names.append(symbol)
    return names if saw_error else []
