"""Static census of the non-Python portfolio (read-only shallow clones in scratchpad/portfolio).

Per repository: manifest kind and identity, toolchain floor, dependency counts, source and header
counts, README size, fences by language, fences carrying file literals, images, tests, CI workflows,
licence, fixture-like files, and registry publication (NuGet, Maven Central, npm, Go proxy,
crates.io) — probed read-only. Output: portfolio_census.json beside this file and a Markdown table.
"""

from __future__ import annotations

import os
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

# Owner/reviewer tooling (docs/REPOSITORY_LAYOUT.md) — a planning-time static census, never imported
# by src/repository_presenter and never a runtime input to the product.
REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
PORTFOLIO = Path(os.environ.get("CENSUS_CLONE_DIR", str(HERE / ".local" / "portfolio")))
REGISTRY = REPO / "data" / "registry.json"
DOC_EXT = {".xlsx", ".xls", ".csv", ".docx", ".doc", ".pdf", ".pptx", ".ppt", ".png", ".jpg", ".jpeg", ".bmp", ".gif",
           ".svg", ".obj", ".stl", ".gltf", ".glb", ".fbx", ".3mf", ".dae", ".msg", ".eml", ".mbox", ".pst", ".ttf", ".otf",
           ".woff", ".html", ".htm", ".one", ".ps", ".eps", ".xps", ".tex", ".psd", ".xml", ".txt", ".odt", ".ods", ".odp",
           ".rtf", ".epub", ".tiff", ".tif", ".ico", ".webp", ".zip"}
FENCE = re.compile(r"```([\w+#.-]*)\n(.*?)```", re.S)
FILE_LIT = re.compile(r"[\"'][\w./\\-]+\.(" + "|".join(e[1:] for e in sorted(DOC_EXT)) + r")[\"']", re.I)
SKIP_DIRS = {".git", "node_modules", "bin", "obj", "target", "build", "dist", ".venv", "vendor"}


def files_of(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts[:-1]) & SKIP_DIRS):
            yield p


def readme_facts(root: Path) -> dict:
    rd = next((p for p in root.iterdir() if p.is_file() and p.name.lower() in ("readme.md", "readme.rst", "readme")), None)
    if rd is None:
        return {"readme": None, "readme_lines": 0, "fences": {}, "fences_with_file_literals": 0, "images": 0}
    text = rd.read_text(encoding="utf-8", errors="replace")
    fences: dict[str, int] = {}
    with_files = 0
    for lang, body in FENCE.findall(text):
        fences[lang or "(none)"] = fences.get(lang or "(none)", 0) + 1
        if FILE_LIT.search(body):
            with_files += 1
    return {"readme": rd.name, "readme_lines": len(text.splitlines()), "fences": fences,
            "fences_with_file_literals": with_files, "images": len(re.findall(r"!\[", text)),
            "has_project_tree": bool(re.search(r"^[│├└]", text, re.M))}


def common_facts(root: Path) -> dict:
    fl = list(files_of(root))
    rel = [p.relative_to(root).as_posix() for p in fl]
    return {
        "files": len(fl),
        "license": any(re.match(r"licen[cs]e", Path(r).name, re.I) for r in rel if "/" not in r),
        "ci_workflows": sum(1 for r in rel if r.startswith(".github/workflows/") and r.endswith((".yml", ".yaml"))),
        "tests_present": any(re.search(r"(^|/)(tests?|__tests__|spec)(/|$)|Tests?\.csproj$|_test\.go$|/test/", r, re.I) for r in rel),
        "fixture_like_files": sum(1 for r in rel if Path(r).suffix.lower() in DOC_EXT and not r.lower().startswith(("readme", "license", ".github"))),
        **readme_facts(root),
    }


def probe(url: str, headers: dict | None = None) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "repository-presenter-census/1 (owner review)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(4000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        return e.code, ""
    except Exception as e:
        return -1, e.__class__.__name__


def net(root: Path) -> dict:
    csproj = [p for p in files_of(root) if p.suffix == ".csproj"]
    tfms, pkg_ids, refs = set(), set(), 0
    for p in csproj:
        try:
            x = ET.parse(p).getroot()
        except Exception:
            continue
        for tag in ("TargetFramework", "TargetFrameworks"):
            for el in x.iter(tag):
                tfms.update((el.text or "").split(";"))
        for el in x.iter("PackageId"):
            pkg_ids.add((el.text or "").strip())
        for el in x.iter("AssemblyName"):
            pkg_ids.add((el.text or "").strip())
        refs += sum(1 for _ in x.iter("PackageReference"))
    main = sorted(p for p in csproj if "test" not in p.name.lower())
    pkg = sorted(i for i in pkg_ids if i) or [main[0].stem] if main else []
    out = {"manifest": f"{len(csproj)} csproj" + (" + sln" if any(p.suffix == ".sln" for p in files_of(root)) else ""),
           "identity": pkg[0] if pkg else None, "floor": ",".join(sorted(t for t in tfms if t)) or None, "deps": refs,
           "sources": sum(1 for p in files_of(root) if p.suffix == ".cs"), "headers": 0}
    if out["identity"]:
        st, _ = probe(f"https://api.nuget.org/v3-flatcontainer/{out['identity'].lower()}/index.json")
        out["registry"] = "NuGet published" if st == 200 else ("NuGet not found" if st == 404 else f"NuGet probe {st}")
    return out


def java(root: Path) -> dict:
    poms = [p for p in files_of(root) if p.name == "pom.xml"]
    gradle = [p for p in files_of(root) if p.name in ("build.gradle", "build.gradle.kts")]
    out = {"manifest": f"{len(poms)} pom" + (f" + {len(gradle)} gradle" if gradle else ""), "identity": None, "floor": None, "deps": 0,
           "sources": sum(1 for p in files_of(root) if p.suffix == ".java"), "headers": 0}
    if poms:
        p = sorted(poms, key=lambda q: len(q.parts))[0]
        txt = p.read_text(encoding="utf-8", errors="replace")
        ns = re.sub(r"<project[^>]*>", "<project>", txt, count=1)
        try:
            x = ET.fromstring(ns)
            g = x.findtext("groupId") or x.findtext("parent/groupId")
            a = x.findtext("artifactId")
            out["identity"] = f"{g}:{a}" if g and a else a
            out["deps"] = len(x.findall("dependencies/dependency"))
            fl = (x.findtext("properties/maven.compiler.release") or x.findtext("properties/maven.compiler.source")
                  or x.findtext("properties/java.version") or x.findtext("properties/maven.compiler.target"))
            out["floor"] = f"java {fl}" if fl else None
            if g and a:
                st, _ = probe(f"https://repo1.maven.org/maven2/{g.replace('.', '/')}/{a}/maven-metadata.xml")
                out["registry"] = "Maven Central published" if st == 200 else ("Maven Central not found" if st == 404 else f"Maven probe {st}")
        except ET.ParseError:
            out["identity"] = "pom unparsable"
    elif gradle:
        out["floor"] = "gradle only (gradle ABSENT on machine)"
    return out


def cpp(root: Path) -> dict:
    cm = [p for p in files_of(root) if p.name == "CMakeLists.txt"]
    out = {"manifest": f"{len(cm)} CMakeLists" + (" + vcpkg.json" if (root / "vcpkg.json").exists() else "") + (" + conanfile" if any(p.name.startswith("conanfile") for p in files_of(root)) else ""),
           "identity": None, "floor": None, "deps": 0,
           "sources": sum(1 for p in files_of(root) if p.suffix in (".cpp", ".cc", ".cxx")),
           "headers": sum(1 for p in files_of(root) if p.suffix in (".h", ".hpp", ".hxx"))}
    if cm:
        top = sorted(cm, key=lambda q: len(q.parts))[0].read_text(encoding="utf-8", errors="replace")
        m = re.search(r"project\s*\(\s*([\w.-]+)", top)
        out["identity"] = m.group(1) if m else None
        s = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", top)
        out["floor"] = f"C++{s.group(1)}" if s else None
        out["deps"] = len(re.findall(r"find_package|FetchContent_Declare|ExternalProject_Add", top))
        out["registry"] = "no registry (source build)"
    return out


def typescript(root: Path) -> dict:
    pj = root / "package.json"
    out = {"manifest": "package.json" + (" + tsconfig" if (root / "tsconfig.json").exists() else ""), "identity": None, "floor": None, "deps": 0,
           "sources": sum(1 for p in files_of(root) if p.suffix in (".ts", ".tsx") and not p.name.endswith(".d.ts")), "headers": 0}
    if pj.exists():
        try:
            d = json.loads(pj.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            d = {}
        out["identity"] = d.get("name")
        eng = (d.get("engines") or {}).get("node")
        ts = (d.get("devDependencies") or {}).get("typescript") or (d.get("dependencies") or {}).get("typescript")
        out["floor"] = " ".join(x for x in (f"node {eng}" if eng else "", f"ts {ts}" if ts else "") if x) or None
        out["deps"] = len(d.get("dependencies") or {})
        out["dev_deps"] = len(d.get("devDependencies") or {})
        out["module_shape"] = ",".join(k for k in ("main", "module", "exports", "types") if k in d) or None
        if out["identity"]:
            st, _ = probe(f"https://registry.npmjs.org/{out['identity']}")
            out["registry"] = "npm published" if st == 200 else ("npm not found" if st == 404 else f"npm probe {st}")
    else:
        out["manifest"] = "NO package.json"
    return out


def go(root: Path) -> dict:
    gm = root / "go.mod"
    out = {"manifest": "go.mod" if gm.exists() else "NO go.mod", "identity": None, "floor": None, "deps": 0,
           "sources": sum(1 for p in files_of(root) if p.suffix == ".go" and not p.name.endswith("_test.go")), "headers": 0}
    if gm.exists():
        t = gm.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^module\s+(\S+)", t, re.M)
        out["identity"] = m.group(1) if m else None
        g = re.search(r"^go\s+([\d.]+)", t, re.M)
        out["floor"] = f"go {g.group(1)}" if g else None
        out["deps"] = len(re.findall(r"^\s+\S+\s+v[\d.]", t, re.M)) or len(re.findall(r"^require\s+\S+\s+v", t, re.M))
        if out["identity"]:
            st, _ = probe(f"https://proxy.golang.org/{out['identity'].lower()}/@v/list")
            out["registry"] = "Go proxy lists versions" if st == 200 else ("Go proxy: no versions" if st in (404, 410) else f"Go proxy probe {st}")
    return out


def rust(root: Path) -> dict:
    ct = root / "Cargo.toml"
    out = {"manifest": "Cargo.toml" if ct.exists() else "NO Cargo.toml", "identity": None, "floor": None, "deps": 0,
           "sources": sum(1 for p in files_of(root) if p.suffix == ".rs"), "headers": 0}
    if ct.exists():
        t = ct.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^name\s*=\s*"([^"]+)"', t, re.M)
        out["identity"] = m.group(1) if m else None
        ed = re.search(r'^edition\s*=\s*"(\d+)"', t, re.M)
        rv = re.search(r'^rust-version\s*=\s*"([^"]+)"', t, re.M)
        out["floor"] = " ".join(x for x in (f"edition {ed.group(1)}" if ed else "", f"msrv {rv.group(1)}" if rv else "") if x) or None
        dep_block = re.search(r"^\[dependencies\](.*?)(^\[|\Z)", t, re.M | re.S)
        out["deps"] = len(re.findall(r"^\s*[\w-]+\s*=", dep_block.group(1), re.M)) if dep_block else 0
        if out["identity"]:
            st, _ = probe(f"https://crates.io/api/v1/crates/{out['identity']}")
            out["registry"] = "crates.io published" if st == 200 else ("crates.io not found" if st == 404 else f"crates.io probe {st}")
    return out


ECOSYSTEM = {"net": net, "java": java, "cpp": cpp, "typescript": typescript, "go": go, "rust": rust}


def machine() -> dict:
    out = {}
    for tool, args in (("dotnet", ["--version"]), ("java", ["-version"]), ("mvn", ["-v"]), ("gradle", ["-v"]), ("cmake", ["--version"]),
                       ("cl", []), ("msbuild", ["-version"]), ("node", ["--version"]), ("npx", ["--version"]), ("go", ["version"]),
                       ("cargo", ["--version"]), ("rustup", ["--version"])):
        import shutil

        exe = shutil.which(tool) or shutil.which(tool + ".cmd") or shutil.which(tool + ".bat")
        if exe is None:
            out[tool] = "ABSENT"
            continue
        try:
            r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=60)
            line = (r.stdout or r.stderr).strip().splitlines()
            out[tool] = (line[0][:70] if line else "present") + (" (via .cmd shim - call by resolved path)" if exe.lower().endswith((".cmd", ".bat")) else "")
        except Exception as e:
            out[tool] = f"present; probe {e.__class__.__name__}"
    return out


def main() -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = []
    for e in reg["entries"]:
        eco = e["ecosystem"].lower()
        if eco.startswith("py"):
            continue
        name = e["repository"].split("/", 1)[1]
        root = PORTFOLIO / name
        row = {"repository": e["repository"], "ecosystem": eco, "family": e.get("family"), "mode": e["mode"]}
        if not root.exists():
            row["status"] = "NOT CLONED"
            rows.append(row)
            continue
        row.update(common_facts(root))
        row.update(ECOSYSTEM[eco](root))
        rows.append(row)
    data = {"census_date": "2026-09-05", "machine": machine(), "repositories": rows}
    (HERE / "portfolio_census.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("| Repo | Eco | Mode | Manifest | Identity | Floor | Deps | Src/Hdr | Files | README ln | Fences (lang) | w/ file lit | Img | Tests | CI | Lic | Fixture files | Registry |")
    print("|" + "---|" * 18)
    for r in rows:
        if r.get("status") == "NOT CLONED":
            print(f"| {r['repository']} | {r['ecosystem']} | {r['mode']} | NOT CLONED |" + " |" * 14)
            continue
        fences = ", ".join(f"{k} {v}" for k, v in sorted(r["fences"].items(), key=lambda kv: -kv[1])[:3])
        print(f"| {r['repository'].split('/')[1]} | {r['ecosystem']} | {r['mode']} | {r['manifest']} | {r.get('identity')} | {r.get('floor')} | {r.get('deps')} | "
              f"{r['sources']}/{r['headers']} | {r['files']} | {r['readme_lines']} | {fences} | {r['fences_with_file_literals']} | {r['images']} | "
              f"{'y' if r['tests_present'] else 'n'} | {r['ci_workflows']} | {'y' if r['license'] else 'n'} | {r['fixture_like_files']} | {r.get('registry', '-')} |")
    print("\nmachine:", json.dumps(data["machine"]))


if __name__ == "__main__":
    main()
