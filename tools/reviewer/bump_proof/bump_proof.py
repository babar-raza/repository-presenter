"""Rung 3 proof, by command: a throwaway bump of each governed constant must not invalidate a bundle.

For each sealed repository given as ``ROOT=OWNER/NAME`` (ROOT holds ``candidates/``), this runs the
real ``repository-presenter recheck`` once on the running source (the baseline: the bundle must be
current) and once per governed constant on a scratch copy of ``src`` with that constant raised by
one and nothing else changed. Nothing in the repository or in a bundle is modified.

Expected outcome, recorded in ``docs/DECISION_LOG.md`` (2026-10-15):

- baseline ``CURRENT`` (or ``RECHECKED_CURRENT``);
- ``NORMALISATION_VERSION``, ``RENDERER_VERSION``, ``REVIEWER_LOGIC_VERSION``,
  ``INHERITED_UNITS_VERSION``, ``VALIDATOR_VERSION``: ``RECHECKED_CURRENT`` (or
  ``UPDATE_OPTIONAL``), never ``UPDATE_REQUIRED``;
- ``EXTRACTOR_VERSION``: ``UNVERIFIED``. That constant is the one whose change can alter the facts
  themselves, and proving it did not needs the pinned revision cloned and re-extracted, which a
  recheck never does and the drift monitor (upstream moved) does not cover. The ladder therefore
  treats it as a bump that needs the necessity test.

Exit status is 1 when any other cell differs from that expectation.

    python tools/reviewer/bump_proof/bump_proof.py --target G:/rp-w7/cells-go=aspose-cells-foss/Aspose.Cells-FOSS-for-Go
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
README = "src/repository_presenter/components/readme"
CONSTANTS: dict[str, str] = {
    "NORMALISATION_VERSION": f"{README}/composition/authoring.py",
    "RENDERER_VERSION": f"{README}/composition/renderer.py",
    "REVIEWER_LOGIC_VERSION": f"{README}/review/independent/review.py",
    "EXTRACTOR_VERSION": f"{README}/extractors/surface/extractor.py",
    "INHERITED_UNITS_VERSION": f"{README}/evidence/facts/inherited.py",
    "VALIDATOR_VERSION": f"{README}/validation/registry.py",
}
HOLDS = {"CURRENT", "RECHECKED_CURRENT", "UPDATE_OPTIONAL"}
EXPECTED_UNVERIFIED = {"EXTRACTOR_VERSION"}


def bump(tree: Path, constant: str, relpath: str) -> str:
    """Raise the constant's last ``NAME = "N"`` assignment by one; return ``"N -> N+1"``."""
    target = tree / relpath
    text = target.read_text(encoding="utf-8")
    matches = list(re.finditer(rf'^{constant} = "(\d+)"', text, re.M))
    if not matches:
        raise SystemExit(f"{constant} not found in {relpath}")
    last = matches[-1]
    new = str(int(last.group(1)) + 1)
    target.write_text(
        text[: last.start()] + f'{constant} = "{new}"' + text[last.end() :], encoding="utf-8"
    )
    return f"{last.group(1)} -> {new}"


def recheck(src: Path, root: Path, repo: str) -> dict[str, object]:
    env = dict(os.environ, PYTHONPATH=str(src))
    env.setdefault("GIT_CEILING_DIRECTORIES", str(Path.home()))
    command = [
        sys.executable,
        "-c",
        "import sys; from repository_presenter.cli import main; sys.exit(main())",
        "recheck",
        "--root",
        str(root),
        "--repo",
        repo,
        "--json",
    ]
    done = subprocess.run(command, capture_output=True, text=True, env=env, cwd=root, check=False)
    try:
        bundle = json.loads(done.stdout)["bundles"][0]
    except (ValueError, KeyError, IndexError):
        return {"error": (done.stdout + done.stderr)[-400:]}
    return {
        "currency": bundle["currency"],
        "cost": bundle["cost"],
        "differences": bundle["differences"],
        "scopes": {s["scope"]: s["outcome"] for s in bundle["scopes"]},
    }


def judge(constant: str | None, result: dict[str, object]) -> bool:
    if "error" in result:
        return False
    currency = result["currency"]
    if constant in EXPECTED_UNVERIFIED:
        return currency == "UNVERIFIED"
    return currency in HOLDS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", action="append", required=True, metavar="ROOT=OWNER/NAME")
    parser.add_argument("--src", type=Path, default=REPO / "src")
    parser.add_argument("--out", type=Path, help="write the full result table as JSON here")
    args = parser.parse_args()
    targets = [tuple(t.rsplit("=", 1)) for t in args.target]

    rows: list[dict[str, object]] = []
    ok = True
    with tempfile.TemporaryDirectory(prefix="bump-proof-") as scratch:
        for constant, relpath in [(None, ""), *CONSTANTS.items()]:
            src = args.src
            change = "baseline"
            if constant:
                work = Path(scratch) / constant
                shutil.copytree(args.src, work / "src", ignore=shutil.ignore_patterns("__pycache__"))
                change = bump(work, constant, relpath)
                src = work / "src"
            for root, repo in targets:
                result = recheck(src, Path(root), repo)
                good = judge(constant, result)
                ok = ok and good
                rows.append({"constant": constant, "change": change, "repo": repo, **result})
                state = result.get("currency", "ERROR")
                print(f"{'ok  ' if good else 'FAIL'} {constant or 'baseline':24} {change:8} {repo} -> {state}")
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
