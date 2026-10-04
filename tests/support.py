"""Builders for synthetic project roots, cursors, sealed bundles, and disposable git repos."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import OpenAI

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.llm import transport
from repository_presenter.core.state.cas import SaveResult
from repository_presenter.core.state.schema import RepositoryRecord

REPO_ROOT = Path(__file__).resolve().parents[1]


def empty_enum_paths(node: Any, path: str = "$") -> list[str]:
    """Every JSON-schema path whose ``enum`` is an empty list. No value satisfies such a keyword,
    so a strict json_schema request carrying one cannot be decoded (the S5 HTTP 500/502 on
    Aspose.GIS, 2026-10-04, whose three link targets were all shell-owned)."""
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("enum") == []:
            found.append(path)
        for key, value in node.items():
            found.extend(empty_enum_paths(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(empty_enum_paths(value, f"{path}[{index}]"))
    return found


def assert_no_empty_enums(schema: dict[str, Any]) -> None:
    assert empty_enum_paths(schema) == [], "a strict json_schema request cannot carry an empty enum"


class InMemoryStateBackend:
    """A :class:`~repository_presenter.core.state.cas.StateBackend` test double with the real
    compare-and-swap contract (stale-version rejection, no silent lost update) but no git
    subprocess - fast enough for the bulk of ``tests/core/state/`` while ``test_git_backend.py``
    separately proves the real ref-based mechanism against a disposable local repository."""

    def __init__(self) -> None:
        self._records: dict[str, RepositoryRecord] = {}

    def load(self, repository: str) -> RepositoryRecord | None:
        return self._records.get(repository)

    def save(
        self, repository: str, record: RepositoryRecord, expected_version: int | None
    ) -> SaveResult:
        current = self._records.get(repository)
        current_version = current.state_version if current is not None else None
        if current_version != expected_version:
            return SaveResult(outcome="stale", record=current)
        saved = record.model_copy(update={"state_version": (current_version or 0) + 1})
        self._records[repository] = saved
        return SaveResult(outcome="saved", record=saved)


def model_listing(*models: tuple[str, str]) -> httpx.Response:
    """A ``GET /models`` body in the OpenAI list shape, one entry per (id, owned_by)."""
    data = [{"id": model_id, "object": "model", "owned_by": owner} for model_id, owner in models]
    return httpx.Response(200, json={"object": "list", "data": data})


def mock_gateway(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Serve the gateway from ``handler`` through the real SDK client, never the network."""

    def build(config: GatewayConfig) -> OpenAI:
        return OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

    monkeypatch.setattr(transport, "build_client", build)


def write_cursor(
    root: Path,
    *,
    gate: str = "G0_FOUNDATION",
    gate_status: str = "READY",
    work_item: str = "G0-W01",
    work_item_status: str = "READY",
    recorded_candidates: int = 0,
    denominator: int = 34,
    canary: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
) -> Path:
    """Write a minimal cursor with the fields the CLI reports."""
    path = root / "project" / "state.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        "progress:",
        f"  current_candidates: {recorded_candidates}",
        f"  denominator: {denominator}",
        f"  canary: {canary}",
        "current_gate:",
        f"  id: {gate}",
        f"  status: {gate_status}",
        "active_work_item:",
        f"  id: {work_item}",
        f"  status: {work_item_status}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_bundle(
    root: Path,
    repository_dir: str,
    revision: str,
    state: str | None,
    *,
    raw: str | None = None,
    current: bool = True,
) -> Path:
    """Create a bundle directory; seal it with a manifest when ``state`` or ``raw`` is given.

    Writes ``CURRENT`` pointing at ``revision`` too (unless ``current=False``), matching what a
    real seal always does - ``count_current_candidates`` (TB-06) only ever resolves a repository
    through its own ``CURRENT`` file, never by scanning revision directories directly.
    """
    bundle = root / "candidates" / repository_dir / revision
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / "manifest.json"
    if raw is not None:
        manifest.write_text(raw, encoding="utf-8")
    elif state is not None:
        readme = bundle / "README.md"
        readme.write_bytes(b"")
        digest = {"README.md": {"sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}}
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": repository_dir.replace("__", "/", 1),
                    "revision": revision,
                    "state": state,
                    "files": digest,
                }
            ),
            encoding="utf-8",
        )
    if current and (raw is not None or state is not None):
        (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def init_git_repository(path: Path, *, with_commit: bool = True) -> Path:
    """A disposable local repository on branch ``main`` with a local identity.

    ``git init``'s exit status is never the evidence: when git already resolves ``path`` inside
    some repository, ``git init`` there is a no-op re-init that still exits 0, and every fixture
    command after it (identity config, ``add``, ``commit``) lands on that repository instead -
    measured 2026-09-11 as fixture commits on live lane branches and this checkout's own identity
    and ``core.bare`` rewritten (RESEARCH_AND_GUIDELINES.md section 29, G4-W17 arrival item 55).
    So the target is refused up front if git resolves any repository for it, and the repository
    just created is verified to be the one at ``path`` before anything is written into it.
    """
    path.mkdir(parents=True, exist_ok=True)
    enclosing = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    if enclosing.returncode == 0:
        raise RuntimeError(
            f"refusing to init a fixture repository at {path}: git already resolves it inside"
            f" {enclosing.stdout.strip()}, where `git init` would be a no-op re-init exiting 0"
            " and every fixture command after it would land on that repository"
        )
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        result = run_git(args, cwd=path)
        assert result.returncode == 0, result.stderr
    own = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    assert own.returncode == 0, own.stderr
    assert Path(own.stdout.strip()).resolve() == (path / ".git").resolve(), (
        f"fixture at {path} resolved to a different repository: {own.stdout.strip()}"
    )
    if with_commit:
        (path / "README.md").write_text("# test\n", encoding="utf-8")
        commit_all(path, "initial")
    return path


def commit_all(path: Path, message: str) -> str:
    """Stage everything, commit, and return the new HEAD revision."""
    assert run_git(["add", "."], cwd=path).returncode == 0
    result = run_git(["commit", "-q", "-m", message], cwd=path)
    assert result.returncode == 0, result.stderr
    return head_revision(path)


def head_revision(path: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd=path)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@dataclass(frozen=True)
class CallStatistics:
    """How often a job's first reply was accepted, from a sealed ledger.

    RESEARCH_AND_GUIDELINES.md section 27.6 control 1: first-attempt acceptance and the re-ask
    share are computed from the sealed calls.jsonl, never estimated. Only provider calls count;
    a reused stored output was accepted when it was first made.
    """

    calls: int
    invalid: int
    rejections: tuple[str, ...] = ()

    @property
    def first_attempt_rate(self) -> float:
        return 100.0 * (self.calls - self.invalid) / self.calls if self.calls else 100.0

    @property
    def reask_share(self) -> float:
        return 100.0 * self.invalid / self.calls if self.calls else 0.0


def call_statistics(calls_jsonl: Path) -> dict[str, CallStatistics]:
    """Per job, plus ``TOTAL``, the provider calls and how many were rejected."""
    calls: Counter[str] = Counter()
    invalid: Counter[str] = Counter()
    rejections: dict[str, list[str]] = {}
    for line in calls_jsonl.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("disposition") != "provider_call":
            continue
        for key in (record["job"], "TOTAL"):
            calls[key] += 1
            if record.get("outcome") == "response_invalid":
                invalid[key] += 1
                rejections.setdefault(key, []).extend(record.get("rejection") or ())
    return {
        job: CallStatistics(count, invalid[job], tuple(rejections.get(job, ())))
        for job, count in sorted(calls.items())
    }


def monitor_registry_entry(
    repository: str, *, mode: str = "dry_run", repository_id: int = 1
) -> dict[str, Any]:
    """One registry entry payload for an Aspose FOSS repository (``data/registry.json`` shape)."""
    owner, name = repository.split("/")
    family = owner.removeprefix("aspose-").removesuffix("-foss")
    platform = name.split("-for-")[1].lower()
    platform = "net" if platform == ".net" else platform
    return {
        "repository": repository,
        "family": family,
        "platform": platform,
        "ecosystem": platform,
        "mode": mode,
        "policy_profile": "fixture",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_fixture_{repository_id}",
        },
    }


class FakeDefaultBranchReader:
    """Injected stand-in for ``core/github/read_client.py::fetch_default_branch_sha``.

    Each repository maps to a head sha, a ready ``DefaultBranchRead``, or an exception to raise.
    Every call and the token it was given are recorded, so a test can prove what was read.
    """

    def __init__(self, outcomes: dict[str, str | DefaultBranchRead | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []
        self.tokens: list[str | None] = []

    def __call__(self, repository: str, *, token: str | None = None) -> DefaultBranchRead:
        self.calls.append(repository)
        self.tokens.append(token)
        outcome = self.outcomes[repository]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, DefaultBranchRead):
            return outcome
        return DefaultBranchRead(repository, sha=outcome, branch="main")


def make_permit(repository: str, *, mode: str = "full", effect: str = "readme_proposal") -> Any:
    """A ``WritePermit`` for a repository that is not a real Aspose FOSS name (the registry model
    validates the name, ``model_construct`` does not) - the effect modules only read ``.effect``
    and ``.entry.repository`` from it."""
    from repository_presenter.core.registry.models import RegistryEntry
    from repository_presenter.core.registry.write_gate import WritePermit

    entry = RegistryEntry.model_construct(
        repository=repository,
        family="fixture",
        platform="fixture",
        ecosystem="fixture",
        mode=mode,
        policy_profile="fixture",
        active=True,
        provider_identity=None,
    )
    return WritePermit(effect=effect, entry=entry)  # type: ignore[arg-type]


def write_registry_file(root: Path, entries: list[dict[str, Any]]) -> Path:
    """``data/registry.json`` under a synthetic project root."""
    path = root / "data" / "registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8")
    return path


def write_proposable_bundle(
    root: Path,
    repository: str,
    revision: str,
    readme_text: str,
    *,
    state: str = "READY_FOR_PROPOSAL",
) -> Path:
    """A sealed bundle with a real README and a manifest that verifies, plus ``CURRENT``."""
    owner, name = repository.split("/", 1)
    bundle = root / "candidates" / f"{owner}__{name}" / revision
    bundle.mkdir(parents=True, exist_ok=True)
    data = readme_text.encode("utf-8")
    (bundle / "README.md").write_bytes(data)
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repository": repository,
                "revision": revision,
                "state": state,
                "files": {
                    "README.md": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def merge_to_origin_main(root: Path, message: str = "merge") -> str:
    """Commit everything under ``root`` (initialising a disposable repository on first use) and
    point ``refs/remotes/origin/main`` at the new commit - the state of a control checkout whose
    ``main`` already holds that content. Returns the commit."""
    if not (root / ".git").exists():
        init_git_repository(root, with_commit=False)
    revision = commit_all(root, message)
    assert run_git(["update-ref", "refs/remotes/origin/main", revision], cwd=root).returncode == 0
    return revision
