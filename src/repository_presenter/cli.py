"""The single command-line entry point, ``repository-presenter``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from repository_presenter import __version__
from repository_presenter.core.candidates import BundleError, count_current_candidates
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.loader import (
    REGISTRY_RELATIVE_PATH,
    load_registry,
    require_listed,
)
from repository_presenter.core.secrets import configured_secrets, find_secret_leaks
from repository_presenter.core.snapshot.capture import (
    capture_snapshot,
    verify_snapshot,
    write_source_artifacts,
)
from repository_presenter.cursor import (
    CURSOR_RELATIVE_PATH,
    CursorError,
    find_project_root,
    load_cursor,
)

PROGRAM = "repository-presenter"
RUNS_DIRNAME = "runs"
EXIT_OK = 0
EXIT_INCONSISTENT = 1
EXIT_USAGE = 2
EXIT_UNSAFE = 3


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for every subcommand."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Keep the README files of authorized repositories accurate and current.",
    )
    parser.add_argument("--version", action="version", version=f"{PROGRAM} {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    root_help = (
        f"project root holding {CURSOR_RELATIVE_PATH.as_posix()}; "
        "discovered from the working directory when omitted"
    )
    status = subcommands.add_parser(
        "status",
        help="report the current gate and current reviewable no-op-proven candidates",
    )
    status.add_argument("--root", type=Path, default=None, help=root_help)
    present = subcommands.add_parser(
        "present",
        help="run the README transaction for one admitted repository",
    )
    present.add_argument(
        "--repo",
        required=True,
        metavar="OWNER/NAME",
        help="repository coordinates exactly as listed in the registry",
    )
    present.add_argument("--root", type=Path, default=None, help=root_help)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return run_status(args.root)
    if args.command == "present":
        return run_present(args.repo, args.root)
    parser.error(f"unknown command {args.command!r}")


def run_status(root_argument: Path | None) -> int:
    """Print version, gate, work item, and N/34 progress from sealed bundles on disk."""
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        cursor = load_cursor(root)
        leaks = find_secret_leaks(root, configured_secrets(os.environ))
        on_disk = count_current_candidates(root)
    except (CursorError, BundleError, OSError) as exc:
        _fail(str(exc))
        return EXIT_INCONSISTENT
    if leaks:
        for leak in leaks:
            relative = leak.path.relative_to(root).as_posix()
            _fail(f"secret canary: value of {leak.variable} found in {relative}")
        return EXIT_UNSAFE
    print(f"{PROGRAM} {__version__}")
    print(f"gate: {cursor.current_gate_id} ({cursor.current_gate_status})")
    print(f"work item: {cursor.active_work_item_id} ({cursor.active_work_item_status})")
    print(f"candidates: {on_disk}/{cursor.denominator} current reviewable no-op-proven")
    print(f"canary: {cursor.canary}")
    if on_disk != cursor.recorded_candidates:
        _fail(
            f"cursor records {cursor.recorded_candidates} current candidates "
            f"but {on_disk} sealed on disk"
        )
        return EXIT_INCONSISTENT
    return EXIT_OK


def run_present(repository: str, root_argument: Path | None) -> int:
    """Admit ``repository`` from the registry, then run the transaction stages."""
    root = _resolve_root(root_argument)
    if root is None:
        return EXIT_USAGE
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
        entry = require_listed(registry, repository)
        print(
            f"admitted: {entry.repository} (mode {entry.mode}, ecosystem {entry.ecosystem}, "
            f"family {entry.family}, platform {entry.platform})"
        )
        clone = pinned_read_only_clone(
            entry.clone_url,
            root / RUNS_DIRNAME / "clones" / f"{entry.owner}__{entry.name}",
            token=os.environ.get("GH_TOKEN") or None,
        )
        print(
            f"snapshot: {entry.repository} at {clone.revision} in "
            f"{clone.path.relative_to(root).as_posix()} (push disabled, verified)"
        )
        snapshot = capture_snapshot(entry.repository, clone)
        transaction = (
            root / RUNS_DIRNAME / "transactions" / f"{entry.owner}__{entry.name}" / clone.revision
        )
        artifacts = write_source_artifacts(snapshot, clone.path, transaction / "source")
        verify_snapshot(snapshot, clone.path)
    except PresenterError as exc:
        _fail(str(exc))
        return exc.exit_code
    print(
        f"source: {artifacts.directory.relative_to(root).as_posix()} "
        f"({len(artifacts.files)} files, {snapshot.tree_entries} tree entries, "
        f"readme {snapshot.readme_path or 'absent'}, digest {artifacts.digest})"
    )
    _fail("present: the facts stage is not implemented at this revision")
    return EXIT_INCONSISTENT


def _resolve_root(root_argument: Path | None) -> Path | None:
    """Return the project root, printing the usage failure when it cannot be found."""
    if root_argument is None:
        root = find_project_root(Path.cwd())
        if root is None:
            _fail(f"no {CURSOR_RELATIVE_PATH.as_posix()} found at or above {Path.cwd()}")
        return root
    root = root_argument.resolve()
    if not (root / CURSOR_RELATIVE_PATH).is_file():
        _fail(f"no {CURSOR_RELATIVE_PATH.as_posix()} under {root}")
        return None
    return root


def _fail(message: str) -> None:
    print(f"{PROGRAM}: {message}", file=sys.stderr)
