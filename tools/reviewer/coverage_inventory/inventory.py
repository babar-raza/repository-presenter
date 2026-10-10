# Part of TC-COV-01 (plans: reseal-and-refresh). Owner/reviewer measurement tooling (tools/README.md):
# read-only, no provider call, writes only the files it is told to. Not imported by src/.
"""Enumerate the information units a cloned repository holds, per spec.md.

Each ``extract_*`` function reads files of a checked-out clone and returns ``Unit`` objects
(see matching.py); none of them writes, executes, or fetches anything.
"""
from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path

import yaml

from matching import Unit, body_is_material, norm_heading, split_sections, tokens, version_pattern

PRUNE = {".git", "node_modules", "vendor", "target", "obj", ".venv", "venv", "__pycache__", ".tox",
         ".gradle", ".idea", ".vs", "dist", ".mypy_cache", ".pytest_cache", "site-packages"}
MAX_FILES = 40000
TEST_SEG = re.compile(r"^(tests?|__tests__|spec|specs|testing|integrationtests?|unittests?|conformancetests?)$|(\.|_|-)?tests?$", re.I)
EXAMPLE_SEG = {"example", "examples", "sample", "samples", "demo", "demos", "cookbook", "tutorial", "tutorials"}
BENCH_SEG = {"bench", "benches", "benchmark", "benchmarks"}
CODE_EXT = {".py", ".cs", ".java", ".go", ".rs", ".ts", ".tsx", ".js", ".mjs", ".cpp", ".cc", ".c", ".h", ".hpp",
            ".md", ".ipynb", ".kt", ".scala", ".rb", ".php", ".sh", ".ps1", ".csx", ".fsx", ".vb"}
DOC_EXT = {".md", ".mdx", ".rst"}

COMMUNITY = {
    "contributing": (re.compile(r"^contributing([-_ ]?guide)?$", re.I), ["contributing", "contribute", "contributions", "how to contribute", "contributing guide"]),
    "security_policy": (re.compile(r"^security([-_ ]?(policy|md))?$", re.I), ["security", "security policy", "reporting vulnerabilities", "vulnerability reporting", "reporting a vulnerability"]),
    "code_of_conduct": (re.compile(r"^code[-_ ]?of[-_ ]?conduct$", re.I), ["code of conduct"]),
}
CHANGELOG_STEM = re.compile(r"^(changelog|changes|change[-_ ]?log|history|news|releases?|release[-_ ]?notes?|whatsnew|whats[-_ ]new)$", re.I)
CHANGELOG_HEADINGS = ["changelog", "change log", "release notes", "what's new", "whats new", "releases", "release history", "history", "changes"]
LICENSE_STEM = re.compile(r"^(licen[sc]e|copying)", re.I)
NOTICE_STEM = re.compile(r"^(notice|third[-_ ]?party)", re.I)
AGENT_DOCS = {"agents.md", "claude.md", "gemini.md", "copilot-instructions.md"}


def segs(rel: str) -> list[str]:
    return rel.replace("\\", "/").split("/")


def _seg(s: str) -> str:
    return s.lstrip("_.")  # ``_examples`` is an examples directory


def is_test_path(rel: str) -> bool:
    return any(TEST_SEG.search(_seg(s)) for s in segs(rel)[:-1]) or bool(
        re.search(r"(^test_|_test\.|tests?\.[a-z]+$|\.test\.|\.spec\.)", segs(rel)[-1], re.I)
    )


def is_example_path(rel: str) -> bool:
    return any(_seg(s).lower() in EXAMPLE_SEG for s in segs(rel)[:-1])


def is_aux_path(rel: str) -> bool:
    """Tests, examples and benchmarks: programs that are not the product's own entry point."""
    return is_test_path(rel) or is_example_path(rel) or any(s.lower() in BENCH_SEG for s in segs(rel)[:-1])


def list_files(root: Path) -> list[str]:
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for f in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, f), root).replace("\\", "/"))
            if len(out) >= MAX_FILES:
                return out
    return sorted(out)


def read(root: Path, rel: str, limit: int = 400_000) -> str:
    try:
        with open(root / rel, "rb") as fh:
            return fh.read(limit).decode("utf-8", "replace")
    except OSError:
        return ""


def lines_of(text: str) -> int:
    return text.count("\n") + 1 if text else 0


def top_dir(rel: str) -> str:
    return segs(rel)[0] if len(segs(rel)) > 1 else ""


# --- README ----------------------------------------------------------------------------------

def find_readme(files: list[str]) -> str | None:
    cands = [f for f in files if "/" not in f and re.match(r"^readme(\.(md|markdown|rst|txt))?$", f, re.I)]
    cands.sort(key=lambda f: (0 if f.lower().endswith(".md") else 1, f))
    return cands[0] if cands else None


def extract_readme_units(readme_text: str) -> list[Unit]:
    units, seen = [], {}
    for heading, body in split_sections(readme_text):
        if not body_is_material(body):
            continue
        key = norm_heading(heading) or "(untitled)"
        seen[key] = seen.get(key, 0) + 1
        name = heading if seen[key] == 1 else f"{heading} #{seen[key]}"
        t = tokens(heading + "\n" + body)
        units.append(Unit("readme_unit", name, heading=key, body_tokens=t, size=lines_of(body),
                          detail=f"{lines_of(body)} lines"))
    return units


# --- documentation, community, changelog, license ------------------------------------------------

def headings_of(text: str, n: int = 8) -> list[str]:
    return [h for h, _ in split_sections(text)][:n]


def _doc_unit(root: Path, rel: str, unit_type: str, heading_keys: list[str] | None = None, pointers: list[str] | None = None) -> Unit:
    text = read(root, rel)
    hs = headings_of(text)
    return Unit(unit_type, rel, path=rel, size=lines_of(text), body_tokens=tokens(text[:30000]),
                heading_keys=heading_keys or [], pointer_dirs=pointers or [],
                detail=f"{lines_of(text)} lines; headings: " + " | ".join(hs[:5]))


def extract_doc_units(root: Path, files: list[str]) -> list[Unit]:
    units = []
    for rel in files:
        parts = segs(rel)
        stem, ext = os.path.splitext(parts[-1])
        if ext.lower() not in DOC_EXT or parts[-1].lower() in AGENT_DOCS:
            continue
        in_docs = len(parts) > 1 and parts[0].lower() in {"docs", "doc", "documentation", "wiki"}
        in_gh = len(parts) == 2 and parts[0].lower() == ".github"
        root_level = len(parts) == 1
        if is_test_path(rel) or is_example_path(rel):
            continue
        if re.match(r"^readme$", stem, re.I) and root_level:
            continue
        cat = None
        for t, (rx, keys) in COMMUNITY.items():
            if rx.search(stem) and (root_level or in_docs or in_gh):
                cat = (t, keys)
        if cat:
            units.append(_doc_unit(root, rel, cat[0], cat[1]))
        elif CHANGELOG_STEM.match(stem) and (root_level or in_docs or in_gh):
            units.append(_doc_unit(root, rel, "changelog", CHANGELOG_HEADINGS))
        elif in_docs:
            units.append(_doc_unit(root, rel, "doc_page", pointers=[parts[0]]))
        elif root_level and not LICENSE_STEM.match(stem) and not NOTICE_STEM.match(stem):
            units.append(_doc_unit(root, rel, "root_doc"))
    return units


def extract_license_units(root: Path, files: list[str]) -> list[Unit]:
    units = []
    for rel in files:
        parts = segs(rel)
        stem = os.path.splitext(parts[-1])[0]
        if len(parts) > 2 or is_test_path(rel) or is_example_path(rel):
            continue
        in_license_dir = len(parts) == 2 and parts[0].lower() in {"license", "licenses", "licence"}
        if len(parts) == 2 and not in_license_dir:
            continue
        if LICENSE_STEM.match(stem) or in_license_dir:
            text = read(root, rel, 4000).lower()
            spdx = [p for k, p in (("mit license", r"\bmit\b"), ("apache license", r"apache"), ("gnu general public", r"\bgpl|general public"),
                                   ("bsd", r"\bbsd\b")) if k in text]
            units.append(Unit("license_notice", rel, path=rel, size=lines_of(text), patterns=spdx[:1],
                              heading_keys=["license", "licence", "licensing", "license and copyright"], detail=f"{lines_of(text)} lines"))
        elif NOTICE_STEM.match(stem):
            units.append(Unit("license_notice", rel, path=rel, size=lines_of(read(root, rel, 4000)),
                              heading_keys=["third-party notices", "third party notices", "notices", "acknowledgements", "acknowledgments", "attribution", "notice"],
                              detail="notice file"))
    return units


def extract_release_unit(release: dict | None) -> list[Unit]:
    if not release or not isinstance(release, dict) or not release.get("tag_name"):
        return []
    body = release.get("body") or ""
    t = tokens(body)
    if len(t) < 3:
        return []
    tag = release["tag_name"]
    return [Unit("github_release", f"release {tag}", size=len(body), body_tokens=t,
                 patterns=[r"github\.com/[^\s)\"']+/releases(?:/|\b)"], heading_keys=CHANGELOG_HEADINGS,
                 detail=f"latest release {tag} published {str(release.get('published_at'))[:10]}; {len(body)} chars")]


# --- entry points ----------------------------------------------------------------------------

def _tomlload(root: Path, rel: str) -> dict:
    try:
        return tomllib.loads(read(root, rel))
    except tomllib.TOMLDecodeError:
        return {}


AUX_NAME = re.compile(r"^(sample|example|demo|bench)|(^|[_-])(tests?|benchmarks?)$", re.I)


def _cli(name: str, source: str, rel: str, words: list[str] | None = None, patterns: list[str] | None = None) -> Unit | None:
    if AUX_NAME.search(name):  # a sample, demo, benchmark or test runner, not the product's command
        return None
    return Unit("cli_entry", name, path=rel, detail=f"{source} in {rel}", names=words if words is not None else [name],
                patterns=patterns or [], use_basename=False)


def extract_cli_units(root: Path, files: list[str]) -> list[Unit]:
    out: dict[str, Unit] = {}

    def add(u: Unit | None) -> None:
        if u:
            out.setdefault(u.name, u)

    for rel in files:
        parts = segs(rel)
        base = parts[-1].lower()
        if is_aux_path(rel):
            continue
        if base == "pyproject.toml":
            d = _tomlload(root, rel)
            proj = d.get("project", {})
            for table in ("scripts", "gui-scripts"):
                for n in proj.get(table, {}):
                    add(_cli(n, f"[project.{table}]", rel))
            for n in d.get("tool", {}).get("poetry", {}).get("scripts", {}):
                add(_cli(n, "[tool.poetry.scripts]", rel))
        elif base in ("setup.py", "setup.cfg"):
            text = read(root, rel)
            if "console_scripts" in text or "gui_scripts" in text:
                for n in re.findall(r"[\"']?([A-Za-z0-9_.-]+)\s*=\s*[A-Za-z0-9_.]+:[A-Za-z0-9_.]+", text):
                    add(_cli(n, "console_scripts", rel))
        elif base == "__main__.py":
            pkg = parts[-2] if len(parts) > 1 else ""
            if pkg and pkg != "src":
                add(_cli(f"python -m {pkg}", "__main__.py", rel, words=[], patterns=[rf"-m\s+{re.escape(pkg.lower())}\b"]))
        elif base == "package.json" and len(parts) <= 3:
            try:
                d = json.loads(read(root, rel))
            except ValueError:
                continue
            b = d.get("bin")
            if isinstance(b, str) and d.get("name"):
                add(_cli(str(d["name"]).split("/")[-1], "package.json bin", rel))
            elif isinstance(b, dict):
                for n in b:
                    add(_cli(n, "package.json bin", rel))
        elif base.endswith((".csproj", ".fsproj")):
            text = read(root, rel)
            if re.search(r"<OutputType>\s*(Win)?Exe\s*</OutputType>", text, re.I) and "Microsoft.NET.Test.Sdk" not in text:
                add(_cli(os.path.splitext(parts[-1])[0], "OutputType Exe", rel))
        elif base.endswith(".go") and not base.endswith("_test.go"):
            if re.search(r"^package main\b", read(root, rel, 3000), re.M) and "func main(" in read(root, rel, 60000):
                d = "/".join(parts[:-1]) or "."
                n = parts[-2] if len(parts) > 1 else "main"
                add(_cli(n, "go main package", d))
        elif base == "cargo.toml":
            d = _tomlload(root, rel)
            for b in d.get("bin", []):
                if b.get("name"):
                    add(_cli(b["name"], "[[bin]]", rel))
            pkgname = d.get("package", {}).get("name")
            here = "/".join(parts[:-1])
            if pkgname and (f"{here}/src/main.rs".lstrip("/") in files):
                add(_cli(pkgname, "src/main.rs default bin", rel))
        elif base == "cmakelists.txt":
            for n in re.findall(r"add_executable\(\s*([A-Za-z0-9_.\-]+)", read(root, rel)):
                add(_cli(n, "add_executable", rel))
        elif base == "pom.xml":
            text = read(root, rel)
            for cls in set(re.findall(r"<mainClass>\s*([\w.$]+)\s*</mainClass>", text) + re.findall(r"Main-Class>\s*([\w.$]+)\s*<", text)):
                simple = cls.split(".")[-1]
                add(_cli(cls, "pom main class", rel, words=[cls] + ([simple] if simple.lower() not in {"main", "app", "program"} else [])))
        elif base in ("build.gradle", "build.gradle.kts"):
            for cls in set(re.findall(r"mainClass(?:Name)?(?:\.set\()?\s*[=(]?\s*[\"']([\w.$]+)[\"']", read(root, rel))):
                add(_cli(cls, "gradle main class", rel, words=[cls]))
    for rel in files:  # src/bin/*.rs additional Cargo binaries
        m = re.match(r"^(.*?)src/bin/([^/]+?)(?:\.rs|/main\.rs)$", rel)
        if m and not is_aux_path(rel):
            u = _cli(m.group(2), "src/bin", rel)
            if u:
                out.setdefault(m.group(2), u)
    return list(out.values())


# --- target frameworks and CI matrices ---------------------------------------------------------

def extract_framework_units(root: Path, files: list[str]) -> list[Unit]:
    found: dict[tuple[str, str], tuple[str, list[str]]] = {}  # (kind, value) -> (label, [sources])

    def add(kind: str, value: str, label: str, src: str) -> None:
        value = value.strip()
        if value:
            found.setdefault((kind, value), (label, []))[1].append(src)

    for rel in files:
        parts, base = segs(rel), segs(rel)[-1].lower()
        if base.endswith((".csproj", ".fsproj", ".vbproj")) or base in ("directory.build.props", "directory.build.targets"):
            if is_aux_path(rel):
                continue
            text = read(root, rel)
            if "Microsoft.NET.Test.Sdk" in text:
                continue
            for m in re.finditer(r"<TargetFrameworks?>\s*([^<]+)</TargetFrameworks?>", text):
                for v in re.split(r"[;,\s]+", m.group(1)):
                    if v and "$(" not in v:
                        add("dotnet", v, f"target framework {v}", rel)
        elif base == "pom.xml":
            text = read(root, rel)
            for m in re.finditer(r"<(?:maven\.compiler\.(?:release|source|target)|java\.version|release)>\s*([0-9.]+)\s*<", text):
                v = m.group(1)
                add("java", v[2:] if v.startswith("1.") else v, f"java release {v}", rel)
        elif base in ("build.gradle", "build.gradle.kts"):
            text = read(root, rel)
            for m in re.finditer(r"(?:JavaVersion\.VERSION_|jvmToolchain\(|languageVersion(?:\.set\()?\s*=?\s*JavaLanguageVersion\.of\()(\d+)", text):
                add("java", m.group(1), f"java toolchain {m.group(1)}", rel)
        elif base.startswith("tsconfig") and base.endswith(".json"):
            m = re.search(r"\"target\"\s*:\s*\"([^\"]+)\"", read(root, rel))
            if m and not is_aux_path(rel):
                add("ts", m.group(1), f"tsconfig target {m.group(1)}", rel)
        elif base == "package.json" and len(parts) <= 3:
            try:
                eng = json.loads(read(root, rel)).get("engines", {})
            except ValueError:
                continue
            if isinstance(eng, dict) and eng.get("node"):
                m = re.search(r"(\d+(?:\.\d+)?)", str(eng["node"]))
                if m:
                    add("node", m.group(1), f"node engine {eng['node']}", rel)
        elif base == "cargo.toml" and not is_aux_path(rel):
            pk = _tomlload(root, rel).get("package", {})
            if isinstance(pk.get("edition"), str):
                add("rust", pk["edition"], f"rust edition {pk['edition']}", rel)
            if isinstance(pk.get("rust-version"), str):
                add("rust", pk["rust-version"], f"rust-version {pk['rust-version']}", rel)
        elif base == "go.mod":
            m = re.search(r"^go\s+(\d+\.\d+)", read(root, rel), re.M)
            if m:
                add("go", m.group(1), f"go {m.group(1)}", rel)
        elif base == "pyproject.toml":
            rp = _tomlload(root, rel).get("project", {}).get("requires-python")
            if rp:
                m = re.search(r"(\d+\.\d+)", str(rp))
                if m:
                    add("python", m.group(1), f"requires-python {rp}", rel)
        elif base in ("setup.py", "setup.cfg"):
            m = re.search(r"python_requires\s*[=:]\s*[\"']?[><=~! ]*(\d+\.\d+)", read(root, rel))
            if m:
                add("python", m.group(1), f"python_requires {m.group(1)}", rel)
        elif base == "cmakelists.txt" and not is_aux_path(rel):
            text = read(root, rel)
            for m in re.finditer(r"CMAKE_CXX_STANDARD\s+(\d+)|cxx_std_(\d+)", text):
                v = m.group(1) or m.group(2)
                add("cxx", v, f"C++ standard {v}", rel)
    units = []
    for (kind, value), (label, srcs) in sorted(found.items()):
        pats = version_pattern(kind, value) if kind != "ts" else [rf"(?<![a-z0-9]){re.escape(value.lower())}(?![a-z0-9])"]
        units.append(Unit("target_framework", label, path=srcs[0], patterns=pats, use_basename=False,
                          detail=f"{kind}; declared in {len(set(srcs))} file(s): {srcs[0]}"))
    return units


MATRIX_AXIS = re.compile(r"^(os|runner|runs-on|platform|arch|target|rust|toolchain|compiler|cc|cxx|build[-_]type|configuration|framework"
                         r"|python|java|jdk|dotnet|node|go|[a-z]+[-_]version)$", re.I)
OS_ALTERNATES = {"ubuntu": "ubuntu|linux", "windows": "windows|win32", "macos": "macos|mac os|osx|darwin"}


def _matrix_value(v: str) -> str | None:
    v = str(v).strip()
    if "${{" in v or not v:
        return None
    m = re.match(r"^(ubuntu|windows|macos)[-.].*$", v, re.I)
    return OS_ALTERNATES[m.group(1).lower()] if m else v


def extract_matrix_units(root: Path, files: list[str]) -> list[Unit]:
    seen: dict[tuple[str, tuple[str, ...]], Unit] = {}
    for rel in files:
        if not re.match(r"^\.github/workflows/[^/]+\.ya?ml$", rel):
            continue
        try:
            doc = yaml.load(read(root, rel), Loader=yaml.BaseLoader) or {}
        except yaml.YAMLError:
            continue
        jobs = doc.get("jobs") if isinstance(doc, dict) else None
        for _, job in (jobs or {}).items():
            matrix = ((job or {}).get("strategy") or {}).get("matrix") if isinstance(job, dict) else None
            if not isinstance(matrix, dict):
                continue
            axes: dict[str, list[str]] = {}
            for k, v in matrix.items():
                if k in ("include", "exclude") and isinstance(v, list):
                    for entry in v:
                        for ek, ev in (entry.items() if isinstance(entry, dict) else []):
                            if isinstance(ev, str):
                                axes.setdefault(ek, []).append(ev)
                elif isinstance(v, list):
                    axes.setdefault(k, []).extend(x for x in v if isinstance(x, str))
            for axis, vals in axes.items():
                if not MATRIX_AXIS.match(axis):
                    continue
                clean = [c for c in dict.fromkeys(_matrix_value(x) for x in vals) if c]
                if len(clean) < 2:
                    continue
                key = (axis, tuple(clean))
                if key in seen:
                    seen[key].detail += f", {rel}"
                    continue
                seen[key] = Unit("ci_matrix", f"{axis}: {', '.join(c.split('|')[0] for c in clean)}", path=rel, values=clean, use_basename=False,
                                 detail=f"matrix axis in {rel}")
    return list(seen.values())


# --- examples, tests ---------------------------------------------------------------------------

def extract_example_units(root: Path, files: list[str]) -> list[Unit]:
    units = []
    for rel in files:
        parts = segs(rel)
        ext = os.path.splitext(parts[-1])[1].lower()
        if not is_example_path(rel) or is_test_path(rel) or ext not in CODE_EXT:
            continue
        text = read(root, rel, 60000)
        ex_root = next(i for i, s in enumerate(parts[:-1]) if _seg(s).lower() in EXAMPLE_SEG)
        units.append(Unit("example_file", rel, path=rel, size=lines_of(text), body_tokens=tokens(text),
                          pointer_dirs=["/".join(parts[: ex_root + 1])], detail=f"{lines_of(text)} lines"))
    return units


def extract_test_units(root: Path, files: list[str]) -> list[Unit]:
    groups: dict[str, int] = {}
    for rel in files:
        parts = segs(rel)
        ext = os.path.splitext(parts[-1])[1].lower()
        if ext in {".json", ".txt", ".xml", ".csv", ".png", ".jpg", ".md", ".yml", ".yaml", ".svg", ".bin", ".pdf", ".docx", ".xlsx"} or is_example_path(rel):
            continue
        if not is_test_path(rel):
            continue
        root_dir = next((("/".join(parts[: i + 1])) for i, s in enumerate(parts[:-1]) if TEST_SEG.search(s)), "/".join(parts[:-1]) or ".")
        groups[root_dir] = groups.get(root_dir, 0) + 1
    return [Unit("test_suite", d, path=d + "/", size=n, pointer_dirs=[d], use_basename=False, detail=f"{n} test file(s)")
            for d, n in sorted(groups.items()) if n >= 1]


# --- build and test commands -------------------------------------------------------------------

_SKIP_FIRST = {"sudo", "time", "xvfb-run", "env", "call", "exec", "start", "nohup", "cmd", "powershell", "pwsh", "bash", "sh"}


def command_key(segment: str) -> tuple[str, list[str]] | None:
    """Reduce one shell command to ``(kind, key words)`` when it builds or tests; else None."""
    toks = segment.strip().split()
    while toks and (toks[0] in _SKIP_FIRST or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0])):
        toks = toks[1:]
    if not toks:
        return None
    tool = re.sub(r"\.(sh|cmd|bat|exe)$", "", toks[0].replace("\\", "/").rsplit("/", 1)[-1].lower())
    rest = [t.lower() for t in toks[1:] if not t.startswith(("-", "$", "|", ">"))]
    if tool == "dotnet" and rest:
        v = rest[0]
        if v == "test":
            return "test", ["dotnet", "test"]
        if v in ("build", "publish", "pack"):
            return "build", ["dotnet", v]
    elif tool in ("mvn", "mvnw", "./mvnw"):
        for v in rest:
            if v in ("test", "verify"):
                return "test", ["mvn", v]
            if v in ("package", "install", "compile"):
                return "build", ["mvn", v]
    elif tool in ("gradle", "gradlew"):
        for v in rest:
            if v in ("test", "check"):
                return "test", ["gradle", v]
            if v in ("build", "assemble"):
                return "build", ["gradle", v]
    elif tool in ("npm", "yarn", "pnpm"):
        words = rest[1:] if rest and rest[0] == "run" else rest
        if words and words[0] in ("test", "t"):
            return "test", [tool, "test"]
        if words and words[0] == "build":
            return "build", [tool, "build"]
    elif tool == "cargo" and rest and rest[0] in ("build", "test", "check"):
        return ("build" if rest[0] != "test" else "test"), ["cargo", rest[0]]
    elif tool == "go" and rest and rest[0] in ("build", "test"):
        return ("test" if rest[0] == "test" else "build"), ["go", rest[0]]
    elif tool == "ctest":
        return "test", ["ctest"]
    elif tool == "cmake" and any(t in ("--build",) for t in toks):
        return "build", ["cmake", "--build"]
    elif tool in ("pytest", "py.test"):
        return "test", ["pytest"]
    elif tool in ("python", "python3", "py") and len(toks) > 2 and toks[1] == "-m":
        if toks[2] == "pytest":
            return "test", ["pytest"]
        if toks[2] == "unittest":
            return "test", ["unittest"]
        if toks[2] == "build":
            return "build", ["python", "-m", "build"]
    elif tool in ("tox", "nox"):
        return "test", [tool]
    elif tool in ("tsc",):
        return "build", ["tsc"]
    elif tool == "make" and rest:
        if rest[0] in ("test", "check", "verify"):
            return "test", ["make", rest[0]]
        if rest[0] in ("build", "all", "compile"):
            return "build", ["make", rest[0]]
    return None


def extract_command_units(root: Path, files: list[str]) -> list[Unit]:
    cmds: dict[tuple[str, tuple[str, ...]], list[str]] = {}

    def add(kind: str, key: list[str], source: str) -> None:
        cmds.setdefault((kind, tuple(key)), []).append(source)

    def add_line(line: str, source: str) -> None:
        for seg in re.split(r"&&|;|\|\||\|", line):
            r = command_key(seg)
            if r:
                add(r[0], r[1], source)

    has_tests = any(is_test_path(f) for f in files)
    for rel in files:
        parts, base = segs(rel), segs(rel)[-1].lower()
        if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", rel):
            try:
                doc = yaml.load(read(root, rel), Loader=yaml.BaseLoader) or {}
            except yaml.YAMLError:
                continue
            for job in ((doc.get("jobs") if isinstance(doc, dict) else None) or {}).values():
                for step in (job.get("steps") if isinstance(job, dict) else None) or []:
                    run = step.get("run") if isinstance(step, dict) else None
                    for line in (run or "").splitlines():
                        add_line(line.strip().rstrip("\\"), f"ci:{rel}")
        elif base == "package.json" and len(parts) <= 3:
            try:
                scripts = json.loads(read(root, rel)).get("scripts", {})
            except ValueError:
                continue
            if "build" in scripts:
                add("build", ["npm", "build"], f"manifest:{rel}")
            if "test" in scripts:
                add("test", ["npm", "test"], f"manifest:{rel}")
        elif base == "makefile" and len(parts) <= 2:
            for t in re.findall(r"^([A-Za-z0-9_.-]+)\s*:", read(root, rel), re.M):
                if t in ("test", "check", "verify"):
                    add("test", ["make", t], f"manifest:{rel}")
                elif t in ("build", "all", "compile"):
                    add("build", ["make", t], f"manifest:{rel}")
        elif base == "go.mod":
            add("build", ["go", "build"], f"convention:{rel}")
            if has_tests:
                add("test", ["go", "test"], f"convention:{rel}")
        elif base == "cargo.toml" and len(parts) <= 2:
            add("build", ["cargo", "build"], f"convention:{rel}")
            add("test", ["cargo", "test"], f"convention:{rel}")
        elif base.endswith((".sln", ".csproj")) and not is_aux_path(rel):
            add("build", ["dotnet", "build"], f"convention:{rel}")
            if has_tests:
                add("test", ["dotnet", "test"], f"convention:{rel}")
        elif base == "pom.xml" and len(parts) <= 2:
            add("test", ["mvn", "test"], f"convention:{rel}")
        elif base == "cmakelists.txt" and len(parts) <= 2:
            add("build", ["cmake", "--build"], f"convention:{rel}")
        elif base in ("pytest.ini", "tox.ini", "conftest.py") and len(parts) <= 2:
            add("test", ["pytest"], f"convention:{rel}")
        elif base == "pyproject.toml" and len(parts) <= 2 and "[tool.pytest" in read(root, rel):
            add("test", ["pytest"], f"convention:{rel}")
    units = []
    for (kind, key), srcs in sorted(cmds.items()):
        uniq = list(dict.fromkeys(srcs))
        units.append(Unit(f"{kind}_command", " ".join(key), command=list(key), use_basename=False,
                          detail=f"{len(uniq)} source(s): " + "; ".join(uniq[:3])))
    return units


def inventory(root: Path, release: dict | None = None) -> tuple[list[Unit], dict]:
    """All units of a clone, plus a small facts dict (readme path, file count)."""
    files = list_files(root)
    readme = find_readme(files)
    readme_text = read(root, readme) if readme else ""
    units: list[Unit] = []
    units += extract_readme_units(readme_text)
    units += extract_doc_units(root, files)
    units += extract_license_units(root, files)
    units += extract_release_unit(release)
    units += extract_cli_units(root, files)
    units += extract_framework_units(root, files)
    units += extract_matrix_units(root, files)
    units += extract_example_units(root, files)
    units += extract_test_units(root, files)
    units += extract_command_units(root, files)
    return units, {"readme": readme, "readme_text": readme_text, "files": len(files)}
