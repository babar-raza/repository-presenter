"""The retention report for sealed regeneration bundles: the table the acceptance reviews quote.

Reads bundle directories (a sealed candidate ``candidates/<owner>__<name>/<revision>/``, a pipeline
draft ``runs/transactions/<owner>__<name>/<revision>/`` or a correction bundle) and, for each,
compares the candidate ``README.md`` with the live README at the same revision:

* **retention**   share of the live prose (sentences and list items) kept verbatim and in any form,
                  and of live lines, code blocks, links, images and headings kept;
* **introduced**  share of the candidate's prose that neither the live README nor the bundle's facts
                  say, and the part of it that sits in an authored (model-written) content unit;
* **edit script** unified-diff hunks (three lines of context) and lines removed/added.

Where the live README comes from, in order: ``README.original.md`` (a correction bundle);
``README.patch`` reverse-applied and proven by re-diffing (``bundle.recheck.original_readme``, the
function the recheck uses); ``source/README.md`` (a draft); the corpus row whose head is this
revision; ``git show <revision>:README.md`` in a clone under ``--clones``. A bundle whose live
README cannot be found is listed as such, never skipped silently.

Read-only: it reads files and, for the last source, runs ``git show``. No network, no model.

    python -X utf8 -m tools.idempotence report <dir> [<dir> ...] [--clones DIR] [--json OUT]
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.bundle.recheck import original_readme
from tools.idempotence import corpus
from tools.idempotence.atoms import atomise
from tools.idempotence.editscript import EditScript, edit_script
from tools.idempotence.introduced import IntroducedReport, fact_texts, introduced_text
from tools.idempotence.retention import RetentionReport, retention

_REVISION = re.compile(r"[0-9a-f]{40}")
SEALED, DRAFT, CORRECTION = "sealed", "draft", "correction"


@dataclass(frozen=True)
class Bundle:
    path: Path
    slug: str  # owner__name
    revision: str
    kind: str
    readme: str
    live: str | None
    live_source: str  # patch | source | original | corpus | git | missing

    @property
    def repository(self) -> str:
        return self.slug.replace("__", "/", 1)

    def facts(self) -> list[dict[str, Any]]:
        """The bundle's facts, read when asked (a sealed ``facts.json`` is about 3 MB)."""
        path = self.path / "facts.json"
        return list(_json(path).get("facts", ())) if path.is_file() else []

    def authored(self) -> list[str] | None:
        """The texts of the authored content units, or None when the bundle has none."""
        path = self.path / "content_units.json"
        if not path.is_file():
            return None
        return [str(unit.get("text", "")) for unit in _json(path)["units"]]


@dataclass
class Row:
    bundle: Bundle
    retention: RetentionReport | None = None
    introduced: IntroducedReport | None = None
    script: EditScript | None = None
    note: str = ""

    @property
    def measured(self) -> bool:
        return self.retention is not None


def _read(path: Path) -> str:
    """The file's text with its line endings exactly as written (no universal-newline folding)."""
    return path.read_bytes().decode("utf-8")


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_show(clones: Sequence[Path], repository: str, revision: str) -> str | None:
    owner, name = repository.split("/")
    for root in clones:
        for clone in (root / name, root / f"{owner}_{name}", root / f"{owner}__{name}"):
            if not clone.is_dir():
                continue
            shown = subprocess.run(
                ["git", "-C", str(clone), "show", f"{revision}:README.md"],
                capture_output=True,
                check=False,
            )
            if shown.returncode == 0:
                return shown.stdout.decode("utf-8", errors="replace")
    return None


def load_bundle(
    path: Path,
    kind: str | None = None,
    corpus_entries: dict[str, corpus.Entry] | None = None,
    clones: Sequence[Path] = (),
) -> Bundle | None:
    """The bundle in directory ``path``, or None when it holds no candidate README."""
    readme_path = path / "README.md"
    if not readme_path.is_file():
        return None
    revision = path.name if _REVISION.fullmatch(path.name) else ""
    slug = path.parent.name
    readme = _read(readme_path)
    if (path / "README.original.md").is_file():
        original = _read(path / "README.original.md")
        manifest = path / "manifest.json"
        if manifest.is_file():
            document = _json(manifest)
            revision = revision or str(document.get("revision", ""))
            slug = str(document.get("repository", slug)).replace("/", "__")
        return Bundle(path, slug, revision, CORRECTION, readme, original, "original")
    live: str | None = None
    source = "missing"
    if (path / "README.patch").is_file():
        live = original_readme(readme, _read(path / "README.patch"))
        source = "patch" if live is not None else "missing"
    if live is None and (path / "source" / "README.md").is_file():
        live, source = _read(path / "source" / "README.md"), "source"
    repository = slug.replace("__", "/", 1)
    if live is None and corpus_entries is not None:
        entry = corpus_entries.get(repository)
        if entry is not None and entry.head == revision:
            live, source = entry.text, "corpus"
    if live is None and clones and revision:
        live = _git_show(clones, repository, revision)
        source = "git" if live is not None else "missing"
    made = kind or (SEALED if (path / "manifest.json").is_file() else DRAFT)
    return Bundle(path, slug, revision, made, readme, live, source)


def locate(roots: Iterable[Path]) -> list[tuple[Path, str | None]]:
    """Every bundle directory under ``roots`` with the kind its location implies (None: decide
    from its files). A root is a bundle directory itself, a ``candidates``-shaped directory
    (``<slug>/<revision>/``), a pipeline checkout (``candidates/`` and ``runs/transactions/``) or a
    corrections directory (``<run>/<slug>/`` with ``README.original.md``)."""
    found: list[tuple[Path, str | None]] = []

    def scan(base: Path, kind: str | None) -> None:
        if not base.is_dir():
            return
        for first in sorted(p for p in base.iterdir() if p.is_dir()):
            if (first / "README.md").is_file():
                found.append((first, kind))
            for second in sorted(p for p in first.iterdir() if p.is_dir()):
                if (second / "README.md").is_file():
                    found.append((second, kind))

    for root in roots:
        if (root / "README.md").is_file() and (
            _REVISION.fullmatch(root.name) or (root / "README.original.md").is_file()
        ):
            found.append((root, None))
            continue
        scan(root / "candidates", None)
        scan(root / "runs" / "transactions", DRAFT)
        scan(root / "corrections", CORRECTION)
        if not ((root / "candidates").is_dir() or (root / "runs").is_dir()):
            scan(root, None)
    return found


def _key(path: Path) -> tuple[str, str, str]:
    """Identity of a bundle without loading it: where it sits and the digest of its candidate."""
    digest = hashlib.sha256((path / "README.md").read_bytes()).hexdigest()
    return (path.parent.name, path.name if _REVISION.fullmatch(path.name) else "", digest)


def stamp(path: Path) -> str:
    """When the bundle was made, as ``YYYY-MM-DDTHH:MM:SSZ``: a sealed bundle's ``sealed_at``,
    else the modification time of its README (a draft or correction has no sealing time)."""
    manifest = path / "manifest.json"
    if manifest.is_file():
        sealed = _json(manifest).get("sealed_at")
        if isinstance(sealed, str):
            return sealed
    moment = datetime.fromtimestamp((path / "README.md").stat().st_mtime, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def discover(
    roots: Iterable[Path],
    corpus_entries: dict[str, corpus.Entry] | None = None,
    clones: Sequence[Path] = (),
    exclude: Iterable[Path] = (),
    since: str | None = None,
) -> list[Bundle]:
    """Every bundle under ``roots`` (see ``locate``), each listed once: the same slug, revision and
    candidate bytes found in several checkouts count as one, a bundle that is also under one of
    ``exclude`` is left out (to report only what a run added to the committed candidates), and
    with ``since`` (``YYYY-MM-DDTHH:MM:SSZ``) a bundle made earlier is left out (a checkout carries
    the sealed candidates it started from)."""
    skip = {_key(path) for path, _ in locate(exclude)}
    chosen: dict[tuple[str, str, str], tuple[Path, str | None]] = {}
    for path, kind in locate(roots):
        key = _key(path)
        if key in skip or (since is not None and stamp(path) < since):
            continue
        chosen.setdefault(key, (path, kind))
    loaded = (load_bundle(path, kind, corpus_entries, clones) for path, kind in chosen.values())
    return sorted((b for b in loaded if b is not None), key=lambda b: (b.slug, b.revision, b.kind))


def measure(bundle: Bundle) -> Row:
    if bundle.live is None:
        return Row(bundle, note="the live README at this revision was not found")
    live = atomise(bundle.live)
    return Row(
        bundle,
        retention(bundle.live, bundle.readme),
        introduced_text(live, bundle.readme, fact_texts(bundle.facts()), bundle.authored()),
        edit_script(bundle.live, bundle.readme),
    )


def measure_all(bundles: Iterable[Bundle]) -> list[Row]:
    return [measure(b) for b in bundles]


def _pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def _ratio(category: Any) -> str:
    return f"{category.kept}/{category.total}" if category.total else "-"


def render_table(rows: Sequence[Row]) -> str:
    head = (
        "| repository | rev | kind | live from | prose verbatim | prose kept | lines kept | links "
        "| images | code | headings | introduced (llm) | hunks (runs) | +/- lines |"
    )
    out = [head, "|" + "---|" * 14]
    measured = [r for r in rows if r.measured]
    for row in rows:
        name = row.bundle.repository
        if not row.measured:
            out.append(
                f"| {name} | {row.bundle.revision[:8]} | {row.bundle.kind} "
                f"| {row.bundle.live_source} | {row.note} |" + " |" * 9
            )
            continue
        r, i, s = row.retention, row.introduced, row.script
        assert r is not None and i is not None and s is not None
        llm = i.llm_share
        introduced = f"{_pct(i.share)} ({_pct(llm) if llm is not None else '?'})"
        out.append(
            f"| {name} | {row.bundle.revision[:8]} | {row.bundle.kind} | {row.bundle.live_source} "
            f"| {_pct(r.prose.verbatim_share) if r.prose.total else '-'} "
            f"| {_pct(r.prose.kept_share) if r.prose.total else '-'} "
            f"| {_pct(r.lines.share) if r.lines.eligible else '-'} "
            f"| {_ratio(r.categories['link'])} "
            f"| {_ratio(r.categories['image'])} | {_ratio(r.categories['code'])} "
            f"| {_ratio(r.categories['heading'])} | {introduced} | {s.hunks} ({s.runs}) "
            f"| +{s.added}/-{s.removed} |"
        )
    if measured:
        out.append("")
        out.append(render_summary(measured))
    return "\n".join(out) + "\n"


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def summary(measured: Sequence[Row]) -> dict[str, Any]:
    reports = [(r.retention, r.introduced, r.script) for r in measured]
    prose_total = sum(x.prose.total for x, _, _ in reports if x)
    prose_verbatim = sum(x.prose.verbatim for x, _, _ in reports if x)
    prose_kept = sum(x.prose.kept for x, _, _ in reports if x)
    cand_total = sum(i.total for _, i, _ in reports if i)
    cand_introduced = sum(len(i.introduced) for _, i, _ in reports if i)
    cand_llm = sum(i.llm for _, i, _ in reports if i)
    return {
        "bundles": len(measured),
        "prose_atoms": prose_total,
        "prose_verbatim_share": prose_verbatim / prose_total if prose_total else 0.0,
        "prose_kept_share": prose_kept / prose_total if prose_total else 0.0,
        "lines_kept_share": (
            sum(x.lines.kept for x, _, _ in reports if x)
            / max(1, sum(x.lines.eligible for x, _, _ in reports if x))
        ),
        "candidate_prose_atoms": cand_total,
        "introduced_share": cand_introduced / cand_total if cand_total else 0.0,
        "introduced_llm_share": cand_llm / cand_total if cand_total else 0.0,
        "median_hunks": _median([s.hunks for _, _, s in reports if s]),
        "median_runs": _median([s.runs for _, _, s in reports if s]),
        "min_hunks": min((s.hunks for _, _, s in reports if s), default=0),
        "max_hunks": max((s.hunks for _, _, s in reports if s), default=0),
    }


def render_summary(measured: Sequence[Row]) -> str:
    s = summary(measured)
    return (
        f"Pooled over {s['bundles']} bundles: live prose {s['prose_atoms']} atoms, "
        f"{_pct(s['prose_verbatim_share'])} verbatim, "
        f"{_pct(s['prose_kept_share'])} kept in any form; "
        f"live non-diagram lines kept {_pct(s['lines_kept_share'])}; candidate prose "
        f"{s['candidate_prose_atoms']} atoms, {_pct(s['introduced_share'])} introduced "
        f"({_pct(s['introduced_llm_share'])} in authored units); unified-diff hunks median "
        f"{s['median_hunks']:g} (min {s['min_hunks']:g}, max {s['max_hunks']:g}), separate runs of "
        f"changed lines median {s['median_runs']:g}.\n"
    )


def rows_json(rows: Sequence[Row]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        entry: dict[str, Any] = {
            "repository": row.bundle.repository,
            "revision": row.bundle.revision,
            "kind": row.bundle.kind,
            "live_source": row.bundle.live_source,
            "path": str(row.bundle.path),
        }
        if row.retention and row.introduced and row.script:
            r, i, s = row.retention, row.introduced, row.script
            entry.update(
                {
                    "categories": {
                        kind: {
                            "total": c.total,
                            "verbatim": c.verbatim,
                            "kept": c.kept,
                            "lost": [
                                {"line": a.line, "section": a.section, "text": a.text[:160]}
                                for a in c.lost
                            ],
                        }
                        for kind, c in r.categories.items()
                    },
                    "prose": {
                        "total": r.prose.total,
                        "verbatim": r.prose.verbatim,
                        "kept": r.prose.kept,
                    },
                    "lines": {
                        "eligible": r.lines.eligible,
                        "kept": r.lines.kept,
                        "present": r.lines.present,
                        "diagram": r.lines.diagram,
                        "lost": [{"line": ln.number, "text": ln.text[:160]} for ln in r.lines.lost],
                    },
                    "introduced": {
                        "total": i.total,
                        "from_live": i.from_live,
                        "from_facts": i.from_facts,
                        "introduced": len(i.introduced),
                        "llm": i.llm if i.units_known else None,
                    },
                    "edit_script": {
                        "hunks": s.hunks,
                        "runs": s.runs,
                        "added": s.added,
                        "removed": s.removed,
                    },
                }
            )
        else:
            entry["note"] = row.note
        out.append(entry)
    return out
