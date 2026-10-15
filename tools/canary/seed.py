"""Seed the sandbox with one product's committed tree: one pinned, reproducible commit (local only).

The sandbox canary (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) proposes a README correction to
``babar-raza/presenter-sandbox``. A correction needs facts, and facts need the product's source
tree, not only its README: a README-and-LICENSE repository is a placeholder the pipeline refuses
(``insufficient_evidence``). So the sandbox is seeded with a copy of one real product at one pinned
revision, once, by the owner.

The correction bundle, the authorization record and the hosted dry run all name the sandbox's
*source revision*: the commit the seeding creates. So that the bundle can be reviewed and merged
BEFORE the seed is pushed, the seed commit is reproducible: its tree is the product's tree at the
pinned revision minus ``.github/``, its parent is the sandbox head the pin names, and its author,
committer, date and message are constants of this module, so every machine that follows the pin
makes the same commit id. ``ops/sandbox-canary/seed.json`` records that id; ``--commit`` makes the
commit and refuses unless it equals the pin, so what the owner pushes is exactly what was reviewed.

This module only creates objects in the owner's two local clones. It never touches a working tree,
never pushes, never contacts a network and never changes the product clone. The owner's own push of
the one fast-forward commit, with the owner's own credentials, is the one write the seeding needs,
to the owner's own throwaway repository.

What it does, and refuses:

* uses exactly the blobs the product's pinned commit holds (read with plumbing, so no line-ending
  filter, ``core.autocrlf``, file-mode setting or signing configuration can alter a byte or the id);
* makes the sandbox a faithful copy of that tree, not a merge (the sandbox's previous contents stay
  in its git history, as the commit's parent);
* drops ``.github/`` (workflows and issue templates would run, or be offered, in the sandbox) and
  says so;
* refuses a symbolic link, a submodule, an absolute or ``..`` path, an oversized file, an oversized
  tree, and a sandbox clone with uncommitted changes;
* refuses a product clone whose ``HEAD`` is not the pinned revision or whose ``origin`` is not the
  pinned repository, and a sandbox clone whose ``HEAD`` is not the pinned parent or whose ``origin``
  is not ``babar-raza/presenter-sandbox``.

    python tools/canary/seed.py --product DIR --sandbox DIR            # plan only, writes nothing
    python tools/canary/seed.py --product DIR --sandbox DIR --commit   # make the pinned commit
    python tools/canary/seed.py --product DIR --sandbox DIR --write-pin --product-repository OWNER/NAME
                                                                       # operator: record the pin
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

SANDBOX_REPOSITORY = "babar-raza/presenter-sandbox"
SANDBOX_REMOTE = re.compile(r"github\.com[:/]babar-raza/presenter-sandbox(?:\.git)?/?$")
#: Paths that must not travel: anything that would make the sandbox run or offer automation.
DROPPED_PREFIXES = (".github/",)
MAX_FILE_BYTES = 5_000_000
MAX_TOTAL_BYTES = 40_000_000
MAX_FILES = 5_000
_SYMLINK, _SUBMODULE = "120000", "160000"
_SHA = re.compile(r"^[0-9a-f]{40}$")

#: The seed commit's identity and time are constants: the commit id must not depend on who runs
#: this, on their git configuration or on when. 2026-10-12T00:00:00Z.
SEED_NAME = "Repository Presenter canary seed"
SEED_EMAIL = "canary-seed@users.noreply.github.com"
SEED_DATE = "1791763200 +0000"
SEED_BRANCH = "seed"  # the local branch in the sandbox clone that names the commit to push

PIN_PATH = Path(__file__).resolve().parents[2] / "ops" / "sandbox-canary" / "seed.json"


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


@dataclass(frozen=True)
class SeedPin:
    """``ops/sandbox-canary/seed.json``: the commit the owner will push, as reviewed."""

    product_repository: str
    product_revision: str
    sandbox_parent: str
    commit: str
    tree: str
    message: str


@dataclass(frozen=True)
class SeedCommit:
    sha: str
    tree: str
    parent: str
    message: str


def _run(
    directory: Path,
    args: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    stdin: bytes | None = None,
) -> bytes:
    done = subprocess.run(
        ["git", *args],
        cwd=directory,
        capture_output=True,
        check=False,
        input=stdin,
        env=None if env is None else {**os.environ, **env},
    )
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", errors="replace").strip()
        raise SeedError(f"git {' '.join(args[:2])} failed in {directory}: {detail}")
    return done.stdout


def git(directory: Path, *args: str, binary: bool = False) -> str | bytes:
    out = _run(directory, args)
    return out if binary else out.decode("utf-8")


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


def _remote_matches(directory: Path, repository: str) -> bool:
    remote = _text(directory, "remote", "get-url", "origin").strip()
    return re.search(rf"github\.com[:/]{re.escape(repository)}(?:\.git)?/?$", remote, re.I) is not None


def plan_seed(
    product: Path, sandbox: Path, *, check_remote: bool = True, pin: SeedPin | None = None
) -> SeedPlan:
    """What seeding would do, or :class:`SeedError`. Reads both clones; changes neither.

    With ``pin`` the product clone must be at the pinned revision (and, unless ``check_remote`` is
    off, be a clone of the pinned repository), and the sandbox clone at the pinned parent."""
    if _text(sandbox, "status", "--porcelain").strip():
        raise SeedError(f"{sandbox} has uncommitted changes: commit or discard them first")
    if check_remote:
        remote = _text(sandbox, "remote", "get-url", "origin").strip()
        if not SANDBOX_REMOTE.search(remote):
            raise SeedError(
                f"{sandbox}'s origin is not babar-raza/presenter-sandbox ({remote!r}); "
                "seeding refuses any other repository"
            )
        if pin is not None and not _remote_matches(product, pin.product_repository):
            raise SeedError(
                f"{product}'s origin is not {pin.product_repository}; the pin seeds that product only"
            )
    plan = SeedPlan(product_revision=_text(product, "rev-parse", "HEAD").strip())
    if pin is not None:
        if plan.product_revision != pin.product_revision:
            raise SeedError(
                f"{product} is at {plan.product_revision}, the pin seeds {pin.product_revision}: "
                f"git -C {product} checkout {pin.product_revision}"
            )
        parent = _text(sandbox, "rev-parse", "HEAD").strip()
        if parent != pin.sandbox_parent:
            raise SeedError(
                f"{sandbox} is at {parent}, the pin was made on {pin.sandbox_parent}: the sandbox "
                "moved since the pin, so the pinned commit is no longer a fast-forward of it"
            )
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


def seed_message(product_repository: str, revision: str) -> str:
    return f"Seed the sandbox with {product_repository.rsplit('/', 1)[-1]} at {revision}"


def build_seed_commit(plan: SeedPlan, product: Path, sandbox: Path, *, message: str) -> SeedCommit:
    """The seed commit, as git objects in ``sandbox``'s repository; no ref, working tree or index of
    the clone changes. Its tree is the product's pinned tree without the dropped paths; its parent
    is the sandbox's ``HEAD``. Deterministic: see the module docstring."""
    parent = _text(sandbox, "rev-parse", "HEAD").strip()
    # The product's objects, so the sandbox repository can name and later push them. They are
    # reachable only through the new commit's tree: the product's history never travels.
    _run(sandbox, ["fetch", "--no-tags", "--quiet", str(product.resolve()), plan.product_revision])
    git_dir = Path(_text(sandbox, "rev-parse", "--absolute-git-dir").strip())
    with tempfile.TemporaryDirectory(dir=git_dir, prefix="seed-") as scratch:
        index = {"GIT_INDEX_FILE": str(Path(scratch) / "index")}
        _run(sandbox, ["read-tree", f"{plan.product_revision}^{{tree}}"], env=index)
        if plan.dropped:
            names = "".join(f"{path}\0" for path in plan.dropped).encode("utf-8")
            _run(sandbox, ["update-index", "--force-remove", "-z", "--stdin"], env=index, stdin=names)
        tree = _run(sandbox, ["write-tree"], env=index).decode("ascii").strip()
    identity = {
        "GIT_AUTHOR_NAME": SEED_NAME,
        "GIT_AUTHOR_EMAIL": SEED_EMAIL,
        "GIT_AUTHOR_DATE": SEED_DATE,
        "GIT_COMMITTER_NAME": SEED_NAME,
        "GIT_COMMITTER_EMAIL": SEED_EMAIL,
        "GIT_COMMITTER_DATE": SEED_DATE,
    }
    sha = (
        _run(
            sandbox,
            ["-c", "commit.gpgsign=false", "commit-tree", tree, "-p", parent, "-m", message],
            env=identity,
        )
        .decode("ascii")
        .strip()
    )
    return SeedCommit(sha=sha, tree=tree, parent=parent, message=message)


def load_pin(path: Path = PIN_PATH) -> SeedPin:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        pin = SeedPin(
            product_repository=str(raw["product"]["repository"]),
            product_revision=str(raw["product"]["revision"]),
            sandbox_parent=str(raw["sandbox"]["parent"]),
            commit=str(raw["seed"]["commit"]),
            tree=str(raw["seed"]["tree"]),
            message=str(raw["seed"]["message"]),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SeedError(f"the seed pin {path} cannot be read: {exc}") from exc
    for label, value in (
        ("product.revision", pin.product_revision),
        ("sandbox.parent", pin.sandbox_parent),
        ("seed.commit", pin.commit),
        ("seed.tree", pin.tree),
    ):
        if not _SHA.match(value):
            raise SeedError(f"the seed pin's {label} is not a 40-character commit id")
    if pin.message != seed_message(pin.product_repository, pin.product_revision):
        raise SeedError("the seed pin's message is not the message this tool composes")
    if raw["sandbox"].get("repository") != SANDBOX_REPOSITORY:
        raise SeedError(f"the seed pin does not name {SANDBOX_REPOSITORY}")
    return pin


def write_pin(path: Path, *, product_repository: str, plan: SeedPlan, commit: SeedCommit) -> None:
    document = {
        "schema_version": 1,
        "note": (
            "The commit tools/canary/seed.py --commit makes in a clone of the sandbox, and the "
            "owner pushes once. Reproducible: tree = the product's tree at product.revision minus "
            ".github/, parent = sandbox.parent. The canary bundle's source revision is seed.commit."
        ),
        "product": {"repository": product_repository, "revision": plan.product_revision},
        "sandbox": {"repository": SANDBOX_REPOSITORY, "parent": commit.parent},
        "seed": {
            "commit": commit.sha,
            "tree": commit.tree,
            "message": commit.message,
            "files": len(plan.copy),
            "bytes": plan.total_bytes,
            "dropped": plan.dropped,
        },
    }
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--product", type=Path, required=True, help="a clone of the product, HEAD at the pinned revision")
    parser.add_argument("--sandbox", type=Path, required=True, help="a clean clone of babar-raza/presenter-sandbox")
    parser.add_argument("--pin", type=Path, default=PIN_PATH, help="the reviewed seed pin (default: ops/sandbox-canary/seed.json)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--commit", action="store_true", help="make the pinned commit in the sandbox clone (default: plan only)")
    mode.add_argument("--write-pin", action="store_true", help="operator: record the commit this would make as the pin")
    parser.add_argument("--product-repository", metavar="OWNER/NAME", help="with --write-pin: the product's repository")
    args = parser.parse_args(argv)
    try:
        if args.write_pin:
            if not args.product_repository:
                raise SeedError("--write-pin needs --product-repository OWNER/NAME")
            plan = plan_seed(args.product, args.sandbox)
            message = seed_message(args.product_repository, plan.product_revision)
            commit = build_seed_commit(plan, args.product, args.sandbox, message=message)
            write_pin(args.pin, product_repository=args.product_repository, plan=plan, commit=commit)
            print(f"seed: pinned commit {commit.sha} (tree {commit.tree}) on {commit.parent} in {args.pin}")
            return 0
        pin = load_pin(args.pin)
        plan = plan_seed(args.product, args.sandbox, pin=pin)
        print(f"seed: product {pin.product_repository} at {plan.product_revision}")
        print(f"seed: copy {len(plan.copy)} files ({plan.total_bytes} bytes)")
        print(f"seed: drop {len(plan.dropped)} automation file(s) under .github/")
        print(f"seed: the sandbox's {len(plan.remove)} file(s) the product lacks leave the tree: {', '.join(plan.remove) or 'none'}")
        print(f"seed: the pinned commit is {pin.commit} on the sandbox head {pin.sandbox_parent}")
        if not args.commit:
            print("seed: plan only; pass --commit to make the pinned commit in the sandbox clone")
            return 0
        commit = build_seed_commit(plan, args.product, args.sandbox, message=pin.message)
        if commit.sha != pin.commit or commit.tree != pin.tree:
            raise SeedError(
                f"the commit made here is {commit.sha} (tree {commit.tree}), not the pinned "
                f"{pin.commit} (tree {pin.tree}): do not push it; check the product revision and "
                "that git is at least 2.30"
            )
        _run(args.sandbox, ["update-ref", f"refs/heads/{SEED_BRANCH}", commit.sha])
    except SeedError as exc:
        print(f"seed: refused: {exc}", file=sys.stderr)
        return 2
    print(f"seed: commit {commit.sha} equals the pin; the branch '{SEED_BRANCH}' names it. Nothing is pushed.")
    print("seed: to publish it (OWNER, your own git login; one fast-forward; never --force):")
    print(f"  git -C {args.sandbox} push origin {SEED_BRANCH}:main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
