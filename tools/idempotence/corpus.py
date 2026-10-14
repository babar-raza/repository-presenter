"""The idempotence corpus: the live README of every registry repository, frozen with its checksum.

``data/idempotence/corpus.json`` has the shape of ``data/readme_standard/survey.json`` (schema
version, capture date, ``rows`` keyed by repository) but holds the README text itself instead of
measures of it, plus the head commit it was read at and its SHA-256, so a test never needs a
network, a clone or a token and a changed byte is caught by the checksum. It is the input of the
retention, fixed-point and mutation measures.

Read-only toward every repository: the builder reads ``git rev-parse HEAD`` and ``git show
HEAD:README.md`` of clones the caller already made (the committed blob, not the working copy, so
autocrlf cannot move the hash), and never fetches. A clone is untrusted data: its bytes are read
and nothing in it is run.

    python -X utf8 -m tools.idempotence build-corpus --root <clones> --captured 2026-10-12
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.readme_standard.build_survey import find_clone, head_of

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "data" / "registry.json"
DEFAULT_CORPUS = REPO_ROOT / "data" / "idempotence" / "corpus.json"
SCHEMA_VERSION = 1


class CorpusError(ValueError):
    """The corpus file is malformed or one of its READMEs does not match its checksum."""


@dataclass(frozen=True)
class Entry:
    repository: str
    head: str
    text: str
    sha256: str


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(roots: Path | Sequence[Path], registry: Path, captured: str) -> dict[str, Any]:
    entries = json.loads(registry.read_text(encoding="utf-8"))["entries"]
    rows: dict[str, Any] = {}
    for entry in entries:
        repository = entry["repository"]
        clone = find_clone(roots, repository)
        if clone is None:
            raise SystemExit(f"no clone of {repository} under {roots}")
        row: dict[str, Any] = {"head": head_of(clone)}
        shown = subprocess.run(
            ["git", "-C", str(clone), "show", "HEAD:README.md"], capture_output=True, check=False
        )
        if shown.returncode != 0:
            row["readme"] = False
        else:
            try:
                text = shown.stdout.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise SystemExit(f"{repository}: README.md is not UTF-8: {exc}") from exc
            row["readme"] = True
            row["readme_sha256"] = hashlib.sha256(shown.stdout).hexdigest()
            if digest(text) != row["readme_sha256"]:
                raise SystemExit(f"{repository}: README.md does not round-trip through UTF-8")
            row["text"] = text
        rows[repository] = row
    return {
        "schema_version": SCHEMA_VERSION,
        "captured": captured,
        "rows": rows,
    }


def write(document: dict[str, Any], out: Path) -> None:
    text = json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")


def parse(document: dict[str, Any]) -> dict[str, Entry]:
    """The entries of a corpus document, each README checked against its recorded SHA-256."""
    if document.get("schema_version") != SCHEMA_VERSION or not isinstance(
        document.get("rows"), dict
    ):
        raise CorpusError("not an idempotence corpus document of schema version 1")
    entries: dict[str, Entry] = {}
    for repository, row in sorted(document["rows"].items()):
        if not row.get("readme"):
            continue
        text, recorded = row.get("text"), row.get("readme_sha256")
        if not isinstance(text, str) or not isinstance(recorded, str):
            raise CorpusError(f"{repository}: a row with a README needs its text and checksum")
        if digest(text) != recorded:
            raise CorpusError(f"{repository}: README text does not match its recorded SHA-256")
        entries[repository] = Entry(repository, str(row["head"]), text, recorded)
    return entries


def load(path: Path = DEFAULT_CORPUS) -> dict[str, Entry]:
    return parse(json.loads(path.read_text(encoding="utf-8")))
