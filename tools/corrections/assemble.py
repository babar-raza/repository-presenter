"""Assemble ``corrections/<run-id>/`` from a correction run: the pull request the owner reviews.

The correction wave (docs/OPERATIONS_RUNBOOK.md section 12) proposes README corrections through the
hosted ``propose.yml`` in its correction mode, which reads each bundle from a *committed* directory,
``corrections/<run-id>/<owner>__<name>/``. This tool writes that directory, locally and from files
only. It holds no write path to any GitHub repository and reads GitHub only through the one command
it runs when it drafts the authorization records (``draft-proposal-authorization``, whose live read
is ``GH_TOKEN``'s, as for any record).

Input: a run directory holding one ``correct-readme --out`` bundle per repository,
``<run>/<owner>__<name>/`` (a ``status.json`` there means the repository had nothing to correct).
Only the repositories the owner approved are assembled, each named with ``--repo`` (or listed in
``--repos-file``): there is no "all".

For each, in order, and none of it is kept if any of it fails:

1. the bundle passes the typed correction gate (``load_proposable_correction``) against the
   production registry, and no hold is recorded for it (``data/correction_holds.json``);
2. exactly the bundle's files are copied - ``manifest.json``, ``README.md``, ``README.original.md``,
   ``README.patch``, ``corrections.json``, ``validation_delta.json``, ``facts.json``, ``tree.txt`` -
   nothing else from the run directory (no status file, clone, log or working file);
3. ``PULL_REQUEST.md`` is written: the title and body the effect will post, for the reviewer to read
   in the diff, and ``SHA256SUMS`` over all nine files;
4. the committed shape is verified with the check the workflow's command applies (``--require-sums``);
5. unless ``--no-records``: ``data/registry.json`` gets ``mode: full`` for exactly these repositories
   (the wave's own minimal edit), and ``draft-proposal-authorization --correction-bundle`` writes
   each record into ``ops/proposal-authorizations/`` for ``--approver``.

It prints what to review and the paced ``gh workflow run`` lines for the dry runs and then the real
dispatches, and never runs them. The records authorize nothing until the pull request that adds
them is merged to main.

    PYTHONPATH=src python tools/corrections/assemble.py --root . --run runs/correct/1012 \\
        --run-id 2026-10-12 --repo aspose-3d-foss/Aspose.3D-FOSS-for-Java --approver babar-raza
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from repository_presenter import cli
from repository_presenter.components.propose.wave import _registry_with_full
from repository_presenter.components.readme_correction.committed import (
    BUNDLE_FILES,
    PULL_REQUEST_NAME,
    pull_request_text,
    write_sums,
)
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.components.readme_correction.run import STATUS_NAME
from repository_presenter.components.readme_correction.send import load_holds
from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    CURRENT_POLICY_VERSION,
    record_filename,
)
from repository_presenter.core.authorization.refusals import WriteRefusedError
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.registry.loader import load_registry, require_listed

CORRECTIONS_DIRNAME = Path("corrections")
REGISTRY_RELATIVE = Path("data") / "registry.json"
CONTROL = "babar-raza/repository-presenter"
WORKFLOW = "propose.yml"
#: The same pattern ``propose.yml`` validates ``correction_run`` against.
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
PAUSE_SECONDS = 30


class AssemblyError(Exception):
    """A refusal to assemble; nothing has been written (or everything written was removed)."""


@dataclass(frozen=True)
class Row:
    repository: str
    revision: str
    candidate_hash: str
    summary: dict[str, int]
    pr_order: int | None
    bundle: str
    record: str | None


def slug(repository: str) -> str:
    return repository.replace("/", "__")


def _stage(source: Path, staged: Path) -> None:
    staged.mkdir(parents=True)
    for name in BUNDLE_FILES:
        original = source / name
        if original.is_symlink() or not original.is_file():
            raise AssemblyError(f"{source.name}: {name} is missing from the correction run")
        shutil.copyfile(original, staged / name)


def _hold_reason(repository: str) -> str | None:
    hold = load_holds().get(repository)
    if hold is None:
        return None
    return (
        f"{hold['reason_code']}: {hold['reason']} (pair with {hold['pair_with']}, recorded "
        f"{hold['recorded']}); remove the hold from data/correction_holds.json first"
    )


def assemble(
    root: Path,
    run_directory: Path,
    run_id: str,
    repositories: Sequence[str],
    *,
    approver: str,
    hours: int = 168,
    records: bool = True,
) -> list[Row]:
    """Write ``corrections/<run_id>/`` (and, with ``records``, the registry flip and the records)
    into ``root``, a control-repository worktree; leave ``root`` as it was on any failure."""
    if not RUN_ID.match(run_id) or ".." in run_id:
        raise AssemblyError(
            f"--run-id {run_id!r} must be 1-64 of [A-Za-z0-9._-], starting alphanumeric: it is "
            "the propose.yml correction_run input"
        )
    if not repositories:
        raise AssemblyError("name the approved repositories with --repo (there is no 'all')")
    if len(set(repositories)) != len(repositories):
        raise AssemblyError("a repository is named twice")
    destination = root / CORRECTIONS_DIRNAME / run_id
    if destination.exists():
        raise AssemblyError(
            f"{destination.relative_to(root).as_posix()} exists: a committed run is never "
            "rewritten; pick a new --run-id"
        )
    registry = load_registry(root / REGISTRY_RELATIVE)
    entries = {name: require_listed(registry, name) for name in repositories}

    # Directories this call may create: removed again on failure if it did and they are empty.
    created = [
        directory
        for directory in (
            root / AUTHORIZATION_DIRNAME,
            root / AUTHORIZATION_DIRNAME.parent,
            root / CORRECTIONS_DIRNAME,
        )
        if not directory.exists()
    ]
    work = Path(tempfile.mkdtemp(prefix="corrections-assemble-"))
    registry_path = root / REGISTRY_RELATIVE
    original_registry = registry_path.read_bytes()
    drafted: list[Path] = []
    try:
        rows: list[Row] = []
        staging = work / "run"
        for repository in repositories:
            source = run_directory / slug(repository)
            if not (source / "manifest.json").is_file():
                status = source / STATUS_NAME
                why = (
                    json.loads(status.read_text(encoding="utf-8")).get("reason", "")
                    if status.is_file()
                    else "no bundle in the run directory"
                )
                raise AssemblyError(f"{repository}: there is no correction bundle to assemble: {why}")
            held = _hold_reason(repository)
            if held is not None:
                raise AssemblyError(f"{repository} is held: {held}")
            proven = load_proposable_correction(
                source, repository, root=root, entry=entries[repository]
            )
            staged = staging / slug(repository)
            _stage(source, staged)
            text = pull_request_text(
                compose_correction_pull_request(
                    bundle=staged,
                    repository=repository,
                    candidate_hash=proven.candidate_hash,
                    source_revision=proven.revision,
                    policy_version=CURRENT_POLICY_VERSION,
                )
            )
            (staged / PULL_REQUEST_NAME).write_bytes(text.encode("utf-8"))
            write_sums(staged)
            committed = load_proposable_correction(
                staged, repository, root=root, entry=entries[repository], require_sums=True
            )
            if committed.candidate_hash != proven.candidate_hash:
                raise AssemblyError(f"{repository}: the staged copy differs from the run's bundle")
            document = json.loads((staged / "corrections.json").read_text(encoding="utf-8"))
            rows.append(
                Row(
                    repository,
                    proven.revision,
                    proven.candidate_hash,
                    dict(document.get("summary", {})),
                    (document.get("send") or {}).get("pr_order"),
                    (CORRECTIONS_DIRNAME / run_id / slug(repository)).as_posix(),
                    None,
                )
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging, destination)

        if records:
            registry_path.write_text(
                _registry_with_full(root, set(repositories)), encoding="utf-8", newline="\n"
            )
            finished: list[Row] = []
            for row in rows:
                record = (
                    root / AUTHORIZATION_DIRNAME / record_filename(row.repository, row.candidate_hash)
                )
                existed = record.exists()
                code = cli.main(
                    [
                        "draft-proposal-authorization",
                        "--repo",
                        row.repository,
                        "--root",
                        str(root),
                        "--correction-bundle",
                        str(root / row.bundle),
                        "--approver",
                        approver,
                        "--expires-in-hours",
                        str(hours),
                    ]
                )
                if code != 0:
                    raise AssemblyError(
                        f"{row.repository}: draft-proposal-authorization ended {code} (see above)"
                    )
                if not existed:
                    drafted.append(record)
                finished.append(replace(row, record=record.relative_to(root).as_posix()))
            rows = finished
        return rows
    except BaseException:  # leave the worktree exactly as it was: no half-assembled pull request
        shutil.rmtree(destination, ignore_errors=True)
        registry_path.write_bytes(original_registry)
        for record in drafted:
            record.unlink(missing_ok=True)
        for directory in created:
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def dispatch_plan(run_id: str, rows: Sequence[Row]) -> list[str]:
    """The paced ``gh workflow run`` lines: every dry run first, then every real dispatch."""
    lines: list[str] = []
    for write in (False, True):
        lines.append(
            "# --- the real dispatches (do_propose=true), one at a time, after the dry runs are green"
            if write
            else "# --- dry runs (do_propose omitted: plan and authorization decision, no write)"
        )
        for index, row in enumerate(rows):
            if row.record is None:
                continue
            line = (
                f"gh workflow run {WORKFLOW} -R {CONTROL} --ref main -f repo={row.repository} "
                f"-f correction_run={run_id} -f authorization_record={row.record}"
            )
            lines.append(line + (" -f do_propose=true" if write else ""))
            if index != len(rows) - 1:
                lines.append(f"sleep {PAUSE_SECONDS}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="a control-repository worktree")
    parser.add_argument("--run", type=Path, required=True, help="the correction run directory")
    parser.add_argument("--run-id", required=True, help="corrections/<run-id>/; the correction_run input")
    parser.add_argument("--repo", action="append", default=[], metavar="OWNER/NAME")
    parser.add_argument("--repos-file", type=Path, help="one OWNER/NAME per line (# comments)")
    parser.add_argument("--approver", help="the owner's GitHub login (required unless --no-records)")
    parser.add_argument("--hours", type=int, default=168, help="record lifetime, at most 168")
    parser.add_argument(
        "--no-records",
        action="store_true",
        help="write the bundles only: no registry flip, no records, no GitHub read",
    )
    args = parser.parse_args(argv)
    repositories = list(args.repo)
    if args.repos_file is not None:
        for line in args.repos_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                repositories.append(line)
    if not args.no_records and not args.approver:
        parser.error("--approver is required (or pass --no-records)")
    root = args.root.resolve()
    try:
        rows = assemble(
            root,
            args.run.resolve(),
            args.run_id,
            repositories,
            approver=args.approver or "",
            hours=args.hours,
            records=not args.no_records,
        )
    except (AssemblyError, WriteRefusedError, PresenterError, FileExistsError, OSError) as exc:
        print(f"corrections: assemble: {exc}", file=sys.stderr)
        return 2
    print(f"corrections: assembled {len(rows)} correction(s) as corrections/{args.run_id}/")
    for row in rows:
        kinds = ", ".join(f"{kind} {count}" for kind, count in sorted(row.summary.items()))
        print(
            f"  {row.repository}  rev {row.revision[:12]}  hash {row.candidate_hash[:12]}  "
            f"order {row.pr_order}  [{kinds}]"
        )
    print("corrections: review the diff, then commit these paths in ONE pull request:")
    print(f"  git add corrections/{args.run_id}")
    if not args.no_records:
        print(f"  git add {REGISTRY_RELATIVE.as_posix()}")
        for row in rows:
            print(f"  git add {row.record}")
        print("corrections: the records authorize nothing until that pull request is merged to main")
        print("corrections: after the merge (never run by this tool):")
        for line in dispatch_plan(args.run_id, rows):
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
