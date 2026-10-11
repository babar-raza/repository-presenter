"""Seed the sandbox clone's working tree with a product repository's files (one-off, local only).

The sandbox canary (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) proposes a README correction to
``babar-raza/presenter-sandbox``. A correction needs facts, and facts need the product's source
tree, not only its README: a README-and-LICENSE repository is a placeholder the pipeline refuses
(``insufficient_evidence``). So the sandbox is seeded with a copy of one real product at one pinned
revision, once, by the owner.

This module only edits files on the owner's disk. It never commits, never pushes, never contacts a
network and never changes the product clone. The owner reviews ``git status`` in the sandbox clone,
commits, and pushes with the owner's own credentials (a fast-forward: no force, no history
rewrite); that push is the one write the seeding needs, to the owner's own throwaway repository.

What it does, and refuses:

* copies exactly the blobs the product clone's ``HEAD`` commit holds (read with ``git cat-file``,
  so no line-ending filter or working-tree edit can alter a byte), and nothing untracked;
* removes the sandbox's tracked files that the product does not have, so the sandbox becomes a
  faithful copy, not a merge (the sandbox's previous contents stay in its git history);
* drops ``.github/`` (workflows and issue templates would run, or be offered, in the sandbox) and
  says so;
* refuses a symbolic link, a submodule, an absolute or ``..`` path, an oversized file, an oversized
  tree, and a sandbox clone with uncommitted changes;
* refuses a sandbox clone whose ``origin`` is not ``babar-raza/presenter-sandbox``.

    python tools/canary/seed.py --product DIR --sandbox DIR            # plan only, writes nothing
    python tools/canary/seed.py --product DIR --sandbox DIR --apply    # edit the sandbox working tree
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

SANDBOX_REMOTE = re.compile(r"github\.com[:/]babar-raza/presenter-sandbox(?:\.git)?/?$")
#: Paths that must not travel: anything that would make the sandbox run or offer automation.
DROPPED_PREFIXES = (".github/",)
MAX_FILE_BYTES = 5_000_000
MAX_TOTAL_BYTES = 40_000_000
MAX_FILES = 5_000
_SYMLINK, _SUBMODULE = "120000", "160000"


class SeedError(Exception):
    """A refusal: nothing was changed."""


@dataclass(frozen=True)
class Blob:
    path: str
    sha: str
    size: int


@dataclass
class SeedPlan:
    product_revision: str
    copy: list[Blob] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(blob.size for blob in self.copy)


def git(directory: Path, *args: str, binary: bool = False) -> str | bytes:
    done = subprocess.run(["git", *args], cwd=directory, capture_output=True, check=False)
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", errors="replace").strip()
        raise SeedError(f"git {' '.join(args[:2])} failed in {directory}: {detail}")
    return done.stdout if binary else done.stdout.decode("utf-8")


def _text(directory: Path, *args: str) -> str:
    out = git(directory, *args)
    assert isinstance(out, str)
    return out


def head_tree(product: Path) -> list[tuple[str, Blob]]:
    """``(mode, blob)`` for every entry of the product's ``HEAD`` tree, from ``git ls-tree``."""
    entries = []
    for record in filter(None, _text(product, "ls-tree", "-r", "-l", "-z", "HEAD").split("\0")):
        meta, _, path = record.partition("\t")
        mode, _kind, sha, size = meta.split()
        entries.append((mode, Blob(path, sha, 0 if size == "-" else int(size))))
    return entries


def _plain(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(pure.parts) and not pure.is_absolute() and not {"..", ".git"} & set(pure.parts)


def plan_seed(product: Path, sandbox: Path, *, check_remote: bool = True) -> SeedPlan:
    """What seeding would do, or :class:`SeedError`. Reads both clones; changes neither."""
    if _text(sandbox, "status", "--porcelain").strip():
        raise SeedError(f"{sandbox} has uncommitted changes: commit or discard them first")
    if check_remote:
        remote = _text(sandbox, "remote", "get-url", "origin").strip()
        if not SANDBOX_REMOTE.search(remote):
            raise SeedError(
                f"{sandbox}'s origin is not babar-raza/presenter-sandbox ({remote!r}); "
                "seeding refuses any other repository"
            )
    plan = SeedPlan(product_revision=_text(product, "rev-parse", "HEAD").strip())
    for mode, blob in head_tree(product):
        if mode in (_SYMLINK, _SUBMODULE):
            kind = "symbolic link" if mode == _SYMLINK else "submodule"
            raise SeedError(f"{blob.path} is a {kind}")
        if not _plain(blob.path):
            raise SeedError(f"{blob.path!r} is not a plain repository-relative path")
        if blob.path.startswith(DROPPED_PREFIXES):
            plan.dropped.append(blob.path)
            continue
        if blob.size > MAX_FILE_BYTES:
            raise SeedError(f"{blob.path} is {blob.size} bytes (limit {MAX_FILE_BYTES})")
        plan.copy.append(blob)
    if len(plan.copy) > MAX_FILES or plan.total_bytes > MAX_TOTAL_BYTES:
        raise SeedError(f"{len(plan.copy)} files / {plan.total_bytes} bytes exceed the sandbox limits")
    if not any(blob.path == "README.md" for blob in plan.copy):
        raise SeedError("the product has no README.md at its root: nothing to correct")
    keep = {blob.path for blob in plan.copy}
    sandbox_files = _text(sandbox, "ls-files", "-z").split("\0")
    plan.remove = [path for path in sandbox_files if path and path not in keep]
    return plan


def apply_seed(plan: SeedPlan, product: Path, sandbox: Path) -> None:
    """Make the sandbox working tree match the plan. Edits files only; no git state changes."""
    for path in plan.remove:
        (sandbox / path).unlink(missing_ok=True)
    for blob in plan.copy:
        data = git(product, "cat-file", "blob", blob.sha, binary=True)
        assert isinstance(data, bytes)
        target = sandbox / blob.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for directory in sorted({Path(p).parent for p in plan.remove}, key=lambda d: -len(d.parts)):
        try:  # directories the removals emptied; a non-empty one stays
            (sandbox / directory).rmdir()
        except OSError:
            pass


def commit_message(plan: SeedPlan, product_name: str) -> str:
    return f"Seed the sandbox with {product_name} at {plan.product_revision}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--product", type=Path, required=True, help="a clone of the product, HEAD at the revision to copy")
    parser.add_argument("--sandbox", type=Path, required=True, help="a clean clone of babar-raza/presenter-sandbox")
    parser.add_argument("--apply", action="store_true", help="edit the sandbox working tree (default: plan only)")
    args = parser.parse_args(argv)
    try:
        plan = plan_seed(args.product, args.sandbox)
        print(f"seed: product revision {plan.product_revision}")
        print(f"seed: copy {len(plan.copy)} files ({plan.total_bytes} bytes)")
        print(f"seed: remove {len(plan.remove)} sandbox file(s): {', '.join(plan.remove) or 'none'}")
        print(f"seed: drop {len(plan.dropped)} automation file(s) under .github/")
        if not args.apply:
            print("seed: plan only; pass --apply to edit the sandbox working tree (nothing is committed)")
            return 0
        apply_seed(plan, args.product, args.sandbox)
    except SeedError as exc:
        print(f"seed: refused: {exc}", file=sys.stderr)
        return 2
    name = args.product.resolve().name
    print("seed: sandbox working tree edited. Review it, then (OWNER, your own git login):")
    print(f"  cd {args.sandbox}")
    print("  git status")
    print("  git -c core.autocrlf=false add -A")
    print(f'  git commit -m "{commit_message(plan, name)}"')
    print("  git push origin main        # fast-forward only; never --force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
