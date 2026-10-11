"""Which shell commands a README already shows, and whether a fact's command repeats one.

An addition that repeats a command the maintainers already show - written differently, in another
block, even inside a collapsed ``<details>`` - is noise to the reader, so before a build, test or
install command is inserted it is compared, normalised, with every command the README holds (fenced
lines and inline code, anywhere). Two commands are equivalent when they name the same tool and ask
for the same thing, whatever the flags or the project file they point at: ``mvn clean package`` and
``mvn -B package -DskipTests`` are the same build, ``dotnet build A.sln`` and ``dotnet build
B.csproj`` are the same verb.

A command that needs a package the toolchain does not ship (``python -m build`` needs
``pip install build``) is not safe to publish alone: ``missing_precondition`` names it so the
detector can skip and report instead of printing a command that fails on a clean machine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from repository_presenter.components.readme_correction.detectors._layout import fence_lines
from repository_presenter.components.readme_correction.model import Context

_PROMPT = re.compile(r"^\s*(?:\$|>|PS [^>]*>)\s+")
_INLINE = re.compile(r"`([^`\n]+)`")
_SEPARATORS = re.compile(r"\s*(?:&&|;|\|\|)\s*")
_ENVIRONMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
_WRAPPERS = {
    "./mvnw": "mvn",
    "mvnw": "mvn",
    "mvnw.cmd": "mvn",
    "./gradlew": "gradle",
    "gradlew": "gradle",
}
_PYTHONS = frozenset({"python", "python3", "py"})
_GOALS = frozenset({"mvn", "gradle"})
_RUNNERS = frozenset({"npm", "yarn", "pnpm", "bun"})
#: tools whose arguments are targets (paths, files), not verbs: the command is the tool itself.
_TARGETED = frozenset({"pytest", "py.test", "tox", "nox", "ctest"})
#: modules ``python -m`` runs from the standard library: nothing to install first.
_STANDARD_MODULES = frozenset(
    {
        "unittest",
        "venv",
        "pip",
        "ensurepip",
        "compileall",
        "doctest",
        "timeit",
        "http.server",
        "json.tool",
        "zipapp",
        "py_compile",
        "cProfile",
        "pdb",
    }
)


@dataclass(frozen=True)
class Signature:
    tool: str
    verbs: frozenset[str]


def commands_of(text: str) -> list[str]:
    """The individual commands in ``text`` (a block or one line): prompts stripped, split on
    ``&&``, ``;`` and ``||``, comments and blank lines dropped."""
    found: list[str] = []
    for raw in text.splitlines():
        line = _PROMPT.sub("", raw).strip()
        if not line or line.startswith("#"):
            continue
        found += [part.strip() for part in _SEPARATORS.split(line) if part.strip()]
    return found


def signature(command: str) -> Signature | None:
    tokens = [t for t in command.split() if t]
    while tokens and (_ENVIRONMENT.match(tokens[0]) or tokens[0] == "sudo"):
        tokens.pop(0)
    if not tokens:
        return None
    tool = _WRAPPERS.get(tokens[0].lower(), tokens[0].lower()).removeprefix("./")
    rest = tokens[1:]
    positional = [t for t in rest if not t.startswith("-") and "=" not in t]
    if tool in _PYTHONS:
        if len(rest) >= 2 and rest[0] == "-m":
            return Signature(f"python -m {rest[1].lower()}", frozenset())
        return Signature("python", frozenset(positional[:1]))
    if tool in _GOALS:
        return Signature(tool, frozenset(t for t in positional if t != "clean"))
    if tool in _RUNNERS:
        if positional[:1] == ["run"] and len(positional) > 1:
            return Signature(tool, frozenset({f"run:{positional[1]}"}))
        return Signature(tool, frozenset(positional[:1]))
    if tool in _TARGETED:
        return Signature(tool, frozenset())
    if tool == "pip":
        return Signature(tool, frozenset(positional))
    if tool == "cmake":
        return Signature(tool, frozenset(rest[:1]))
    return Signature(tool, frozenset(positional[:1]))


def readme_commands(ctx: Context) -> list[Signature]:
    """The signature of every command the README shows: fenced lines and inline code spans,
    anywhere in the file (a collapsed ``<details>`` block included)."""
    sources = [line for _language, line in fence_lines(ctx)]
    for line in ctx.lines:
        if not line.in_fence:
            sources += _INLINE.findall(line.text)
    found: list[Signature] = []
    for source in sources:
        for command in commands_of(source):
            parsed = signature(command)
            if parsed is not None:
                found.append(parsed)
    return found


def equivalent(wanted: Signature, shown: Signature) -> bool:
    """``shown`` already does what ``wanted`` asks."""
    if wanted.tool != shown.tool:
        return False
    if wanted.tool in _GOALS:
        return wanted.verbs <= shown.verbs
    return wanted.verbs == shown.verbs


def covered(ctx: Context, value: str, shown: list[Signature] | None = None) -> bool:
    """Whether every command in the fact value ``value`` is already shown, in any form."""
    present = readme_commands(ctx) if shown is None else shown
    wanted = [s for s in (signature(c) for c in commands_of(value)) if s is not None]
    return bool(wanted) and all(any(equivalent(w, s) for s in present) for w in wanted)


def missing_precondition(value: str) -> str | None:
    """The install a command in ``value`` needs first, when it runs a module the toolchain does not
    ship (``python -m build``): the name of the package, else None."""
    for command in commands_of(value):
        parsed = signature(command)
        if parsed is None or not parsed.tool.startswith("python -m "):
            continue
        module = parsed.tool.removeprefix("python -m ")
        if module not in _STANDARD_MODULES:
            return module.split(".")[0]
    return None


def states_install(ctx: Context, package: str) -> bool:
    """Whether the README already shows installing ``package`` (``pip install ... build``)."""
    pattern = re.compile(rf"(?i)\binstall\b[^\n]*\b{re.escape(package)}\b")
    return pattern.search(ctx.readme) is not None
