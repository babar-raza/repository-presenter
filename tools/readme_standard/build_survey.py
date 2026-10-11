"""Rebuild data/readme_standard/survey.json from clones of the registry repositories.

Read-only: it reads each clone's ``README.md`` bytes and ``git rev-parse HEAD`` and writes one
JSON file. It never clones, fetches, or contacts a network; clone the repositories first (shallow,
GET-only) and point ``--root`` at the directory that holds them. A clone is found as
``<root>/<name>``, ``<root>/<owner>_<name>`` or ``<root>/<owner>__<name>``.

    python -X utf8 -m tools.readme_standard.build_survey --root <clones> --captured 2026-10-11

Downloaded clones are untrusted data: this reads bytes and never imports or runs anything in them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from tools.readme_standard import survey_features
except ModuleNotFoundError:  # run as a script from another directory
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.readme_standard import survey_features

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "data" / "registry.json"
DEFAULT_OUT = REPO_ROOT / "data" / "readme_standard" / "survey.json"


def find_clone(root: Path, repository: str) -> Path | None:
    owner, name = repository.split("/")
    for candidate in (root / name, root / f"{owner}_{name}", root / f"{owner}__{name}"):
        if candidate.is_dir():
            return candidate
    return None


def head_of(clone: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def build(root: Path, registry: Path, captured: str) -> dict[str, Any]:
    entries = json.loads(registry.read_text(encoding="utf-8"))["entries"]
    rows: dict[str, Any] = {}
    for entry in entries:
        repository = entry["repository"]
        clone = find_clone(root, repository)
        if clone is None:
            raise SystemExit(f"no clone of {repository} under {root}")
        row: dict[str, Any] = {"head": head_of(clone)}
        # The committed blob, not the working copy: autocrlf must not move the hash.
        shown = subprocess.run(
            ["git", "-C", str(clone), "show", "HEAD:README.md"], capture_output=True, check=False
        )
        if shown.returncode != 0:
            row["readme"] = False
        else:
            data = shown.stdout
            row["readme"] = True
            row["readme_sha256"] = hashlib.sha256(data).hexdigest()
            row.update(survey_features.features(data.decode("utf-8"), clone))
        rows[repository] = row
    return {
        "schema_version": 1,
        "features_version": survey_features.FEATURES_VERSION,
        "captured": captured,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, required=True, help="directory holding the clones")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--captured", required=True, help="capture date, YYYY-MM-DD")
    args = parser.parse_args(argv)
    survey = build(args.root, args.registry, args.captured)
    text = json.dumps(survey, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.out} ({len(survey['rows'])} repositories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
